"""Batch configuration preserves provider behavior without legacy transport."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('batches', Path(__file__).parents[1]/'scripts/prepare-production-batches.py')
batches = importlib.util.module_from_spec(spec); spec.loader.exec_module(batches)


class BatchTests(unittest.TestCase):
    def fixture(self):
        env = {key: 'target-'+key for key in batches.CLIENT_ENV}
        env['OLDAP_BACKEND'] = 'jena'
        core = {'services': {'oldap-api': {'environment': env, 'volumes': [{
            'type':'bind', 'source':'/target/policy.json', 'target':'/run/oldap-policy/archive-policy.json', 'read_only':True}]}}}
        source = {'services': {'oldap-harvesters': {
            'command':['--config','a path.toml','--write-oldap'], 'image':'old:mutable',
            'environment':{'OLDAP_TS_PASSWORD':'old-secret','OMP_NUM_THREADS':'2'},
            'networks':{'default':{}},'depends_on':{'graphdb':{}},'mem_limit':5000000000,
            'volumes':[{'type':'bind','source':'/legacy','target':'/run/oldap-writer-client'},
                       {'type':'bind','source':'/srv/storage/oldap-data/oldap-harvesters/secrets','target':'/run/secrets','read_only':True}]}}}
        return source, core

    def test_source_behavior_target_identity_and_no_legacy_coordinator(self):
        source,core=self.fixture(); before=copy.deepcopy(source)
        service=batches.prepare_service(source,core,'sha256:'+'a'*64)
        self.assertEqual(source,before)
        self.assertEqual(service['command'],source['services']['oldap-harvesters']['command'])
        self.assertEqual(service['mem_limit'],5000000000)
        self.assertNotIn('depends_on',service);self.assertNotIn('networks',service)
        self.assertEqual(service['network_mode'],'service:oldap-jena')
        self.assertNotIn('OLDAP_TS_PASSWORD',service['environment'])
        self.assertEqual(service['environment']['OMP_NUM_THREADS'],'2')
        self.assertEqual(service['profiles'],['harvesters'])
        self.assertEqual(service['volumes'][-1]['source'],'/target/policy.json')
        self.assertNotIn('/legacy',[m['source'] for m in service['volumes']])

    def test_fail_closed_on_unreviewed_or_mutable_inputs(self):
        for change in ('image','backend','environment','mount','policy','command'):
            with self.subTest(change=change):
                source,core=self.fixture();image='sha256:'+'a'*64
                s=source['services']['oldap-harvesters']
                if change=='image':image='image:latest'
                if change=='backend':core['services']['oldap-api']['environment']['OLDAP_BACKEND']='graphdb'
                if change=='environment':s['environment']['NEW_SECRET']='secret'
                if change=='mount':s['volumes'][-1]['source']='/srv/storage/oldap-data/oldap-harvesters/../../other'
                if change=='policy':core['services']['oldap-api']['volumes'][0]['read_only']=False
                if change=='command':s['command']='shell words'
                with self.assertRaises(ValueError):batches.prepare_service(source,core,image)
