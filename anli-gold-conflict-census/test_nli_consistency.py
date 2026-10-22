# test_nli_consistency.py -- stdlib unittest; run in the sealed compete lane.
import unittest

from nli_consistency import analyze, public_summary, normalize
from cases import ROWS, PREMISE_KEY, HYPOTHESIS_KEY, LABEL_KEY, TARGET
from job import detect_premise_key


def _run():
    return analyze(ROWS, PREMISE_KEY, HYPOTHESIS_KEY, LABEL_KEY)


class TestNliConsistency(unittest.TestCase):
    def test_fixture_matches_target(self):
        self.assertEqual(public_summary(_run()), TARGET)

    def test_normalize(self):
        self.assertEqual(normalize("Birds  fly  south."), "birds fly south.")
        self.assertEqual(normalize("  A\tB\nC "), "a b c")

    def test_exact_is_subset_of_norm(self):
        r = _run()
        self.assertLessEqual(r["exact_conflict_pairs"], r["norm_conflict_pairs"])
        self.assertLessEqual(r["distinct_norm_pairs"], r["distinct_exact_pairs"])

    def test_skip_label_is_ignored(self):
        rows = ROWS + [{"premise": "x", "hypothesis": "y", "label": "-"}]
        r = analyze(rows, PREMISE_KEY, HYPOTHESIS_KEY, LABEL_KEY)
        self.assertEqual(r["rows_valid"], TARGET["rows_valid"])

    def test_normalized_only_conflict_count(self):
        r = _run()
        norm_only = r["norm_conflict_pairs"] - r["exact_conflict_pairs"]
        self.assertEqual(norm_only, 1)

    def test_detect_premise_key_prefers_context(self):
        # Raw ANLI v1.0 names the premise field "context".
        self.assertEqual(
            detect_premise_key([{"context": "a", "hypothesis": "b", "label": "e"}]),
            "context",
        )

    def test_detect_premise_key_falls_back_to_premise(self):
        self.assertEqual(
            detect_premise_key([{"premise": "a", "hypothesis": "b", "label": "e"}]),
            "premise",
        )

    def test_analyze_reads_context_keyed_rows(self):
        # The v1 bug: real rows keyed by "context" read as premise="premise" -> 0 valid.
        rows = [
            {"context": "A man is playing guitar.", "hypothesis": "A person makes music.", "label": "e"},
            {"context": "A man is playing guitar.", "hypothesis": "A person makes music.", "label": "n"},
        ]
        r = analyze(rows, "context", HYPOTHESIS_KEY, LABEL_KEY)
        self.assertEqual(r["rows_valid"], 2)
        self.assertEqual(r["exact_conflict_pairs"], 1)


if __name__ == "__main__":
    unittest.main()
