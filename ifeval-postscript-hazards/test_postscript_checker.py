# Unit tests: each pre-registered case must reproduce both its shipped and its
# intended verdict, and the aggregate corpus must match the pre-registered
# target. Pure stdlib (unittest); no network, no third-party packages.

import unittest

from postscript_checker import shipped_check, intended_check
from cases import CASES, MARKER

TARGET = {
    "n_cases": 6,
    "n_verdict_flip": 4,
    "n_false_pass": 1,
    "n_false_fail": 3,
    "all_reproduced": True,
}


def corpus_summary():
    n_flip = n_fp = n_ff = 0
    all_ok = True
    for cid, text, ship_exp, int_exp, kind, note in CASES:
        ship = shipped_check(text, MARKER)
        intended = intended_check(text, MARKER)
        if ship != ship_exp or intended != int_exp:
            all_ok = False
        if ship != intended:
            n_flip += 1
        if ship and not intended:
            n_fp += 1
        if intended and not ship:
            n_ff += 1
    return {
        "n_cases": len(CASES),
        "n_verdict_flip": n_flip,
        "n_false_pass": n_fp,
        "n_false_fail": n_ff,
        "all_reproduced": all_ok,
    }


class TestPostscriptCases(unittest.TestCase):
    def test_each_case_reproduces(self):
        for cid, text, ship_exp, int_exp, kind, note in CASES:
            self.assertEqual(shipped_check(text, MARKER), ship_exp, cid)
            self.assertEqual(intended_check(text, MARKER), int_exp, cid)

    def test_corpus_matches_target(self):
        self.assertEqual(corpus_summary(), TARGET)


if __name__ == "__main__":
    unittest.main()
