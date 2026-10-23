"""Tests for the ARC disjointness / leakage / gold-conflict census (stdlib unittest)."""
import unittest

import cases
from arc_consistency import (
    normalize, parse_row, within_file, overlap, flatten,
)


def _parse(fixture):
    return [parse_row(obj) for obj in fixture]


def _within_map(names, fixtures):
    return {n: within_file(_parse(f)) for n, f in zip(names, fixtures)}


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        within_map = _within_map(cases.NAMES, [cases.FIXTURE_X, cases.FIXTURE_Y])
        overlap_map = {("X", "Y"): overlap(_parse(cases.FIXTURE_X), _parse(cases.FIXTURE_Y))}
        flat = flatten(within_map, overlap_map, cases.NAMES, cases.PAIRS)
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_normalize_collapses_whitespace_and_case(self):
        self.assertEqual(normalize("  The   SKY "), "the sky")
        self.assertEqual(normalize(None), "")

    def test_parse_reads_identity_and_gold(self):
        r = parse_row(cases.FIXTURE_X[0])
        self.assertEqual(r["id"], "x1")
        self.assertEqual(r["gold"], "aa")
        self.assertFalse(r["malformed"])
        self.assertEqual(r["identity"], ("s1", frozenset({"aa", "bb"})))

    def test_malformed_when_answerkey_matches_no_label(self):
        r = parse_row(cases.FIXTURE_X[3])
        self.assertTrue(r["malformed"])
        self.assertIsNone(r["gold"])

    def test_parse_accepts_flat_hf_shape(self):
        obj = {"id": "z", "question": "What?",
               "choices": {"text": ["aa", "bb"], "label": ["A", "B"]}, "answerKey": "B"}
        r = parse_row(obj)
        self.assertEqual(r["gold"], "bb")
        self.assertEqual(r["identity"], ("what?", frozenset({"aa", "bb"})))

    def test_within_file_counts_conflict_and_excludes_malformed(self):
        w = within_file(_parse(cases.FIXTURE_X))
        self.assertEqual(w["rows"], 4)
        self.assertEqual(w["malformed"], 1)
        self.assertEqual(w["identity_keys_multi"], 1)
        self.assertEqual(w["identity_keys_conflict"], 1)

    def test_duplicate_identity_same_gold_is_not_a_conflict(self):
        rows = [
            parse_row(cases._row("a", "S", [("A", "p"), ("B", "q")], "A")),
            parse_row(cases._row("b", "S", [("A", "p"), ("B", "q")], "A")),
        ]
        w = within_file(rows)
        self.assertEqual(w["identity_keys_multi"], 1)
        self.assertEqual(w["identity_keys_conflict"], 0)

    def test_overlap_counts_shared_ids_identities_and_conflicts(self):
        o = overlap(_parse(cases.FIXTURE_X), _parse(cases.FIXTURE_Y))
        self.assertEqual(o["shared_ids"], 1)
        self.assertEqual(o["shared_identities"], 2)
        self.assertEqual(o["shared_identity_gold_conflict"], 1)

    def test_disjoint_records_have_no_overlap(self):
        a = [parse_row(cases._row("a", "SA", [("A", "x"), ("B", "y")], "A"))]
        b = [parse_row(cases._row("b", "SB", [("A", "m"), ("B", "n")], "B"))]
        o = overlap(a, b)
        self.assertEqual(o["shared_ids"], 0)
        self.assertEqual(o["shared_identities"], 0)
        self.assertEqual(o["shared_identity_gold_conflict"], 0)


if __name__ == "__main__":
    unittest.main()
