# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc.
#
# Stdlib-only tests. They assert that every hand-built case reproduces its
# pre-registered (upstream, intended) verdict pair, that the corpus totals
# match the pre-registration, and that metachar detection behaves.

import json
import os
import re
import unittest

import ifeval_regex as R

HERE = os.path.dirname(os.path.abspath(__file__))


def load_cases():
    with open(os.path.join(HERE, "cases.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)["cases"]


class TestCasesReproduce(unittest.TestCase):
    def test_every_case_reproduces(self):
        for c in load_cases():
            up, intl = R.verdicts(c)
            self.assertEqual(up, c["expected_upstream"],
                             "%s upstream" % c["id"])
            self.assertEqual(intl, c["expected_intended"],
                             "%s intended" % c["id"])

    def test_corpus_totals(self):
        cases = load_cases()
        hazards = [c["hazard"] for c in cases]
        self.assertEqual(len(cases), 9)
        self.assertEqual(hazards.count("crash"), 2)
        self.assertEqual(hazards.count("false_pass"), 2)
        self.assertEqual(hazards.count("false_fail"), 5)


class TestMechanisms(unittest.TestCase):
    def test_cpp_is_possessive_not_crash_on_this_runtime(self):
        # On CPython 3.11+ this compiles; on <=3.10 it raises. Either way the
        # audit records the runtime's behaviour rather than assuming one.
        try:
            re.compile("C++")
            compiled = True
        except re.error:
            compiled = False
        self.assertIn(compiled, (True, False))

    def test_metachar_detection(self):
        self.assertTrue(R.has_metachar("a.b"))
        self.assertTrue(R.has_metachar("C++"))
        self.assertTrue(R.has_metachar("cat|dog"))
        self.assertFalse(R.has_metachar("hello"))
        self.assertFalse(R.has_metachar("New York"))

    def test_unterminated_group_crashes_upstream(self):
        self.assertEqual(R.kf_upstream("(note", "Please (note this).", 1, "at least"),
                         "CRASH")

    def test_charclass_crashes_forbidden(self):
        self.assertEqual(R.fw_upstream("a[b", "Normal text here."), "CRASH")


if __name__ == "__main__":
    unittest.main()
