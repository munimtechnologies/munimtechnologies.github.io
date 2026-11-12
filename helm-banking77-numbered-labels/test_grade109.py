"""Unit tests for grade109 (standard library only; every expectation traced by hand). Apache-2.0."""

import math
import unittest
from fractions import Fraction

import grade109 as g

L = {1: "Refund_not_showing_up", 2: "card_arrival", 3: "verify_source_of_funds"}
VSF = "verify_source_of_funds"


class TestScorer(unittest.TestCase):
    def test_normalize_text(self):
        # lower -> drop punctuation incl. '_' -> no article -> one word
        self.assertEqual(g.normalize_text("Verify_Source_of_Funds"), "verifysourceoffunds")
        # 'the' removed, whitespace collapsed
        self.assertEqual(g.normalize_text("The card arrival"), "card arrival")
        self.assertEqual(g.normalize_text("reverted_card_payment?"), "revertedcardpayment")

    def test_quasi_exact_match(self):
        self.assertEqual(g.quasi_exact_match("card_arrival", ""), 0)
        self.assertEqual(g.quasi_exact_match("card_arrival", "Card_Arrival"), 1)
        # spaces cannot be joined back: 'card arrival' != 'cardarrival'
        self.assertEqual(g.quasi_exact_match("card_arrival", "card arrival"), 0)
        self.assertEqual(g.quasi_exact_match(VSF, "71"), 0)


class TestLabels(unittest.TestCase):
    def test_parse_ok(self):
        instr = "Intro. Answer with only the label.\nPossible labels:\n1. a_b\n2. c?\n"
        self.assertEqual(g.parse_labels(instr), {1: "a_b", 2: "c?"})

    def test_parse_bad(self):
        self.assertIsNone(g.parse_labels("Possible labels:\n1. x\n3. y\n"))  # gap
        self.assertIsNone(g.parse_labels("no list here\n1. x\n"))  # no head
        self.assertIsNone(g.parse_labels("Possible labels:\n1. x\nfoo\n"))  # junk line
        self.assertIsNone(g.parse_labels("Possible labels:\n1. x\n1. y\n"))  # duplicate
        self.assertIsNone(g.parse_labels(None))
        self.assertIsNone(g.parse_labels("Possible labels:\n"))  # empty list

    def test_alnum(self):
        self.assertEqual(g.alnum("A_b c!"), "abc")
        self.assertEqual(g.alnum(None), "")

    def test_gold_of(self):
        inst = {"references": [{"output": {"text": "x"}, "tags": []}, {"output": {"text": "y"}, "tags": ["correct"]}]}
        self.assertEqual(g.gold_of(inst), "y")
        self.assertIsNone(g.gold_of({"references": [{"output": {"text": "x"}, "tags": []}]}))
        self.assertIsNone(g.gold_of(None))

    def test_cover(self):
        self.assertTrue(g.labels_cover_gold(L, ["card_arrival", "Verify_Source_of_Funds", "refund_not_showing_up"]))
        self.assertFalse(g.labels_cover_gold(L, ["card_arrival", "top_up_failed"]))


