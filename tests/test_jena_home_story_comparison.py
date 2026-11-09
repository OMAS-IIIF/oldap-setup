"""Acceptance treats known keyword IRIs equally, but preserves all content."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('home_check', Path(__file__).parents[1] / 'scripts/check-jena-home.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StoryComparisonTests(unittest.TestCase):
    def test_keyword_alias_equal_and_input_unchanged(self):
        short = [{'fasnacht:storyKeywords': ['L-StoryKeywords:Example']}]
        full = [{'fasnacht:storyKeywords': ['http://fasnacht.digital/ns/StoryKeywords#Example']}]
        self.assertEqual(module.normalized_stories(short), module.normalized_stories(full))
        self.assertEqual(short[0]['fasnacht:storyKeywords'], ['L-StoryKeywords:Example'])

    def test_literal_content_and_other_fields_remain_exact(self):
        short = [{'fasnacht:storyTitle': 'L-StoryKeywords:Example', 'other': 'L-StoryKeywords:Example'}]
        full = [{'fasnacht:storyTitle': 'http://fasnacht.digital/ns/StoryKeywords#Example', 'other': 'L-StoryKeywords:Example'}]
        self.assertNotEqual(module.normalized_stories(short), module.normalized_stories(full))

    def test_different_keyword_is_still_a_difference(self):
        a = [{'fasnacht:storyKeywords': ['L-StoryKeywords:A']}]
        b = [{'fasnacht:storyKeywords': ['http://fasnacht.digital/ns/StoryKeywords#B']}]
        self.assertNotEqual(module.normalized_stories(a), module.normalized_stories(b))
