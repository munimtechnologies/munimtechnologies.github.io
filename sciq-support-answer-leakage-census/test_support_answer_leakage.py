"""Tests for the SciQ support->answer lexical-leakage census (stdlib unittest)."""
import unittest

import cases
from support_answer_leakage import normalize, parse_row, support_answer_stats, flatten


def _parse(fixture):
    return [parse_row(obj) for obj in fixture]


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        stats = support_answer_stats(_parse(cases.FIXTURE))
        flat = flatten(stats)
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_coverage_rates(self):
        stats = support_answer_stats(_parse(cases.FIXTURE))
        self.assertAlmostEqual(stats["gold_coverage_rate"], 2.0 / 3.0)
        self.assertAlmostEqual(stats["distractor_coverage_rate"], 1.0 / 9.0)
        self.assertGreater(stats["gold_coverage_rate"], stats["distractor_coverage_rate"])

    def test_normalize_collapses_whitespace_and_case(self):
        self.assertEqual(normalize("  The   SKY "), "the sky")
        self.assertEqual(normalize(None), "")

    def test_parse_reads_gold_distractors_and_support(self):
        r = parse_row(cases.FIXTURE[0])
        self.assertEqual(r["gold_text"], "water")
        self.assertEqual(r["distractor_texts"], ["fire", "earth", "air"])
        self.assertEqual(r["support"], "water is a liquid that flows")
        self.assertFalse(r["malformed"])

    def test_malformed_when_no_correct_answer_key(self):
        r = parse_row(cases.FIXTURE[4])
        self.assertTrue(r["malformed"])
        self.assertIsNone(r["gold_text"])

    def test_empty_support_counted_and_excluded_from_rates(self):
        stats = support_answer_stats(_parse(cases.FIXTURE))
        self.assertEqual(stats["n_empty_support"], 1)
        self.assertEqual(stats["n_with_support"], 3)
        # the empty-support row's distractors are not counted
        self.assertEqual(stats["n_distractors_total"], 9)

    def test_gold_in_support_is_substring_not_token(self):
        # gold "ice" is a substring of "price" -> counts; documents the substring semantics.
        obj = {"question": "q", "correct_answer": "ice",
               "distractor1": "x", "distractor2": "y", "distractor3": "z",
               "support": "the price was high"}
        stats = support_answer_stats([parse_row(obj)])
        self.assertEqual(stats["n_gold_in_support"], 1)

    def test_distractor_in_support_counted(self):
        stats = support_answer_stats(_parse(cases.FIXTURE))
        self.assertEqual(stats["n_any_distractor_in_support"], 1)
        self.assertEqual(stats["total_distractor_in_support"], 1)

    def test_examples_capture_gold_leaks(self):
        stats = support_answer_stats(_parse(cases.FIXTURE))
        golds = {e["gold"] for e in stats["examples"]}
        self.assertEqual(golds, {"water", "ice"})

    def test_empty_gold_never_counts_as_in_support(self):
        obj = {"question": "q", "correct_answer": "",
               "distractor1": "a", "distractor2": "b", "distractor3": "c",
               "support": "anything at all"}
        stats = support_answer_stats([parse_row(obj)])
        self.assertEqual(stats["n_gold_in_support"], 0)
        self.assertEqual(stats["n_with_support"], 1)

    def test_support_equals_choice_detection(self):
        obj = {"question": "q", "correct_answer": "mercury",
               "distractor1": "venus", "distractor2": "mars", "distractor3": "earth",
               "support": "mercury"}
        stats = support_answer_stats([parse_row(obj)])
        self.assertEqual(stats["n_support_eq_a_choice"], 1)


if __name__ == "__main__":
    unittest.main()
