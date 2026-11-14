# SPDX-License-Identifier: Apache-2.0
"""Hand-traced unit tests for audit 121 (grade121.py). Standard library only. Apache-2.0.
Made with AI agents working in MV2's name (MV2 of Munim, Inc.).
"""
import unittest

import grade121 as g

TR = {"name": "translate", "computed_on": "perturbed"}
TR_ZH = {"name": "translate", "language_code": "zh-CN"}


def ref(text, correct=False):
    return {"output": {"text": text}, "tags": ["correct"] if correct else []}


class TestNormalizeAndMetric(unittest.TestCase):
    def test_normalize(self):
        # "Project A" -> "project a" -> article 'a' removed -> "project"; "$12,000" -> '$' and ',' removed.
        cases = [("Project A", "project"), ("The", ""), ("A", ""), ("$12,000", "12000"), ("红色", "红色"),
                 ("an apple.", "apple"), ("  B ", "b")]
        for t, want in cases:
            self.assertEqual(g.normalize_text(t), want, t)

    def test_quasi_prefix(self):
        self.assertEqual(g.quasi_prefix_exact_match("Project A", "Project B"), 1)  # "project b" starts with "project"
        self.assertEqual(g.quasi_prefix_exact_match("A", "B"), 1)                  # gold normalises to ''
        self.assertEqual(g.quasi_prefix_exact_match("B", "A"), 0)                  # '' does not start with 'b'
        self.assertEqual(g.quasi_prefix_exact_match("红", "红色"), 1)
        self.assertEqual(g.quasi_prefix_exact_match("红色", "红"), 0)
        self.assertEqual(g.quasi_prefix_exact_match("x", ""), 0)                   # empty prediction scores 0

    def test_letter_index(self):
        self.assertEqual(g.letter_index("D", 4), 3)
        self.assertEqual(g.letter_index(" B\n", 2), 1)
        for pred in ("E", "b", "", "D.", None):
            self.assertIsNone(g.letter_index(pred, 4), pred)


class TestGradeAndCensus(unittest.TestCase):
    def test_grade_over_classes(self):
        r = g.grade(["Project A", "Project B"], 0, "B")
        self.assertEqual((r["idx"], r["h"], r["i"], r["cls"], r["mapped"]), (1, 1, 0, "over:prefix_only", "Project B"))
        r = g.grade(["A", "B", "Not enough information"], 0, "C")
        self.assertEqual((r["h"], r["i"], r["cls"]), (1, 0, "over:gold_empty"))
        r = g.grade(["A", "B", "Not enough information"], 1, "A")
        self.assertEqual((r["h"], r["i"], r["cls"]), (0, 0, None))
        r = g.grade(["猫", "猫头鹰", "狗"], 0, "B")
        self.assertEqual((r["h"], r["i"], r["cls"]), (1, 0, "over:prefix_only"))
        r = g.grade(["two", "two", "three"], 0, "B")
        self.assertEqual(r["cls"], "over:identical")
        r = g.grade(["-7", "7"], 0, "B")
        self.assertEqual(r["cls"], "over:quasi_only")

    def test_grade_under_and_unmapped(self):
        r = g.grade(["", "x"], 0, "A")
        self.assertEqual((r["idx"], r["h"], r["i"], r["cls"]), (0, 0, 1, "under"))
        r = g.grade(["p", "q"], 1, "Z")
        self.assertEqual((r["idx"], r["h"], r["i"], r["cls"], r["mapped"]), (None, 0, 0, None, None))

    def test_collisions(self):
        self.assertEqual(g.collisions(["A", "B", "Not enough information"], 0),
                         {"gold_empty": True, "identical": [], "quasi_only": [], "prefix_only": [1, 2]})
        self.assertEqual(g.collisions(["red", "red couch", "car"], 0),
                         {"gold_empty": False, "identical": [], "quasi_only": [], "prefix_only": [1]})
        self.assertEqual(g.collisions(["二", "二十", "三"], 0)["prefix_only"], [1])
        self.assertEqual(g.collisions(["Aspirin", "aspirin.", "Aspirin"], 0),
                         {"gold_empty": False, "identical": [2], "quasi_only": [1], "prefix_only": []})
        e = g.collisions(["red couch", "red", "car"], 0)
        self.assertFalse(g.any_collision(e))
        self.assertTrue(g.any_collision(g.collisions(["A", "B"], 0)))


