"""Unit tests for audit 69 (stdlib only). Every expected value was traced by hand. Apache-2.0."""

import unittest
from fractions import Fraction as F

import cases
import redux_length as rl

O4 = cases.O4


class TestOneQuestion(unittest.TestCase):
    def test_credits(self):
        self.assertEqual(rl.credits(O4, 3), (F(1), F(0)))
        self.assertEqual(rl.credits(O4, 0), (F(0), F(1)))
        self.assertEqual(rl.credits(["pp", "qq", "r", "s"], 1), (F(1, 2), F(0)))
        self.assertEqual(rl.credits(["a", "b", "c", "eeeee"], 2), (F(0), F(1, 3)))
        self.assertEqual(rl.credits(["  a  ", "bb"], 0), (F(0), F(1)))  # outer spaces are stripped

    def test_length_rank(self):
        self.assertEqual(rl.length_rank(O4, 3), F(1))
        self.assertEqual(rl.length_rank(O4, 0), F(0))
        self.assertEqual(rl.length_rank(O4, 1), F(1, 3))
        self.assertEqual(rl.length_rank(["pp", "qq", "r", "s"], 1), F(5, 6))
        self.assertEqual(rl.length_rank(["a", "b", "c", "eeeee"], 2), F(1, 3))

    def test_unique_extremes(self):
        self.assertEqual(rl.unique_longest(O4), 3)
        self.assertEqual(rl.unique_shortest(O4), 0)
        self.assertIsNone(rl.unique_longest(["pp", "qq", "r", "s"]))
        self.assertIsNone(rl.unique_shortest(["pp", "qq", "r", "s"]))

    def test_validity(self):
        self.assertTrue(rl.is_valid(O4, 0))
        self.assertFalse(rl.is_valid(["a", " "], 0))
        self.assertFalse(rl.is_valid(["a", "b"], 2))
        self.assertFalse(rl.is_valid(["a", "b"], True))
        self.assertFalse(rl.is_valid(["a"], 0))

    def test_labels(self):
        self.assertEqual(rl.normalise_label(" OK "), "ok")
        self.assertEqual(rl.error_class("ok"), "ok")
        self.assertEqual(rl.error_class("wrong_groundtruth"), "error")
        self.assertEqual(rl.error_class("expert"), "unsure")
        self.assertEqual(rl.error_class("other"), "unknown")


