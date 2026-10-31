"""Unit tests for audit 70 (stdlib only). Every expected value was traced by hand. Apache-2.0."""

import unittest
from fractions import Fraction as F

import cases
import gmmlu_length as gl

O4, R4, T4 = cases.O4, cases.R4, cases.T4


def rows(raw):
    return [gl.to_row(r) for r in raw]


class TestOneQuestion(unittest.TestCase):
    def test_credits(self):
        self.assertEqual(gl.credits(O4, 3), (F(1), F(0)))
        self.assertEqual(gl.credits(O4, 0), (F(0), F(1)))
        self.assertEqual(gl.credits(T4, 1), (F(1, 2), F(0)))
        self.assertEqual(gl.credits(T4, 2), (F(0), F(1, 2)))
        self.assertEqual(gl.credits(["  a  ", "bb"], 0), (F(0), F(1)))  # outer spaces are stripped

    def test_unique_longest(self):
        self.assertEqual(gl.unique_longest(O4), 3)
        self.assertEqual(gl.unique_longest(R4), 0)
        self.assertIsNone(gl.unique_longest(T4))

    def test_key_and_label(self):
        self.assertEqual(gl.key_index("A"), 0)
        self.assertEqual(gl.key_index(" d "), 3)
        self.assertIsNone(gl.key_index("E"))
        self.assertIsNone(gl.key_index(""))
        self.assertIsNone(gl.key_index(None))
        self.assertIsNone(gl.key_index("AB"))
        self.assertEqual(gl.normalise_label(" cs "), "CS")
        self.assertEqual(gl.normalise_label("CA"), "CA")
        self.assertEqual(gl.normalise_label("-"), "unlabelled")
        self.assertEqual(gl.normalise_label(None), "unlabelled")

    def test_to_row(self):
        r = gl.to_row(cases.FIXTURE_EN[2])
        self.assertEqual(r, {"sample_id": "s1/test/2", "subject": "s1", "category": "STEM", "options": T4,
                             "key": 1, "label": "CA"})

    def test_validity(self):
        self.assertTrue(gl.is_valid(O4, 0))
        self.assertFalse(gl.is_valid(["a", " "], 0))
        self.assertFalse(gl.is_valid(["a", None], 0))
        self.assertFalse(gl.is_valid(["a", "b"], 2))
        self.assertFalse(gl.is_valid(["a", "b"], None))
        self.assertFalse(gl.is_valid(["a", "b"], True))
        self.assertFalse(gl.is_valid(["a"], 0))


class TestEnglishFixture(unittest.TestCase):
    def setUp(self):
        self.en = rows(cases.FIXTURE_EN)
        self.c = gl.census(self.en)
        self.t = cases.FIXTURE_TARGET

    def test_census(self):
        self.assertEqual(self.c["n_rows"], self.t["en_n_rows"])
        self.assertEqual(self.c["n_invalid"], self.t["en_n_invalid"])
        self.assertEqual(self.c["labels"], self.t["en_labels"])
        for s in ("ALL", "label=CS", "label=CA", "label=unlabelled", "cat=STEM", "cat=Humanities",
                  "label=CA|cat=STEM"):
            self.assertEqual(gl.exact(self.c["accs"][s]), self.t["en_" + s], s)
        self.assertEqual(sorted(self.c["strata"]), ["s1", "s2"])
        self.assertEqual([a["n"] for a in self.c["strata"]["s1"]], [1, 2])
        self.assertEqual([a["n"] for a in self.c["strata"]["s2"]], [1, 1])

    def test_floor_report(self):
        r = gl.floor_report(self.c["accs"]["label=CA"])
        self.assertEqual(r["n"], 3)
        self.assertAlmostEqual(r["lift"], -1 / 12, places=12)
        self.assertAlmostEqual(r["se"], 1 / 6, places=12)
        self.assertAlmostEqual(r["z"], -0.5, places=12)
        r = gl.floor_report(self.c["accs"]["label=CS"])
        self.assertEqual(r["se"], 0.0)
        self.assertIsNone(r["z"])

    def test_diff(self):
        d = gl.diff_report(self.c["accs"]["label=CS"], self.c["accs"]["label=CA"])
        self.assertEqual(d["exact"], self.t["en_diff_exact"])
        self.assertEqual((d["n_1"], d["n_2"]), (2, 3))
        self.assertAlmostEqual(d["diff"], 5 / 6, places=12)
        self.assertAlmostEqual(d["se"], 1 / 6, places=12)
        self.assertAlmostEqual(d["z"], 5.0, places=12)
        empty = gl.diff_report(gl.new_acc(), self.c["accs"]["label=CA"])
        self.assertIsNone(empty["diff"])

    def test_stratified(self):
        s = gl.stratified_diff(self.c["strata"])
        self.assertEqual(s["exact"], self.t["en_stratified_exact"])
        self.assertEqual(s["n_strata_used"], self.t["en_stratified_n_used"])
        self.assertAlmostEqual(s["se"], 1 / (7 * 2 ** 0.5), places=12)
        self.assertAlmostEqual(s["z"], 6 * 2 ** 0.5, places=10)
        one_sided = {"s3": (self.c["strata"]["s1"][0], gl.new_acc())}
        self.assertEqual(gl.stratified_diff(one_sided)["n_strata_used"], 0)


class TestComparisons(unittest.TestCase):
    def setUp(self):
        self.en = rows(cases.FIXTURE_EN)
        self.xx = rows(cases.FIXTURE_XX)
        self.ref = gl.build_reference(self.en)
        self.t = cases.FIXTURE_TARGET

    def test_reference(self):
        self.assertEqual(self.ref["s1/test/0"], (3, 3, "CS"))
        self.assertEqual(self.ref["s1/test/2"], (1, None, "CA"))
        self.assertEqual(self.ref["s2/test/2"], (2, None, "unlabelled"))
        self.assertEqual(self.ref["s2/test/3"], (3, 0, "CA"))
        self.assertEqual(len(self.ref), 7)

    def test_compare_to_reference(self):
        self.assertEqual(gl.compare_to_reference(self.ref, self.xx), self.t["xx_compare"])

    def test_relabel_and_language_floor(self):
        rx = gl.relabel(self.xx, self.ref)
        self.assertEqual([r["label"] for r in rx], ["CS", "CA", "CA", "CS", "unlabelled"])
        self.assertEqual(self.xx[3]["label"], "CA")  # originals untouched
        c = gl.census(rx)
        self.assertEqual(gl.exact(c["accs"]["ALL"]), self.t["xx_ALL"])
        d = gl.diff_report(c["accs"]["label=CS"], c["accs"]["label=CA"])
        self.assertEqual(d["exact"], self.t["xx_diff_exact"])

    def test_mmlu_join(self):
        self.assertEqual(gl.compare_to_mmlu(self.en, cases.FIXTURE_MMLU), self.t["mmlu_join"])
        idx = gl.mmlu_index(cases.FIXTURE_MMLU)
        self.assertEqual(sorted(idx)[:3], ["s1/test/0", "s1/test/1", "s1/test/2"])
        self.assertIn("s3/test/0", idx)
        self.assertEqual(idx["s2/test/3"]["key"], 0)


if __name__ == "__main__":
    unittest.main()
