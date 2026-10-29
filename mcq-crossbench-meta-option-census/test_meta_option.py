"""Tests for the META-OPTION classifier and census (audit 57). Standard library unittest only.

Checks the hand-traced meta fixture for EXACT equality against META_TARGET, then the individual predicates,
the question-level priority rules and the report's rates against their chance baselines. The classifier and the
fixture are reused verbatim from audit 56; these tests lock them against transcription error.
"""

import unittest

import meta_option as mo
import cases


class TestMetaFixtureExact(unittest.TestCase):
    def test_run_meta_census_equals_target(self):
        got = mo.run_meta_census(cases.META_FIXTURE_ROWS)
        self.assertEqual(got, cases.META_TARGET)


class TestPredicates(unittest.TestCase):
    def test_aota(self):
        for t in ["All of the above", "all the above", "Both of these", "All of these", "both these",
                  "All of the above are correct"]:
            self.assertTrue(mo.is_aota(t), t)
        for t in ["None of the above", "Both A and B", "overall these", "red", cases.LONG]:
            self.assertFalse(mo.is_aota(t), t)

    def test_nota(self):
        for t in ["None of the above", "none of these", "Neither of those", "None of the above is correct"]:
            self.assertTrue(mo.is_nota(t), t)
        for t in ["All of the above", "None", "nonetheless these", "Neither A nor B"]:
            self.assertFalse(mo.is_nota(t), t)

    def test_letterref(self):
        for t in ["Both A and B", "A and C", "(a) and (b)", "A, B, and C", "Neither A nor B", "A and B are correct",
                  "B and D only"]:
            self.assertTrue(mo.is_letterref(t), t)
        for t in ["A", "Both", "a and b", "All of the above", "Vitamin A and B12"]:
            self.assertFalse(mo.is_letterref(t), t)

    def test_roman(self):
        for t in ["I only", "II only", "I and II", "I, II, and III", "II and III only", "Both I and II",
                  "Neither I nor II", "I, II and IV", "III"]:
            self.assertTrue(mo.is_roman(t), t)
        for t in ["Type II", "I think so", "VI", "i and ii", ""]:
            self.assertFalse(mo.is_roman(t), t)

    def test_roman_count(self):
        self.assertEqual(mo.roman_count("I only"), 1)
        self.assertEqual(mo.roman_count("I and II"), 2)
        self.assertEqual(mo.roman_count("I, II, and III"), 3)
        self.assertEqual(mo.roman_count("II, III and IV only"), 3)
        self.assertEqual(mo.roman_count("red"), 0)

    def test_most_inclusive_index(self):
        self.assertEqual(mo.most_inclusive_index(["I only", "II only", "I and II", "I, II, and III"]), 3)
        self.assertIsNone(mo.most_inclusive_index(["I and II", "II and III", "I only", "III only"]))  # tie at 2


class TestClassifyQuestion(unittest.TestCase):
    def test_priority_and_guards(self):
        self.assertEqual(mo.classify_question(["a", "b", "All of the above", "None of the above"]), "aota")
        self.assertEqual(mo.classify_question(["a", "b", "c", "None of the above"]), "nota")
        self.assertEqual(mo.classify_question(["a", "b", "Both A and B", "c"]), "letterref")
        self.assertEqual(mo.classify_question(["I only", "II only", "I and II", "All of the above"]), "roman")
        self.assertEqual(mo.classify_question(["I", "II", "III", "IV"]), "plain")          # quadrant, no combo
        self.assertEqual(mo.classify_question(["I and II", "x", "y", "z"]), "plain")       # only one roman option
        self.assertEqual(mo.classify_question([cases.LONG, "x", "y", "z"]), "plain")       # token guard
        self.assertEqual(mo.classify_question(["red", "blue", "green", "yellow"]), "plain")

    def test_meta_indices(self):
        self.assertEqual(mo.meta_indices(["Both of these", "x", "y", "All of the above"], "aota"), [0, 3])
        self.assertEqual(mo.meta_indices(["a", "b", "c", "d"], "plain"), [])
        self.assertEqual(mo.meta_indices(["I only", "II only", "I and II", "I, II, and III"], "roman"), [])


class TestMetaReport(unittest.TestCase):
    def setUp(self):
        self.rep = mo.meta_report(mo.run_meta_census(cases.META_FIXTURE_ROWS))

    def test_aota_rates(self):
        a = self.rep["aota"]
        self.assertEqual(a["n"], 3)
        self.assertEqual(a["n_with_meta_option"], 3)
        self.assertEqual(a["meta_first_pos_counts"], {"0": 2, "3": 1})
        self.assertAlmostEqual(a["meta_last_rate"], 2 / 3)
        self.assertAlmostEqual(a["meta_gold_rate"], 2 / 3)
        self.assertAlmostEqual(a["meta_gold_chance_rate"], 1 / 3)   # expected 1 over 3 questions

    def test_nota_chance_mixes_k(self):
        b = self.rep["nota"]
        self.assertAlmostEqual(b["meta_gold_chance_rate"], (7 / 12) / 2)

    def test_plain_and_roman(self):
        self.assertIsNone(self.rep["plain"]["meta_last_rate"])
        r = self.rep["roman"]
        self.assertEqual(r["n_inclusive_unique"], 1)
        self.assertAlmostEqual(r["gold_inclusive_rate"], 1.0)
        self.assertAlmostEqual(r["gold_inclusive_chance_rate"], 0.25)
        self.assertIsNone(r["meta_gold_rate"])


if __name__ == "__main__":
    unittest.main()
