# Stdlib-only tests. They (1) assert the exact normalization properties behind
# each hazard group and (2) recompute every labeled case in cases.json from the
# faithfully-reproduced upstream logic and check it against the stored label.
import json
import os
import unittest

from math_equiv import (
    UPSTREAM_COMMITS,
    strip_string,
    is_equiv,
    lm_eval_exact_match,
    verl_compute_score,
)

HERE = os.path.dirname(os.path.abspath(__file__))


class NormalizationProperties(unittest.TestCase):
    def test_group_a_text_truncation_keeps_first_option(self):
        self.assertEqual(strip_string("2 \\text{ or } 3"), "2")
        self.assertEqual(strip_string("x = 2 \\text{ or } x = 3"), "2")
        self.assertTrue(is_equiv("2 \\text{ or } 3", "2"))
        self.assertFalse(is_equiv("2 \\text{ or } 3", "3"))
        # Three pieces trip the assert and fall back to raw equality.
        with self.assertRaises(AssertionError):
            strip_string("2 \\text{ or } 3 \\text{ or } 4")
        self.assertFalse(is_equiv("2 \\text{ or } 3 \\text{ or } 4", "2"))
        # No space after the brace: nothing is truncated.
        self.assertEqual(strip_string("2 \\text{or} 3"), "2\\text{or}3")

    def test_group_a_hedge_pays_rl_reward(self):
        hedge = "Therefore the answer is \\boxed{2 \\text{ or } 3}."
        self.assertEqual(verl_compute_score(hedge, "2"), 1.0)
        self.assertEqual(verl_compute_score(hedge, "3"), 0.0)

    def test_group_b_equals_strip_depends_on_spacing(self):
        self.assertEqual(strip_string("x = 5"), "5")
        self.assertEqual(strip_string(" x = 5"), "x=5")
        self.assertEqual(strip_string("xy = 5"), "xy=5")
        self.assertEqual(strip_string("xy=5"), "5")
        self.assertEqual(lm_eval_exact_match("The answer is $x = 5$.", "So $x = \\boxed{5}$."), 1)
        self.assertEqual(lm_eval_exact_match("The answer is $ x = 5$.", "So $x = \\boxed{5}$."), 0)

    def test_group_c_rescues_are_sign_asymmetric(self):
        self.assertEqual(strip_string("1/2"), "\\frac{1}{2}")
        self.assertEqual(strip_string("-1/2"), "\\frac{-1}{2}")
        self.assertEqual(strip_string("-\\frac{1}{2}"), "-\\frac{1}{2}")
        self.assertEqual(strip_string("0.5"), "\\frac{1}{2}")
        self.assertEqual(strip_string("-0.5"), "-0.5")

    def test_group_d_valueerror_escapes_only_in_lm_eval(self):
        s = "\\dfrac{3}{2}\\text{m/s}"
        with self.assertRaises(ValueError):
            strip_string(s)
        self.assertEqual(strip_string(s, catch_all=True), "\\frac{3}{2}\\text{m/s}")
        self.assertFalse(is_equiv(s, "\\frac{3}{2}\\text{m/s}"))
        self.assertTrue(is_equiv(s, "\\frac{3}{2}\\text{m/s}", catch_all=True))

    def test_group_e_left_right_substring_collision(self):
        self.assertEqual(strip_string("\\rightarrow"), "arrow")
        self.assertEqual(strip_string("\\leftarrow"), "arrow")
        self.assertTrue(is_equiv("\\rightarrow", "\\leftarrow"))


class LabeledCorpusMatchesComputed(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(HERE, "cases.json"), encoding="utf-8") as fh:
            self.corpus = json.load(fh)

    def test_commit_pins_match(self):
        self.assertEqual(self.corpus["upstream_commits"], UPSTREAM_COMMITS)

    def test_every_case_recomputes_to_its_label(self):
        for case in self.corpus["cases"]:
            cid = case["id"]
            if case["path"] == "is_equiv":
                got = is_equiv(case["prediction"], case["gold"])
                got_all = is_equiv(case["prediction"], case["gold"], catch_all=True)
                self.assertEqual(got, case["lm_eval"], "lm_eval " + cid)
                self.assertEqual(got_all, case["catch_all"], "catch_all " + cid)
            elif case["path"] == "lm_eval_response":
                got = lm_eval_exact_match(case["response"], case["solution"])
                self.assertEqual(got, case["score"], cid)
            elif case["path"] == "verl_reward":
                got = verl_compute_score(case["response"], case["solution"])
                self.assertEqual(got, case["score"], cid)
            else:
                self.fail("unknown path " + cid)

    def test_hazard_flag_is_consistent(self):
        # A hazard is any case where a scorer disagrees with the hand label
        # (false positive or false negative).
        for case in self.corpus["cases"]:
            want = case["semantically_correct"]
            if case["path"] == "is_equiv":
                disagree = (case["lm_eval"] != want) or (case["catch_all"] != want)
            else:
                disagree = bool(case["score"]) != want
            self.assertEqual(case["hazard"], disagree, case["id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
