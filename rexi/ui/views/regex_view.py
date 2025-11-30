"""Main regex view for the TUI application."""

from typing import Optional, cast, Set

from textual import on
from textual.app import App, ComposeResult, ReturnType
from textual.containers import Horizontal, ScrollableContainer
from textual.widgets import Button, Footer, Header, Input, Select, Static

from ...data_providers.regex_provider import RegexProvider
from ...data_providers.profile_manager import ProfileManager, RegexProfile
from ...presentation.formatter import RegexFormatter
from ..widgets.help_modal import HelpModal
from ..widgets.features_modal import FeaturesModal


# noinspection SpellCheckingInspection
class RexiApp(App[ReturnType]):
    """Main TUI application for regex testing."""
    
    CSS_PATH = "../../rexi.tcss"
    
    BINDINGS = [
        ("f1", "show_help", "Help"),
        ("f2", "show_features", "Features"),
        ("escape", "quit", "Quit"),
    ]

    def __init__(
        self,
        input_content: str,
        initial_pattern: Optional[str] = None,
    ):
        """Initialize the Rexi TUI application.
        
        Args:
            input_content: The text content to test regex against
            initial_pattern: Initial regex pattern to display
        """
        super().__init__()
        self.input_content: str = input_content
        self.pattern = initial_pattern
        
        # Initialize providers
        self.profile_manager = ProfileManager()
        self.regex_provider = RegexProvider(input_content)
        self.formatter = RegexFormatter(input_content)
        
        # Set default profile
        default_profile_id = self.profile_manager.get_default_profile_id()
        default_profile = self.profile_manager.get_profile(default_profile_id)
        if default_profile:
            self.regex_provider.set_profile(default_profile)

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()
        with Horizontal(id="inputs"):
            yield Input(value=self.pattern, placeholder="Enter regex pattern", id="pattern_input")
            
            # Profile selector
            profiles = [(p.name, p.id) for p in self.profile_manager.list_profiles()]
            default_id = self.profile_manager.get_default_profile_id()
            yield Select(
                profiles,
                value=default_id,
                id="profile_select",
                allow_blank=False
            )
            
            yield Button("Features", id="features", variant="default")
            yield Button("Help", id="help", variant="primary")
            
        with ScrollableContainer(id="result"):
            with ScrollableContainer(id="output-container"):
                with Header():
                    yield Static("Result")
                yield Static(self.input_content, id="output", markup=False)
            with ScrollableContainer(id="groups-container"):
                with Header():
                    yield Static("Groups")
                yield Static(id="groups")
        yield Footer()

    def action_show_help(self) -> None:
        """Show the help modal."""
        self.push_screen(HelpModal())

    def action_show_features(self) -> None:
        """Show the features modal."""
        if not self.regex_provider.current_profile:
            return
            
        current_features = self.regex_provider.current_profile.enabled_features
        
        def handle_features(features: Optional[Set[str]]) -> None:
            if features is not None:
                # Create a new custom profile with these features
                # For now, we just update the current profile in memory
                # In Phase 4 we will save this properly
                
                # If current profile is a default one, create a copy
                current = self.regex_provider.current_profile
                if current:
                    # Create custom profile
                    new_profile = RegexProfile(
                        id="custom",
                        name="Custom",
                        description="Custom feature set",
                        enabled_features=features,
                        use_regex_module=True # Default to regex module for custom profiles to allow all features
                    )
                    
                    # Register it temporarily
                    self.profile_manager.profiles["custom"] = new_profile
                    
                    # Update selector
                    select = self.query_one("#profile_select", Select)
                    # Update options to include custom if not present
                    profiles = [(p.name, p.id) for p in self.profile_manager.list_profiles()]
                    select.set_options(profiles)
                    select.value = "custom"
                    
        self.push_screen(FeaturesModal(current_features), handle_features)

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "help":
            self.action_show_help()
        elif event.button.id == "features":
            self.action_show_features()

    @on(Input.Changed)
    async def on_input_changed(self, message: Input.Changed) -> None:
        """Handle input field changes."""
        self.pattern = message.value
        self.run_worker(self.update_regex(message.value), exclusive=True)

    @on(Select.Changed)
    async def on_select_changed(self, message: Select.Changed) -> None:
        """Handle profile selection changes."""
        if message.select.id == "profile_select":
            profile_id = cast(str, message.value)
            profile = self.profile_manager.get_profile(profile_id)
            if profile:
                self.regex_provider.set_profile(profile)
                # Re-run regex with new profile settings
                if self.pattern:
                    self.run_worker(self.update_regex(self.pattern), exclusive=True)

    async def update_regex(self, str_pattern: str) -> None:
        """Update the regex output based on current pattern.
        
        Args:
            str_pattern: The regex pattern string to apply
        """
        output_widget = self.query_one("#output", Static)
        groups_widget = self.query_one("#groups", Static)
        output_result = ""
        groups_result = ""
        
        if str_pattern:
            # Always use finditer mode
            groups, error = self.regex_provider.get_matches(
                str_pattern, "finditer"
            )
            
            if error:
                # Show error in groups widget or log it
                # For now, let's show it in the groups widget so user sees it clearly
                groups_result = f"[red]{error}[/red]"
                # Also reset output highlighting if there's an error
                output_result = self.input_content
            elif groups:
                groups_result = self.formatter.create_groups_output(groups)
                output_result = self.formatter.create_highlighted_output(groups)

        output_widget.update(output_result or self.input_content)
        groups_widget.update(groups_result)
