"""Unit tests for audit 102 with the hand traces. Standard library only. Apache-2.0.

Hand traces (HELM's _strip_string steps that matter are named):
- reg ("5", "5$"): _strip_string leaves "5$" (only an escaped "\\$" is removed) -> H 0; the text before the first
  unescaped "$" is "5" -> A 1, dollar_tail.
- reg ("1000", "1,000"): "1,000" != "1000" -> H 0; value() drops thousands commas -> 1000 = 1000 -> A 1, value_format.
- reg ("\\frac{1}{2}", "0.5"): _strip_string maps the exact string "0.5" to \\frac{1}{2} -> H 1, A 1.
- reg ("\\frac{1}{4}", "0.25"): "0.25" is kept -> H 0; value: 1/4 both -> A 1, value_format.
- reg ("\\$5", "\\$5"): "\\$" is removed by _strip_string -> H 1; the "$" is escaped so nothing is cut -> A 1.
- reg ("a$b", "a$b"): equal strings -> H 1; cut to "a" -> A 0, other (a down-flip of our rule).
- cot G = "So $x=5$. Thus the answer is $\\boxed{5}$." -> HELM's gold answer "5".
  "The answer is $5$.": no \\boxed -> H 0; unboxed_candidate: line " $5$." -> segment "5" -> A 1, unboxed.
  "So $\\boxed{5.0}$": boxed "5.0" != "5" -> H 0; value 5 = 5 -> A 1, value_format.
  "\\boxed 5": no closing brace, so HELM extracts None -> H 0; the bare-\\boxed fallback gives "5" -> pred_fallback.
  gold "x is 5." vs "I think 5.": both None -> HELM scores 1.0 -> H 1; no gold answer -> A 0, both_none.
- reg run: id1 t0 "5" (1,1); id1 t1 "5$" (0,1, dollar_tail, 20 output tokens = cap); id2 t0 "1,000" (0,1,
  value_format); id2 t1 "999" (0,0; stored 1.0 -> mismatch); id3 valid -> not_test; id1 t0 again -> duplicate;
  perturbed -> skipped; id1 t2 "6" (0,0; no stored score -> missing); id2 t2 "1000" (1,1).
  Trial means H 1/2, 0, 1/2 -> 1/3; A 1, 1/2, 1/2 -> 2/3.
- cells: X has s1 (H 1/2, A 1) and s2 (H 0, A 1/4) -> H 1/4, A 5/8; Y lacks s2 -> no cell.
- tau-b: [1,2,3] vs [1,3,2]: 2 concordant, 1 discordant -> 1/3; [1,1,2] vs [1,2,2]: c 1, d 0, one tie each in 3
  pairs -> 1/sqrt(2*2) = 0.5.
"""

import unittest

import cases102 as C
import grade102 as g


class TestGrades(unittest.TestCase):
    def test_reg(self):
        for (gold, pred), want in C.FIX_REG:
            r = g.grade_reg(gold, pred)
            self.assertEqual((r["h"], r["a"], r["cls"]), want, (gold, pred))

    def test_cot(self):
        for (gold, pred), want in C.FIX_COT:
            r = g.grade_one("cot", gold, pred)
            self.assertEqual((r["h"], r["a"], r["cls"]), want, (gold, pred))

    def test_record(self):
        for (mode, golds, pred), want in C.FIX_RECORD:
            self.assertEqual(g.grade_record(mode, golds, pred), want, (mode, golds, pred))


class TestNames(unittest.TestCase):
    def test_names(self):
        for run, want in C.FIX_NAMES["mode"]:
            self.assertEqual(g.run_mode(run), want, run)
        for run, want in C.FIX_NAMES["subject"]:
            self.assertEqual(g.subject_of(run), want, run)
        for run, want in C.FIX_NAMES["adapter"]:
            self.assertEqual(g.adapter_of(run), want, run)
        for run, want in C.FIX_NAMES["model"]:
            self.assertEqual(g.model_part(run), want, run)
        self.assertEqual(g.select_runs(C.FIX_SUITES), C.FIX_SELECT)


class TestCensus(unittest.TestCase):
    def test_reg_run(self):
        s = g.summarize_run("reg", C.FIX_REG_INSTANCES, C.FIX_REG_PREDS, C.CAP["reg"])
        for k, want in C.FIX_REG_RUN.items():
            self.assertEqual(s[k], want, k)
        for k, want in C.FIX_REG_MEANS.items():
            self.assertEqual(g.run_mean(s["trials"], k), want, k)

    def test_cot_run(self):
        s = g.summarize_run("cot", C.FIX_COT_INSTANCES, C.FIX_COT_PREDS, C.CAP["cot"])
        for k, want in C.FIX_COT_RUN.items():
            self.assertEqual(s[k], want, k)
        for k, want in C.FIX_COT_MEANS.items():
            self.assertEqual(g.run_mean(s["trials"], k), want, k)


class TestAggregates(unittest.TestCase):
    def test_cells(self):
        self.assertEqual(g.build_cells(C.FIX_CELL_RUNS, C.FIX_CELL_SUBJECTS), C.FIX_CELLS)

    def test_ranks_tau_match_group(self):
        vals, want = C.FIX_RANKS
        self.assertEqual(g.ranks_high(vals), want)
        for (xs, ys), want in C.FIX_TAU:
            got = g.kendall_tau_b(xs, ys)
            if want is None:
                self.assertIsNone(got)
            else:
                self.assertAlmostEqual(got, want, places=12)
        ours, pub, want = C.FIX_MATCH
        self.assertEqual(g.match_cells(ours, pub, C.TOL_CELL), want)
        self.assertEqual(g.group_values(C.FIX_GROUP), C.FIX_GROUP_VALUES)

    def test_verdicts(self):
        self.assertTrue(all(g.verdicts(C.FIX_VERDICT_ON).values()))
        self.assertFalse(any(g.verdicts(C.FIX_VERDICT_PAST).values()))


if __name__ == "__main__":
    unittest.main()
