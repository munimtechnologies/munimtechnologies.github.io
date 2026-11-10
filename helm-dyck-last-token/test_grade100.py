"""Unit tests for audit 100 (standard library only). Every expectation is hand-traced in the comments. Apache-2.0."""

import math
import unittest
from fractions import Fraction

import cases100 as C
import grade100 as g


class TestHelmTranscription(unittest.TestCase):
    def test_indicator_keeps_last_token_only(self):
        # " ) ] }".split(" ") = ["", ")", "]", "}"] -> "}"; "] ) }" -> "}" -> equal -> 1
        self.assertEqual(g.exact_match_indicator(" ) ] }", "] ) }"), 1)
        # ")]}" has no space -> compared whole with "}" -> 0
        self.assertEqual(g.exact_match_indicator(" ) ] }", ")]}"), 0)
        # empty prediction -> exact_match's "not pred" -> 0
        self.assertEqual(g.exact_match_indicator(" }", ""), 0)

    def test_exact_match(self):
        self.assertEqual(g.exact_match("}", " } "), 1)
        self.assertEqual(g.exact_match("}", ""), 0)


class TestGrades(unittest.TestCase):
    def test_fixture_grades(self):
        # Traces: see cases100.FIX_GRADES; e.g. gold " ) ] }", pred "}" -> ind 1 (last tokens "}"), strict 0
        # (")]}" vs "}"), lenient 0, pb "}" is a proper suffix of ")]}" -> missing_leading.
        for (gold, pred), want in C.FIX_GRADES:
            r = g.grade_record([gold], pred)
            self.assertEqual((r["ind"], r["strict"], r["lenient"], r["cls"]), want, (gold, pred))

    def test_multi_reference_takes_max(self):
        # golds " )" and " ] )", pred "] )": ind 1 for both; strict 0 vs ")" and 1 vs "])" -> 1; cls None
        r = g.grade_record([" )", " ] )"], "] )")
        self.assertEqual((r["ind"], r["strict"], r["lenient"], r["cls"]), (1, 1, 1, None))

    def test_depth_and_helpers(self):
        self.assertEqual(g.depth(" ) ] }"), 3)
        self.assertEqual(g.depth(" }"), 1)
        self.assertEqual(g.seq(" ) ]\t}"), ")]}")
        self.assertEqual(g.brackets("so ) and ]"), ")]")


class TestCensus(unittest.TestCase):
    def test_fixture_run(self):
        s = g.summarize_run(C.FIX_INSTANCES, C.FIX_PREDS, C.CAP)
        for k, want in C.FIX_RUN.items():
            self.assertEqual(s[k], want, k)
        for k, want in C.FIX_RUN_KEYS.items():
            self.assertEqual(s["keys"][k], want, k)
        for k, want in C.FIX_RUN_MEANS.items():
            # ind: (3/3 + 1/3) / 2 = 2/3; strict and lenient: (2/3 + 1/3) / 2 = 1/2
            self.assertEqual(g.run_mean(s["trials"], k), want, k)

    def test_run_mean_empty(self):
        self.assertIsNone(g.run_mean({}, "ind"))


class TestRanksAndTau(unittest.TestCase):
    def test_ranks(self):
        r = g.ranks_high({"a": Fraction(1, 2), "b": Fraction(1, 2), "c": Fraction(1, 3)})
        self.assertEqual(r, {"a": 1, "b": 1, "c": 3})

    def test_tau(self):
        # pairs (0,1) c, (0,2) c, (1,2) d -> (2 - 1) / 3
        self.assertAlmostEqual(g.kendall_tau_b([1, 2, 3], [1, 3, 2]), 1 / 3, places=12)
        # x tie on (0,1): tx = 1; (0,2), (1,2) c -> 2 / sqrt((3-1)*(3-0))
        self.assertAlmostEqual(g.kendall_tau_b([1, 1, 2], [1, 2, 3]), 2 / math.sqrt(6), places=12)
        self.assertIsNone(g.kendall_tau_b([1, 1], [1, 2]))

    def test_group_and_match(self):
        self.assertEqual(g.group_em_values(C.FIX_GROUP), C.FIX_GROUP_VALUES)
        self.assertIsNone(g.group_em_values([{"header": [{"value": "X"}], "rows": []}]))
        # 0.3 finds nothing; 0.5 takes 0.5 -> 1
        self.assertEqual(g.match_cells({"r1": 0.5, "r2": 0.3}, [0.25, 0.5], C.TOL_CELL), 1)

    def test_model_and_select(self):
        self.assertEqual(g.model_of("dyck_language_np=3:model=org_m-1,stop=hash"), "org_m-1")
        sel = g.select_runs({"dyck_language_np=3:model=a": "v0.3.0", "gsm:model=a": "v0.3.0"}, C.PREFIX)
        self.assertEqual(sel, {"dyck_language_np=3:model=a": "v0.3.0"})

    def test_stat_entry(self):
        stats = [{"name": {"name": "exact_match_indicator", "split": "test"}, "count": 3, "sum": 1.5, "mean": 0.5},
                 {"name": {"name": "exact_match_indicator", "split": "test", "perturbation": {"name": "x"}},
                  "count": 3, "sum": 0.0, "mean": 0.0}]
        self.assertEqual(g.stat_entry(stats, "exact_match_indicator"), {"count": 3, "sum": 1.5, "mean": 0.5})
        self.assertIsNone(g.stat_entry(stats, "exact_match"))

    def test_pick(self):
        self.assertIsNone(g.pick([], "s"))
        lst = [("id1", 0), ("id2", 1), ("id3", 2)]
        p = g.pick(lst, "salt")
        self.assertIn(p, lst)
        self.assertEqual(p, g.pick(list(reversed(lst)), "salt"))


class TestVerdicts(unittest.TestCase):
    def test_on_boundary_all_hold(self):
        # P1 540 >= 540 and 490 >= 486; P2 5/100 = 1/20; P3 2/10 > 1/10; P4 1/20; P5 5; P6 0.8; P7 4 < 5
        self.assertEqual(g.verdicts(C.FIX_VERDICT_ON), {k: True for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P7")})

    def test_past_boundary_all_fail(self):
        # P1 530 < 540; P2 4/100; P3 2/10 = 2/10; P4 49/1000; P5 4; P6 0.79; P7 4 < 4 false
        self.assertEqual(g.verdicts(C.FIX_VERDICT_PAST),
                         {k: False for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P7")})

    def test_missing_values(self):
        # P1 480 < 486; P2 no credits; P3 no depths; P4 None; P5 movers 5 -> True; P6 None; P7 wrong 0
        want = {k: False for k in ("P1", "P2", "P3", "P4", "P6", "P7")}
        want["P5"] = True
        self.assertEqual(g.verdicts(C.FIX_VERDICT_NONE), want)


if __name__ == "__main__":
    unittest.main()
