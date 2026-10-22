"""Tests for the BoolQ gold-conflict census (stdlib unittest, run in the compete lane)."""
import unittest

import cases
from boolq_gold_conflict import census, normalize, answer_of, public_summary


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        result = census(cases.FIXTURE)
        for key, expected in cases.TARGET.items():
            self.assertEqual(result[key], expected, "mismatch on %s" % key)

    def test_normalize_collapses_whitespace_and_case(self):
        self.assertEqual(normalize("  Hello   World  "), "hello world")
        self.assertEqual(normalize("A\tB\nC"), "a b c")
        self.assertEqual(normalize(None), "")

    def test_answer_of_bool(self):
        self.assertTrue(answer_of({"answer": True}))
        self.assertFalse(answer_of({"answer": False}))

    def test_answer_of_label_int(self):
        self.assertTrue(answer_of({"label": 1}))
        self.assertFalse(answer_of({"label": 0}))

    def test_answer_of_label_string(self):
        self.assertTrue(answer_of({"label": "True"}))
        self.assertFalse(answer_of({"answer": "no"}))

    def test_answer_of_raises_on_missing_or_bad(self):
        with self.assertRaises(KeyError):
            answer_of({"question": "q"})
        with self.assertRaises(ValueError):
            answer_of({"answer": 7})

    def test_duplicate_without_conflict_is_not_counted(self):
        rows = [
            {"question": "q", "passage": "p", "answer": True},
            {"question": "q", "passage": "p", "answer": True},
        ]
        r = census(rows)
        self.assertEqual(r["qp_duplicate_groups"], 1)
        self.assertEqual(r["qp_conflict_groups"], 0)
        self.assertEqual(r["question_conflict_groups"], 0)

    def test_question_only_conflict_not_counted_as_qp_conflict(self):
        rows = [
            {"question": "q", "passage": "p1", "answer": True},
            {"question": "q", "passage": "p2", "answer": False},
        ]
        r = census(rows)
        self.assertEqual(r["qp_conflict_groups"], 0)
        self.assertEqual(r["qp_duplicate_groups"], 0)
        self.assertEqual(r["question_conflict_groups"], 1)

    def test_public_summary_is_a_string(self):
        self.assertIsInstance(public_summary(census(cases.FIXTURE)), str)


if __name__ == "__main__":
    unittest.main()
