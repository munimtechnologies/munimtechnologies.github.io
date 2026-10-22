# test_split_overlap.py -- stdlib unittest; run in the sealed compete lane.
import unittest

from split_overlap import analyze, public_summary, normalize, final_answer
from cases import TRAIN, TEST, TARGET


class TestSplitOverlap(unittest.TestCase):
    def test_fixture_matches_target(self):
        public = public_summary(analyze(TRAIN, TEST))
        self.assertEqual(public, TARGET)

    def test_normalize(self):
        self.assertEqual(normalize("A  B\nC"), "a b c")
        self.assertEqual(normalize("  Hello   World  "), "hello world")

    def test_final_answer(self):
        self.assertEqual(final_answer("x = 1,200\n#### 1,200"), "1200")
        self.assertEqual(final_answer("steps\n#### $42"), "42")
        self.assertIsNone(final_answer("no marker here"))

    def test_exact_is_subset_of_norm(self):
        result = analyze(TRAIN, TEST)
        self.assertLessEqual(result["exact_overlap_pairs"], result["norm_overlap_pairs"])
        self.assertLessEqual(
            result["exact_overlap_answer_conflicts"],
            result["norm_overlap_answer_conflicts"],
        )

    def test_normalized_only_overlap_includes_count(self):
        result = analyze(TRAIN, TEST)
        norm_only = result["norm_overlap_pairs"] - result["exact_overlap_pairs"]
        self.assertEqual(norm_only, 1)


if __name__ == "__main__":
    unittest.main()
