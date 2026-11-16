"""Unit tests for audit 124 with the hand traces. Standard library only. Apache-2.0.

Hand traces (record-level ones are audit 104's, unchanged):
- GPT-2 byte table: bytes 0..32 map to chr(256..288), so newline (10) is '\\u010a' and space (32) is '\\u0120'.
  '<0x0A>' is a byte token; '<|newline|>' is replaced by a newline; '\\u2581' is a space; a plain ' ' or '\\n' is not
  in the table and stays as UTF-8.
- keep_count: ['\\u0120Yes', '\\u010a', ...] -> prefix 1 ' Yes' (no stop), prefix 2 ' Yes\\n' (stop) -> keep 1;
  ['\\u010a', ...] -> keep 0; ['\\u0120#', '##', ...] with stop '###' -> prefix 2 ' ###' -> keep 1; no stops -> all.
- Records: C1 tokens -0.25, -0.125, -0.125, -0.25, -0.25 (sum -1.0); keep 1 -> answer-only -0.25, excess -0.75.
  C3 '' with a newline first -> keep 0 -> answer-only log probability 0 -> T = 1.0; em 0 (empty prediction).
  C7 text ' Yes' but kept token ' No' -> consistent False.
- Run census (new, keyed by (id, split, trial)): kept id1 valid t0 (C1, Yes, em 1), id2 valid t0 (C2, gold No ->
  em 0), id1 test t0 (C4; same id, other split, so kept), id3 test t1 (C7, em 1); id1 valid t0 again -> duplicate;
  id2 t1 perturbed; id4 train -> not_eval; id5 test t1 without completions -> no_result. 4 kept, 2 per split.
  Overrun C1, C4, C7 = 3 of 4 -> class overrun; consistent C1, C2, C4 = 3; overrun and consistent C1, C4 = 2;
  tokens 5 + 1 + 2 + 2 = 10; excess in order -0.75 (C1), -0.25 (C4), -0.25 (C7); samples C1 and C4.
- Per-split ECE with P: valid t0 has e^-1 (right) and e^-0.5 (wrong); two records -> two chunks, boundary
  (e^-1 + e^-0.5) / 2 ~ 0.487 -> separate bins -> ((1 - e^-1) + e^-0.5) / 2, one trial. test t0: one record e^-0.75
  (right) -> bins [1.0] -> 1 - e^-0.75; test t1: e^-0.5 (right) -> 1 - e^-0.5; mean of the two, two trials.
  With T: valid t0 e^-0.25 (right), e^-0.5 (wrong) -> (e^-0.5 + (1 - e^-0.25)) / 2; test t0 e^-0.5 -> 1 - e^-0.5;
  test t1 e^-0.25 -> 1 - e^-0.25. EM: valid 1/2 (one trial); test 1 and 1 -> 1.0 (two trials).
- Mean confidence: P = (e^-1 + e^-0.5 + e^-0.75 + e^-0.5) / 4; T = (e^-0.25 + e^-0.5 + e^-0.5 + e^-0.25) / 4.
- Pooled cell: (0.2 x 3 + 0.4 x 1) / 4 = 0.25; empty, a None value or a zero count -> None.
- Names: subset= and demographic= parts and data_augmentation=canonical are dropped from the adapter; ablation runs
  (groups=...), contrast sets and other scenarios are not canonical here. model_id keeps the part before the first
  comma, so meta_llama-2-70b is not the flagged meta_llama-2-7b.
- stats lookup skips the sub_split and perturbed entries.
- Equal-mass bins and ECE, ranks, tau-b, matching, group column, medians: as in audit 104.
- Verdicts: ON sits on each boundary (9 of 10 included and matched; 15 overrun; median excess -2.0; 8 of 15 is at
  least half; better 1 > worse 0; 19 of 20 consistent; tau 0.79 < 0.8 with 5 movers); PAST is just past every one
  (fixtures False; 8 of 10; 14 overrun; -1.99; 6 of 14 under half; 1 = 1; 18 of 20; tau 0.8).
"""

import copy
import unittest

import cases124 as C
import grade124 as g


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
        self.assertEqual(len(s["samples"]), 2)
        self.assertEqual(g.run_class(s["rec"]["overrun"], s["counts"]["kept"]), C.FIX_RUN_CLASS_OF_FIXTURE)
        for (o, n), want in C.FIX_RUN_CLASS:
            self.assertEqual(g.run_class(o, n), want, (o, n))

    def test_split_values_and_confidence(self):
        s = g.summarize_run(copy.deepcopy(C.FIX_STATE))
        for key, want in C.FIX_SPLIT_VALUES.items():
            got = g.split_values(s["trials"], key, C.NUM_BINS)
            self.assertEqual(sorted(got), sorted(want), key)
            for split, (v, n) in want.items():
                self.assertAlmostEqual(got[split][0], v, places=12, msg=(key, split))
                self.assertEqual(got[split][1], n, (key, split))
        for key, want in C.FIX_MEAN_CONF.items():
            self.assertAlmostEqual(g.mean_conf(s["trials"], key), want, places=12)
        self.assertIsNone(g.mean_conf({}, "p"))

    def test_pooled(self):
        for pairs, want in C.FIX_POOLED:
            got = g.pooled_value(pairs)
            if want is None:
                self.assertIsNone(got, pairs)
            else:
                self.assertAlmostEqual(got, want, places=12)

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
            self.assertEqual(g.is_canonical(run), want, run)
        for run, want in C.FIX_NAMES["scenario"]:
            self.assertEqual(g.scenario_of(run), want, run)
        for run, want in C.FIX_NAMES["adapter"]:
            self.assertEqual(g.adapter_of(run), want, run)
        for name, want in C.FIX_NAMES["model"]:
            self.assertEqual(g.model_part(name), want, name)
        for ad, want in C.FIX_NAMES["flagged"]:
            self.assertEqual(g.is_flagged(ad), want, ad)
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
        on = g.verdicts(C.FIX_VERDICT_ON)
        self.assertEqual(sorted(on), ["P%d" % i for i in range(1, 9)])
        self.assertTrue(all(on.values()), on)
        past = g.verdicts(C.FIX_VERDICT_PAST)
        self.assertFalse(any(past.values()), past)


if __name__ == "__main__":
    unittest.main()
