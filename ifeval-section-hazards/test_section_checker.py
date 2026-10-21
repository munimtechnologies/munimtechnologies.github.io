# stdlib unittest for the ifeval-section-hazards audit. Each case must reproduce
# its exact section count and verdict, the corrected count must recover each
# case's true section count, and the aggregate must match the pre-registered
# TARGET. Apache-2.0.

import unittest

from section_checker import count_sections, corrected_count, classify
from cases import CASES, TARGET

_KEY = {
    "match": "n_match",
    "correct_neg": "n_correct_neg",
    "false_pass": "n_false_pass",
    "false_fail": "n_false_fail",
}


class TestSectionChecker(unittest.TestCase):
    def test_counts_and_verdicts(self):
        for (cid, value, spliter, num_req, true_count, exp_num,
             exp_verdict, _note) in CASES:
            self.assertEqual(count_sections(value, spliter), exp_num,
                             "count " + cid)
            self.assertEqual(classify(value, spliter, num_req, true_count),
                             exp_verdict, "verdict " + cid)

    def test_corrected_recovers_true_count(self):
        for (cid, value, spliter, _num_req, true_count, *_rest) in CASES:
            self.assertEqual(corrected_count(value, spliter), true_count,
                             "corrected " + cid)

    def test_aggregate_matches_target(self):
        agg = {"n_cases": 0, "n_match": 0, "n_correct_neg": 0,
               "n_false_pass": 0, "n_false_fail": 0, "n_flips": 0,
               "all_reproduced": True}
        for (cid, value, spliter, num_req, true_count, _exp_num,
             _exp_verdict, _note) in CASES:
            verdict = classify(value, spliter, num_req, true_count)
            agg["n_cases"] += 1
            agg[_KEY[verdict]] += 1
        agg["n_flips"] = agg["n_false_pass"] + agg["n_false_fail"]
        self.assertEqual(agg, TARGET)


if __name__ == "__main__":
    unittest.main()
