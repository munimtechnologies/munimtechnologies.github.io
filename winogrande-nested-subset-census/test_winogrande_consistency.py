"""Tests for the WinoGrande nested-subset census (stdlib unittest, run in compete)."""
import unittest

import cases
from winogrande_consistency import (
    census, flatten, parse_row, normalize, within_file, nesting, overlap, public_summary,
)


def _parse(fixture):
    return [parse_row(obj) for obj in fixture]


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        result = census([("A", _parse(cases.FIXTURE_A)), ("B", _parse(cases.FIXTURE_B))])
        flat = flatten(result, cases.NAMES, cases.PAIRS)
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_normalize_collapses_whitespace_and_case(self):
        self.assertEqual(normalize("  The _   is BLUE "), "the _ is blue")
        self.assertEqual(normalize(None), "")

    def test_parse_reads_identity_and_answer(self):
        row = parse_row(cases.FIXTURE_A[0])
        self.assertEqual(row["qID"], "q1")
        self.assertEqual(row["answer"], "1")
        self.assertEqual(row["identity"], ("the _ is blue", "sky", "sea"))
        self.assertFalse(row["qid_missing"])

    def test_within_file_counts_duplicate_identity_conflict(self):
        stats = within_file(_parse(cases.FIXTURE_B))
        self.assertEqual(stats["rows"], 4)
        self.assertEqual(stats["unique_identity_keys"], 2)
        self.assertEqual(stats["identity_keys_multi"], 1)
        self.assertEqual(stats["identity_keys_conflict"], 1)
        self.assertEqual(stats["duplicate_qids"], 0)

    def test_duplicate_identity_same_answer_is_not_a_conflict(self):
        rows = [
            parse_row(cases._row("a", "The _ is x", "p", "q", "1")),
            parse_row(cases._row("b", "The _ is x", "p", "q", "1")),
        ]
        stats = within_file(rows)
        self.assertEqual(stats["identity_keys_multi"], 1)
        self.assertEqual(stats["identity_keys_conflict"], 0)

    def test_nesting_flags_violation_and_answer_conflict(self):
        n = nesting(_parse(cases.FIXTURE_A), _parse(cases.FIXTURE_B))
        self.assertEqual(n["shared_qids"], 2)
        self.assertEqual(n["qids_only_in_smaller"], 1)
        self.assertEqual(n["shared_answer_conflict"], 1)

    def test_nesting_perfect_subset_has_no_violation(self):
        small = _parse(cases.FIXTURE_A)
        larger = small + [parse_row(cases._row("qX", "The _ is new", "m", "n", "2"))]
        n = nesting(small, larger)
        self.assertEqual(n["qids_only_in_smaller"], 0)
        self.assertEqual(n["shared_answer_conflict"], 0)
        self.assertEqual(n["shared_qids"], 3)

    def test_overlap_counts_shared_qids(self):
        o = overlap(_parse(cases.FIXTURE_A), _parse(cases.FIXTURE_B))
        self.assertEqual(o["shared_qids"], 2)

    def test_public_summary_is_a_string(self):
        result = census([("A", _parse(cases.FIXTURE_A)), ("B", _parse(cases.FIXTURE_B))])
        self.assertIsInstance(public_summary(result, cases.PAIRS), str)


if __name__ == "__main__":
    unittest.main()
