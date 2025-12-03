<p align="center">
     <a><img src="https://github.com/royreznik/rexi/blob/master/docs/rexi.png" alt="Rexi"></a>
</p>

<p align="center">
     <a href="https://github.com/royreznik/greps/actions/workflows/tests.yml"><img src="https://github.com/royreznik/rexi/actions/workflows/tests.yml/badge.svg" alt="Testing"></a>
     <a href="https://img.shields.io/github/license/royreznik/rexi"><img src="https://img.shields.io/github/license/royreznik/rexi" alt="License"></a>
     <a href="https://codecov.io/gh/royreznik/rexi"><img src="https://codecov.io/gh/royreznik/rexi/graph/badge.svg?token=LOIYAMEI08" alt="coverage"></a>
     <a href="https://pypi.org/project/rexi/"><img src="https://img.shields.io/pypi/pyversions/rexi" alt="versions"></a>
     <img src="https://img.shields.io/badge/code%20style-black-black" alt="style">
</p>

---

`rexi` is a modern, interactive Terminal User Interface (TUI) for crafting and testing Regular Expressions, AWK scripts, and JQ filters. Built with [Textual](https://textual.textualize.io/), it provides real-time feedback, detailed pattern breakdowns, and support for multiple regex engines.

## Key Features

*   **Real-time Highlighting**: See matches instantly as you type.
*   **Multi-Engine Support**: Switch between **Python (re)**, **PCRE**, **Grep**, **Sed**, **AWK**, and **JQ**.
*   **Pattern Breakdown**: Understand complex regex with a detailed breakdown of capture groups and matches.
*   **AWK Support**: Write and test AWK scripts interactively with field breakdowns (`$1`, `$2`, etc.).
*   **JQ Support**: Filter and transform JSON data with `jq` filters and see results in real-time.
*   **Educational**: Visual error pointers and context-aware help make learning regex easier.
*   **Flexible Input**: Pipe data from stdin or load from files.
*   **Copy to Clipboard**: Easily copy patterns with a button or keyboard shortcut.

## Installation

### From PyPI
```bash
pip install rexi
```

### From Source
```bash
git clone https://github.com/royreznik/rexi.git
cd rexi
./install.sh
```

### System Dependencies

For AWK support, install one of:
```bash
# Ubuntu/Debian
sudo apt install gawk  # or mawk

# macOS (AWK pre-installed)
```

For JQ support:
```bash
# Ubuntu/Debian
sudo apt install jq

# macOS
brew install jq
```

## Usage

### Piping Input (Recommended)
Pipe output from any command directly into `rexi`:
```bash
cat /etc/hosts | rexi
ls -la | rexi
curl -s https://example.com | rexi
cat data.json | rexi  # For JQ mode
```

### File Input
Load a file directly:
```bash
rexi -i path/to/file.txt
rexi -i data.json  # Supports JSON for JQ
```

### Initial Pattern
Start with a pattern pre-loaded:
```bash
rexi -p "^\\d+" -i data.txt
```

## Interface & Controls

| Key | Action |
| :--- | :--- |
| `F2` | Toggle Views (Groups / Help / Features / Hidden) |
| `n` / `N` | Jump to Next / Previous Match |
| `j` / `k` | Scroll Output |
| `Enter` | Focus Results |
| `i` | Focus Input |
| `Ctrl+Shift+C` | Copy Pattern |
| `Escape` | Quit |

## Profiles

Rexi supports multiple regex flavors and tools:

*   **RE - Python (re)**: Standard Python regular expressions.
*   **RE - PCRE**: Perl Compatible Regular Expressions (supports atomic groups, recursion, etc.).
*   **RE - Grep/Sed**: Simulates basic POSIX regex behavior.
*   **AWK**: Full AWK script execution (supports `gawk`, `mawk`, etc.).
*   **JQ**: JSON processor for filtering and transforming JSON data.

## Testing

Run the test suite:
```bash
./run_tests.sh
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License
