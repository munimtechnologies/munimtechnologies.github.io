# Unit tests: every pre-registered case must reproduce its verdict, and the
# aggregate must match the pre-registered target. Pure stdlib (unittest);
# no network, no third-party packages, no dataset needed.

import unittest

from mwp_eval import classify
from cases import CASES, TARGET


def corpus_summary():
    n_match = n_mismatch = n_uneval = 0
    all_ok = True
    for cid, notation, eq, nums, ans, exp, note in CASES:
        verdict, _ = classify(notation, eq, nums, ans)
        if verdict != exp:
            all_ok = False
        if verdict == "match":
            n_match += 1
        elif verdict == "mismatch":
            n_mismatch += 1
        else:
            n_uneval += 1
    return {
        "n_cases": len(CASES),
        "n_match": n_match,
        "n_mismatch": n_mismatch,
        "n_unevaluable": n_uneval,
        "all_reproduced": all_ok,
    }


class TestMwpEval(unittest.TestCase):
    def test_each_case_reproduces(self):
        for cid, notation, eq, nums, ans, exp, note in CASES:
            verdict, _ = classify(notation, eq, nums, ans)
            self.assertEqual(verdict, exp, cid)

    def test_corpus_matches_target(self):
        self.assertEqual(corpus_summary(), TARGET)


if __name__ == "__main__":
    unittest.main()
