"""Tests for the OpenBookQA Main-vs-Additional census (stdlib unittest, run in compete)."""
import unittest

import cases
from openbookqa_consistency import (
    census, flatten, parse_row, normalize, within_file, cross_file, public_summary,
)


def _parse(fixture):
    return [parse_row(obj, split) for obj, split in fixture]


class TestCensus(unittest.TestCase):
    def test_fixture_matches_hand_traced_target(self):
        result = census(_parse(cases.FIXTURE_MAIN), _parse(cases.FIXTURE_ADDITIONAL))
        flat = flatten(result)
        for key, expected in cases.TARGET.items():
            self.assertEqual(flat[key], expected, "mismatch on %s" % key)

    def test_normalize_collapses_whitespace_and_case(self):
        self.assertEqual(normalize("  Sky   COLOR? "), "sky color?")
        self.assertEqual(normalize(None), "")

    def test_parse_resolves_answer_text_from_key(self):
        row = parse_row(cases.FIXTURE_MAIN[0][0], "train")
        self.assertEqual(row["answer_text"], "blue")
        self.assertFalse(row["malformed"])

    def test_parse_marks_malformed_when_key_matches_no_choice(self):
        obj = {"id": "x", "question": {"stem": "s", "choices": [
            {"text": "a", "label": "A"}]}, "answerKey": "Z"}
        row = parse_row(obj, "train")
        self.assertTrue(row["malformed"])
        self.assertIsNone(row["answer_text"])

    def test_within_file_counts_duplicate_and_conflict(self):
        stats = within_file(_parse(cases.FIXTURE_MAIN))
        self.assertEqual(stats["unique_identity_keys"], 4)
        self.assertEqual(stats["identity_keys_multi"], 2)
        self.assertEqual(stats["identity_keys_conflict"], 1)
        self.assertEqual(stats["duplicate_ids"], 0)

    def test_duplicate_question_same_gold_is_not_a_conflict(self):
        # two rows, same (stem, choice-set), same gold -> multi but no conflict
        rows = [
            parse_row(cases._row("a", "Q?", "x", "y", "A"), "train"),
            parse_row(cases._row("b", "Q?", "x", "y", "A"), "train"),
        ]
        stats = within_file(rows)
        self.assertEqual(stats["identity_keys_multi"], 1)
        self.assertEqual(stats["identity_keys_conflict"], 0)

    def test_crossfile_flags_answerkey_disagreement(self):
        x = cross_file(_parse(cases.FIXTURE_MAIN), _parse(cases.FIXTURE_ADDITIONAL))
        self.assertEqual(x["shared_ids"], 5)
        self.assertEqual(x["answerkey_disagree"], 1)
        self.assertEqual(x["ids_only_in_main"], 1)
        self.assertEqual(x["ids_only_in_additional"], 1)

    def test_crossfile_identical_files_fully_agree(self):
        same = _parse(cases.FIXTURE_MAIN)
        x = cross_file(same, list(same))
        self.assertEqual(x["answerkey_disagree"], 0)
        self.assertEqual(x["ids_only_in_main"], 0)
        self.assertEqual(x["ids_only_in_additional"], 0)
        self.assertEqual(x["shared_ids"], 6)

    def test_public_summary_is_a_string(self):
        result = census(_parse(cases.FIXTURE_MAIN), _parse(cases.FIXTURE_ADDITIONAL))
        self.assertIsInstance(public_summary(result), str)


if __name__ == "__main__":
    unittest.main()
