"""Migration cache cleanup preserves durable auth/coordination and unknown data."""
import importlib.util
import json
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('cache',Path(__file__).resolve().parents[1]/'scripts/clear-migrated-model-cache.py')
cache=importlib.util.module_from_spec(spec);spec.loader.exec_module(cache)


class RedisFake:
    def __init__(self):
        self.values={b'model':b'{"__class__":"DataModel","legacy":true}',
                     b'revoked':b'1', b'session':b'{"__class__":"AuthSession"}',
                     b'nested':b'{"data":{"__class__":"User"}}'}
        self.changed=False
    def scan_iter(self, **kwargs):return iter(list(self.values))
    def type(self,key):return b'string'
    def get(self,key):return self.values[key]
    def eval(self,script,n,key,value):
        if self.changed:return -1
        if self.values[key]!=value:return -1
        del self.values[key];return 1


class CacheMigrationTests(unittest.TestCase):
    def test_plan_is_nonmutating_and_apply_preserves_other_records(self):
        r=RedisFake();before=dict(r.values)
        self.assertEqual(cache.clear_cache(r)['status'],'planned');self.assertEqual(r.values,before)
        result=cache.clear_cache(r,apply=True)
        self.assertEqual(result['derived_objects'],{'DataModel':1})
        self.assertEqual(r.values,{k:v for k,v in before.items() if k!=b'model'})
        self.assertEqual(cache.clear_cache(r,apply=True)['derived_objects'],{})
    def test_changed_entry_blocks_cleanup(self):
        r=RedisFake();r.changed=True
        with self.assertRaises(RuntimeError):cache.clear_cache(r,apply=True)
        self.assertIn(b'model',r.values)
    def test_unknown_invalid_or_nested_types_are_preserved(self):
        for value in [None,b'\xff',b'not json',b'[]',b'{"__class__":[]}',b'{"__class__":"Token"}']:
            self.assertIsNone(cache.derived_class(value))
