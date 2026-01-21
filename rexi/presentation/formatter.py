"""Formatter for regex match output."""

from rich.text import Text
from rich.markup import escape
from ..data_providers.regex_provider import GroupMatch


class RegexFormatter:
    """Formats regex match results for display."""
    
    # Colors for highlighting
    MATCH_STYLE = "bold #ffffff on #005f87"  # White on dark blue for main match
    GROUP_STYLES = [
        "bold #00ff00 on #005f87",  # Bright Green on dark blue
        "bold #ffff00 on #005f87",  # Bright Yellow on dark blue
        "bold #ff00ff on #005f87",  # Magenta on dark blue
        "bold #ff4444 on #005f87",  # Red on dark blue
        "bold #00ffff on #005f87",  # Cyan on dark blue
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
                        text.stylize("bold black on #4fc3f7", group.span[0], group.span[1])
                    else:
                        # Unfocused matches get a visible but subtle highlight
                        text.stylize("bold #4fc3f7 on #2d3748", group.span[0], group.span[1])
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
    def create_groups_output(matches: list[list[GroupMatch]]) -> str:
        """Create educational output explaining matches and capture groups.
        
        Args:
            matches: List of matches, where each match is a list of GroupMatch objects
            
        Returns:
            Formatted string explaining the pattern and showing captured groups
        """
        lines = []
        
        # Count total matches and groups
        total_matches = len(matches)
        total_groups = sum(len([g for g in match if g.group_index > 0]) for match in matches)
        
        if total_groups == 0:
            if total_matches > 0:
                return f"[bold]Found {total_matches} match(es)[/bold]\n\n[dim]No capture groups in pattern.[/dim]\n[yellow]Tip:[/yellow] Add parentheses [cyan]()[/cyan] around parts of your pattern to capture groups.\n[dim]Example: [cyan]\\d+[/cyan] → [cyan](\\d+)[/cyan][/dim]"
            else:
                return "[dim]No matches found[/dim]"
        
        # Summary header
        lines.append(f"[bold cyan]Found {total_matches} match(es) with {total_groups} captured group(s)[/bold cyan]\n")
        
        # Explain what capture groups are
        lines.append("[bold]What are capture groups?[/bold]")
        lines.append("[dim]Parts of your pattern in [cyan]()[/cyan] are 'captured' so you can:")
        lines.append("  • Extract specific parts of matches")
        lines.append("  • Reference them later with [cyan]\\1[/cyan], [cyan]\\2[/cyan], etc.")
        lines.append("  • Use them in search & replace operations[/dim]\n")
        
        # Show captured values grouped by group number
        groups_by_index = {}
        for match_groups in matches:
            for group in match_groups:
                if group.group_index > 0:
                    if group.group_index not in groups_by_index:
                        groups_by_index[group.group_index] = []
                    groups_by_index[group.group_index].append(group.value)
        
        # Show each capture group's values
        for group_idx in sorted(groups_by_index.keys()):
            values = groups_by_index[group_idx]
            unique_count = len(set(values))
            
            # Show group header
            group_name = f"Group {group_idx}"
            
            # Find name from any match that has this group
            name = None
            for match_groups in matches:
                for g in match_groups:
                    if g.group_index == group_idx and g.name:
                        name = g.name
                        break
                if name:
                    break
            
            if name:
                group_name += f" [cyan]({name})[/cyan]"
            
            lines.append(f"[bold magenta]{group_name}:[/bold magenta] {len(values)} captured")
            
            # Show first few unique examples
            unique_values = list(dict.fromkeys(values[:20]))  # Keep order, remove dupes
            examples = unique_values[:5]
            
            if examples:
                examples_str = ", ".join([f"[cyan]{escape(repr(v[:20]))}[/cyan]" if len(v) <= 20 else f"[cyan]{escape(repr(v[:17]))}...[/cyan]" for v in examples])
                lines.append(f"  Examples: {examples_str}")
                
                if len(unique_values) > 5:
                    lines.append(f"  [dim]...and {len(unique_values) - 5} more unique value(s)[/dim]")
            
            lines.append("")  # Blank line between groups
        
        return "\n".join(lines)
