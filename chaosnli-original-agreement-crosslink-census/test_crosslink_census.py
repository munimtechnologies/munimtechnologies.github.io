"""Tests for the ChaosNLI x original-agreement cross-link census (stdlib unittest)."""
import unittest

import cases
from crosslink_census import (
    norm_label, plurality, strict_majority, agreement_count, census, flatten,
    no_strict_rate, old_flip_rate,
)


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        flat = flatten(census(cases.FIXTURE))
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_bucket_n_sums_to_joined(self):
        flat = flatten(census(cases.FIXTURE))
        total = flat["b5_n"] + flat["b4_n"] + flat["b3_n"] + flat["bdash_n"] + flat["bother_n"]
        self.assertEqual(total, flat["n_joined"])

    def test_norm_label(self):
        self.assertEqual(norm_label("entailment"), "e")
        self.assertEqual(norm_label("NEUTRAL"), "n")
        self.assertEqual(norm_label("c"), "c")
        self.assertIsNone(norm_label("-"))
        self.assertIsNone(norm_label(""))
        self.assertIsNone(norm_label(None))

    def test_agreement_count(self):
        self.assertEqual(agreement_count(["e", "e", "e", "e", "e"], "entailment"), 5)
        self.assertEqual(agreement_count(["contradiction", "contradiction", "contradiction", "neutral", "neutral"], "c"), 3)
        self.assertEqual(agreement_count(["e", "", "e", "n", "c"], "e"), 2)
        self.assertIsNone(agreement_count(["e", "n", "c"], "-"))

    def test_plurality_and_strict(self):
        self.assertEqual(plurality([90, 5, 5], cases.NAMES_3WAY), "e")
        self.assertIsNone(plurality([50, 50, 0], cases.NAMES_3WAY))
        self.assertEqual(strict_majority([90, 5, 5], cases.NAMES_3WAY), "e")
        self.assertIsNone(strict_majority([48, 46, 6], cases.NAMES_3WAY))
        self.assertIsNone(strict_majority([50, 50, 0], cases.NAMES_3WAY))

    def test_old_eq_origgold_excludes_mismatch(self):
        # r6's old_label (c) deliberately differs from its original gold (e).
        flat = flatten(census(cases.FIXTURE))
        self.assertEqual(flat["n_old_eq_origgold"], 5)
        self.assertEqual(flat["n_orig_gold_valid"], 6)

    def test_directional_rates_on_fixture(self):
        stats = census(cases.FIXTURE)
        # P2 shape: unanimous-original examples are more decisive at 100 votes than bare-majority ones.
        self.assertEqual(no_strict_rate(stats, "5"), 0.0)
        self.assertEqual(no_strict_rate(stats, "3"), 1.0)
        self.assertLess(no_strict_rate(stats, "5"), no_strict_rate(stats, "3"))
        # P3 shape: the old gold flips against the 100-vote plurality more often for bare-majority ones.
        self.assertEqual(old_flip_rate(stats, "5"), 0.0)
        self.assertEqual(old_flip_rate(stats, "3"), 0.5)
        self.assertGreater(old_flip_rate(stats, "3"), old_flip_rate(stats, "5"))

    def test_examples_captured(self):
        stats = census(cases.FIXTURE)
        # r5 is the only bare-majority flip in the fixture.
        flips = stats["examples_bare_majority_flipped"]
        self.assertEqual(len(flips), 1)
        self.assertEqual(flips[0]["uid"], "r5")
        self.assertEqual(flips[0]["old"], "n")
        self.assertEqual(flips[0]["plurality"], "e")
        # no unanimous-original example lacks a strict majority in the fixture.
        self.assertEqual(stats["examples_orig_unanimous_no_strict"], [])

    def test_metadata(self):
        self.assertEqual(cases.EXPECTED_SUBSET_ROWS, {"snli": 1514, "mnli_m": 1599})
        self.assertEqual(cases.MIN_JOIN_COVERAGE, 0.99)


if __name__ == "__main__":
    unittest.main()
