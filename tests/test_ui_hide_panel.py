import unittest
from unittest.mock import MagicMock
from rexi.ui.views.regex_view import RexiApp
from textual.widgets import Static
from textual.containers import ScrollableContainer

class TestHideSidePanel(unittest.TestCase):
    def setUp(self):
        self.app = RexiApp("test content")
        # Mock UI components since we're not running the full app
        self.app.query_one = MagicMock()
        
        # Mock widgets
        self.groups_widget = MagicMock(spec=Static)
        self.help_widget = MagicMock(spec=Static)
        self.features_widget = MagicMock()
        self.header_widget = MagicMock(spec=Static)
        self.output_container = MagicMock(spec=ScrollableContainer)
        self.groups_container = MagicMock(spec=ScrollableContainer)
        
        def query_side_effect(selector, type=None):
            if selector == "#groups": return self.groups_widget
            if selector == "#help": return self.help_widget
            if selector == "#features_widget": return self.features_widget
            if selector == "#panel-header": return self.header_widget
            if selector == "#output-container": return self.output_container
            if selector == "#groups-container": return self.groups_container
            return MagicMock()
            
        self.app.query_one.side_effect = query_side_effect

    def test_toggle_view_cycle_regex_mode(self):
        # Initial state: 0 (Groups)
        self.app.view_mode = 0
        self.app.is_awk_mode = False
        self.app.is_jq_mode = False
        
        # Toggle to 1 (Help)
        self.app.action_toggle_view()
        self.assertEqual(self.app.view_mode, 1)
        self.assertTrue(self.help_widget.display)
        self.assertFalse(self.output_container.add_class.called)
        
        # Toggle to 2 (Features)
        self.app.action_toggle_view()
        self.assertEqual(self.app.view_mode, 2)
        self.assertTrue(self.features_widget.display)
        
        # Toggle to 3 (Hidden)
        self.app.action_toggle_view()
        self.assertEqual(self.app.view_mode, 3)
        self.assertFalse(self.groups_container.display)
        self.output_container.add_class.assert_called_with("full-width")
        
        # Toggle back to 0 (Groups)
        self.app.action_toggle_view()
        self.assertEqual(self.app.view_mode, 0)
        self.assertTrue(self.groups_widget.display)
        self.output_container.remove_class.assert_called_with("full-width")

    def test_toggle_view_cycle_awk_mode(self):
        # Initial state: 0 (Fields)
        self.app.view_mode = 0
        self.app.is_awk_mode = True
        self.app.is_jq_mode = False
        
        # Toggle to 1 (Help)
        self.app.action_toggle_view()
        self.assertEqual(self.app.view_mode, 1)
        
        # Toggle to 3 (Hidden) - Should skip 2 (Features)
        self.app.action_toggle_view()
        self.assertEqual(self.app.view_mode, 3)
        self.assertFalse(self.groups_container.display)
        self.output_container.add_class.assert_called_with("full-width")
        
        # Toggle back to 0
        self.app.action_toggle_view()
        self.assertEqual(self.app.view_mode, 0)

if __name__ == "__main__":
    unittest.main()
