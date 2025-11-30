import re
from typing import Iterable, Optional, Tuple, List, Pattern, Match, Set
from dataclasses import dataclass
try:
    import regex
except ImportError:
    regex = None

from .profile_manager import RegexProfile

@dataclass
class GroupMatch:
    """Represents a matched group in the regex."""
    span: Tuple[int, int]
    value: str
    name: Optional[str] = None
    group_index: int = 0

class RegexProvider:
    """Provides regex matching functionality with support for multiple engines and profiles."""

    def __init__(self, content: str):
        self.content = content
        self.current_profile: Optional[RegexProfile] = None

    def set_profile(self, profile: RegexProfile) -> None:
        """Set the current regex profile."""
        self.current_profile = profile

    def validate_pattern(self, pattern: str) -> Optional[str]:
        """Validate the pattern against the current profile's enabled features.
        
        Returns:
            Error message string if invalid, None if valid.
        """
        if not self.current_profile:
            return None

        features = self.current_profile.enabled_features

        # Basic feature validation (simple string checks for now)
        # This is a simplified validator. A full AST parser would be better but complex.
        
        if "lookahead" not in features and "(?=" in pattern:
            return "Error: Lookahead '(?=' is not enabled in this profile."
        if "lookbehind" not in features and "(?<=" in pattern:
            return "Error: Lookbehind '(?<=' is not enabled in this profile."
        if "atomic" not in features and "(?>" in pattern:
            return "Error: Atomic groups '(?>' are not enabled in this profile."
        if "possessive" not in features and ("*+" in pattern or "++" in pattern or "?+" in pattern):
            return "Error: Possessive quantifiers are not enabled in this profile."
        if "recursion" not in features and ("(?R)" in pattern or "(?0)" in pattern):
            return "Error: Recursion is not enabled in this profile."
        if "named_groups" not in features and "(?P<" in pattern:
            return "Error: Named groups '(?P<...>' are not enabled in this profile."
        
        return None

    def get_matches(self, pattern: str, mode: str = "finditer") -> Tuple[List[List[GroupMatch]], Optional[str]]:
        """
        Get matches for the given pattern.
        
        Args:
            pattern: The regex pattern string.
            mode: 'match' or 'finditer' (default).
            
        Returns:
            A tuple containing:
            - A list of lists of GroupMatch objects (one list of groups per match).
            - An error message string if an error occurred, or None.
        """
        if not pattern:
            return [], None

        # Validate pattern against profile features
        validation_error = self.validate_pattern(pattern)
        if validation_error:
            return [], validation_error

        try:
            # Determine which engine to use
            use_regex = False
            if self.current_profile and self.current_profile.use_regex_module:
                if regex:
                    use_regex = True
                else:
                    return [], "Error: 'regex' module is required for this profile but not installed."
            
            compiled_pattern = self._compile_pattern(pattern, use_regex)
            
            matches: Iterable[Match[str]] = []
            if mode == "match":
                match = compiled_pattern.match(self.content)
                if match:
                    matches = [match]
            else:  # finditer
                matches = compiled_pattern.finditer(self.content)

            results = []
            for match in matches:
                results.append(self._extract_groups(match))
            
            return results, None

        except (re.error, regex.error if regex else re.error) as e:
            return [], f"Regex Error: {str(e)}"
        except Exception as e:
            return [], f"Error: {str(e)}"

    def _compile_pattern(self, pattern: str, use_regex: bool):
        """Compile the pattern using the appropriate engine."""
        if use_regex:
            # Use regex module with VERSION1 for full PCRE compatibility
            return regex.compile(pattern, flags=regex.MULTILINE | regex.VERSION1)
        else:
            # Use standard re module
            return re.compile(pattern, re.MULTILINE)

    def _extract_groups(self, match: Match[str]) -> List[GroupMatch]:
        """Extract groups from a match object."""
        groups = []
        
        # Add the full match (group 0)
        groups.append(GroupMatch(
            span=match.span(0),
            value=match.group(0),
            name=None,
            group_index=0
        ))

        # Add capturing groups
        for i, value in enumerate(match.groups(), start=1):
            if value is None:
                continue
                
            # Find group name if it exists
            name = None
            for group_name, group_index in match.re.groupindex.items():
                if group_index == i:
                    name = group_name
                    break
            
            groups.append(GroupMatch(
                span=match.span(i),
                value=value,
                name=name,
                group_index=i
            ))
            
        return groups
