"""Tests for the QASC composition->answer lexical-leakage census (stdlib unittest)."""
import unittest

import cases
from qasc_leakage import normalize, parse_row, leakage_stats, flatten


def _parse(fixture):
    return [parse_row(obj) for obj in fixture]


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        stats = leakage_stats(_parse(cases.FIXTURE))
        flat = flatten(stats)
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_coverage_rates(self):
        stats = leakage_stats(_parse(cases.FIXTURE))
        self.assertAlmostEqual(stats["gold_rate_fact1"], 2.0 / 3.0)
        self.assertAlmostEqual(stats["gold_rate_fact2"], 0.0)
        self.assertAlmostEqual(stats["gold_rate_combinedfact"], 1.0)
        self.assertAlmostEqual(stats["dist_rate_combinedfact"], 0.0)
        # headline orderings the predictions bet on
        self.assertGreater(stats["gold_rate_combinedfact"], stats["dist_rate_combinedfact"])
        self.assertGreater(stats["gold_rate_combinedfact"], stats["gold_rate_fact1"])
        self.assertGreater(stats["gold_rate_combinedfact"], stats["gold_rate_fact2"])

    def test_normalize_collapses_whitespace_and_case(self):
        self.assertEqual(normalize("  The   WIND "), "the wind")
        self.assertEqual(normalize(None), "")

    def test_parse_nested_shape(self):
        r = parse_row(cases.FIXTURE[0])
        self.assertEqual(r["gold_text"], "wind")
        self.assertEqual(r["distractor_texts"], ["sun", "rain"])
        self.assertEqual(r["facts"]["combinedfact"], "wind can make electricity")
        self.assertTrue(r["annotated"])

    def test_parse_hf_struct_of_lists_shape(self):
        obj = {"question": "what blows?",
               "choices": {"text": ["wind", "sun", "rain"], "label": ["A", "B", "C"]},
               "answerKey": "A", "fact1": "x", "fact2": "y", "combinedfact": "wind blows"}
        r = parse_row(obj)
        self.assertEqual(r["gold_text"], "wind")
        self.assertEqual(r["distractor_texts"], ["sun", "rain"])
        self.assertTrue(r["annotated"])

    def test_parse_flat_list_shape(self):
        obj = {"question": "q",
               "choices": [{"text": "wind", "label": "A"}, {"text": "sun", "label": "B"}],
               "answerKey": "B", "fact1": "x", "fact2": "y", "combinedfact": "z"}
        r = parse_row(obj)
        self.assertEqual(r["gold_text"], "sun")
        self.assertEqual(r["distractor_texts"], ["wind"])

    def test_unannotated_row_skipped(self):
        r = parse_row(cases.FIXTURE[3])
        self.assertFalse(r["annotated"])
        stats = leakage_stats([r])
        self.assertEqual(stats["n_unannotated"], 1)
        self.assertEqual(stats["n_valid"], 0)

    def test_malformed_when_answerkey_matches_no_choice(self):
        r = parse_row(cases.FIXTURE[4])
        self.assertTrue(r["annotated"])
        self.assertIsNone(r["gold_text"])
        stats = leakage_stats([r])
        self.assertEqual(stats["n_malformed"], 1)
        self.assertEqual(stats["n_valid"], 0)

    def test_gold_in_field_is_substring_not_token(self):
        # gold "ice" is a substring of "price" -> counts; documents the substring semantics.
        obj = {"question": "q",
               "choices": [{"text": "ice", "label": "A"}, {"text": "x", "label": "B"}],
               "answerKey": "A", "fact1": "the price was high", "fact2": "", "combinedfact": ""}
        stats = leakage_stats([parse_row(obj)])
        self.assertEqual(stats["gold_in_fact1"], 1)

    def test_combined_not_single_counts_composition_only_leak(self):
        stats = leakage_stats(_parse(cases.FIXTURE))
        self.assertEqual(stats["n_gold_in_combined_not_single"], 1)
        self.assertEqual(stats["n_gold_in_either_single"], 2)

    def test_examples_capture_composition_only_leaks(self):
        stats = leakage_stats(_parse(cases.FIXTURE))
        golds = {e["gold"] for e in stats["examples"]}
        self.assertEqual(golds, {"ice"})

    def test_empty_gold_never_counts(self):
        obj = {"question": "q",
               "choices": [{"text": "", "label": "A"}, {"text": "x", "label": "B"}],
               "answerKey": "A", "fact1": "anything at all", "fact2": "", "combinedfact": "anything"}
        stats = leakage_stats([parse_row(obj)])
        self.assertEqual(stats["gold_in_fact1"], 0)
        self.assertEqual(stats["gold_in_combinedfact"], 0)
        self.assertEqual(stats["n_valid"], 1)


if __name__ == "__main__":
    unittest.main()
