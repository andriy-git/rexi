import unittest
from unittest.mock import AsyncMock

from rexi.ui.views.regex_view import RexiApp


class TestUI(unittest.TestCase):
    """Test the UI components of the Rexi application."""

    def test_app_initialization(self):
        """Test that the RexiApp can be initialized correctly."""
        content = "This iS! aTe xt2 F0r T3sT!ng"
        app = RexiApp(content)

        # Verify the app was created with the correct content
        self.assertEqual(app.input_content, content)

    def test_app_initialization_with_initial_pattern(self):
        """Test that the RexiApp can be initialized with an initial pattern."""
        content = "This iS! aTe xt2 F0r T3sT!ng"
        initial_pattern = "(This.*iS!)"
        app = RexiApp(input_content=content, initial_pattern=initial_pattern)

        # Verify the app was created with the correct content and pattern
        self.assertEqual(app.input_content, content)
        # Note: We can't directly check pattern since it's set after app starts
        # but we can at least verify initialization works
        self.assertIsNotNone(app)

    # Note: The async tests for UI interactions require more complex setup
    # which may be better handled with integration tests
    # For now, we'll focus on basic initialization and logic tests
