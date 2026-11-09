"""Unit tests for audit 94 (standard library only). Apache-2.0.

Hand traces (cases94.FIX_*):
- build_inst_map skips the perturbed copy of id1; id1 correct [1]; id2 correct [0], texts x / y / 'x ' -> dup True
  ('x '.strip() == 'x'); id3 correct [0]; id4 correct [1]; split 'valid'.
- r1 em 1, pi 1 in [1] -> plain, F 1. r2 em 1, pi 2 not in [0] -> old_tie, F 0. r3 em 0.5 -> frac, F 0.
  r4 em 0, pi 0 not in [1] -> plain, F 0. r5 (mild_mix) em 0, pi 1 in [1] -> inconsistent. r6 (mild_mix) em 0.25 ->
  frac (pi 1 in [1], F 1). r7 trial 1, em 1, pi 0 in [0] -> plain, F 1. r8 id9 -> unmatched, F = em = 1.
- Unperturbed, all trials: r1 r2 r3 r4 r7 r8 -> n 6, published 1+1+0.5+0+1+1 = 4.5, F 1+0+0+0+1+1 = 3.
  First trial: r1 r2 r3 r4 r8 -> n 5, published 3.5, F 2.
- reproduce: 4.5/6 = 0.75 -> 'all'; 3.5/5 = 0.7 -> 't0'; 0.6 -> fail; num_instances 4 != 5 -> fail.
- ranks: a 0.9 -> 1; b, c 0.8 -> 2 (one higher); d 0.5 -> 4 (three higher).
- top 3 of {5, 1, 3, 2} = 10.
- verdicts: case 1 ties 5, 5/1000 <= 1%, 4/5 >= 1/2, 0.02 >= 0.01, 3/5 >= 1/2 -> all True. Case 2 no ties -> only
  P4 True. Case 3 frac 2 -> P3 False; 5/100 > 1% -> P4 False; 2/5 < 1/2 -> P5, P7 False; 0.005 -> P6 False.
"""

import unittest

import cases94 as C
import grade94 as g


class TestGrade(unittest.TestCase):
    def test_names(self):
        for run, model, method, group, scen in C.FIX_NAMES:
            self.assertEqual(g.model_of(run), model)
            self.assertEqual(g.method_of(run), method)
            self.assertEqual(g.group_of(run), group)
            self.assertEqual(g.scenario_of(run), scen)
        self.assertIn(g.method_of(C.FIX_NAMES[0][0]), g.SEPARATE)
        self.assertNotIn(g.method_of(C.FIX_NAMES[2][0]), g.SEPARATE)

    def test_dup(self):
        for (texts, correct), want in C.FIX_DUP_CASES:
            self.assertEqual(g.has_dup_correct(texts, correct), want, (texts, correct))

    def test_inst_map(self):
        m, split = g.build_inst_map(C.FIX_INSTANCES)
        self.assertEqual(split, "valid")
        self.assertEqual(sorted(m), ["id1", "id2", "id3", "id4"])
        self.assertEqual(m["id1"]["correct"], [1])
        self.assertEqual(m["id1"]["texts"], ["a", "b", "c"])
        self.assertTrue(m["id2"]["dup"])
        self.assertFalse(m["id4"]["dup"])

    def test_classify(self):
        self.assertEqual(g.classify(1.0, 1, [1]), "plain")
        self.assertEqual(g.classify(1.0, 0, [1]), "old_tie")
        self.assertEqual(g.classify(0.5, 0, [1]), "frac")
        self.assertEqual(g.classify(0.0, 1, [1]), "inconsistent")
        self.assertEqual(g.classify(0.0, 0, [1]), "plain")
        self.assertEqual(g.classify(None, 0, [1]), "missing")

    def test_run_summary(self):
        m, _ = g.build_inst_map(C.FIX_INSTANCES)
        s = g.summarize_run(C.FIX_PREDS, m)
        for k, v in C.FIX_RUN_TARGET.items():
            self.assertEqual(s[k], v, k)

    def test_stats_and_reproduce(self):
        for (name, split), want in C.FIX_STAT_CASES:
            self.assertEqual(g.stat_mean(C.FIX_STATS, name, split), want)
        m, _ = g.build_inst_map(C.FIX_INSTANCES)
        s = g.summarize_run(C.FIX_PREDS, m)
        for (pub, n), want in C.FIX_REPRO_CASES:
            self.assertEqual(g.reproduce(s, pub, n, C.TOL), want, (pub, n))

    def test_ranks_top(self):
        self.assertEqual(g.ranks_high(C.FIX_RANKS_IN), C.FIX_RANKS_OUT)
        self.assertEqual(g.top_share(C.FIX_TOP_IN, 3), C.FIX_TOP_OUT)

    def test_verdicts(self):
        for args, want in C.FIX_V_CASES:
            self.assertEqual(g.predictions94(*args, C.THRESHOLDS), want, args)


if __name__ == "__main__":
    unittest.main()
