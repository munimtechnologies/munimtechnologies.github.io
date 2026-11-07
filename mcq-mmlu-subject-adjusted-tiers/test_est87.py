"""Unit tests for audit 87 (standard library only). Run: python -m unittest -v. Apache-2.0.

Hand trace of fixture A (two subjects a = q0-q5 and b = q6-q11; tiers T1, T3, T0 repeating; wrong keys
{0, 3, 6, 7, 8, 9, 10}; fold 0 = q0-q2 and q6-q8):
- Fold 0 is fitted on fold 1 = {3, 4, 5, 9, 10, 11}. Tier rates: T1 2/2 = 1, T3 1/2 (q10 of q4, q10), T0 0/2;
  pooled 3/6. Subject a: O = 1 (q3), E = 1 + 1/2 + 0 = 3/2, k = (1 + 1) / (3/2 + 1) = 4/5. Subject b: O = 2 (q9, q10),
  E = 3/2, k = 3 / (5/2) = 6/5. Predictions: q0 4/5, q1 2/5, q2 0, q6 min(6/5, 1) = 1, q7 3/5, q8 0. Subject a:
  6/5 predicted vs 1 actual; b: 8/5 vs 3 -> error 1/5 + 7/5 = 8/5; total 14/5 against 4 actual.
- Fold 1 is fitted on fold 0 = {0, 1, 2, 6, 7, 8}. Tier rates: T1 1, T3 1/2 (q7), T0 1/2 (q8); pooled 4/6. a: O = 1,
  E = 2, k = 2/3; b: O = 3, E = 2, k = 4/3. Predictions: q3 2/3, q4 1/3, q5 1/3 (a: 4/3 vs 1); q9 min(4/3, 1) = 1,
  q10 2/3, q11 2/3 (b: 7/3 vs 2) -> error 1/3 + 1/3 = 2/3; total 11/3 against 3 actual.
- base87.cross_fold: subject rates fold 0 a 1/3, b 2/3 -> errors 0 + 1; tiers 1/2 + 3/2 = 2. Fold 1: subject a 1/3,
  b 1 -> 0 + 1; tiers (a 2 vs 1, b 2 vs 2) -> 1.
- Verdicts (fixture C): adjusted 8/5 + 2/3 = 34/15 is not below subject 2 (P2 false); fold 1's actual 3 is outside
  (0, 2) (P3 false); 4 < 5 < 7 (P4 true); 1/2 + 1/4 < 1 + 0 (P5 true).
- Bootstrap: with no target every probability is 0 (interval (0, 0)); with every question in T1 and in the target,
  rates are 1.0 and k = (3 + 1) / (3 + 1) = 1.0, so every draw hits (interval (6, 6)).
"""

import unittest
from fractions import Fraction

import base87 as qm
import cases87 as C
import est87 as em


class TestAdjusted(unittest.TestCase):
    def test_rates_fold0(self):
        rate, pooled, den = qm.rates(C.FIX_TIERS, C.FIX_TARGET, C.FIX_JUDGED, C.FIX_TRAIN_F0)
        self.assertEqual(rate, C.FIX_RATE_F0)
        self.assertEqual(pooled, C.FIX_POOLED_F0)
        self.assertEqual(den, {1: 2, 3: 2, 0: 2})

    def test_factors_fold0(self):
        fac = em.subject_factors(C.FIX_TIERS, C.FIX_SUBJ, C.FIX_TARGET, C.FIX_JUDGED, C.FIX_TRAIN_F0,
                                 C.FIX_RATE_F0, C.FIX_POOLED_F0, C.PRIOR)
        self.assertEqual(fac, C.FIX_FACTORS_F0)

    def test_adjusted_predict_caps_at_one(self):
        p = em.adjusted_predict(C.FIX_TIERS, C.FIX_SUBJ, C.FIX_RATE_F0, C.FIX_POOLED_F0, C.FIX_FACTORS_F0,
                                [0, 1, 2, 6, 7, 8])
        self.assertEqual(p, {0: Fraction(4, 5), 1: Fraction(2, 5), 2: Fraction(0), 6: Fraction(1),
                             7: Fraction(3, 5), 8: Fraction(0)})

    def test_missing_subject_factor_is_one(self):
        p = em.adjusted_predict({0: 3}, {0: "z"}, {3: Fraction(1, 4)}, Fraction(1, 2), {}, [0])
        self.assertEqual(p, {0: Fraction(1, 4)})

    def test_cross_fold_adjusted(self):
        out = em.cross_fold_adjusted(C.FIX_TIERS, C.FIX_SUBJ, C.FIX_FOLD, C.FIX_TARGET, C.FIX_JUDGED, C.PRIOR)
        self.assertEqual(out, C.FIX_ADJ)

    def test_base_cross_fold(self):
        out = qm.cross_fold(C.FIX_TIERS, C.FIX_SUBJ, C.FIX_FOLD, C.FIX_TARGET, C.FIX_JUDGED)
        self.assertEqual([(f["mae_subject"], f["mae_tier"]) for f in out], C.FIX_BASE_MAE)
        self.assertEqual([f["actual"] for f in out], [4, 3])


class TestBootstrap(unittest.TestCase):
    def test_pct_bounds(self):
        for b, want in C.FIX_PCT:
            self.assertEqual(em.pct_bounds(b), want)

    def test_no_target(self):
        lo, hi, tot = em.bootstrap_total(C.FIX_TIERS, C.FIX_SUBJ, set(), C.FIX_JUDGED, list(range(12)), C.PRIOR,
                                         40, 1)
        self.assertEqual((lo, hi), (0, 0))
        self.assertEqual(len(tot), 40)

    def test_all_target(self):
        lo, hi, tot = em.bootstrap_total(C.FIX_B_TIERS, C.FIX_B_SUBJ, set(range(6)), set(range(6)),
                                         list(range(6)), C.PRIOR, 40, 1)
        self.assertEqual((lo, hi), (6, 6))
        self.assertEqual(set(tot), {6})

    def test_deterministic(self):
        a = em.bootstrap_total(C.FIX_TIERS, C.FIX_SUBJ, C.FIX_TARGET, C.FIX_JUDGED, list(range(12)), C.PRIOR, 40, 5)
        b = em.bootstrap_total(C.FIX_TIERS, C.FIX_SUBJ, C.FIX_TARGET, C.FIX_JUDGED, list(range(12)), C.PRIOR, 40, 5)
        self.assertEqual(a, b)
        self.assertTrue(0 <= a[0] <= a[1] <= 12)


class TestVerdicts(unittest.TestCase):
    def test_verdicts(self):
        adj, tier, subj = C.FIX_V_EST
        v = em.predictions87(C.FIX_ADJ, C.FIX_V_BASE, C.FIX_V_ADJ_ERR, C.FIX_V_BASE_ERR, C.FIX_V_BOOT, adj, tier,
                             subj)
        self.assertEqual(v, C.FIX_VERDICTS)


if __name__ == "__main__":
    unittest.main()
