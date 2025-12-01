"""Widget for toggling regex features."""

from typing import Set

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Checkbox, Label

from ...data_providers.profile_manager import RegexProfile

FEATURE_CATEGORIES = {
    "Anchors & Boundaries": [
        ("anchors", "Start/End (^, $)"),
        ("lookahead", "Lookahead (?=...)"),
        ("lookbehind", "Lookbehind (?<=...)"),
        ("variable_lookbehind", "Variable Lookbehind"),
    ],
    "Groups & Captures": [
        ("groups", "Capturing Groups (...)"),
        ("named_groups", "Named Groups (?P<name>...)"),
        ("non_capturing", "Non-capturing (?:...)"),
        ("backreferences", "Backreferences \\1"),
        ("branch_reset", "Branch Reset (?|...)"),
    ],
    "Quantifiers": [
        ("quantifiers", "Basic (*, +, ?)"),
        ("possessive", "Possessive (*+, ++, ?+)"),
        ("atomic", "Atomic Groups (?>...)"),
    ],
    "Other": [
        ("classes", "Character Classes [...]"),
        ("alternation", "Alternation |"),
        ("escapes", "Escapes \\d, \\w"),
        ("unicode_properties", "Unicode Properties \\p{...}"),
        ("recursion", "Recursion (?R)"),
        ("fuzzy", "Fuzzy Matching"),
    ]
}

class FeaturesWidget(VerticalScroll):
    """Widget for toggling regex features."""

    class Changed(Message):
        """Posted when features change."""
        def __init__(self, enabled_features: Set[str]) -> None:
            self.enabled_features = enabled_features
            super().__init__()

    def __init__(self, current_features: Set[str], id: str | None = None):
        super().__init__(id=id)
        self.current_features = set(current_features)
        self.original_features = set(current_features)  # For cancel
        self.checkboxes: dict[str, Checkbox] = {}

    def compose(self) -> ComposeResult:
        for category, features in FEATURE_CATEGORIES.items():
            with Vertical(classes="feature-category-box"):
                yield Label(category, classes="feature-category-header")
                for feature_id, label in features:
                    is_checked = feature_id in self.current_features
                    checkbox = Checkbox(label, value=is_checked, id=f"feat_{feature_id}")
                    self.checkboxes[feature_id] = checkbox
                    yield checkbox
        
        # Add Save/Cancel buttons
        with Horizontal(classes="feature-buttons"):
            yield Button("Save", id="save_features", variant="primary")
            yield Button("Cancel", id="cancel_features", variant="error")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes (but don't save yet)."""
        # Update current features in memory
        feature_id = event.checkbox.id.replace("feat_", "")
        if event.value:
            self.current_features.add(feature_id)
        else:
            self.current_features.discard(feature_id)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Save/Cancel button presses."""
        if event.button.id == "save_features":
            # Save: update original and notify parent
            self.original_features = set(self.current_features)
            self.post_message(self.Changed(self.current_features))
        elif event.button.id == "cancel_features":
            # Cancel: revert to original
            self.current_features = set(self.original_features)
            # Update all checkboxes to match original
            for feature_id, checkbox in self.checkboxes.items():
                checkbox.value = feature_id in self.original_features
    
    def update_from_profile(self, profile: RegexProfile) -> None:
        """Update checkboxes to match the given profile's features."""
        self.current_features = set(profile.enabled_features)
        self.original_features = set(profile.enabled_features)
        
        # Update all checkboxes
        for feature_id, checkbox in self.checkboxes.items():
            checkbox.value = feature_id in self.current_features
