# Unit tests: every pre-registered case must reproduce its verdict, and the
# aggregate must match the pre-registered target. Pure stdlib (unittest);
# no network, no third-party packages, no dataset needed.

import unittest

from title_checker import check_title, classify
from cases import CASES, TARGET


def corpus_summary():
    n_true = n_false_pass = n_false_fail = 0
    all_ok = True
    for cid, value, intended, exp, note in CASES:
        if check_title(value):
            n_true += 1
        verdict = classify(value, intended)
        if verdict != exp:
            all_ok = False
        if verdict == "false_pass":
            n_false_pass += 1
        elif verdict == "false_fail":
            n_false_fail += 1
    return {
        "n_cases": len(CASES),
        "n_checker_true": n_true,
        "n_flips": n_false_pass + n_false_fail,
        "n_false_pass": n_false_pass,
        "n_false_fail": n_false_fail,
        "all_reproduced": all_ok,
    }


class TestTitleChecker(unittest.TestCase):
    def test_each_case_reproduces(self):
        for cid, value, intended, exp, note in CASES:
            self.assertEqual(classify(value, intended), exp, cid)

    def test_corpus_matches_target(self):
        self.assertEqual(corpus_summary(), TARGET)


if __name__ == "__main__":
    unittest.main()
