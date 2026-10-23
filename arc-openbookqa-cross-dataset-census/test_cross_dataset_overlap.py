"""Tests for the ARC<->OpenBookQA cross-dataset overlap census (stdlib unittest)."""
import unittest

import cases
from cross_dataset_overlap import (
    normalize, parse_row, cross_overlap, flatten, identity_gold_map, stem_set,
)


def _parse(fixture):
    return [parse_row(obj) for obj in fixture]


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        result = cross_overlap(_parse(cases.FIXTURE_A), _parse(cases.FIXTURE_B))
        flat = flatten(result)
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_normalize_collapses_whitespace_and_case(self):
        self.assertEqual(normalize("  The   SKY "), "the sky")
        self.assertEqual(normalize(None), "")

    def test_parse_reads_identity_and_gold(self):
        r = parse_row(cases.FIXTURE_A[0])
        self.assertEqual(r["id"], "a1")
        self.assertEqual(r["gold"], "aa")
        self.assertFalse(r["malformed"])
        self.assertEqual(r["identity"], ("s1", frozenset({"aa", "bb"})))
        self.assertEqual(r["stem"], "s1")

    def test_malformed_when_answerkey_matches_no_label(self):
        r = parse_row(cases.FIXTURE_A[3])
        self.assertTrue(r["malformed"])
        self.assertIsNone(r["gold"])

    def test_parse_accepts_flat_hf_shape(self):
        obj = {"id": "z", "question": "What?",
               "choices": {"text": ["aa", "bb"], "label": ["A", "B"]}, "answerKey": "B"}
        r = parse_row(obj)
        self.assertEqual(r["gold"], "bb")
        self.assertEqual(r["identity"], ("what?", frozenset({"aa", "bb"})))

    def test_malformed_excluded_from_identity_and_stem_maps(self):
        recs = _parse(cases.FIXTURE_A)
        self.assertEqual(len(identity_gold_map(recs)), 3)
        self.assertEqual(stem_set(recs), {"s1", "s2", "s3"})

    def test_shared_identity_and_gold_conflict(self):
        result = cross_overlap(_parse(cases.FIXTURE_A), _parse(cases.FIXTURE_B))
        self.assertEqual(result["shared_identities"], 2)
        self.assertEqual(result["shared_identity_gold_conflict"], 1)
        self.assertEqual(result["shared_stems"], 3)

    def test_examples_report_the_conflict(self):
        result = cross_overlap(_parse(cases.FIXTURE_A), _parse(cases.FIXTURE_B))
        conflicts = [e for e in result["examples"] if e["gold_conflict"]]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["stem"], "s2")

    def test_disjoint_datasets_have_no_overlap(self):
        a = [parse_row(cases._row("a", "SA", [("A", "x"), ("B", "y")], "A"))]
        b = [parse_row(cases._row("b", "SB", [("A", "m"), ("B", "n")], "B"))]
        result = cross_overlap(a, b)
        self.assertEqual(result["shared_identities"], 0)
        self.assertEqual(result["shared_identity_gold_conflict"], 0)
        self.assertEqual(result["shared_stems"], 0)

    def test_max_examples_caps_the_list(self):
        a = [parse_row(cases._row("a%d" % i, "S%d" % i, [("A", "x%d" % i), ("B", "y%d" % i)], "A"))
             for i in range(10)]
        b = [parse_row(cases._row("b%d" % i, "S%d" % i, [("A", "x%d" % i), ("B", "y%d" % i)], "A"))
             for i in range(10)]
        result = cross_overlap(a, b, max_examples=3)
        self.assertEqual(result["shared_identities"], 10)
        self.assertEqual(len(result["examples"]), 3)


if __name__ == "__main__":
    unittest.main()
