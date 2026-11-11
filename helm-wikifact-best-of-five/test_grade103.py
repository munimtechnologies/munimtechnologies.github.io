"""Unit tests for audit 103 with the hand traces. Standard library only. Apache-2.0.

Hand traces (HELM's normalize_text: lower, drop punctuation, replace a/an/the by a space, collapse whitespace):
- "The Beatles" -> "the beatles" -> " beatles" -> "beatles" = "beatles" -> 1. "U.S." -> "us" = "us" -> 1.
  "Paris" vs "" -> 0 (empty prediction). "paris" vs "paris france" -> 0. "new  york." -> "new york" -> 1.
  "A" -> " " -> "" and "the" -> " " -> "": equal -> 1 (a quirk of the normalisation).
- COMPS_A, gold Paris: scores [0, 1, 1, 0, 0] ("Paris." normalises to "paris"); sort keys -logprob = [3, 1, 1.5,
  4, 3] -> order 1, 2, 0, 4, 3 -> top 1 -> H 1; F = score of index 0 = 0; q_sum 2; distinct London, Paris, Paris.,
  Rome = 4.
- COMPS_B, gold Paris: scores [0, 1, 1, 1, 1]; every logprob 0 -> the stable sort keeps index 0 on top -> H 0, F 0,
  q_sum 4, distinct 2, zero_lp and equal_lp.
- COMPS_C, golds Paris / "Paris, France": five times " paris" -> all 1 -> H 1, F 1, q_sum 5, distinct 1.
- COMPS_D, gold Lyon: scores [0, 0, 1]; keys [2, 1, 1] -> order 1, 2, 0 (tie kept in order) -> top 1 -> H 0.
- COMPS_E, gold Paris: scores [1, 0]; keys [5, 1] -> top 1 -> H 0, F 1, q_sum 1.
- Run: kept id1 t0 (A: H1 F0 M 2/5 K1), id6 t1 (C: 1 1 1 1), id2 t0 (B: 0 0 4/5 1), id4 t1 (D: 0 0 1/3 1),
  id5 t0 (E: 0 1 1/2 1); id3 valid -> not_test; id1 t0 again -> duplicate; perturbed id2 t1 -> perturbed;
  id2 t1 without result -> no_result. Trial 0: n 3, H 1, F 1, M 2/5 + 4/5 + 1/2 = 17/10, K 3. Trial 1: n 2, H 1,
  F 1, M 1 + 1/3 = 4/3, K 2. Means: H (1/3 + 1/2)/2 = 5/12; F 5/12; M (17/30 + 20/30)/2 = 37/60; K 1.
  Records: 5 completions in A, C, B -> n5 3; collapsed C; zero_lp B; equal_lp C, B; top_not_first A, D, E;
  F != H in A and E -> display_disagree 2, keys (id1, 0), (id5, 0). Stored: id2 t0 1.0 vs H 0 -> mismatch;
  id5 t0 1.0 vs H 0 -> mismatch that equals F; id4 t1 no stat -> missing. Shown: id4 t1 " Paris" but
  completions[0] is " Rome" -> shown_mismatch 1. zero_lp 1 and collapsed 1 of 5 -> class ranked.
- cells: X = runs x1 (H 1/2, F 0, M 1/4, K 1/2) and x2 (0, 1, 1, 1) -> H 1/4, F 1/2, M 5/8, K 3/4; Y lacks y2.
- tau-b: [1,2,3] vs [1,3,2]: 2 concordant, 1 discordant -> 1/3; [1,1,2] vs [1,2,2]: c 1, d 0, one tie each in 3
  pairs -> 1/sqrt(2*2) = 0.5.
"""

import unittest

import cases103 as C
import grade103 as g


class TestScoring(unittest.TestCase):
    def test_qem(self):
        for (gold, pred), want in C.FIX_QEM:
            self.assertEqual(g.quasi_exact_match(gold, pred), want, (gold, pred))

    def test_record(self):
        for (golds, comps), want in C.FIX_RECORD:
            self.assertEqual(g.score_record(golds, comps), want, (golds, comps))

    def test_parsing(self):
        for rs, want in C.FIX_COMPLETIONS:
            self.assertEqual(g.completions_of(rs), want)
        inst, want = C.FIX_GOLDS
        self.assertEqual(g.golds_of_instance(inst), want)


class TestRun(unittest.TestCase):
    def test_run(self):
        s = g.summarize_run(C.FIX_STATE, C.FIX_PREDS, C.KEYS_PER_RUN)
        for k, want in C.FIX_RUN.items():
            self.assertEqual(s[k], want, k)
        for k, want in C.FIX_MEANS.items():
            self.assertEqual(g.run_mean(s["trials"], k), want, k)
        self.assertEqual(g.run_class(s["rec"], s["counts"]["kept"]), C.FIX_RUN_CLASS_OF_FIXTURE)

    def test_classes(self):
        for (rec, kept), want in C.FIX_RUN_CLASS:
            self.assertEqual(g.run_class(rec, kept), want, (rec, kept))
        for classes, want in C.FIX_ADAPTER_CLASS:
            self.assertEqual(g.adapter_class(classes), want, classes)


class TestNames(unittest.TestCase):
    def test_names(self):
        for run, want in C.FIX_NAMES["k5"]:
            self.assertEqual(g.is_wikifact_k5(run), want, run)
        for run, want in C.FIX_NAMES["subject"]:
            self.assertEqual(g.subject_of(run), want, run)
        for run, want in C.FIX_NAMES["adapter"]:
            self.assertEqual(g.adapter_of(run), want, run)
        for run, want in C.FIX_NAMES["model"]:
            self.assertEqual(g.model_part(run), want, run)
        self.assertEqual(g.select_runs(C.FIX_SUITES), C.FIX_SELECT)


class TestAggregates(unittest.TestCase):
    def test_cells(self):
        self.assertEqual(g.build_cells(C.FIX_CELL_RUNS, C.FIX_CELL_LISTED), C.FIX_CELLS)

    def test_ranks_tau_match_group_median(self):
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
        self.assertEqual(g.group_values(C.FIX_GROUP, C.COLUMN), C.FIX_GROUP_VALUES)
        self.assertIsNone(g.group_values(C.FIX_GROUP_NO_COLUMN, C.COLUMN))
        for xs, want in C.FIX_MEDIAN:
            self.assertEqual(g.median(xs), want, xs)

    def test_verdicts(self):
        self.assertTrue(all(g.verdicts(C.FIX_VERDICT_ON).values()))
        self.assertFalse(any(g.verdicts(C.FIX_VERDICT_PAST).values()))


if __name__ == "__main__":
    unittest.main()
