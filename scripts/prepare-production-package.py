#!/usr/bin/env python3
"""Build private, pinned production Compose/runtime archives without deploying.

Use accepted home topology/images with the frozen production identities, URLs,
mail settings and archive policy. Generate new private Jena transport keys. Never
copy home signing keys or home data. The output directory must not exist; all
state import, final source-drift checks and private acceptance remain separate.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import tarfile

# These are backend wiring, not source account/site settings. All other accepted
# environment keys inherit the source value when the old service defined one.
JENA_ENV = {'OLDAP_BACKEND', 'OLDAP_TS_SERVER', 'GUNICORN_CMD_ARGS',
            'OLDAP_ARCHIVE_POLICY_FILE', 'OLDAP_STAGING_LOCK_REDIS_URL'}


def production_environment(home, source):
    """Keep accepted backend wiring and source identity/site/mail configuration.

    Source-only GraphDB writer variables are deliberately not introduced into the
    Jena environment. New Jena secrets are replaced by the package builder later.
    """
    for key in home:
        if key.endswith(('_PASSWORD', '_SECRET', '_TOKEN', '_KEY')) and not key.startswith('OLDAP_JENA_') and key not in source:
            raise ValueError('Refusing to copy a home credential absent from production: '+key)
    return {k: (v if k in JENA_ENV or k.startswith('OLDAP_JENA_') else source.get(k, v))
            for k, v in home.items()}


def read_member(archive, name):
    """Read one regular configuration member, without extracting archive paths."""
    with tarfile.open(archive) as stream:
        members = [m for m in stream if m.name == name]
        if len(members) != 1 or not members[0].isfile():
            raise ValueError('Missing, duplicate or nonregular source configuration: '+name)
        return stream.extractfile(members[0]).read()


def write(path, data, mode=0o600):
    """Write a new private package member; never replace an existing input."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data.encode() if isinstance(data, str) else data)
    path.chmod(mode)


def archive(directory, destination):
    """Archive ordinary files/directories only, with deterministic metadata."""
    with tarfile.open(destination, 'w') as stream:
        for path in sorted(directory.rglob('*')):
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                raise ValueError('Package must contain only ordinary paths')
            info = stream.gettarinfo(str(path), str(path.relative_to(directory)))
            info.uid = info.gid = 0; info.uname = info.gname = ''; info.mtime = 0
            if path.is_file():
                with path.open('rb') as content: stream.addfile(info, content)
            else: stream.addfile(info)


