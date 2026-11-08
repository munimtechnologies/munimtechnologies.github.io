"""Unit tests for audit 90 (standard library only). Each expectation below was traced by hand against grade90.py
before the job was queued. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.

Traces (H regex -?[\\d,]+(?:.\\d+)? with an unescaped '.'; F regex -?\\d[\\d,]*(?:\\.\\d+)?):
 1 '... 9 * 2 = 18 dollars. The answer is 18.': H matches 9, 2, 18, 18 -> '18'; F the same; stated 18 -> all 1.
 2 'The answer is 72, in total, so ...': H matches '72,' then the lone ',' after 'total' -> '' -> H 0. F cannot
   start at a comma -> '72'. Stated '72,' -> '72'. Up-flip; HELM's final is '' -> comma_only.
 3 'Counting the boxes: 3 4': H's '.' takes the space -> '3 4' (H 0); F -> '4'; no phrase or box -> stated is F's
   '4'. Up-flip; '3 4' holds a space -> dot_merge.
 4 '... = $7.00. The answer is \\$7.00.': H and F -> '7.00' != '7' (H 0, F 0); as numbers 7.00 = 7 (N 1); the
   phrase skips ' \\$' -> '7.00' (A 1). Up-flip; last number equals the key as a number -> decimal_format.
 5 '... R = 5. The answer is 5. Question: ... = 7. The answer is 7.': last number 7 (H, F, N 0); first phrase 5
   (A 1). Up-flip; no comma, no merge, last number not the key, stated from a phrase -> run_on.
 6 'He makes 1/2.5 hours' (gold 5): H matches '1/2' then '5' -> credited (H 1); F matches '1', '2.5' -> 0; stated is
   F's 2.5 -> A 0. Down-flip; F's last number is not the key -> helm_regex_only.
 7 'The answer is 10. Note: each box holds 12' (gold 12): H, F, N 1; stated 10 -> A 0. Down-flip; F's last number
   equals the key, stated from a phrase -> stated_differs.
 8 '\\[ \\boxed{160,000} \\]' (gold 160000): H '160,000' ('.' takes '}' but no digit follows) -> '160000' (1); no
   phrase; the box gives 160000 -> A 1.
 9 'I am not sure.': no numbers; every grade 0; stated '' from 'last'.
10 'Therefore, the answer is 1000 people. Check: (2/5) * 5000 = 2000 people.': H matches ',', 1000, '2/5', 5000,
   2000 -> 2000 (H 0); F -> 2000 (0); phrase 1000 -> A 1 -> run_on.
11 'The answer is 60%.': '.' takes '%' but no digit follows -> '60' -> all 1.
12 'The answer is not obvious ..., but the answer is 9.': the first 'answer is' has no number after it, so the
   search moves to the second -> 9; H's lone ',' is not last -> all 1.
13 'The answer is \\(\\boxed{18}\\).': the phrase skips ' \\(\\', then 'boxed{' -> 18 -> all 1.
14 '... -3 degrees. The answer is -3.': every grader -> -3 -> all 1.
Ranks: 9/10 > 8/10 = 8/10 > 1/2 -> 1, 2, 2, 4 (one more than the number strictly above).
Tau-b of [1,1,2] vs [1,2,3]: pairs (0,1) tied in x only, (0,2) and (1,2) concordant -> 2 / sqrt(3 * 2).
Verdict case 1: 900 >= 900, 100 >= 100, mean gains 1/100 > 1/1000 with 36 and 54 runs, 5 >= 5, 5 * 200 <= 1000.
Case 2: one short on every count (4 stop=none runs < 5; 5 * 201 > 1000). Case 3: equal mean gains (1/100 each)
are not 'more'; no up-flips -> P6 FAILED.
"""

import unittest

import grade90 as g
import cases90 as C


class TestGraders(unittest.TestCase):
    def test_fixture_grades(self):
        for gold, pred, hfna, hf, ff, st, src, cls in C.FIX_GRADE:
            r = g.grade(gold, pred)
            self.assertEqual((r["h"], r["f"], r["n"], r["a"]), hfna, pred)
            self.assertEqual(r["helm_final"], hf, pred)
            self.assertEqual(r["fixed_final"], ff, pred)
            self.assertEqual((r["stated"], r["source"]), (st, src), pred)
            self.assertEqual(g.flip_class(r), cls, pred)

    def test_helm_matches_its_own_examples(self):
        # HELM's docstring example: gold 'The answer is 15.' vs 'The answer is 15 eggs.' scores 1.
        self.assertEqual(g.helm_fnem("The answer is 15.", "The answer is 15 eggs."), 1)
        self.assertEqual(g.helm_final("It costs $1,000."), "1000")
        self.assertEqual(g.helm_final("12a34"), "12a34")
        self.assertEqual(g.helm_final("so 4 apples, b"), "")
        self.assertEqual(g.exact_match("4", ""), 0)

    def test_to_num(self):
        for s, want in C.FIX_TO_NUM:
            self.assertEqual(g.to_num(s), want, s)
        self.assertTrue(g.num_eq("7", "7.00"))
        self.assertFalse(g.num_eq("7", ""))

    def test_classes_cover_fixture(self):
        seen = {cls for *_x, cls in C.FIX_GRADE if cls}
        self.assertTrue(seen <= set(g.UP_CLASSES) | set(g.DOWN_CLASSES))
        self.assertEqual(seen, {"comma_only", "dot_merge", "decimal_format", "run_on", "helm_regex_only",
                                "stated_differs"})


class TestRunsRanks(unittest.TestCase):
    def test_select_runs(self):
        self.assertEqual(g.select_runs(C.FIX_RUNS), C.FIX_RUNS_TARGET)

    def test_stop_none(self):
        for run, want in C.FIX_STOP:
            self.assertEqual(g.is_stop_none(run), want, run)

    def test_ranks(self):
        self.assertEqual(g.min_ranks(C.FIX_ACC), C.FIX_RANKS)

    def test_tau(self):
        for xs, ys, want in C.FIX_TAU:
            got = g.kendall_tau_b(xs, ys)
            if want is None:
                self.assertIsNone(got)
            else:
                self.assertAlmostEqual(got, want, places=12)


class TestVerdicts(unittest.TestCase):
    def test_cases(self):
        for args, want in C.FIX_V_CASES:
            self.assertEqual(g.predictions90(*args, C.THRESHOLDS), want)


if __name__ == "__main__":
    unittest.main()
