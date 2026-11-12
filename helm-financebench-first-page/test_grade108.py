"""Unit tests for grade108 (standard library only; every expectation traced by hand). Apache-2.0."""

import unittest
from fractions import Fraction

import grade108 as g


def ev(text, page, num, doc="D"):
    return {"evidence_text": text, "evidence_text_full_page": page, "evidence_page_num": num, "doc_name": doc}


class EvidenceClassTest(unittest.TestCase):
    def test_squash(self):
        self.assertEqual(g.squash(" a \n b\tc  "), "abc")
        self.assertEqual(g.squash(None), "")

    def test_snippet_in_own_page(self):
        self.assertTrue(g.snippet_in_own_page(ev("a  b", "xa\nby", 1)))
        self.assertFalse(g.snippet_in_own_page(ev("", "abc", 1)))
        self.assertFalse(g.snippet_in_own_page(ev("q", "abc", 1)))
        self.assertFalse(g.snippet_in_own_page(None))

    def test_single(self):
        cls, info = g.evidence_class([ev("a b", "x a b y", 1)])
        self.assertEqual(cls, "single")
        self.assertEqual(info, {"n": 1, "other_pages": 0, "missing": [], "unverifiable": []})

    def test_same_page_is_covered(self):
        cls, info = g.evidence_class([ev("a", "page one a", 1), ev("zzz", "other text", 1)])
        self.assertEqual(cls, "covered")
        self.assertEqual(info["other_pages"], 0)

    def test_same_page_text_other_number_is_covered(self):
        cls, info = g.evidence_class([ev("a", "page one a", 1), ev("zzz", "page  one\na", 7)])
        self.assertEqual(cls, "covered")
        self.assertEqual(info["other_pages"], 0)

    def test_other_page_snippet_in_given_is_covered(self):
        cls, info = g.evidence_class([ev("Income", "Income\n Statement  Revenue 10", 1),
                                      ev("Revenue  10", "p2 Revenue 10", 2)])
        self.assertEqual(cls, "covered")
        self.assertEqual(info["other_pages"], 1)

    def test_missing(self):
        cls, info = g.evidence_class([ev("Income", "Income statement", 1),
                                      ev("Balance sheet", "Balance sheet total", 2),
                                      ev("Cash flow", "Cash flow page", 3)])
        self.assertEqual(cls, "missing")
        self.assertEqual(info, {"n": 3, "other_pages": 2, "missing": [1, 2], "unverifiable": []})

    def test_other_doc_same_number_is_not_same_page(self):
        cls, info = g.evidence_class([ev("Income", "Income statement", 1),
                                      ev("Balance", "Balance sheet", 1, doc="E")])
        self.assertEqual(cls, "missing")
        self.assertEqual(info["missing"], [1])

    def test_doc_of(self):
        self.assertEqual(g.doc_of({"doc_name": "A", "evidence_doc_name": "B"}), "A")
        self.assertEqual(g.doc_of({"evidence_doc_name": "B"}), "B")
        self.assertIsNone(g.doc_of(None))
        a = {"evidence_text": "Income", "evidence_text_full_page": "Income statement", "evidence_page_num": 1,
             "evidence_doc_name": "D"}
        b = {"evidence_text": "Balance", "evidence_text_full_page": "Balance sheet", "evidence_page_num": 1,
             "evidence_doc_name": "E"}
        self.assertEqual(g.evidence_class([a, b])[0], "missing")
        b["evidence_doc_name"] = "D"
        self.assertEqual(g.evidence_class([a, b])[0], "covered")

    def test_unverifiable(self):
        cls, info = g.evidence_class([ev("a", "page a", 1), ev("abc", "xyz", 2)])
        self.assertEqual(cls, "unverifiable")
        self.assertEqual(info["unverifiable"], [1])

    def test_empty_snippet_is_unverifiable(self):
        cls, info = g.evidence_class([ev("a", "page a", 1), ev("", "abc", 2)])
        self.assertEqual(cls, "unverifiable")

    def test_missing_beats_unverifiable(self):
        cls, info = g.evidence_class([ev("a", "page a", 1), ev("abc", "xyz", 2), ev("q r", "q r s", 3)])
        self.assertEqual(cls, "missing")
        self.assertEqual(info["missing"], [2])
        self.assertEqual(info["unverifiable"], [1])

    def test_no_evidence(self):
        self.assertEqual(g.evidence_class([])[0], "no_evidence")
        self.assertEqual(g.evidence_class([None])[0], "no_evidence")
        self.assertEqual(g.evidence_class(None)[0], "no_evidence")

    def test_prompt_matches(self):
        rec = {"question": "Q?", "evidence": [{"evidence_text_full_page": "P"}, {"evidence_text_full_page": "R"}]}
        self.assertTrue(g.prompt_matches("Evidence: P\nQuestion: Q?", rec))
        self.assertFalse(g.prompt_matches("Evidence: P\nQuestion: Q? ", rec))
        self.assertFalse(g.prompt_matches("Evidence: P\nQuestion: Q?", {"question": "Q?", "evidence": []}))


