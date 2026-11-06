"""Unit tests for audit 82 (standard library only). Every expectation below is traced by hand in the comments.
Apache-2.0."""

import unittest
from fractions import Fraction

import disc82 as dm
import cases82 as C


def letters_to_indices(preds, questions):
    return {m: {q: dm.pred_index(p, questions[q][0]) for q, p in d.items()} for m, d in preds.items()}


class TestCopiedPanel(unittest.TestCase):
    def test_panel_and_flags(self):
        # Audit 77's fixture: letters become indices first (Z -> None; E is out of range for k=4 -> None).
        panel = dm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
        self.assertEqual(panel, ["m1", "m2", "m3"])
        idx = letters_to_indices(C.FIX_PREDS, C.FIX_QUESTIONS)
        self.assertIsNone(idx["m2"][6])
        self.assertIsNone(idx["m3"][6])
        flags, _t = dm.panel_flags(panel, idx, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
        self.assertEqual(flags, C.FIX_TARGET["flags"])

    def test_votes(self):
        self.assertEqual(dm.votes([0, 1, 1, None, 7], 4), ([1, 2, 0, 0], 2))


class TestCopiedHelm(unittest.TestCase):
    def test_select_runs(self):
        # As audit 80: x_a/anatomy keeps the run without model_deployment (1 duplicate dropped); the other method,
        # the valid split and the gsm run are ignored.
        self.assertEqual(dm.select_runs(C.FIX_RUNS), C.FIX_RUNS_TARGET)

    def test_universe_predictions_redux(self):
        # As audit 80: Q1 duplicated (dropped, 2 copies), Q3 without gold; qids anatomy/Q2 -> 0, V1 -> 1, V2 -> 2.
        parsed = {s: dm.parse_instances(items) for s, items in C.FIX_INST.items()}
        qids, info, counts = dm.build_universe(parsed)
        t = C.FIX_UNIVERSE_TARGET
        self.assertEqual((qids, info, counts), (t["qids"], t["info"], t["counts"]))
        for subj in ("virology", "anatomy"):
            self.assertEqual(dm.map_predictions(C.FIX_PRED[subj], parsed[subj], subj, qids),
                             C.FIX_PRED_TARGET[subj], subj)
        got = dm.redux_join(C.FIX_REDUX, qids, C.FIX_GOLD)
        self.assertEqual(got, C.FIX_REDUX_TARGET)
        self.assertEqual(dm.groups(3, got[0]), C.FIX_GROUPS_TARGET)

    def test_restrict(self):
        self.assertEqual(dm.restrict({"miskey": [1, 2], "ok": [3, 5]}, {2, 3}), {"miskey": [2], "ok": [3]})


class TestDiscrimination(unittest.TestCase):
    def test_pearson(self):
        # x = [1, 1, 0, 0], y = [7, 5, 4, 2] / 9: deviations x +-1/2, y (5, 1, -1, -5)/18; sxy = 1/3, sxx = 1,
        # syy = 52/324 = 13/81 -> r = (1/3) / (sqrt(13)/9) = 3/sqrt(13).
        self.assertAlmostEqual(dm.pearson([1, 1, 0, 0], [7 / 9, 5 / 9, 4 / 9, 2 / 9]), 3 / 13 ** 0.5, places=12)
        self.assertIsNone(dm.pearson([1, 1, 1], [0.1, 0.2, 0.3]))
        self.assertIsNone(dm.pearson([1], [0.5]))

    def test_discrimination(self):
        # Rest accuracy y = (correct - x) / (covered - 1); A 8/10, B 6/10, C 4/10, D 2/10.
        # q0 key 0: A 0 yes, B 0 yes, C 1 no, D 3 no -> x [1,1,0,0], y [7,5,4,2]/9 -> 3/sqrt(13).
        # q1 key 1: A 3 no, B None no, C 1 yes, D 1 yes -> x [0,0,1,1], y [8,6,3,1]/9; deviations x -+1/2,
        #   y (7, 3, -3, -7)/18; sxy = -20/36 = -5/9, syy = 116/324 = 29/81 -> -5/sqrt(29).
        # q2 key 2: everyone picks 2 -> all_correct -> +1.
        # q3 key 0: D has no prediction; A yes, B no (1), C yes -> x [1,0,1], y [7,6,3]/9; mean x 2/3, mean y 16/27;
        #   x dev (1/3, -2/3, 1/3), y dev (5, 2, -7)/27; sxy = (5 - 4 - 7)/81 = -2/27; sxx = 2/3; syy = 78/729
        #   -> r = (-2/27) / sqrt(52/729) = -2/sqrt(52) = -1/sqrt(13).
        # q4 key 0: picks 1, 1, 2, None -> all_wrong -> -1.
        r, n_models, n_key, counts = dm.discrimination(C.FIX_D_MODELS, C.FIX_D_PREDS, C.FIX_D_ACC, C.FIX_D_GOLD, 5)
        for got, want in zip(r, C.FIX_D_R):
            self.assertAlmostEqual(got, want, places=12)
        self.assertEqual(len(r), 5)
        self.assertEqual(n_models, C.FIX_D_N_MODELS)
        self.assertEqual(n_key, C.FIX_D_N_KEY)
        self.assertEqual(counts, C.FIX_D_COUNTS)

    def test_rank_and_neg_flags(self):
        # r: q0 0.832, q1 -0.928, q2 1.0, q3 -0.277, q4 -1.0 -> order q4, q1, q3, q0, q2; budget 2 -> {q4, q1};
        # r < 0 -> {q1, q3, q4}.
        self.assertEqual(dm.rank_order(C.FIX_D_R), C.FIX_D_ORDER)
        self.assertEqual(dm.rank_flags(C.FIX_D_R, 2), C.FIX_D_RANK2)
        self.assertEqual(dm.neg_flags(C.FIX_D_R), C.FIX_D_NEG)
        # ties keep id order
        self.assertEqual(dm.rank_order([0.5, -0.5, -0.5]), [1, 2, 0])


class TestMarginAuc(unittest.TestCase):
    def test_margin(self):
        # [2,5,3,0] key 0: 5 - 2 = 3. [6,1,1,2] key 0: 2 - 6 = -4. [0,0,10,0] key 2: 0 - 10. [4,4,1,1] key 3: 4 - 1.
        for (counts, key), want in C.FIX_MARGIN:
            self.assertEqual(dm.margin(counts, key), want)

    def test_auc(self):
        # pos [3, 1] vs neg [1, 0, -4]: 3 beats all three (3); 1 ties 1 (1/2), beats 0 and -4 (2) -> 5.5/6 = 11/12.
        # pos [0.9, 0.2] vs neg [0.5, 0.3, -0.4, -0.6]: 4 + 2 = 6 of 8 = 3/4.
        # pos [6, 2] vs neg [4, 2, -8, -10]: 4 + (1/2 + 2) = 6.5 of 8 = 13/16. One tie: 1/2. Empty: None.
        for (pos, neg), want in C.FIX_AUC:
            self.assertEqual(dm.auc(pos, neg), want)


class TestVerdicts(unittest.TestCase):
    def test_precisions(self):
        # budget: miskey 1 + other 7 = 2 error-labelled; OK 4 -> (2, 3). consensus: miskey 1, 2; OK 3, 4 -> (2, 4).
        self.assertEqual(dm.flag_precision(C.FIX_V_BUDGET, C.FIX_V_G), (2, 3))
        self.assertEqual(dm.flag_precision(C.FIX_V_CONS, C.FIX_V_G), (2, 4))
        self.assertEqual(dm.both(C.FIX_V_CONS, C.FIX_V_BUDGET)[4], (True, None))
        self.assertEqual(dm.both(C.FIX_V_CONS, C.FIX_V_BUDGET)[7], (False, None))

    def test_verdicts(self):
        # P2: miskeys with r < 0: 2 of 2; OK: 1 of 4 (q3) -> 2 * 4 = 8 >= 5 * 1 * 2 = 10? no.
        # P3: 2/3 > 2/4 yes. P4: AUC(-r) 3/4 vs AUC(margin) 13/16 -> no.
        # P5: both = {1, 4, 8}: miskey 1, OK 4 -> (1, 2); 1/2 > 2/3? no -> False.
        # P6 (no virology): budget miskey 1 + other 7, OK 4 -> (2, 3); consensus miskey 1, OK 3, 4 -> (1, 3) -> yes.
        v = dm.predictions82(C.FIX_V_G, C.FIX_V_GX, C.FIX_V_CONS, C.FIX_V_BUDGET, C.FIX_V_NEG, C.FIX_V_SDISC,
                             C.FIX_V_SCONS, C.THRESHOLDS)
        self.assertEqual(v, C.FIX_VERDICTS)


class TestFrozen(unittest.TestCase):
    def test_rule_and_thresholds(self):
        self.assertEqual((C.PANEL_SIZE, C.MIN_AGREE), (10, 6))
        self.assertEqual(C.THRESHOLDS["P2_ratio"], Fraction(5))
        self.assertEqual(C.EXPECTED_80["precision"], (130, 484))
        self.assertEqual(C.EXPECTED_80["flagged"]["all"], 1207)
        self.assertEqual(len(C.EXPECTED_80["panel"]), 10)


if __name__ == "__main__":
    unittest.main()
