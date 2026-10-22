"""Tests for the CommonsenseQA gold-conflict census (stdlib unittest, run in compete)."""
import unittest

import cases
from commonsenseqa_gold_conflict import (
    census, normalize, gold_text, stem_of, choice_texts, public_summary,
)


def _q(stem, choices, answer_label):
    return {"answerKey": answer_label,
            "question": {"stem": stem,
                         "choices": [{"label": l, "text": t} for l, t in choices]}}


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        result = census(cases.FIXTURE)
        for key, expected in cases.TARGET.items():
            self.assertEqual(result[key], expected, "mismatch on %s" % key)

    def test_normalize_collapses_whitespace_and_case(self):
        self.assertEqual(normalize("  Hello   World  "), "hello world")
        self.assertEqual(normalize("A\tB\nC"), "a b c")
        self.assertEqual(normalize(None), "")

    def test_gold_text_returns_chosen_option_text(self):
        row = _q("q", [("A", "alpha"), ("B", "beta")], "B")
        self.assertEqual(gold_text(row), "beta")
        self.assertEqual(stem_of(row), "q")
        self.assertEqual(choice_texts(row), ["alpha", "beta"])

    def test_gold_text_raises_on_missing_or_bad(self):
        with self.assertRaises(KeyError):
            gold_text({"question": {"stem": "q", "choices": [{"label": "A", "text": "a"}]}})
        with self.assertRaises(ValueError):
            gold_text(_q("q", [("A", "a"), ("B", "b")], "Z"))

    def test_option_order_does_not_create_a_conflict(self):
        # Same stem, same option set in different order, same correct TEXT -> not a conflict.
        rows = [
            _q("q", [("A", "a"), ("B", "b")], "A"),
            _q("q", [("A", "b"), ("B", "a")], "B"),
        ]
        r = census(rows)
        self.assertEqual(r["item_conflict_groups"], 0)
        self.assertEqual(r["item_duplicate_groups"], 1)
        self.assertEqual(r["stem_duplicate_groups"], 1)

    def test_duplicate_without_conflict_is_not_counted(self):
        rows = [
            _q("q", [("A", "a"), ("B", "b")], "A"),
            _q("q", [("A", "a"), ("B", "b")], "A"),
        ]
        r = census(rows)
        self.assertEqual(r["item_duplicate_groups"], 1)
        self.assertEqual(r["item_conflict_groups"], 0)

    def test_stem_reuse_with_different_options_is_context_not_conflict(self):
        rows = [
            _q("q", [("A", "a"), ("B", "b")], "A"),
            _q("q", [("A", "c"), ("B", "d")], "B"),
        ]
        r = census(rows)
        self.assertEqual(r["item_conflict_groups"], 0)
        self.assertEqual(r["item_duplicate_groups"], 0)
        self.assertEqual(r["stem_duplicate_groups"], 1)

    def test_normalized_only_conflict(self):
        rows = [
            _q("Q", [("A", "Red"), ("B", "Blue")], "A"),
            _q("Q", [("A", "red "), ("B", "blue")], "B"),
        ]
        r = census(rows)
        self.assertEqual(r["item_conflict_groups"], 0)
        self.assertEqual(r["norm_item_conflict_groups"], 1)
        self.assertEqual(r["norm_additional"], 1)

    def test_public_summary_is_a_string(self):
        self.assertIsInstance(public_summary(census(cases.FIXTURE)), str)


if __name__ == "__main__":
    unittest.main()
