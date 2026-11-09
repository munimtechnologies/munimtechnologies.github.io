"""Unit tests for audit 92 (mcq-helm-option-collisions). Standard library only. Apache-2.0.

Hand traces (normalize_text = lower -> drop ASCII punctuation -> replace whole-word a/an/the by ' ' -> join words):
FIX_NORM: '-7' -> '7'; '1.25' -> '125'; 'The heart' -> ' heart' -> 'heart'; '  An  Apple. ' -> '  an  apple ' ->
  'apple'; 'a b' -> 'b'; '?' -> ''; 'Type II' -> 'type ii'; 'then' keeps 'the' (no word boundary) -> 'then'.
FIX_METRIC: exact('-7','7') 0, quasi 1 ('7' = '7'); exact(' x ','x') 1 (both stripped); exact('x','') 0 (empty pred);
  quasi('?','!') 1 (both normalise to '', pred non-empty); quasi_prefix('red','red blue') 1, reversed 0;
  quasi_prefix('2','24') 1 ('24' starts with '2').
FIX_GRADE (opts, gold, output, metric):
 1  'B' -> option 1 '7'; quasi('-7','7') 1, not the gold -> over, quasi_only (exact is 0).
 2  same under exact_match -> H 0, I 0, no flip.
 3  'C' -> 'Aspirin' = gold text -> H 1, I 0 -> identical.
 4  ' B\\n' strips to 'B' -> option 1 = gold -> H 1, I 1.
 5  'A' -> '' -> exact_match returns 0 for an empty pred, but it is the gold letter -> I 1 -> under.
 6  'b' is not a key ('A'-'D') -> unmapped lowercase_letter, H 0.
 7  'E' with 4 options -> unmapped letter_out_of_range.   8 'The' -> other.   9 ' ' -> '' -> empty.
10  'A' -> 'The heart'; gold 'heart'; both normalise to 'heart' -> over, quasi_only.
11  'B' -> '24' vs gold '2': quasi '24' != '2' -> H 0, I 0 (the headline metric is not a prefix metric).
FIX_COLL: ['-7','7','0','1'] -> 7 quasi; ['2','24','4','20'] -> 24 and 20 prefix; 'Aspirin ' strips to the gold
  (identical) and ' aspirin.' normalises to it (quasi_only); 'red blue' prefix-matches 'red'; gold '?' normalises to
  '' so 'a b' (-> 'b') prefix-matches it, while '' is an empty pred (0) -> gold_norm_empty True; gold 'red blue' is
  not a prefix of 'red' -> no collision.
FIX_RUNS: med_qa a_x: two v1.0.0 runs, the shorter name wins (1 dropped); b_y: v1.9.0 beats v1.0.0 (2 dropped);
  the separate_original MMLU run is filtered out before counting and mmlu_pro: does not start with 'mmlu:'.
FIX_V_CASES: case 1 sits exactly on every boundary (20 x 1000 = 10000 x 2; 6 >= 2 x 3) -> all held; case 2 is one
  step past each -> all failed; case 3 (all zero): P3 needs predictions -> failed, P4 (no model moves) -> held.
"""

import unittest

import cases92 as C
import grade92 as g
import job


class TestNormalisation(unittest.TestCase):
    def test_normalize(self):
        for t, w in C.FIX_NORM:
            self.assertEqual(g.normalize_text(t), w, t)

    def test_metrics(self):
        fn = {"exact_match": g.exact_match, "quasi_exact_match": g.quasi_exact_match,
              "quasi_prefix_exact_match": g.quasi_prefix_exact_match}
        for m, a, b, w in C.FIX_METRIC:
            self.assertEqual(fn[m](a, b), w, (m, a, b))


class TestGrade(unittest.TestCase):
    def test_grade_fixture(self):
        for opts, gi, pred, metric, idx, h, i, cls, unm in C.FIX_GRADE:
            r = g.grade(opts, gi, pred, metric)
            self.assertEqual((r["idx"], r["h"], r["i"], r["cls"], r["unmapped"]), (idx, h, i, cls, unm),
                             (opts, gi, pred, metric))

    def test_letter_index(self):
        self.assertEqual(g.letter_index(" C ", 4), 2)
        self.assertIsNone(g.letter_index("C.", 4))
        self.assertIsNone(g.letter_index("AB", 4))
        self.assertIsNone(g.letter_index(None, 4))
        self.assertEqual(g.unmapped_kind(None, 4), "empty")

    def test_collisions(self):
        for opts, gi, want, empty in C.FIX_COLL:
            self.assertEqual(g.collisions(opts, gi), want, opts)
            self.assertEqual(g.gold_norm_empty(opts, gi), empty, opts)


class TestRunsRanksVerdicts(unittest.TestCase):
    def test_select_runs(self):
        for b, want in C.FIX_RUNS_TARGET.items():
            cfg = C.BENCHES[b]
            self.assertEqual(g.select_runs(C.FIX_RUNS, cfg["prefix"], cfg["must_contain"]), want, b)

    def test_ranks_tau(self):
        self.assertEqual(g.min_ranks(C.FIX_ACC), C.FIX_RANKS)
        for x, y, w in C.FIX_TAU:
            t = g.kendall_tau_b(x, y)
            if w is None:
                self.assertIsNone(t)
            else:
                self.assertAlmostEqual(t, w, places=12)

    def test_verdicts(self):
        for args, want in C.FIX_V_CASES:
            self.assertEqual(g.predictions92(*args, C.THRESHOLDS), want, args)

    def test_job_fixture_gate(self):
        self.assertTrue(all(job.fixture_ok().values()), job.fixture_ok())

    def test_job_helpers(self):
        self.assertEqual(job.median([3, 1, 2]), 2)
        self.assertEqual(job.median([1, 2, 3, 4]), job.Fraction(5, 2))
        self.assertEqual(job.g_num("id42"), 42)
        self.assertEqual(job.qhash("Q  one", ["a", "b"], 1), job.qhash("Q one", ["a", "b"], 1))
        self.assertNotEqual(job.qhash("Q one", ["a", "b"], 1), job.qhash("Q one", ["a", "b"], 0))


if __name__ == "__main__":
    unittest.main()
