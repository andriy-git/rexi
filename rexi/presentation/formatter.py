"""Formatter for regex match output."""

from colorama import Fore

from ..data_providers.regex_provider import GroupMatch

UNDERLINE = "\033[4m"
RESET_UNDERLINE = "\033[24m"


class RegexFormatter:
    """Formats regex match results for display."""
    
    def __init__(self, input_content: str):
        """Initialize the formatter with input content.
        
        Args:
            input_content: The original input text
        """
        self.input_content = input_content
    
    def create_highlighted_output(self, matches: list[list[GroupMatch]]) -> str:
        """Create highlighted output with color codes and underlining.
        
        Args:
            matches: List of matches, where each match is a list of GroupMatch objects
            
        Returns:
            String with ANSI color codes for highlighting
        """
        if not matches:
            return self.input_content
            
        # Flatten matches for processing
        all_groups = [group for match_groups in matches for group in match_groups]
            
        output = ""
        # Group 0 (full match) gets underline
        first_starts = {group.span[0] for group in all_groups if group.group_index == 0}
        first_ends = {group.span[1] for group in all_groups if group.group_index == 0}
        
        # Other groups get color
        starts = {group.span[0] for group in all_groups if group.group_index > 0}
        ends = {group.span[1] for group in all_groups if group.group_index > 0}
        
        input_length = len(self.input_content)
        
        for character in range(input_length):
            # Apply styles at start positions
            if character in first_starts and character not in first_ends:
                output += UNDERLINE
            if character in starts and character not in ends:
                output += Fore.RED
                
            # Reset styles at end positions
            # Note: The order of reset matters if ranges coincide
            if character in ends and character not in starts:
                output += Fore.RESET
            if character in first_ends and character not in first_starts:
                output += RESET_UNDERLINE
                
            output += self.input_content[character]

        # Handle end of string
        if input_length in ends:
            output += Fore.RESET
        if input_length in first_ends:
            output += RESET_UNDERLINE

        return output
    
    @staticmethod
    def create_groups_output(matches: list[list[GroupMatch]]) -> str:
        """Create formatted output for matched groups.
        
        Args:
            matches: List of matches, where each match is a list of GroupMatch objects
            
        Returns:
            Formatted string showing all groups
        """
        # Flatten matches
        all_groups = [group for match_groups in matches for group in match_groups]
        
        # Only show capture groups (index > 0), not the full match
        return "\n".join(
            [repr(group) for group in all_groups if group.group_index > 0]
        )
