"""Stdlib unittest suite for the ANLI per-gold-class verifier-agreement census.

Verifies the primitives (norm_label, strict_majority, parse_verifier_row) and, above all, that the census
reproduces the hand-traced TARGET in cases.py exactly, before any real ANLI file is read.

Run: python -m unittest -v
"""
import unittest

import cases
from class_census import (census_by_class, flatten, norm_label, parse_verifier_row, strict_majority)


class TestNormLabel(unittest.TestCase):
    def test_letters_and_words(self):
        self.assertEqual(norm_label("e"), "e")
        self.assertEqual(norm_label("Entailment"), "e")
        self.assertEqual(norm_label("NEUTRAL"), "n")
        self.assertEqual(norm_label("contradiction"), "c")

    def test_junk_is_none(self):
        for x in (None, "", "   ", "-", "x", "maybe"):
            self.assertIsNone(norm_label(x))


class TestStrictMajority(unittest.TestCase):
    def test_pair_agree(self):
        self.assertEqual(strict_majority(["e", "e"]), "e")

    def test_pair_split_is_none(self):
        self.assertIsNone(strict_majority(["e", "n"]))

    def test_triple_two_one(self):
        self.assertEqual(strict_majority(["c", "n", "c"]), "c")

    def test_triple_all_different_is_none(self):
        self.assertIsNone(strict_majority(["e", "n", "c"]))

    def test_empty_is_none(self):
        self.assertIsNone(strict_majority([]))
        self.assertIsNone(strict_majority([None, None]))


class TestParseVerifier(unittest.TestCase):
    def test_space_key(self):
        r = parse_verifier_row({"uid": "x", "verifier labels": ["e", "n"]})
        self.assertEqual(r, {"uid": "x", "labels": ["e", "n"]})

    def test_underscore_key_and_missing(self):
        self.assertEqual(parse_verifier_row({"uid": "y", "verifier_labels": ["c"]}),
                         {"uid": "y", "labels": ["c"]})
        self.assertEqual(parse_verifier_row({"uid": "z"}), {"uid": "z", "labels": []})


class TestFixtureMatchesTarget(unittest.TestCase):
    def setUp(self):
        rows = [parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW]
        idx = cases.build_gold_index(cases.FIXTURE_MAIN_RAW)
        self.stats = census_by_class(rows, idx)
        self.flat = flatten(self.stats)

    def test_every_target_key_matches(self):
        for k, v in cases.TARGET.items():
            self.assertEqual(self.flat[k], v, "key %s: got %r want %r" % (k, self.flat[k], v))

    def test_no_extra_or_missing_flat_keys(self):
        self.assertEqual(set(self.flat), set(cases.TARGET))

    def test_per_class_n_sums_to_joined_minus_unexpected(self):
        t = self.stats["totals"]
        joined_valid = t["n_joined"] - t["n_gold_unexpected"]
        per_class_sum = sum(self.stats["per_class"][g]["n"] for g in ("e", "n", "c"))
        self.assertEqual(per_class_sum, joined_valid)

    def test_devtest_plus_train_equals_all(self):
        for g in ("e", "n", "c"):
            for f in ("n", "unanimous", "match", "differ", "no_majority"):
                self.assertEqual(
                    self.stats["per_class_devtest"][g][f] + self.stats["per_class_train"][g][f],
                    self.stats["per_class"][g][f],
                    "class %s field %s" % (g, f))

    def test_match_differ_nomajority_partition_n(self):
        for g in ("e", "n", "c"):
            cell = self.stats["per_class"][g]
            self.assertEqual(cell["match"] + cell["differ"] + cell["no_majority"], cell["n"])

    def test_orphan_counted_not_joined(self):
        self.assertEqual(self.stats["totals"]["n_orphan"], 1)
        self.assertEqual(self.stats["totals"]["n_joined"], 5)


class TestK2SplitAnomaly(unittest.TestCase):
    def test_disagreeing_pair_flagged(self):
        rows = [parse_verifier_row({"uid": "a", "verifier labels": ["e", "n"]})]
        idx = {"a": {"split": "dev", "round": "R1", "gold": "e"}}
        stats = census_by_class(rows, idx)
        cell = stats["per_class"]["e"]
        self.assertEqual(cell["k2"], 1)
        self.assertEqual(cell["k2_split"], 1)
        self.assertEqual(cell["unanimous"], 0)
        self.assertEqual(cell["no_majority"], 1)  # 1-1 pair has no strict majority


if __name__ == "__main__":
    unittest.main()