class TestRunsAndStats(unittest.TestCase):
    def test_run_fields(self):
        self.assertEqual(g.run_field("a_okvqa:model=m,data_augmentation=chinese,groups=a_okvqa_chinese", "groups"),
                         "a_okvqa_chinese")
        self.assertEqual(g.run_field("a_okvqa:model=m,data_augmentation=dialect_prob=1.0_source=SAE_target=AAVE,"
                                     "groups=a_okvqa_dialect", "data_augmentation"),
                         "dialect_prob=1.0_source=SAE_target=AAVE")
        self.assertEqual(g.group_of("mmmu:subject=Art,question_type=multiple-choice,model=x", "mmmu"), "mmmu")
        self.assertEqual(g.variant_of(None), "")
        self.assertEqual(g.variant_of(TR_ZH), "translate:zh-CN")
        self.assertEqual(g.variant_of({"name": "dialect"}), "dialect")
        self.assertEqual(g.pert_key(TR), "translate")
        self.assertEqual(g.pert_key(None), "")

    def test_worst_name(self):
        self.assertIsNone(g.worst_name([]))
        self.assertEqual(g.worst_name([{"name": "translate", "fairness": False, "robustness": False}]), "translate")
        self.assertEqual(g.worst_name([{"name": "dialect", "fairness": True}]), "fairness")
        self.assertEqual(g.worst_name([{"name": "typos", "robustness": True}]), "robustness")

    def test_stat_mean(self):
        s = g.STAT
        stats = [{"name": {"name": s, "split": "valid"}, "mean": 0.892},
                 {"name": {"name": s, "split": "valid", "perturbation": {"name": "translate",
                                                                         "computed_on": "perturbed"}}, "mean": 0.861},
                 {"name": {"name": s, "split": "valid", "perturbation": {"name": "translate",
                                                                         "computed_on": "worst"}}, "mean": 0.843},
                 {"name": {"name": "exact_match", "split": "valid"}, "mean": 0.5}]
        self.assertEqual(g.stat_mean(stats, "valid"), 0.892)
        self.assertEqual(g.stat_mean(stats, "valid", "translate", "perturbed"), 0.861)
        self.assertEqual(g.stat_mean(stats, "valid", "translate", "worst"), 0.843)
        self.assertIsNone(g.stat_mean(stats, "test"))
        self.assertIsNone(g.stat_mean(stats, "valid", "fairness", "worst"))


class TestSummarize(unittest.TestCase):
    def test_worst_case_with_translation(self):
        inst = [
            {"id": "i1", "split": "valid", "references": [ref("red", True), ref("blue")]},
            {"id": "i1", "split": "valid", "perturbation": TR_ZH, "references": [ref("红", True), ref("红色")]},
            {"id": "i2", "split": "valid", "references": [ref("cat"), ref("dog", True)]},
            {"id": "i2", "split": "valid", "perturbation": TR_ZH, "references": [ref("猫"), ref("狗", True)]},
            {"id": "t0", "split": "train", "references": [ref("x", True)]},
        ]
        preds = [
            {"instance_id": "i1", "train_trial_index": 0, "predicted_text": "A", "mapped_output": "red"},
            {"instance_id": "i1", "train_trial_index": 0, "perturbation": TR, "predicted_text": "B",
             "mapped_output": "红色"},
            {"instance_id": "i2", "train_trial_index": 0, "predicted_text": "A", "mapped_output": "cat"},
            {"instance_id": "i2", "train_trial_index": 0, "perturbation": TR, "predicted_text": "B",
             "mapped_output": "狗"},
            {"instance_id": "i2", "train_trial_index": 1, "predicted_text": "B", "mapped_output": "dog"},
        ]
        s = g.summarize_run(preds, g.instance_map(inst, "valid"))
        c = s["counts"]
        self.assertEqual((c["n_pred"], c["other_trial"], c["scored"], c["map_checked"], c["map_agree"],
                          c["no_instance"], c["no_gold"], c["duplicate"]), (5, 1, 4, 4, 4, 0, 0, 0))
        o = s["subsets"][""]
        self.assertEqual((o["n"], o["h"], o["i"], o["unmapped"], o["under"], sum(o["over"].values())),
                         (2, 1, 1, 0, 0, 0))
        t = s["subsets"]["translate:zh-CN"]
        self.assertEqual((t["n"], t["h"], t["i"], t["over"]["prefix_only"]), (2, 2, 1, 1))
        w = s["worst"]
        # i1: min(h)=1, min(i)=0 -> over (from the Chinese copy); i2: min(h)=0, min(i)=0.
        self.assertEqual((w["n"], w["h"], w["i"], w["over"]["prefix_only"], w["under"], w["ids_without_original"]),
                         (2, 1, 0, 1, 0, 0))
        self.assertEqual(s["flips"], [{"id": "i1", "variant": "translate:zh-CN", "letter": "B",
                                       "class": "prefix_only"}])
        self.assertEqual(len(s["questions"]), 4)
        self.assertIs(g.published(s), w)
        self.assertEqual(s["examples"], [("i1", "translate:zh-CN", "B", "A", "prefix_only")])

    def test_original_only_run(self):
        inst = [
            {"id": "q1", "split": "test", "references": [ref("A", True), ref("B"), ref("Not enough information")]},
            {"id": "q2", "split": "test", "references": [ref("x", True), ref("y", True)]},
            {"id": "q4", "split": "test", "references": [ref("p", True), ref("q")]},
            {"id": "q5", "split": "test", "references": [ref("p"), ref("q", True)]},
        ]
        preds = [
            {"instance_id": "q1", "train_trial_index": 0, "predicted_text": "C",
             "mapped_output": "Not enough information"},
            {"instance_id": "q1", "train_trial_index": 0, "predicted_text": "A", "mapped_output": "A"},
            {"instance_id": "q2", "train_trial_index": 0, "predicted_text": "A", "mapped_output": "x"},
            {"instance_id": "q3", "train_trial_index": 0, "predicted_text": "A", "mapped_output": "z"},
            {"instance_id": "q4", "train_trial_index": 0, "predicted_text": "p", "mapped_output": None},
            {"instance_id": "q5", "train_trial_index": 0, "predicted_text": "B", "mapped_output": "p"},
        ]
        s = g.summarize_run(preds, g.instance_map(inst, "test"))
        c = s["counts"]
        self.assertEqual((c["n_pred"], c["no_instance"], c["no_gold"], c["duplicate"], c["scored"],
                          c["map_checked"], c["map_agree"]), (6, 1, 1, 1, 3, 3, 2))
        o = s["subsets"][""]
        self.assertEqual((o["n"], o["h"], o["i"], o["unmapped"], o["under"], o["over"]["gold_empty"]),
                         (3, 2, 1, 1, 0, 1))
        self.assertIsNone(s["worst"])
        self.assertEqual(s["flips"], [{"id": "q1", "variant": "", "letter": "C", "class": "gold_empty"}])
        self.assertIs(g.published(s), o)


