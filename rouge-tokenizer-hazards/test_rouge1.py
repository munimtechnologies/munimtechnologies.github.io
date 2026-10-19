"""Stdlib unit tests for the ROUGE residual-ASCII hazard.

Every expected value below is hand-traceable from the documented tokenizer:
lowercase -> replace runs of [^a-z0-9] with a space -> split on whitespace ->
keep tokens matching ^[a-z0-9]+$. Non-Latin strings are written with explicit
\\uXXXX escapes so the test is encoding-proof.

Run:  python -m unittest -v test_rouge1.py
"""
import unittest

from rouge1 import tokenize, rouge1

# "2024 nian qihou gaishan"  == 2024, climate, improves
GOLD_IMPROVE = "2024年气候改善"   # 2024 climate improves
# "2024 nian qihou ehua"     == 2024, climate, WORSENS (opposite meaning)
WORSEN = "2024年气候恶化"          # 2024 climate worsens
# "qihou gaishan"            == climate improves (correct meaning, no year)
IMPROVE_NO_YEAR = "气候改善"
# "2024 nian zhanzheng jieshu" == 2024, war, ends (wrong meaning, has 2024)
WAR_ENDS = "2024年战争结束"


class TestTokenizer(unittest.TestCase):
    def test_non_latin_collapses_to_residual_ascii(self):
        # Every CJK char is non [a-z0-9] -> replaced by space. Only "2024" survives.
        self.assertEqual(tokenize(GOLD_IMPROVE), ["2024"])
        self.assertEqual(tokenize(WORSEN), ["2024"])
        self.assertEqual(tokenize(WAR_ENDS), ["2024"])

    def test_pure_non_latin_becomes_empty(self):
        # No ASCII alphanumerics at all -> empty token list (the known zero case).
        self.assertEqual(tokenize(IMPROVE_NO_YEAR), [])

    def test_comma_splits_a_number(self):
        # ASCII-only, any language: a thousands separator changes the tokens.
        self.assertEqual(tokenize("2,024"), ["2", "024"])
        self.assertEqual(tokenize("2024"), ["2024"])


class TestRouge1Hazards(unittest.TestCase):
    def test_opposite_meaning_scores_perfect(self):
        # Two sentences with OPPOSITE meaning both reduce to ["2024"] -> F = 1.0.
        s = rouge1(GOLD_IMPROVE, WORSEN)
        self.assertEqual(s["fmeasure"], 1.0)
        self.assertEqual(s["ref_tokens"], ["2024"])
        self.assertEqual(s["pred_tokens"], ["2024"])

    def test_ranking_inversion(self):
        # Correct answer (no year) scores 0; wrong answer (shares 2024) scores 1.
        correct = rouge1(GOLD_IMPROVE, IMPROVE_NO_YEAR)
        wrong = rouge1(GOLD_IMPROVE, WAR_ENDS)
        self.assertEqual(correct["fmeasure"], 0.0)
        self.assertEqual(wrong["fmeasure"], 1.0)
        self.assertGreater(wrong["fmeasure"], correct["fmeasure"])

    def test_empty_prediction_scores_zero_not_error(self):
        s = rouge1(GOLD_IMPROVE, IMPROVE_NO_YEAR)
        self.assertEqual(s["precision"], 0.0)
        self.assertEqual(s["recall"], 0.0)
        self.assertEqual(s["fmeasure"], 0.0)

    def test_comma_number_is_a_false_negative(self):
        # Same number, one with a thousands separator -> no overlap -> F = 0.
        s = rouge1("2024", "2,024")
        self.assertEqual(s["fmeasure"], 0.0)


if __name__ == "__main__":
    unittest.main()
