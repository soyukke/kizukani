#!/usr/bin/env python3
"""Checks the comment rule of AGENTS.md on Kizu sources.

    python3 scripts/comment-lint/check.py [--root DIR] [FILE...]

FILE is relative to DIR (default: the current directory). With no FILE, every
.kizu file under DIR/src is checked. Exit status 1 and one `path:line: reason`
per violation when a file breaks the rule.

`///` (exactly three slashes) and `// SAFETY:` pass. Every other `//` fails, at
the start of a line or after code. `"` opens a string that runs to the next `"`,
and `\\\\` opens a multiline-string line that runs to the end of the line, so a
`//` inside either is not a comment.
"""

import argparse
import os
import re
import sys

SAFETY = re.compile(r"^//[ \t]*SAFETY:")


def scan_comments(source):
    comments = []
    index = 0
    length = len(source)
    line = 1
    line_has_code = False
    while index < length:
        character = source[index]
        if character == "\n":
            line += 1
            line_has_code = False
            index += 1
        elif character == '"':
            line_has_code = True
            index += 1
            while index < length and source[index] != '"':
                if source[index] == "\n":
                    line += 1
                index += 1
            index += 1
        elif source.startswith("\\\\", index):
            line_has_code = True
            end = source.find("\n", index)
            index = length if end < 0 else end
        elif source.startswith("//", index):
            end = source.find("\n", index)
            end = length if end < 0 else end
            comments.append((line, source[index:end], not line_has_code))
            index = end
        else:
            if character not in " \t\r":
                line_has_code = True
            index += 1
    return comments


def is_allowed(text):
    if text.startswith("///") and not text.startswith("////"):
        return True
    return SAFETY.match(text) is not None


def check_source(source):
    violations = []
    for line, text, leading in scan_comments(source):
        if not is_allowed(text):
            violations.append((line, "comment" if leading else "comment after code"))
    return violations


def source_files(root):
    found = []
    for directory, _, names in os.walk(os.path.join(root, "src")):
        for name in names:
            if name.endswith(".kizu"):
                found.append(os.path.relpath(os.path.join(directory, name), root))
    return sorted(found)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("files", nargs="*")
    arguments = parser.parse_args(argv)
    failed = False
    for path in arguments.files or source_files(arguments.root):
        with open(os.path.join(arguments.root, path), encoding="latin-1") as source:
            for line, reason in check_source(source.read()):
                print(f"{path}:{line}: {reason}")
                failed = True
    if failed:
        print("Kizu sources carry only `///` and `// SAFETY:` comments (AGENTS.md).", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
