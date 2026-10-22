import unittest

import cases
from gsm8k_socratic_consistency import final_answer, census, public_summary


class TestFinalAnswer(unittest.TestCase):
    def test_basic_tail(self):
        self.assertEqual(final_answer("steps...\n#### 24"), "24")

    def test_strips_commas_and_dollar(self):
        self.assertEqual(final_answer("#### 1,000"), "1000")
        self.assertEqual(final_answer("#### $5"), "5")

    def test_last_marker_wins(self):
        self.assertEqual(final_answer("#### 3 then #### 9"), "9")

    def test_no_marker_is_none(self):
        self.assertIsNone(final_answer("no marker here"))
        self.assertIsNone(final_answer(None))


class TestCensusAgainstTarget(unittest.TestCase):
    def test_matches_pre_registered_target(self):
        result = census(cases.MAIN_ROWS, cases.SOCRATIC_ROWS,
                        cases.QUESTION_KEY, cases.ANSWER_KEY)
        self.assertEqual(public_summary(result), cases.TARGET)

    def test_disagree_example_recorded(self):
        result = census(cases.MAIN_ROWS, cases.SOCRATIC_ROWS,
                        cases.QUESTION_KEY, cases.ANSWER_KEY)
        self.assertEqual(result["final_answer_disagree"], 1)
        ex = result["disagree_examples"][0]
        self.assertEqual(ex["main_final"], "5")
        self.assertEqual(ex["socratic_final"], "7")

    def test_comma_pair_agrees(self):
        # Julie's "1,000" vs "1000" must count as agreement, not disagreement.
        result = census(cases.MAIN_ROWS, cases.SOCRATIC_ROWS)
        finals = [e["question"] for e in result["disagree_examples"]]
        self.assertNotIn("Julie reads a book. How many pages tomorrow?", finals)


if __name__ == "__main__":
    unittest.main()
