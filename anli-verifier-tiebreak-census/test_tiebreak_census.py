"""Stdlib unittest suite for the ANLI verifier-tiebreak census.

Checks the label/majority helpers, then runs the hand-traced fixture through census_tiebreak and asserts
the flattened result equals the frozen TARGET, cell by cell. No network, no files.
"""
import unittest

import cases
from tiebreak_census import (
    census_tiebreak, flatten, norm_label, parse_verifier_row, strict_majority,
)


class TestHelpers(unittest.TestCase):
    def test_norm_label(self):
        self.assertEqual(norm_label("entailment"), "e")
        self.assertEqual(norm_label("Neutral"), "n")
        self.assertEqual(norm_label(" c "), "c")
        self.assertIsNone(norm_label(""))
        self.assertIsNone(norm_label(None))
        self.assertIsNone(norm_label("x"))

    def test_parse_verifier_row(self):
        self.assertEqual(parse_verifier_row({"uid": "a", "verifier labels": ["e", "n"]}),
                         {"uid": "a", "labels": ["e", "n"]})
        self.assertEqual(parse_verifier_row({"uid": "b", "verifier_labels": ["c"]}),
                         {"uid": "b", "labels": ["c"]})
        self.assertEqual(parse_verifier_row({"uid": "c"}), {"uid": "c", "labels": []})

    def test_strict_majority(self):
        self.assertEqual(strict_majority(["e", "n", "e"]), "e")
        self.assertEqual(strict_majority(["n", "c", "n"]), "n")
        self.assertIsNone(strict_majority(["e", "n", "c"]))
        self.assertIsNone(strict_majority(["n", "c"]))
        self.assertEqual(strict_majority(["e", "e"]), "e")
        self.assertEqual(strict_majority(["c", "c", "n"]), "c")


class TestFixture(unittest.TestCase):
    def setUp(self):
        verifier_rows = [parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW]
        gold_index = cases.build_gold_index(cases.FIXTURE_MAIN_RAW)
        self.stats = census_tiebreak(verifier_rows, gold_index)
        self.flat = flatten(self.stats)

    def test_matches_target_cell_by_cell(self):
        self.assertEqual(set(self.flat), set(cases.TARGET))
        for k in sorted(cases.TARGET):
            self.assertEqual(self.flat[k], cases.TARGET[k], msg="mismatch at %s" % k)

    def test_totals_add_up(self):
        t = self.stats["totals"]
        self.assertEqual(t["n_joined"], t["k2"] + t["k3"] + t["k_other"])
        self.assertEqual(t["n_joined"],
                         t["all_lines_match"] + t["all_lines_differ"] + t["all_lines_no_majority"])

    def test_overall_equals_sum_of_breakdowns(self):
        # The overall tiebreak tally must equal the sum over classes and the sum over rounds.
        for f in ("n", "n_tiebreak", "tiebreak_gold", "tiebreak_other", "tiebreak_third",
                  "match", "differ", "no_majority", "firsttwo_agree"):
            by_class = sum(self.stats["by_class"][g][f] for g in cases.LETTERS)
            by_round = sum(self.stats["by_round"][r][f] for r in cases.ROUNDS)
            self.assertEqual(self.stats["overall"][f], by_class, msg="class sum %s" % f)
            self.assertEqual(self.stats["overall"][f], by_round, msg="round sum %s" % f)

    def test_tiebreak_partition(self):
        # Every genuine tiebreak resolves to exactly one of {gold, other, third}.
        o = self.stats["overall"]
        self.assertEqual(o["n_tiebreak"], o["tiebreak_gold"] + o["tiebreak_other"] + o["tiebreak_third"])
        self.assertEqual(o["n"], o["gold_in_firsttwo"] + o["gold_not_in_firsttwo"])
        self.assertEqual(o["n"], o["majority_formed"] + o["no_majority"])


if __name__ == "__main__":
    unittest.main()
