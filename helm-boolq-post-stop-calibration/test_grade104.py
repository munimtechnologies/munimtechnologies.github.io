"""Unit tests for audit 104 with the hand traces. Standard library only. Apache-2.0.

Hand traces:
- GPT-2 byte table: bytes 0..32 map to chr(256..288), so newline (10) is '\\u010a' and space (32) is '\\u0120'.
  '<0x0A>' is a byte token; '<|newline|>' is replaced by a newline; '\\u2581' is a space; a plain ' ' or '\\n' is not
  in the table and stays as UTF-8.
- keep_count: ['\\u0120Yes', '\\u010a', ...] -> prefix 1 ' Yes' (no stop), prefix 2 ' Yes\\n' (stop) -> keep 1;
  ['\\u010a', ...] -> keep 0; ['\\u0120#', '##', ...] with stop '###' -> prefix 2 ' ###' -> keep 1; no stops -> all.
- Records: C1 tokens -0.25, -0.125, -0.125, -0.25, -0.25 (sum -1.0); keep 1 -> answer-only -0.25, excess -0.75.
  C3 '' with a newline first -> keep 0 -> answer-only log probability 0 -> T = 1.0; em 0 (empty prediction).
  C7 text ' Yes' but kept token ' No' -> consistent False.
- Run: kept id1 t0 (C1, Yes), id2 t0 (C2, gold No -> em 0), id1 t1 (C4), id3 t1 (C7); duplicate id1 t0; perturbed
  id2 t1; train id4; id5 t1 without completions -> no_result. Overrun C1, C4, C7 = 3 of 4 -> class overrun;
  consistent C1, C2, C4 = 3; overrun and consistent C1, C4 = 2; tokens 5 + 1 + 2 + 2 = 10.
- ECE, trial 0, P: probabilities e^-1 (right) and e^-0.5 (wrong) fall in two bins -> ((1 - e^-1) + e^-0.5) / 2;
  trial 1, P: e^-0.75 and e^-0.5, both right -> ((1 - e^-0.75) + (1 - e^-0.5)) / 2; run value = mean of the two.
  T: trial 0 e^-0.25 (right), e^-0.5 (wrong) -> (e^-0.5 + (1 - e^-0.25)) / 2; trial 1 e^-0.5, e^-0.25 (both right)
  -> ((1 - e^-0.5) + (1 - e^-0.25)) / 2. EM = (1/2 + 1) / 2 = 0.75.
- Equal-mass bins: [0.25, 0.625 | 0.75, 0.875] -> boundary 0.6875; ECE = (|0.875 - 1| + |1.625 - 1|) / 4 = 0.1875.
  Three 0.5s with 10 bins -> 3 chunks, boundaries 0.5, 0.5, 1.0 -> [0.5, 1.0]; all in bin 0 -> |1.5 - 2| / 3 = 1/6.
  Five values, 2 bins -> chunks of 3 and 2 (np.array_split) -> boundary (0.5 + 0.75) / 2 = 0.625; 1.0 sits in the
  last bin (left search) -> (|0.875 - 1| + |1.75 - 2|) / 5 = 0.075.
- tau-b: [1,2,3] vs [1,3,2] -> 1/3; [1,1,2] vs [1,2,2] -> 0.5; constant -> None. Ranks: lower is better.
"""

import copy
import unittest

import cases104 as C
import grade104 as g


class TestTokens(unittest.TestCase):
    def test_bytes_decode_keep(self):
        for t, want in C.FIX_BYTES:
            self.assertEqual(g.token_bytes(t), want, t)
        for ts, want in C.FIX_DECODE:
            self.assertEqual(g.decode_tokens(ts), want, ts)
        for (ts, stops), want in C.FIX_KEEP:
            self.assertEqual(g.keep_count(ts, stops), want, (ts, stops))

    def test_exact_match(self):
        for (gold, pred), want in C.FIX_EM:
            self.assertEqual(g.exact_match(gold, pred), want, (gold, pred))


class TestRecords(unittest.TestCase):
    def test_record(self):
        for (golds, comp, stops), want in C.FIX_RECORD:
            self.assertEqual(g.score_record(golds, comp, stops), want, (golds, comp))

    def test_top(self):
        for rs, want in C.FIX_TOP:
            self.assertEqual(g.top_completion(rs), want)


class TestRun(unittest.TestCase):
    def test_run(self):
        s = g.summarize_run(copy.deepcopy(C.FIX_STATE))
        for k, want in C.FIX_RUN.items():
            self.assertEqual(s[k], want, k)
        for k, want in C.FIX_RUN_ECE.items():
            self.assertAlmostEqual(g.run_ece(s["trials"], k, C.NUM_BINS), want, places=12)
        self.assertAlmostEqual(g.run_em(s["trials"]), C.FIX_RUN_EM, places=12)
        self.assertEqual(g.run_class(s["rec"]["overrun"], s["counts"]["kept"]), C.FIX_RUN_CLASS_OF_FIXTURE)
        for (o, n), want in C.FIX_RUN_CLASS:
            self.assertEqual(g.run_class(o, n), want, (o, n))
        self.assertEqual(len(s["samples"]), 2)

    def test_ece(self):
        for (probs, nb), want in C.FIX_BINS:
            self.assertEqual(g.equal_mass_bins(probs, nb), want, probs)
        for (probs, labels, nb), want in C.FIX_ECE:
            got = g.ece_em(probs, labels, nb)
            if want is None:
                self.assertIsNone(got)
            else:
                self.assertAlmostEqual(got, want, places=12)


class TestNamesFiles(unittest.TestCase):
    def test_names(self):
        for run, want in C.FIX_NAMES["canonical"]:
            self.assertEqual(g.is_boolq_canonical(run), want, run)
        for run, want in C.FIX_NAMES["adapter"]:
            self.assertEqual(g.adapter_of(run), want, run)
        for name, want in C.FIX_NAMES["model"]:
            self.assertEqual(g.model_part(name), want, name)
        self.assertEqual(g.select_runs(C.FIX_SUITES), C.FIX_SELECT)

    def test_stats_slim(self):
        for (name, split), want in C.FIX_STAT_ENTRY:
            self.assertEqual(g.stat_entry(C.FIX_STATS, name, split), want, (name, split))
        for d, want in C.FIX_SLIM:
            self.assertEqual(g.slim_hook(copy.deepcopy(d)), want, d)


class TestAggregates(unittest.TestCase):
    def test_ranks_tau_match_group_median(self):
        vals, want = C.FIX_RANKS
        self.assertEqual(g.ranks_low(vals), want)
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
