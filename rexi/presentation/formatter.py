"""Formatter for regex match output."""

from rich.text import Text
from rich.table import Table
from rich import box
from ..data_providers.regex_provider import GroupMatch


class RegexFormatter:
    """Formats regex match results for display."""
    
    # Colors for capture groups (cycling) - using backgrounds for better visibility
    GROUP_STYLES = [
        "bold white on dark_cyan",
        "bold white on dark_green",
        "bold black on yellow",
        "bold white on dark_magenta",
        "bold white on dark_blue",
        "bold black on bright_cyan",
        "bold black on bright_green",
        "bold black on bright_yellow",
        "bold black on bright_magenta",
    ]
    
    def __init__(self, input_content: str):
        """Initialize the formatter with input content.
        
        Args:
            input_content: The original input text
        """
        self.input_content = input_content
    
    def create_highlighted_output(self, matches: list[list[GroupMatch]], current_match_index: int = -1) -> Text:
        """Create highlighted output with color codes and underlining.
        
        Args:
            matches: List of matches, where each match is a list of GroupMatch objects
            current_match_index: Index of the current match to highlight differently (default: -1 for none)
            
        Returns:
            Text object with highlighting applied
        """
        text = Text(self.input_content)
        
        if not matches:
            return text
            
        # Flatten matches for processing
        all_groups = [group for match_groups in matches for group in match_groups]
        
        for match_idx, match_groups in enumerate(matches):
            for group in match_groups:
                # Group 0 (full match) gets a subtle background
                if group.group_index == 0:
                    if match_idx == current_match_index:
                        # Current match gets a bright, inverted highlight
                        text.stylize("bold reverse white", group.span[0], group.span[1])
                    else:
                        text.stylize("bold white on #444444", group.span[0], group.span[1])
                # Other groups get color from palette with backgrounds
                else:
                    style = self.GROUP_STYLES[(group.group_index - 1) % len(self.GROUP_STYLES)]
                    if match_idx == current_match_index:
                        # Make current match's groups more prominent
                        style = f"reverse {style}"
                    text.stylize(style, group.span[0], group.span[1])
                
        return text
    
    def get_match_positions(self, matches: list[list[GroupMatch]]) -> list[int]:
        """Get the start positions of all matches.
        
        Args:
            matches: List of matches, where each match is a list of GroupMatch objects
            
        Returns:
            List of character positions (start of each match)
        """
        positions = []
        for match_groups in matches:
            if match_groups and match_groups[0].group_index == 0:
                positions.append(match_groups[0].span[0])
        return positions
    
    @staticmethod
    def create_groups_output(matches: list[list[GroupMatch]]) -> Table:
        """Create formatted output for matched groups.
        
        Args:
            matches: List of matches, where each match is a list of GroupMatch objects
            
        Returns:
            Rich Table showing all groups
        """
        table = Table(
            box=box.ROUNDED, 
            expand=True, 
            show_header=True,
            show_lines=False,
            padding=(0, 1)
        )
        table.add_column("Match", style="cyan", no_wrap=True, width=6)
        table.add_column("Group", style="magenta", no_wrap=True, width=6)
        table.add_column("Name", style="green", width=12)
        table.add_column("Value", style="white")
        table.add_column("Span", style="yellow", justify="right", width=12)
        
        for i, match_groups in enumerate(matches, 1):
            for group in match_groups:
                if group.group_index == 0:
                    continue
                    
                table.add_row(
                    str(i),
                    str(group.group_index),
                    group.name or "-",
                    group.value,
                    f"{group.span[0]}-{group.span[1]}"
                )
                
        return table
