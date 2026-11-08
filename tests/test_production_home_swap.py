"""Home rehearsal path recovery must work after an interrupted installation."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('home_swap',Path(__file__).resolve().parents[1]/'scripts/prepare-home-production-rehearsal.py')
swap=importlib.util.module_from_spec(spec);spec.loader.exec_module(swap)


class HomeSwapTests(unittest.TestCase):
    def exercise(self, interrupt):
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
            with patch.dict(swap.PREFIXES,{'api':[prefix]}), patch.object(swap,'require_stopped'), patch.object(swap.subprocess,'run',side_effect=copy):
                if interrupt:
                    with self.assertRaises(RuntimeError):swap.swap('api',root)
                else:
                    swap.swap('api',root)
                    self.assertEqual((live/'data').read_text(),'production')
                swap.restore('api',root)
                self.assertEqual((live/'data').read_text(),'home')
                with self.assertRaises(FileExistsError):swap.restore('api',root)

    def test_round_trip(self):self.exercise(False)
    def test_interrupted_copy_restores_home(self):self.exercise(True)

