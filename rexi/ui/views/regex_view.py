"""Regex interactive TUI application."""

import asyncio
import re
import sys
from enum import IntEnum
from typing import Optional, cast, Set, Union

from textual import on
from textual.app import App, ComposeResult, ReturnType
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static
from rich.text import Text
from rich.markup import escape

from ...data_providers.regex_provider import RegexProvider
from ...data_providers.profile_manager import ProfileManager, RegexProfile
from ...data_providers.awk_executor import AwkExecutor, AwkRecord
from ...data_providers.jq_executor import JqExecutor
from ...presentation.formatter import RegexFormatter
from ..widgets.help_modal import HelpModal
from ..widgets.features_widget import FeaturesWidget

try:
    import pyperclip
except ImportError:
    pyperclip = None


# noinspection SpellCheckingInspection
class ViewMode(IntEnum):
    """Enumeration for view modes."""
    GROUPS = 0
    HELP = 1
    FEATURES = 2
    HIDDEN = 3


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
        ("ctrl+shift+c", "copy_pattern", "Copy Pattern"),
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
        # 0: Groups (Pattern Breakdown)
        # 1: Help
        # 2: Features
        # Panel state
        self.view_mode = ViewMode.GROUPS
        
        # AWK mode state
        self.is_awk_mode = False
        self.awk_executor: Optional[AwkExecutor] = None
        self.awk_records: list[AwkRecord] = []
        
        # JQ mode state
        self.is_jq_mode = False
        self.jq_executor: Optional[JqExecutor] = None

        # Widget cache
        self._output_widget: Optional[Static] = None
        self._groups_widget: Optional[Static] = None
        self._help_widget: Optional[Static] = None
        self._features_widget: Optional[FeaturesWidget] = None
        self._groups_container: Optional[ScrollableContainer] = None
        self._output_container: Optional[ScrollableContainer] = None
        self._pattern_input: Optional[Input] = None
        self._panel_header: Optional[Static] = None
        self._match_counter: Optional[Static] = None

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()
        with Horizontal(id="input-row"):
            # Left: Vertical container with Input + Buttons
            with Vertical(id="input-controls"):
                yield Input(value=self.pattern, placeholder="Enter regex pattern", id="pattern_input")
                with Horizontal(id="button-row"):
                    yield Button("Toggle View (F2)", id="toggle_view", variant="primary")
                    yield Button("Copy Pattern (Ctrl+Shift+C)", id="copy_pattern", variant="default")
                    yield Static("", id="match-counter")
            
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
                yield Static(numbered_content, id="output")
            with ScrollableContainer(id="groups-container", can_focus=True):
                with Header():
                    yield Static("Pattern Breakdown", id="panel-header")
                yield Static(id="groups", markup=True)
                yield Static(id="help", markup=True)
                
                # Initialize with current profile features
                # Use the default profile since we haven't rendered yet
                default_profile_id = self.profile_manager.get_default_profile_id()
                default_profile = self.profile_manager.get_profile(default_profile_id)
                current_features = default_profile.enabled_features if default_profile else set()
                
                yield FeaturesWidget(current_features, id="features_widget")
        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted."""
        self._cache_widgets()

    def _cache_widgets(self) -> None:
        """Cache references to frequently used widgets."""
        self._output_widget = self.query_one("#output", Static)
        self._groups_widget = self.query_one("#groups", Static)
        self._help_widget = self.query_one("#help", Static)
        self._features_widget = self.query_one("#features_widget", FeaturesWidget)
        self._groups_container = self.query_one("#groups-container", ScrollableContainer)
        self._output_container = self.query_one("#output-container", ScrollableContainer)
        self._pattern_input = self.query_one("#pattern_input", Input)
        self._panel_header = self.query_one("#panel-header", Static)
        self._match_counter = self.query_one("#match-counter", Static)
    
    def _add_line_numbers(self, content: Union[str, Text]) -> Text:
        """Add line numbers to content, returning a Rich Text object."""
        if isinstance(content, str):
            # Use Text.from_ansi to preserve any ANSI codes (common in AWK/JQ output)
            rich_text = Text.from_ansi(content)
        else:
            rich_text = content
            
        lines = rich_text.split('\n')
        max_line_num = len(lines)
        width = len(str(max_line_num))
        
        result = Text()
        for i, line_text in enumerate(lines, 1):
            # Add line number with dim styling
            result.append(f"{i:>{width}} ", style="dim")
            result.append(line_text)
            if i < max_line_num:
                result.append("\n")
        
        return result

    def _add_line_numbers_with_highlighting(self, highlighted_text: Text) -> Text:
        """Add line numbers to already-highlighted Rich Text object.
        
        This is now a wrapper around the more general _add_line_numbers.
        """
        return self._add_line_numbers(highlighted_text)

    def action_toggle_view(self) -> None:
        """Toggle between groups, help, features, and hidden view."""
        # Determine next mode
        next_mode = (self.view_mode + 1)
        
        # Skip features view (2) if not in regex mode
        if next_mode == ViewMode.FEATURES and (self.is_awk_mode or self.is_jq_mode):
            next_mode = ViewMode.HIDDEN
            
        # Wrap around
        if next_mode > ViewMode.HIDDEN:
            next_mode = ViewMode.GROUPS
            
        self.view_mode = next_mode
        
        # Reset full width state
        self._output_container.remove_class("full-width")
        self._groups_container.display = True
        
        # Hide all content widgets first
        self._groups_widget.display = False
        self._help_widget.display = False
        self._features_widget.display = False
        
        if self.view_mode == ViewMode.GROUPS:
            # Groups View (or Fields for AWK/JQ)
            self._groups_widget.display = True
            if self.is_awk_mode:
                self._panel_header.update("AWK Fields")
            elif self.is_jq_mode:
                self._panel_header.update("JQ Output")
            else:
                self._panel_header.update("Pattern Breakdown")
        elif self.view_mode == ViewMode.HELP:
            # Help View
            self._help_widget.display = True
            if self.is_awk_mode:
                self._panel_header.update("AWK Help")
                self._help_widget.update(self.get_awk_help_content())
            elif self.is_jq_mode:
                self._panel_header.update("JQ Help")
                self._help_widget.update(self.get_jq_help_content())
            else:
                self._panel_header.update("Regex Help")
                self._help_widget.update(self.get_help_content())
        elif self.view_mode == ViewMode.FEATURES:
            # Features View (only for regex mode)
            self._features_widget.display = True
            self._panel_header.update("Features Configuration")
        elif self.view_mode == ViewMode.HIDDEN:
            # Hidden Side Panel
            self._groups_container.display = False
            self._output_container.add_class("full-width")
    
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
        self._pattern_input.placeholder = "Enter AWK program (e.g., '{print $1}')"
        
        # Update panel header
        self._panel_header.update("AWK Fields")
        self._match_counter.update("")
        
        # Switch to groups view to show fields
        self.view_mode = ViewMode.GROUPS
        self._groups_widget.display = True
        self._help_widget.display = False
        self._features_widget.display = False
        
        # Re-run with current pattern if exists
        if self.pattern:
            self.run_worker(self.update_awk(self.pattern), exclusive=True)
        else:
            self._groups_widget.update(
                "[cyan]AWK Mode Active[/cyan]\n\n"
                "Enter an AWK program above.\n\n"
                "[bold]Examples:[/bold]\n"
                "  {print $1}           - Print first field\n"
                "  /pattern/ {print}    - Print lines matching pattern\n"
                "  {sum += $2} END {print sum}  - Sum second field\n\n"
                "[dim]Press F2 for AWK help[/dim]"
            )
            
    async def _switch_to_jq_mode(self, profile: RegexProfile) -> None:
        """Switch the UI to JQ mode."""
        self.is_jq_mode = True
        self.is_awk_mode = False
        
        self.jq_executor = JqExecutor()
        
        # Check if JQ is available
        if not self.jq_executor.is_available():
            groups_widget = self.query_one("#groups", Static)
            groups_widget.update(
                f"[red]Error: jq not found.[/red]\n"
                f"Please install jq to use this mode.\n\n"
                f"On Ubuntu/Debian: sudo apt install jq\n"
                f"On macOS: brew install jq"
            )
            return
            
        # Update input placeholder
        self._pattern_input.placeholder = "Enter JQ filter (e.g., '.')"
        
        # Update panel header
        self._panel_header.update("JQ Output")
        self._match_counter.update("")
        
        # Switch to groups view to show output
        self.view_mode = ViewMode.GROUPS
        self._groups_widget.display = True
        self._help_widget.display = False
        self._features_widget.display = False
        
        # Re-run with current pattern if exists
        if self.pattern:
            self.run_worker(self.update_jq(self.pattern), exclusive=True)
        else:
            self._groups_widget.update(
                "[cyan]JQ Mode Active[/cyan]\n\n"
                "Enter a JQ filter above.\n\n"
                "[bold]Examples:[/bold]\n"
                "  .                    - Pretty print all\n"
                "  .key                 - Get value of key\n"
                "  .[0]                 - Get first array item\n"
                "  . | keys             - List keys\n\n"
                "[dim]Press F2 for JQ help[/dim]"
            )
    
    async def _switch_to_regex_mode(self, profile: RegexProfile) -> None:
        """Switch the UI back to Regex mode."""
        self.is_awk_mode = False
        self.is_jq_mode = False
        self.awk_executor = None
        self.awk_records = []
        
        # Update input placeholder
        self._pattern_input.placeholder = "Enter regex pattern"
        
        # Update panel header
        self._panel_header.update("Pattern Breakdown")
        self._match_counter.update("")
        
        # Set profile
        self.regex_provider.set_profile(profile)
        
        # Update FeaturesWidget to match new profile
        self._features_widget.update_from_profile(profile)
        
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
            # Format field information as Text object to avoid markup errors 
            # and support ANSI colors from AWK output
            self.awk_records = records
            content = Text()
            content.append(f"Total Records: {len(records)}\n", style="bold cyan")
            content.append("\n")
            
            # Show first few records
            for record in records[:5]:
                content.append(f"Record {record.number}:", style="bold")
                content.append("\n")
                content.append("  $0: ", style="dim")
                content.append(Text.from_ansi(record.full_record))
                content.append("\n")
                content.append("  NF: ", style="dim")
                content.append(str(record.num_fields))
                content.append("\n")
                for field in record.fields[:10]:  # Limit fields shown
                    content.append(f"  ${field.index}: ", style="cyan")
                    content.append(Text.from_ansi(field.value))
                    content.append("\n")
                content.append("\n")
            
            if len(records) > 5:
                content.append(f"... and {len(records) - 5} more records", style="dim")
            
            groups_widget.update(content)
    
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

    async def update_jq(self, jq_program: str):
        """Execute JQ program and update UI."""
        if not self.jq_executor:
            return
            
        # Run in thread pool to avoid blocking
        output, error = await asyncio.to_thread(
            self.jq_executor.execute,
            jq_program,
            self.input_content
        )
        
        output_widget = self.query_one("#output", Static)
        groups_widget = self.query_one("#groups", Static)
        
        if error:
            # Show error
            from rich.markup import escape
            groups_widget.update(f"[red]JQ Error:[/red]\n{escape(error)}")
            output_widget.update(self._add_line_numbers(self.input_content))
            return
        
        # Show JQ output in the main area (it replaces the content view)
        # For JQ, we want to see the result of the transformation
        numbered_output = self._add_line_numbers(output if output else "(no output)")
        output_widget.update(numbered_output)
        
        # Update status in side panel
        groups_widget.update("[green]JQ execution successful[/green]")

    def get_jq_help_content(self) -> str:
        """Generate JQ-specific help content."""
        lines = []
        lines.append("[bold cyan]JQ Quick Reference[/bold cyan]\n")
        
        lines.append("[bold]Basic Filters:[/bold]")
        lines.append("[cyan].[/cyan]             Identity (pretty print)")
        lines.append("[cyan].foo[/cyan]          Value of key 'foo'")
        lines.append("[cyan].[0][/cyan]          First item in array")
        lines.append("[cyan].[][/cyan]          Iterate over values\n")
        
        lines.append("[bold]Pipes & Functions:[/bold]")
        lines.append("[cyan]|[/cyan]             Pipe output to next filter")
        lines.append("[cyan]keys[/cyan]          List keys")
        lines.append("[cyan]length[/cyan]        Length of string/array")
        lines.append("[cyan]select(foo)[/cyan]   Filter by condition\n")
        
        lines.append("[bold]Constructors:[/bold]")
        lines.append("[cyan]{a: .b}[/cyan]      Build object")
        lines.append("[cyan][.foo, .bar][/cyan] Build array\n")
        
        lines.append("[bold]Examples:[/bold]")
        lines.append("[cyan].users[].name[/cyan]")
        lines.append("  Get name of every user")
        lines.append("[cyan]select(.id > 10)[/cyan]")
        lines.append("  Select items with id > 10")
        lines.append("[cyan]keys[/cyan]")
        lines.append("  Show available keys\n")
        
        lines.append("[dim]Press F2 to return to output view[/dim]")
        
        return "\n".join(lines)



    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
    
    def action_focus_results(self) -> None:
        """Switch focus to the results container."""
        self._output_container.focus()
    
    def action_focus_input(self) -> None:
        """Switch focus back to the input field."""
        self._pattern_input.focus()
    
    def action_focus_groups(self) -> None:
        """Switch focus to the groups/help container."""
        self._groups_container.focus()
    
    def action_next_match(self) -> None:
        """Navigate to the next match."""
        if not self.match_positions:
            return
        
        self.current_match_index = (self.current_match_index + 1) % len(self.match_positions)
        self._scroll_to_match(self.current_match_index)
        self._refresh_highlighting()
        self._update_match_counter()
    
    def action_prev_match(self) -> None:
        """Navigate to the previous match."""
        if not self.match_positions:
            return
        
        self.current_match_index = (self.current_match_index - 1) % len(self.match_positions)
        self._scroll_to_match(self.current_match_index)
        self._refresh_highlighting()
        self._update_match_counter()
    
    def action_scroll_down(self) -> None:
        """Scroll down in the active container."""
        if self.focused.id == "groups-container":
            self._groups_container.scroll_down()
        else:
            self._output_container.scroll_down()

    def action_scroll_up(self) -> None:
        """Scroll up in the active container."""
        if self.focused.id == "groups-container":
            self._groups_container.scroll_up()
        else:
            self._output_container.scroll_up()

    def _scroll_to_match(self, match_index: int) -> None:
        """Scroll to the specified match, keeping it centered in the viewport."""
        if match_index < 0 or match_index >= len(self.match_positions):
            return
        
        position = self.match_positions[match_index]
        container = self._output_container
        
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
        
        output_result = self.formatter.create_highlighted_output(
            self._last_matches, 
            self.current_match_index
        )
        
        # Add line numbers to the highlighted output
        numbered_output = self._add_line_numbers_with_highlighting(output_result)
        self._output_widget.update(numbered_output)

    def _update_match_counter(self) -> None:
        """Update the match counter UI."""
        if self.is_awk_mode or self.is_jq_mode:
            self._match_counter.update("")
            return
            
        count = len(self.match_positions)
        if count == 0:
            self._match_counter.update("[dim]0 matches[/dim]")
        else:
            current = self.current_match_index + 1
            self._match_counter.update(f"[bold]{current}[/bold] of [bold]{count}[/bold] matches")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "toggle_view":
            self.action_toggle_view()
        elif event.button.id == "copy_pattern":
            self.action_copy_pattern()
            
    def action_copy_pattern(self) -> None:
        """Copy current pattern to clipboard."""
        if not self.pattern:
            self.notify("Nothing to copy", severity="warning")
            return
            
        if pyperclip:
            try:
                pyperclip.copy(self.pattern)
                self.notify("Pattern copied to clipboard!", severity="information")
            except Exception as e:
                self.notify(f"Failed to copy: {str(e)}", severity="error")
        else:
            self.notify("pyperclip not installed. Cannot copy.", severity="error")

    @on(Input.Changed)
    async def on_input_changed(self, message: Input.Changed) -> None:
        """Handle input field changes."""
        # Sanitize input to remove terminal escape sequences (e.g., mouse events)
        
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
        elif self.is_jq_mode:
            self.run_worker(self.update_jq(clean_value), exclusive=True)
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
                elif profile.profile_type == "jq":
                    # Switch to JQ mode
                    await self._switch_to_jq_mode(profile)
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
        if not str_pattern:
            self._output_widget.update(self._add_line_numbers(self.input_content))
            self._groups_widget.update("[dim]Enter a regex pattern to see matches[/dim]")
            self.match_positions = []
            self.current_match_index = -1
            self._update_match_counter()
            return

        # Run heavy lifting in a thread to avoid blocking the UI
        groups_result, error, output_result, match_positions, groups = await asyncio.to_thread(
            self._get_regex_result, str_pattern
        )
        
        if error:
            error_msg = self._get_regex_error_message(str(error), str_pattern)
            self._groups_widget.update(error_msg)
            
            # Also reset output highlighting if there's an error
            self._output_widget.update(self._add_line_numbers(self.input_content))
            self.match_positions = []
            self.current_match_index = -1
            self._last_matches = []
            self._match_counter.update("[bold red]Error[/bold red]")
        elif output_result is not None:
            # Update match tracking
            self.match_positions = match_positions
            self.current_match_index = 0 if match_positions else -1
            self._last_matches = groups if groups else []
            
            # Update widgets (only update groups if in groups view)
            if self.view_mode == ViewMode.GROUPS:
                self._groups_widget.update(groups_result if groups_result else "[dim]No capture groups in pattern[/dim]")
                self._groups_widget.refresh()  # Force redraw
            
            # Add line numbers and update output
            numbered_output = self._add_line_numbers_with_highlighting(output_result)
            self._output_widget.update(numbered_output)
            
            # Update match counter
            self._update_match_counter()

            # Autoscroll to first match
            if match_positions:
                self._scroll_to_match(0)
        else:
            # No matches found
            if self.view_mode == ViewMode.GROUPS:
                self._groups_widget.update("[dim]No matches found[/dim]")
            self._output_widget.update(self._add_line_numbers(self.input_content))
            self.match_positions = []
            self.current_match_index = -1
            self._last_matches = []
            self._update_match_counter()
    
    def _get_regex_error_message(self, error_str: str, pattern: str) -> str:
        """Construct a detailed error message for regex errors."""
        pos_match = re.search(r"at position (\d+)", error_str)
        error_msg = f"[bold red]Regex Error:[/bold red] {error_str}"
        
        if pos_match:
            try:
                pos = int(pos_match.group(1))
                # Create a visual pointer
                start = max(0, pos - 20)
                end = min(len(pattern), pos + 20)
                
                prefix = "..." if start > 0 else ""
                suffix = "..." if end < len(pattern) else ""
                
                snippet = pattern[start:end]
                pointer_pos = pos - start
                
                pointer_line = " " * (pointer_pos + len(prefix)) + "[bold red]^[/bold red]"
                pattern_line = f"{escape(prefix)}[cyan]{escape(snippet)}[/cyan]{escape(suffix)}"
                
                error_msg += f"\n\n[dim]Error location:[/dim]\n{pattern_line}\n{pointer_line}"
            except (ValueError, IndexError):
                pass
        return error_msg

    # Method removed and replaced by a wrapper around _add_line_numbers above.
    pass
