"""Unit tests for audit 83 (standard library only). Every expectation below is traced by hand in the comments.
Apache-2.0."""

import unittest
from fractions import Fraction

import panel83 as pm
import cases83 as C


def letters_to_indices(preds, questions):
    return {m: {q: pm.pred_index(p, questions[q][0]) for q, p in d.items()} for m, d in preds.items()}


class TestCopiedPanel(unittest.TestCase):
    def test_panel_and_flags(self):
        # Audit 77's fixture: letters become indices first (Z -> None; E is out of range for k=4 -> None).
        panel = pm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
        self.assertEqual(panel, ["m1", "m2", "m3"])
        idx = letters_to_indices(C.FIX_PREDS, C.FIX_QUESTIONS)
        self.assertIsNone(idx["m2"][6])
        self.assertIsNone(idx["m3"][6])
        flags, _t = pm.panel_flags(panel, idx, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
        self.assertEqual(flags, C.FIX_TARGET["flags"])

    def test_votes(self):
        self.assertEqual(pm.votes([0, 1, 1, None, 7], 4), ([1, 2, 0, 0], 2))


class TestCopiedHelm(unittest.TestCase):
    def test_select_runs(self):
        # As audit 80: x_a/anatomy keeps the run without model_deployment (1 duplicate dropped); the other method,
        # the valid split and the gsm run are ignored.
        self.assertEqual(pm.select_runs(C.FIX_RUNS), C.FIX_RUNS_TARGET)

    def test_universe_predictions_redux(self):
        # As audit 80: Q1 duplicated (dropped, 2 copies), Q3 without gold; qids anatomy/Q2 -> 0, V1 -> 1, V2 -> 2.
        parsed = {s: pm.parse_instances(items) for s, items in C.FIX_INST.items()}
        qids, info, counts = pm.build_universe(parsed)
        t = C.FIX_UNIVERSE_TARGET
        self.assertEqual((qids, info, counts), (t["qids"], t["info"], t["counts"]))
        for subj in ("virology", "anatomy"):
            self.assertEqual(pm.map_predictions(C.FIX_PRED[subj], parsed[subj], subj, qids),
                             C.FIX_PRED_TARGET[subj], subj)
        got = pm.redux_join(C.FIX_REDUX, qids, C.FIX_GOLD)
        self.assertEqual(got, C.FIX_REDUX_TARGET)
        self.assertEqual(pm.groups(3, got[0]), C.FIX_GROUPS_TARGET)


class TestCopiedMarginAuc(unittest.TestCase):
    def test_margin(self):
        # [2,5,3,0] key 0: 5 - 2 = 3. [6,1,1,2] key 0: 2 - 6 = -4. [0,0,10,0] key 2: 0 - 10. [4,4,1,1] key 3: 4 - 1.
        for (counts, key), want in C.FIX_MARGIN:
            self.assertEqual(pm.margin(counts, key), want)

    def test_auc(self):
        # pos [3, 1] vs neg [1, 0, -4]: 3 beats all three (3); 1 ties 1 (1/2), beats 0 and -4 (2) -> 5.5/6 = 11/12.
        # pos [0.9, 0.2] vs neg [0.5, 0.3, -0.4, -0.6]: 4 + 2 = 6 of 8 = 3/4.
        # pos [6, 2] vs neg [4, 2, -8, -10]: 4 + (1/2 + 2) = 6.5 of 8 = 13/16. One tie: 1/2. Empty: None.
        for (pos, neg), want in C.FIX_AUC:
            self.assertEqual(pm.auc(pos, neg), want)


class TestStrata(unittest.TestCase):
    def test_strata(self):
        # Ranked: a .9, b .8, c .8 (tie, by name), e .7, g .6, d .5, f .1 -> [a b] [c e] [g d]; f left over.
        self.assertEqual(pm.strata(C.FIX_S_ACC, 2, 3), C.FIX_S_TARGET)
        # 3 panels of 3 need 9 models; there are 7.
        self.assertIsNone(pm.strata(C.FIX_S_ACC, 3, 3))

    def test_margins(self):
        # q1 key 0 votes [2,5,3,0] -> 3; q2 key 2 votes [0,0,10,0] -> -10.
        tallies = {1: ([2, 5, 3, 0], 0), 2: ([0, 0, 10, 0], 0)}
        questions = {1: (4, 0), 2: (4, 2)}
        self.assertEqual(pm.margins(tallies, questions), {1: 3, 2: -10})


class TestBudget(unittest.TestCase):
    def test_budget_counts(self):
        # Levels: 3 -> {0, 1}; 1 -> {2, 3, 4}; -2 -> {5}. Sets: err {0, 2}, judged {0, 1, 2, 3}, miskey {0}.
        # K=4: level 3 whole (err 1, judged 2, miskey 1, taken 2); level 1 straddles: 2 of 3 places -> f = 2/3;
        #   err +2/3 (q2) = 5/3; judged +2/3 * 2 (q2, q3) = 10/3; miskey stays 1.
        # K=2: level 3 whole, then stop -> 1, 2, 1. K=0: nothing. K=10: everything -> 2, 4, 1.
        for budget, want in C.FIX_B_CASES:
            self.assertEqual(pm.budget_counts(C.FIX_B_SCORE, C.FIX_B_SETS, budget), want, budget)

    def test_stratum_stats(self):
        # Flags q0, q2, q5 -> 3; precision: err q0 (miskey) + q5 (other) = 2, judged + q2 (OK) = 3; miskeys 1.
        # AUC miskey scores [4, 0] vs OK [4, -6, -2]: 4 -> 1/2 + 2; 0 -> 2; 4.5 of 6 = 3/4.
        # Budget 3: level 4 -> {q0, q2}: err 1, judged 2, miskey 1; level 1 -> {q5}: err 2, judged 3. Stop.
        got = pm.stratum_stats(C.FIX_P_FLAGS, C.FIX_P_SCORE, C.FIX_P_G, C.FIX_P_BUDGET)
        self.assertEqual(got, C.FIX_P_TARGET)
        js = pm.stats_json(got)
        self.assertEqual(js["budget"], {"error_labelled": "2", "judged": "3", "miskeys": "1",
                                        "precision": float(Fraction(2, 3))})
        self.assertEqual(js["precision"][:2], [2, 3])
        self.assertEqual(js["auc_miskey_vs_ok"], 0.75)


class TestVerdicts(unittest.TestCase):
    def test_verdicts(self):
        # S1 / S4 / S7: flags 10 / 15 / 30; AUC 4/5, 7/10, 7/10; budget precision 3/5, 2/5, 1/5.
        # P2 30 > 10 yes. P3 needs 4/5 > 7/10 > 7/10 -> no (tie). P4 3/5 > 2/5 > 1/5 yes.
        # P5: base 1 of 20; S7 1 * 20 = 20 >= 2 * 1 * 5 = 10 yes. P6: top-20 3/5 > 3/5 no.
        v = pm.predictions83(C.FIX_V_ST, C.FIX_V_TOP20, C.FIX_V_BASE[0], C.FIX_V_BASE[1], C.THRESHOLDS)
        self.assertEqual(v, C.FIX_VERDICTS)

    def test_verdicts_flipped(self):
        # S4's AUC raised to 3/4: 4/5 > 3/4 > 7/10 -> P3 holds. Top-20 at 4/5 > 3/5 -> P6 holds.
        # Base 1 of 2 (50%): S7 1 * 2 = 2 >= 2 * 1 * 5 = 10? no -> P5 fails.
        st = list(C.FIX_V_ST)
        st[3] = C._st(15, Fraction(3, 4), 2, 5)
        top20 = C._st(9, Fraction(4, 5), 4, 5)
        v = pm.predictions83(st, top20, 1, 2, C.THRESHOLDS)
        self.assertTrue(v["P3_auc_falls_with_strength"])
        self.assertTrue(v["P6_top20_beats_top10"])
        self.assertFalse(v["P5_weakest_still_informative"])
        self.assertEqual(v["P6_precision"], [0.8, 0.6])


class TestFrozen(unittest.TestCase):
    def test_rule_and_thresholds(self):
        self.assertEqual((C.PANEL_SIZE, C.MIN_AGREE, C.N_STRATA), (10, 6, 7))
        self.assertEqual((C.TOP20_SIZE, C.TOP20_MIN_AGREE), (20, 12))
        self.assertEqual(C.THRESHOLDS["P5_mult"], Fraction(2))
        self.assertEqual(C.EXPECTED_80["precision"], (130, 484))
        self.assertEqual(C.EXPECTED_80["flagged"]["all"], 1207)
        self.assertEqual(len(C.EXPECTED_80["panel"]), 10)
        self.assertEqual(C.WINDOW_STARTS[0], 0)
        self.assertEqual(C.WINDOW_STARTS[-1], 68)


if __name__ == "__main__":
    unittest.main()