class TestRanksAndVerdicts(unittest.TestCase):
    def test_ranks_tau(self):
        from fractions import Fraction as F
        self.assertEqual(g.min_ranks({"a": F(9, 10), "b": F(8, 10), "c": F(8, 10), "d": F(1, 2)}),
                         {"a": 1, "b": 2, "c": 2, "d": 4})
        self.assertAlmostEqual(g.kendall_tau_b([1, 2, 3], [3, 2, 1]), -1.0)
        self.assertAlmostEqual(g.kendall_tau_b([1, 1, 2], [1, 2, 3]), 2 / 6 ** 0.5)
        self.assertIsNone(g.kendall_tau_b([1, 1, 1], [1, 2, 3]))

    def test_verdicts(self):
        names = ("P1_reproduced", "P2_mmmu_gold_empty", "P3_translation_collisions", "P4_translation_identical",
                 "P5_overcredit_small", "P6_ranks_stable", "P7_chinese_prefix_more", "P8_format_loss")
        st = {"family_included": {"a": (99, 100), "b": (10, 10)}, "mmmu_gold_empty": 5, "tr_any": 10, "tr_q": 1000,
              "en_any": 3, "en_q": 1000, "tr_identical": 1, "pub_over": 9, "pub_credits": 1000, "movers": 0,
              "zh_prefix": 2, "es_prefix": 1, "models_unmapped_base": 3}
        self.assertEqual(g.verdicts(st), {k: True for k in names})
        st = {"family_included": {"a": (98, 100)}, "mmmu_gold_empty": 4, "tr_any": 9, "tr_q": 1000, "en_any": 0,
              "en_q": 1000, "tr_identical": 0, "pub_over": 10, "pub_credits": 1000, "movers": 1, "zh_prefix": 1,
              "es_prefix": 1, "models_unmapped_base": 2}
        self.assertEqual(g.verdicts(st), {k: False for k in names})
        st = {"family_included": {"a": (0, 0)}, "mmmu_gold_empty": 6, "tr_any": 11, "tr_q": 1000, "en_any": 4,
              "en_q": 1000, "tr_identical": 2, "pub_over": 0, "pub_credits": 0, "movers": 0, "zh_prefix": 0,
              "es_prefix": 0, "models_unmapped_base": 4}
        self.assertEqual(g.verdicts(st), dict(zip(names, (False, True, False, True, False, True, False, True))))


if __name__ == "__main__":
    unittest.main()
