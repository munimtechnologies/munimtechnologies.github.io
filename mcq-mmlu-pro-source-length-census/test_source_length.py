"""Unit tests for the MMLU-Pro source length census (audit 63). Standard library only. Apache-2.0."""

import copy
import unittest

import cases
import gold_length as gl
import source as sl


def E(n, chance, acc, ushort=0.0):
    """Minimal report entry for the prediction logic."""
    return {"n_valid": n, "chance_accuracy": chance,
            "char": {"longest_accuracy": acc, "unique_shortest_rate": ushort}}


class CoreFixture(unittest.TestCase):
    def test_core_matches_target(self):
        self.assertEqual(gl.run_census(cases.FIXTURE_ROWS), cases.TARGET)


class SourceKeys(unittest.TestCase):
    def test_family(self):
        self.assertEqual(sl.family("ori_mmlu-high_school_biology"), "ori_mmlu")
        self.assertEqual(sl.family("stemez-Biology"), "stemez")
        self.assertEqual(sl.family("theoremQA-Physics"), "theoremQA")
        self.assertEqual(sl.family("scibench-thermo"), "scibench")
        self.assertEqual(sl.family(""), "unknown")
        self.assertEqual(sl.family(None), "unknown")

    def test_provenance(self):
        self.assertEqual(sl.provenance("ori_mmlu-x"), "ori_mmlu")
        self.assertEqual(sl.provenance("stemez-x"), "new")
        self.assertEqual(sl.provenance(None), "new")

    def test_family_digest(self):
        rows = sl.census_rows(cases.KEY_ROWS, lambda r: sl.family(r["src"]))
        self.assertEqual(sl.digest(gl.run_census(rows)), cases.KEY_TARGET_FAMILY)

    def test_provenance_digest(self):
        rows = sl.census_rows(cases.KEY_ROWS, lambda r: sl.provenance(r["src"]))
        self.assertEqual(sl.digest(gl.run_census(rows)), cases.KEY_TARGET_PROV)

    def test_category_provenance_digest(self):
        rows = sl.census_rows(cases.KEY_ROWS, lambda r: r["category"] + "|" + sl.provenance(r["src"]))
        self.assertEqual(sl.digest(gl.run_census(rows)), cases.KEY_TARGET_CATPROV)


def _gate_inputs():
    ex = cases.EXPECTED
    pooled = {"n_valid": ex["n_valid"], "n_bad_key": 0, "n_degenerate": 0,
              "char": {"unique_longest_count": ex["unique_longest"], "longest_accuracy": ex["longest_accuracy"]}}
    by_prov = {k: {"n_valid": n, "char": {"longest_accuracy": a}} for k, (n, a) in ex["provenance"].items()}
    by_cat = {k: {"n_valid": n, "char": {"longest_accuracy": a}} for k, (n, a) in ex["category"].items()}
    return pooled, by_prov, by_cat


class Gate(unittest.TestCase):
    def test_passes_on_expected(self):
        pooled, by_prov, by_cat = _gate_inputs()
        ok, _detail = sl.structural_gate(pooled, by_prov, by_cat, cases.EXPECTED)
        self.assertTrue(ok)

    def test_fails_on_drift(self):
        pooled, by_prov, by_cat = _gate_inputs()
        by_cat = copy.deepcopy(by_cat)
        by_cat["biology"]["char"]["longest_accuracy"] += 1e-6
        ok, detail = sl.structural_gate(pooled, by_prov, by_cat, cases.EXPECTED)
        self.assertFalse(ok)
        self.assertFalse(detail["category:biology"]["match"])

    def test_fails_on_missing_key(self):
        pooled, by_prov, by_cat = _gate_inputs()
        del by_prov["new"]
        ok, detail = sl.structural_gate(pooled, by_prov, by_cat, cases.EXPECTED)
        self.assertFalse(ok)
        self.assertIsNone(detail["provenance:new"]["got"])


class Predictions(unittest.TestCase):
    def setUp(self):
        # scibench has n < 100 and is left out of P3/P4/P6.
        self.fam = {"ori_mmlu": E(1000, .1, .11, .09), "stemez": E(500, .1, .4, .01),
                    "theoremQA": E(200, .1, .2, .02), "scibench": E(50, .1, .05, .2)}
        # law|new has n < 50, so law is not eligible for P5. Eligible: biology, math, psychology.
        self.cp = {"biology|ori_mmlu": E(200, .1, .15), "biology|new": E(500, .1, .6),
                   "psychology|ori_mmlu": E(400, .1, .1), "psychology|new": E(300, .1, .45),
                   "math|ori_mmlu": E(800, .1, .1), "math|new": E(500, .1, .08),
                   "law|ori_mmlu": E(1000, .1, .2), "law|new": E(1, .1, 1.0)}

    def test_hand_traced(self):
        p = sl.predictions(self.fam, self.cp)
        self.assertTrue(p["P1_new_source_biology_pick_longest_at_least_50pct"])     # .6 >= .5
        self.assertFalse(p["P2_new_source_psychology_pick_longest_at_least_50pct"])  # .45 < .5
        self.assertTrue(p["P3_every_new_family_lift_exceeds_ori_mmlu"])             # .3, .1 > .01
        self.assertEqual(sorted(p["P3_detail"]["family_lifts"]), ["stemez", "theoremQA"])
        self.assertTrue(p["P4_stemez_has_largest_new_family_lift"])
        self.assertEqual(p["P5_detail"]["eligible"], ["biology", "math", "psychology"])
        self.assertEqual(p["P5_detail"]["new_wins"], ["biology", "psychology"])     # math -.02 < 0
        self.assertTrue(p["P5_new_lift_exceeds_ori_in_majority_of_categories"])     # 2 of 3
        self.assertTrue(p["P6_new_family_gold_unique_shortest_under_5pct"])         # .01, .02

    def test_failures(self):
        fam = copy.deepcopy(self.fam)
        fam["theoremQA"] = E(200, .1, .5, .08)   # largest lift, and unique-shortest 8%
        fam["stemez"] = E(500, .1, .105, .01)    # lift .005 < ori .01
        p = sl.predictions(fam, self.cp)
        self.assertFalse(p["P3_every_new_family_lift_exceeds_ori_mmlu"])
        self.assertFalse(p["P4_stemez_has_largest_new_family_lift"])
        self.assertEqual(p["P4_detail"]["top_family"], "theoremQA")
        self.assertFalse(p["P6_new_family_gold_unique_shortest_under_5pct"])

    def test_p5_tie_is_not_majority(self):
        cp = {"a|ori_mmlu": E(60, .1, .1), "a|new": E(60, .1, .3),
              "b|ori_mmlu": E(60, .1, .3), "b|new": E(60, .1, .1)}
        p = sl.predictions(self.fam, cp)
        self.assertFalse(p["P5_new_lift_exceeds_ori_in_majority_of_categories"])
        self.assertFalse(p["P1_new_source_biology_pick_longest_at_least_50pct"])    # no biology cell


if __name__ == "__main__":
    unittest.main()
