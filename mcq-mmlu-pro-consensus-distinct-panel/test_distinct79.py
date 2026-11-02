"""Unit tests for audit 79 (standard library only). Every expectation below is traced by hand in the comments.
Apache-2.0."""

import unittest
from fractions import Fraction

import distinct79 as dm
import cases79 as C


class TestCopied(unittest.TestCase):
    def test_panel_and_flags(self):
        # Same fixture and expected values as audits 77 and 78 (both passed in sealed runs on 2026-11-02).
        panel = dm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
        self.assertEqual(panel, ["m1", "m2", "m3"])
        flags, _t = dm.panel_flags(panel, C.FIX_PREDS, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
        self.assertEqual(flags, C.FIX_TARGET["flags"])

    def test_redux_join(self):
        labels, amb, mk, counts = dm.redux_labels(C.FIX_REDUX, C.FIX_MMLU, C.FIX_PRO)
        t = C.FIX_REDUX_TARGET
        self.assertEqual(labels, t["labels"])
        self.assertEqual(amb, t["ambiguous_ids"])
        self.assertEqual(mk, t["miskey_ids"])
        self.assertEqual(counts, t["counts"])


class TestDistinctPanel(unittest.TestCase):
    def test_select_distinct_panel(self):
        # Order by (-accuracy, name): a1 .9, a2 .8, b1 .7, c1 .6, e1 .6 (c1 before e1 by name), d1 .5.
        # a1 takes line A; a2 is line A -> skipped; b1, c1 fill the panel of 3.
        self.assertEqual(dm.select_distinct_panel(C.FIX_D_ACC, C.FIX_D_SIZE, C.FIX_D_LINES), C.FIX_D_TARGET)
        # Without lines it equals the plain panel rule.
        self.assertEqual(dm.select_distinct_panel(C.FIX_D_ACC, 3, {}), dm.select_panel(C.FIX_D_ACC, 3))
        self.assertEqual(dm.select_panel(C.FIX_D_ACC, 3), ["a1", "a2", "b1"])

    def test_line_of(self):
        self.assertEqual(dm.line_of("a2", C.FIX_D_LINES), "A")
        self.assertEqual(dm.line_of("b1", C.FIX_D_LINES), "b1")
        self.assertEqual(dm.line_of("sonnet-3.5_0shots_09_34_29", C.LINES), "claude-3.5-sonnet")
        self.assertEqual(dm.line_of("gpt-4o-mini_5shots", C.LINES), "gpt-4o-mini_5shots")


class TestWrongAgreement(unittest.TestCase):
    def test_wrong_agreement(self):
        # a1 vs a2: q1 B,B key A -> both wrong, same; q2 C,D -> both wrong, differ; q3 key B: A,A -> same;
        # q4 a1 picks the key -> skipped; q5 has 3 options, a1's D is out of range -> skipped. (2, 3).
        p = C.FIX_W_PREDS
        self.assertEqual(dm.wrong_agreement(p["a1"], p["a2"], C.FIX_W_QUESTIONS), C.FIX_W_TARGET["a1_a2"])

    def test_pair_rates(self):
        # a1|b1: q1 B/C differ, q2 C/C same, q3 A/C differ, q4 a1 key, q5 a1 invalid -> (1, 3).
        # a2|b1: q1 B/C, q2 D/C, q3 A/C, q4 B/C, q5 A/B (key C) -> all differ -> (0, 5).
        within, cross = dm.pair_rates(["b1", "a2", "a1"], C.FIX_W_PREDS, C.FIX_W_QUESTIONS, C.FIX_D_LINES)
        self.assertEqual(within, C.FIX_W_TARGET["within"])
        self.assertEqual(cross, C.FIX_W_TARGET["cross"])

    def test_median(self):
        self.assertEqual(dm.median([Fraction(1, 3), Fraction(0)]), Fraction(1, 6))
        self.assertEqual(dm.median([3, 1, 2]), 2)
        self.assertIsNone(dm.median([]))


class TestVerdicts(unittest.TestCase):
    def test_precision(self):
        # D: miskey flagged 1 (q1) + other_error flagged 1 (q7) = 2; OK flagged 1 (q3) -> (2, 3).
        # A: miskey flagged 2 + other_error 0 = 2; OK flagged 2 (q3, q4) -> (2, 4).
        self.assertEqual(dm.flag_precision(C.FIX_FLAGS_D, C.FIX_G), (2, 3))
        self.assertEqual(dm.flag_precision(C.FIX_FLAGS_A, C.FIX_G), (2, 4))

    def test_verdicts(self):
        # P2: 1*4 = 4 >= 5*1*2 = 10? no -> False. P3: 2/3 > 2/4 -> True. P4: 1 >= 30? no -> False.
        # P5: within min 2/3 > cross median (0 + 1/3)/2 = 1/6 -> True.
        # P6: stemez 1/2 < ori_mmlu 3/7 (q1, q3, q7)? no -> False.
        within, cross = C.FIX_W_TARGET["within"], C.FIX_W_TARGET["cross"]
        v = dm.predictions79(C.FIX_G, C.FIX_FLAGS_A, C.FIX_FLAGS_D, within, cross, C.THRESHOLDS)
        self.assertEqual(v, C.FIX_VERDICTS)

    def test_empty_within_is_false(self):
        v = dm.predictions79(C.FIX_G, C.FIX_FLAGS_A, C.FIX_FLAGS_D, {}, C.FIX_W_TARGET["cross"], C.THRESHOLDS)
        self.assertFalse(v["P5_within_line_above_cross_median"])
        self.assertEqual(v["P5_counts"][0], "None")


class TestFrozen(unittest.TestCase):
    def test_rule_and_thresholds(self):
        self.assertEqual((C.PANEL_SIZE, C.MIN_AGREE), (10, 6))
        self.assertEqual(C.THRESHOLDS, {"P2_ratio": Fraction(5), "P4_min_miskeys": 30})
        self.assertEqual(len(C.ARCHIVES), 48)
        names = {C.model_name(z) for z in C.ARCHIVES}
        self.assertTrue(set(C.EXPECTED_PANEL) <= names)
        self.assertTrue(set(C.EXPECTED_DISTINCT_PANEL) <= names)
        self.assertTrue(set(C.LINES) <= names)
        self.assertEqual(len(set(C.EXPECTED_DISTINCT_PANEL)), 10)
        lines = [dm.line_of(m, C.LINES) for m in C.EXPECTED_DISTINCT_PANEL]
        self.assertEqual(len(set(lines)), 10)
        # Audit 77's panel holds 10 archives from 6 lines; the union of both panels holds 14 archives.
        self.assertEqual(len({dm.line_of(m, C.LINES) for m in C.EXPECTED_PANEL}), 6)
        self.assertEqual(len(set(C.EXPECTED_PANEL) | set(C.EXPECTED_DISTINCT_PANEL)), 14)
        self.assertEqual(C.EXPECTED_77_FLAGGED["all"], 1210)
        self.assertEqual(C.EXPECTED_77_PRECISION, (65, 359))


if __name__ == "__main__":
    unittest.main()
