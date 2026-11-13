# SPDX-License-Identifier: Apache-2.0
# Unit tests for audit 117 (MV2 of Munim, Inc.; made with AI agents). Standard library only.
import unittest

from convfinqa_check import (
    MAX_TOKENS,
    _strip_string,
    digit_split_min_tokens,
    digit_split_truncate,
    float_equiv,
    natural_form,
    reachable_digit_split,
    shortest_form,
)


class TranscribedScorer(unittest.TestCase):
    def test_exact_gold(self):
        self.assertEqual(float_equiv("0.14136", "0.14136"), 1.0)

    def test_within_tolerance(self):
        self.assertEqual(float_equiv("0.1413605", "0.14136"), 1.0)

    def test_truncated_fraction_scores_zero(self):
        self.assertEqual(float_equiv("0.141", "0.14136"), 0.0)

    def test_percent_not_converted(self):
        self.assertEqual(float_equiv("14.136%", "0.14136"), 0.0)

    def test_thousands_separator(self):
        self.assertEqual(_strip_string("1,234"), 1.0)
        self.assertEqual(float_equiv("1,234", "1234.0"), 0.0)

    def test_first_number_is_read(self):
        self.assertEqual(_strip_string("In 2009 it was 0.5"), 2009.0)
        self.assertEqual(float_equiv("In 2009 it was 0.5", "0.5"), 0.0)

    def test_leading_zero_dropped(self):
        self.assertEqual(float_equiv("-.5", "-0.5"), 1.0)

    def test_sign_in_words(self):
        self.assertEqual(float_equiv("decline of 5", "-5"), 0.0)

    def test_yes_gold_never_credited(self):
        self.assertEqual(float_equiv("yes", "yes"), 0.0)
        self.assertEqual(float_equiv("no", "no"), 0.0)


class Forms(unittest.TestCase):
    def test_natural_form(self):
        self.assertEqual(natural_form("206588.0"), "206588")
        self.assertEqual(natural_form("-3.0"), "-3")
        self.assertEqual(natural_form("0.14136"), "0.14136")
        self.assertEqual(natural_form("yes"), "yes")

    def test_shortest_form(self):
        self.assertEqual(shortest_form("0.14136"), ".14136")
        self.assertEqual(shortest_form("206588.0"), "206588")
        self.assertEqual(shortest_form("-0.5"), "-.5")
        self.assertEqual(shortest_form("0.0"), "0")
        self.assertEqual(shortest_form("14.1"), "14.1")
        self.assertEqual(shortest_form("-0.0368"), "-.0368")
        self.assertIsNone(shortest_form("yes"))

    def test_shortest_form_is_credited(self):
        for gold in ["0.14136", "206588.0", "-0.5", "0.0", "14.1", "-0.0368", "1234.5"]:
            self.assertEqual(float_equiv(shortest_form(gold), gold), 1.0, gold)


class DigitSplitBudget(unittest.TestCase):
    def test_budget_is_five(self):
        self.assertEqual(MAX_TOKENS, 5)

    def test_min_tokens(self):
        self.assertEqual(digit_split_min_tokens(".14136"), 6)
        self.assertEqual(digit_split_min_tokens("0.14136"), 7)
        self.assertEqual(digit_split_min_tokens("-0.0368"), 7)
        self.assertEqual(digit_split_min_tokens("-.0368"), 5)
        self.assertEqual(digit_split_min_tokens("206588"), 6)
        self.assertEqual(digit_split_min_tokens("14.1"), 4)
        self.assertEqual(digit_split_min_tokens("-.5"), 2)

    def test_truncate(self):
        self.assertEqual(digit_split_truncate("0.14136"), "0.141")
        self.assertEqual(digit_split_truncate("14.1"), "14.1")
        self.assertEqual(digit_split_truncate("206588"), "20658")
        self.assertEqual(float_equiv(digit_split_truncate("0.14136"), "0.14136"), 0.0)
        self.assertEqual(float_equiv(digit_split_truncate("14.1"), "14.1"), 1.0)

    def test_reachable(self):
        self.assertFalse(reachable_digit_split("0.14136"))
        self.assertTrue(reachable_digit_split("14.1"))
        self.assertFalse(reachable_digit_split("1234.5"))
        self.assertTrue(reachable_digit_split("12345.0"))
        self.assertFalse(reachable_digit_split("206588.0"))
        self.assertTrue(reachable_digit_split("-0.0368"))
        self.assertFalse(reachable_digit_split("yes"))


if __name__ == "__main__":
    unittest.main()