class TestClassify(unittest.TestCase):
    def c(self, pred, gold=VSF):
        return g.classify(pred, gold, L)

    def test_match(self):
        self.assertEqual(self.c("card_arrival", "card_arrival"), "match")
        self.assertEqual(self.c(" Verify_source_of_funds\n"), "match")

    def test_number_only(self):
        for p in (" 3 ", "3", "3.", "#3", "3)", "3:"):
            self.assertEqual(self.c(p), "number_gold", p)
        self.assertEqual(self.c("1", "Refund_not_showing_up"), "number_gold")
        self.assertEqual(self.c("2"), "number_other")
        self.assertEqual(self.c("99"), "number_other")

    def test_numbered(self):
        self.assertEqual(self.c("3. verify_source_of_funds"), "numbered_gold")
        self.assertEqual(self.c("3 verify source of funds"), "numbered_gold")
        self.assertEqual(self.c("3-verify_source_of_funds"), "numbered_gold")
        self.assertEqual(self.c("3.verify_source_of_funds"), "numbered_gold")
        # wrong number, gold text: not credited, gold is one word of the answer
        self.assertEqual(self.c("2. verify_source_of_funds"), "contains_gold")
        # gold number, wrong text: not credited
        self.assertEqual(self.c("3. card_arrival"), "other")

    def test_spacing(self):
        self.assertEqual(self.c("Verify Source Of Funds"), "spacing_gold")
        self.assertEqual(self.c("refund not showing up", "Refund_not_showing_up"), "spacing_gold")
        self.assertEqual(self.c("verify-source-of-funds"), "match")  # '-' is deleted like '_'
        self.assertEqual(self.c("verify-source-of funds"), "spacing_gold")  # the one space stays

    def test_rest(self):
        self.assertEqual(self.c("Label: verify_source_of_funds"), "contains_gold")
        self.assertEqual(self.c("   "), "empty")
        self.assertEqual(self.c(None), "empty")
        self.assertEqual(self.c("I cannot help"), "other")
        self.assertEqual(self.c("2023"), "other")


class TestCensus(unittest.TestCase):
    def test_summarize(self):
        gold = {"id1": "card_arrival", "id2": VSF, "id3": VSF}
        preds = [
            {"instance_id": "id1", "train_trial_index": 0, "predicted_text": "card_arrival",
             "stats": {"quasi_exact_match": 1.0}},
            {"instance_id": "id2", "train_trial_index": 0, "predicted_text": "3",
             "stats": {"quasi_exact_match": 0.0}},
            {"instance_id": "id3", "train_trial_index": 0, "predicted_text": "card_arrival",
             "stats": {"quasi_exact_match": 1.0}},  # stored 1, ours 0 -> mismatch
            {"instance_id": "idX", "train_trial_index": 0, "predicted_text": "x", "stats": {}},
            {"instance_id": "id1", "train_trial_index": 0, "predicted_text": "zzz",
             "stats": {"quasi_exact_match": 0.0}},  # duplicate
            {"instance_id": "id1", "train_trial_index": 0, "perturbation": {"name": "typo"}},
            {"instance_id": "id3", "train_trial_index": 1, "predicted_text": "", "stats": {}},
            "not a dict",
        ]
        s = g.summarize_run(preds, gold, L)
        self.assertEqual(s["counts"], {"n_records": 7, "perturbed": 1, "not_test": 1, "duplicate": 1, "kept": 4})
        self.assertEqual(s["stored_missing"], 1)
        self.assertEqual(s["recompute_mismatch"], 1)
        self.assertEqual(s["trials"][0], {"n": 3, "published": Fraction(2), "lenient": 2})
        self.assertEqual(s["trials"][1], {"n": 1, "published": Fraction(0), "lenient": 0})
        self.assertEqual(s["classes"], {"id1": "match", "id2": "number_gold", "id3": "other"})
        self.assertEqual(s["texts"]["id2"], "3")
        # mean over trials of trial means: (2/3 + 0) / 2
        self.assertEqual(g.run_mean(s["trials"], "published"), Fraction(1, 3))
        self.assertEqual(g.run_mean(s["trials"], "lenient"), Fraction(1, 3))
        self.assertIsNone(g.run_mean({}, "published"))
        cc = g.class_counts(s["classes"])
        self.assertEqual(cc["match"], 1)
        self.assertEqual(cc["number_gold"], 1)
        self.assertEqual(cc["other"], 1)
        self.assertEqual(sum(cc.values()), 3)

    def test_stat_entry(self):
        stats = [{"name": {"name": "quasi_exact_match", "split": "valid"}, "mean": 0.1},
                 {"name": {"name": "quasi_exact_match", "split": "test", "perturbation": {"x": 1}}, "mean": 0.2},
                 {"name": {"name": "quasi_exact_match", "split": "test"}, "count": 1, "sum": 327.0, "mean": 0.327}]
        self.assertEqual(g.stat_entry(stats, "quasi_exact_match"), {"count": 1, "sum": 327.0, "mean": 0.327})
        self.assertIsNone(g.stat_entry(stats, "exact_match"))

    def test_model_and_select(self):
        self.assertEqual(g.model_of("banking77:model=openai_gpt-4o-2024-05-13"), "openai_gpt-4o-2024-05-13")
        self.assertEqual(sorted(g.select_runs({"banking77:model=a": "s", "fin_qa:model=a": "s"}, "banking77:")),
                         ["banking77:model=a"])


