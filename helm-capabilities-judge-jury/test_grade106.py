"""Unit tests for audit 106 (standard library only). Apache-2.0.
Authored by AI agents working in the name of MV2, Munim, Inc."""

import copy
import unittest

import cases106 as C
import grade106 as g


class ParseTests(unittest.TestCase):
    def test_parse_annotation(self):
        for (ann, scen), want in C.FIX_PARSE:
            self.assertEqual(g.parse_annotation(ann, g.SCENARIOS[scen]), want, (ann, scen))

    def test_empty_keys_end_with_suffix(self):
        for scen in g.SCENARIOS.values():
            self.assertTrue(scen["empty"].endswith(scen["suffix"]))

    def test_rescale(self):
        self.assertEqual(g.rescale_wb(10.0), 1.0)
        self.assertEqual(g.rescale_wb(1.0), 0.0)
        self.assertIsNone(g.rescale_wb(None))


class WildBenchRunTests(unittest.TestCase):
    def setUp(self):
        self.s = g.summarize_run(copy.deepcopy(C.FIX_WB_PREDS), C.WB)
        self.recs = self.s["records"]

    def test_census(self):
        self.assertEqual(self.s["counts"], C.FIX_WB_COUNTS)
        self.assertEqual((self.s["stored_n"], self.s["mismatch"]), C.FIX_WB_STORED)
        self.assertEqual([r["h"] for r in self.recs], C.FIX_WB_H)

    def test_means(self):
        self.assertEqual(g.run_mean(self.recs, lambda r: r["h"]), C.FIX_WB_MEAN)
        self.assertAlmostEqual(g.rescale_wb(g.run_mean(self.recs, lambda r: r["h"])), C.FIX_WB_RESCALED, places=12)
        self.assertIsNone(g.run_mean([], lambda r: 1.0))

    def test_coverage_and_offsets(self):
        n, cov = g.judge_coverage(self.recs)
        self.assertEqual((n, cov), C.FIX_WB_COVERAGE)
        for share, want in C.FIX_WB_PRESENT.items():
            self.assertEqual(g.present_judges(n, cov, share), want)
        self.assertEqual(g.judge_offsets(self.recs, ["llama", "gpt", "claude"]), C.FIX_WB_OFFSETS)
        self.assertIsNone(g.judge_offsets(self.recs, ["gpt"]))

    def test_juries(self):
        for names, (mean, fallback) in C.FIX_WB_JURY.items():
            self.assertEqual(g.run_mean(self.recs, lambda r, n=names: g.jury_score(r, n)), mean)
            self.assertEqual(sum(1 for r in self.recs if g.jury_fallback(r, names)), fallback)


class OmniRunTests(unittest.TestCase):
    def test_omni(self):
        s = g.summarize_run(copy.deepcopy(C.FIX_OM_PREDS), C.OM)
        self.assertEqual(s["counts"], C.FIX_OM_COUNTS)
        self.assertEqual((s["stored_n"], s["mismatch"]), C.FIX_OM_STORED)
        self.assertAlmostEqual(g.run_mean(s["records"], lambda r: r["h"]), C.FIX_OM_MEAN, places=12)
        self.assertEqual(g.judge_offsets(s["records"], ["claude", "gpt", "llama"]), C.FIX_OM_OFFSETS)

    def test_state_fallback(self):
        self.assertEqual(g.predictions_from_state(C.FIX_STATE), C.FIX_STATE_PREDS)
        self.assertEqual(g.predictions_from_state({}), [])


class FamilyTests(unittest.TestCase):
    def test_families(self):
        for name, want in C.FIX_JUDGE_FAMILY:
            self.assertEqual(g.judge_family(name), want)
        for run, want in C.FIX_MODEL:
            self.assertEqual(g.model_part(run), want)
        for model, want in C.FIX_MODEL_FAMILY:
            self.assertEqual(g.model_family(model), want)

    def test_composition(self):
        for (suite, n, cov), want in C.FIX_COMPOSITION:
            self.assertEqual(g.composition_check(suite, n, cov, C.LAST_SUITE, C.FULL_SHARE), want, (suite, cov))

    def test_self_preference(self):
        for judge, (diff, n_own, n_other) in C.FIX_SP.items():
            got = g.self_preference(C.FIX_SP_ROWS, judge)
            self.assertAlmostEqual(got[0], diff, places=12)
            self.assertEqual(got[1:3], (n_own, n_other))
        self.assertIsNone(g.self_preference(C.FIX_SP_ROWS[:2], "gpt")[0])

    def test_perm_p(self):
        self.assertEqual(g.perm_p([1.0, 1.0], [1.0, 1.0, 1.0], 200, 1), 1.0)
        self.assertLessEqual(g.perm_p([5, 5, 5], [0, 0, 0, 0, 0, 0], 2000, C.PERM_SEED), 0.05)
        self.assertIsNone(g.perm_p([], [1.0], 10, 1))


class NamesAndAggregates(unittest.TestCase):
    def test_select(self):
        got = {k: g.select_runs(C.FIX_SUITES, sc["prefix"]) for k, sc in g.SCENARIOS.items()}
        self.assertEqual(got, C.FIX_SELECT)

    def test_stat_entry(self):
        for (name, split), want in C.FIX_STAT_ENTRY:
            self.assertEqual(g.stat_entry(C.FIX_STATS, name, split), want)

    def test_group(self):
        self.assertEqual(g.group_values(C.FIX_GROUP, C.WB["column"]), C.FIX_GROUP_VALUES)
        self.assertIsNone(g.group_values(C.FIX_GROUP, "Nope"))
        self.assertIsNone(g.group_values({}, C.WB["column"]))

    def test_ranks_tau_match(self):
        self.assertEqual(g.ranks_high(C.FIX_RANKS[0]), C.FIX_RANKS[1])
        for (xs, ys), want in C.FIX_TAU:
            got = g.kendall_tau_b(xs, ys)
            if want is None:
                self.assertIsNone(got)
            else:
                self.assertAlmostEqual(got, want, places=12)
        self.assertEqual(g.match_cells(C.FIX_MATCH[0], C.FIX_MATCH[1], C.TOL_CELL), C.FIX_MATCH[2])

    def test_verdicts(self):
        self.assertTrue(all(g.verdicts(C.FIX_VERDICT_ON).values()))
        self.assertFalse(any(g.verdicts(C.FIX_VERDICT_PAST).values()))


if __name__ == "__main__":
    unittest.main()
