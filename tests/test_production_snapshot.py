"""Production snapshot lock lifetime and shared snapshot coverage boundaries."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]


class ProductionSnapshotTests(unittest.TestCase):
    def test_failure_keeps_maintenance_lock_and_success_releases_last(self):
        tasks=yaml.safe_load((ROOT/'oldap-jena-production-backup.yml').read_text())[0]['tasks']
        start=next(i for i,t in enumerate(tasks) if t.get('name')=='Verify media access before holding the shared lock')
        for failure in ('','Verify media access before holding the shared lock','Confirm exclusive maintenance ownership before stopping any writer','Capture the reviewed production snapshot'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                path=Path(directory);log=path/'events'
                record=path/'record.py'
                record.write_text('import sys\nfrom pathlib import Path\np=Path(sys.argv[1])\nwith p.open("a") as f:f.write(sys.argv[3]+"\\n")\nsys.exit(int(sys.argv[2]==sys.argv[3]))\n')
                fixture=[{'hosts':'localhost','gather_facts':False,
                          'vars':{'ansible_python_interpreter':sys.executable},
                          'tasks':[{'name':t['name'],'ansible.builtin.command':{'argv':[sys.executable,str(record),str(log),failure,t['name']]}} for t in tasks[start:] if 'name' in t]}]
                play=path/'play.yml';play.write_text(yaml.safe_dump(fixture))
                result=subprocess.run(['ansible-playbook','-i','localhost,','-c','local',str(play)],capture_output=True,text=True)
                events=log.read_text().splitlines()
                release='Release maintenance only after successful snapshot publication'
                if failure:
                    self.assertNotEqual(result.returncode,0);self.assertNotIn(release,events)
                    if failure == 'Verify media access before holding the shared lock':
                        self.assertNotIn('Hold the existing maintenance lock independently of SSH', events)
                else:
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertEqual(events[-1],release)

    def test_production_and_home_use_one_snapshot_implementation(self):
        for filename in ['oldap-jena-production-backup.yml','oldap-jena-home-backup.yml']:
            play=yaml.safe_load((ROOT/filename).read_text())[0]
            self.assertIn('tasks/jena-snapshot.yml',[t.get('ansible.builtin.include_tasks') for t in play['tasks']])
            self.assertIn('opt/oldap-mediaserver',play['vars']['media_paths'])
            self.assertIn('srv/storage/oldap-data/oldap-app',play['vars']['api_paths'])
