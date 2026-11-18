#!/usr/bin/env python3
"""Pins the rule that scripts/comment-lint/check.py enforces."""

import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check  # noqa: E402


class Allowed(unittest.TestCase):
    def test_doc_comment(self):
        self.assertEqual(check.check_source("/// Reads the file.\nfn f() -> void {}\n"), [])

    def test_safety_comment_on_its_own_line(self):
        self.assertEqual(check.check_source("// SAFETY: the view is live.\nlet a = 1;\n"), [])

    def test_safety_comment_after_code(self):
        self.assertEqual(check.check_source("let a = 1; // SAFETY: the view is live.\n"), [])

    def test_slashes_inside_a_string(self):
        self.assertEqual(check.check_source('let url = "https://example.com";\n'), [])

    def test_slashes_inside_a_string_across_lines(self):
        self.assertEqual(check.check_source('let text = "first\n// second";\n'), [])

    def test_slashes_inside_a_multiline_string_line(self):
        self.assertEqual(check.check_source("let text =\n    \\\\// kept as text\n;\n"), [])


class Rejected(unittest.TestCase):
    def test_comment_on_its_own_line(self):
        self.assertEqual(check.check_source("// explains the code\nlet a = 1;\n"), [(1, "comment")])

    def test_comment_after_code(self):
        self.assertEqual(check.check_source("let a = 1; // explains\n"), [(1, "comment after code")])

    def test_four_slashes(self):
        self.assertEqual(check.check_source("//// heading\n"), [(1, "comment")])

    def test_lowercase_safety_is_not_a_safety_comment(self):
        self.assertEqual(check.check_source("// safety: the view is live.\n"), [(1, "comment")])

    def test_line_numbers_follow_multiline_strings(self):
        self.assertEqual(check.check_source('let a = "x\ny";\n// late\n'), [(3, "comment")])


class CommandLine(unittest.TestCase):
    def test_walks_src_and_reports_a_violation(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "src", "model"))
            with open(os.path.join(root, "src", "model", "bad.kizu"), "w") as target:
                target.write("// explains\n")
            self.assertEqual(check.source_files(root), [os.path.join("src", "model", "bad.kizu")])
            self.assertEqual(check.main(["--root", root]), 1)

    def test_passes_a_clean_tree(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "src"))
            with open(os.path.join(root, "src", "good.kizu"), "w") as target:
                target.write("/// Documented.\nfn f() -> void {}\n")
            self.assertEqual(check.main(["--root", root]), 0)


if __name__ == "__main__":
    unittest.main()
