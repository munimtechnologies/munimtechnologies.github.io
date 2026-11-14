# SPDX-License-Identifier: Apache-2.0
"""Hand-traced unit tests for audit 120 (standard library only). Apache-2.0.
Made with AI agents working in MV2's name (MV2 of Munim, Inc.)."""
import unittest
from fractions import Fraction

import grade120 as g

CYR_A, CYR_BE, CYR_VE, CYR_GE = "А", "Б", "В", "Г"


class TestTranscription(unittest.TestCase):
    def test_letter_a_normalises_to_empty(self):
        self.assertEqual(g.normalize_text("A"), "")
        self.assertEqual(g.normalize_text("(A)"), "")
        self.assertEqual(g.normalize_text("A."), "")
        self.assertEqual(g.normalize_text("A", should_remove_articles=False), "a")
        self.assertEqual(g.normalize_text("B"), "b")

    def test_any_answer_matches_gold_a(self):
        self.assertEqual(g.quasi_prefix_exact_match("A", "## Step 1: Understand the question"), 1)
        self.assertEqual(g.quasi_prefix_exact_match("A", "The"), 1)
        self.assertEqual(g.quasi_prefix_exact_match("A", "C."), 1)
        self.assertEqual(g.quasi_prefix_exact_match("A", ""), 0)

    def test_other_letters(self):
        self.assertEqual(g.quasi_prefix_exact_match("B", "The"), 0)
        self.assertEqual(g.quasi_prefix_exact_match("B", "Both"), 1)
        self.assertEqual(g.quasi_prefix_exact_match("C", "C."), 1)
        self.assertEqual(g.quasi_prefix_exact_match("D", "B"), 0)

    def test_cyrillic_gold_never_matches_latin(self):
        self.assertEqual(g.quasi_prefix_exact_match(CYR_A, "A"), 0)
        self.assertEqual(g.quasi_prefix_exact_match(CYR_VE, "B"), 0)
        self.assertEqual(g.quasi_prefix_exact_match(CYR_GE, "**" + CYR_GE + "**"), 1)


class TestOurGrades(unittest.TestCase):
    def test_first_word(self):
        self.assertEqual(g.first_word("A."), "a")
        self.assertEqual(g.first_word("(A)"), "a")
        self.assertEqual(g.first_word("**" + CYR_GE + "**"), "г")
        self.assertEqual(g.first_word(CYR_GE + ") № 4"), "г")
        self.assertEqual(g.first_word("   "), "")

    def test_letter_grade(self):
        self.assertEqual(g.letter_grade("A", "A."), 1)
        self.assertEqual(g.letter_grade("A", "C."), 0)
        self.assertEqual(g.letter_grade("A", "Answer"), 0)
        self.assertEqual(g.letter_grade("B", "Both"), 0)
        self.assertEqual(g.letter_grade("A", ""), 0)
        self.assertEqual(g.letter_grade("red car", "red car parked"), 1)

    def test_classes(self):
        self.assertEqual(g.grade_record(["A"], "The")["cls"], "free_article_gold")
        self.assertEqual(g.grade_record(["A"], "A")["cls"], "genuine")
        self.assertEqual(g.grade_record(["B"], "Both")["cls"], "prefix_word")
        self.assertEqual(g.grade_record(["C"], "C")["cls"], "genuine")
        self.assertEqual(g.grade_record(["D"], "B")["cls"], "miss")
        self.assertEqual(g.grade_record(["A"], "")["cls"], "miss")
        self.assertTrue(g.grade_record(["(A)"], "B")["article_gold"])

    def test_cyrillic_helpers(self):
        self.assertTrue(g.is_cyrillic(CYR_BE))
        self.assertFalse(g.is_cyrillic("B"))
        self.assertEqual(g.answer_kind("C."), "latin_letter")
        self.assertEqual(g.answer_kind(CYR_VE + ")"), "cyr_letter")
        self.assertEqual(g.answer_kind("## Step 1"), "other")
        self.assertEqual(g.answer_kind(""), "empty")
        self.assertTrue(g.cyr_position_right(CYR_VE, "C"))
        self.assertFalse(g.cyr_position_right(CYR_VE, "B"))
        self.assertTrue(g.cyr_lookalike_b(CYR_VE, "B"))
        self.assertTrue(g.cyr_position_right("а", "A"))
        self.assertTrue(g.cyr_position_right(CYR_BE, "b."))
        self.assertTrue(g.beyond_four("E"))
        self.assertTrue(g.beyond_four("2"))
        self.assertFalse(g.beyond_four("D"))


