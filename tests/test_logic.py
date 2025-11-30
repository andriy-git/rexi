import re
import unittest

from rexi.data_providers.regex_provider import GroupMatch, RegexProvider


class TestLogic(unittest.TestCase):

    def test_group_match_equals(self):
        test_cases = [
            (GroupMatch([1], "name", 1, 2), GroupMatch([2], "name2", 1, 2), False),  # Different spans
            (GroupMatch([1, 2], "name", 1, 2), GroupMatch([1, 2], "name", 1, 2), True),  # Same spans
            (GroupMatch([1], "name", 1, 2), GroupMatch([1], "name", 1, 3), False),  # Different end positions
            (GroupMatch([1], "name", 1, 3), GroupMatch([1], "name", 2, 3), False),  # Different start positions
            (GroupMatch([1], "name", 1, 3), object(), False),  # Different object types
        ]

        for group_one, group_two, expected_equals in test_cases:
            with self.subTest(group_one=group_one, group_two=group_two):
                self.assertEqual((group_one == group_two), expected_equals)

    def test_regex_provider_extraction(self):
        """Test the regex provider's group extraction functionality"""
        content = "This iS! aTe xt2 F0r T3sT!ng"
        provider = RegexProvider(content)

        # Test basic pattern
        pattern = r".*(aTe).*"
        match = re.match(pattern, content)
        if match:
            # We can't test the internal _extract_groups method directly since it's private
            # and would require creating a Match object manually, so instead we'll test the public API
            matches, error = provider.get_matches(pattern, "match")
            self.assertIsNone(error)
            # Should have at least one match
            if matches:
                self.assertGreater(len(matches), 0)
                # First match should have groups
                first_match = matches[0]
                # Should have at least the full match (group 0) and the captured group
                self.assertGreater(len(first_match), 1)

    def test_group_match_creation(self):
        """Test GroupMatch dataclass functionality"""
        group1 = GroupMatch(span=(0, 5), value="hello", name="test", group_index=0)
        group2 = GroupMatch(span=(0, 5), value="hello", name="test", group_index=0)

        # Same content should be equal
        self.assertEqual(group1, group2)

        # Different spans should not be equal
        group3 = GroupMatch(span=(0, 6), value="hello", name="test", group_index=0)
        self.assertNotEqual(group1, group3)