class TestRanks(unittest.TestCase):
    def test_ranks(self):
        self.assertEqual(g.ranks_high({"a": 3, "b": 5, "c": 3}), {"a": 2, "b": 1, "c": 2})

    def test_tau(self):
        self.assertEqual(g.kendall_tau_b([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertEqual(g.kendall_tau_b([1, 2, 3], [3, 2, 1]), -1.0)
        # one x-tie, two concordant pairs: 2 / sqrt((3-1)*(3-0))
        self.assertAlmostEqual(g.kendall_tau_b([1, 1, 2], [1, 2, 3]), 2 / math.sqrt(6))
        self.assertIsNone(g.kendall_tau_b([1, 1], [1, 2]))

    def test_group_and_match(self):
        doc = [{"header": [{"value": "Model"}, {"value": "EM"}],
                "rows": [[{"value": "m1"}, {"value": 0.5}], [{"value": "m2"}, {"value": "x"}], [{"value": "m3"}]]}]
        self.assertEqual(g.group_values(doc), [0.5])
        self.assertIsNone(g.group_values([{"header": [{"value": "Model"}], "rows": []}]))
        self.assertEqual(g.match_cells({"a": 0.5, "b": 0.7}, [0.7000001, 0.5, 0.9], 1e-6), 2)
        self.assertEqual(g.match_cells({"a": 0.5, "b": 0.5}, [0.5], 1e-6), 1)


class TestVerdicts(unittest.TestCase):
    def base(self, **kw):
        s = {"test_ids": 1000, "runs_listed": 22, "runs_included": 22, "lists_ok": True, "cells_matched": 20,
             "labels_cover_gold": True, "runs_misread_2pct": 3, "pooled_n": 22000, "pooled_misread": 110,
             "max_gain": Fraction(5, 100), "tau": 0.8, "movers": 1, "leader_ok": True}
        s.update(kw)
        return g.verdicts(s)

    def test_all_held_at_boundary(self):
        self.assertEqual(set(self.base().values()), {True})

    def test_failures(self):
        self.assertFalse(self.base(cells_matched=19)["P1"])  # 190 < 198
        self.assertFalse(self.base(runs_included=19)["P1"])
        self.assertFalse(self.base(test_ids=999)["P1"])
        self.assertFalse(self.base(lists_ok=False)["P1"])
        self.assertFalse(self.base(labels_cover_gold=False)["P2"])
        self.assertFalse(self.base(runs_misread_2pct=2)["P3"])
        self.assertFalse(self.base(pooled_misread=109)["P4"])  # 21800 < 22000
        self.assertFalse(self.base(pooled_n=0)["P4"])
        self.assertFalse(self.base(max_gain=Fraction(49, 1000))["P5"])
        self.assertFalse(self.base(max_gain=None)["P5"])
        self.assertFalse(self.base(tau=0.79)["P6"])
        self.assertFalse(self.base(tau=None)["P6"])
        self.assertFalse(self.base(movers=0)["P7"])
        self.assertFalse(self.base(leader_ok=False)["P8"])

    def test_words(self):
        self.assertEqual(g.verdict_word(True), "HELD")
        self.assertEqual(g.verdict_word(False), "FAILED")
        self.assertEqual(g.verdict_word(None), "NOT GRADED")


if __name__ == "__main__":
    unittest.main()
