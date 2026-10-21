# SPDX-License-Identifier: Apache-2.0
# Part of MV2's eval-reliability audits (Munim, Inc.). Made with AI.
"""Unit tests gating the GSM8K calculator-annotation census.

The census job only runs after these pass, so a miscounted fixture or a broken
evaluator stops the run before any dataset number is produced.
"""

import unittest
from collections import Counter
from fractions import Fraction

from calc_eval import (
    UnparseableExpr,
    classify_annotation,
    safe_eval,
    solution_consistency,
)
from cases import ANNOTATION_CASES, SOLUTION_CASES, TARGET


class TestAnnotationClassification(unittest.TestCase):
    def test_each_case(self):
        for expr, result, label in ANNOTATION_CASES:
            self.assertEqual(classify_annotation(expr, result), label, (expr, result))

    def test_aggregate_matches_target(self):
        counts = Counter(classify_annotation(e, r) for e, r, _ in ANNOTATION_CASES)
        for key in TARGET:
            self.assertEqual(counts[key], TARGET[key], key)


class TestSafeEvalRejectsCode(unittest.TestCase):
    def test_names_and_calls_rejected(self):
        for expr in ("sqrt(4)", "x + 1", "2 ** 3", "7 % 2", "__import__('os')"):
            with self.assertRaises(UnparseableExpr):
                safe_eval(expr)

    def test_plain_numbers(self):
        self.assertEqual(safe_eval("5"), Fraction(5))
        self.assertEqual(safe_eval(".5"), Fraction(1, 2))
        self.assertEqual(safe_eval("-2"), Fraction(-2))
        self.assertEqual(safe_eval("3.14"), Fraction(157, 50))
        self.assertEqual(safe_eval("1,000"), Fraction(1000))


class TestSolutionLevel(unittest.TestCase):
    def test_final_and_last_annotation(self):
        for answer, has_annot, matches in SOLUTION_CASES:
            res = solution_consistency(answer)
            self.assertEqual(res["has_annotation"], has_annot, answer)
            self.assertEqual(res["final_matches_last"], matches, answer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
