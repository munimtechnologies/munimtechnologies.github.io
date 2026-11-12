"""Unit tests for audit 107 (standard library only; FinQA's helper and sympy are not needed here). Apache-2.0.

Every expectation below was traced by hand from the code in grade107.py before any data was read.
"""

import unittest
from fractions import Fraction

import grade107 as g


class NormText(unittest.TestCase):
    def test_hyphen_and_none(self):
        # hyphen renamed; the row name has no comma, so ', none' is added after the rename
        self.assertEqual(g.norm_text("table-average(sales)"), "table_average(sales, none)")
        self.assertEqual(g.norm_text("table-max(net revenue, none)"), "table_max(net revenue, none)")
        self.assertEqual(g.norm_text("table_sum(total)"), "table_sum(total, none)")

    def test_single_fixes(self):
        # hyphen only: no 'none' added; none only: a hyphenated op is not touched (ONEARG_RE needs the underscore)
        self.assertEqual(g.norm_text("table-average(sales)", True, False), "table_average(sales)")
        self.assertEqual(g.norm_text("table-average(sales)", False, True), "table-average(sales)")
        self.assertEqual(g.norm_text("table_min(cost)", False, True), "table_min(cost, none)")

    def test_unchanged(self):
        self.assertEqual(g.norm_text("  divide(1, 2) \n"), "divide(1, 2)")
        self.assertEqual(g.norm_text("subtract(5829, 5735), divide(#0, 5735)"),
                         "subtract(5829, 5735), divide(#0, 5735)")
        self.assertEqual(g.norm_text("subtable-max(x)"), "subtable-max(x)")  # no word boundary before 'table'
        self.assertEqual(g.norm_text(None), "")


class Numbers(unittest.TestCase):
    def test_to_number(self):
        self.assertEqual(g.to_number("5,829"), 5829.0)
        self.assertAlmostEqual(g.to_number("14.1%"), 0.141)
        self.assertEqual(g.to_number("const_100"), 100.0)
        self.assertEqual(g.to_number("const_m1"), -1.0)
        self.assertEqual(g.to_number("$ 12.5"), 12.5)
        self.assertIsNone(g.to_number("#0"))
        self.assertIsNone(g.to_number("abc"))
        self.assertIsNone(g.to_number("const_x"))
        self.assertIsNone(g.to_number(""))

    def test_canon_arg(self):
        self.assertEqual(g.canon_arg("const_100"), "100")
        self.assertEqual(g.canon_arg("100"), "100")
        self.assertEqual(g.canon_arg("5735.0"), "5735")
        self.assertEqual(g.canon_arg("14.1%"), "0.141")
        self.assertEqual(g.canon_arg("#0"), "#0")
        self.assertEqual(g.canon_arg("none"), "none")
        self.assertEqual(g.canon_arg("abc"), "abc")
        self.assertEqual(g.canon_arg("const_100", "number"), "const_100")
        self.assertEqual(g.canon_arg("5,829", "const"), "5,829")
        self.assertEqual(g.canon_arg("5,829", "number"), "5829")
        self.assertEqual(g.canon_arg("5735", "all", None), "5735.0")


class Tokens(unittest.TestCase):
    T = ["subtract(", "5,829", "const_100", ")", "divide(", "#0", "5735.0", ")", "EOF"]

    def test_all(self):
        self.assertEqual(g.norm_tokens(self.T),
                         ["subtract(", "5829", "100", ")", "divide(", "#0", "5735", ")", "EOF"])

    def test_modes(self):
        self.assertEqual(g.norm_tokens(self.T, "const"),
                         ["subtract(", "5,829", "100", ")", "divide(", "#0", "5735.0", ")", "EOF"])
        self.assertEqual(g.norm_tokens(self.T, "number"),
                         ["subtract(", "5829", "const_100", ")", "divide(", "#0", "5735", ")", "EOF"])
        self.assertEqual(g.norm_tokens(self.T, None), self.T)

    def test_table_and_malformed(self):
        t = ["table_max(", "2019", "none", ")", "EOF"]
        self.assertEqual(g.norm_tokens(t), t)  # row names are never touched
        bad = ["divide(", "1", ")", "EOF"]
        self.assertEqual(g.norm_tokens(bad), bad)  # 3 body tokens: not whole steps

    def test_up_class(self):
        self.assertEqual(g.up_class({"table_name": False, "table_none": False, "const": True, "number_form": True}),
                         "const")
        self.assertEqual(g.up_class({"table_name": True}), "table_name")
        self.assertEqual(g.up_class({}), "combined")


