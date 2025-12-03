import unittest
from unittest.mock import MagicMock, patch
from rexi.ui.views.regex_view import RexiApp

class TestCopyButton(unittest.TestCase):
    def setUp(self):
        self.app = RexiApp("test content")
        self.app.notify = MagicMock()

    @patch("rexi.ui.views.regex_view.pyperclip")
    def test_copy_pattern_success(self, mock_pyperclip):
        self.app.pattern = "test pattern"
        self.app.action_copy_pattern()
        
        mock_pyperclip.copy.assert_called_with("test pattern")
        self.app.notify.assert_called_with("Pattern copied to clipboard!", severity="information")

    @patch("rexi.ui.views.regex_view.pyperclip")
    def test_copy_pattern_empty(self, mock_pyperclip):
        self.app.pattern = ""
        self.app.action_copy_pattern()
        
        mock_pyperclip.copy.assert_not_called()
        self.app.notify.assert_called_with("Nothing to copy", severity="warning")

    @patch("rexi.ui.views.regex_view.pyperclip", None)
    def test_copy_pattern_no_pyperclip(self):
        self.app.pattern = "test pattern"
        self.app.action_copy_pattern()
        
        self.app.notify.assert_called_with("pyperclip not installed. Cannot copy.", severity="error")

    @patch("rexi.ui.views.regex_view.pyperclip")
    def test_copy_pattern_error(self, mock_pyperclip):
        mock_pyperclip.copy.side_effect = Exception("Clipboard error")
        self.app.pattern = "test pattern"
        self.app.action_copy_pattern()
        
        self.app.notify.assert_called_with("Failed to copy: Clipboard error", severity="error")

if __name__ == "__main__":
    unittest.main()
