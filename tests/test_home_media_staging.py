"""Opt-in Linux integration test of the actual home media staging tasks.

Run with OLDAP_MEDIA_TEST_HOST=media.home.org. Uses only a new private /tmp
fixture over SSH; never stops services or touches live media. The controller
needs Ansible/PyYAML, and the target needs rsync with Linux ACL/xattr support.
"""
import copy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOST = os.environ.get('OLDAP_MEDIA_TEST_HOST')


@unittest.skipUnless(HOST, 'Set OLDAP_MEDIA_TEST_HOST for the Linux fixture test')
class MediaStagingTests(unittest.TestCase):
    def test_precopy_final_sync_and_frozen_archive(self):
        """Preserve metadata, detect hidden edits/deletions, and freeze the copy."""
        play = yaml.safe_load((ROOT / 'oldap-jena-home-backup.yml').read_text())[0]
        selected = {}
        for task in play['tasks']:
            for item in task.get('block', [task]):
                selected[item['name']] = item

        def actual(name):
            return copy.deepcopy(selected[name])

        def python(name, code):
            return {'name': name, 'ansible.builtin.command': {
                'argv': ['/usr/bin/python3', '-c', code, '{{ fixture.path }}']}}

        create = '''import os,sys
from pathlib import Path
root=Path(sys.argv[1]); media=root/'live/data/media'; media.mkdir(parents=True)
(root/'backup/tree').mkdir(parents=True)
(media/'edit').write_bytes(b'AAAA'); (media/'delete').write_text('delete me')
(media/'mode').write_text('metadata'); (media/'mode').chmod(0o600)
os.setxattr(media/'mode', 'user.oldap_fixture', b'old')
(media/'link-a').write_text('hardlink'); os.link(media/'link-a', media/'link-b')
ops=root/'live/data/operations'; ops.mkdir(); (ops/'registry').write_text('before')
'''
        mutate = '''import os,sys
from pathlib import Path
root=Path(sys.argv[1]); media=root/'live/data/media'; item=media/'edit'; old=item.stat()
item.write_bytes(b'BBBB'); os.utime(item, ns=(old.st_atime_ns,old.st_mtime_ns))
(media/'delete').unlink(); (media/'new').write_text('added')
(media/'mode').chmod(0o640); os.setxattr(media/'mode','user.oldap_fixture',b'new')
(root/'live/data/operations/registry').write_text('after')
'''
        check = '''import os,sys
from pathlib import Path
root=Path(sys.argv[1]); staged=root/'backup/tree'/str(root).lstrip('/')/'live'
media=staged/'data/media'
assert (media/'edit').read_bytes()==b'BBBB'
assert not (media/'delete').exists() and (media/'new').read_text()=='added'
assert (media/'mode').stat().st_mode & 0o777 == 0o640
assert os.getxattr(media/'mode','user.oldap_fixture')==b'new'
assert (media/'link-a').stat().st_ino==(media/'link-b').stat().st_ino
assert (staged/'data/operations/registry').read_text()=='after'
# Simulate resumed writers after accepted final comparison. Staging must stay frozen.
(root/'live/data/media/edit').write_bytes(b'CCCC')
(root/'live/data/operations/registry').write_text('resumed')
'''
        inspect_archive = '''import sys,tarfile
from pathlib import Path
root=Path(sys.argv[1]); prefix=str(root).lstrip('/')+'/live/'
with tarfile.open(root/'backup/media.tar') as archive:
 assert archive.extractfile(prefix+'data/media/edit').read()==b'BBBB'
 assert archive.extractfile(prefix+'data/operations/registry').read()==b'after'
 assert prefix+'data/media/delete' not in archive.getnames()
'''
        verify = actual('Verify finalized media staging against stopped sources')
        # Execute a successful rsync dry-run that detects changed state. The real
        # task must fail on itemized differences even though rsync returns zero.
        negative = copy.deepcopy(verify)
        negative['ignore_errors'] = True
        negative['register'] = 'detected_changes'
        tasks = [python('Create Linux fixture', create),
                 actual('Pre-copy media and operational state while services are online'),
                 python('Modify content with unchanged size and mtime', mutate),
                 negative,
                 {'ansible.builtin.assert': {'that': [
                     'detected_changes is failed', 'detected_changes.rc == 0',
                     'detected_changes.stdout | length > 0']}},
                 actual('Finalize media staging from stopped sources'), verify,
                 python('Check frozen data and resume fixture writers', check),
                 actual('Archive frozen media staging while services are online'),
                 actual('Restrict media archive permissions'),
                 actual('Compare media archive with frozen staging'),
                 python('Verify archived state excludes resumed writes', inspect_archive)]
        fixture = [{'hosts': 'all', 'gather_facts': False,
                    'vars': {'ansible_python_interpreter': '/usr/bin/python3',
                             'ansible_user': 'rosenth', 'media_host': HOST,
                             'home_media_precopy': True,
                             'media_backup': '{{ fixture.path }}/backup',
                             'media_paths': ["{{ fixture.path[1:] }}/live/data/media",
                                             "{{ fixture.path[1:] }}/live/data/operations"],
                             'media_sync_argv': play['vars']['media_sync_argv']},
                    'tasks': [
                        {'ansible.builtin.tempfile': {'state': 'directory',
                                                     'prefix': 'oldap-staging-test-'},
                         'register': 'fixture'},
                        {'block': tasks, 'always': [
                            {'ansible.builtin.file': {'path': '{{ fixture.path }}',
                                                     'state': 'absent'}}]}]}]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'play.yml'
            path.write_text(yaml.safe_dump(fixture))
            result = subprocess.run(['ansible-playbook', '-i', HOST + ',', str(path)],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
