"""Unit tests for audit 85 (standard library only). Every expectation below is traced by hand in the comments.
Apache-2.0."""

import unittest
from fractions import Fraction

import queue85 as qm
import cases85 as C


def letters_to_indices(preds, questions):
    return {m: {q: qm.pred_index(p, questions[q][0]) for q, p in d.items()} for m, d in preds.items()}


def fixture_panel():
    idx = letters_to_indices(C.FIX_PREDS, C.FIX_QUESTIONS)
    panel = qm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
    flags, tallies = qm.panel_flags(panel, idx, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
    return idx, panel, flags, tallies


class TestCopied(unittest.TestCase):
    def test_panel_and_flags(self):
        # Audit 77's fixture: Z -> None; E is out of range for k=4 -> None.
        idx, panel, flags, _t = fixture_panel()
        self.assertEqual(panel, C.FIX_TARGET["panel"])
        self.assertIsNone(idx["m2"][6])
        self.assertIsNone(idx["m3"][6])
        self.assertEqual(flags, C.FIX_TARGET["flags"])

    def test_helm_and_redux(self):
        # As audits 80-83: run selection, universe (Q1 duplicated -> dropped, Q3 no gold), mapping, Redux join.
        self.assertEqual(qm.select_runs(C.FIX_RUNS), C.FIX_RUNS_TARGET)
        parsed = {s: qm.parse_instances(items) for s, items in C.FIX_INST.items()}
        qids, info, counts = qm.build_universe(parsed)
        t = C.FIX_UNIVERSE_TARGET
        self.assertEqual((qids, info, counts), (t["qids"], t["info"], t["counts"]))
        for subj in ("virology", "anatomy"):
            self.assertEqual(qm.map_predictions(C.FIX_PRED[subj], parsed[subj], subj, qids),
                             C.FIX_PRED_TARGET[subj], subj)
        got = qm.redux_join(C.FIX_REDUX, qids, C.FIX_GOLD)
        self.assertEqual(got, C.FIX_REDUX_TARGET)
        self.assertEqual(qm.groups(3, got[0]), C.FIX_GROUPS_TARGET)

    def test_margin(self):
        # [2,5,3,0] key 0: 5 - 2 = 3. [0,0,10,0] key 2: 0 - 10.
        self.assertEqual(qm.margin([2, 5, 3, 0], 0), 3)
        self.assertEqual(qm.margin([0, 0, 10, 0], 2), -10)


class TestTiers(unittest.TestCase):
    def test_key_pickers(self):
        # Over all five models. q1 key A: only m3 -> 1. q2 key C: m1, m5 -> 2. q3 key A: m3 -> 1. q4 key B: m1, m2
        # -> 2 (m3's None still covers). q5 key D: m3 -> 1. q6 key A: B, None, None, B, B -> 0. q7 key A: C C C B C
        # -> 0. q8 all A -> 5. Every model covers every question -> 5. No-key: q6, q7.
        idx = letters_to_indices(C.FIX_PREDS, C.FIX_QUESTIONS)
        counts, nokey = qm.key_pickers(idx, sorted(C.FIX_ACC), C.FIX_QUESTIONS)
        self.assertEqual(counts, C.FIX_KEY_COUNTS)
        self.assertEqual(nokey, C.FIX_NOKEY)

    def test_key_pickers_needs_two_models(self):
        # One covering model that misses the key is not enough for the no-key set.
        counts, nokey = qm.key_pickers({"m": {0: 1}}, ["m", "absent"], {0: (4, 0)})
        self.assertEqual(counts, {0: (1, 0)})
        self.assertEqual(nokey, set())

    def test_tier_of(self):
        for args, want in C.FIX_TIER_OF:
            self.assertEqual(qm.tier_of(*args), want, args)

    def test_assign_tiers(self):
        # Panel m1-m3, flags as audit 77. No-key set {6}. q1 votes [1,2,0,0] flagged, top 2 of 3 -> T3; q2 [0,0,1,2]
        # -> T3; q5 [2,0,0,1] -> T3; q7 [0,0,3,0] flagged with all 3 -> T2; q6 -> T1; q3, q4, q8 unflagged -> T0.
        _idx, _p, flags, tallies = fixture_panel()
        self.assertEqual(qm.assign_tiers(flags, tallies, C.FIX_TIER_NOKEY, C.FIX_PANEL_SIZE), C.FIX_TIERS)


class TestQueue(unittest.TestCase):
    def test_queue_rows(self):
        # Tiers 1-3: q6 (T1), q7 (T2), q1, q2, q5 (T3, all margin 1). Within T3: picks of the key q1 1, q5 1, q2 2
        # -> q1 (position 1), q5 (position 5), q2. q6: votes [0,1,0,0], 2 unanswered (Z, E), margin 1 - 0 = 1.
        _idx, _p, flags, tallies = fixture_panel()
        rows = qm.queue_rows(sorted(C.FIX_QUESTIONS), C.FIX_TIERS, flags, tallies, C.FIX_KEY_COUNTS, C.FIX_Q_INFO)
        self.assertEqual([r["qid"] for r in rows], C.FIX_Q_ORDER)
        self.assertEqual(rows[0], C.FIX_Q_FIRST)
        self.assertEqual([r["rank"] for r in rows], [1, 2, 3, 4, 5])
        self.assertEqual(rows[1]["margin"], 3)


class TestFoldsAndRates(unittest.TestCase):
    def test_fold_of(self):
        # Deterministic, 0 or 1, and balanced: 2,000 keys give 1,000 +- 100 ones (about 4.5 standard deviations).
        self.assertEqual(qm.fold_of("virology", "id21"), qm.fold_of("virology", "id21"))
        ones = sum(qm.fold_of("s", "id%d" % i) for i in range(2000))
        self.assertTrue(all(qm.fold_of("s", "id%d" % i) in (0, 1) for i in range(50)))
        self.assertTrue(900 <= ones <= 1100, ones)

    def test_rates(self):
        # Fold 0's training half = judged questions of fold 1: q1 (T2, OK), q3 (T0), q5 (T3, miskey), q7 (T0).
        # T2 0/1, T0 0/2, T3 1/1; pooled 1/4.
        got = qm.rates(C.FIX_CF_TIERS, C.FIX_CF_TARGET, C.FIX_CF_JUDGED,
                       {q for q in C.FIX_CF_JUDGED if C.FIX_FOLD[q] == 1})
        self.assertEqual(got, C.FIX_RATES_F0)

    def test_cross_fold(self):
        # Fold 0 test q0 (T1, a, miskey), q2 (T3, a), q6 (T0, b), q8 (T0, b), q9 (T2, b, miskey) -> actual 2.
        #   Tier: q0 has no T1 rate -> pooled 1/4; q2 -> 1; others 0 -> expected 5/4; variance 1/4 * 3/4 = 3/16
        #   (T1 had no judged question, so no rate term; rates 0 and 1 add nothing).
        #   Subject rates from fold 1: a 0/2, b 1/2 -> 0 + 0 + 3 * 1/2 = 3/2.
        #   Per subject: tier a 5/4 vs 1 -> 1/4, b 0 vs 1 -> 1: 5/4. Subject a 0 vs 1 -> 1, b 3/2 vs 1 -> 1/2: 3/2.
        # Fold 1 test q1 (T2, a), q3 (T0, a), q5 (T3, b, miskey), q7 (T0, b) -> actual 1. Rates from fold 0: T1 1/1,
        #   T3 0/1, T0 0/2, T2 1/1; a 1/2, b 1/3. Tier: 1 + 0 + 0 + 0 = 1, variance 0. Subject: 1/2 + 1/2 + 1/3 +
        #   1/3 = 5/3. Per subject: tier a 1 vs 0, b 0 vs 1 -> 2; subject a 1 vs 0, b 2/3 vs 1 -> 4/3.
        got = qm.cross_fold(C.FIX_CF_TIERS, C.FIX_SUBJ, C.FIX_FOLD, C.FIX_CF_TARGET, C.FIX_CF_JUDGED)
        self.assertEqual(got, C.FIX_CF)

    def test_estimate(self):
        # Cells: 0 -> q3, q7 (n 2, r 1/10, judged 10); 1 -> q2 (n 1, r 1/2, judged 2); 3 -> q6 (no rate: pooled 1/5,
        # judged 0). Expected 1/5 + 1/2 + 1/5 = 9/10. Variance: cell 0: 2 * 9/100 + 4/10 * 9/100 = 27/125;
        # cell 1: 1/4 + 1/2 * 1/4 = 3/8; cell 3: 4/25 (no rate term). 0.216 + 0.375 + 0.16 = 0.751.
        got = qm.estimate(C.FIX_E_CELLS, C.FIX_E_RATE, C.FIX_E_POOLED, C.FIX_E_DEN, C.FIX_E_QS)
        self.assertEqual(got, C.FIX_E_TARGET)

    def test_transport(self):
        # Reviewed: a q0 (flagged), q1 -> 1/2; b q4, q5 -> 0. Unreviewed: a q2, q3 (both flagged), b q6 (flagged),
        # c q7 (no reviewed question -> skipped). Observed 2 + 1 = 3; expected 2 * 1/2 + 1 * 0 = 1.
        # Variance a: 4/2 * 1/4 + 2 * 1/4 = 1; b: 0.
        got = qm.transport(C.FIX_T_FLAGGED, C.FIX_T_SUBJ, C.FIX_T_REVIEWED, C.FIX_T_UNREVIEWED)
        self.assertEqual(got, C.FIX_T_TARGET)

    def test_wilson(self):
        # 5 of 10: centre 0.5, half-width 1.96 * sqrt(0.025 + 0.009604) / 1.38416 = 0.2634 -> 0.2366 to 0.7634.
        lo, hi = qm.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=3)
        self.assertAlmostEqual(hi, 0.7634, places=3)
        self.assertIsNone(qm.wilson(0, 0))
        lo0, hi0 = qm.wilson(0, 20)
        self.assertAlmostEqual(lo0, 0.0, places=9)
        self.assertTrue(0 < hi0 < 0.2)


