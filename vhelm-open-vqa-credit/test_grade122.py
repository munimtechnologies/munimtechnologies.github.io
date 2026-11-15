# SPDX-License-Identifier: Apache-2.0
"""Hand-traced tests for grade122 (audit 122). Standard library only. Made with AI agents working in MV2's name."""
import unittest
from fractions import Fraction

import grade122 as g


class TestNormalize(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(g.normalize_text("The Car!"), "car")
        self.assertEqual(g.normalize_text("No, the pot is black."), "no pot is black")


class TestCreditClass(unittest.TestCase):
    def test_mid_word(self):
        self.assertEqual(g.credit_class(["car", "The car is red."], "Carpet"), (1, 0, "mid_word"))
        self.assertEqual(g.credit_class(["wood"], "wooden"), (1, 0, "mid_word"))

    def test_word_prefix(self):
        self.assertEqual(g.credit_class(["no", "No, the pot is black."], "No, it is not."), (1, 0, "word_prefix"))

    def test_match_and_miss(self):
        self.assertEqual(g.credit_class(["Dog"], "dog."), (1, 1, "match"))
        self.assertEqual(g.credit_class(["yes"], "No"), (0, 0, None))

    def test_empty_ref_and_blank_answer(self):
        self.assertEqual(g.credit_class(["a"], "blue"), (1, 0, "empty_ref"))
        self.assertEqual(g.credit_class(["dog"], "   "), (0, 0, None))


class TestConsensus(unittest.TestCase):
    def test_vqa_consensus(self):
        self.assertEqual(g.vqa_consensus(0, 10), Fraction(0))
        self.assertEqual(g.vqa_consensus(1, 10), Fraction(3, 10))
        self.assertEqual(g.vqa_consensus(2, 10), Fraction(3, 5))
        self.assertEqual(g.vqa_consensus(3, 10), Fraction(9, 10))
        self.assertEqual(g.vqa_consensus(4, 10), Fraction(1))
        self.assertIsNone(g.vqa_consensus(1, 2))

    def test_match_count(self):
        refs = ["sidewalk"] * 4 + ["on sidewalk"] * 6
        self.assertEqual(g.match_count(refs, "Sidewalk"), 4)
        self.assertEqual(g.credit_class(refs, "Sidewalk"), (1, 1, "match"))

    def test_markup(self):
        self.assertTrue(g.has_markup("<ref>dog</ref><box>(1,2),(3,4)</box>"))
        self.assertFalse(g.has_markup("dog"))


class TestRunFiles(unittest.TestCase):
    def test_run_field_and_stat_mean(self):
        self.assertEqual(g.run_field("vqa:model=a_b,groups=vqa_base", "model"), "a_b")
        stats = [{"name": {"name": g.STAT, "split": "valid", "perturbation": {"name": "robustness"}}, "mean": 0.1},
                 {"name": {"name": g.STAT, "split": "valid"}, "mean": 0.5}]
        self.assertEqual(g.stat_mean(stats, "valid", g.STAT), 0.5)
        self.assertIsNone(g.stat_mean(stats, "test", g.STAT))

    def test_instance_map(self):
        inst = [{"id": "i1", "split": "valid", "references": [
                    {"output": {"text": "yes"}, "tags": ["correct"]}, {"output": {"text": "x"}, "tags": []}]},
                {"id": "i2", "split": "valid", "perturbation": {"name": "robustness"}, "references": []},
                {"id": "i3", "split": "train", "references": []}]
        imap, pert = g.instance_map(inst, "valid")
        self.assertEqual(imap, {"i1": ["yes"]})
        self.assertEqual(pert, 1)

    def test_summarize_run(self):
        imap = {"i1": ["yes"], "i2": ["car"], "i3": ["blue", "Blue sky."]}
        preds = [{"instance_id": "i1", "train_trial_index": 0, "predicted_text": "Yes", "stats": {g.STAT: 1.0}},
                 {"instance_id": "i2", "train_trial_index": 0, "predicted_text": "carpet", "stats": {g.STAT: 1.0}},
                 {"instance_id": "i2", "train_trial_index": 0, "predicted_text": "car"},
                 {"instance_id": "i9", "train_trial_index": 0, "predicted_text": "x"},
                 {"instance_id": "i3", "train_trial_index": 1, "predicted_text": "blue"},
                 {"instance_id": "i3", "train_trial_index": 0, "predicted_text": "blue", "stats": {g.STAT: 0.0}}]
        c, s, ex = g.summarize_run(preds, imap)
        self.assertEqual((c["n_pred"], c["scored"], c["duplicate"], c["no_instance"], c["other_trial"]),
                         (6, 3, 1, 1, 1))
        self.assertEqual((c["rec_checked"], c["rec_agree"]), (3, 2))
        self.assertEqual((s["n"], s["h"], s["q"]), (3, 3, 2))
        self.assertEqual(s["cls"], {"match": 2, "word_prefix": 0, "mid_word": 1, "empty_ref": 0})
        self.assertEqual(s["zero_match"], 1)
        self.assertEqual(s["m_hist"], {"0": 1, "1": 2, "2": 0, "3": 0, "4+": 0})
        self.assertEqual(ex, [("i2", "mid_word", 0)])

    def test_summarize_vqa_consensus(self):
        imap = {"a": ["blue"] * 5 + ["white"] * 5,
                "b": ["pamphlets"] * 3 + ["tags", "box", "booklets", "plate", "linens", "cards", "manuals"]}
        preds = [{"instance_id": "a", "train_trial_index": 0, "predicted_text": "White"},
                 {"instance_id": "b", "train_trial_index": 0, "predicted_text": "tags"}]
        c, s, ex = g.summarize_run(preds, imap, consensus=True)
        self.assertEqual((s["n"], s["h"], s["c_n"]), (2, 2, 2))
        self.assertEqual(s["c_sum"], Fraction(13, 10))
        self.assertEqual(s["minority"], 1)
        self.assertEqual(ex, [("b", "match", 1)])


class TestRanksAndVerdicts(unittest.TestCase):
    def test_ranks(self):
        self.assertEqual(g.min_ranks({"a": 1, "b": 2, "c": 2}), {"a": 3, "b": 1, "c": 1})
        self.assertEqual(g.kendall_tau_b([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertIsNone(g.kendall_tau_b([1, 1], [1, 2]))

    def test_verdicts(self):
        st = {"fam_inc": {"gqa": (51, 51), "vqa": (51, 51), "viz_wiz": (50, 51)},
              "vqa_credits": 1000, "vqa_minority": 20, "vqa_zero_match": 9, "vqa_median_diff": Fraction(3, 100),
              "vqa_movers": 1, "gqa_credits": 1000, "gqa_mid": 9, "gqa_word_models": 3,
              "qwen_markup": {"vqa": (9, 10), "viz_wiz": (10, 10)}}
        vd = g.verdicts(st)
        self.assertEqual(sum(vd.values()), 7)
        self.assertFalse(vd["P1_reproduced"])
        st["fam_inc"]["viz_wiz"] = (51, 51)
        st["qwen_markup"] = {"vqa": (9, 10)}
        st["vqa_zero_match"] = 10
        vd = g.verdicts(st)
        self.assertTrue(vd["P1_reproduced"])
        self.assertFalse(vd["P7_qwen_vl_chat_markup"])
        self.assertFalse(vd["P8_vqa_prefix_only_rare"])
        self.assertEqual(g.verdict_word(True), "HELD")


if __name__ == "__main__":
    unittest.main()
