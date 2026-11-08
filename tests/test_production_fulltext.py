"""A source connector must never silently disappear or change its search paths."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('coverage', Path(__file__).resolve().parents[1]/'scripts/check-production-fulltext.py')
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)


class FulltextCoverageTests(unittest.TestCase):
    def inputs(self):
        projects = [{'name':'a','namespace':'urn:a:'}, {'name':'b','namespace':'urn:b:'}]
        connectors = {'a':{'fields':[{'fieldName':'title','propertyChain':['urn:name'], 'indexed':True, 'analyzed':True}]}}
        plans = {'a':{'project':'a','graph':'urn:a:data','fields':{'title':['urn:name']}}}
        return projects, connectors, plans

    def test_unindexed_projects_remain_explicit(self):
        result = coverage.audit(*self.inputs())
        self.assertEqual(result['projects'][1]['status'], 'no_source_index')
        self.assertFalse(result['projects'][0]['semantic_parity_claimed'])

    def test_unknown_connector_or_missing_plan_is_rejected(self):
        for failure in ['unknown', 'missing']:
            p,c,f=self.inputs()
            if failure == 'unknown': c['other']=c['a']
            else: f.clear()
            with self.assertRaises(ValueError): coverage.audit(p,c,f)

    def test_path_drift_or_duplicate_field_is_rejected(self):
        for failure in ['path','duplicate','dynamic']:
            p,c,f=self.inputs()
            if failure == 'path': f['a']['fields']['title']=['urn:wrong']
            elif failure == 'duplicate': c['a']['fields'] *= 2
            else: c['a']['detectFields']=True
            with self.assertRaises(ValueError): coverage.audit(p,c,f)
