"""Regex interactive TUI application."""

import asyncio
import sys
from typing import Optional, cast, Set

from textual import on
from textual.app import App, ComposeResult, ReturnType
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static
from rich.text import Text

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
        ("f1", "toggle_help", "Toggle Help"),
        ("f2", "show_features", "Features"),
        ("n", "next_match", "Next Match"),
        ("N", "prev_match", "Prev Match"),
        ("i", "focus_input", "Input"),
        ("g", "focus_groups", "Groups"),
        ("enter", "focus_results", "Results"),
        ("j", "scroll_down", "Scroll Down"),
        ("k", "scroll_up", "Scroll Up"),
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
        
        # Panel state
        self.showing_help = False

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()
        with Horizontal(id="input-row"):
            # Left: Vertical container with Input + Buttons
            with Vertical(id="input-controls"):
                yield Input(value=self.pattern, placeholder="Enter regex pattern", id="pattern_input")
                with Horizontal(id="button-row"):
                    yield Button("Features", id="features", variant="default")
                    yield Button("Help", id="help", variant="primary")
            
            # Right: Profile selector
            profiles = [(p.name, p.id) for p in self.profile_manager.list_profiles()]
            default_id = self.profile_manager.get_default_profile_id()
            yield Select(
                profiles,
                value=default_id,
                id="profile_select",
                allow_blank=False
            )
            
        with ScrollableContainer(id="result"):
            with ScrollableContainer(id="output-container", can_focus=True):
                with Header():
                    yield Static("Result")
                # Add line numbers to the content
                numbered_content = self._add_line_numbers(self.input_content)
                yield Static(numbered_content, id="output", markup=True)
            with ScrollableContainer(id="groups-container", can_focus=True):
                with Header():
                    yield Static("Pattern Breakdown (F1 for Help)", id="panel-header")
                yield Static(id="groups")
                yield Static(id="help", markup=True)
        yield Footer()
    
    def _add_line_numbers(self, content: str) -> str:
        """Add line numbers to content."""
        lines = content.split('\n')
        max_line_num = len(lines)
        width = len(str(max_line_num))
        
        numbered_lines = []
        for i, line in enumerate(lines, 1):
            # Escape any markup in the line
            line_escaped = line.replace('[', '\\[').replace(']', '\\]')
            numbered_lines.append(f"[dim]{i:>{width}}[/dim] {line_escaped}")
        
        return '\n'.join(numbered_lines)

    def action_toggle_help(self) -> None:
        """Toggle between groups and help view."""
        self.showing_help = not self.showing_help
        
        groups_widget = self.query_one("#groups", Static)
        help_widget = self.query_one("#help", Static)
        header_widget = self.query_one("#panel-header", Static)
        
        if self.showing_help:
            # Show help, hide groups
            groups_widget.display = False
            help_widget.display = True
            header_widget.update("Help (F1 for Pattern)")
            help_widget.update(self.get_help_content())
        else:
            # Show groups, hide help
            groups_widget.display = True
            help_widget.display = False
            header_widget.update("Pattern Breakdown (F1 for Help)")
    
    def get_help_content(self) -> str:
        """Generate help content based on current profile."""
        if not self.regex_provider.current_profile:
            return "[dim]No profile selected[/dim]"
        
        profile = self.regex_provider.current_profile
        features = profile.enabled_features
        
        lines = []
        lines.append(f"[bold cyan]{profile.name}[/bold cyan]")
        lines.append(f"[dim]{profile.description}[/dim]\n")
        
        lines.append("[bold]Basic Patterns:[/bold]")
        lines.append("[cyan].[/cyan]         Any character (except newline)")
        lines.append("[cyan]\\d[/cyan]        Digit (0-9)")
        lines.append("[cyan]\\D[/cyan]        Not a digit")
        lines.append("[cyan]\\w[/cyan]        Word character (a-z, A-Z, 0-9, _)")
        lines.append("[cyan]\\W[/cyan]        Not a word character")
        lines.append("[cyan]\\s[/cyan]        Whitespace")
        lines.append("[cyan]\\S[/cyan]        Not whitespace")
        
        if profile.use_regex_module:
            lines.append("[cyan]\\h[/cyan]        Horizontal whitespace")
            lines.append("[cyan]\\H[/cyan]        Not horizontal whitespace")
            lines.append("[cyan]\\v[/cyan]        Vertical whitespace")
            lines.append("[cyan]\\V[/cyan]        Not vertical whitespace")
            lines.append("[cyan]\\R[/cyan]        Any linebreak")
        
        lines.append("[cyan][abc][/cyan]     Any of a, b, or c")
        lines.append("[cyan][a-z][/cyan]     Any lowercase letter")
        lines.append("[cyan][^abc][/cyan]    Not a, b, or c\n")
        
        # POSIX character classes (available in regex module)
        if profile.use_regex_module:
            lines.append("[bold]POSIX Character Classes:[/bold]")
            lines.append("[cyan][[:digit:]][/cyan]  Digits (0-9)")
            lines.append("[cyan][[:alpha:]][/cyan]  Alphabetic characters")
            lines.append("[cyan][[:alnum:]][/cyan]  Alphanumeric characters")
            lines.append("[cyan][[:lower:]][/cyan]  Lowercase letters")
            lines.append("[cyan][[:upper:]][/cyan]  Uppercase letters")
            lines.append("[cyan][[:space:]][/cyan]  Whitespace characters")
            lines.append("[cyan][[:punct:]][/cyan]  Punctuation characters")
            lines.append("[cyan][[:xdigit:]][/cyan] Hexadecimal digits\n")
        
        if "quantifiers" in features:
            lines.append("[bold]Quantifiers:[/bold]")
            lines.append("[cyan]*[/cyan]         0 or more")
            lines.append("[cyan]+[/cyan]         1 or more")
            lines.append("[cyan]?[/cyan]         0 or 1")
            lines.append("[cyan]{n}[/cyan]       Exactly n times")
            lines.append("[cyan]{n,}[/cyan]      n or more times")
            lines.append("[cyan]{n,m}[/cyan]     Between n and m times\n")
        
        if "anchors" in features:
            lines.append("[bold]Anchors:[/bold]")
            lines.append("[cyan]^[/cyan]         Start of line")
            lines.append("[cyan]$[/cyan]         End of line")
            lines.append("[cyan]\\b[/cyan]        Word boundary\n")
        
        if "groups" in features:
            lines.append("[bold]Groups:[/bold]")
            lines.append("[cyan](abc)[/cyan]     Capture group")
            if "named_groups" in features:
                lines.append("[cyan](?P<name>abc)[/cyan] Named capture group")
            if "non_capturing" in features:
                lines.append("[cyan](?:abc)[/cyan] Non-capturing group\n")
        
        if "alternation" in features:
            lines.append("[bold]Alternation:[/bold]")
            lines.append("[cyan]a|b[/cyan]      Match a or b\n")
        
        if "lookahead" in features:
            lines.append("[bold]Lookahead:[/bold]")
            lines.append("[cyan](?=abc)[/cyan]  Positive lookahead")
            lines.append("[cyan](?!abc)[/cyan]  Negative lookahead\n")
        
        if "lookbehind" in features:
            lines.append("[bold]Lookbehind:[/bold]")
            lines.append("[cyan](?<=abc)[/cyan] Positive lookbehind")
            lines.append("[cyan](?<!abc)[/cyan] Negative lookbehind\n")
        
        if "backreferences" in features:
            lines.append("[bold]Backreferences:[/bold]")
            lines.append("[cyan]\\1[/cyan]        Reference to group 1\n")
        
        lines.append("[dim]Press F1 to return to Groups view[/dim]")
        
        return "\n".join(lines)

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
    
    def action_focus_results(self) -> None:
        """Switch focus to the results container."""
        container = self.query_one("#output-container", ScrollableContainer)
        container.focus()
    
    def action_focus_input(self) -> None:
        """Switch focus back to the input field."""
        input_widget = self.query_one("#pattern_input", Input)
        input_widget.focus()
    
    def action_focus_groups(self) -> None:
        """Switch focus to the groups/help container."""
        container = self.query_one("#groups-container", ScrollableContainer)
        container.focus()
    
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
    
    def action_scroll_down(self) -> None:
        """Scroll down in the active container."""
        if self.focused.id == "groups-container":
            self.query_one("#groups-container", ScrollableContainer).scroll_down()
        else:
            self.query_one("#output-container", ScrollableContainer).scroll_down()

    def action_scroll_up(self) -> None:
        """Scroll up in the active container."""
        if self.focused.id == "groups-container":
            self.query_one("#groups-container", ScrollableContainer).scroll_up()
        else:
            self.query_one("#output-container", ScrollableContainer).scroll_up()

    def _scroll_to_match(self, match_index: int) -> None:
        """Scroll to the specified match, keeping it centered in the viewport."""
        if match_index < 0 or match_index >= len(self.match_positions):
            return
        
        position = self.match_positions[match_index]
        container = self.query_one("#output-container", ScrollableContainer)
        
        # Calculate visual line for the position (accounting for wrapping)
        # 1. Get container width
        container_width = container.size.width
        if container_width <= 0:
            # Fallback if width not available yet
            container_width = 80
            
        # 2. Calculate line number width (gutter)
        lines = self.input_content.split('\n')
        max_line_num = len(lines)
        gutter_width = len(str(max_line_num)) + 1  # +1 for space
        
        # 3. Calculate available width for text
        # Subtract gutter and scrollbar (approx 2 chars)
        available_width = max(10, container_width - gutter_width - 2)
        
        # 4. Calculate visual lines before the match
        match_logical_line_idx = self.input_content[:position].count('\n')
        visual_lines_before = 0
        
        for i in range(match_logical_line_idx):
            line_len = len(lines[i])
            # Calculate how many visual lines this logical line takes
            # max(1, ...) ensures empty lines take 1 visual line
            import math
            visual_lines = max(1, math.ceil(line_len / available_width))
            visual_lines_before += visual_lines
            
        # Add offset within the current line if needed (for very long lines)
        # For simplicity, we just scroll to the start of the logical line's visual block
        
        # 5. Calculate target scroll position
        container_height = container.size.height
        target_y = max(0, visual_lines_before - (container_height // 2))
        
        container.scroll_to(y=target_y, animate=False)
    
    def _refresh_highlighting(self) -> None:
        """Refresh the output highlighting with current match emphasized."""
        if not hasattr(self, '_last_matches'):
            return
        
        output_widget = self.query_one("#output", Static)
        output_result = self.formatter.create_highlighted_output(
            self._last_matches, 
            self.current_match_index
        )
        
        # Add line numbers to the highlighted output
        numbered_output = self._add_line_numbers_with_highlighting(output_result)
        output_widget.update(numbered_output)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "help":
            self.action_toggle_help()
        elif event.button.id == "features":
            self.action_show_features()

    @on(Input.Changed)
    async def on_input_changed(self, message: Input.Changed) -> None:
        """Handle input field changes."""
        self.pattern = message.value
        self.run_worker(self.update_regex(message.value), exclusive=True)
    
    @on(Input.Submitted)
    async def on_input_submitted(self, message: Input.Submitted) -> None:
        """Handle Enter key in input field."""
        self.action_focus_results()

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
            numbered_content = self._add_line_numbers(self.input_content)
            output_widget.update(numbered_content)
            groups_widget.update("[dim]Enter a regex pattern to see matches[/dim]")
            self.match_positions = []
            self.current_match_index = -1
            return

        # Run heavy lifting in a thread to avoid blocking the UI
        groups_result, error, output_result, match_positions, groups = await asyncio.to_thread(
            self._get_regex_result, str_pattern
        )
        
        if error:
            # Try to extract position from error message
            # Typical error: "unknown property at position 19" or "missing ) at position 5"
            import re
            pos_match = re.search(r"at position (\d+)", str(error))
            
            error_msg = f"[bold red]Regex Error:[/bold red] {error}"
            
            if pos_match:
                try:
                    pos = int(pos_match.group(1))
                    # Create a visual pointer
                    # Limit pattern display length if it's too long
                    start = max(0, pos - 20)
                    end = min(len(str_pattern), pos + 20)
                    
                    prefix = "..." if start > 0 else ""
                    suffix = "..." if end < len(str_pattern) else ""
                    
                    snippet = str_pattern[start:end]
                    pointer_pos = pos - start
                    
                    # Build the visual representation
                    # Pattern:  ((P|p)lug|[[
                    # Pointer:             ^
                    
                    pointer_line = " " * (pointer_pos + len(prefix)) + "[bold red]^[/bold red]"
                    pattern_line = f"{prefix}[cyan]{snippet}[/cyan]{suffix}"
                    
                    error_msg += f"\n\n[dim]Error location:[/dim]\n{pattern_line}\n{pointer_line}"
                except (ValueError, IndexError):
                    pass
            
            groups_widget.update(error_msg)
            
            # Also reset output highlighting if there's an error
            numbered_content = self._add_line_numbers(self.input_content)
            output_widget.update(numbered_content)
            self.match_positions = []
            self.current_match_index = -1
            self._last_matches = []
        elif output_result is not None:
            # Update match tracking
            self.match_positions = match_positions
            self.current_match_index = 0 if match_positions else -1
            self._last_matches = groups if groups else []
            
            # Update widgets (only update groups if not showing help)
            if not self.showing_help:
                groups_widget.update(groups_result if groups_result else "[dim]No capture groups in pattern[/dim]")
                groups_widget.refresh()  # Force redraw
            
            # Add line numbers and update output
            numbered_output = self._add_line_numbers_with_highlighting(output_result)
            output_widget.update(numbered_output)
            
            # Autoscroll to first match
            if match_positions:
                self._scroll_to_match(0)
        else:
            # No matches found
            if not self.showing_help:
                groups_widget.update("[dim]No matches found[/dim]")
            numbered_content = self._add_line_numbers(self.input_content)
            output_widget.update(numbered_content)
            self.match_positions = []
            self.current_match_index = -1
            self._last_matches = []
    
    def _add_line_numbers_with_highlighting(self, highlighted_text: Text) -> Text:
        """Add line numbers to already-highlighted Rich Text object."""
        from rich.text import Text as RichText
        
        # Split the Rich Text object by lines (this preserves styling)
        lines_text = highlighted_text.split('\n')
        
        max_line_num = len(lines_text)
        width = len(str(max_line_num))
        
        # Create a new Text object for the result
        result = RichText()
        
        for i, line_text in enumerate(lines_text, 1):
            # Add line number with dim styling
            line_num = RichText(f"{i:>{width}} ", style="dim")
            result.append(line_num)
            result.append(line_text)
            
            # Add newline between lines (but not after the last line)
            if i < max_line_num:
                result.append("\n")
        
        return result
