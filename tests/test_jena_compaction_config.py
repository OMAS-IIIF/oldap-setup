"""The maintenance policy is explicit and absent from legacy deployments."""
import unittest
from pathlib import Path
import jinja2
from ansible.plugins.filter.core import to_bool

ROOT = Path(__file__).resolve().parents[1]


class CompactionConfigurationTests(unittest.TestCase):
    def render(self, **settings):
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(ROOT / 'templates'), undefined=jinja2.StrictUndefined)
        env.filters['bool'] = to_bool
        values = {key: 'synthetic-test-key' for key in ('oldap_jena_identity_key', 'oldap_jena_service_key', 'oldap_jena_bootstrap_key', 'oldap_jena_fulltext_key')}
        return env.get_template('jena-service.properties.j2').render(**values, **settings)

    def test_legacy_and_disabled_configs_have_no_new_keys(self):
        self.assertNotIn('compactionCheckSeconds', self.render())
        self.assertNotIn('compactionCheckSeconds', self.render(oldap_jena_compaction_enabled=False))

    def test_opt_in_renders_complete_default_policy(self):
        text = self.render(oldap_jena_compaction_enabled=True)
        for value in ('compactionCheckSeconds=900', 'compactionMinSeconds=86400', 'compactionGrowthBytes=536870912', 'compactionGrowthRatio=2.0', 'compactionZone=Europe/Zurich', 'compactionWindowStart=01:00', 'compactionWindowEnd=03:00'):
            self.assertIn(value, text)

    def test_operator_override_preserves_values(self):
        text = self.render(oldap_jena_compaction_enabled=True, oldap_jena_compaction_check_seconds=600, oldap_jena_compaction_min_seconds=7200, oldap_jena_compaction_growth_bytes=1073741824, oldap_jena_compaction_growth_ratio=3.0)
        self.assertIn('compactionCheckSeconds=600', text)
        self.assertIn('compactionMinSeconds=7200', text)
        self.assertIn('compactionGrowthBytes=1073741824', text)
        self.assertIn('compactionGrowthRatio=3.0', text)

    def test_custom_night_window(self):
        text = self.render(oldap_jena_compaction_enabled=True, oldap_jena_compaction_zone='UTC', oldap_jena_compaction_window_start='23:00', oldap_jena_compaction_window_end='02:00')
        for value in ('compactionZone=UTC', 'compactionWindowStart=23:00', 'compactionWindowEnd=02:00'):
            self.assertIn(value, text)
