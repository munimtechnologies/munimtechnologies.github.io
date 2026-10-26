"""Standard-library unit tests for the ANLI per-(genre, class) within-R3 verifier-agreement census.

Checks the primitives and asserts the hand-traced fixture reproduces the frozen TARGET exactly.

Apache-2.0.
"""
import unittest

import cases
from genre_class_agreement import (census_genre_class, flatten, norm_label, parse_verifier_row,
                                   strict_majority, genre_key)


class TestPrimitives(unittest.TestCase):
    def test_norm_label(self):
        self.assertEqual(norm_label("Entailment"), "e")
        self.assertEqual(norm_label(" n "), "n")
        self.assertEqual(norm_label("c"), "c")
        self.assertIsNone(norm_label(""))
        self.assertIsNone(norm_label(None))
        self.assertIsNone(norm_label("x"))

    def test_parse_verifier_row_space_and_underscore(self):
        self.assertEqual(parse_verifier_row({"uid": "a", "verifier labels": ["e", "n"]}),
                         {"uid": "a", "labels": ["e", "n"]})
        self.assertEqual(parse_verifier_row({"uid": "b", "verifier_labels": ["c"]}),
                         {"uid": "b", "labels": ["c"]})
        self.assertEqual(parse_verifier_row({"uid": "c"}), {"uid": "c", "labels": []})

    def test_strict_majority(self):
        self.assertEqual(strict_majority(["e", "e"]), "e")
        self.assertEqual(strict_majority(["c", "e", "c"]), "c")
        self.assertIsNone(strict_majority(["n", "c"]))
        self.assertIsNone(strict_majority(["e", "n", "c"]))
        self.assertIsNone(strict_majority([]))

    def test_genre_key(self):
        self.assertEqual(genre_key("wiki"), "wiki")
        self.assertEqual(genre_key("  news "), "news")
        self.assertIsNone(genre_key(""))
        self.assertIsNone(genre_key("   "))
        self.assertIsNone(genre_key(None))


class TestFixture(unittest.TestCase):
    def setUp(self):
        self.stats = census_genre_class(
            [parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW],
            cases.build_gold_index(cases.FIXTURE_MAIN_RAW))
        self.flat = flatten(self.stats)

    def test_target_met_exactly(self):
        self.assertEqual(set(self.flat), set(cases.TARGET))
        for k in cases.TARGET:
            self.assertEqual(self.flat[k], cases.TARGET[k], "mismatch at %s" % k)

    def test_totals(self):
        t = self.stats["totals"]
        self.assertEqual(t["n_verifier_lines"], 9)
        self.assertEqual(t["n_joined"], 8)
        self.assertEqual(t["n_orphan"], 1)
        self.assertEqual(t["n_not_r3"], 1)
        self.assertEqual(t["n_genre_absent"], 1)
        self.assertEqual(t["all_lines_match"], 7)
        self.assertEqual(t["all_lines_no_majority"], 1)
        self.assertEqual(t["all_lines_differ"], 0)

    def test_cells_present(self):
        cells = self.stats["by_cell"]
        # Six (genre, class) cells, all within R3; r1x and the genre-absent line are excluded.
        self.assertEqual(set(cells), {"wiki|e", "wiki|n", "wiki|c", "news|e", "news|n", "news|c"})
        self.assertEqual(cells["wiki|n"]["no_majority"], 1)
        self.assertEqual(cells["wiki|n"]["unanimous"], 0)
        self.assertEqual(cells["news|c"]["gold_votes"], 2)
        self.assertEqual(cells["news|c"]["total_votes"], 3)
        self.assertEqual(cells["wiki|c"]["unanimous"], 1)


if __name__ == "__main__":
    unittest.main()
