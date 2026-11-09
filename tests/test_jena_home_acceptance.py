"""Protect the content comparison used to accept a real backend cutover."""
import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "home_acceptance", Path(__file__).parents[1] / "scripts/check-jena-home.py"
)
acceptance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acceptance)
concurrent_spec = importlib.util.spec_from_file_location(
    "concurrent_acceptance", Path(__file__).parents[1] / "scripts/check-jena-concurrency.py"
)
concurrent_acceptance = importlib.util.module_from_spec(concurrent_spec)
concurrent_spec.loader.exec_module(concurrent_acceptance)


class ContentComparisonTests(unittest.TestCase):
    def test_list_iri_equivalence_does_not_hide_changed_resources_or_text(self):
        normalize = concurrent_acceptance.normalized
        short = {'fasnacht:carnivalPractice': ['L-CarnivalPracticeTaxonomy:Music']}
        full = {'fasnacht:carnivalPractice': ['http://fasnacht.digital/ns/CarnivalPracticeTaxonomy#Music']}
        self.assertEqual(normalize(short), normalize(full))
        self.assertNotEqual(normalize(short), normalize({
            'fasnacht:carnivalPractice': ['L-CarnivalPracticeTaxonomy:Changed']}))
        text = {'schema:description': ['L-CarnivalPracticeTaxonomy:Music']}
        self.assertEqual(normalize(text), text)

    def test_order_is_ignored_but_changed_content_is_detected(self):
        """RDF result ordering is irrelevant; losing scalar values is not."""
        source = [{"title": "Laterne", "published": True, "count": 3},
                  {"title": "Stamm", "published": False, "count": None}]
        self.assertEqual(acceptance.normalized(source),
                         acceptance.normalized(list(reversed(source))))
        for field, value in (("title", "Changed"), ("published", False), ("count", 4)):
            target = [dict(row) for row in source]
            target[0][field] = value
            with self.subTest(field=field):
                self.assertNotEqual(acceptance.normalized(source),
                                    acceptance.normalized(target))


if __name__ == "__main__":
    unittest.main()