class TestCorrection(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(rl.parse_correction(None, O4), ("none", ()))
        self.assertEqual(rl.parse_correction("  ", O4), ("none", ()))
        self.assertEqual(rl.parse_correction("D", O4), ("letters", (3,)))
        self.assertEqual(rl.parse_correction("(B)", O4), ("letters", (1,)))
        self.assertEqual(rl.parse_correction("A,C", O4), ("letters", (0, 2)))
        self.assertEqual(rl.parse_correction("A, B and C", O4), ("letters", (0, 1, 2)))
        self.assertEqual(rl.parse_correction("E", O4), ("unmatched", ()))
        self.assertEqual(rl.parse_correction("zzz", ["x", "yy", "zzz", "wwww"]), ("text", (2,)))
        self.assertEqual(rl.parse_correction(" ZZZ ", ["x", "yy", "zzz", "wwww"]), ("text", (2,)))
        self.assertEqual(rl.parse_correction("3", ["a", "b", "c", "eeeee"]), ("digits", (3,)))
        self.assertEqual(rl.parse_correction("3", ["1", "2", "3", "4"]), ("text", (2,)))
        self.assertEqual(rl.parse_correction("10,000/250,000", O4), ("unmatched", ()))
        self.assertEqual(rl.parse_correction("Observer bias", O4), ("unmatched", ()))

    def test_resolve(self):
        self.assertEqual(rl.resolve("letters", (3,), 4), (3,))
        self.assertEqual(rl.resolve("text", (2,), 4), (2,))
        self.assertIsNone(rl.resolve("digits", (3,), 4))
        self.assertEqual(rl.resolve("digits", (3,), 4, 0), (3,))
        self.assertEqual(rl.resolve("digits", (3,), 4, 1), (2,))
        self.assertIsNone(rl.resolve("digits", (0,), 4, 1))
        self.assertIsNone(rl.resolve("unmatched", (), 4, 0))


class TestFixture(unittest.TestCase):
    def setUp(self):
        self.rows = cases.FIXTURE_ROWS
        self.t = cases.FIXTURE_TARGET

    def test_census(self):
        c = rl.census(self.rows)
        self.assertEqual(c["n_rows"], self.t["n_rows"])
        self.assertEqual(c["n_invalid"], self.t["n_invalid"])
        self.assertEqual(c["labels"], self.t["labels"])
        self.assertEqual(c["subjects"], {"S1": 6, "S2": 5})
        for s in ("ALL", "class=ok", "class=error", "class=unsure", "label=wrong_groundtruth", "ok|subject=S1"):
            self.assertEqual(rl.exact(c["accs"][s]), self.t[s], s)
        self.assertNotIn("ok|subject=S2", c["accs"])

    def test_floor_report(self):
        r = rl.floor_report(rl.census(self.rows)["accs"]["class=ok"])
        self.assertEqual(r["n"], 3)
        self.assertAlmostEqual(r["lift"], 0.25, places=12)
        self.assertAlmostEqual(r["ratio"], 2.0, places=12)
        self.assertAlmostEqual(r["se"], (1 / 12) ** 0.5, places=12)
        self.assertAlmostEqual(r["z"], 0.25 / (1 / 12) ** 0.5, places=12)

    def test_miskey_pairs(self):
        pairs, why = rl.miskey_pairs(self.rows)
        self.assertEqual([(k, c) for _o, k, c in pairs], [(1, 3), (0, 2), (1, 2)])
        self.assertEqual(why, self.t["why_digits_unresolved"])
        s = rl.paired(pairs)
        self.assertEqual((s["n"], s["d"], s["dr"]), self.t["pairs_digits_unresolved"])
        self.assertEqual((s["pl_orig"], s["pl_corr"], s["d_sq"]), (F(1), F(1), F(2)))
        self.assertEqual((s["rank_orig"], s["rank_corr"], s["dr_sq"]), (F(5, 3), F(2), F(1)))
        self.assertEqual((s["ul_orig"], s["ul_corr"], s["us_orig"], s["us_corr"]), (1, 1, 0, 0))
        p0, why0 = rl.miskey_pairs(self.rows, digit_base=0)
        s0 = rl.paired(p0)
        self.assertEqual((s0["n"], s0["d"], s0["dr"]), self.t["pairs_digits_0_based"])
        self.assertEqual(why0, {})
        _p1, why1 = rl.miskey_pairs(self.rows, digit_base=1)
        self.assertEqual(why1, self.t["why_digits_1_based"])
        px, whyx = rl.miskey_pairs(self.rows, exclude_subjects=("S2",))
        self.assertEqual([(k, c) for _o, k, c in px], [(1, 3)])
        self.assertEqual(whyx, {})

    def test_paired_report(self):
        r = rl.paired_report(rl.paired(rl.miskey_pairs(self.rows)[0]))
        self.assertEqual(r["n"], 3)
        self.assertAlmostEqual(r["pick_longest_vs_published_key"], 1 / 3, places=12)
        self.assertAlmostEqual(r["pick_longest_vs_corrected_key"], 1 / 3, places=12)
        self.assertAlmostEqual(r["mean_diff"], 0.0, places=12)
        self.assertAlmostEqual(r["diff_se"], (1 / 3) ** 0.5, places=12)
        self.assertAlmostEqual(r["diff_z"], 0.0, places=12)
        self.assertAlmostEqual(r["rank_diff"], 1 / 9, places=12)
        self.assertAlmostEqual(r["rank_diff_se"], 13 ** 0.5 / 9, places=12)
        self.assertAlmostEqual(r["rank_diff_z"], 1 / 13 ** 0.5, places=12)

    def test_detectors(self):
        d = rl.detector(self.rows, rl.flag_key_unique_shortest, (rl.MISKEY,))
        self.assertEqual(d["pooled"]["table"], self.t["detector_key_shortest_vs_miskey"])
        self.assertEqual(d["strata"], {"S1": [0, 1, 1, 4], "S2": [0, 0, 3, 1]})
        self.assertAlmostEqual(d["pooled"]["chi_square_stat"], 160 / 216, places=12)
        self.assertAlmostEqual(d["by_subject_cmh"]["sum_observed_minus_expected"], -1 / 6, places=12)
        self.assertAlmostEqual(d["by_subject_cmh"]["cmh_stat"], 0.2, places=12)
        self.assertAlmostEqual(d["by_subject_cmh"]["mh_odds_ratio"], 0.0, places=12)
        self.assertEqual(d["by_subject_cmh"]["n_informative_strata"], 1)
        d2 = rl.detector(self.rows, rl.flag_other_unique_longest, (rl.MISKEY,))
        self.assertEqual(d2["pooled"]["table"], self.t["detector_other_longest_vs_miskey"])
        d3 = rl.detector(self.rows, rl.flag_other_unique_longest, rl.ERROR_TYPES)
        self.assertEqual(d3["pooled"]["table"], self.t["detector_other_longest_vs_any_error"])

    def test_correction_formats(self):
        self.assertEqual(rl.correction_formats(self.rows),
                         {"multiple_correct_answers": {"letters": 1}, "no_correct_answer": {"unmatched": 1},
                          "wrong_groundtruth": {"digits": 1, "letters": 2, "text": 1}})


if __name__ == "__main__":
    unittest.main()
