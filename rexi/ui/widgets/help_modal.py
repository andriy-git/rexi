"""Help modal widget."""

from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Markdown

from ...utils.regex_help import REGEX_HELP


class HelpModal(ModalScreen):
    """Modal screen for displaying regex help."""

    CSS = """
    HelpModal {
        align: center middle;
    }

    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 11;
        border: thick $background 80%;
        background: $surface;
    }

    #help-content {
        height: 1fr;
    }
    
    .help-category {
        text-style: bold;
        color: $primary;
        margin-top: 1;
    }
    
    .help-item {
        margin-left: 2;
    }
    """

    def compose(self):
        with Container(id="dialog"):
            with VerticalScroll(id="help-content"):
                yield Label("Regex Help", id="title")
                
                for category, items in REGEX_HELP.items():
                    yield Label(category, classes="help-category")
                    for pattern, description in items.items():
                        yield Label(f"{pattern:<15} {description}", classes="help-item")
                        
            yield Button("Close", id="exitHelp", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "exitHelp":
            self.dismiss()
