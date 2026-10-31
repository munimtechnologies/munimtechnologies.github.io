"""Unit tests for audit 71 (stdlib only). Every expected value was traced by hand. Apache-2.0."""

import unittest
from fractions import Fraction as F

import cases
import keydrift as kd


class TestOneOption(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(kd.numbers("x = 3.5 and 12"), ("3", "5", "12"))
        self.assertEqual(kd.numbers("٣"), ("3",))          # Arabic-Indic three
        self.assertEqual(kd.numbers("１２"), ("12",))   # full-width 12, folded by NFKC
        self.assertEqual(kd.numbers("007"), ("7",))
        self.assertEqual(kd.numbers("abc"), ())
        self.assertEqual(kd.numbers(None), ())

    def test_matches(self):
        self.assertTrue(kd.matches("Paris", " Paris "))
        self.assertTrue(kd.matches("10 m", "10 米"))
        self.assertFalse(kd.matches("red", "红"))
        self.assertFalse(kd.matches("", ""))
        self.assertFalse(kd.matches("10 m", "100 m"))

    def test_key_and_validity(self):
        self.assertEqual(kd.key_index("A"), 0)
        self.assertEqual(kd.key_index(" d "), 3)
        self.assertIsNone(kd.key_index("E"))
        self.assertIsNone(kd.key_index(None))
        self.assertTrue(kd.is_valid(["a", "b"], 1))
        self.assertFalse(kd.is_valid(["a", " "], 0))
        self.assertFalse(kd.is_valid(["a", "b"], 2))
        self.assertFalse(kd.is_valid(["a", "b"], None))

    def test_pick_longest_credit(self):
        self.assertEqual(kd.pick_longest_credit(["a", "bb", "ccc", "dddd"], 3), F(1))
        self.assertEqual(kd.pick_longest_credit(["a", "bb", "ccc", "dddd"], 0), F(0))
        self.assertEqual(kd.pick_longest_credit(["pp", "qq", "r", "s"], 1), F(1, 2))


class TestPermutation(unittest.TestCase):
    def test_identity_and_swap(self):
        self.assertEqual(kd.permutation(["1", "2", "3", "4"], ["1", "2", "3", "4"]), (0, 1, 2, 3))
        self.assertEqual(kd.permutation(["1", "2", "3", "4"], ["2", "1", "3", "4"]), (1, 0, 2, 3))

    def test_ambiguous_or_incomplete(self):
        # translated "1" matches English "1" by text and "1 m" by number -> ambiguous
        self.assertIsNone(kd.permutation(["1", "1 m", "3", "4"], ["1", "1", "3", "4"]))
        # two translated options hit the same English option
        self.assertIsNone(kd.permutation(["1", "2", "3", "4"], ["1", "1", "3", "4"]))
        self.assertIsNone(kd.permutation(["1", "2", "3", "4"], ["1", "2", "3"]))
        self.assertIsNone(kd.permutation(["red", "green"], ["红", "绿"]))

    def test_order_and_kind(self):
        self.assertEqual(kd.order_of(None), "unresolved")
        self.assertEqual(kd.order_of((0, 1, 2, 3)), "same_order")
        self.assertEqual(kd.order_of((1, 0, 2, 3)), "reordered")
        self.assertEqual(kd.kind_of("unresolved", "unknown"), "unresolved")
        self.assertEqual(kd.kind_of("reordered", "same"), "same_answer_new_letter")
        self.assertEqual(kd.kind_of("same_order", "different"), "different_answer_same_order")
        self.assertEqual(kd.kind_of("reordered", "different"), "different_answer_reordered")


class TestTally(unittest.TestCase):
    def test_fixture(self):
        ref = kd.reference(cases.FIXTURE_EN)
        self.assertEqual(len(ref), 6)
        tally, mism = kd.tally_language(ref, cases.FIXTURE_XX)
        self.assertEqual(tally, cases.FIXTURE_TALLY)
        self.assertEqual(mism, cases.FIXTURE_MISMATCHES)

    def test_overlap(self):
        self.assertEqual(kd.overlap({"a": 1, "b": 2}, {"b": 2, "c": 0}), {"shared": 1, "same_key": 1})
        self.assertEqual(kd.overlap({"a": 1, "b": 2}, {"a": 3, "b": 2}), {"shared": 2, "same_key": 1})
        self.assertEqual(kd.overlap({}, {"a": 1}), {"shared": 0, "same_key": 0})


class TestRedux(unittest.TestCase):
    def test_labels_and_corrections(self):
        self.assertEqual(kd.normalise_label(" Wrong_Groundtruth "), "wrong_groundtruth")
        self.assertEqual(kd.label_class("ok"), "ok")
        self.assertEqual(kd.label_class("no_correct_answer"), "error")
        self.assertEqual(kd.label_class("expert"), "unsure")
        self.assertEqual(kd.label_class(""), "other")
        self.assertEqual(kd.letter_correction("B"), 1)
        self.assertEqual(kd.letter_correction("(c)"), 2)
        self.assertEqual(kd.letter_correction("D."), 3)
        self.assertEqual(kd.letter_correction(" b "), 1)
        self.assertIsNone(kd.letter_correction("A, C"))
        self.assertIsNone(kd.letter_correction("3"))
        self.assertIsNone(kd.letter_correction("E"))
        self.assertIsNone(kd.letter_correction(None))

    def test_join(self):
        ref = kd.reference(cases.FIXTURE_EN)
        joined, st = kd.join_redux(list(ref.values()), cases.FIXTURE_REDUX)
        self.assertEqual(st, cases.FIXTURE_JOIN_STATS)
        self.assertEqual(sorted(joined), ["s/test/0", "s/test/2"])

    def test_join_ambiguous(self):
        en = [cases._e("s/test/0", ["1", "2"], 0)]
        rx = [cases._x(["1", "2"], 0, "ok"), cases._x(["1", "2"], 1, "ok")]
        joined, st = kd.join_redux(en, rx)
        self.assertEqual(joined, {})
        self.assertEqual(st["ambiguous"], 2)
        self.assertEqual(st["joined"] + st["not_found"] + st["ambiguous"], st["n_redux"])

    def test_profile_and_correction(self):
        ref = kd.reference(cases.FIXTURE_EN)
        joined, _ = kd.join_redux(list(ref.values()), cases.FIXTURE_REDUX)
        p = kd.redux_profile(["s/test/0", "s/test/2", "s/test/1"], joined)
        self.assertEqual(p, {"n": 3, "joined": 2, "classes": {"ok": 1, "error": 1},
                             "labels": {"ok": 1, "wrong_groundtruth": 1}})
        _, mism = kd.tally_language(ref, cases.FIXTURE_XX)
        got = kd.correction_agreement({s: v[0] for s, v in mism.items()}, joined)
        self.assertEqual(got, cases.FIXTURE_TARGET["correction"])
        # the English key itself equals the published key, never the correction
        self.assertEqual(kd.correction_agreement({"s/test/2": 2}, joined),
                         {"n": 1, "equals_correction": 0, "equals_published": 1, "other": 0})


if __name__ == "__main__":
    unittest.main()
