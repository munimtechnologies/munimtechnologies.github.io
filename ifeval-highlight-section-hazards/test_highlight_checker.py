# Unit tests: every pre-registered case must reproduce its verdict and count,
# and the aggregate must match the pre-registered target. Pure stdlib
# (unittest); no network, no third-party packages, no dataset needed.

import unittest

from highlight_checker import (
    count_highlights, count_triple_spans, corrected_count, classify,
)
from cases import CASES, TARGET


def corpus_summary():
    n_match = n_correct_neg = n_false_pass = n_false_fail = 0
    all_ok = True
    for cid, value, req, intended, exp, note in CASES:
        verdict = classify(value, req, intended)
        if verdict != exp:
            all_ok = False
        if verdict == "match":
            n_match += 1
        elif verdict == "correct_neg":
            n_correct_neg += 1
        elif verdict == "false_pass":
            n_false_pass += 1
        else:
            n_false_fail += 1
    return {
        "n_cases": len(CASES),
        "n_match": n_match,
        "n_correct_neg": n_correct_neg,
        "n_false_pass": n_false_pass,
        "n_false_fail": n_false_fail,
        "n_flips": n_false_pass + n_false_fail,
        "all_reproduced": all_ok,
    }


class TestHighlightChecker(unittest.TestCase):
    def test_each_case_reproduces(self):
        for cid, value, req, intended, exp, note in CASES:
            self.assertEqual(classify(value, req, intended), exp, cid)

    def test_triple_overcount_is_two(self):
        # The headline hazard: one bold-italic span counts as 2.
        self.assertEqual(count_highlights("***only one***"), 2)
        self.assertEqual(count_triple_spans("***only one***"), 1)
        self.assertEqual(corrected_count("***only one***"), 1)

    def test_corpus_matches_target(self):
        self.assertEqual(corpus_summary(), TARGET)


if __name__ == "__main__":
    unittest.main()
