"""Unit tests for audit 65 (hand-traced fixtures in cases.py). Apache-2.0."""

import unittest

import cases
import model_length as ml


def _models(spec):
    """Build a predictions() input from {model: (acc, ratio_all, ratio_stemez, ratio_ori, biopsy_acc, ul, not_ul)}."""
    out = {}
    for m, (acc, ra, rs, ro, ba, ul, nul) in spec.items():
        out[m] = {
            "ALL": {"accuracy": acc, "error_pull_ratio": ra},
            "fam:stemez": {"error_pull_ratio": rs},
            "fam:ori_mmlu": {"error_pull_ratio": ro},
            "sub:stemez-biopsy": {"accuracy": ba, "n_gold_unique_longest": 30, "n_gold_not_unique_longest": 30,
                                  "accuracy_gold_unique_longest": ul, "accuracy_gold_not_unique_longest": nul},
        }
    return out


class TestAccumulator(unittest.TestCase):
    def test_add_matches_hand_trace(self):
        acc = ml.new_acc()
        for options, gold, pred in cases.ADD_ROWS:
            ml.add(acc, options, gold, pred)
        self.assertEqual(acc, cases.ADD_TARGET)

    def test_report_ratio(self):
        acc = ml.new_acc()
        for options, gold, pred in cases.ADD_ROWS:
            ml.add(acc, options, gold, pred)
        r = ml.report(acc)
        self.assertEqual(r["base_longest_exact"], "7/6")
        self.assertAlmostEqual(r["error_pull_ratio"], 6 / 7)
        self.assertAlmostEqual(r["wrong_on_longest_distractor"], 0.5)
        self.assertAlmostEqual(r["wrong_on_longest_distractor_baseline"], 7 / 12)
        self.assertAlmostEqual(r["accuracy"], 2 / 7)

    def test_pick_longest_credit(self):
        for options, gold, want in cases.CREDIT_CASES:
            self.assertEqual(ml.pick_longest_credit(options, gold), want)

    def test_pred_index(self):
        self.assertEqual(ml.pred_index("a", 3), 0)
        self.assertEqual(ml.pred_index("J", 10), 9)
        self.assertIsNone(ml.pred_index("J", 9))
        self.assertIsNone(ml.pred_index("AB", 10))
        self.assertIsNone(ml.pred_index(None, 10))
        self.assertIsNone(ml.pred_index(3, 10))


class TestJoinAndKeys(unittest.TestCase):
    def test_join(self):
        for rec, want in cases.JOIN_CASES:
            self.assertEqual(ml.join_status(rec, cases.JOIN_HF), want, rec)

    def test_keys(self):
        for row, want in cases.KEY_CASES:
            self.assertEqual(ml.keys_for(row), want, row)

    def test_family(self):
        self.assertEqual(ml.family("stemez-Biology"), "stemez")
        self.assertEqual(ml.family(""), "unknown")
        self.assertEqual(ml.family(None), "unknown")


class TestPredictions(unittest.TestCase):
    def test_all_held(self):
        # m1 weak and pulled, m2 strong and mildly pulled, m3 strong and not pulled. Median accuracy = 0.6.
        models = _models({
            "m1": (0.2, 1.5, 1.8, 1.1, 0.40, 0.6, 0.3),
            "m2": (0.6, 1.2, 1.3, 1.0, 0.70, 0.8, 0.7),
            "m3": (0.8, 0.9, 1.0, 0.8, 0.90, 0.95, 0.9),
        })
        p = ml.predictions(models, heuristic_biopsy=0.66)
        self.assertTrue(p["P1_error_pull_above_random_in_majority_of_models"])   # m1, m2 > 1: 2 of 3
        self.assertTrue(p["P2_error_pull_larger_on_stemez_in_majority_of_models"])  # all 3
        self.assertTrue(p["P3_stemez_biopsy_more_accurate_when_gold_longest_for_every_model"])
        self.assertTrue(p["P4_weaker_models_pulled_more"])  # below median: m1 1.5; at/above: (1.2+0.9)/2
        self.assertTrue(p["P5_quarter_of_models_below_pick_longest_on_stemez_biopsy"])  # m1 0.40 < 0.66

    def test_all_failed(self):
        models = _models({
            "m1": (0.2, 0.9, 0.8, 0.9, 0.70, 0.5, 0.6),
            "m2": (0.6, 1.2, 1.0, 1.1, 0.70, 0.8, 0.7),
            "m3": (0.8, 0.95, 1.0, 1.0, 0.90, 0.95, 0.9),
        })
        p = ml.predictions(models, heuristic_biopsy=0.66)
        self.assertFalse(p["P1_error_pull_above_random_in_majority_of_models"])   # only m2
        self.assertFalse(p["P2_error_pull_larger_on_stemez_in_majority_of_models"])  # none strictly larger
        self.assertFalse(p["P3_stemez_biopsy_more_accurate_when_gold_longest_for_every_model"])  # m1 gap < 0
        self.assertFalse(p["P4_weaker_models_pulled_more"])  # low 0.9 vs high (1.2+0.95)/2
        self.assertFalse(p["P5_quarter_of_models_below_pick_longest_on_stemez_biopsy"])  # none below 0.66


if __name__ == "__main__":
    unittest.main()