class TestVerdicts(unittest.TestCase):
    def test_verdicts(self):
        # P2: tier 5/4 + 2 = 13/4 = 3.25 vs subject 3/2 + 4/3 = 17/6 = 2.83 -> not smaller -> False.
        # P3: fold 0 (2 - 5/4)^2 = 0.5625 <= 3.8416 * 0.1875 = 0.7203; fold 1 0 <= 0 -> True.
        # P4: (3 - 1)^2 = 4 > 3.8416 * 1 -> False. P5: 2/3 > 1/2 > 1/4 > 0 -> True.
        tr = qm.transport(C.FIX_T_FLAGGED, C.FIX_T_SUBJ, C.FIX_T_REVIEWED, C.FIX_T_UNREVIEWED)
        v = qm.predictions85(C.FIX_CF, tr, C.FIX_V_RATES, C.Z2)
        self.assertEqual(v, C.FIX_VERDICTS)

    def test_verdicts_flipped(self):
        # Subject errors raised to 4 per fold -> 13/4 < 8 -> P2 True. Tier rates tied (1/2, 1/2) -> P5 False.
        # A missing rate -> P5 False.
        folds = [dict(f, mae_subject=Fraction(4)) for f in C.FIX_CF]
        tr = (1, Fraction(1), Fraction(1), [])
        v = qm.predictions85(folds, tr, [Fraction(1, 2), Fraction(1, 2), Fraction(1, 4), Fraction(0)], C.Z2)
        self.assertTrue(v["P2_tier_beats_subject"])
        self.assertTrue(v["P4_transport"])
        self.assertFalse(v["P5_tiers_ordered"])
        v2 = qm.predictions85(folds, tr, [None, Fraction(1, 2), Fraction(1, 4), Fraction(0)], C.Z2)
        self.assertFalse(v2["P5_tiers_ordered"])


class TestFrozen(unittest.TestCase):
    def test_rule_and_gates(self):
        self.assertEqual((C.PANEL_SIZE, C.MIN_AGREE), (10, 6))
        self.assertEqual(C.Z2, Fraction(38416, 10000))
        self.assertEqual(C.EXPECTED_80["precision"], (130, 484))
        self.assertEqual(C.EXPECTED_80["flagged"]["all"], 1207)
        self.assertEqual(len(C.EXPECTED_80["panel"]), 10)
        self.assertEqual(C.EXPECTED_82_NOKEY["all"], 88)
        self.assertEqual(sum(v for k, v in C.EXPECTED_82_NOKEY.items() if k != "all"), 88)


if __name__ == "__main__":
    unittest.main()
