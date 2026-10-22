"""Tests for the SNLI x MultiNLI cross-overlap census (stdlib unittest, run in compete)."""
import os
import tempfile
import unittest
import zipfile

import cases
import job
from cross_nli_overlap import (
    cross_census, build_index, normalize, _bit, _labels, public_summary,
)


class TestCrossCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        result = cross_census(cases.FIXTURE_SNLI, cases.FIXTURE_MULTINLI)
        flat = cases.flatten(result)
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_normalize_collapses_whitespace_and_case(self):
        self.assertEqual(normalize("  Hello   World  "), "hello world")
        self.assertEqual(normalize("A\tB\nC"), "a b c")
        self.assertEqual(normalize(None), "")

    def test_bit_excludes_dash_and_unknown(self):
        self.assertEqual(_bit("entailment"), 1)
        self.assertEqual(_bit("-"), 0)
        self.assertEqual(_bit("hidden"), 0)

    def test_labels_decodes_bitmask(self):
        self.assertEqual(_labels(1 | 4), ["contradiction", "entailment"])

    def test_dash_rows_are_malformed_not_counted(self):
        exact, norm, stats = build_index([("p", "h", "-"), ("p", "h", "entailment")])
        self.assertEqual(stats["malformed"], 1)
        self.assertEqual(stats["rows_kept"], 1)
        self.assertEqual(stats["unique_pairs"], 1)

    def test_same_label_shared_pair_is_not_a_conflict(self):
        r = cross_census(
            [("p", "h", "entailment")],
            [("p", "h", "entailment")],
        )
        self.assertEqual(r["exact_overlap_pairs"], 1)
        self.assertEqual(r["exact_overlap_same_label"], 1)
        self.assertEqual(r["exact_overlap_conflicting_label"], 0)

    def test_conflicting_shared_pair_is_flagged(self):
        r = cross_census(
            [("p", "h", "entailment")],
            [("p", "h", "contradiction")],
        )
        self.assertEqual(r["exact_overlap_pairs"], 1)
        self.assertEqual(r["exact_overlap_conflicting_label"], 1)
        self.assertEqual(r["exact_overlap_same_label"], 0)

    def test_disjoint_pairs_do_not_overlap(self):
        r = cross_census(
            [("a", "b", "neutral")],
            [("c", "d", "neutral")],
        )
        self.assertEqual(r["exact_overlap_pairs"], 0)
        self.assertEqual(r["norm_overlap_pairs"], 0)

    def test_normalized_only_overlap_is_additional(self):
        r = cross_census(
            [("Two  women   talk.", "People converse.", "neutral")],
            [("two women talk.", "people converse.", "neutral")],
        )
        self.assertEqual(r["exact_overlap_pairs"], 0)
        self.assertEqual(r["norm_overlap_pairs"], 1)
        self.assertEqual(r["norm_additional_over_exact"], 1)
        self.assertEqual(r["norm_overlap_same_label"], 1)

    def test_public_summary_is_a_string(self):
        r = cross_census(cases.FIXTURE_SNLI, cases.FIXTURE_MULTINLI)
        self.assertIsInstance(public_summary(r), str)


class TestIterRowsDedup(unittest.TestCase):
    """iter_rows must read each member basename once even if two mirror zips are present."""

    @staticmethod
    def _write_snli_zip(path):
        row = ('{"sentence1": "A man sits.", "sentence2": "A person rests.", '
               '"gold_label": "entailment"}\n')
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("snli_1.0/snli_1.0_train.jsonl", row)

    def test_two_identical_snli_zips_are_counted_once(self):
        with tempfile.TemporaryDirectory() as d:
            a = os.path.join(d, "snli_1.0.zip")
            b = os.path.join(d, "snli_1.0_mirror.zip")
            self._write_snli_zip(a)
            self._write_snli_zip(b)
            rows = list(job.iter_rows(sorted([a, b]), "snli"))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "A man sits.")
            self.assertEqual(rows[0][3], "train")

    def test_single_zip_reads_its_rows(self):
        with tempfile.TemporaryDirectory() as d:
            a = os.path.join(d, "snli_1.0.zip")
            self._write_snli_zip(a)
            rows = list(job.iter_rows([a], "snli"))
            self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
