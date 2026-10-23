"""Tests for the SNLI annotator-agreement / gold-derivation census (stdlib unittest)."""
import unittest

import cases
from snli_agreement import strict_majority, parse_row, agreement_stats, flatten


def _parse(fixture):
    return [parse_row(obj) for obj in fixture]


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        stats = agreement_stats(_parse(cases.FIXTURE))
        flat = flatten(stats)
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_strict_majority(self):
        self.assertIsNone(strict_majority([]))
        self.assertEqual(strict_majority(["entailment"]), "entailment")
        self.assertEqual(strict_majority(["a", "a", "b"]), "a")          # 2/3
        self.assertIsNone(strict_majority(["a", "b"]))                    # 1-1 tie, no majority
        self.assertIsNone(strict_majority(["a", "a", "b", "b", "c"]))     # 2-2-1, no majority
        self.assertEqual(strict_majority(["a", "a", "a", "b", "c"]), "a")  # 3/5

    def test_parse_row_extracts_fields(self):
        r = parse_row(cases.FIXTURE[1])
        self.assertEqual(r["gold"], "neutral")
        self.assertEqual(r["annotators"], ["neutral", "neutral", "entailment", "neutral", "contradiction"])

    def test_parse_row_missing_annotators(self):
        r = parse_row({"gold_label": "entailment"})
        self.assertEqual(r["annotators"], [])
        stats = agreement_stats([r])
        self.assertEqual(stats["n_no_annotators"], 1)
        self.assertEqual(stats["n_labeled_without_majority"], 1)  # no annotators -> no majority

    def test_mismatch_counted_and_captured(self):
        stats = agreement_stats(_parse(cases.FIXTURE))
        self.assertEqual(stats["n_gold_mismatch_majority"], 1)
        self.assertEqual(len(stats["examples_mismatch"]), 1)
        self.assertEqual(stats["examples_mismatch"][0]["gold"], "entailment")
        self.assertEqual(stats["examples_mismatch"][0]["majority"], "neutral")

    def test_no_consensus_without_majority_is_clean(self):
        stats = agreement_stats(_parse(cases.FIXTURE))
        self.assertEqual(stats["n_no_consensus"], 1)
        self.assertEqual(stats["n_no_consensus_with_majority"], 0)

    def test_no_consensus_with_majority_flagged(self):
        # a synthetic "-" row that actually has a 3/5 majority -> filter anomaly
        obj = {"gold_label": "-",
               "annotator_labels": ["entailment", "entailment", "entailment", "neutral", "contradiction"]}
        stats = agreement_stats([parse_row(obj)])
        self.assertEqual(stats["n_no_consensus"], 1)
        self.assertEqual(stats["n_no_consensus_with_majority"], 1)

    def test_multi_and_unanimous_counts(self):
        stats = agreement_stats(_parse(cases.FIXTURE))
        self.assertEqual(stats["n_multi"], 4)
        self.assertEqual(stats["n_unanimous_multi"], 1)

    def test_agreement_hist(self):
        stats = agreement_stats(_parse(cases.FIXTURE))
        self.assertEqual(stats["agreement_hist"], {"1": 1, "3": 1, "5": 3})

    def test_single_label_row_matches(self):
        stats = agreement_stats([parse_row(cases.FIXTURE[0])])
        self.assertEqual(stats["n_gold_matches_majority"], 1)
        self.assertEqual(stats["n_gold_mismatch_majority"], 0)
        self.assertEqual(stats["n_labeled_without_majority"], 0)


if __name__ == "__main__":
    unittest.main()
