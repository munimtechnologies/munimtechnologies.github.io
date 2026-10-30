"""Unit tests for audit 66 (hand-traced fixtures in cases.py). Apache-2.0."""

import unittest
from fractions import Fraction

import cases
import strata as st


def _models(spec):
    """{model: (acc, pull, rank_all, sbp_rank, sbp_n, sbp_acc, obp_rank, obp_n, mh_stemez, mh_ori)}"""
    out = {}
    for m, (acc, pull, ra, sr, sn, sa, orank, on, ms, mo) in spec.items():
        out[m] = {
            "ALL": {"accuracy": acc, "error_pull_ratio": pull, "length_rank_mean": ra},
            "sub:stemez-biopsy": {"length_rank_mean": sr, "length_rank_n": sn, "accuracy": sa},
            "sub:ori-biopsy": {"length_rank_mean": orank, "length_rank_n": on},
            "fam:stemez": {"mh_rd_gold_ul": ms},
            "fam:ori_mmlu": {"mh_rd_gold_ul": mo},
        }
    return out


class TestRankAndStrata(unittest.TestCase):
    def test_length_rank(self):
        for options, gold, pick, want in cases.RANK_CASES:
            self.assertEqual(st.length_rank(options, gold, pick), want, (options, gold, pick))

    def test_rank_mean_over_distractors_is_half(self):
        options = ["a", "bbb", "cc", "bbb", "dddd", "e"]
        gold = 4
        ranks = [st.length_rank(options, gold, j) for j in range(len(options)) if j != gold]
        self.assertEqual(sum(ranks) / len(ranks), Fraction(1, 2))

    def test_add_strata(self):
        acc = st.new_strata_acc()
        for src, options, gold, pred in cases.STRATA_ROWS:
            st.add_strata(acc, src, options, gold, pred)
        self.assertEqual(acc, cases.STRATA_TARGET)
        rep = st.report_strata(acc)
        self.assertEqual(set(rep), set(cases.STRATA_REPORT))
        for k, v in cases.STRATA_REPORT.items():
            self.assertAlmostEqual(rep[k], v, places=12, msg=k)

    def test_mh(self):
        self.assertEqual(st.mh_risk_difference(cases.MH_CELLS), cases.MH_TARGET)
        self.assertEqual(st.mh_risk_difference([[0, 0, 2, 1]]), (None, 0, 0))

    def test_spearman(self):
        self.assertEqual(st.avg_ranks([3, 1, 2]), [3.0, 1.0, 2.0])
        self.assertEqual(st.avg_ranks([1, 2, 2, 3]), [1.0, 2.5, 2.5, 4.0])
        self.assertAlmostEqual(st.spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertAlmostEqual(st.spearman([1, 2, 2, 3], [1, 2, 3, 4]), 4.5 / (22.5 ** 0.5))
        self.assertIsNone(st.spearman([1, 2], [2, 1]))
        self.assertIsNone(st.spearman([1, 1, 1], [1, 2, 3]))

    def test_model_name(self):
        self.assertEqual(cases.model_name("model_outputs_gpt-4o-mini_5shots.zip"), "gpt-4o-mini_5shots")
        self.assertEqual(cases.model_name("model_outputs_arx_0314_5shots.json.zip"), "arx_0314_5shots")
        self.assertEqual(len(cases.ARCHIVES), 48)
        self.assertEqual(len(set(cases.model_name(z) for z in cases.ARCHIVES)), 48)
        for m in cases.AUDIT65:
            self.assertIn("model_outputs_%s.zip" % m, cases.ARCHIVES)


class TestPredictions(unittest.TestCase):
    def test_all_held(self):
        models = _models({
            "m1": (0.2, 1.2, 0.53, 0.70, 40, 0.50, 0.55, 40, 0.20, 0.00),
            "m2": (0.5, 1.1, 0.52, 0.60, 40, 0.80, 0.50, 40, 0.10, 0.05),
            "m3": (0.8, 1.0, 0.49, 0.45, 40, 0.90, 0.50, 40, -0.10, -0.20),
        })
        p = st.predictions(models, heuristic_biopsy=0.66, new_models=["m1"])
        self.assertTrue(p["P1_length_rank_above_half_in_majority"])           # m1, m2
        self.assertTrue(p["P2_median_length_rank_in_0_51_0_56"])              # median 0.52
        self.assertTrue(p["P3_stemez_biopsy_rank_above_ori_biopsy_in_majority"])  # m1, m2 of 3
        self.assertTrue(p["P4_within_src_gold_longest_advantage_positive_on_stemez"])  # m1, m2
        self.assertTrue(p["P5_within_src_advantage_larger_on_stemez_than_ori"])  # all 3
        self.assertTrue(p["P6_accuracy_and_error_pull_negatively_correlated"])  # rho -1
        self.assertTrue(p["P7_a_new_model_below_pick_longest_on_stemez_biopsy"])  # m1 0.50 < 0.66

    def test_all_failed(self):
        models = _models({
            "m1": (0.2, 1.0, 0.49, 0.40, 40, 0.70, 0.50, 40, -0.10, 0.00),
            "m2": (0.5, 1.1, 0.50, 0.50, 40, 0.80, 0.50, 40, 0.00, 0.10),
            "m3": (0.8, 1.2, 0.60, 0.70, 40, 0.90, 0.50, 40, 0.10, 0.20),
        })
        p = st.predictions(models, heuristic_biopsy=0.66, new_models=["m1"])
        self.assertFalse(p["P1_length_rank_above_half_in_majority"])          # only m3
        self.assertFalse(p["P2_median_length_rank_in_0_51_0_56"])             # median 0.50
        self.assertFalse(p["P3_stemez_biopsy_rank_above_ori_biopsy_in_majority"])  # only m3
        self.assertFalse(p["P4_within_src_gold_longest_advantage_positive_on_stemez"])  # only m3
        self.assertFalse(p["P5_within_src_advantage_larger_on_stemez_than_ori"])  # none
        self.assertFalse(p["P6_accuracy_and_error_pull_negatively_correlated"])  # rho +1
        self.assertFalse(p["P7_a_new_model_below_pick_longest_on_stemez_biopsy"])  # m1 0.70 >= 0.66

    def test_p3_eligibility(self):
        models = _models({
            "m1": (0.2, 1.2, 0.53, 0.70, 29, 0.50, 0.55, 40, 0.20, 0.00),
        })
        p = st.predictions(models, heuristic_biopsy=0.66, new_models=[])
        self.assertFalse(p["P3_stemez_biopsy_rank_above_ori_biopsy_in_majority"])  # nobody eligible
        self.assertFalse(p["P7_a_new_model_below_pick_longest_on_stemez_biopsy"])  # no new models
        self.assertIsNone(p["P6_detail"]["spearman"])                              # fewer than 3 models


if __name__ == "__main__":
    unittest.main()