FAKE = {
    "p1": dict(pa=1, ea=1, anpa=1, anea=1, cls=None, hyphen=False, onearg=False, invalid=False, err=False),
    "p2": dict(pa=0, ea=1, anpa=1, anea=1, cls="const", hyphen=False, onearg=False, invalid=False, err=False),
    "p3": dict(pa=0, ea=0, anpa=1, anea=1, cls="table_name", hyphen=True, onearg=False, invalid=True, err=False),
}


def fake_grade(prog, exe, table, iid, pred):
    return FAKE[pred]


def refs(n=3):
    return [{"output": {"text": "x"}, "tags": []} for _ in range(n)]


INSTANCES = [
    {"id": "id1", "split": "test", "references": refs()},
    {"id": "id2", "split": "test", "references": refs()},
    {"id": "id3", "split": "test", "references": refs()},
    {"id": "id9", "split": "train", "references": refs()},
]
PREDS = [
    {"instance_id": "id1", "train_trial_index": 0, "predicted_text": "p1", "stats": {"program_accuracy": 1.0}},
    {"instance_id": "id2", "train_trial_index": 0, "predicted_text": "p2", "stats": {"program_accuracy": 0.0}},
    {"instance_id": "id3", "train_trial_index": 0, "predicted_text": "p3", "stats": {"program_accuracy": 1.0}},
    {"instance_id": "id1", "train_trial_index": 0, "predicted_text": "p2", "stats": {"program_accuracy": 0.0}},
    {"instance_id": "id9", "train_trial_index": 0, "predicted_text": "p1", "stats": {"program_accuracy": 1.0}},
    {"instance_id": "id2", "train_trial_index": 0, "predicted_text": "p1", "perturbation": {"name": "x"}},
]


def ea_stat(v):
    return {"name": {"name": "execution_accuracy", "split": "test"}, "count": 1, "sum": v, "mean": v}


PIS = [
    {"instance_id": "id1", "train_trial_index": 0, "stats": [ea_stat(1.0)]},
    {"instance_id": "id2", "train_trial_index": 0, "stats": [ea_stat(1.0)]},
    {"instance_id": "id3", "train_trial_index": 0, "stats": []},
]


class Census(unittest.TestCase):
    def test_summary(self):
        s = g.summarize_run(INSTANCES, PREDS, PIS, fake_grade)
        self.assertEqual(s["counts"], {"n_records": 6, "perturbed": 1, "not_test": 1, "duplicate": 1, "kept": 3})
        self.assertEqual(s["trials"], {0: {"n": 3, "pa": 1, "ea": 2, "anpa": 3, "anea": 3}})
        self.assertEqual((s["up"], s["down"], s["exec_only"]), (2, 0, 0))
        self.assertEqual(s["classes"], {"table_name": 1, "table_none": 0, "const": 1, "number_form": 0,
                                        "combined": 0})
        self.assertEqual(s["keys"]["const"], [("id2", 0)])
        self.assertEqual(s["keys"]["table_name"], [("id3", 0)])
        self.assertEqual((s["hyphen"], s["onearg"], s["invalid"], s["errors"]), (1, 0, 1, 0))
        self.assertEqual((s["pa_missing"], s["pa_mismatch"], s["ea_missing"], s["ea_mismatch"]), (0, 1, 1, 0))
        self.assertEqual((s["anea_up"], s["anea_down"]), (1, 0))
        self.assertEqual(g.run_mean(s["trials"], "pa"), Fraction(1, 3))
        self.assertEqual(g.run_mean(s["trials"], "anpa"), Fraction(1, 1))

    def test_stored_exec(self):
        self.assertEqual(g.stored_exec(PIS), {("id1", 0): 1.0, ("id2", 0): 1.0})


