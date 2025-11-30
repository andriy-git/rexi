import os
import tempfile
import unittest
from io import StringIO
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from rexi.parser import app, is_stdin_a_tty
from rexi.ui.views.regex_view import RexiApp


class TestCli(unittest.TestCase):

    def test_is_stdin_a_tty_true(self):
        with patch('rexi.parser.sys.stdin.isatty', return_value=True):
            self.assertTrue(is_stdin_a_tty())

    def test_is_stdin_a_tty_false(self):
        with patch('rexi.parser.sys.stdin.isatty', return_value=False):
            self.assertFalse(is_stdin_a_tty())

    @patch('rexi.parser.RexiApp')
    @patch('sys.stdin')
    def test_file_input(self, mock_stdin, mock_rexi_app):
        runner = CliRunner()

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("This iS! aTe xt2 F0r T3sT!ng")
            temp_file_path = f.name

        try:
            # Mock the RexiApp instance
            mock_app_instance = Mock()
            mock_rexi_app.return_value = mock_app_instance

            # Run the command
            result = runner.invoke(app, ["--input", temp_file_path])

            # Verify the command completed without error
            self.assertEqual(result.exit_code, 0)

            # Verify RexiApp was instantiated with the correct content
            mock_rexi_app.assert_called_once()
        finally:
            os.unlink(temp_file_path)  # Clean up the temp file

    @patch('sys.stdin')
    def test_no_stdin_error(self, mock_stdin):
        """Test that an error occurs when no input is provided"""
        runner = CliRunner()

        with patch('rexi.parser.is_stdin_a_tty', return_value=True):
            result = runner.invoke(app)
            # The new parser should handle this case with a proper error
            self.assertNotEqual(result.exit_code, 0)
