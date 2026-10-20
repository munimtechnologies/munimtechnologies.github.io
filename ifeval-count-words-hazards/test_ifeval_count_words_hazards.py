# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
#
# Standard-library tests for the ifeval-count-words-hazards audit. Run with:
#     python -m unittest -v

import json
import os
import re
import unittest

from count_words_audit import (
    count_words_ifeval,
    count_words_whitespace,
    number_words_pass,
    evaluate_case,
)

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_cases():
    with open(os.path.join(HERE, "cases.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)["cases"]


class CounterBehaviour(unittest.TestCase):
    def test_ifeval_matches_regexp_tokenizer_semantics(self):
        # IFEval uses nltk RegexpTokenizer(r"\w+"); for str that equals
        # re.findall(r"\w+", text). Lock that equivalence on varied text.
        for text in [
            "don't", "state-of-the-art", "3.14", "U.S.A.",
            "plain words here", "emoji \U0001f389 only", "", "   ",
        ]:
            self.assertEqual(
                count_words_ifeval(text), len(re.findall(r"\w+", text))
            )

    def test_known_counts(self):
        self.assertEqual(count_words_ifeval("don't"), 2)         # don, t
        self.assertEqual(count_words_whitespace("don't"), 1)
        self.assertEqual(count_words_ifeval("U.S.A."), 3)        # U, S, A
        self.assertEqual(count_words_whitespace("U.S.A."), 1)
        self.assertEqual(count_words_ifeval("max_retries"), 1)   # underscore is \w
        self.assertEqual(count_words_whitespace("max_retries"), 1)

    def test_number_words_pass(self):
        self.assertTrue(number_words_pass(5, 5, "at least"))
        self.assertFalse(number_words_pass(4, 5, "at least"))
        self.assertTrue(number_words_pass(4, 5, "less than"))
        self.assertFalse(number_words_pass(5, 5, "less than"))
        with self.assertRaises(ValueError):
            number_words_pass(5, 5, "exactly")


class HandCases(unittest.TestCase):
    def test_all_cases_reproduce(self):
        for case in _load_cases():
            c_if, c_ws, v_if, v_ws, flip = evaluate_case(case)
            self.assertEqual(c_if, case["expected_count_ifeval"], case["id"])
            self.assertEqual(c_ws, case["expected_count_ws"], case["id"])
            self.assertEqual(
                "PASS" if v_if else "FAIL", case["expected_verdict_ifeval"], case["id"]
            )
            self.assertEqual(
                "PASS" if v_ws else "FAIL", case["expected_verdict_ws"], case["id"]
            )
            self.assertEqual(flip, case["expected_flip"], case["id"])

    def test_flip_count_matches_manifest(self):
        cases = _load_cases()
        flips = sum(1 for c in cases if evaluate_case(c)[4])
        expected = sum(1 for c in cases if c["expected_flip"])
        self.assertEqual(flips, expected)
        self.assertEqual(flips, 5)  # W1,W2,W3,W4,W6 flip; W5 is the control


if __name__ == "__main__":
    unittest.main()
