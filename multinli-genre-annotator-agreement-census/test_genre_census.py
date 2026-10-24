"""Tests for the MultiNLI per-genre annotator-agreement census (stdlib unittest)."""
import unittest

import cases
from genre_census import (
    norm_label, majority_label, agreement_count, census, flatten,
    unanimous_rate, individual_agreement_rate,
)


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        flat = flatten(census(cases.FIXTURE))
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_totals_sum_across_genres(self):
        stats = census(cases.FIXTURE)
        t = stats["totals"]
        self.assertEqual(t["n"], 7)
        self.assertEqual(t["valid"], 6)
        self.assertEqual(t["dash"], 1)
        self.assertEqual(t["unanimous"], 1)
        self.assertEqual(t["gold_eq_majority"], 6)
        # valid + dash == n for every genre and the totals.
        for cell in list(stats["genres"].values()) + [t]:
            self.assertEqual(cell["valid"] + cell["dash"], cell["n"])
            self.assertEqual(cell["b5"] + cell["b4"] + cell["b3"] + cell["bother"], cell["valid"])

    def test_norm_label(self):
        self.assertEqual(norm_label("entailment"), "e")
        self.assertEqual(norm_label("NEUTRAL"), "n")
        self.assertEqual(norm_label("c"), "c")
        self.assertIsNone(norm_label("-"))
        self.assertIsNone(norm_label(""))
        self.assertIsNone(norm_label(None))

    def test_majority_label(self):
        self.assertEqual(majority_label(["e", "e", "e", "n", "c"]), "e")       # 3 of 5
        self.assertEqual(majority_label(["n", "n", "n", "n", "e"]), "n")       # 4 of 5
        self.assertIsNone(majority_label(["e", "e", "n", "n", "c"]))            # 2-2-1, no majority
        self.assertIsNone(majority_label(["e", "n", "c"]))                      # 1-1-1
        self.assertIsNone(majority_label([]))

    def test_agreement_count(self):
        self.assertEqual(agreement_count(["e", "e", "e", "e", "e"], "entailment"), 5)
        self.assertEqual(agreement_count(["c", "c", "c", "n", "n"], "c"), 3)
        self.assertIsNone(agreement_count(["e", "n", "c"], "-"))

    def test_by_construction_gold_equals_majority(self):
        # Every non-dash record's gold equals the strict majority of its five labels (P1 shape).
        stats = census(cases.FIXTURE)
        for cell in stats["genres"].values():
            self.assertEqual(cell["gold_eq_majority"], cell["valid"])

    def test_rates(self):
        stats = census(cases.FIXTURE)
        self.assertAlmostEqual(unanimous_rate(stats, "government"), 1.0 / 3.0)
        self.assertEqual(unanimous_rate(stats, "telephone"), 0.0)
        # P2 shape: telephone (spoken) less unanimous than government (formal written).
        self.assertLess(unanimous_rate(stats, "telephone"), unanimous_rate(stats, "government"))
        self.assertAlmostEqual(individual_agreement_rate(stats, "government"), 12.0 / 15.0)
        self.assertAlmostEqual(individual_agreement_rate(stats, "telephone"), 10.0 / 15.0)
        # unknown genre -> 0.0, never a KeyError.
        self.assertEqual(unanimous_rate(stats, "nope"), 0.0)
        self.assertEqual(individual_agreement_rate(stats, "nope"), 0.0)

    def test_p3_spread_on_fixture(self):
        stats = census(cases.FIXTURE)
        rates = [unanimous_rate(stats, g) for g in stats["genres"]]
        self.assertGreater(max(rates) - min(rates), cases.P3_SPREAD_THRESHOLD)

    def test_metadata(self):
        self.assertEqual(cases.EXPECTED_TOTAL_DEV_ROWS, 20000)
        self.assertEqual(len(cases.MATCHED_GENRES), 5)
        self.assertEqual(len(cases.MISMATCHED_GENRES), 5)
        self.assertIn("telephone", cases.MATCHED_GENRES)
        self.assertIn("government", cases.MATCHED_GENRES)


if __name__ == "__main__":
    unittest.main()
