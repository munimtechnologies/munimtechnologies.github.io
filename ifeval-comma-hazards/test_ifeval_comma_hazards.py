# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
#
# Standard-library tests for the ifeval-comma-hazards audit. No third-party
# dependencies: run with `python -m unittest -v`.

import json
import os
import unicodedata
import unittest

from comma_checker import (
    ifeval_no_comma,
    intended_no_comma,
    has_any_comma,
    comma_chars,
    nonascii_comma_chars,
    evaluate_case,
)

HERE = os.path.dirname(os.path.abspath(__file__))


def load_cases():
    with open(os.path.join(HERE, "cases.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)["cases"]


class TestMechanism(unittest.TestCase):
    def test_ascii_comma_detected_by_both(self):
        self.assertFalse(ifeval_no_comma("a,b"))
        self.assertFalse(intended_no_comma("a,b"))

    def test_fullwidth_comma_only_caught_by_intended(self):
        txt = "a" + chr(0xFF0C) + "b"
        self.assertTrue(ifeval_no_comma(txt))       # shipped: no ASCII comma
        self.assertFalse(intended_no_comma(txt))    # intended: comma present
        self.assertEqual(nonascii_comma_chars(txt), [chr(0xFF0C)])

    def test_plain_text_has_no_comma(self):
        self.assertTrue(ifeval_no_comma("a b c"))
        self.assertTrue(intended_no_comma("a b c"))
        self.assertEqual(comma_chars("a b c"), [])


class TestUnicodeNames(unittest.TestCase):
    """Guard the design: every non-ASCII comma used in cases.json must truly be
    named '... COMMA ...' by the Unicode database shipped with Python."""

    def test_codepoints_are_named_comma(self):
        for cp in (0xFF0C, 0x3001, 0x060C, 0x002C):
            self.assertIn("COMMA", unicodedata.name(chr(cp), ""))


class TestCases(unittest.TestCase):
    def test_all_cases_reproduce(self):
        cases = load_cases()
        self.assertEqual(len(cases), 6)
        n_flip = 0
        for c in cases:
            shipped, intended, flip = evaluate_case(c)
            self.assertEqual(shipped, c["expected_shipped_pass"], c["id"])
            self.assertEqual(intended, c["expected_intended_pass"], c["id"])
            self.assertEqual(flip, c["expected_flip"], c["id"])
            if flip:
                n_flip += 1
        self.assertEqual(n_flip, 4)


if __name__ == "__main__":
    unittest.main()
