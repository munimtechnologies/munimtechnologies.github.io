"""Stdlib unittest suite for the ANLI per-(round, class) verifier-agreement census.

Verifies the label/majority primitives, the join + round x class counting against the hand-traced fixture
TARGET, and the two aggregation helpers (over rounds -> per class; over classes -> per round).

Apache-2.0. Authored by AI agents working in MV2's name at Munim, Inc.
"""
import unittest

import cases
from round_class_census import (
    LETTERS, ROUNDS, aggregate_over_classes, aggregate_over_rounds, census_by_round_class,
    flatten_rc, norm_label, parse_verifier_row, strict_majority,
)


class TestPrimitives(unittest.TestCase):
    def test_norm_label(self):
        self.assertEqual(norm_label("entailment"), "e")
        self.assertEqual(norm_label("Neutral"), "n")
        self.assertEqual(norm_label(" c "), "c")
        self.assertEqual(norm_label("contradiction"), "c")
        self.assertIsNone(norm_label("-"))
        self.assertIsNone(norm_label(""))
        self.assertIsNone(norm_label(None))
        self.assertIsNone(norm_label("x"))

    def test_strict_majority(self):
        self.assertEqual(strict_majority(["e", "e"]), "e")          # unanimous pair
        self.assertEqual(strict_majority(["c", "n", "c"]), "c")     # 2-of-3
        self.assertIsNone(strict_majority(["e", "n", "c"]))         # 1-1-1, no majority
        self.assertIsNone(strict_majority(["e", "n"]))              # tie, no majority
        self.assertIsNone(strict_majority([None, None]))
        self.assertEqual(strict_majority(["n", "n", None]), "n")    # None votes dropped

    def test_parse_verifier_row(self):
        self.assertEqual(parse_verifier_row({"uid": "x", "verifier labels": ["e", "n"]}),
                         {"uid": "x", "labels": ["e", "n"]})
        self.assertEqual(parse_verifier_row({"uid": "y", "verifier_labels": ["c"]}),
                         {"uid": "y", "labels": ["c"]})
        self.assertEqual(parse_verifier_row({"uid": "z"}), {"uid": "z", "labels": []})


class TestFixture(unittest.TestCase):
    def setUp(self):
        self.stats = census_by_round_class(
            [parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW],
            cases.build_gold_index(cases.FIXTURE_MAIN_RAW),
        )
        self.flat = flatten_rc(self.stats["per_round_class"], self.stats["totals"])

    def test_matches_hand_traced_target(self):
        self.assertEqual(set(self.flat), set(cases.TARGET))
        for k in cases.TARGET:
            self.assertEqual(self.flat[k], cases.TARGET[k], "mismatch at %s" % k)

    def test_totals(self):
        t = self.stats["totals"]
        self.assertEqual(t["n_verifier_lines"], 6)
        self.assertEqual(t["n_joined"], 5)
        self.assertEqual(t["n_orphan"], 1)
        self.assertEqual(t["n_train"], 1)
        self.assertEqual(t["n_devtest"], 4)
        self.assertEqual(t["n_gold_unexpected"], 0)

    def test_r1_neutral_pools_two_records(self):
        cell = self.stats["per_round_class"]["R1"]["n"]
        self.assertEqual(cell["n"], 2)
        self.assertEqual(cell["unanimous"], 2)
        self.assertEqual(cell["match"], 1)
        self.assertEqual(cell["differ"], 1)

    def test_aggregate_over_rounds_sums_classes(self):
        # Summing R1..R3 per class must reproduce the total joined-with-gold count.
        per_class = aggregate_over_rounds(self.stats["per_round_class"])
        total_n = sum(per_class[g]["n"] for g in LETTERS)
        self.assertEqual(total_n, 5)  # all 5 joined examples carry a recognised gold
        self.assertEqual(per_class["e"]["n"], 2)   # (R1,e)=1 + (R3,e)=1
        self.assertEqual(per_class["n"]["n"], 2)   # (R1,n)=2
        self.assertEqual(per_class["c"]["n"], 1)   # (R2,c)=1

    def test_aggregate_over_classes_sums_rounds(self):
        per_round = aggregate_over_classes(self.stats["per_round_class"])
        self.assertEqual(per_round["R1"]["n"], 3)  # (R1,e)=1 + (R1,n)=2
        self.assertEqual(per_round["R2"]["n"], 1)
        self.assertEqual(per_round["R3"]["n"], 1)
        self.assertEqual(sum(per_round[r]["n"] for r in ROUNDS), 5)


if __name__ == "__main__":
    unittest.main()
