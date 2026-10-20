# Tests for prevalence.py on hand-traced toy golds. Standard library only.
#
# Apache-2.0. Made with AI by MV2 of Munim, Inc.

import unittest

import prevalence as pv

TOY = [
    ("a", "\\frac{3}{4}"),
    ("b", "-\\frac{3}{4}"),
    ("c", "5 \\text{ cm}"),
    ("d", "2 \\text{ or } 3"),
    ("e", "1 \\text{ or } 2 \\text{ or } 3"),
    ("f", "x/2"),
    ("g", "y = 2x"),
]


class Helpers(unittest.TestCase):
    def test_extract_gold(self):
        self.assertEqual(pv.extract_gold("so $\\boxed{\\frac{1}{2}}$."), "\\frac{1}{2}")
        self.assertIsNone(pv.extract_gold("no box here"))

    def test_strip_error(self):
        self.assertIsNone(pv.strip_error("\\frac{1}{2}", False))
        self.assertEqual(pv.strip_error("1 \\text{ or } 2 \\text{ or } 3", False), "AssertionError")
        self.assertEqual(pv.strip_error("1 \\text{ or } 2 \\text{ or } 3", True), "AssertionError")
        self.assertEqual(pv.strip_error("x/2", False), "ValueError")
        self.assertIsNone(pv.strip_error("x/2", True))

    def test_text_units(self):
        self.assertEqual(pv.text_units("5 \\text{ cm}"), (1, "cm}"))
        self.assertEqual(pv.text_units("2 \\text{ or } 3"), (1, "or } 3"))
        self.assertEqual(pv.text_units("\\text{Evelyn}"), (0, None))
        self.assertEqual(pv.text_units("1 \\text{ or } 2 \\text{ or } 3")[0], 2)
        self.assertFalse(pv.CONNECTIVE.search("floors}"))

    def test_slash_rewrite(self):
        self.assertEqual(pv.slash_rewrite("-\\frac{3}{4}"), ("-3/4", True))
        self.assertEqual(pv.slash_rewrite("\\dfrac{3}{4}"), ("3/4", False))
        self.assertEqual(pv.slash_rewrite("\\frac{x}{4}"), (None, None))


class Measure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = pv.measure(TOY)

    def test_m0_control(self):
        self.assertEqual(self.r["M0"], {"L": 7, "C": 7})

    def test_m1_normalization_disabled(self):
        self.assertEqual(self.r["M1"]["L"]["count"], 2)
        self.assertEqual(self.r["M1"]["L"]["by_type"], {"AssertionError": 1, "ValueError": 1})
        self.assertEqual(self.r["M1"]["C"]["count"], 1)
        self.assertEqual(self.r["M1_L_only"], [{"id": "f", "gold": "x/2"}])

    def test_m2_units(self):
        m2 = self.r["M2"]
        self.assertEqual((m2["count"], m2["M2a"], m2["M2b"], m2["M2c"]), (3, 2, 1, 1))
        self.assertEqual([i["id"] for i in m2["items"] if i["connective"]], ["d"])

    def test_m3_leading_space(self):
        self.assertEqual(self.r["M3"]["L"]["ids"], ["e", "f", "g"])
        self.assertEqual(self.r["M3"]["C"]["ids"], ["e", "g"])

    def test_m4_trailing_space(self):
        self.assertEqual(self.r["M4"]["L"]["ids"], ["e", "f"])
        self.assertEqual(self.r["M4"]["C"]["ids"], ["e"])

    def test_m5_dfrac(self):
        self.assertEqual(self.r["M5"], {"exposed": 2, "L": 0, "C": 0})

    def test_m6_sign_asymmetry(self):
        m6 = self.r["M6"]
        self.assertEqual(m6["pos"], {"n": 1, "L": 1, "C": 1})
        self.assertEqual(m6["neg"], {"n": 1, "L": 0, "C": 0})
        self.assertEqual(m6["neg_ids"], ["b"])

    def test_grade(self):
        g = pv.grade(self.r)
        self.assertTrue(g["P2"]["hit"])
        self.assertFalse(g["P4"]["hit"])  # fewer than 50 negative fractions in the toy set
        self.assertTrue(g["P6"]["hit"])


if __name__ == "__main__":
    unittest.main()
