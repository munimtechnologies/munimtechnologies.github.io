"""Unit tests for audit 78 (standard library only). Every expectation below is traced by hand in the comments.
Apache-2.0."""

import unittest
from fractions import Fraction

import added78 as am
import cases78 as C

O, A = am.ORIGINAL, am.ADDED


class TestCopiedFromAudit77(unittest.TestCase):
    def test_panel_and_flags(self):
        # Same fixture and expected values as audit 77 (its test passed in the sealed run of 2026-11-02).
        panel = am.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
        self.assertEqual(panel, ["m1", "m2", "m3"])
        flags, _t = am.panel_flags(panel, C.FIX_PREDS, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
        self.assertEqual(flags, C.FIX_TARGET["flags"])

    def test_redux_join(self):
        labels, amb, mk, counts = am.redux_labels(C.FIX_REDUX, C.FIX_MMLU, C.FIX_PRO)
        t = C.FIX_REDUX_TARGET
        self.assertEqual(labels, t["labels"])
        self.assertEqual(amb, t["ambiguous_ids"])
        self.assertEqual(mk, t["miskey_ids"])
        self.assertEqual(counts, t["counts"])


class TestMap(unittest.TestCase):
    def test_map(self):
        # Pro index (ori_mmlu only): "Q one" -> [1], "Q two" -> [2], "Q six" -> [3]; id 4 is stemez, excluded.
        # MMLU row 1 (Q one, a b c d): overlap with [b x1 a c d x2] = 4, same subject -> in_pro, id 1.
        # MMLU row 2 ("Q  two" -> "Q two", e f g h): overlap with [e f y1 y2] = 2 < 3 -> not_in_pro.
        # MMLU row 3 (Q six, m n o p): overlap with [m n o "p " z] = 4 -> in_pro, id 3.
        # MMLU row 4 (Q six, m n o q): overlap 3 -> in_pro, id 3 again with a different choice set.
        # MMLU row 5: answer 7 out of range -> skipped.
        # in_pro 3, not_in_pro 1; id 3 has two choice sets -> multi_mmlu 1, dropped.
        mapping, counts = am.map_mmlu_to_pro(C.FIX_MAP_MMLU, C.FIX_MAP_PRO)
        self.assertEqual(mapping, {1: ("a", "b", "c", "d")})
        self.assertEqual(counts, {"in_pro": 3, "ambiguous_pro": 0, "not_in_pro": 1, "multi_mmlu": 1})
        self.assertEqual(mapping, C.FIX_MAP_TARGET["mapping"])
        self.assertEqual(counts, C.FIX_MAP_TARGET["counts"])

    def test_origins(self):
        # [b x1 a c d x2] against {a b c d}: O A O O O A, all four present -> intact.
        self.assertEqual(am.origins(C.FIX_MAP_PRO[0]["options"], ("a", "b", "c", "d")), C.FIX_MAP_TARGET["origins_1"])
        self.assertEqual(am.origins(["b", "x1", "a", "c", "d", "x2"], ("a", "b", "c", "d")),
                         ([O, A, O, O, O, A], True))
        # whitespace is normalised: "p " equals "p".
        self.assertEqual(am.origins(["m", "n", "o", "p ", "z"], ("m", "n", "o", "p")), ([O, O, O, O, A], True))
        # d missing -> not intact.
        self.assertEqual(am.origins(["a", "b", "c", "x1", "x2"], ("a", "b", "c", "d")), ([O, O, O, A, A], False))
        # duplicate MMLU choices (3 distinct) -> never intact.
        self.assertEqual(am.origins(["a", "b", "c", "z"], ("a", "b", "c", "c")), ([O, O, O, A], False))


class TestOriginCounts(unittest.TestCase):
    def test_consensus_origin(self):
        # miskey [1, 2]: q1 consensus 1 -> O; q2 consensus 4 -> A.
        self.assertEqual(am.consensus_origin(C.FIX_FLAGS, C.FIX_ORIGIN, [1, 2]), (1, 1))
        # ok [3, 4, 5]: q3 idx1 -> A; q4 idx0 -> A; q5 idx2 -> O.
        self.assertEqual(am.consensus_origin(C.FIX_FLAGS, C.FIX_ORIGIN, [3, 4, 5]), (1, 2))
        # unflagged (6, 7) never count; 7 also has no origins.
        self.assertEqual(am.consensus_origin(C.FIX_FLAGS, C.FIX_ORIGIN, [6, 7]), (0, 0))

    def test_wrong_pick_origin(self):
        # Only q6 is unflagged with origins: counts [5,2,1,1,0], key 0 -> idx1 O x2, idx2 A x1, idx3 A x1.
        self.assertEqual(am.wrong_pick_origin(C.FIX_TALLIES, C.FIX_KEYS, C.FIX_FLAGS, C.FIX_ORIGIN,
                                              [1, 2, 3, 4, 5, 6, 7]), (2, 2))

    def test_verdicts(self):
        # P2: 1 of 2 original = 1/2 < 4/5 -> False. P3: 2 of 3 added >= 1/2 -> True.
        # P4: 2*(2+2)=8 > 2*(1+2)=6 -> True. Law [1,3,5,7]: O, A, O -> (2,1); rest [2,4,6]: A, A -> (0,2);
        # P5: 1*2=2 > 2*3=6 is False.
        v = am.predictions78(C.FIX_G, C.FIX_FLAGS, C.FIX_TALLIES, C.FIX_KEYS, C.FIX_ORIGIN, C.FIX_CATEGORY,
                             C.THRESHOLDS)
        self.assertEqual(v, C.FIX_VERDICTS)


class TestFrozen(unittest.TestCase):
    def test_rule_and_thresholds(self):
        self.assertEqual((C.PANEL_SIZE, C.MIN_AGREE), (10, 6))
        self.assertEqual(C.THRESHOLDS, {"P2_original": Fraction(4, 5), "P3_added": Fraction(1, 2)})
        self.assertEqual(len(C.EXPECTED_PANEL), 10)
        self.assertEqual(len(set(C.EXPECTED_PANEL)), 10)
        self.assertEqual(len(C.ARCHIVES), 48)
        names = {C.model_name(z) for z in C.ARCHIVES}
        self.assertTrue(set(C.EXPECTED_PANEL) <= names)
        self.assertEqual(C.EXPECTED_77_FLAGGED["all"], 1210)


if __name__ == "__main__":
    unittest.main()
