#!/usr/bin/env python3
"""Stdlib unit tests for the GSM8K annotation audit. Run before the audit.

By AI agents working in MV2's name, Munim, Inc. Apache-2.0.
"""
import unittest
from fractions import Fraction

import audit


class TestEvalExpr(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(audit.eval_expr("48/2"), Fraction(24))
        self.assertEqual(audit.eval_expr("3+4*2"), Fraction(11))      # precedence
        self.assertEqual(audit.eval_expr("(3+4)*2"), Fraction(14))
        self.assertEqual(audit.eval_expr("10-3-2"), Fraction(5))      # left assoc

    def test_exact_fractions(self):
        self.assertEqual(audit.eval_expr("1/3"), Fraction(1, 3))
        self.assertEqual(audit.eval_expr("10/4"), Fraction(5, 2))
        self.assertEqual(audit.eval_expr("0.1+0.2"), Fraction(3, 10))  # exact, not 0.3000..4

    def test_commas_and_dollar(self):
        self.assertEqual(audit.eval_expr("1,000+2,500"), Fraction(3500))
        self.assertEqual(audit.eval_expr("$5*3"), Fraction(15))

    def test_caret_power(self):
        self.assertEqual(audit.eval_expr("2^10"), Fraction(1024))
        self.assertEqual(audit.eval_expr("3^2+1"), Fraction(10))

    def test_unicode_operators(self):
        self.assertEqual(audit.eval_expr("6×7"), Fraction(42))    # times
        self.assertEqual(audit.eval_expr("8÷2"), Fraction(4))     # divide
        self.assertEqual(audit.eval_expr("5−2"), Fraction(3))     # minus

    def test_unary(self):
        self.assertEqual(audit.eval_expr("-5+8"), Fraction(3))
        self.assertEqual(audit.eval_expr("3*-2"), Fraction(-6))

    def test_rejects_names_and_calls(self):
        for bad in ("x+1", "min(1,2)", "2**x", "", "   ", "1/0", "2^1000", "[1]",
                    "import os", "48=24"):
            with self.assertRaises(audit.ExprError):
                audit.eval_expr(bad)


class TestParseNumber(unittest.TestCase):
    def test_integer(self):
        self.assertEqual(audit.parse_number("24"), (Fraction(24), 0))

    def test_decimals(self):
        self.assertEqual(audit.parse_number("24.0"), (Fraction(24), 1))
        self.assertEqual(audit.parse_number("33.33"), (Fraction(3333, 100), 2))

    def test_commas_and_symbols(self):
        self.assertEqual(audit.parse_number("1,200"), (Fraction(1200), 0))
        self.assertEqual(audit.parse_number("$50"), (Fraction(50), 0))
        self.assertEqual(audit.parse_number("20%"), (Fraction(20), 0))

    def test_rejects_non_numeric(self):
        for bad in ("", "abc", "1/2", "two"):
            with self.assertRaises(audit.ExprError):
                audit.parse_number(bad)


class TestRoundings(unittest.TestCase):
    def test_half_modes(self):
        r = audit._roundings(Fraction(5, 2))      # 2.5
        self.assertEqual(r["half_up"], 3)
        self.assertEqual(r["half_even"], 2)
        self.assertEqual(r["trunc"], 2)

    def test_half_even_up(self):
        r = audit._roundings(Fraction(7, 2))      # 3.5
        self.assertEqual(r["half_up"], 4)
        self.assertEqual(r["half_even"], 4)

    def test_below_and_above_half(self):
        self.assertEqual(audit._roundings(Fraction(10, 3))["half_up"], 3)   # 3.33
        self.assertEqual(audit._roundings(Fraction(11, 3))["half_up"], 4)   # 3.67

    def test_negative_trunc(self):
        self.assertEqual(audit._roundings(Fraction(-5, 2))["trunc"], -2)    # toward zero


class TestClassify(unittest.TestCase):
    def test_exact(self):
        cls, _, _ = audit.classify("48/2", "24")
        self.assertEqual(cls, "exact")

    def test_exact_decimal(self):
        cls, _, _ = audit.classify("1/2", "0.5")
        self.assertEqual(cls, "exact")

    def test_rounding(self):
        cls, _, _ = audit.classify("10/3", "3.33")
        self.assertEqual(cls, "rounding")
        cls2, _, _ = audit.classify("100/3", "33")
        self.assertEqual(cls2, "rounding")

    def test_mismatch(self):
        cls, _, _ = audit.classify("48/2", "25")
        self.assertEqual(cls, "mismatch")

    def test_unparseable_expr(self):
        cls, _, _ = audit.classify("x+1", "2")
        self.assertEqual(cls, "unparseable_expr")

    def test_unparseable_result(self):
        cls, _, _ = audit.classify("1+1", "two")
        self.assertEqual(cls, "unparseable_result")


class TestAnnotationAndChain(unittest.TestCase):
    def test_split_annotation(self):
        self.assertEqual(audit.split_annotation("48/2=24"), ("48/2", "24"))
        self.assertIsNone(audit.split_annotation("48/2"))
        # split on the LAST '='
        self.assertEqual(audit.split_annotation("a=b=3"), ("a=b", "3"))

    def test_final_answer(self):
        self.assertEqual(audit.final_answer("blah\n#### 72"), Fraction(72))
        self.assertEqual(audit.final_answer("x <<1+1=2>>\n#### 1,000"), Fraction(1000))
        self.assertIsNone(audit.final_answer("no final here"))

    def test_audit_split_roundtrip(self):
        rows = [
            {"answer": "Natalia sold 48/2 = <<48/2=24>> clips.\n#### 24"},
            {"answer": "She has <<10-3=7>> left and <<7*2=14>> total.\n#### 14"},
            {"answer": "Bad math: <<2+2=5>> oops.\n#### 5"},   # mismatch annotation
        ]
        s, bad, breaks = audit.audit_split("test", rows)
        self.assertEqual(s["n_problems"], 3)
        self.assertEqual(s["n_annotations"], 4)
        self.assertEqual(s["classes"]["exact"], 3)
        self.assertEqual(s["classes"]["mismatch"], 1)
        # all three chains: last annotation result equals the #### value
        self.assertEqual(s["last_matches_count"], 3)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["class"], "mismatch")

    def test_chain_break_detected(self):
        rows = [{"answer": "<<2+2=4>> but then\n#### 99"}]  # last result 4 != 99
        s, bad, breaks = audit.audit_split("test", rows)
        self.assertEqual(s["last_matches_count"], 0)
        self.assertEqual(len(breaks), 1)
        self.assertFalse(breaks[0]["last_matches"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