class Tables(unittest.TestCase):
    TABLE = {"header": [{"value": "Model"}, {"value": "Program Accuracy"}, {"value": "# eval"}],
             "rows": [[{"value": "A"}, {"value": 0.5}, {"value": 1000}],
                      [{"value": "B"}, {"value": 0.25}, {"value": 1000}],
                      [{"value": "C"}, {"value": None}, {}]]}

    def test_group_values(self):
        self.assertEqual(g.group_values([self.TABLE]), [0.5, 0.25])
        self.assertEqual(g.group_values(self.TABLE), [0.5, 0.25])
        self.assertIsNone(g.group_values([{"header": [{"value": "EM"}], "rows": []}]))

    def test_match_ranks_tau(self):
        self.assertEqual(g.match_cells({"r1": 0.5, "r2": 0.25, "r3": 0.75}, [0.25, 0.5], 1e-6), 2)
        self.assertEqual(g.ranks_high({"a": 3, "b": 1, "c": 3}), {"a": 1, "b": 3, "c": 1})
        self.assertEqual(g.kendall_tau_b([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertEqual(g.kendall_tau_b([1, 2, 3], [3, 2, 1]), -1.0)
        self.assertAlmostEqual(g.kendall_tau_b([1, 1, 2], [1, 2, 3]), 2 / 6 ** 0.5)
        self.assertIsNone(g.kendall_tau_b([1, 1], [1, 2]))

    def test_names(self):
        self.assertEqual(g.model_of("fin_qa:model=openai_gpt-4o-2024-05-13"), "openai_gpt-4o-2024-05-13")
        self.assertEqual(g.select_runs({"fin_qa:model=a": "v1.0.0", "banking77:model=a": "v1.0.0"}, "fin_qa:"),
                         {"fin_qa:model=a": "v1.0.0"})
        self.assertIsNone(g.pick([], "x"))
        self.assertEqual(g.pick([("id1", 0)], "x"), ("id1", 0))


ON = dict(fixtures=True, runs_listed=22, runs_included=20, cells_matched=18, records=20000, up=200,
          up_classes={"table_name": 4, "table_none": 0, "const": 5, "number_form": 4, "combined": 0},
          hyphen=20, max_rise=Fraction(1, 50), tau=0.85, leader_ok=True, ea_gap_runs=10)
PAST = dict(fixtures=True, runs_listed=21, runs_included=19, cells_matched=17, records=20000, up=199,
            up_classes={"table_name": 4, "table_none": 0, "const": 4, "number_form": 1, "combined": 0},
            hyphen=19, max_rise=Fraction(19, 1000), tau=0.849, leader_ok=False, ea_gap_runs=9)


class Verdicts(unittest.TestCase):
    def test_on_boundary_all_hold(self):
        v = g.verdicts(ON)
        self.assertEqual(sorted(v), ["P%d" % i for i in range(1, 9)])
        self.assertTrue(all(v.values()), v)

    def test_past_boundary_all_fail(self):
        v = g.verdicts(PAST)
        self.assertFalse(any(v.values()), v)

    def test_no_up(self):
        v = g.verdicts(dict(ON, up=0, up_classes={c: 0 for c in g.UP_CLASSES}, max_rise=None, tau=None))
        self.assertFalse(v["P2"] or v["P3"] or v["P5"] or v["P6"])


if __name__ == "__main__":
    unittest.main()
