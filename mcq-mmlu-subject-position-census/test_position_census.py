"""Tests for the MCQ gold-answer-POSITION census core (audit 54). Standard library unittest only.

The census core and its hand-traced fixture are reused verbatim from audit 53. These tests check the fixture
for EXACT equality against the TARGET, then verify the derived report values (chi-square statistic,
best-constant-position accuracy, modal selection and coverage) that job.py relies on.
"""

import unittest
from fractions import Fraction

import position_census as pc
import cases


class TestFixtureExact(unittest.TestCase):
    def test_run_census_equals_target(self):
        got = pc.run_census(cases.FIXTURE_ROWS)
        self.assertEqual(got, cases.TARGET)

    def test_validity_classification(self):
        self.assertEqual(pc.question_validity(["A", "B", "C", "D"], ["w", "x", "y", "z"], "A"), "valid")
        self.assertEqual(pc.question_validity(["A", "B", "C", "D"], ["w", "x", "y", "z"], "Z"), "bad_key")
        self.assertEqual(pc.question_validity(["A", "A", "C"], ["w", "x", "y"], "C"), "degenerate")  # dup label
        self.assertEqual(pc.question_validity(["A"], ["x"], "A"), "degenerate")                      # single
        self.assertEqual(pc.question_validity(["A", "B", "C"], ["w", "x"], "A"), "degenerate")        # len mismatch
        self.assertEqual(pc.question_validity(None, None, "A"), "degenerate")


class TestReport(unittest.TestCase):
    def setUp(self):
        self.rep = pc.to_report(pc.run_census(cases.FIXTURE_ROWS))

    def test_modal_selection_and_coverage(self):
        e = self.rep["exam4"]
        self.assertEqual(e["modal_option_count"], 4)          # k=4 (n=4) beats k=3 (n=1)
        self.assertEqual(e["n_valid"], 5)
        self.assertEqual(e["n_bad_key"], 1)
        self.assertAlmostEqual(e["modal_coverage"], 4 / 5)
        self.assertEqual(e["option_count_hist"], {"3": 1, "4": 4})

    def test_exam4_modal_stats(self):
        m = self.rep["exam4"]["modal"]
        self.assertEqual(m["n"], 4)
        self.assertEqual(m["pos_counts"], {"0": 2, "1": 0, "2": 1, "3": 1})
        self.assertEqual(m["best_position"], 0)
        self.assertEqual(m["best_position_count"], 2)
        self.assertAlmostEqual(m["best_position_accuracy"], 0.5)
        self.assertEqual(m["best_position_accuracy_exact"], str(Fraction(1, 2)))
        self.assertAlmostEqual(m["chance_accuracy"], 0.25)
        self.assertAlmostEqual(m["best_minus_chance"], 0.25)
        # exp = 4/4 = 1; stat = (2-1)^2 + (0-1)^2 + (1-1)^2 + (1-1)^2 = 2.0
        self.assertAlmostEqual(m["chi_square_stat"], 2.0)
        self.assertEqual(m["df"], 3)
        self.assertEqual(m["uniform_rejected_0.001"], False)

    def test_crowd5_modal_stats(self):
        m = self.rep["crowd5"]["modal"]
        self.assertEqual(m["n"], 2)
        self.assertEqual(m["pos_counts"], {"0": 0, "1": 0, "2": 0, "3": 0, "4": 2})
        self.assertEqual(m["best_position"], 4)
        self.assertAlmostEqual(m["best_position_accuracy"], 1.0)
        self.assertAlmostEqual(m["chance_accuracy"], 0.2)
        self.assertAlmostEqual(m["best_minus_chance"], 0.8)
        # exp = 2/5 = 0.4; stat = 4*(0-0.4)^2/0.4 + (2-0.4)^2/0.4 = 4*0.4 + 6.4 = 8.0
        self.assertAlmostEqual(m["chi_square_stat"], 8.0)
        self.assertEqual(m["df"], 4)
        self.assertEqual(m["uniform_rejected_0.001"], False)

    def test_chi_square_rejects_a_strong_skew(self):
        # 400 questions all with gold at position 0 over 4 options -> extreme skew, must reject at 0.001.
        rows = [("x", ["A", "B", "C", "D"], ["a", "b", "c", "d"], "A") for _ in range(400)]
        m = pc.to_report(pc.run_census(rows))["x"]["modal"]
        self.assertEqual(m["uniform_rejected_0.001"], True)
        self.assertAlmostEqual(m["best_position_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
