"""Main regex view for the TUI application."""

from typing import Optional, cast, Set
import asyncio

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
        ("n", "next_match", "Next Match"),
        ("N,shift+n", "prev_match", "Prev Match"),
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
        
        # Match navigation tracking
        self.match_positions: list[int] = []
        self.current_match_index: int = -1
        self._last_matches: list = []

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
            with ScrollableContainer(id="output-container", can_focus=True):
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
    
    def action_next_match(self) -> None:
        """Navigate to the next match."""
        if not self.match_positions:
            return
        
        self.current_match_index = (self.current_match_index + 1) % len(self.match_positions)
        self._scroll_to_match(self.current_match_index)
        self._refresh_highlighting()
    
    def action_prev_match(self) -> None:
        """Navigate to the previous match."""
        if not self.match_positions:
            return
        
        self.current_match_index = (self.current_match_index - 1) % len(self.match_positions)
        self._scroll_to_match(self.current_match_index)
        self._refresh_highlighting()
    
    def _scroll_to_match(self, match_index: int) -> None:
        """Scroll to the specified match."""
        if match_index < 0 or match_index >= len(self.match_positions):
            return
        
        position = self.match_positions[match_index]
        
        # Calculate line and column for the position
        lines_before = self.input_content[:position].count('\n')
        line_start = self.input_content.rfind('\n', 0, position) + 1
        column = position - line_start
        
        # Scroll the container to make this position visible
        container = self.query_one("#output-container", ScrollableContainer)
        # Use scroll_to with actual line/column
        container.scroll_to(x=column, y=lines_before, animate=True)
    
    def _refresh_highlighting(self) -> None:
        """Refresh the output highlighting with current match emphasized."""
        if not hasattr(self, '_last_matches'):
            return
        
        output_widget = self.query_one("#output", Static)
        output_result = self.formatter.create_highlighted_output(
            self._last_matches, 
            self.current_match_index
        )
        output_widget.update(output_result)

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

    def _get_regex_result(self, str_pattern: str):
        """Run regex matching and formatting synchronously."""
        if not str_pattern:
            return None, None, None, [], None
            
        # Always use finditer mode
        groups, error = self.regex_provider.get_matches(
            str_pattern, "finditer"
        )
        
        if error:
            return None, error, None, [], None
        
        if not groups:
            return None, None, None, [], None
            
        groups_result = self.formatter.create_groups_output(groups)
        output_result = self.formatter.create_highlighted_output(groups, 0)  # Start with first match highlighted
        match_positions = self.formatter.get_match_positions(groups)
        
        return groups_result, None, output_result, match_positions, groups

    async def update_regex(self, str_pattern: str) -> None:
        """Update the regex output based on current pattern.
        
        Args:
            str_pattern: The regex pattern string to apply
        """
        output_widget = self.query_one("#output", Static)
        groups_widget = self.query_one("#groups", Static)
        
        if not str_pattern:
            output_widget.update(self.input_content)
            groups_widget.update("[dim]Enter a regex pattern to see matches[/dim]")
            self.match_positions = []
            self.current_match_index = -1
            return

        # Run heavy lifting in a thread to avoid blocking the UI
        groups_result, error, output_result, match_positions, groups = await asyncio.to_thread(
            self._get_regex_result, str_pattern
        )
        
        if error:
            # Show error in groups widget or log it
            groups_widget.update(f"[red]{error}[/red]")
            # Also reset output highlighting if there's an error
            output_widget.update(self.input_content)
            self.match_positions = []
            self.current_match_index = -1
            self._last_matches = []
        elif output_result is not None:
            # Update match tracking
            self.match_positions = match_positions
            self.current_match_index = 0 if match_positions else -1
            self._last_matches = groups if groups else []
            
            # Update widgets
            groups_widget.update(groups_result if groups_result else "[dim]No capture groups in pattern[/dim]")
            groups_widget.refresh()  # Force redraw
            output_widget.update(output_result)
            
            # Autoscroll to first match
            if match_positions:
                self._scroll_to_match(0)
        else:
            # No matches found
            groups_widget.update("[dim]No matches found[/dim]")
            output_widget.update(self.input_content)
            self.match_positions = []
            self.current_match_index = -1
            self._last_matches = []
