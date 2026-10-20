# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
#
# Standard-library tests for the ifeval-quotation-hazards audit. No third-party
# dependencies: run with `python -m unittest -v`.

import json
import os
import unicodedata
import unittest

from quote_checker import (
    is_double_quote,
    shipped_quotation,
    intended_quotation,
    nonascii_double_quote_boundaries,
    evaluate_case,
)

HERE = os.path.dirname(os.path.abspath(__file__))


def load_cases():
    with open(os.path.join(HERE, "cases.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)["cases"]


class TestMechanism(unittest.TestCase):
    def test_ascii_wrapped_passes_both(self):
        self.assertTrue(shipped_quotation('"hello"'))
        self.assertTrue(intended_quotation('"hello"'))

    def test_curly_wrapped_only_intended(self):
        txt = chr(0x201C) + "hello" + chr(0x201D)
        self.assertFalse(shipped_quotation(txt))   # shipped: no ASCII quote
        self.assertTrue(intended_quotation(txt))   # intended: double quotes
        self.assertEqual(
            nonascii_double_quote_boundaries(txt), [chr(0x201C), chr(0x201D)]
        )

    def test_unwrapped_fails_both(self):
        self.assertFalse(shipped_quotation("hello"))
        self.assertFalse(intended_quotation("hello"))

    def test_leading_trailing_whitespace_is_stripped(self):
        self.assertTrue(shipped_quotation('  "hello"  '))
        self.assertTrue(intended_quotation('  ' + chr(0x201C) + "x" + chr(0x201D)))

    def test_single_quotes_are_not_double(self):
        self.assertFalse(is_double_quote(chr(0x2018)))  # LEFT SINGLE QUOTATION MARK
        self.assertFalse(is_double_quote(chr(0x2019)))  # RIGHT SINGLE QUOTATION MARK
        self.assertFalse(is_double_quote("'"))          # APOSTROPHE


class TestUnicodeNames(unittest.TestCase):
    """Guard the design: each double-quote codepoint used is truly a double
    quotation mark per the Unicode database shipped with Python, and the single
    quotes are not."""

    def test_double_quote_codepoints(self):
        for cp in (0x0022, 0x201C, 0x201D, 0x201E, 0x00AB, 0x00BB):
            self.assertTrue(is_double_quote(chr(cp)), hex(cp))

    def test_names_contain_quotation_mark(self):
        for cp in (0x201C, 0x201D, 0x201E, 0x00AB, 0x00BB):
            self.assertIn("QUOTATION MARK", unicodedata.name(chr(cp), ""))


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
