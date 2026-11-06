"""Unit tests for audit 84 (standard library only). Every expectation below is traced by hand in the comments.
Apache-2.0."""

import unittest
from fractions import Fraction

import panel84 as pm
import cases84 as C


class TestCopiedPanel(unittest.TestCase):
    def test_panel_and_flags(self):
        # Same fixture and expected values as audits 77-79 (letters; Z and the out-of-range E count as no answer).
        panel = pm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
        self.assertEqual(panel, ["m1", "m2", "m3"])
        flags, _t = pm.panel_flags(panel, C.FIX_PREDS, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
        self.assertEqual(flags, C.FIX_TARGET["flags"])

    def test_votes(self):
        # Letters: A, B, B valid; None and 'Z' are no answer; 'E' is out of range for k=4.
        self.assertEqual(pm.votes(["A", "B", "b ", None, "Z", "E"], 4), ([1, 2, 0, 0], 3))

    def test_redux_join(self):
        labels, amb, mk, counts = pm.redux_labels(C.FIX_REDUX, C.FIX_MMLU, C.FIX_PRO)
        t = C.FIX_REDUX_TARGET
        self.assertEqual(labels, t["labels"])
        self.assertEqual(amb, t["ambiguous_ids"])
        self.assertEqual(mk, t["miskey_ids"])
        self.assertEqual(counts, t["counts"])


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


class TestCopiedStrataBudget(unittest.TestCase):
    def test_strata(self):
        # Ranked: a .9, b .8, c .8 (tie, by name), e .7, g .6, d .5, f .1 -> [a b] [c e] [g d]; f left over.
        self.assertEqual(pm.strata(C.FIX_S_ACC, 2, 3), C.FIX_S_TARGET)
        self.assertIsNone(pm.strata(C.FIX_S_ACC, 3, 3))

    def test_margins_letters(self):
        # Votes from letters: q1 key A, panel B B C -> counts [0,2,1,0], margin 2 - 0 = 2.
        questions = {1: (4, 0)}
        _f, tallies = pm.panel_flags(["x", "y", "z"], {"x": {1: "B"}, "y": {1: "B"}, "z": {1: "C"}}, questions, 2)
        self.assertEqual(tallies[1], ([0, 2, 1, 0], 0))
        self.assertEqual(pm.margins(tallies, questions), {1: 2})

    def test_budget_counts(self):
        # Levels: 3 -> {0, 1}; 1 -> {2, 3, 4}; -2 -> {5}. Sets: err {0, 2}, judged {0, 1, 2, 3}, miskey {0}.
        # K=4: level 3 whole (1, 2, 1; taken 2); level 1 straddles with f = 2/3: err +2/3, judged +4/3 -> 5/3, 10/3, 1.
        # K=2: level 3 only -> 1, 2, 1. K=0: nothing. K=10: everything -> 2, 4, 1.
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
        self.assertEqual(js["auc_miskey_vs_ok"], 0.75)


class TestNoKey(unittest.TestCase):
    def test_key_counts(self):
        # q1 key A: B, C, B -> covered 3, key 0. q2 key B: a B (key), b None (covered, no answer), c A -> 3, 1.
        # q3 k=3 key C: A, D (out of range), B -> 3, 0. q4 key D: only a, D -> 1, 1. q5 key A: only a, B -> 1, 0.
        kc = pm.key_counts(C.FIX_K_MODELS, C.FIX_K_PREDS, C.FIX_K_QUESTIONS)
        self.assertEqual(kc, C.FIX_K_COUNTS)

    def test_nk_and_share(self):
        # No-key with at least 2 covering: q1 and q3 only (q5 has no key pick but only 1 archive).
        # Share: q2 -1/3, q4 -1, others 0.
        self.assertEqual(pm.nk_flags(C.FIX_K_COUNTS, C.NK_MIN_COV), C.FIX_K_NK)
        self.assertEqual(pm.key_share(C.FIX_K_COUNTS), C.FIX_K_SHARE)
        self.assertEqual(pm.key_share({9: (0, 0)}), {9: Fraction(0)})


class TestVerdicts(unittest.TestCase):
    def test_verdicts(self):
        # S1 / S2 / S4: flags 10 / 12 / 20; budget precision 3/5, 2/5, 1/5; AUC S1 4/5, S4 7/10.
        # P2 20 > 10 yes. P3 3/5 > 2/5 > 1/5 yes. P4 4/5 > 7/10 yes. P5 base 1 of 20: 1 * 20 = 20 >= 2 * 1 * 5 = 10.
        # P6 top-20 3/5 <= 3/5 yes. P7 no-key judged 6 < 10 -> undecidable -> False.
        v = pm.predictions84(C.FIX_V_ST, C.FIX_V_TOP20, C.FIX_V_BASE[0], C.FIX_V_BASE[1], C.FIX_V_NK, C.FIX_V_UNAN,
                             C.THRESHOLDS)
        self.assertEqual(v, C.FIX_VERDICTS)

    def test_verdicts_flipped(self):
        # S2 raised to 3/5: 3/5 > 3/5 fails -> P3 False. Top-20 4/5 > 3/5 -> P6 False.
        # No-key 8 of 12 (12 >= 10) vs unanimous 3 of 6: 2/3 > 1/2 -> P7 True. Base 1 of 2: 20 >= 2*1*5? 1*2=2 < 10.
        st = list(C.FIX_V_ST)
        st[1] = C._st(12, Fraction(3, 4), 3, 5)
        top20 = C._st(9, Fraction(4, 5), 4, 5)
        v = pm.predictions84(st, top20, 1, 2, (8, 12), (3, 6), C.THRESHOLDS)
        self.assertFalse(v["P3_budget_precision_falls"])
        self.assertFalse(v["P6_top20_not_better"])
        self.assertTrue(v["P7_no_key_beats_unanimous"])
        self.assertFalse(v["P5_weakest_still_informative"])
        self.assertEqual(v["P6_precision"], [0.8, 0.6])
        self.assertEqual(v["P7_counts"], [8, 12, 3, 6])


class TestFrozen(unittest.TestCase):
    def test_rule_and_thresholds(self):
        self.assertEqual((C.PANEL_SIZE, C.MIN_AGREE, C.N_STRATA), (10, 6, 4))
        self.assertEqual((C.TOP20_SIZE, C.TOP20_MIN_AGREE, C.UNANIMOUS, C.NK_MIN_COV), (20, 12, 10, 2))
        self.assertEqual(C.THRESHOLDS, {"P5_mult": Fraction(2), "P7_min_judged": 10})
        self.assertEqual(C.EXPECTED_77_PRECISION, (65, 359))
        self.assertEqual(C.EXPECTED_77_FLAGGED["all"], 1210)
        self.assertEqual(len(C.EXPECTED_PANEL), 10)
        self.assertEqual(len(C.ARCHIVES), 48)
        names = {C.model_name(z) for z in C.ARCHIVES}
        self.assertTrue(set(C.EXPECTED_PANEL) <= names)
        self.assertEqual(C.WINDOW_STARTS, [0, 5, 10, 15, 20, 25, 30, 35])
        self.assertGreaterEqual(C.MIN_INCLUDED_ARCHIVES, C.N_STRATA * C.PANEL_SIZE)


if __name__ == "__main__":
    unittest.main()