def pred(iid, label, stored="absent", trial=0, pert=None):
    r = {"instance_id": iid, "train_trial_index": trial, "annotations": {"financebench": {"label": label}},
         "stats": {}}
    if stored != "absent":
        r["stats"][g.STAT_CORRECT] = stored
    if pert is not None:
        r["perturbation"] = pert
    return r


class CensusTest(unittest.TestCase):
    def setUp(self):
        self.preds = [
            pred("A", "correct_answer", 1.0),
            pred("B", "failure_to_answer", 0.0),
            pred("C", "correct_answer", 1.0),
            pred("A", "incorrect_answer", 0.0),
            pred("A", "correct_answer", 1.0, pert={"name": "x"}),
            pred("D", "weird", 0.0),
            pred("E", "incorrect_answer"),
            pred("F", "correct_answer", 0.0),
            "junk",
        ]
        self.s = g.summarize_run(self.preds, {"A", "B", "D", "E", "F"})

    def test_counts(self):
        self.assertEqual(self.s["counts"], {"n_records": 8, "perturbed": 1, "not_test": 1, "duplicate": 1,
                                            "kept": 5})
        self.assertEqual(self.s["label_bad"], 1)
        self.assertEqual(self.s["stored_missing"], 1)
        self.assertEqual(self.s["stored_mismatch"], 1)

    def test_trials_and_labels(self):
        self.assertEqual(self.s["trials"], {0: {"n": 5, "correct_answer": 2, "incorrect_answer": 1,
                                                "failure_to_answer": 1}})
        self.assertEqual(self.s["labels"], {"A": "correct_answer", "B": "failure_to_answer", "D": "weird",
                                            "E": "incorrect_answer", "F": "correct_answer"})
        self.assertEqual(g.run_mean(self.s["trials"], "correct_answer"), Fraction(2, 5))

    def test_by_class_merge_share(self):
        bc = g.by_class(self.s["labels"], {"A": "single", "B": "missing", "D": "missing", "E": "covered"})
        self.assertEqual(bc["single"], {"n": 1, "correct_answer": 1, "incorrect_answer": 0, "failure_to_answer": 0})
        self.assertEqual(bc["missing"], {"n": 2, "correct_answer": 0, "incorrect_answer": 0, "failure_to_answer": 1})
        self.assertEqual(bc["covered"], {"n": 1, "correct_answer": 0, "incorrect_answer": 1, "failure_to_answer": 0})
        m = g.merge([bc], g.COMPLETE)
        self.assertEqual(m, {"n": 2, "correct_answer": 1, "incorrect_answer": 1, "failure_to_answer": 0})
        self.assertEqual(g.share(m, "correct_answer"), Fraction(1, 2))
        self.assertIsNone(g.share({"n": 0, "correct_answer": 0}, "correct_answer"))
        self.assertEqual(g.merge([bc, bc], ("missing",))["n"], 4)

    def test_run_mean_two_trials(self):
        tr = {0: {"n": 2, "x": 1}, 1: {"n": 4, "x": 1}}
        self.assertEqual(g.run_mean(tr, "x"), Fraction(3, 8))
        self.assertIsNone(g.run_mean({}, "x"))


