"""Standard-library unit tests for the MCQ gold-answer-length census, run before any real data is read."""

import unittest
from fractions import Fraction

import gold_length as gl
import cases


class TestLengthFunctions(unittest.TestCase):
    def test_strip_and_count(self):
        self.assertEqual(gl.char_len("  abc  "), 3)
        self.assertEqual(gl.char_len(""), 0)
        self.assertEqual(gl.char_len(None), 0)
        self.assertEqual(gl.token_len("  one two  three "), 3)
        self.assertEqual(gl.token_len("word"), 1)
        self.assertEqual(gl.token_len(""), 0)


class TestValidity(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(gl.question_validity(["A", "B"], ["x", "y"], "A"), "valid")

    def test_bad_key(self):
        self.assertEqual(gl.question_validity(["A", "B"], ["x", "y"], "Z"), "bad_key")

    def test_degenerate_single_option(self):
        self.assertEqual(gl.question_validity(["A"], ["x"], "A"), "degenerate")

    def test_degenerate_length_mismatch(self):
        self.assertEqual(gl.question_validity(["A", "B"], ["x"], "A"), "degenerate")

    def test_degenerate_duplicate_labels(self):
        self.assertEqual(gl.question_validity(["A", "A"], ["x", "y"], "A"), "degenerate")


class TestPerQuestion(unittest.TestCase):
    def test_unique_longest(self):
        r = gl._per_question(["A", "B", "C"], ["aa", "bbbb", "c"], "B", gl.char_len)
        self.assertEqual(r["gold"], 4)
        self.assertEqual(r["unique_longest"], 1)
        self.assertEqual(r["unique_shortest"], 0)
        self.assertEqual(r["longest_credit"], Fraction(1))

    def test_tie_longest_credit(self):
        r = gl._per_question(["A", "B"], ["xxxx", "yyyy"], "A", gl.char_len)
        self.assertEqual(r["unique_longest"], 0)
        self.assertEqual(r["longest_credit"], Fraction(1, 2))

    def test_unique_shortest(self):
        r = gl._per_question(["A", "B"], ["a", "bbb"], "A", gl.char_len)
        self.assertEqual(r["unique_shortest"], 1)
        self.assertEqual(r["shortest_credit"], Fraction(1))


class TestFixtureCensus(unittest.TestCase):
    def test_matches_hand_traced_target(self):
        got = gl.run_census(cases.FIXTURE_ROWS)
        self.assertEqual(got, cases.TARGET)

    def test_report_and_predictions_shapes(self):
        rep = gl.to_report(gl.run_census(cases.FIXTURE_ROWS))
        # alpha has char length bias; beta does not (gold shorter on average)
        self.assertGreater(rep["alpha"]["char"]["mean_gold_len"], rep["alpha"]["char"]["mean_distractor_len"])
        self.assertLess(rep["beta"]["char"]["mean_gold_len"], rep["beta"]["char"]["mean_distractor_len"])
        # chance baseline for alpha = (13/12)/4 = 13/48
        self.assertAlmostEqual(rep["alpha"]["chance_accuracy"], 13.0 / 48.0)
        # predictions on the fixture: P1 fails (beta has bad_key + degenerate), P3 fails (beta gold shorter)
        preds = gl.predictions(rep)
        self.assertFalse(preds["P1_clean_parse_every_benchmark"])
        self.assertFalse(preds["P3_mean_gold_longer_than_distractors_every_benchmark"])


if __name__ == "__main__":
    unittest.main()
