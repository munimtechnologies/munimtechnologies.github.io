"""Hand-traced tests of the per-schema row shaping (audit 57). Standard library unittest only.

Confirms that each real parquet schema (ARC/CommonsenseQA struct choices; HellaSwag endings) maps to the generic
(labels, texts, answer_key) tuple the census consumes, including that a goldless test row (empty answer) shapes
cleanly and is then classed 'bad_key' -- which is why the goldless test splits are excluded in cases.DATASETS.
"""

import unittest

import loaders
import position_census as pc


class TestShapeChoicesStruct(unittest.TestCase):
    def test_arc_four_letter_labels(self):
        choices = {"text": ["dry palms", "wet palms", "palms covered with oil", "palms covered with lotion"],
                   "label": ["A", "B", "C", "D"]}
        labels, texts, key = loaders.shape_choices_struct(choices, "A")
        self.assertEqual(labels, ["A", "B", "C", "D"])
        self.assertEqual(texts, ["dry palms", "wet palms", "palms covered with oil", "palms covered with lotion"])
        self.assertEqual(key, "A")
        self.assertEqual(pc.question_validity(labels, texts, key), "valid")

    def test_arc_numeric_labels(self):
        choices = {"text": ["a", "b", "c", "d"], "label": ["1", "2", "3", "4"]}
        labels, texts, key = loaders.shape_choices_struct(choices, "3")
        self.assertEqual(labels, ["1", "2", "3", "4"])
        self.assertEqual(key, "3")
        self.assertEqual(labels.index(key), 2)   # gold position 2

    def test_csqa_five_options(self):
        choices = {"text": ["ignore", "enforce", "authoritarian", "yell at", "avoid"],
                   "label": ["A", "B", "C", "D", "E"]}
        labels, texts, key = loaders.shape_choices_struct(choices, "A")
        self.assertEqual(len(labels), 5)
        self.assertEqual(labels[4], "E")
        self.assertEqual(pc.question_validity(labels, texts, key), "valid")

    def test_goldless_is_bad_key(self):
        choices = {"text": ["a", "b", "c", "d"], "label": ["A", "B", "C", "D"]}
        labels, texts, key = loaders.shape_choices_struct(choices, "")
        self.assertEqual(key, "")
        self.assertEqual(pc.question_validity(labels, texts, key), "bad_key")


class TestShapeEndings(unittest.TestCase):
    def test_hellaswag(self):
        endings = ["e0", "e1", "e2", "e3"]
        labels, texts, key = loaders.shape_endings(endings, "3")
        self.assertEqual(labels, ["0", "1", "2", "3"])
        self.assertEqual(texts, endings)
        self.assertEqual(key, "3")
        self.assertEqual(pc.question_validity(labels, texts, key), "valid")
        self.assertEqual(labels.index(key), 3)

    def test_hellaswag_goldless(self):
        labels, texts, key = loaders.shape_endings(["a", "b", "c", "d"], "")
        self.assertEqual(labels, ["0", "1", "2", "3"])
        self.assertEqual(key, "")
        self.assertEqual(pc.question_validity(labels, texts, key), "bad_key")

    def test_none_safe(self):
        labels, texts, key = loaders.shape_endings([None, "b"], None)
        self.assertEqual(texts, ["", "b"])
        self.assertEqual(key, "")


if __name__ == "__main__":
    unittest.main()
