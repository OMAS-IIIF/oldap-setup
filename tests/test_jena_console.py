"""Deployment boundaries for the official, service-owned Fuseki administration UI.

Native transactions, uploads, index replacement and receipt protection are tested
by oldaplib/services/jena/check_administration.py against the packaged Java server.
"""
import base64
import sys
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[1]

class FusekiAdministrationDeploymentTests(unittest.TestCase):
    def test_official_proxy_keeps_password_and_private_transport_separate(self):
        template = jinja2.Environment(loader=jinja2.FileSystemLoader(ROOT / 'templates')).get_template('Caddyfile.j2')
        for mode, domain in [('dev','fuseki.home.org'),('prod','fuseki.oldap.org')]:
            disabled=template.render(caddy_mode=mode,caddy_email='ops@example.org')
            self.assertNotIn(domain,disabled)
            enabled=template.render(caddy_mode=mode,caddy_email='ops@example.org',oldap_jena_console_enabled=True,oldap_jena_console_origin='https://'+domain)
            self.assertIn(domain,enabled)
            self.assertIn('{env.OLDAP_JENA_CONSOLE_PASSWORD_HASH}',enabled)
            self.assertIn('header_up X-Oldap-Admin-Key {env.OLDAP_JENA_ADMIN_KEY}',enabled)
            self.assertIn('reverse_proxy oldap-api:8040',enabled)

    def test_native_overlay_adds_no_storage_owner_or_public_port(self):
        names=['docker-compose.yml','jena-compose.yml','fuseki-admin-compose.yml']
        source=''.join((ROOT/n).read_text() for n in names)
        variables={n:'/tmp/fuseki-fixture' for n in re.findall(r'\$\{([A-Z_]+)',source)}
        variables.update(OLDAP_JENA_HEAP_MB='512',OLDAP_JENA_CONSOLE_USER='admin',
            OLDAP_JENA_CONSOLE_PASSWORD_HASH='console-password-hash',GRAPHDB_BASIC_HASH='original-password-hash')
        with tempfile.TemporaryDirectory() as directory:
            env=Path(directory)/'.env';env.write_text('')
            args=['docker','compose','--env-file',str(env)]
            for n in names:args+=['-f',str(ROOT/n)]
            result=subprocess.run(args+['config','--format','json'],env={**os.environ,**variables},capture_output=True,text=True,check=True)
        services=json.loads(result.stdout)['services']
        self.assertNotIn('jena-console',services)
        self.assertNotIn('ports',services['oldap-jena'])
        self.assertEqual(services['caddy']['environment']['GRAPHDB_BASIC_HASH'],'original-password-hash')
        self.assertEqual(services['caddy']['environment']['OLDAP_JENA_CONSOLE_PASSWORD_HASH'],'console-password-hash')

    def test_candidate_validation_precedes_drain_and_preserves_rollback(self):
        tasks=yaml.safe_load((ROOT/'oldap-fuseki-admin-install.yml').read_text())[0]['tasks']
        names=[t['name'] for t in tasks]
        activation=next(t for t in tasks if 'rescue' in t)
        self.assertLess(names.index('Validate native console Caddy route before maintenance'),names.index(activation['name']))
        self.assertIn('Restore previous environment and proxy configuration',[t['name'] for t in activation['rescue']])
        recovery=yaml.safe_load((ROOT/'tasks/jena-home-start.yml').read_text())
        names=[t['name'] for t in recovery]
        self.assertLess(names.index('Verify native administration before opening ingress'),names.index('Reopen API ingress for media workers'))

    def test_real_ansible_candidate_has_literal_lines_and_preserves_credentials(self):
        tasks=yaml.safe_load((ROOT/'oldap-fuseki-admin-install.yml').read_text())[0]['tasks']
        prepare=next(t for t in tasks if t['name']=='Prepare candidate selection without changing unrelated environment')
        config=next(t for t in tasks if t['name']=='Stage private backend configuration with native listener')
        config['ansible.builtin.copy'].pop('owner')
        config['ansible.builtin.copy'].pop('group')
        before='COMPOSE_FILE=docker-compose.yml:jena-compose.yml:jena-console-compose.yml:salsah-compose.yml\nOLDAP_JENA_RELEASE=/old\nOLDAP_JENA_CONFIG=/old.properties\nGRAPHDB_BASIC_HASH=original\nOLDAP_JENA_CONSOLE_PASSWORD_HASH=independent\n'
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            variables={'ansible_python_interpreter':sys.executable,'previous_env':before,'release_dir':'/new',
                       'candidate_config':str(folder/'service.properties'),'native_admin_key':'test-key',
                       'oldap_jena_console_origin':'https://fuseki.home.org',
                       'previous_config':{'content':base64.b64encode(b'dataset=/owned\nport=3031\n').decode()}}
            play=[{'hosts':'localhost','gather_facts':False,'vars':variables,'tasks':[prepare,config,
                {'copy':{'dest':str(folder/'candidate.env'),'content':'{{ candidate_env }}','mode':'0600'}}]}]
            path=folder/'play.yml';path.write_text(yaml.safe_dump(play))
            result=subprocess.run(['ansible-playbook','-i','localhost,','-c','local',str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            env=(folder/'candidate.env').read_text().splitlines()
            self.assertIn('OLDAP_JENA_ADMIN_KEY=test-key',env)
            self.assertIn('GRAPHDB_BASIC_HASH=original',env)
            self.assertIn('OLDAP_JENA_CONSOLE_PASSWORD_HASH=independent',env)
            self.assertIn('COMPOSE_FILE=docker-compose.yml:jena-compose.yml:salsah-compose.yml:fuseki-admin-compose.yml',env)
            properties=(folder/'service.properties').read_text().splitlines()
            self.assertIn('adminPort=8040',properties)
            self.assertIn('adminSecret=test-key',properties)
            self.assertIn('port=3031',properties)
