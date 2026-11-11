"""Unit tests for audit 101 (standard library only). Every expectation is hand-traced in the comments. Apache-2.0."""

import math
import unittest
from fractions import Fraction

import cases101 as C
import grade101 as g


class TestHelmTranscription(unittest.TestCase):
    def test_indicator_keeps_last_token_only(self):
        # gold "... The answer is 7." -> last token "7."; pred "So 7." -> "7." -> 1
        self.assertEqual(g.exact_match_indicator(C.G1, "So 7."), 1)
        # "7" (no period) vs "7." -> 0
        self.assertEqual(g.exact_match_indicator(C.G1, "The answer is 7"), 0)
        # empty prediction -> exact_match's "not pred" -> 0
        self.assertEqual(g.exact_match_indicator(C.G1, ""), 0)

    def test_helm_final_number(self):
        # "<<3+4=7>>7 apples. The answer is 7." -> matches "3+4" (unescaped dot), "7", "7", "7" -> last "7"
        self.assertEqual(g.helm_final_number(C.G1), "7")
        # "1,000 apples, all" -> matches "1,000", "," -> last "," -> "" (HELM issue #4337)
        self.assertEqual(g.helm_final_number("1,000 apples, all"), "")
        # "7.0" -> "7" then ".0" via (?:.\d+) -> "7.0"
        self.assertEqual(g.helm_final_number("is 7.0"), "7.0")
        self.assertEqual(g.helm_final_number("none"), "")

    def test_final_number_exact_match(self):
        self.assertEqual(g.final_number_exact_match(C.G2, "The answer is 1,000."), 1)  # "1000" == "1000"
        self.assertEqual(g.final_number_exact_match(C.G1, "is 7.0"), 0)  # "7" vs "7.0" as strings
        self.assertEqual(g.final_number_exact_match(C.G1, ""), 0)

    def test_exact_match(self):
        self.assertEqual(g.exact_match("7.", " 7. "), 1)
        self.assertEqual(g.exact_match("7.", ""), 0)


class TestStatedAnswer(unittest.TestCase):
    def test_stated(self):
        # " $1,200.50." -> NUM_AFTER: "$", then "1,200.50" -> 120050/100 = 2401/2
        v, end = g.stated("The answer is $1,200.50.")
        self.assertEqual(v, Fraction(2401, 2))
        self.assertEqual(end, len("The answer is $1,200.50"))
        # first phrase is used: 6, not 7
        self.assertEqual(g.stated("The answer is 6. The answer is 7.")[0], 6)
        self.assertEqual(g.stated("The answer is 6. The answer is 7.", last=True)[0], 7)
        # no number right after the phrase -> (None, None); no phrase -> (None, None)
        self.assertEqual(g.stated("The answer is seven."), (None, None))
        self.assertEqual(g.stated("So 7."), (None, None))

    def test_gold_value_and_last_number(self):
        self.assertEqual(g.gold_value(C.G1), 7)
        self.assertEqual(g.gold_value(C.G2), 1000)
        self.assertEqual(g.gold_value("no phrase, 12 then 15."), 15)  # last number fallback
        self.assertEqual(g.last_number("1,000, so"), 1000)  # NUM_ANY "1,000," -> commas removed
        self.assertIsNone(g.last_number("none"))
        self.assertIsNone(g.to_value(","))

    def test_fixture_grades(self):
        # Traces: see cases101.FIX_GRADES; e.g. G1, "The answer is 7.\nQ: Tom has 5 pens. How many?" -> ind 0 (last
        # token "many?"), fnem 0 (last number 5), corr 1 (stated 7), rest ".\nQ: ..." has a newline -> continued.
        for (gold, pred), want in C.FIX_GRADES:
            r = g.grade_record([gold], pred)
            self.assertEqual((r["ind"], r["fnem"], r["corr"], r["cls"]), want, (gold, pred))

    def test_lone_comma(self):
        for pred, want in C.FIX_LONE_COMMA:
            self.assertEqual(g.lone_comma(pred), want, pred)

    def test_multi_reference_takes_max(self):
        # golds G2 (1000) and G1 (7), pred "The answer is 7.": ind 1 via G1; corr 1 via G1; cls None
        r = g.grade_record([C.G2, C.G1], "The answer is 7.")
        self.assertEqual((r["ind"], r["fnem"], r["corr"], r["cls"]), (1, 1, 1, None))


class TestCensus(unittest.TestCase):
    def test_fixture_run(self):
        s = g.summarize_run(C.FIX_INSTANCES, C.FIX_PREDS, C.CAP)
        for k, want in C.FIX_RUN.items():
            self.assertEqual(s[k], want, k)
        for k, want in C.FIX_RUN_KEYS.items():
            self.assertEqual(s["keys"][k], want, k)
        for k, want in C.FIX_RUN_MEANS.items():
            # ind: (1/2 + 1/2 + 0) / 3 = 1/3; fnem: (1 + 1 + 0) / 3 = 2/3; corr: (1 + 1/2 + 1/2) / 3 = 2/3
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
        self.assertEqual(g.model_of("gsm:model=org_m-1,stop=hash"), "org_m-1")
        sel = g.select_runs({"gsm:model=a": "v0.3.0", "dyck_language_np=3:model=a": "v0.3.0"}, C.PREFIX)
        self.assertEqual(sel, {"gsm:model=a": "v0.3.0"})

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
        # P1 540 >= 540 and 490 >= 486; P2 300 >= 300; P3 2 < 3; P4 1/100; P5 5; P6 0.9; P7 2 > 1, 0, 0, 0
        self.assertEqual(g.verdicts(C.FIX_VERDICT_ON), {k: True for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P7")})

    def test_past_boundary_all_fail(self):
        # P1 530 < 540; P2 300 < 301; P3 3 < 3 false; P4 99/10000; P5 4; P6 0.89; P7 1 > 1 false
        self.assertEqual(g.verdicts(C.FIX_VERDICT_PAST),
                         {k: False for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P7")})

    def test_missing_values(self):
        # P1 480 < 486; P2 no credits; P3 0 < 0 false; P4 None; P5 movers 5 -> True; P6 None; P7 under 0
        want = {k: False for k in ("P1", "P2", "P3", "P4", "P6", "P7")}
        want["P5"] = True
        self.assertEqual(g.verdicts(C.FIX_VERDICT_NONE), want)


if __name__ == "__main__":
    unittest.main()
