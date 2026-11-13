# SPDX-License-Identifier: Apache-2.0
# Unit tests for audit 118 (MV2 of Munim, Inc.; made with AI agents). Standard library only.
import unittest
from fractions import Fraction

import grade118 as g

S = g.STAT


def inst(iid, question, gold, split="test"):
    return {"input": {"text": "", "multimedia_content": {"media_objects": [
        {"content_type": "image/jpeg", "location": "x.jpg"},
        {"content_type": "text/plain", "text": question}]}},
        "references": [{"output": {"text": gold}, "tags": ["correct"]}], "split": split, "id": iid}


class Scorer(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(g.normalize_text("The Yes."), "yes")

    def test_prefix_reads_ten_as_one(self):
        self.assertEqual(g.quasi_prefix_exact_match("1", "10"), 1)
        self.assertEqual(g.quasi_exact_match("1", "10"), 0)

    def test_prefix_reads_not_as_no(self):
        self.assertEqual(g.quasi_prefix_exact_match("no", "Not"), 1)

    def test_empty_prediction(self):
        self.assertEqual(g.quasi_prefix_exact_match("Yes", ""), 0)

    def test_cut_word(self):
        self.assertEqual(g.quasi_prefix_exact_match("2", "Numer"), 0)
        self.assertEqual(g.quasi_prefix_exact_match("0", "0"), 1)


class Classes(unittest.TestCase):
    def test_question_class(self):
        self.assertEqual(g.question_class("OODCV-VQA", "Is there a bicycle in the image?"), "presence")
        self.assertEqual(g.question_class("OODCV-VQA", "Is there an aeroplane in the image?"), "presence")
        self.assertEqual(g.question_class("OODCV-VQA", "How many unicorns are there in the image?"), "unicorn")
        self.assertEqual(g.question_class("OODCV-VQA", "How many bicycles are there in the image?"), "count")
        self.assertEqual(g.question_class("Sketchy-VQA", "Is this a radio in the image?"), "sketch")
        self.assertEqual(g.question_class("OODCV-VQA", "What is this?"), "other")

    def test_answer_kind(self):
        self.assertEqual(g.answer_kind("Yes."), "yesno")
        self.assertEqual(g.answer_kind(" 3"), "number")
        self.assertEqual(g.answer_kind("10"), "number")
        self.assertEqual(g.answer_kind("Numer"), "other")
        self.assertEqual(g.answer_kind("The"), "other")
        self.assertEqual(g.answer_kind(""), "empty")

    def test_question_of(self):
        self.assertEqual(g.question_of(inst("a", "Is there a bicycle in the image?", "Yes")),
                         "Is there a bicycle in the image?")
        self.assertEqual(g.question_of({"input": {"text": "Q?"}}), "Q?")

    def test_names(self):
        run = "unicorn:subject=OODCV-VQA,model=openai_gpt-4o"
        self.assertEqual(g.subject_of(run), "OODCV-VQA")
        self.assertEqual(g.model_of(run), "openai_gpt-4o")

    def test_instance_map(self):
        m = g.instance_map("OODCV-VQA", [inst("a", "How many unicorns are there in the image?", "0"),
                                         inst("b", "Is there a cat in the image?", "Yes", split="train")])
        self.assertEqual(m, {"a": ("unicorn", "0")})

    def test_stat_entry(self):
        stats = [{"name": {"name": S, "split": "test", "perturbation": {"name": "robustness"}},
                  "count": 1, "sum": 0.5, "mean": 0.5},
                 {"name": {"name": S, "split": "test"}, "count": 1, "sum": 0.808, "mean": 0.808}]
        self.assertEqual(g.stat_entry(stats, S)["mean"], 0.808)


class Blind(unittest.TestCase):
    def test_best_constant(self):
        self.assertEqual(g.best_constant(["2", "1", "2", "3"]), "2")
        self.assertEqual(g.best_constant(["1", "2"]), "1")
        self.assertIsNone(g.best_constant([]))

    def test_blind_score(self):
        imap = {"a": ("presence", "Yes"), "b": ("unicorn", "0"), "c": ("count", "2"), "d": ("count", "3")}
        self.assertEqual(g.blind_score(imap, "2", None), Fraction(3, 4))


class Summary(unittest.TestCase):
    def test_summarize_run(self):
        imap = {"i1": ("presence", "Yes"), "i2": ("unicorn", "0"), "i3": ("count", "1"), "i4": ("count", "2")}
        preds = [
            {"instance_id": "i1", "predicted_text": "Yes", "stats": {S: 1.0}},
            {"instance_id": "i2", "predicted_text": "0", "stats": {S: 1.0}},
            {"instance_id": "i3", "predicted_text": "10", "stats": {S: 1.0}},
            {"instance_id": "i4", "predicted_text": "There", "stats": {S: 0.0}},
            {"instance_id": "i4", "predicted_text": "2", "stats": {S: 1.0}},
            {"instance_id": "zz", "predicted_text": "Yes", "stats": {S: 1.0}},
            {"instance_id": "i1", "predicted_text": "Yes", "perturbation": {"name": "x"}, "stats": {}},
        ]
        s = g.summarize_run(preds, imap)
        c = s["counts"]
        self.assertEqual((c["n_records"], c["perturbed"], c["not_test"], c["duplicate"], c["kept"]), (7, 1, 1, 1, 4))
        self.assertEqual((c["stored_missing"], c["mismatch"], c["prefix_only"], c["credit"]), (0, 0, 1, 3))
        self.assertEqual(s["by_class"]["presence"], {"n": 1, "credit": 1, "exact": 1})
        self.assertEqual(s["by_class"]["unicorn"], {"n": 1, "credit": 1, "exact": 1})
        self.assertEqual(s["by_class"]["count"], {"n": 2, "credit": 1, "exact": 0})
        self.assertEqual(s["kinds"], {"yesno": 1, "number": 2, "empty": 0, "other": 1})
        self.assertEqual(s["answers"], {"yes": 1, "0": 1, "10": 1, "<other>": 1})
        self.assertEqual(g.acc(s["by_class"]["count"]), Fraction(1, 2))

    def test_mismatch(self):
        s = g.summarize_run([{"instance_id": "j", "predicted_text": "No", "stats": {S: 1.0}}],
                            {"j": ("presence", "Yes")})
        self.assertEqual((s["counts"]["mismatch"], s["counts"]["credit"]), (1, 1))


class Stats(unittest.TestCase):
    def test_ranks_and_tau(self):
        self.assertEqual(g.ranks_high({"a": 3, "b": 5, "c": 3}), {"a": 2, "b": 1, "c": 2})
        self.assertEqual(g.kendall_tau_b([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertEqual(g.kendall_tau_b([1, 2, 3], [3, 2, 1]), -1.0)

    def test_verdicts(self):
        s = {"runs_listed": 102, "runs_included": 100, "ids_oodcv": 1000, "ids_sketchy": 1000,
             "below_blind_oodcv": 5, "pooled_presence": Fraction(96, 100), "pooled_unicorn": Fraction(9, 10),
             "pooled_count": Fraction(7, 10), "pooled_credits": 1000, "pooled_prefix_only": 4,
             "movers_count": 10, "runs_nonanswer5": 3, "sketchy_one_answer80": 1, "leader_changes": True}
        self.assertTrue(all(g.verdicts(s).values()))
        s2 = dict(s, runs_included=96, pooled_prefix_only=5, leader_changes=None)
        v = g.verdicts(s2)
        self.assertFalse(v["P1"])
        self.assertFalse(v["P5"])
        self.assertIsNone(v["P8"])
        self.assertEqual(g.verdict_word(None), "NOT GRADED")


if __name__ == "__main__":
    unittest.main()
