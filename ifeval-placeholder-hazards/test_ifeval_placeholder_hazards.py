# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0.
#
# Standard-library tests: each pre-registered case reproduces its recorded upstream and
# intended outcomes, and every case is a genuine hazard (upstream != intended). Run with:
#   python -m unittest -v
import json
import os
import unittest

import ifeval_placeholder as ip

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "cases.json"), encoding="utf-8") as _f:
    CASES = json.load(_f)["cases"]


class TestIFEvalPlaceholderHazards(unittest.TestCase):
    def test_outcomes_match_prereg(self):
        for case in CASES:
            up, it = ip.run_case(case)
            self.assertEqual(
                up, case["expected_upstream"],
                "%s: upstream outcome %r != pre-registered %r" % (
                    case["id"], up, case["expected_upstream"]))
            self.assertEqual(
                it, case["expected_intended"],
                "%s: intended outcome %r != pre-registered %r" % (
                    case["id"], it, case["expected_intended"]))

    def test_every_case_is_a_hazard(self):
        for case in CASES:
            up, it = ip.run_case(case)
            self.assertNotEqual(
                up, it,
                "%s is not a hazard: upstream and intended both %r" % (case["id"], up))

    def test_false_pass_cases_have_zero_genuine_placeholders(self):
        # Every false_pass case must pass upstream but have an intended count strictly
        # below its requirement -- i.e. the bracket spans are all markdown noise.
        for case in CASES:
            if case["hazard"] != "false_pass":
                continue
            self.assertTrue(ip.upstream_placeholder(case["value"], case["num_placeholders"]))
            self.assertLess(
                ip.intended_placeholder_count(case["value"]), case["num_placeholders"],
                "%s: intended count should be below the requirement" % case["id"])

    def test_genuine_placeholders_pass_both(self):
        # Sanity / control (NOT in cases.json because it is not a hazard): a response with
        # real fill-in placeholders is accepted by BOTH the upstream and intended checkers.
        value = "Dear [name], your order [order_id] ships to [address] on [date]."
        self.assertTrue(ip.upstream_placeholder(value, 4))
        self.assertTrue(ip.intended_placeholder(value, 4))
        self.assertEqual(ip.intended_placeholder_count(value), 4)

    def test_noise_helpers(self):
        # The four excluded constructs are each recognised as markdown noise.
        self.assertTrue(ip._is_markdown_noise("[OpenAI]", "("))   # inline link
        self.assertTrue(ip._is_markdown_noise("[docs]", "["))     # reference link
        self.assertTrue(ip._is_markdown_noise("[id]", ":"))       # reference definition
        self.assertTrue(ip._is_markdown_noise("[^1]", " "))       # footnote
        self.assertTrue(ip._is_markdown_noise("[ ]", " "))        # checkbox
        self.assertTrue(ip._is_markdown_noise("[12]", " "))       # numeric citation
        self.assertFalse(ip._is_markdown_noise("[address]", " "))  # genuine placeholder


if __name__ == "__main__":
    unittest.main()
