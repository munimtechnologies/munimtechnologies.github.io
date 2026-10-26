"""Stdlib unittest suite for the ANLI per-genre verifier-agreement census.

Checks the label/majority/genre helpers, then runs the hand-traced fixture through census_genre and
asserts the flattened result equals the frozen TARGET, cell by cell. No network, no files.
"""
import unittest

import cases
from genre_agreement import (
    census_genre, flatten, genre_key, norm_label, parse_verifier_row, strict_majority,
)


class TestHelpers(unittest.TestCase):
    def test_norm_label(self):
        self.assertEqual(norm_label("entailment"), "e")
        self.assertEqual(norm_label("Neutral"), "n")
        self.assertEqual(norm_label(" c "), "c")
        self.assertIsNone(norm_label(""))
        self.assertIsNone(norm_label(None))
        self.assertIsNone(norm_label("x"))

    def test_parse_verifier_row(self):
        self.assertEqual(parse_verifier_row({"uid": "a", "verifier labels": ["e", "n"]}),
                         {"uid": "a", "labels": ["e", "n"]})
        self.assertEqual(parse_verifier_row({"uid": "b", "verifier_labels": ["c"]}),
                         {"uid": "b", "labels": ["c"]})
        self.assertEqual(parse_verifier_row({"uid": "c"}), {"uid": "c", "labels": []})

    def test_strict_majority(self):
        self.assertEqual(strict_majority(["e", "n", "e"]), "e")
        self.assertIsNone(strict_majority(["e", "n", "c"]))
        self.assertIsNone(strict_majority(["n", "c"]))
        self.assertEqual(strict_majority(["e", "e"]), "e")
        self.assertEqual(strict_majority(["c", "c", "n"]), "c")

    def test_genre_key(self):
        self.assertEqual(genre_key("wikipedia"), "wikipedia")
        self.assertEqual(genre_key(" news "), "news")
        self.assertEqual(genre_key("procedural/causal"), "procedural/causal")
        self.assertIsNone(genre_key(""))
        self.assertIsNone(genre_key("   "))
        self.assertIsNone(genre_key(None))


class TestFixture(unittest.TestCase):
    def setUp(self):
        verifier_rows = [parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW]
        gold_index = cases.build_gold_index(cases.FIXTURE_MAIN_RAW)
        self.stats = census_genre(verifier_rows, gold_index)
        self.flat = flatten(self.stats)

    def test_matches_target_cell_by_cell(self):
        self.assertEqual(set(self.flat), set(cases.TARGET))
        for k in sorted(cases.TARGET):
            self.assertEqual(self.flat[k], cases.TARGET[k], msg="mismatch at %s" % k)

    def test_totals_add_up(self):
        t = self.stats["totals"]
        self.assertEqual(t["n_joined"],
                         t["all_lines_match"] + t["all_lines_differ"] + t["all_lines_no_majority"])

    def test_pooled_partition(self):
        # In each genre, n splits exactly into gold_majority + majority_differs + no_majority.
        for g, tally in self.stats["by_genre"].items():
            self.assertEqual(tally["n"],
                             tally["gold_majority"] + tally["majority_differs"] + tally["no_majority"],
                             msg="partition %s" % g)
            self.assertLessEqual(tally["gold_votes"], tally["total_votes"])

    def test_r3_is_subset_of_pooled(self):
        # Every R3-only tally cell must be <= the pooled cell for the same genre and field.
        for g, r3 in self.stats["by_genre_r3"].items():
            pooled = self.stats["by_genre"][g]
            for f in ("n", "gold_majority", "no_majority", "gold_votes", "total_votes"):
                self.assertLessEqual(r3[f], pooled[f], msg="r3<=pooled %s %s" % (g, f))

    def test_genre_absent_not_attributed(self):
        # The one genre-absent line is counted in totals but in no genre tally.
        self.assertEqual(self.stats["totals"]["n_genre_absent"], 1)
        pooled_n = sum(t["n"] for t in self.stats["by_genre"].values())
        self.assertEqual(pooled_n + self.stats["totals"]["n_genre_absent"]
                         + self.stats["totals"]["n_gold_unexpected"],
                         self.stats["totals"]["n_joined"])


if __name__ == "__main__":
    unittest.main()