def build(home_inputs, source, release, target_root, output):
    """Create complete candidate archives and a manifest binding their inputs.

    Args:
        home_inputs: Private accepted API/media JSON and static home input files.
        source: Verified frozen production snapshot directory, including tar files.
        release: Accepted native service distribution, with build.json.
        target_root: New absolute production root; writable paths stay below data/.
        output: New private local directory. No existing files are overwritten.
    """
    if target_root.parent != Path('/srv/storage') or not target_root.name.startswith('oldap-jena-production-'):
        raise ValueError('Expected a new production target root')
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    source_config = {role: json.loads((source/f'{role}-source-compose.json').read_text()) for role in ['api', 'media']}
    config = {role: json.loads((home_inputs/f'{role}-compose.json').read_text()) for role in ['api', 'media']}
    native_build = json.loads((release/'build.json').read_text())
    service = release/'lib'/f'oldap-jena-service-{native_build["version"]}.jar'
    if hashlib.sha256(service.read_bytes()).hexdigest() != native_build['service_sha256']:
        raise ValueError('Native service differs from its build manifest')
    if hashlib.sha256((release/'lib/fuseki-server.jar').read_bytes()).hexdigest() != native_build['fuseki_sha256']:
        raise ValueError('Native dependency differs from its build manifest')
    keys = {name: secrets.token_hex(32) for name in ['identity','service','bootstrap','fulltext','admin']}
    for role, document in config.items():
        document['name'] = 'compose'
        for name, svc in document['services'].items():
            svc.pop('profiles', None)
            svc['pull_policy'] = 'never'
            if 'environment' in svc:
                source_name = 'oldap-api' if name == 'oldap-jena-identity' else name
                svc['environment'] = production_environment(svc['environment'], source_config[role]['services'].get(source_name, {}).get('environment', {}))
        # Reuse the actual production bridge/volume identities; do not carry a
        # home rehearsal network name or replace shared production media caches.
        for key in ['networks', 'volumes']:
            if key in source_config[role]: document[key] = copy.deepcopy(source_config[role][key])
    api = config['api']['services']; media = config['media']['services']
    api_env = api['oldap-api']['environment']
    for name in ['identity','service','bootstrap','fulltext']:
        api_env['OLDAP_JENA_'+name.upper()+'_KEY'] = keys[name]
    identity = api['oldap-jena-identity']['environment']
    for key in ['OLDAP_ACCESS_JWT_SECRET','OLDAP_JWT_ISSUER','OLDAP_JWT_AUDIENCE']:
        identity[key] = api_env[key]
    identity['OLDAP_JENA_IDENTITY_KEY'] = keys['identity']
    proxy = api['caddy']['environment']; source_proxy = source_config['api']['services']['caddy']['environment']
    proxy.update(OLDAP_JENA_ADMIN_KEY=keys['admin'], OLDAP_JENA_CONSOLE_USER=source_proxy['GRAPHDB_BASIC_USER'],
                 OLDAP_JENA_CONSOLE_PASSWORD_HASH=source_proxy['GRAPHDB_BASIC_HASH'])
    if media['mediaserver']['environment']['OLDAP_ACCESS_JWT_SECRET'] != api_env['OLDAP_ACCESS_JWT_SECRET']:
        raise ValueError('Frozen API and media signing keys differ')
    mappings = {
        ('redis','/data'):target_root/'data/redis',
        ('oldap-api','/data'):target_root/'data/api',
        ('oldap-api','/run/oldap-policy/archive-policy.json'):target_root/'config/archive-policy.json',
        ('oldap-jena','/var/lib/oldap-jena'):target_root/'data/native',
        ('oldap-jena','/opt/oldap-jena/release'):target_root/'release',
        ('oldap-jena','/run/oldap-jena/service.properties'):target_root/'config/service.properties',
        ('oldap-jena-identity','/opt/oldap-identity/jena_identity.py'):target_root/'identity/jena_identity.py',
    }
    for name, svc in api.items():
        for mount in svc.get('volumes', []):
            key = (name, mount['target'])
            if key in mappings: mount['source'] = str(mappings[key])
            if 'oldap-jena-home-' in mount.get('source',''):
                raise ValueError('Unmapped home bind mount')
    runtime = output/'runtime'; runtime.mkdir(mode=0o700)
    shutil.copytree(release, runtime/'release')
    write(runtime/'identity/jena_identity.py', (home_inputs/'api-jena_identity.py').read_bytes(), 0o644)
    write(runtime/'config/archive-policy.json', read_member(source/'api.tar', 'opt/oldap/.env/archive-writer-client/archive-policy.json'), 0o644)
    properties = (home_inputs/'api-service.properties').read_text()
    replacements = {name+'Secret':value for name,value in keys.items()}
    replacements['adminOrigin'] = 'https://fuseki.oldap.org'
    seen = set(); lines = []
    for line in properties.splitlines():
        key = line.partition('=')[0]
        if key.endswith('Secret') and key not in replacements:
            raise ValueError('Unreviewed native secret property')
        if key in replacements:
            line = key+'='+replacements[key]; seen.add(key)
        lines.append(line)
    if seen != set(replacements): raise ValueError('Missing native secret/origin property')
    write(runtime/'config/service.properties', '\n'.join(lines)+'\n', 0o644)
    for role, document in config.items():
        directory = output/role; directory.mkdir(mode=0o700)
        write(directory/'.env', 'COMPOSE_FILE=docker-compose.yml\n')
        write(directory/'docker-compose.yml', json.dumps(document, indent=2)+'\n')
        member = 'opt/oldap/compose/Caddyfile' if role=='api' else 'opt/oldap-mediaserver/compose/Caddyfile'
        caddy = read_member(source/(role+'.tar'), member).decode()
        if role == 'api':
            # Cover both api.oldap.org and the SALSAH API alias. Public clients
            # must never reach the private identity callback through either host.
            caddy = caddy.replace('    reverse_proxy oldap-api:8000',
                '    @oldap_private path /internal/jena /internal/jena/*\n    respond @oldap_private 404\n    reverse_proxy oldap-api:8000')
            caddy += '\nhttps://fuseki.oldap.org {\n    basicauth {\n        {env.OLDAP_JENA_CONSOLE_USER} {env.OLDAP_JENA_CONSOLE_PASSWORD_HASH}\n    }\n    reverse_proxy oldap-api:8040 {\n        header_up X-Oldap-Admin-Key {env.OLDAP_JENA_ADMIN_KEY}\n    }\n}\n'
            write(directory/'frontends.json', read_member(source/'api.tar','opt/oldap/compose/frontends.json'), 0o644)
        write(directory/'Caddyfile', caddy, 0o644)
        archive(directory, output/f'candidate-{role}.tar')
    archive(runtime, output/'candidate-runtime.tar')
    files = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(output.rglob('*')) if p.is_file()}
    manifest = {'status':'prepared_offline_not_deployed','target_root':str(target_root),
                'source_snapshot':json.loads((source/'manifest.json').read_text())['snapshot_id'],
                'input_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                    [source/'manifest.json', source/'api-source-compose.json', source/'media-source-compose.json',
                     home_inputs/'api-compose.json', home_inputs/'media-compose.json', release/'build.json']},
                'source_configuration_sha256':{name:hashlib.sha256(read_member(source/(role+'.tar'),name)).hexdigest()
                    for role,name in [('api','opt/oldap/compose/Caddyfile'),('api','opt/oldap/compose/frontends.json'),
                                      ('api','opt/oldap/.env/archive-writer-client/archive-policy.json'),
                                      ('media','opt/oldap-mediaserver/compose/Caddyfile')]},
                'native_service_sha256':native_build['service_sha256'], 'files':files,
                'images':{role:{name:svc['image'] for name,svc in document['services'].items()} for role,document in config.items()},
                'required_before_activation':['Revalidate source configuration hashes at final freeze',
                    'Verify target capacity and load every pinned image',
                    'Install runtime into new root; copy frozen API/Redis state into separate data/api and data/redis',
                    'Convert, correct and model-clean final RDF; import into new data/native/dataset',
                    'With clients stopped and target Redis bind verified, selectively clear derived library caches in the target copy',
                    'Activate reviewed fulltext; complete all nine private acceptance checks'],
                'console_auth':'existing production GraphDB proxy account/hash; fresh native admin key',
                'scheduled_jobs':'not enabled or included in this core bundle; keep old timers paused until Jena backup/harvester acceptance'}
    write(output/'manifest.json', json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['home-inputs','source','release','target-root','output']:
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(); os.umask(0o077)
    result=build(args.home_inputs,args.source,args.release,args.target_root,args.output)
    print(json.dumps({'status':result['status'],'files':len(result['files']),'target_root':result['target_root']}))
