"""JQ program executor using subprocess."""

import subprocess
import shutil
from typing import Optional

class JqExecutor:
    """Executes JQ programs."""
    
    def __init__(self, jq_command: str = "jq"):
        """Initialize with specific JQ command."""
        self.jq_command = jq_command
        self._check_jq_available()
    
    def _check_jq_available(self) -> bool:
        """Check if JQ is available on the system."""
        return shutil.which(self.jq_command) is not None
    
    def is_available(self) -> bool:
        """Check if JQ is available."""
        return self._check_jq_available()
    
    def execute(self, program: str, input_text: str, timeout: int = 5) -> tuple[Optional[str], Optional[str]]:
        """
        Execute a JQ program.
        
        Args:
            program: The JQ program to execute
            input_text: The input text to process (should be JSON)
            timeout: Maximum execution time in seconds
            
        Returns:
            Tuple of (output, error). If successful, error is None.
        """
        try:
            # Ensure program is not empty, default to identity
            if not program.strip():
                program = "."
                
            result = subprocess.run(
                [self.jq_command, program],
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                return None, result.stderr or "JQ execution failed"
            
            return result.stdout, None
            
        except subprocess.TimeoutExpired:
            return None, f"JQ execution timed out after {timeout} seconds"
        except FileNotFoundError:
            return None, f"{self.jq_command} not found. Please install JQ."
        except Exception as e:
            return None, f"Error executing JQ: {str(e)}"
