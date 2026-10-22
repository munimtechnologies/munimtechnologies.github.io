import unittest

import cases
from gsm8k_socratic_steps import census, public_summary, reasoning_lines, strip_subquestion


class TestLineHelpers(unittest.TestCase):
    def test_reasoning_lines_drop_final_and_blanks(self):
        self.assertEqual(reasoning_lines("a\n\n b \n#### 3"), ["a", "b"])

    def test_reasoning_lines_without_marker(self):
        self.assertEqual(reasoning_lines("a\nb"), ["a", "b"])

    def test_strip_subquestion_with_separator(self):
        self.assertEqual(strip_subquestion("How many? ** She has 3."), ("She has 3.", True))

    def test_strip_subquestion_splits_on_first_separator_only(self):
        self.assertEqual(strip_subquestion("Q? ** x ** y"), ("x ** y", True))

    def test_strip_subquestion_without_separator(self):
        self.assertEqual(strip_subquestion("She has 3."), ("She has 3.", False))


class TestCensusAgainstTarget(unittest.TestCase):
    def setUp(self):
        self.result = census(cases.MAIN_ROWS, cases.SOCRATIC_ROWS,
                             cases.QUESTION_KEY, cases.ANSWER_KEY)

    def test_matches_pre_registered_target(self):
        self.assertEqual(public_summary(self.result), cases.TARGET)

    def test_annotation_example_is_b(self):
        ex = self.result["annotation_diff_examples"]
        self.assertEqual([e["question"] for e in ex], ["B?"])
        self.assertEqual(ex[0]["main_annotations"], ["<<4*3=12>>"])
        self.assertEqual(ex[0]["socratic_annotations"], ["<<4*3=13>>"])

    def test_step_examples_are_b_and_c(self):
        self.assertEqual([e["question"] for e in self.result["step_diff_examples"]],
                         ["B?", "C?"])


if __name__ == "__main__":
    unittest.main()
