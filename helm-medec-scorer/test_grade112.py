"""Unit tests for grade112 (standard library only; every expectation traced by hand). Apache-2.0."""

import math
import unittest
from fractions import Fraction

import grade112 as g


class TestHelmScorer(unittest.TestCase):
    def test_gold_flag_id_keeps_the_bug(self):
        self.assertEqual(g.gold_flag_id("CORRECT"), (0, -1))
        self.assertEqual(g.gold_flag_id("CORRECT."), (0, -1))
        # int("10 Patient's history is noted") raises ValueError -> -1
        self.assertEqual(g.gold_flag_id("10 Patient's history is noted."), (1, -1))
        self.assertEqual(g.gold_flag_id("7"), (1, 7))
        self.assertEqual(g.gold_flag_id(None), (1, -1))

    def test_gold_fixed_id(self):
        self.assertEqual(g.gold_fixed_id("CORRECT"), (0, -1))
        self.assertEqual(g.gold_fixed_id("10 Patient's history is noted."), (1, 10))
        self.assertEqual(g.gold_fixed_id("3 Dose is 2.5 mg."), (1, 3))
        self.assertEqual(g.gold_fixed_id("no id here"), (1, -1))

    def test_helm_pred(self):
        self.assertEqual(g.helm_pred("CORRECT"), (0, -1))
        self.assertEqual(g.helm_pred("  CORRECT \n"), (0, -1))
        self.assertEqual(g.helm_pred("CORRECT."), (1, -2))
        self.assertEqual(g.helm_pred("correct"), (1, -2))
        self.assertEqual(g.helm_pred("7 The patient was given aspirin."), (1, 7))
        self.assertEqual(g.helm_pred("12"), (1, 12))
        self.assertEqual(g.helm_pred(""), (1, -2))
        self.assertEqual(g.helm_pred(None), (1, -2))
        self.assertEqual(g.helm_pred("**7** The patient"), (1, -2))

    def test_score(self):
        self.assertEqual(g.score((1, 7), (1, 7)), (1, 1))
        self.assertEqual(g.score((1, 7), (1, 3)), (1, 0))
        self.assertEqual(g.score((1, 7), (0, -1)), (0, 0))
        self.assertEqual(g.score((1, 7), (None, None)), (0, 0))
        self.assertEqual(g.score((0, -1), (0, -1)), (1, 1))
        self.assertEqual(g.score((0, -1), (1, -2)), (0, 0))
        self.assertEqual(g.score((0, -1), (None, None)), (0, 0))
        # HELM: an invalid answer on an error note earns flag credit, no sentence credit
        self.assertEqual(g.score((1, -1), (1, -2)), (1, 0))

    def test_bug_end_to_end(self):
        ref, pred = "7 The patient was given aspirin.", "7 The patient was given aspirin"
        self.assertEqual(g.score(g.gold_flag_id(ref), g.helm_pred(pred)), (1, 0))
        self.assertEqual(g.score(g.gold_fixed_id(ref), g.helm_pred(pred)), (1, 1))


