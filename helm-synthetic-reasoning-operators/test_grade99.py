"""Unit tests for audit 99 with the hand traces of every fixture in cases99.py. Standard library only. Apache-2.0.

Hand traces
- normalize_text: "X + Y = Y" -> lower "x + y = y" -> drop punctuation "x  y  y" -> "x y y"; "A + B" -> "a  b" -> the
  article "a" goes -> "b"; "Rule: X * Y" -> "rule x y"; "X-Y" -> "xy" (no space left between the letters).
- grades (em, qem, oa, class): identical -> 1, 1, 1; "X = Y + Y" normalises to "x y y" too, operators "=+" vs "+="
  (same characters) -> 0, 1, 0, ops_reordered; "X Y Y" has no operators -> ops_missing; "X - Y = Y" ("-=" vs "+=")
  -> ops_other; lower-case "x + y = y" is not exact but is quasi and keeps "+=" -> 0, 1, 1; "X + Z = Y" -> "x z y"
  -> 0, 0, 0; "   " strips to "" -> 0, 0, 0; "Rule: X * Y." loses ":" and "." -> quasi, operators "*" both -> 0, 1, 1;
  identical words -> 1, 1, 1; " X + Y = Y " strips to the gold -> 1, 1, 1; "X-Y" -> "xy" vs "x y" -> 0, 0, 0;
  "X == Y" -> "x y", operators "==" vs "=" (different characters) -> 0, 1, 0, ops_other.
- multi-gold ["A + B", "X + Y"] vs "X - Y": "b" != "x y"; the second gold quasi-matches but "-" != "+" -> 0, 1, 0,
  classed against the second gold -> ops_other.
- model_of / mode_of: up to the next comma, so "together_ul2" and "induction"; no key -> "".
- select_runs keeps only "synthetic_reasoning:" (the natural-language group and boolq are dropped).
- summarize_run: 10 entries, "junk" is not a record -> 9 records; the perturbed i2 trial 2, the valid-split v1 and the
  second i1 trial 1 are dropped -> 6 kept. Trial 0: i1 exact (1, 1, 1); i2 "Rule: X = Y" quasi ("rule x y") but "="
  != "*" -> ops_other. Trial 1: i1 "X = Y + Y" -> ops_reordered; i2 "rule: x * y" quasi, same operator, not exact ->
  other_norm. Trial 2: i1 "X + Z = Y" scores 0 but stores 1 -> stat_mismatch; i2 None -> "" -> 0 with no stored stat
  -> stat_missing. Trials {0: n2 em1 qem2 oa1, 1: n2 em0 qem2 oa1, 2: n2 em0 qem0 oa0}; qem_not_em = 3.
- run_mean: qem (1 + 1 + 0) / 3 = 2/3; oa (1/2 + 1/2 + 0) / 3 = 1/3; em (1/2 + 0 + 0) / 3 = 1/6.
- cell: trial means 1, 1/2, 1/4 -> (7/4) / 3 = 7/12.
- stat_entry skips the perturbed and the valid entries and the junk string; exact_match absent -> None.
- ranks_high {1/2, 1/3, 1/2, 3/4}: d 1; a and c 2; b 4.
- kendall_tau_b: [1,2,3,4] vs [1,3,2,4]: 5 concordant, 1 discordant, no ties -> 4/6; [1,1,2] vs [1,2,2]: 1
  concordant, one tie in each -> 1 / sqrt(2 * 2) = 0.5; [1,1] vs [1,2]: x constant -> None.
- group_em_values: the EM column of the first table, skipping None -> [0.25, 0.5]; no EM column -> None.
- match_cells: 0.25 finds 0.25000000001 (1e-11 away), 0.5 finds 0.5, 0.7 finds nothing -> 2.
- verdicts: case 1 sits on every boundary (5/100 = 1/20; pattern_match 3/10 above 1/10 and 1/80; fall 1/20; 5
  movers; tau 0.8; 5/10 = 1/2); case 2 is just past each (4/100; a 1/10 tie is not "most"; 49/1000; 4; 0.79; 4/9);
  case 3 is empty.
"""

import unittest
from fractions import Fraction

import cases99 as C
import grade99 as g


class TestGrade99(unittest.TestCase):
    def test_normalize(self):
        for text, want in C.FIX_NORMALIZE:
            self.assertEqual(g.normalize_text(text), want, text)

    def test_grades(self):
        for (gold, pred), (em, qem, oa, cls) in C.FIX_GRADES:
            got = g.grade_record([gold], pred)
            self.assertEqual((got["em"], got["qem"], got["oa"], got["cls"]), (em, qem, oa, cls), (gold, pred))

    def test_multi_gold(self):
        (golds, pred), want = C.FIX_MULTI
        got = g.grade_record(golds, pred)
        self.assertEqual((got["em"], got["qem"], got["oa"], got["cls"]), want)

    def test_no_gold(self):
        got = g.grade_record([], "X")
        self.assertEqual((got["em"], got["qem"], got["oa"], got["cls"]), (0, 0, 0, None))

    def test_model_mode(self):
        for run, model, mode in C.FIX_MODEL_MODE:
            self.assertEqual(g.model_of(run), model)
            self.assertEqual(g.mode_of(run), mode)

    def test_select_runs(self):
        self.assertEqual(g.select_runs(C.FIX_SUITES, C.PREFIX), C.FIX_SUITES_OUT)

    def test_summarize_run(self):
        s = g.summarize_run(C.FIX_INSTANCES, C.FIX_PREDS)
        for k, want in C.FIX_RUN_TARGET.items():
            self.assertEqual(s[k], want, k)

    def test_run_means(self):
        s = g.summarize_run(C.FIX_INSTANCES, C.FIX_PREDS)
        for k, want in C.FIX_RUN_MEANS.items():
            self.assertEqual(g.run_mean(s["trials"], k), want, k)
        self.assertIsNone(g.run_mean({}, "qem"))

    def test_cell(self):
        trials_list, want = C.FIX_CELL
        self.assertEqual(g.cell(trials_list, "qem"), want)
        self.assertIsNone(g.cell([], "qem"))

    def test_stat_entry(self):
        for name, want in C.FIX_STAT_TARGET.items():
            self.assertEqual(g.stat_entry(C.FIX_STATS, name), want, name)

    def test_ranks(self):
        self.assertEqual(g.ranks_high(C.FIX_RANKS_IN), C.FIX_RANKS_OUT)

    def test_tau(self):
        for (xs, ys), want in C.FIX_TAU:
            got = g.kendall_tau_b(xs, ys)
            if want is None:
                self.assertIsNone(got)
            else:
                self.assertAlmostEqual(got, want, places=12)

    def test_group_values(self):
        self.assertEqual(g.group_em_values(C.FIX_GROUP), C.FIX_GROUP_VALUES)
        self.assertIsNone(g.group_em_values(C.FIX_GROUP_NO_COL))
        self.assertIsNone(g.group_em_values(None))

    def test_match_cells(self):
        (ours, pub, tol), want = C.FIX_MATCH
        self.assertEqual(g.match_cells(ours, pub, tol), want)

    def test_verdicts(self):
        for args, want in C.FIX_V_CASES:
            self.assertEqual(g.predictions99(*args, C.THRESHOLDS), want, args)

    def test_thresholds_are_exact(self):
        self.assertIsInstance(C.THRESHOLDS["P2_share"], Fraction)
        self.assertIsInstance(C.THRESHOLDS["P4_fall"], Fraction)


if __name__ == "__main__":
    unittest.main()
