# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name. Every expectation below was hand-traced
# through HELM's pattern before any run.
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from icd_regex_check import (  # noqa: E402
    classify, edin_format, f1, full_f1, helm_extract, helm_f1, run,
)


class TestGoldFormat(unittest.TestCase):
    def test_diagnosis_gets_period_after_third_character(self):
        self.assertEqual(edin_format("I10", True), "I10.")
        self.assertEqual(edin_format("S72001A", True), "S72.001A")
        self.assertEqual(edin_format("E11.9", True), "E11.9")

    def test_procedure_keeps_no_period(self):
        self.assertEqual(edin_format("0DTJ4ZZ", False), "0DTJ4ZZ")


class TestHelmExtraction(unittest.TestCase):
    def test_intact(self):
        self.assertEqual(helm_extract("I10."), ["I10"])
        self.assertEqual(helm_extract("E11.9"), ["E11.9"])
        self.assertEqual(helm_extract("I50.23"), ["I50.23"])
        self.assertEqual(helm_extract("**E11.9**"), ["E11.9"])

    def test_letter_after_period_truncated_to_category(self):
        self.assertEqual(helm_extract("S72.001A"), ["S72"])
        self.assertEqual(helm_extract("T38.0X5A"), ["T38"])
        self.assertEqual(helm_extract("W19.XXXA"), ["W19"])
        self.assertEqual(helm_extract("S72.92XA"), ["S72"])

    def test_letter_in_third_place_dropped(self):
        self.assertEqual(helm_extract("Z3A.38"), [])
        self.assertEqual(helm_extract("C7A.00"), [])

    def test_pcs_never_matched(self):
        for code in ["0DTJ4ZZ", "5A1955Z", "BW03ZZZ", "XW033E5"]:
            self.assertEqual(helm_extract(code), [], code)

    def test_lower_case_not_matched(self):
        self.assertEqual(helm_extract("e11.9"), [])

    def test_joined_gold_string(self):
        self.assertEqual(helm_extract("0DTJ4ZZ,E11.9,S72.001A,Z3A.38,I10."), ["E11.9", "S72", "I10"])


class TestVerdicts(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify("I10", True)[0], "intact")
        self.assertEqual(classify("I5023", True)[0], "intact")
        self.assertEqual(classify("T380X5A", True)[0], "truncated")
        self.assertEqual(classify("C7A00", True)[0], "dropped")
        self.assertEqual(classify("XW033E5", False)[0], "dropped")

    def test_counts(self):
        self.assertEqual(run()["verdict_counts"], {"intact": 3, "truncated": 3, "dropped": 6})


class TestF1(unittest.TestCase):
    def test_f1_is_two_tp_over_sizes(self):
        self.assertAlmostEqual(f1(["a", "b", "c"], ["a", "b"]), 0.8)
        self.assertEqual(f1(["a"], ["b"]), 0.0)

    def test_procedure_never_scored(self):
        gold = [("0DTJ4ZZ", False), ("E119", True), ("I10", True)]
        self.assertAlmostEqual(helm_f1(gold, "E11.9, I10"), 1.0)
        self.assertAlmostEqual(full_f1(gold, ["E119", "I10"]), 0.8)

    def test_wrong_extension_credited(self):
        gold = [("S72001A", True)]
        self.assertAlmostEqual(helm_f1(gold, "S72.92XA"), 1.0)
        self.assertAlmostEqual(full_f1(gold, ["S7292XA"]), 0.0)

    def test_two_codes_collapse(self):
        gold = [("S72001A", True), ("S72002A", True)]
        self.assertAlmostEqual(helm_f1(gold, "S72.001A"), 1.0)
        self.assertAlmostEqual(full_f1(gold, ["S72001A"]), 2 / 3)

    def test_gestation_code_dropped(self):
        gold = [("Z3A38", True), ("O80", True)]
        self.assertAlmostEqual(helm_f1(gold, "O80"), 1.0)
        self.assertAlmostEqual(full_f1(gold, ["O80"]), 2 / 3)

    def test_examples_rounded(self):
        got = {e["example"]: (e["helm_f1"], e["full_code_f1"]) for e in run()["examples"]}
        self.assertEqual(got, {
            "procedure_never_scored": (1.0, 0.8),
            "wrong_extension_credited": (1.0, 0.0),
            "two_codes_collapse": (1.0, 0.6667),
            "gestation_code_dropped": (1.0, 0.6667),
        })


if __name__ == "__main__":
    unittest.main()
