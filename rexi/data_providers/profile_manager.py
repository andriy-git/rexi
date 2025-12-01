import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Optional



@dataclass
class RegexProfile:
    name: str
    description: str
    enabled_features: Set[str]
    use_regex_module: bool
    id: str
    profile_type: str = "regex"  # "regex" or "awk"

class ProfileManager:
    def __init__(self):
        self.profiles: Dict[str, RegexProfile] = {}
        self.load_default_profiles()

    def load_default_profiles(self) -> None:
        """Load profiles from the default JSON configuration."""
        # In a real package, we might use pkg_resources or importlib.resources
        # For now, we'll assume the file is relative to this file's location
        # or use a hardcoded path relative to the package root.
        
        # Try to find the file relative to this module
        current_dir = Path(__file__).parent.parent
        config_path = current_dir / "default_configs" / "profiles.json"
        
        if config_path.exists():
            with open(config_path, "r") as f:
                data = json.load(f)
                for profile_id, profile_data in data.items():
                    self.profiles[profile_id] = RegexProfile(
                        name=profile_data["name"],
                        description=profile_data["description"],
                        enabled_features=set(profile_data["enabled_features"]),
                        use_regex_module=profile_data["use_regex_module"],
                        id=profile_id,
                        profile_type=profile_data.get("type", "regex")
                    )
        else:
            # Profiles not found - will use empty dict
            pass

    def get_profile(self, profile_id: str) -> Optional[RegexProfile]:
        return self.profiles.get(profile_id)

    def list_profiles(self) -> List[RegexProfile]:
        return list(self.profiles.values())

    def get_default_profile_id(self) -> str:
        return "pcre_full"
