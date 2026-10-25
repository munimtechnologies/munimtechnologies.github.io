"""Stdlib unittest suite for the ANLI per-(gold, model_label) verifier-agreement census.

Checks the label/majority/bucket helpers, then asserts the hand-traced fixture reproduces the frozen
TARGET exactly, the totals counters (orphan, missing model_label, fooled/agreed), a couple of specific
cells, and that aggregating over model_label buckets recovers the per-gold-class totals.
"""
import unittest

import cases
from modellabel_census import (
    LETTERS, MLABELS, aggregate_over_mlabels, census_by_gold_modellabel, flatten_gm,
    get_model_label, mlabel_bucket, norm_label, parse_verifier_row, strict_majority,
)


def _run_fixture():
    return census_by_gold_modellabel(
        [parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW],
        cases.build_gold_index(cases.FIXTURE_MAIN_RAW),
    )


class TestHelpers(unittest.TestCase):
    def test_norm_label(self):
        self.assertEqual(norm_label("Entailment"), "e")
        self.assertEqual(norm_label(" neutral "), "n")
        self.assertEqual(norm_label("CONTRADICTION"), "c")
        self.assertIsNone(norm_label(""))
        self.assertIsNone(norm_label(None))
        self.assertIsNone(norm_label("hidden"))  # h is not in {e,n,c}

    def test_strict_majority(self):
        self.assertEqual(strict_majority(["e", "e"]), "e")
        self.assertEqual(strict_majority(["c", "n", "c"]), "c")
        self.assertIsNone(strict_majority(["e", "n", "c"]))  # 1-1-1, no strict majority
        self.assertIsNone(strict_majority(["e", "n"]))       # tie
        self.assertIsNone(strict_majority([None, None]))

    def test_mlabel_bucket(self):
        self.assertEqual(mlabel_bucket("contradiction"), "c")
        self.assertEqual(mlabel_bucket(None), "x")
        self.assertEqual(mlabel_bucket(""), "x")
        self.assertEqual(mlabel_bucket("???"), "x")

    def test_get_model_label_tolerates_both_keys(self):
        self.assertEqual(get_model_label({"model_label": "n"}), "n")
        self.assertEqual(get_model_label({"model label": "c"}), "c")
        self.assertIsNone(get_model_label({"uid": "x"}))

    def test_parse_verifier_row(self):
        self.assertEqual(parse_verifier_row({"uid": "a", "verifier labels": ["e", "e"]}),
                         {"uid": "a", "labels": ["e", "e"]})
        self.assertEqual(parse_verifier_row({"uid": "b", "verifier_labels": ["c"]}),
                         {"uid": "b", "labels": ["c"]})
        self.assertEqual(parse_verifier_row({"uid": "c"}), {"uid": "c", "labels": []})


class TestFixtureMatchesTarget(unittest.TestCase):
    def test_flat_equals_target(self):
        stats = _run_fixture()
        flat = flatten_gm(stats["per_gold_mlabel"], stats["totals"])
        self.assertEqual(set(flat), set(cases.TARGET))
        for k in cases.TARGET:
            self.assertEqual(flat[k], cases.TARGET[k], "mismatch at %s" % k)

    def test_totals(self):
        t = _run_fixture()["totals"]
        self.assertEqual(t["n_verifier_lines"], 8)
        self.assertEqual(t["n_joined"], 7)
        self.assertEqual(t["n_orphan"], 1)
        self.assertEqual(t["n_gold_unexpected"], 0)
        self.assertEqual(t["n_model_label_recognised"], 6)
        self.assertEqual(t["n_model_label_missing"], 1)
        self.assertEqual(t["n_model_fooled"], 5)
        self.assertEqual(t["n_model_agreed"], 1)
        # fooled + agreed == recognised
        self.assertEqual(t["n_model_fooled"] + t["n_model_agreed"], t["n_model_label_recognised"])

    def test_specific_cells(self):
        prc = _run_fixture()["per_gold_mlabel"]
        # (e, c): u1 match + u5 differ, both unanimous k2
        self.assertEqual(prc["e"]["c"]["n"], 2)
        self.assertEqual(prc["e"]["c"]["match"], 1)
        self.assertEqual(prc["e"]["c"]["differ"], 1)
        self.assertEqual(prc["e"]["c"]["unanimous"], 2)
        # (c, x): the missing-model_label row lands in the x bucket
        self.assertEqual(prc["c"]["x"]["n"], 1)
        self.assertEqual(prc["c"]["x"]["match"], 1)
        # a cell that must be empty
        self.assertEqual(prc["n"]["c"]["n"], 0)

    def test_no_k2_split_in_fixture(self):
        prc = _run_fixture()["per_gold_mlabel"]
        total_split = sum(prc[g][m]["k2_split"] for g in LETTERS for m in MLABELS)
        self.assertEqual(total_split, 0)

    def test_aggregate_over_mlabels_recovers_per_class(self):
        stats = _run_fixture()
        agg = aggregate_over_mlabels(stats["per_gold_mlabel"])
        # entailment: u1 + u2 + u5 = 3 examples, 2 match, 1 differ
        self.assertEqual(agg["e"]["n"], 3)
        self.assertEqual(agg["e"]["match"], 2)
        self.assertEqual(agg["e"]["differ"], 1)
        # neutral: u3 + u6 = 2 match
        self.assertEqual(agg["n"]["n"], 2)
        self.assertEqual(agg["n"]["match"], 2)
        # contradiction: u4 + u7 = 2 match
        self.assertEqual(agg["c"]["n"], 2)
        self.assertEqual(agg["c"]["match"], 2)
        # the aggregate n over all classes equals n_joined minus gold_unexpected
        total_n = sum(agg[g]["n"] for g in LETTERS)
        self.assertEqual(total_n, 7)


if __name__ == "__main__":
    unittest.main()
