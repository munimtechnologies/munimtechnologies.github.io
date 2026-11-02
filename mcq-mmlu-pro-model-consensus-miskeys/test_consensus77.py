"""Unit tests for audit 77 (standard library only). Apache-2.0."""

import unittest
from fractions import Fraction

import cases77 as C
import consensus77 as cm


class TestPredIndex(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(cm.pred_index("B", 4), 1)
        self.assertEqual(cm.pred_index(" c ", 4), 2)
        self.assertIsNone(cm.pred_index("E", 4))     # out of range for k=4
        self.assertEqual(cm.pred_index("J", 10), 9)
        self.assertIsNone(cm.pred_index("Z", 10))
        self.assertIsNone(cm.pred_index("AB", 10))
        self.assertIsNone(cm.pred_index(None, 10))
        self.assertIsNone(cm.pred_index(3, 10))


class TestConsensusAndFlag(unittest.TestCase):
    def test_single_top(self):
        self.assertEqual(cm.consensus([1, 2, 0, 0], 0), (1, 2))

    def test_key_is_skipped(self):
        # key at 1 has the most picks; the best non-key is index 3 with 1
        self.assertEqual(cm.consensus([0, 5, 0, 1], 1), (3, 1))

    def test_tie_gives_none(self):
        self.assertEqual(cm.consensus([1, 1, 1, 0], 0), (None, 1))

    def test_tie_then_higher(self):
        # 2 and 2 tie, then a 3 breaks it
        self.assertEqual(cm.consensus([0, 2, 2, 3], 0), (3, 3))

    def test_no_non_key_pick(self):
        self.assertEqual(cm.consensus([0, 2, 0, 0], 1), (None, 0))

    def test_flag_needs_min_agree_and_beating_key(self):
        self.assertEqual(cm.flag_question([1, 2, 0, 0], 0, 2), (True, 1, 2))
        self.assertEqual(cm.flag_question([2, 2, 0, 0], 0, 2), (False, 1, 2))   # ties the key
        self.assertEqual(cm.flag_question([0, 1, 0, 0], 0, 2), (False, 1, 1))   # below min_agree

    def test_votes(self):
        self.assertEqual(cm.votes(["B", "Z", "E", None, "b"], 4), ([0, 2, 0, 0], 3))


class TestPanel(unittest.TestCase):
    def test_tie_break_by_name(self):
        # m3 and m5 tie at 0.7; m3 sorts first
        self.assertEqual(cm.select_panel(C.FIX_ACC, 3), ["m1", "m2", "m3"])
        self.assertEqual(cm.select_panel(C.FIX_ACC, 4), ["m1", "m2", "m3", "m5"])

    def test_accuracy_zero_n(self):
        self.assertEqual(cm.accuracy(0, 0), Fraction(0))


class TestFixture(unittest.TestCase):
    """Fixture 1 traced by hand (panel m1, m2, m3; min_agree 2):
    q1 k4 key A: B,B,A -> [1,2,0,0] consensus B (2) > key 1 -> flagged B
    q2 k4 key C: C,D,D -> [0,0,1,2] consensus D (2) > key 1 -> flagged D
    q3 k10 key A: B,C,A -> B and C tie at 1 -> no consensus
    q4 k4 key B: B,B,None -> [0,2,0,0] no non-key pick
    q5 k4 key D: A,A,D -> [2,0,0,1] consensus A -> flagged A
    q6 k4 key A: B,Z,E -> Z malformed, E out of range -> [0,1,0,0] B has 1 < 2 -> not flagged, consensus B
    q7 k4 key A: C,C,C -> flagged C
    q8 k4 key A: A,A,A -> no non-key pick
    Groups: miskey [1]; ok [2,3,4]; other_error [6]; unreviewed [7] (8 is ambiguous); stemez [5];
    ori_mmlu [1,2,3,4,6,7,8].
    P2: 1/1 vs 1/3 -> 1*3 >= 5*1*1 is False.  P3: target 1 flagged with B = experts' B -> [1,1,1] True.
    P4: flagged judged {1,2}, with an error label {1} -> 1/2 >= 1/5 True.  P5: 1/1 > 1/3 True.
    P6: stemez 1/1 > ori_mmlu 3/7 True."""

    def setUp(self):
        self.panel = cm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
        self.flags, self.tallies = cm.panel_flags(self.panel, C.FIX_PREDS, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
        self.g = cm.groups(C.FIX_QUESTIONS.keys(), C.FIX_FAMILY, C.FIX_LABELS, C.FIX_AMBIGUOUS)

    def test_panel(self):
        self.assertEqual(self.panel, C.FIX_TARGET["panel"])

    def test_flags(self):
        self.assertEqual(self.flags, C.FIX_TARGET["flags"])

    def test_tallies(self):
        self.assertEqual(self.tallies[4], ([0, 2, 0, 0], 1))
        self.assertEqual(self.tallies[6], ([0, 1, 0, 0], 2))
        self.assertEqual(self.tallies[3], ([1, 1, 1, 0, 0, 0, 0, 0, 0, 0], 0))

    def test_groups(self):
        self.assertEqual(self.g["miskey"], [1])
        self.assertEqual(self.g["ok"], [2, 3, 4])
        self.assertEqual(self.g["other_error"], [6])
        self.assertEqual(self.g["unreviewed_ori_mmlu"], [7])
        self.assertEqual(self.g["ambiguous_ori_mmlu"], [8])
        self.assertEqual(self.g["stemez"], [5])
        self.assertEqual(self.g["ori_mmlu"], [1, 2, 3, 4, 6, 7, 8])
        self.assertEqual(self.g["all"], [1, 2, 3, 4, 5, 6, 7, 8])

    def test_verdicts(self):
        v = cm.predictions(self.g, self.flags, C.FIX_TARGETS, C.THRESHOLDS)
        self.assertEqual(v, C.FIX_TARGET["verdicts"])

    def test_curve(self):
        keys = {q: kk[1] for q, kk in C.FIX_QUESTIONS.items()}
        rows = cm.curve(self.tallies, keys, self.g, (2, 3))
        # min_agree 2 reproduces the flags: all 4 flagged (1,2,5,7); min_agree 3 keeps only q7 (C,C,C)
        self.assertEqual(rows[0]["all"], [4, 8])
        self.assertEqual(rows[1]["all"], [1, 8])
        self.assertEqual(rows[1]["unreviewed_ori_mmlu"], [1, 1])
        self.assertEqual(rows[1]["miskey"], [0, 1])


class TestReduxJoin(unittest.TestCase):
    """Fixture 2 traced by hand: R1 ('Q  one' normalises to 'Q one') joins MMLU and single-matches Pro id 10 (3 of 4
    options shared; the stemez row with the same stem is not indexed); R2 joins MMLU but Pro id 20 shares only 2
    options (stem_only); R3 matches two same-subject Pro rows (30, 31) -> ambiguous; R4 has no MMLU match."""

    def test_join(self):
        labels, amb, mk, counts = cm.redux_labels(C.FIX_REDUX, C.FIX_MMLU, C.FIX_PRO)
        t = C.FIX_REDUX_TARGET
        self.assertEqual(labels, t["labels"])
        self.assertEqual(amb, t["ambiguous_ids"])
        self.assertEqual(mk, t["miskey_ids"])
        self.assertEqual(counts, t["counts"])

    def test_conflict(self):
        rows = C.FIX_REDUX + [dict(C.FIX_REDUX[0], label="ok")]
        labels, _amb, mk, counts = cm.redux_labels(rows, C.FIX_MMLU, C.FIX_PRO)
        self.assertEqual(labels, {10: "conflict"})
        self.assertEqual(mk, {10})
        self.assertEqual(counts["label_conflicts"], 1)
        self.assertEqual(counts["pro_join"]["in_pro"], 2)


class TestFrozen(unittest.TestCase):
    def test_targets(self):
        self.assertEqual(len(C.TARGETS), C.N_TARGETS)
        self.assertEqual(len(set(t[0] for t in C.TARGETS)), C.N_TARGETS)
        self.assertEqual(sum(1 for t in C.TARGETS if t[4] == "primary"), C.N_PRIMARY)
        self.assertTrue(all(t[0] in C.MISKEY_IDS for t in C.TARGETS))
        self.assertTrue(all(t[2] != t[3] for t in C.TARGETS))
        self.assertEqual(len(C.MISKEY_IDS), C.N_MISKEY_IDS)

    def test_rule(self):
        self.assertEqual((C.PANEL_SIZE, C.MIN_AGREE), (10, 6))
        self.assertIn(C.MIN_AGREE, C.CURVE_MS)
        self.assertEqual(len(C.ARCHIVES), 48)
        self.assertEqual(C.model_name("model_outputs_arx_0314_5shots.json.zip"), "arx_0314_5shots")


if __name__ == "__main__":
    unittest.main()
