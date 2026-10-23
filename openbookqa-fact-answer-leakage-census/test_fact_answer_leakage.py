"""Tests for the OpenBookQA fact->answer lexical-leakage census (stdlib unittest)."""
import unittest

import cases
from fact_answer_leakage import normalize, parse_row, fact_answer_stats, flatten


def _parse(fixture):
    return [parse_row(obj) for obj in fixture]


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        stats = fact_answer_stats(_parse(cases.FIXTURE))
        flat = flatten(stats)
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_coverage_rates(self):
        stats = fact_answer_stats(_parse(cases.FIXTURE))
        self.assertAlmostEqual(stats["gold_coverage_rate"], 0.5)
        self.assertAlmostEqual(stats["distractor_coverage_rate"], 0.25)
        self.assertGreater(stats["gold_coverage_rate"], stats["distractor_coverage_rate"])

    def test_normalize_collapses_whitespace_and_case(self):
        self.assertEqual(normalize("  The   SKY "), "the sky")
        self.assertEqual(normalize(None), "")

    def test_parse_reads_gold_distractors_and_fact(self):
        r = parse_row(cases.FIXTURE[0])
        self.assertEqual(r["id"], "q1")
        self.assertEqual(r["gold_text"], "water")
        self.assertEqual(r["distractor_texts"], ["fire"])
        self.assertEqual(r["fact"], "water is wet and water flows")
        self.assertFalse(r["malformed"])

    def test_malformed_when_answerkey_matches_no_label(self):
        r = parse_row(cases.FIXTURE[3])
        self.assertTrue(r["malformed"])
        self.assertIsNone(r["gold_text"])
        self.assertEqual(r["distractor_texts"], [])

    def test_parse_accepts_flat_hf_shape(self):
        obj = {"id": "z", "question_stem": "What?",
               "choices": {"text": ["Water", "Fire"], "label": ["A", "B"]},
               "answerKey": "A", "fact1": "WATER is clear"}
        r = parse_row(obj)
        self.assertEqual(r["gold_text"], "water")
        self.assertEqual(r["distractor_texts"], ["fire"])
        self.assertEqual(r["fact"], "water is clear")

    def test_gold_in_fact_is_substring_not_token(self):
        # gold "ice" is a substring of "price" -> counts; this documents the substring semantics.
        obj = {"id": "p", "question": {"stem": "s",
               "choices": [{"text": "ice", "label": "A"}, {"text": "x", "label": "B"}]},
               "answerKey": "A", "fact1": "the price was high"}
        stats = fact_answer_stats([parse_row(obj)])
        self.assertEqual(stats["n_gold_in_fact"], 1)

    def test_fact_equals_choice_detection(self):
        stats = fact_answer_stats(_parse(cases.FIXTURE))
        self.assertEqual(stats["n_fact_eq_a_choice"], 1)
        self.assertEqual(stats["n_fact_eq_gold_choice"], 1)

    def test_examples_capture_gold_leaks(self):
        stats = fact_answer_stats(_parse(cases.FIXTURE))
        ids = {e["id"] for e in stats["examples"]}
        self.assertEqual(ids, {"q1", "q3"})

    def test_empty_gold_text_never_counts_as_in_fact(self):
        obj = {"id": "e", "question": {"stem": "s",
               "choices": [{"text": "", "label": "A"}, {"text": "y", "label": "B"}]},
               "answerKey": "A", "fact1": "anything at all"}
        stats = fact_answer_stats([parse_row(obj)])
        self.assertEqual(stats["n_gold_in_fact"], 0)


if __name__ == "__main__":
    unittest.main()