class TestClasses(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(g.classify("CORRECT"), ("exact", None))
        self.assertEqual(g.classify(" CORRECT\n"), ("exact", None))
        self.assertEqual(g.classify("12 fixed sentence"), ("digit", 12))
        self.assertEqual(g.classify(""), ("empty", None))
        self.assertEqual(g.classify("   "), ("empty", None))
        self.assertEqual(g.classify(None), ("empty", None))
        self.assertEqual(g.classify("CORRECT."), ("correct_variant", None))
        self.assertEqual(g.classify("correct"), ("correct_variant", None))
        self.assertEqual(g.classify("**Correct**"), ("correct_variant", None))
        self.assertEqual(g.classify("CORRECT\nThe text has no errors."), ("correct_variant", None))
        self.assertEqual(g.classify("Correct. The text contains no errors."), ("correct_variant", None))
        self.assertEqual(g.classify("Sentence 4: Patient was given aspirin."), ("id_variant", 4))
        self.assertEqual(g.classify("**4** The patient"), ("id_variant", 4))
        self.assertEqual(g.classify("Sentence ID: 9 x"), ("id_variant", 9))
        self.assertEqual(g.classify("(5) x"), ("id_variant", 5))
        self.assertEqual(g.classify("Correction: 5 x"), ("other", None))
        self.assertEqual(g.classify("The text is correct."), ("other", None))
        self.assertEqual(g.classify("Identified error in sentence 3"), ("other", None))
        self.assertEqual(g.classify("Correct sentence 3 is fine"), ("other", None))
        self.assertEqual(g.classify("Incorrect"), ("other", None))

    def test_classes_partition_helm_invalid(self):
        for p in ("CORRECT", "3 x", "", "CORRECT.", "**3** x", "prose"):
            c, _ = g.classify(p)
            self.assertEqual(c in g.INVALID, g.helm_pred(p)[1] == -2, p)

    def test_lenient_pred(self):
        self.assertEqual(g.lenient_pred("CORRECT"), (0, -1))
        self.assertEqual(g.lenient_pred("CORRECT."), (0, -1))
        self.assertEqual(g.lenient_pred("Sentence 4: x"), (1, 4))
        self.assertEqual(g.lenient_pred("5 x"), (1, 5))
        self.assertEqual(g.lenient_pred(""), (None, None))
        self.assertEqual(g.lenient_pred("hmm"), (None, None))

    def test_long_digit_string(self):
        self.assertEqual(g.helm_pred("9" * 6000)[0], 1)
        self.assertEqual(g.classify("9" * 6000)[0], "digit")


def _rec(iid, text, flag, sent, t=0, pert=None):
    r = {"instance_id": iid, "train_trial_index": t, "predicted_text": text,
         "stats": {g.FLAG: flag, g.SENT: sent}}
    if pert is not None:
        r["perturbation"] = pert
    return r


REFS = {"id0": "CORRECT", "id1": "3 Fixed sentence.", "id2": "5 Other fix.", "id3": "CORRECT"}


class TestCensus(unittest.TestCase):
    def preds(self):
        return [
            _rec("id0", "CORRECT", 1.0, 1.0),
            _rec("id1", "3 Fixed sentence", 1.0, 0.0),
            _rec("id2", "", 1.0, 0.0),
            _rec("id3", "CORRECT.", 0.0, 0.0),
            _rec("id0", "CORRECT", 1.0, 1.0, pert={"name": "typo"}),
            _rec("id9", "CORRECT", 1.0, 1.0),
            _rec("id0", "4 dup", 0.0, 0.0),
            "not a dict",
        ]

    def test_summarize_run(self):
        s = g.summarize_run(self.preds(), REFS)
        self.assertEqual(s["counts"], {"n_records": 7, "perturbed": 1, "not_test": 1, "duplicate": 1, "kept": 4})
        self.assertEqual((s["stored_missing"], s["flag_mismatch"], s["sent_mismatch"]), (0, 0, 0))
        self.assertEqual((s["error_notes"], s["err_sent_credit"], s["tn"], s["invalid_flag_credit"]), (2, 0, 1, 1))
        self.assertEqual(s["classes"], {"id0": "exact", "id1": "digit", "id2": "empty", "id3": "correct_variant"})
        self.assertEqual(s["golds"]["id1"], (1, 3))
        tr = s["trials"]
        self.assertEqual(g.run_mean(tr, "pub_flag"), Fraction(3, 4))
        self.assertEqual(g.run_mean(tr, "pub_sent"), Fraction(1, 4))
        self.assertEqual(g.run_mean(tr, "fixed_sent"), Fraction(1, 2))
        self.assertEqual(g.run_mean(tr, "noinv_flag"), Fraction(1, 2))
        self.assertEqual(g.run_mean(tr, "noinv_sent"), Fraction(1, 2))
        self.assertEqual(g.run_mean(tr, "len_flag"), Fraction(3, 4))
        self.assertEqual(g.run_mean(tr, "len_sent"), Fraction(3, 4))
        self.assertEqual(g.class_counts(s["classes"]),
                         {"exact": 1, "digit": 1, "correct_variant": 1, "id_variant": 0, "empty": 1, "other": 0})

    def test_mismatch_and_missing(self):
        preds = [_rec("id0", "CORRECT", 0.0, 1.0), _rec("id1", "3 x", 1.0, 1.0),
                 {"instance_id": "id2", "predicted_text": "", "stats": {}}]
        s = g.summarize_run(preds, REFS)
        self.assertEqual(s["flag_mismatch"], 1)
        self.assertEqual(s["sent_mismatch"], 1)
        self.assertEqual(s["stored_missing"], 2)
        self.assertEqual(s["err_sent_credit"], 1)

    def test_two_trials(self):
        preds = [_rec("id0", "CORRECT", 1.0, 1.0, t=0), _rec("id0", "1 x", 0.0, 0.0, t=1)]
        s = g.summarize_run(preds, {"id0": "CORRECT"})
        self.assertEqual(g.run_mean(s["trials"], "pub_flag"), Fraction(1, 2))
        self.assertEqual(s["classes"], {"id0": "exact"})
        self.assertIsNone(g.run_mean({}, "pub_flag"))


class TestHelpers(unittest.TestCase):
    def test_model_and_select(self):
        run = "medec:num_output_tokens=4000,model=openai_o3-mini-2025-01-31,model_deployment=x_o3"
        self.assertEqual(g.model_of(run), "openai_o3-mini-2025-01-31")
        self.assertEqual(sorted(g.select_runs({run: "v4.0.0", "medcalc_bench:model=a": "v4.0.0"}, "medec:")), [run])

    def test_stat_entry(self):
        stats = [{"name": {"name": g.FLAG, "split": "test"}, "count": 1, "sum": 0.5, "mean": 0.5},
                 {"name": {"name": g.FLAG, "split": "test", "perturbation": {"name": "x"}}, "count": 0, "sum": 0}]
        self.assertEqual(g.stat_entry(stats, g.FLAG), {"count": 1, "sum": 0.5, "mean": 0.5})
        self.assertIsNone(g.stat_entry(stats, g.SENT))

    def test_gold_of(self):
        inst = {"references": [{"output": {"text": "x"}, "tags": []}, {"output": {"text": "CORRECT"},
                                                                       "tags": ["correct"]}]}
        self.assertEqual(g.gold_of(inst), "CORRECT")
        self.assertIsNone(g.gold_of({"references": []}))

    def test_ranks_and_tau(self):
        self.assertEqual(g.ranks_high({"a": 3, "b": 5, "c": 5}), {"a": 3, "b": 1, "c": 1})
        self.assertAlmostEqual(g.kendall_tau_b([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertAlmostEqual(g.kendall_tau_b([1, 2, 3], [3, 2, 1]), -1.0)
        self.assertAlmostEqual(g.kendall_tau_b([1, 1, 2], [1, 2, 3]), 2 / math.sqrt(6))
        self.assertIsNone(g.kendall_tau_b([1, 1], [1, 2]))

    def test_group_and_cells(self):
        doc = [{"header": [{"value": "Model"}, {"value": "MedecFlagAcc"}],
                "rows": [[{"value": "A"}, {"value": 0.5}], [{"value": "B"}, {"value": 0.6}]]}]
        self.assertEqual(g.group_values(doc), [0.5, 0.6])
        self.assertIsNone(g.group_values([{"header": [{"value": "EM"}], "rows": []}]))
        self.assertEqual(g.match_cells({"a": 0.5, "b": 0.6000001}, [0.6, 0.5], 1e-6), 2)
        self.assertEqual(g.match_cells({"a": 0.5, "b": 0.5}, [0.5], 1e-6), 1)


def _stats(**kw):
    s = {"test_ids": 597, "runs_listed": 13, "runs_included": 12, "cells_matched": 11, "sent_rise10": 8,
         "max_fixed_sent": Fraction(2, 5), "pooled_n": 100, "pooled_invalid": 5, "runs_invalid20": 1,
         "max_noinv_drop": Fraction(1, 20), "movers_len": 1, "leader_ok_len": True}
    s.update(kw)
    return s


class TestVerdicts(unittest.TestCase):
    def test_all_held_on_boundaries(self):
        v = g.verdicts(_stats())
        self.assertEqual(v, {k: True for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8")})

    def test_each_fails_past_boundary(self):
        cases = {"P1": dict(cells_matched=10), "P2": dict(sent_rise10=7), "P3": dict(max_fixed_sent=Fraction(39, 100)),
                 "P4": dict(pooled_invalid=4), "P5": dict(runs_invalid20=0), "P6": dict(max_noinv_drop=Fraction(4, 100)),
                 "P7": dict(movers_len=0), "P8": dict(leader_ok_len=False)}
        for p, kw in cases.items():
            v = g.verdicts(_stats(**kw))
            self.assertFalse(v[p], p)
            self.assertEqual(sum(1 for x in v.values() if not x), 1, p)

    def test_p1_other_parts_and_none(self):
        self.assertFalse(g.verdicts(_stats(test_ids=596))["P1"])
        self.assertFalse(g.verdicts(_stats(runs_listed=12))["P1"])
        self.assertFalse(g.verdicts(_stats(runs_included=11, cells_matched=11))["P1"])
        v = g.verdicts(_stats(max_fixed_sent=None, max_noinv_drop=None, pooled_n=0, pooled_invalid=0))
        self.assertFalse(v["P3"])
        self.assertFalse(v["P6"])
        self.assertFalse(v["P4"])
        self.assertEqual(g.verdict_word(None), "NOT GRADED")


if __name__ == "__main__":
    unittest.main()
