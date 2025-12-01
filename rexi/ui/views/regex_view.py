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
from ...data_providers.awk_executor import AwkExecutor, AwkRecord
from ...presentation.formatter import RegexFormatter
from ..widgets.help_modal import HelpModal
from ..widgets.features_widget import FeaturesWidget


# noinspection SpellCheckingInspection
class RexiApp(App[ReturnType]):
    """Main TUI application for regex testing."""
    
    CSS_PATH = "../../rexi.tcss"
    
    BINDINGS = [
        ("f2", "toggle_view", "Toggle View"),
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
        # Panel state
        # 0: Groups (Pattern Breakdown)
        # 1: Help
        # 2: Features
        self.view_mode = 0
        
        # AWK mode state
        self.is_awk_mode = False
        self.awk_executor: Optional[AwkExecutor] = None
        self.awk_records: list[AwkRecord] = []

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()
        with Horizontal(id="input-row"):
            # Left: Vertical container with Input + Buttons
            with Vertical(id="input-controls"):
                yield Input(value=self.pattern, placeholder="Enter regex pattern", id="pattern_input")
                with Horizontal(id="button-row"):
                    yield Button("Toggle View (F2)", id="toggle_view", variant="primary")
            
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
                    yield Static("Pattern Breakdown", id="panel-header")
                yield Static(id="groups")
                yield Static(id="help", markup=True)
                
                # Initialize with current profile features
                # Use the default profile since we haven't rendered yet
                default_profile_id = self.profile_manager.get_default_profile_id()
                default_profile = self.profile_manager.get_profile(default_profile_id)
                current_features = default_profile.enabled_features if default_profile else set()
                
                yield FeaturesWidget(current_features, id="features_widget")
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

    def action_toggle_view(self) -> None:
        """Toggle between groups, help, and features view."""
        self.view_mode = (self.view_mode + 1) % 3
        
        groups_widget = self.query_one("#groups", Static)
        help_widget = self.query_one("#help", Static)
        features_widget = self.query_one("#features_widget", FeaturesWidget)
        header_widget = self.query_one("#panel-header", Static)
        
        # Hide all first
        groups_widget.display = False
        help_widget.display = False
        features_widget.display = False
        
        if self.view_mode == 0:
            # Groups View (or Fields for AWK)
            groups_widget.display = True
            if self.is_awk_mode:
                header_widget.update("AWK Fields")
            else:
                header_widget.update("Pattern Breakdown")
        elif self.view_mode == 1:
            # Help View
            help_widget.display = True
            if self.is_awk_mode:
                header_widget.update("AWK Help")
                help_widget.update(self.get_awk_help_content())
            else:
                header_widget.update("Regex Help")
                help_widget.update(self.get_help_content())
        elif self.view_mode == 2:
            # Features View (only for regex mode)
            if not self.is_awk_mode:
                features_widget.display = True
                header_widget.update("Features Configuration")
            else:
                # For AWK mode, cycle back to fields (no features view)
                self.view_mode = 0
                groups_widget.display = True
                header_widget.update("AWK Fields")

    @on(FeaturesWidget.Changed)
    def on_features_widget_changed(self, message: FeaturesWidget.Changed) -> None:
        """Handle feature changes."""
        if self.regex_provider.current_profile:
            # Update profile
            self.regex_provider.current_profile.enabled_features = message.enabled_features
            # Re-run regex with new features
            self.run_worker(self.update_regex(self.pattern), exclusive=True)
    
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
        
        lines.append("[dim]Press F2 to toggle view[/dim]")
        
        return "\n".join(lines)
    
    async def _switch_to_awk_mode(self, profile: RegexProfile) -> None:
        """Switch the UI to AWK mode."""
        self.is_awk_mode = True
        
        # Initialize AWK executor based on profile
        awk_command_map = {
            "awk_gawk": "gawk",
            "awk_mawk": "mawk",
            "awk_posix": "awk"
        }
        awk_command = awk_command_map.get(profile.id, "gawk")
        self.awk_executor = AwkExecutor(awk_command)
        
        # Check if AWK is available
        if not self.awk_executor.is_available():
            groups_widget = self.query_one("#groups", Static)
            groups_widget.update(
                f"[red]Error: {awk_command} not found.[/red]\n"
                f"Please install AWK to use this mode.\n\n"
                f"On Ubuntu/Debian: sudo apt install {awk_command}\n"
                f"On macOS: AWK is pre-installed"
            )
            return
        
        # Update input placeholder
        input_widget = self.query_one("#pattern_input", Input)
        input_widget.placeholder = "Enter AWK program (e.g., '{print $1}')"
        
        # Update panel header
        header_widget = self.query_one("#panel-header", Static)
        header_widget.update("AWK Fields")
        
        # Switch to groups view (mode 0) to show fields
        self.view_mode = 0
        self.query_one("#groups", Static).display = True
        self.query_one("#help", Static).display = False
        self.query_one("#features_widget", FeaturesWidget).display = False
        
        # Re-run with current pattern if exists
        if self.pattern:
            self.run_worker(self.update_awk(self.pattern), exclusive=True)
        else:
            groups_widget = self.query_one("#groups", Static)
            groups_widget.update(
                "[cyan]AWK Mode Active[/cyan]\n\n"
                "Enter an AWK program above.\n\n"
                "[bold]Examples:[/bold]\n"
                "  {print $1}           - Print first field\n"
                "  /pattern/ {print}    - Print lines matching pattern\n"
                "  {sum += $2} END {print sum}  - Sum second field\n\n"
                "[dim]Press F2 for AWK help[/dim]"
            )
    
    async def _switch_to_regex_mode(self, profile: RegexProfile) -> None:
        """Switch the UI back to Regex mode."""
        self.is_awk_mode = False
        self.awk_executor = None
        self.awk_records = []
        
        # Update input placeholder
        input_widget = self.query_one("#pattern_input", Input)
        input_widget.placeholder = "Enter regex pattern"
        
        # Update panel header
        header_widget = self.query_one("#panel-header", Static)
        header_widget.update("Pattern Breakdown")
        
        # Set profile
        self.regex_provider.set_profile(profile)
        
        # Update FeaturesWidget to match new profile
        features_widget = self.query_one("#features_widget", FeaturesWidget)
        features_widget.update_from_profile(profile)
        
        # Re-run regex with new profile settings
        if self.pattern:
            self.run_worker(self.update_regex(self.pattern), exclusive=True)
        else:
            groups_widget = self.query_one("#groups", Static)
            groups_widget.update("")
    
    async def update_awk(self, awk_program: str):
        """Execute AWK program and update UI."""
        if not self.awk_executor:
            return
        
        # Strip 'awk' command prefix if present, as users might type it out of habit
        # e.g. "awk '{print $1}'" -> "'{print $1}'"
        # If we don't do this, awk interprets "awk" as a pattern (variable) which is false, so no output.
        import re
        clean_program = re.sub(r'^(?:g?awk|mawk)\s+', '', awk_program.strip())
        
        # Strip surrounding quotes if present (simulating shell behavior)
        # e.g. "'{print $1}'" -> "{print $1}"
        if len(clean_program) >= 2:
            if (clean_program.startswith("'") and clean_program.endswith("'")) or \
               (clean_program.startswith('"') and clean_program.endswith('"')):
                clean_program = clean_program[1:-1]
        
        # Run in thread pool to avoid blocking
        output, error = await asyncio.to_thread(
            self.awk_executor.execute,
            clean_program,
            self.input_content
        )
        
        output_widget = self.query_one("#output", Static)
        groups_widget = self.query_one("#groups", Static)
        
        if error:
            # Show error
            from rich.markup import escape
            groups_widget.update(f"[red]AWK Error:[/red]\n{escape(error)}")
            output_widget.update(self._add_line_numbers(self.input_content))
            return
        
        # Show AWK output
        numbered_output = self._add_line_numbers(output if output else "(no output)")
        output_widget.update(numbered_output)
        
        # Get field breakdown
        records, field_error = await asyncio.to_thread(
            self.awk_executor.get_field_breakdown,
            self.input_content
        )
        
        if field_error or not records:
            groups_widget.update("[dim]No field information available[/dim]")
        else:
            # Format field information
            self.awk_records = records
            field_lines = []
            field_lines.append(f"[bold cyan]Total Records: {len(records)}[/bold cyan]\n")
            
            # Show first few records
            for i, record in enumerate(records[:5]):
                field_lines.append(f"[bold]Record {record.number}:[/bold]")
                field_lines.append(f"  [dim]$0:[/dim] {record.full_record}")
                field_lines.append(f"  [dim]NF:[/dim] {record.num_fields}")
                for field in record.fields[:10]:  # Limit fields shown
                    field_lines.append(f"  [cyan]${field.index}:[/cyan] {field.value}")
                field_lines.append("")
            
            if len(records) > 5:
                field_lines.append(f"[dim]... and {len(records) - 5} more records[/dim]")
            
            groups_widget.update("\n".join(field_lines))
    
    def get_awk_help_content(self) -> str:
        """Generate AWK-specific help content."""
        lines = []
        lines.append("[bold cyan]AWK Quick Reference[/bold cyan]\n")
        
        lines.append("[bold]Structure:[/bold]")
        lines.append("[cyan]pattern { action }[/cyan]")
        lines.append("Execute action for lines matching pattern\n")
        
        lines.append("[bold]Patterns:[/bold]")
        lines.append("[cyan]/regex/[/cyan]      Lines matching regex")
        lines.append("[cyan]$1 == \"value\"[/cyan] Field comparison")
        lines.append("[cyan]NR > 5[/cyan]       Line number condition")
        lines.append("[cyan]BEGIN[/cyan]        Before processing")
        lines.append("[cyan]END[/cyan]          After processing\n")
        
        lines.append("[bold]Actions:[/bold]")
        lines.append("[cyan]print[/cyan]        Print entire line ($0)")
        lines.append("[cyan]print $1[/cyan]    Print field 1")
        lines.append("[cyan]print $1, $3[/cyan] Print fields 1 and 3")
        lines.append("[cyan]sum += $2[/cyan]   Accumulate field 2\n")
        
        lines.append("[bold]Built-in Variables:[/bold]")
        lines.append("[cyan]$0[/cyan]           Entire record")
        lines.append("[cyan]$1, $2, ...[/cyan] Fields (columns)")
        lines.append("[cyan]NF[/cyan]           Number of fields")
        lines.append("[cyan]NR[/cyan]           Record number (line number)")
        lines.append("[cyan]FS[/cyan]           Field separator (default: space)")
        lines.append("[cyan]OFS[/cyan]          Output field separator\n")
        
        lines.append("[bold]Examples:[/bold]")
        lines.append("[cyan]{print $1}[/cyan]")
        lines.append("  Print first field of each line")
        lines.append("[cyan]/error/ {print NR, $0}[/cyan]")
        lines.append("  Print line number and line for lines containing 'error'")
        lines.append("[cyan]{sum += $3} END {print sum}[/cyan]")
        lines.append("  Sum third field and print total\n")
        
        lines.append("[dim]Press F2 to return to fields view[/dim]")
        
        return "\n".join(lines)



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
        
        # 4. Calculate visual lines before the match
        match_logical_line_idx = self.input_content[:position].count('\n')
        visual_lines_before = 0
        
        import math
        
        for i in range(match_logical_line_idx):
            line_len = len(lines[i])
            # Calculate how many visual lines this logical line takes
            # max(1, ...) ensures empty lines take 1 visual line
            
            total_chars = line_len + gutter_width
            # Subtract 2 for scrollbar/padding roughly
            container_inner_width = max(1, container_width - 2)
            
            visual_lines = max(1, math.ceil(total_chars / container_inner_width))
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
        if event.button.id == "toggle_view":
            self.action_toggle_view()

    @on(Input.Changed)
    @on(Input.Changed)
    async def on_input_changed(self, message: Input.Changed) -> None:
        """Handle input field changes."""
        # Sanitize input to remove terminal escape sequences (e.g., mouse events)
        import re
        
        clean_value = message.value
        
        # 1. Remove real ANSI escape sequences (CSI codes)
        # Matches ESC [ or \x9b followed by params and a final letter
        clean_value = re.sub(r'(\x1b\[|\x9b)[0-9;<>?]*[a-zA-Z]', '', clean_value)
        
        # 2. Remove literal representations of SGR mouse codes
        # Matches ^[[<digits;digits;digitsM or m
        clean_value = re.sub(r'\^\[\[<[\d;]+[mM]', '', clean_value)
        
        if clean_value != message.value:
            # If we stripped something, update the input widget directly
            message.input.value = clean_value
            # The update will trigger another Changed event, so we return early
            return

        self.pattern = clean_value
        
        # Route to AWK or Regex based on mode
        if self.is_awk_mode:
            self.run_worker(self.update_awk(clean_value), exclusive=True)
        else:
            self.run_worker(self.update_regex(clean_value), exclusive=True)
    
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
                # Check if this is an AWK profile
                if profile.profile_type == "awk":
                    # Switch to AWK mode
                    await self._switch_to_awk_mode(profile)
                else:
                    # Switch to Regex mode
                    await self._switch_to_regex_mode(profile)

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
            
            # Update widgets (only update groups if in groups view)
            if self.view_mode == 0:
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
            if self.view_mode == 0:
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
