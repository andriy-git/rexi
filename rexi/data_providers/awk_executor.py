"""AWK program executor using subprocess."""

import subprocess
import shutil
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class AwkField:
    """Represents a field in an AWK record."""
    index: int
    value: str


@dataclass
class AwkRecord:
    """Represents a record (line) processed by AWK."""
    number: int  # NR
    fields: List[AwkField]
    num_fields: int  # NF
    full_record: str  # $0


class AwkExecutor:
    """Executes AWK programs and parses output."""
    
    def __init__(self, awk_command: str = "gawk"):
        """Initialize with specific AWK variant."""
        self.awk_command = awk_command
        self._check_awk_available()
    
    def _check_awk_available(self) -> bool:
        """Check if AWK is available on the system."""
        return shutil.which(self.awk_command) is not None
    
    def is_available(self) -> bool:
        """Check if this AWK variant is available."""
        return self._check_awk_available()
    
    def execute(self, program: str, input_text: str, timeout: int = 5) -> tuple[Optional[str], Optional[str]]:
        """
        Execute an AWK program.
        
        Args:
            program: The AWK program to execute
            input_text: The input text to process
            timeout: Maximum execution time in seconds
            
        Returns:
            Tuple of (output, error). If successful, error is None.
        """
        try:
            result = subprocess.run(
                [self.awk_command, program],
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                return None, result.stderr or "AWK execution failed"
            
            return result.stdout, None
            
        except subprocess.TimeoutExpired:
            return None, f"AWK execution timed out after {timeout} seconds"
        except FileNotFoundError:
            return None, f"{self.awk_command} not found. Please install AWK."
        except Exception as e:
            return None, f"Error executing AWK: {str(e)}"
    
    def get_field_breakdown(self, input_text: str, field_separator: Optional[str] = None) -> tuple[Optional[List[AwkRecord]], Optional[str]]:
        """
        Get detailed field information for each record.
        
        Args:
            input_text: The input text to analyze
            field_separator: Optional field separator (FS)
            
        Returns:
            Tuple of (records, error). If successful, error is None.
        """
        # AWK program to output fields in parseable format
        fs_arg = f'-F"{field_separator}"' if field_separator else ''
        
        # Use a special format to capture field information
        debug_program = '''
        {
            printf "RECORD:%d|NF:%d|FULL:", NR, NF
            # Print full record (escaped)
            gsub(/\\|/, "\\\\|", $0)  # Escape pipes in $0
            printf "%s", $0
            printf "|FIELDS:"
            for (i=1; i<=NF; i++) {
                gsub(/\\|/, "\\\\|", $i)  # Escape pipes in fields
                printf "%d:%s", i, $i
                if (i < NF) printf ","
            }
            printf "\\n"
        }
        '''
        
        output, error = self.execute(debug_program, input_text)
        
        if error:
            return None, error
        
        # Parse the output
        records = []
        for line in output.strip().split('\n'):
            if not line:
                continue
                
            try:
                record = self._parse_record_line(line)
                if record:
                    records.append(record)
            except Exception as e:
                # Skip malformed lines
                continue
        
        return records, None
    
    def _parse_record_line(self, line: str) -> Optional[AwkRecord]:
        """Parse a single record output line."""
        # Format: RECORD:1|NF:3|FULL:text here|FIELDS:1:val1,2:val2,3:val3
        parts = line.split('|')
        
        record_num = None
        num_fields = None
        full_record = None
        fields = []
        
        for part in parts:
            if part.startswith('RECORD:'):
                record_num = int(part.split(':', 1)[1])
            elif part.startswith('NF:'):
                num_fields = int(part.split(':', 1)[1])
            elif part.startswith('FULL:'):
                full_record = part.split(':', 1)[1]
            elif part.startswith('FIELDS:'):
                field_str = part.split(':', 1)[1]
                if field_str:
                    for field in field_str.split(','):
                        idx, val = field.split(':', 1)
                        fields.append(AwkField(int(idx), val))
        
        if record_num is not None and num_fields is not None and full_record is not None:
            return AwkRecord(
                number=record_num,
                fields=fields,
                num_fields=num_fields,
                full_record=full_record
            )
        
        return None


def detect_awk_variants() -> Dict[str, bool]:
    """Detect which AWK variants are available on the system."""
    variants = {
        'gawk': False,
        'mawk': False,
        'awk': False
    }
    
    for variant in variants.keys():
        variants[variant] = shutil.which(variant) is not None
    
    return variants