class TableTest(unittest.TestCase):
    def test_model_and_runs(self):
        self.assertEqual(g.model_of("financebench:model=openai_gpt-4o-2024-05-13"), "openai_gpt-4o-2024-05-13")
        self.assertEqual(g.select_runs({"financebench:model=a": "v1.0.0", "fin_qa:model=a": "v1.0.0"},
                                       "financebench:"), {"financebench:model=a": "v1.0.0"})

    def test_stat_entry(self):
        stats = [{"name": {"name": "num_instances", "split": "test", "perturbation": {"name": "p"}}, "mean": 1},
                 {"name": {"name": "num_instances", "split": "test"}, "count": 1, "sum": 140.0, "mean": 140.0}]
        self.assertEqual(g.stat_entry(stats, "num_instances"), {"count": 1, "sum": 140.0, "mean": 140.0})
        self.assertIsNone(g.stat_entry(stats, "absent"))

    def test_ranks_and_tau(self):
        self.assertEqual(g.ranks_high({"a": 3, "b": 5, "c": 5}), {"a": 3, "b": 1, "c": 1})
        self.assertAlmostEqual(g.kendall_tau_b([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertAlmostEqual(g.kendall_tau_b([1, 2, 3], [3, 2, 1]), -1.0)
        self.assertAlmostEqual(g.kendall_tau_b([1, 2, 2], [1, 2, 3]), 0.816496580927726)
        self.assertIsNone(g.kendall_tau_b([1, 1], [1, 2]))

    def test_group_values_and_match(self):
        doc = [{"header": [{"value": "Model"}, {"value": "Correct Answer"}],
                "rows": [[{"value": "m1"}, {"value": 0.7}], [{"value": "m2"}, {"value": "x"}], [{"value": "m3"}]]}]
        self.assertEqual(g.group_values(doc), [0.7])
        self.assertEqual(g.group_values(doc[0]), [0.7])
        self.assertIsNone(g.group_values([{"header": [{"value": "Model"}], "rows": []}]))
        self.assertEqual(g.match_cells({"a": 0.5, "b": 0.25}, [0.25, 0.5, 0.75], 1e-6), 2)
        self.assertEqual(g.match_cells({"a": 0.5, "b": 0.5}, [0.5], 1e-6), 1)


def base_stats():
    return {
        "test_ids": 140, "test_ids_found": 140, "prompt_ok_min": Fraction(1), "own_page_share": Fraction(9, 10),
        "runs_listed": 22, "runs_included": 22, "cells_matched": 20, "missing": 28,
        "pooled_missing": {"n": 100, "correct_answer": 30, "incorrect_answer": 50, "failure_to_answer": 20},
        "pooled_complete": {"n": 200, "correct_answer": 120, "incorrect_answer": 60, "failure_to_answer": 20},
        "runs_lower": 18,
        "metrics_missing": {"n": 10, "correct_answer": 3, "incorrect_answer": 0, "failure_to_answer": 0},
        "metrics_complete": {"n": 10, "correct_answer": 4, "incorrect_answer": 0, "failure_to_answer": 0},
        "metrics_missing_q": 10, "metrics_complete_q": 10,
        "tau": 0.8, "movers": 1, "leader_ok": True,
    }


class VerdictTest(unittest.TestCase):
    def test_all_hold_on_boundaries(self):
        v = g.verdicts(base_stats())
        self.assertEqual(v, {k: True for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8")})

    def check(self, key, value, pk, want):
        s = base_stats()
        s[key] = value
        self.assertEqual(g.verdicts(s)[pk], want, (key, value, pk))

    def test_past_boundaries(self):
        self.check("cells_matched", 19, "P1", False)
        self.check("own_page_share", Fraction(89, 100), "P1", False)
        self.check("prompt_ok_min", Fraction(94, 100), "P1", False)
        self.check("prompt_ok_min", None, "P1", False)
        self.check("test_ids", 139, "P1", False)
        self.check("runs_included", 19, "P1", False)
        self.check("runs_listed", 21, "P1", False)
        self.check("missing", 27, "P2", False)
        self.check("pooled_complete", {"n": 200, "failure_to_answer": 21}, "P3", False)
        self.check("pooled_missing", {"n": 100, "failure_to_answer": 0}, "P3", False)
        self.check("pooled_complete", {"n": 200, "failure_to_answer": 0}, "P3", True)
        self.check("runs_lower", 17, "P4", False)
        self.check("metrics_complete", {"n": 10, "correct_answer": 3}, "P5", False)
        self.check("metrics_missing_q", 9, "P5", None)
        self.check("metrics_complete_q", 9, "P5", None)
        self.check("metrics_missing", {"n": 0, "correct_answer": 0}, "P5", None)
        self.check("tau", 0.79, "P6", False)
        self.check("tau", None, "P6", False)
        self.check("movers", 0, "P7", False)
        self.check("leader_ok", False, "P8", False)

    def test_words(self):
        self.assertEqual(g.verdict_word(True), "HELD")
        self.assertEqual(g.verdict_word(False), "FAILED")
        self.assertEqual(g.verdict_word(None), "NOT GRADED")


if __name__ == "__main__":
    unittest.main()
