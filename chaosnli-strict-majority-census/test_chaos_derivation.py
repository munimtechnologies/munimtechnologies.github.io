"""Tests for the ChaosNLI strict-majority / old-gold-stability census (stdlib unittest)."""
import unittest

import cases
from chaos_derivation import norm_label, plurality, strict_majority, census, flatten


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        stats = census(cases.FIXTURE)
        flat = flatten(stats)
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_norm_label(self):
        self.assertEqual(norm_label("e"), "e")
        self.assertEqual(norm_label("Entailment"), "e")
        self.assertEqual(norm_label("NEUTRAL"), "n")
        self.assertEqual(norm_label("contradiction"), "c")
        self.assertEqual(norm_label("1"), "1")
        self.assertEqual(norm_label(2), "2")
        self.assertIsNone(norm_label("-"))
        self.assertIsNone(norm_label(""))
        self.assertIsNone(norm_label(None))

    def test_plurality(self):
        self.assertEqual(plurality([70, 20, 10], cases.NAMES_3WAY), "e")
        self.assertEqual(plurality([30, 30, 40], cases.NAMES_3WAY), "c")
        self.assertIsNone(plurality([50, 50, 0], cases.NAMES_3WAY))   # tie at the top
        self.assertEqual(plurality([60, 40], cases.NAMES_2WAY), "1")

    def test_strict_majority(self):
        self.assertEqual(strict_majority([60, 30, 10], cases.NAMES_3WAY), "e")
        self.assertIsNone(strict_majority([50, 50, 0], cases.NAMES_3WAY))   # 50 is not > 50
        self.assertIsNone(strict_majority([40, 35, 25], cases.NAMES_3WAY))
        self.assertEqual(strict_majority([51, 49], cases.NAMES_2WAY), "1")
        self.assertIsNone(strict_majority([0, 0, 0], cases.NAMES_3WAY))

    def test_old_differs_majority_captured(self):
        stats = census(cases.FIXTURE)
        self.assertEqual(stats["n_old_differs_majority"], 1)
        ex = stats["examples_old_differs_majority"][0]
        self.assertEqual(ex["uid"], "r2")
        self.assertEqual(ex["old"], "n")
        self.assertEqual(ex["majority"], "e")

    def test_no_strict_examples_captured(self):
        stats = census(cases.FIXTURE)
        self.assertEqual(stats["n_no_strict_majority"], 3)
        self.assertEqual(len(stats["examples_no_strict_with_old"]), 3)
        self.assertEqual({e["uid"] for e in stats["examples_no_strict_with_old"]}, {"r3", "r4", "r5"})

    def test_strict_partition(self):
        stats = census(cases.FIXTURE)
        # old-vs-strict only counts among records that HAVE a strict majority
        self.assertEqual(stats["n_old_eq_strict"] + stats["n_old_differs_strict"], stats["n_strict_exists"])
        # old-on-no-strict equals no-strict count when every no-strict record has an old label
        self.assertEqual(stats["n_old_on_no_strict"], stats["n_no_strict_majority"])

    def test_two_way_alphanli_path(self):
        recs = [
            {"uid": "a1", "old": "1", "majority": "1", "counts": [80, 20], "names": cases.NAMES_2WAY},
            {"uid": "a2", "old": "2", "majority": "1", "counts": [51, 49], "names": cases.NAMES_2WAY},
            {"uid": "a3", "old": "1", "majority": "1", "counts": [50, 50], "names": cases.NAMES_2WAY},
        ]
        stats = census(recs)
        self.assertEqual(stats["n_records"], 3)
        self.assertEqual(stats["n_strict_exists"], 2)       # a1 (80), a2 (51)
        self.assertEqual(stats["n_no_strict_majority"], 1)  # a3 is a 50-50 tie
        self.assertEqual(stats["n_old_differs_majority"], 1)  # a2 old 2 vs majority 1

    def test_metadata(self):
        self.assertEqual(cases.CARD_OLD_DIFFERS_MAJORITY, {"snli": 378, "mnli_m": 508})
        self.assertEqual(cases.SUBSET_ROWS["snli"], 1514)
        self.assertEqual(cases.SUBSET_NAMES["alphanli"], cases.NAMES_2WAY)


if __name__ == "__main__":
    unittest.main()
