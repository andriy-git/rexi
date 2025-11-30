"""Test profile system functionality."""

import unittest
from unittest.mock import Mock, patch
from rexi.data_providers.profile_manager import ProfileManager, RegexProfile
from rexi.data_providers.regex_provider import RegexProvider

class TestProfileManager(unittest.TestCase):
    """Test ProfileManager functionality."""

    def test_load_profiles(self):
        """Test loading default profiles."""
        manager = ProfileManager()
        profiles = manager.list_profiles()
        self.assertTrue(len(profiles) > 0)
        
        pcre = manager.get_profile("pcre_full")
        self.assertIsNotNone(pcre)
        self.assertEqual(pcre.name, "PCRE (Full)")
        self.assertTrue(pcre.use_regex_module)

        grep = manager.get_profile("grep_basic")
        self.assertIsNotNone(grep)
        self.assertFalse(grep.use_regex_module)

class TestRegexProviderValidation(unittest.TestCase):
    """Test RegexProvider validation logic."""

    def setUp(self):
        self.provider = RegexProvider("test content")
        self.manager = ProfileManager()

    def test_pcre_profile_allows_lookahead(self):
        """Test PCRE profile allows lookahead."""
        profile = self.manager.get_profile("pcre_full")
        self.provider.set_profile(profile)
        
        error = self.provider.validate_pattern("(?=test)")
        self.assertIsNone(error)

    def test_grep_profile_blocks_lookahead(self):
        """Test Grep profile blocks lookahead."""
        profile = self.manager.get_profile("grep_basic")
        self.provider.set_profile(profile)
        
        error = self.provider.validate_pattern("(?=test)")
        self.assertIsNotNone(error)
        self.assertIn("Lookahead", error)

    def test_grep_profile_blocks_named_groups(self):
        """Test Grep profile blocks named groups."""
        profile = self.manager.get_profile("grep_basic")
        self.provider.set_profile(profile)
        
        error = self.provider.validate_pattern("(?P<name>test)")
        self.assertIsNotNone(error)
        self.assertIn("Named groups", error)

    def test_python_profile_blocks_recursion(self):
        """Test Python profile blocks recursion."""
        profile = self.manager.get_profile("python_re")
        self.provider.set_profile(profile)
        
        error = self.provider.validate_pattern("(?R)")
        self.assertIsNotNone(error)
        self.assertIn("Recursion", error)

if __name__ == "__main__":
    unittest.main()
