"""Tests for the ANLI verifier-majority / gold-derivation census (stdlib unittest)."""
import unittest

import cases
from anli_verifier import (norm_label, strict_majority, parse_verifier_row, census, flatten)


def _verifier_rows():
    return [parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW]


def _index():
    return cases.build_gold_index(cases.FIXTURE_MAIN_RAW)


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        stats = census(_verifier_rows(), _index())
        flat = flatten(stats)
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_norm_label(self):
        self.assertEqual(norm_label("e"), "e")
        self.assertEqual(norm_label("entailment"), "e")
        self.assertEqual(norm_label("N"), "n")
        self.assertEqual(norm_label("Contradiction"), "c")
        self.assertIsNone(norm_label("-"))
        self.assertIsNone(norm_label(""))
        self.assertIsNone(norm_label(None))

    def test_strict_majority(self):
        self.assertIsNone(strict_majority([]))
        self.assertEqual(strict_majority(["e"]), "e")
        self.assertEqual(strict_majority(["e", "e"]), "e")
        self.assertIsNone(strict_majority(["e", "n"]))           # 1-1 tie
        self.assertEqual(strict_majority(["c", "n", "c"]), "c")   # 2-1
        self.assertIsNone(strict_majority(["e", "n", "c"]))       # 1-1-1
        self.assertEqual(strict_majority(["e", "e", "e"]), "e")

    def test_parse_verifier_row(self):
        r = parse_verifier_row({"uid": "x", "verifier labels": ["e", "n"]})
        self.assertEqual(r["uid"], "x")
        self.assertEqual(r["labels"], ["e", "n"])
        # tolerate the underscore spelling and a missing list
        self.assertEqual(parse_verifier_row({"uid": "y", "verifier_labels": ["c"]})["labels"], ["c"])
        self.assertEqual(parse_verifier_row({"uid": "z"})["labels"], [])

    def test_differ_captured(self):
        stats = census(_verifier_rows(), _index())
        self.assertEqual(stats["n_gold_differs_from_majority"], 1)
        self.assertEqual(len(stats["examples_differ"]), 1)
        ex = stats["examples_differ"][0]
        self.assertEqual(ex["uid"], "u2")
        self.assertEqual(ex["gold"], "n")
        self.assertEqual(ex["verifier_majority"], "e")

    def test_unanimous_differ_captured(self):
        stats = census(_verifier_rows(), _index())
        self.assertEqual(stats["n_unanimous_differs_from_gold"], 1)
        self.assertEqual(stats["examples_unanimous_differ"][0]["uid"], "u2")

    def test_orphan_counted(self):
        stats = census(_verifier_rows(), _index())
        self.assertEqual(stats["n_orphan"], 1)       # u6 has no main example
        self.assertEqual(stats["n_joined"], 4)

    def test_no_majority_path(self):
        stats = census(_verifier_rows(), _index())
        self.assertEqual(stats["n_no_majority"], 1)  # u4 is 1-1-1

    def test_per_round(self):
        stats = census(_verifier_rows(), _index())
        self.assertEqual(stats["per_round"]["R1"], {"joined": 2, "match": 1, "differ": 1, "no_majority": 0})
        self.assertEqual(stats["per_round"]["R3"]["no_majority"], 1)

    def test_gold_unexpected(self):
        # a joined example whose gold does not normalise to e/n/c is counted, not silently matched
        idx = {"a": {"split": "dev", "round": "R1", "gold": "-"}}
        stats = census([{"uid": "a", "labels": ["e", "e"]}], idx)
        self.assertEqual(stats["n_gold_unexpected"], 1)
        self.assertEqual(stats["n_gold_matches_majority"], 0)

    def test_metadata(self):
        self.assertEqual(cases.ROUNDS, ("R1", "R2", "R3"))
        self.assertEqual(cases.SPLITS, ("train", "dev", "test"))


if __name__ == "__main__":
    unittest.main()
