"""Tests for the PIQA gold-conflict census (stdlib unittest, run in the compete lane)."""
import unittest

import cases
from piqa_gold_conflict import census, normalize, label_of, public_summary


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        result = census(cases.FIXTURE)
        for key, expected in cases.TARGET.items():
            self.assertEqual(result[key], expected, "mismatch on %s" % key)

    def test_normalize_collapses_whitespace_and_case(self):
        self.assertEqual(normalize("  Hello   World  "), "hello world")
        self.assertEqual(normalize("A\tB\nC"), "a b c")
        self.assertEqual(normalize(None), "")

    def test_label_of_int(self):
        self.assertEqual(label_of({"label": 0}), 0)
        self.assertEqual(label_of({"label": 1}), 1)

    def test_label_of_string(self):
        self.assertEqual(label_of({"label": "0"}), 0)
        self.assertEqual(label_of({"label": " 1 "}), 1)

    def test_label_of_raises_on_missing_or_bad(self):
        with self.assertRaises(KeyError):
            label_of({"goal": "g"})
        with self.assertRaises(ValueError):
            label_of({"label": 2})
        with self.assertRaises(ValueError):
            label_of({"label": "yes"})

    def test_duplicate_without_conflict_is_not_counted(self):
        rows = [
            {"goal": "g", "sol1": "a", "sol2": "b", "label": 0},
            {"goal": "g", "sol1": "a", "sol2": "b", "label": 0},
        ]
        r = census(rows)
        self.assertEqual(r["triple_duplicate_groups"], 1)
        self.assertEqual(r["triple_conflict_groups"], 0)
        self.assertEqual(r["goal_duplicate_groups"], 1)

    def test_goal_reuse_not_counted_as_triple_conflict(self):
        rows = [
            {"goal": "g", "sol1": "a", "sol2": "b", "label": 0},
            {"goal": "g", "sol1": "c", "sol2": "d", "label": 1},
        ]
        r = census(rows)
        self.assertEqual(r["triple_conflict_groups"], 0)
        self.assertEqual(r["triple_duplicate_groups"], 0)
        self.assertEqual(r["goal_duplicate_groups"], 1)

    def test_normalized_only_conflict(self):
        rows = [
            {"goal": "g", "sol1": "Twist Left", "sol2": "d", "label": 0},
            {"goal": "g", "sol1": "twist left ", "sol2": "d", "label": 1},
        ]
        r = census(rows)
        self.assertEqual(r["triple_conflict_groups"], 0)
        self.assertEqual(r["norm_triple_conflict_groups"], 1)
        self.assertEqual(r["norm_additional"], 1)

    def test_public_summary_is_a_string(self):
        self.assertIsInstance(public_summary(census(cases.FIXTURE)), str)


if __name__ == "__main__":
    unittest.main()
