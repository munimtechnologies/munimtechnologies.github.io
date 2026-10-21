# stdlib unittest for the ifeval-bullet-list-hazards audit. Each case must
# reproduce its exact bullet count and verdict, and the aggregate must match the
# pre-registered TARGET. Apache-2.0.

import unittest

from bullet_checker import count_bullets, corrected_count, classify
from cases import CASES, TARGET

_KEY = {
    "match": "n_match",
    "correct_neg": "n_correct_neg",
    "false_pass": "n_false_pass",
    "false_fail": "n_false_fail",
}


class TestBulletChecker(unittest.TestCase):
    def test_counts_and_verdicts(self):
        for cid, value, num_req, true_count, exp_count, exp_verdict, _note in CASES:
            self.assertEqual(count_bullets(value), exp_count, "count " + cid)
            self.assertEqual(classify(value, num_req, true_count), exp_verdict,
                             "verdict " + cid)

    def test_corrected_never_exceeds_upstream(self):
        for cid, value, *_rest in CASES:
            self.assertLessEqual(corrected_count(value), count_bullets(value), cid)

    def test_aggregate_matches_target(self):
        agg = {"n_cases": 0, "n_match": 0, "n_correct_neg": 0,
               "n_false_pass": 0, "n_false_fail": 0, "n_flips": 0,
               "all_reproduced": True}
        for cid, value, num_req, true_count, _exp_count, _exp_verdict, _note in CASES:
            verdict = classify(value, num_req, true_count)
            agg["n_cases"] += 1
            agg[_KEY[verdict]] += 1
        agg["n_flips"] = agg["n_false_pass"] + agg["n_false_fail"]
        self.assertEqual(agg, TARGET)


if __name__ == "__main__":
    unittest.main()
