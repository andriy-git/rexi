"""Modal for toggling regex features."""

from typing import Set

from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, Vertical, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Label, Static

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

class FeaturesModal(ModalScreen[Set[str]]):
    """Modal screen for toggling regex features."""

    CSS = """
    FeaturesModal {
        align: center middle;
    }

    #dialog {
        width: 80;
        height: 80%;
        border: thick $accent;
        background: $surface;
    }
    
    #dialog-content {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: auto;
        padding: 0 1;
    }

    .category-box {
        height: auto;
        border: solid $primary;
        padding: 1;
    }

    .category-title {
        text-align: center;
        text-style: bold;
        background: $primary;
        color: $text;
        width: 100%;
        column-span: 2;
    }

    #buttons {
        column-span: 2;
        height: auto;
        align: center bottom;
        padding-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, current_features: Set[str]):
        super().__init__()
        self.current_features = set(current_features)
        self.checkboxes: dict[str, Checkbox] = {}

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="dialog"):
            with Grid(id="dialog-content"):
                yield Label("Regex Features", id="title", classes="category-title")
                
                for category, features in FEATURE_CATEGORIES.items():
                    with Vertical(classes="category-box"):
                        yield Label(category, classes="category-header")
                        for feature_id, label in features:
                            is_checked = feature_id in self.current_features
                            checkbox = Checkbox(label, value=is_checked, id=f"feat_{feature_id}")
                            self.checkboxes[feature_id] = checkbox
                            yield checkbox

                with Horizontal(id="buttons"):
                    yield Button("Apply", variant="primary", id="apply")
                    yield Button("Cancel", variant="error", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply":
            # Collect enabled features
            enabled = {
                fid for fid, cb in self.checkboxes.items() 
                if cb.value
            }
            self.dismiss(enabled)
        elif event.button.id == "cancel":
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)
