"""Tests for the SNLI per-gold-label annotator-agreement census (stdlib unittest)."""
import unittest

import cases
from label_census import (
    norm_label, strict_majority_of_labels, agreement_count, census, flatten,
    unanimous_rate, individual_agreement_rate, aggregate_individual_agreement, LABELS,
)


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        flat = flatten(census(cases.FIXTURE))
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_per_label_n_sums_to_valid(self):
        flat = flatten(census(cases.FIXTURE))
        total = flat["e_n"] + flat["n_n"] + flat["c_n"]
        self.assertEqual(total, flat["n_valid"])
        self.assertEqual(flat["n_valid"] + flat["n_dash"], flat["n_total"])

    def test_norm_label(self):
        self.assertEqual(norm_label("entailment"), "e")
        self.assertEqual(norm_label("NEUTRAL"), "n")
        self.assertEqual(norm_label("c"), "c")
        self.assertIsNone(norm_label("-"))
        self.assertIsNone(norm_label(""))
        self.assertIsNone(norm_label(None))

    def test_strict_majority_of_labels(self):
        self.assertEqual(strict_majority_of_labels(["e", "e", "e", "n", "c"]), "e")
        self.assertEqual(strict_majority_of_labels(["n", "n", "n", "n", "e"]), "n")
        self.assertIsNone(strict_majority_of_labels(["e", "e", "n", "n", "c"]))
        self.assertIsNone(strict_majority_of_labels([]))

    def test_agreement_count(self):
        self.assertEqual(agreement_count(["e", "e", "e", "e", "e"], "entailment"), 5)
        self.assertEqual(agreement_count(["n", "n", "n", "e", "c"], "n"), 3)
        self.assertIsNone(agreement_count(["e", "n", "c"], "-"))

    def test_rates_on_fixture(self):
        stats = census(cases.FIXTURE)
        self.assertEqual(unanimous_rate(stats, "e"), 0.5)
        self.assertEqual(unanimous_rate(stats, "n"), 0.0)
        self.assertEqual(unanimous_rate(stats, "c"), 1.0)
        self.assertEqual(individual_agreement_rate(stats, "e"), 0.8)
        self.assertEqual(individual_agreement_rate(stats, "n"), 0.7)
        self.assertEqual(individual_agreement_rate(stats, "c"), 1.0)
        # P2 shape: neutral is less often unanimous than entailment.
        self.assertLess(unanimous_rate(stats, "n"), unanimous_rate(stats, "e"))

    def test_aggregate_individual_agreement(self):
        stats = census(cases.FIXTURE)
        # (8 + 7 + 5) agreeing of (10 + 10 + 5) individual labels = 20/25 = 0.8.
        self.assertEqual(aggregate_individual_agreement(stats), 0.8)

    def test_gold_eq_majority_by_construction(self):
        stats = census(cases.FIXTURE)
        for L in LABELS:
            cell = stats["per_label"][L]
            self.assertEqual(cell["gold_eq_majority"], cell["n"])

    def test_metadata(self):
        self.assertEqual(cases.MIN_UNANIMOUS_SPREAD, 0.05)
        self.assertEqual(cases.EXPECTED_TOTAL_ROWS, 20000)
        self.assertEqual(cases.SNLI_MEMBERS, ("snli_1.0_dev.jsonl", "snli_1.0_test.jsonl"))


if __name__ == "__main__":
    unittest.main()
