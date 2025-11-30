"""Regex help patterns and descriptions."""

REGEX_HELP = {
    "Anchors": {
        "^": "Start of string (or line in multiline mode)",
        "$": "End of string (or line in multiline mode)",
        "\\b": "Word boundary",
        "\\B": "Not a word boundary",
    },
    "Quantifiers": {
        "*": "0 or more",
        "+": "1 or more",
        "?": "0 or 1",
        "{n}": "Exactly n times",
        "{n,}": "n or more times",
        "{n,m}": "Between n and m times",
    },
    "Character Classes": {
        ".": "Any character (except newline)",
        "\\d": "Digit [0-9]",
        "\\D": "Non-digit",
        "\\w": "Word character [a-zA-Z0-9_]",
        "\\W": "Non-word character",
        "\\s": "Whitespace",
        "\\S": "Non-whitespace",
        "[abc]": "Any of a, b, or c",
        "[^abc]": "Not a, b, or c",
    },
    "Groups": {
        "(...)": "Capturing group",
        "(?:...)": "Non-capturing group",
        "(?P<name>...)": "Named capturing group",
        "\\1": "Backreference to group 1",
    },
    "Lookaround": {
        "(?=...)": "Positive lookahead",
        "(?!...)": "Negative lookahead",
        "(?<=...)": "Positive lookbehind",
        "(?<!...)": "Negative lookbehind",
    },
    "Flags": {
        "(?i)": "Case-insensitive",
        "(?m)": "Multiline",
        "(?s)": "Dot matches newline",
    }
}