class TestRunLevel(unittest.TestCase):
    RUN = ("exams_v:language=Bulgarian,subject_grouped=Natural_Science,type=image_text,"
           "model=openai_gpt-4o-2024-11-20,groups=exams_v_bulgarian")

    def test_run_field(self):
        self.assertEqual(g.run_field(self.RUN, "language"), "Bulgarian")
        self.assertEqual(g.run_field(self.RUN, "model"), "openai_gpt-4o-2024-11-20")
        self.assertEqual(g.family_of(self.RUN), "exams_v")
        self.assertIsNone(g.run_field(self.RUN, "category"))

    def test_stat_entry_skips_perturbed(self):
        stats = [{"name": {"name": g.STAT, "split": "valid", "perturbation": {"name": "robustness"}}, "mean": 0.1},
                 {"name": {"name": g.STAT, "split": "test"}, "mean": 0.2},
                 {"name": {"name": g.STAT, "split": "valid"}, "mean": 0.3}]
        self.assertEqual(g.stat_entry(stats, g.STAT, "valid")["mean"], 0.3)
        self.assertIsNone(g.stat_entry([], g.STAT, "valid"))

    def test_summarize_run(self):
        instances = [
            {"id": "id1", "split": "valid", "references": [{"output": {"text": "A"}, "tags": ["correct"]}]},
            {"id": "id2", "split": "valid", "references": [{"output": {"text": "B"}, "tags": ["correct"]}]},
            {"id": "id3", "split": "valid", "references": [{"output": {"text": "A"}, "tags": ["correct"]}]},
            {"id": "id4", "split": "train", "references": [{"output": {"text": "C"}, "tags": ["correct"]}]},
        ]
        preds = [
            {"instance_id": "id1", "train_trial_index": 0, "predicted_text": "The", "stats": {g.STAT: 1.0}},
            {"instance_id": "id2", "train_trial_index": 0, "predicted_text": " B ", "stats": {g.STAT: 1.0}},
            {"instance_id": "id3", "train_trial_index": 0, "predicted_text": "A", "stats": {g.STAT: 1.0}},
            {"instance_id": "id4", "train_trial_index": 0, "predicted_text": "C", "stats": {g.STAT: 1.0}},
            {"instance_id": "id9", "train_trial_index": 0, "predicted_text": "C", "stats": {g.STAT: 0.0}},
        ]
        s = g.summarize_run(preds, g.instance_map(instances), "valid")
        c = s["counts"]
        self.assertEqual((c["kept"], c["credit"], c["letter"], c["mismatch"]), (3, 3, 2, 0))
        self.assertEqual((c["article_gold"], c["other_split"], c["no_instance"]), (2, 1, 1))
        self.assertEqual(s["classes"]["free_article_gold"], 1)
        self.assertEqual(s["classes"]["genuine"], 2)

    def test_summarize_cyrillic(self):
        instances = [
            {"id": "id1", "split": "test", "references": [{"output": {"text": CYR_VE}, "tags": ["correct"]}]},
            {"id": "id2", "split": "test", "references": [{"output": {"text": CYR_GE}, "tags": ["correct"]}]},
            {"id": "id3", "split": "test", "references": [{"output": {"text": CYR_A}, "tags": ["correct"]}]},
        ]
        preds = [
            {"instance_id": "id1", "train_trial_index": 0, "predicted_text": "C", "stats": {g.STAT: 0.0}},
            {"instance_id": "id2", "train_trial_index": 0, "predicted_text": CYR_GE + ")", "stats": {g.STAT: 1.0}},
            {"instance_id": "id3", "train_trial_index": 0, "predicted_text": "A", "stats": {g.STAT: 0.0}},
        ]
        s = g.summarize_run(preds, g.instance_map(instances), "test")
        cy = s["cyr"]
        self.assertEqual((cy["n"], cy["credit"], cy["latin_letter"], cy["cyr_letter"]), (3, 1, 2, 1))
        self.assertEqual((cy["pos_right"], cy["latin_letter_credit"], s["counts"]["mismatch"]), (2, 0, 0))


class TestStats(unittest.TestCase):
    def test_tau(self):
        self.assertEqual(g.kendall_tau_b([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertEqual(g.kendall_tau_b([1, 2, 3], [3, 2, 1]), -1.0)
        self.assertIsNone(g.kendall_tau_b([1, 1], [2, 2]))

    def test_ranks(self):
        self.assertEqual(g.ranks_high({"x": 3, "y": 5, "z": 3}), {"x": 2, "y": 1, "z": 2})

    def test_verdicts(self):
        fam = {f: {"runs_nonempty": 100, "runs_included": 100, "kept": 10, "article_gold": 3} for f in g.FAMILIES}
        st = {"families": fam, "credits": 100, "free_article_gold": 5, "prefix_word": 0, "models_drop_005": 10,
              "taus": [0.95, 0.89], "bg_latin_letter": 6, "bg_cyr_letter": 4, "bg_pos_right": 2}
        v = g.verdicts(st)
        self.assertEqual([v["P%d" % i] for i in range(1, 9)], [True, True, True, True, True, True, True, False])
        self.assertEqual(Fraction(2, 6) < Fraction(35, 100), True)
        self.assertEqual(g.verdict_word(None), "NOT COMPUTABLE")


if __name__ == "__main__":
    unittest.main()
