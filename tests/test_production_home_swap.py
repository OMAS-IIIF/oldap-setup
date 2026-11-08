"""Home rehearsal path recovery must work after an interrupted installation."""
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('home_swap',Path(__file__).resolve().parents[1]/'scripts/prepare-home-production-rehearsal.py')
swap=importlib.util.module_from_spec(spec);spec.loader.exec_module(swap)


class HomeSwapTests(unittest.TestCase):
    def exercise(self, interrupt, force_copy=False):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); root=base/'checkpoint';root.mkdir()
            live=base/'live';live.mkdir();(live/'data').write_text('home')
            prefix=str(live).lstrip('/')
            staged=root/'source-tree'/prefix;staged.mkdir(parents=True)
            (staged/'data').write_text('production')
            (root/'prepared.json').write_text('{}')
            def copy(args,**kwargs):
                if interrupt:
                    Path(args[-1]).mkdir();(Path(args[-1])/'partial').write_text('incomplete')
                    raise RuntimeError('Injected interrupted copy')
                shutil.copytree(args[-2],args[-1])
            original_stat=Path.stat
            def staged_stat(path,*args,**kwargs):
                result=original_stat(path,*args,**kwargs)
                if force_copy and path==staged:
                    fields=list(result);fields[2]+=1
                    return os.stat_result(fields)
                return result
            with patch.object(Path,'stat',staged_stat), patch.dict(swap.PREFIXES,{'api':[prefix]}), patch.object(swap,'require_stopped'), patch.object(swap.subprocess,'run',side_effect=copy):
                if interrupt:
                    original_rename=Path.rename
                    def interrupted_rename(path,target):
                        if path==staged:
                            Path(target).mkdir();(Path(target)/'partial').write_text('incomplete')
                            raise RuntimeError('Interrupted source installation')
                        return original_rename(path,target)
                    with patch.object(Path,'rename',interrupted_rename):
                        with self.assertRaises(RuntimeError):swap.swap('api',root)
                else:
                    swap.swap('api',root)
                    self.assertEqual((live/'data').read_text(),'production')
                swap.restore('api',root)
                self.assertEqual((live/'data').read_text(),'home')
                with self.assertRaises(FileExistsError):swap.restore('api',root)

    def test_round_trip(self):self.exercise(False)
    def test_interrupted_copy_restores_home(self):self.exercise(True)

    def test_cross_filesystem_copy_round_trip(self):self.exercise(False, force_copy=True)
    def test_cross_filesystem_interrupted_copy(self):self.exercise(True, force_copy=True)

    def test_transport_changes_preserve_rdf_and_secret_values(self):
        original={'OLDAP_API_URL':'https://api.oldap.org',
                  'PUBLIC_API_URL':'https://api.oldap.org',
                  'PROJECT_URL':'https://fasnacht.digital/',
                  'OLDAP_IMPORT_SERVICE_SUBJECT':'https://fasnacht.digital/Importer',
                  'TOKEN_SECRET':'literal$$secret', 'OLDAP_IMPORT_EMAIL_BACKEND':'smtp'}
        result=swap.home_environment(original)
        self.assertEqual(result['OLDAP_API_URL'],'http://api.home.org')
        self.assertEqual(result['PUBLIC_API_URL'],'https://api.home.org')
        self.assertEqual(result['OLDAP_IMPORT_EMAIL_BACKEND'],'console')
        for key in ['PROJECT_URL','OLDAP_IMPORT_SERVICE_SUBJECT','TOKEN_SECRET']:
            self.assertEqual(result[key],original[key])
        self.assertEqual(original['OLDAP_API_URL'],'https://api.oldap.org')
