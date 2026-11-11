"""Unit tests for audit 105 (standard library only). Apache-2.0.
Authored by AI agents working in the name of MV2, Munim, Inc."""

import copy
import unittest

import cases105 as C
import grade105 as g


class ExtractTests(unittest.TestCase):
    def test_helm_extract(self):
        for (text, version), want in C.FIX_EXTRACT:
            self.assertEqual(g.helm_extract(text, version), want, (text, version))

    def test_stated_answer(self):
        for text, want in C.FIX_STATED:
            self.assertEqual(g.stated_answer(text), want, text)

    def test_versions_differ_only_in_regexes(self):
        self.assertEqual(g.VERSIONS["v4"][:2], g.VERSIONS["v2"])
        self.assertEqual(g.VERSIONS["v4"][:3], g.VERSIONS["v3"])
        self.assertEqual(g.VERSIONS["pr4323"][0], g.VERSIONS["v4"][0])
        self.assertEqual(g.VERSIONS["pr4323"][2:], g.VERSIONS["v4"][2:])
        self.assertNotEqual(g.VERSIONS["pr4323"][1], g.VERSIONS["v4"][1])


class RecordTests(unittest.TestCase):
    def test_record_class(self):
        for args, want in C.FIX_CLASS:
            self.assertEqual(g.record_class(*args), want, args)

    def test_gold_letter(self):
        for refs, want in C.FIX_GOLD:
            self.assertEqual(g.gold_letter(refs), want)

    def test_golds_by_id(self):
        self.assertEqual(g.golds_by_id(C.FIX_INSTANCES), C.FIX_GOLDS)

    def test_grade_record(self):
        r = g.grade_record(C.T3, "B")
        self.assertEqual(r["credit"], {"v2": 0, "v3": 0, "v4": 0, "pr4323": 1})
        self.assertEqual((r["s_letter"], r["s_form"], r["stated_credit"]), ("B", "phrase", 1))


class RunTests(unittest.TestCase):
    def setUp(self):
        self.s = g.summarize_run(copy.deepcopy(C.FIX_PREDICTIONS), C.FIX_GOLDS)

    def test_counts(self):
        self.assertEqual(self.s["counts"], C.FIX_RUN_COUNTS)
        self.assertEqual(self.s["stored_n"], C.FIX_RUN_STORED_N)
        self.assertEqual(self.s["mismatch"], C.FIX_RUN_MISMATCH)

    def test_version_and_means(self):
        v = g.choose_version(self.s["mismatch"])
        self.assertEqual(v, C.FIX_RUN_VERSION)
        self.assertEqual(g.run_mean(self.s["records"], lambda r: r["credit"][v]), C.FIX_RUN_MEAN_V3)
        self.assertEqual(g.run_mean(self.s["records"], lambda r: r["stated_credit"]), C.FIX_RUN_MEAN_STATED)
        self.assertIsNone(g.run_mean([], lambda r: 1))

    def test_classes(self):
        self.assertEqual(g.class_counts(self.s["records"], "v3"), C.FIX_RUN_CLASSES_V3)
        self.assertEqual(g.class_counts(self.s["records"], "v4"), C.FIX_RUN_CLASSES_V4)
        self.assertEqual(g.pr_up(self.s["records"], "v3"), C.FIX_RUN_PR_UP_V3)


class NamesAndAggregates(unittest.TestCase):
    def test_names(self):
        self.assertEqual(g.select_runs(C.FIX_SUITES), C.FIX_SELECT)
        for name, want in C.FIX_MODEL:
            self.assertEqual(g.model_part(name), want)

    def test_stat_entry(self):
        for (name, split), want in C.FIX_STAT_ENTRY:
            self.assertEqual(g.stat_entry(C.FIX_STATS, name, split), want)

    def test_group(self):
        self.assertEqual(g.group_values(C.FIX_GROUP, C.COLUMN_PREFIX), C.FIX_GROUP_VALUES)
        self.assertIsNone(g.group_values(C.FIX_GROUP, "Nope"))
        self.assertIsNone(g.group_values({}, C.COLUMN_PREFIX))

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
