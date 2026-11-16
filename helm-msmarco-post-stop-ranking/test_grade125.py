"""Unit tests for audit 125 with the hand traces. Standard library only. Apache-2.0.

Hand traces:
- Tokens, decoding and keep_count: audit 104's, unchanged.
- first_completion takes completions[0] (not the most probable one, unlike the calibration audits): HELM's
  get_model_output_logprob. No result or no completion -> ('missing', 0.0).
- answer_only: A0 keeps 1 of 4 tokens -> -0.25, overrun, consistent; A1 nothing past the stop -> the stored -0.5;
  the missing record has no tokens -> stored 0.0, not overrun, '' != 'missing' -> inconsistent; a kept ' No' under the
  text ' Yes' -> inconsistent; a newline first -> keep 0, sum of nothing = 0; A0 with no stops keeps all 4 -> stored
  -1.0, not overrun, ' Yes\\n\\nPass' != ' Yes'.
- score_key: 'yes' -> (2, lp); 'no' -> (1, -lp); else (0, -lp) on the stripped lower-cased text.
- Run census (stop '\\n'):
  q1 trial 0: o0 ' Yes' p -1.0 t -0.25 (rank 1); o1 gold ' Yes' p = t = -0.5 (rank 2); o2 ' No' p -0.25 t -0.125
  (rank 3); o3 gold ' No' p -2.0 t -1.0 (no rank). Keys with p: (2,-1.0), (2,-0.5), (1,0.25), (1,2.0) -> order
  o1, o0, o3, o2 -> RR@10 1.0; BM25 top 30 drops o3 -> o1, o0, o2 -> 1.0. With t: (2,-0.25), (2,-0.5), (1,0.125),
  (1,1.0) -> o0, o1, o3, o2 -> RR@10 0.5; top 30 -> o0, o1, o2 -> 0.5. First gold 1 -> 2: changed and moved.
  q2 trial 0: o0 ' No' -0.5 (rank 1); o1 gold ' Yes' -0.25 (no rank); o2 ' Maybe' -3.0 (rank 2); all clean. Order
  o1, o0, o2 -> RR@10 1.0; top 30 -> o0, o2 -> 0.0. Same with t.
  q1 trial 1: o0 ' Yes' -2.0; o1 gold, no completion -> 'missing' 0.0 -> (0, -0.0); o2 ' Yes' stored -1.25 (tokens
  sum -1.0 -> lp_mismatch), t -0.5; o3 gold ' no' -0.5 (no rank). p: (2,-2.0), (0,-0.0), (2,-1.25), (1,0.5) ->
  o2, o0, o3, o1 -> RR@10 1/3; top 30 -> o2, o0, o1 -> 1/3. t: o2 (2,-0.5) still first -> same order, 1/3 and 1/3.
  Skipped: one perturbed, one train-split, one without reference_index, one duplicate (q2, 0, 0). 15 states, 11 kept.
  Overrun A0, A2, A3, D2 = 4 (all consistent); consistent 10 (not the missing one); tokens 4+1+2+2+1+1+1+1+0+2+1 = 16;
  excess -0.75, -0.125, -1.0, -0.75; 4 of 11 overrun -> clean. All 3 groups have a gold outside the BM25 top 30.
- Trial means: p10 trial 0 (1 + 1) / 2 = 1, trial 1 1/3 -> (1 + 1/3) / 2; t10 0.75 and 1/3; pk 0.5 and 1/3; tk 0.25
  and 1/3. Two trials.
- RR@k: [OA, OB, OC] -> OB at 2 -> 0.5; top 30 drops OB (no rank) -> OC at 2 -> 0.5; k = 1 -> 0; relevance 0 is not
  relevant; rank 5 > 3 is dropped.
- Ranks are higher-is-better: {a .1, b .2, c .1, d .3} -> a 3, b 2, c 3, d 1.
- Verdicts: ON sits on each boundary (9 of 10; the five expected adapters in another order; -0.1; 3 of 5 is at least
  half; 19 of 20; better 1 > worse 0; 1 mover; 10 of 100 groups); PAST is just past every one.
"""

import copy
import unittest

import cases125 as C
import grade125 as g


class TestTokens(unittest.TestCase):
    def test_bytes_decode_keep(self):
        for t, want in C.FIX_BYTES:
            self.assertEqual(g.token_bytes(t), want, t)
        for ts, want in C.FIX_DECODE:
            self.assertEqual(g.decode_tokens(ts), want, ts)
        for (ts, stops), want in C.FIX_KEEP:
            self.assertEqual(g.keep_count(ts, stops), want, (ts, stops))


class TestRecords(unittest.TestCase):
    def test_first_completion(self):
        for rs, want in C.FIX_FIRST:
            self.assertEqual(g.first_completion(rs), want, rs)

    def test_answer_only(self):
        for (c, stops), want in C.FIX_ANSWER:
            self.assertEqual(g.answer_only(c, stops), want, (c, stops))

    def test_tags(self):
        for ref, want in C.FIX_TAGS:
            self.assertEqual(g.ref_tags(ref), want, ref)


class TestRanking(unittest.TestCase):
    def test_score_key(self):
        for (text, lp), want in C.FIX_SCORE_KEY:
            self.assertEqual(g.score_key(text, lp), want, (text, lp))

    def test_order(self):
        objs, want = C.FIX_ORDER
        self.assertEqual([o["id"] for o in g.model_order(objs, "p")], want)

    def test_rr(self):
        for (objs, k, lim), want in C.FIX_RR:
            self.assertEqual(g.rr_at(objs, k, lim), want, (objs, k, lim))
        for objs, want in C.FIX_FIRST_GOLD:
            self.assertEqual(g.first_gold_position(objs), want, objs)
        for (objs, topk), want in C.FIX_OUTSIDE:
            self.assertEqual(g.gold_outside(objs, topk), want, objs)


class TestRun(unittest.TestCase):
    def test_run(self):
        s = g.summarize_run(copy.deepcopy(C.FIX_STATE))
        for k, want in C.FIX_RUN.items():
            self.assertEqual(s[k], want, k)
        self.assertEqual(len(s["samples"]), 2)
        self.assertEqual(g.run_class(s["rec"]["overrun"], s["rec"]["records"]), C.FIX_RUN_CLASS_OF_FIXTURE)
        for (o, n), want in C.FIX_RUN_CLASS:
            self.assertEqual(g.run_class(o, n), want, (o, n))

    def test_trial_mean(self):
        s = g.summarize_run(copy.deepcopy(C.FIX_STATE))
        for key, (v, n) in C.FIX_TRIAL_MEAN.items():
            got = g.trial_mean(s["trials"], key)
            self.assertAlmostEqual(got[0], v, places=12, msg=key)
            self.assertEqual(got[1], n, key)
        self.assertEqual(g.trial_mean({}, "p10"), (None, 0))


class TestNamesFiles(unittest.TestCase):
    def test_names(self):
        for run, want in C.FIX_NAMES["selected"]:
            self.assertEqual(g.is_selected(run), want, run)
        for run, want in C.FIX_NAMES["scenario"]:
            self.assertEqual(g.scenario_of(run), want, run)
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
        self.assertEqual(sorted(C.EXPECTED), sorted(g.EXPECTED_OVERRUN))
        on = g.verdicts(C.FIX_VERDICT_ON)
        self.assertEqual(sorted(on), ["P%d" % i for i in range(1, 9)])
        self.assertTrue(all(on.values()), on)
        past = g.verdicts(C.FIX_VERDICT_PAST)
        self.assertFalse(any(past.values()), past)


if __name__ == "__main__":
    unittest.main()
