"""Unit tests for audit 113 (standard library only; every expectation traced by hand). Apache-2.0."""

import sqlite3
import unittest
from fractions import Fraction

import grade113 as g


def _db():
    conn = sqlite3.connect(":memory:")
    conn.execute("create table t (a integer, b text)")
    conn.executemany("insert into t values (?, ?)", [(1, "x"), (2, "y"), (2, "y")])
    return conn


class HelmScorer(unittest.TestCase):
    def test_rows_match_as_sets(self):
        self.assertEqual(g.helm_exec_acc("select a", "select a", [[2], [1]], [[1], [2]]), 1)
        self.assertEqual(g.helm_exec_acc("select a", "select a", [[1]], [[1], [1]]), 1)  # set: duplicates ignored
        self.assertEqual(g.helm_exec_acc("select a", "select a", [[1]], [[2]]), 0)

    def test_slot_gold_can_never_match(self):
        slot = ["000-00000", "lab"]
        self.assertEqual(g.helm_exec_acc("q", "gold q", slot, [["000-00000"]]), 0)
        self.assertEqual(g.helm_exec_acc("q", "gold q", slot, [["000-00000", "lab"]]), 0)
        self.assertEqual(g.helm_exec_acc("q", "gold q", slot, [["000-00000"], ["lab"]]), 0)

    def test_empty_gold(self):
        self.assertEqual(g.helm_exec_acc("", "null", [], []), 1)  # abstention credited
        self.assertEqual(g.helm_exec_acc("  ", "null", [], []), 1)
        self.assertEqual(g.helm_exec_acc("select a from t where 0", "select a", [], []), 0)  # right empty result: 0
        self.assertEqual(g.helm_exec_acc("", "", [], []), 0)  # no gold query at all

    def test_validity(self):
        self.assertEqual(g.helm_validity("", None), 0)
        self.assertEqual(g.helm_validity("select 1", None), 1)
        self.assertEqual(g.helm_validity("select 1", "no such table"), 0)

    def test_extract_sql(self):
        self.assertEqual(g.helm_extract_sql("<sql> SELECT 1 </sql>"), "SELECT 1")
        self.assertEqual(g.helm_extract_sql("<SQL>select 2<sql>"), "select 2")
        self.assertEqual(g.helm_extract_sql("```sql\nSELECT 1;\n```"), "SELECT 1;")
        self.assertEqual(g.helm_extract_sql(""), "")
        self.assertEqual(g.helm_extract_sql("``` ```"), "")


class Classes(unittest.TestCase):
    def test_gold_class(self):
        self.assertEqual(g.gold_class([], {"a": "1"}), "empty")
        self.assertEqual(g.gold_class([[0]], {}), "rows")
        self.assertEqual(g.gold_class(["000-00000", "lab"], {"patient_id": "000-00000", "lab_name": "lab"}), "slot")
        self.assertEqual(g.gold_class(["lab", "000-00000"], {"patient_id": "000-00000", "lab_name": "lab"}), "other")
        self.assertEqual(g.gold_class([[1], "a"], {"x": "a"}), "other")

    def test_pred_class(self):
        self.assertEqual(g.pred_class("  ", None, []), "abstain")
        self.assertEqual(g.pred_class("select", "err", []), "error")
        self.assertEqual(g.pred_class("select", None, [[1]]), "rows")
        self.assertEqual(g.pred_class("select", None, []), "empty_result")

    def test_impossible(self):
        self.assertTrue(g.is_impossible({"gq": "null", "impossible": False}))
        self.assertTrue(g.is_impossible({"gq": "select 1", "impossible": True}))
        self.assertFalse(g.is_impossible({"gq": "select 1", "impossible": False}))


class Official(unittest.TestCase):
    def test_time_anchor_and_formats(self):
        q = "select 1 where datetime(x) >= datetime(current_time,'-1 year') and strftime('%y',x) = '2105'"
        self.assertEqual(g.official_sql(q), "select 1 where datetime(x) >= datetime('2105-12-31 23:59:00','-1 year') "
                                            "and strftime('%Y',x) = '2105'")
        self.assertEqual(g.official_sql("select datetime('now')"), "select datetime('2105-12-31 23:59:00')")
        self.assertEqual(g.official_sql("SELECT A FROM T WHERE B = 'PTT'"), "select a from t where b = 'ptt'")
        self.assertEqual(g.official_sql("select 1 where a < = 2 and b = ''x''"), "select 1 where a <= 2 and b = 'x'")

    def test_vitals(self):
        q = "select 1 where v.heartrate between heart_rate_lower and heart_rate_upper"
        self.assertEqual(g.official_sql(q), "select 1 where v.heartrate between 60.0 and 100.0")
        q2 = "select 1 where v.x between foo_lower and foo_upper"  # unknown vital: unchanged
        self.assertEqual(g.official_sql(q2), q2)

    def test_key(self):
        self.assertEqual(g.official_key([(2,), (1,)]), "['(1,)', '(2,)']")
        self.assertEqual(g.official_key([]), "[]")
        self.assertNotEqual(g.official_key([(1,), (1,)]), g.official_key([(1,)]))  # duplicates count

    def test_execute(self):
        conn = _db()
        self.assertEqual(g.execute(conn, "select a from t where a = 1"), ("rows", [(1,)]))
        self.assertEqual(g.execute(conn, "select a from t where a > 5"), ("empty", []))
        cls, msg = g.execute(conn, "select nope from t")
        self.assertEqual(cls, "error")
        self.assertTrue(msg.startswith("OperationalError"))

    def test_execute_timeout(self):
        conn = sqlite3.connect(":memory:")
        q = ("with recursive c(x) as (select 1 union all select x + 1 from c) select count(*) from c")
        cls, _ = g.execute(conn, q, limit_s=0.2)
        self.assertEqual(cls, "timeout")
        self.assertEqual(g.execute(conn, "select 1"), ("rows", [(1,)]))  # handler removed afterwards


class Rescores(unittest.TestCase):
    ANS = {"gq": "select a", "value": {"p": "x"}, "impossible": False}
    IMP = {"gq": "null", "value": {}, "impossible": True}

    def test_fixed(self):
        self.assertEqual(g.fixed_acc(self.IMP, "", None, [], ("error", "e")), 1)
        self.assertEqual(g.fixed_acc(self.IMP, "select 1", None, [[1]], ("error", "e")), 0)
        self.assertEqual(g.fixed_acc(self.ANS, "", "No query generated", [], ("empty", [])), 0)
        self.assertEqual(g.fixed_acc(self.ANS, "select 1", "err", [], ("empty", [])), 0)
        self.assertEqual(g.fixed_acc(self.ANS, "select 1", None, [[1]], ("rows", [[1]])), 1)
        self.assertEqual(g.fixed_acc(self.ANS, "select 1", None, [], ("empty", [])), 1)
        self.assertEqual(g.fixed_acc(self.ANS, "select 1", None, [[1]], ("empty", [])), 0)
        self.assertEqual(g.fixed_acc(self.ANS, "select 1", None, [], ("error", "e")), 0)

    def test_official(self):
        conn = _db()

        def ex(sql):
            return g.execute(conn, sql)
        gold_y = ("rows", [(2, "y"), (2, "y")])
        self.assertEqual(g.official_acc(self.ANS, "SELECT * FROM T WHERE B = 'Y'", gold_y, ex), 1)
        self.assertEqual(g.official_acc(self.ANS, "select distinct * from t where b = 'y'", gold_y, ex), 0)
        self.assertEqual(g.official_acc(self.ANS, "select * from t where a > 9", ("empty", []), ex), 1)
        self.assertEqual(g.official_acc(self.ANS, "", ("empty", []), ex), 0)
        self.assertEqual(g.official_acc(self.ANS, "select nope", ("empty", []), ex), 0)
        self.assertEqual(g.official_acc(self.ANS, "select 1", ("error", "e"), ex), 0)
        self.assertEqual(g.official_acc(self.IMP, "", ("error", "e"), ex), 1)
        self.assertEqual(g.official_acc(self.IMP, "NULL", ("error", "e"), ex), 1)
        self.assertEqual(g.official_acc(self.IMP, "select 1", ("error", "e"), ex), 0)


def _rec(iid, pred, gt, pr, qe, acc, val, t=0, pert=None, ann=True):
    r = {"instance_id": iid, "train_trial_index": t, "predicted_text": pred, "stats": {g.ACC: acc, g.VAL: val}}
    if ann:
        r["annotations"] = {"ehr_sql": {"predicted_result": pr, "ground_truth_result": gt, "query_error": qe}}
    if pert is not None:
        r["perturbation"] = pert
    return r


class Census(unittest.TestCase):
    def test_summarize(self):
        conn = _db()

        def ex(sql):
            return g.execute(conn, sql)
        info = {
            "i1": {"gq": "select a from t where a = 1", "value": {"p": "x"}, "impossible": False},  # rows gold
            "i2": {"gq": "select a from t where a = 9", "value": {"p": "x", "l": "y"}, "impossible": False},  # slot
            "i3": {"gq": "null", "value": {}, "impossible": True},
            "i4": {"gq": "select a from t where a = 2", "value": {"p": "z"}, "impossible": False},
        }
        gold_raw = {"i1": ("rows", [(1,)]), "i2": ("empty", []), "i3": ("error", "e"), "i4": ("rows", [(2,), (2,)])}
        gold_off = dict(gold_raw)
        preds = [
            _rec("i1", "select a from t where a = 1", [[1]], [[1]], None, 1, 1),  # credit, fixed 1, official 1
            _rec("i2", "select a from t where a = 7", ["x", "y"], [], None, 0, 1),  # slot; fixed 1; official 1
            _rec("i3", "", [], [], "No query generated", 1, 0),  # abstain credit
            _rec("i4", "select nope", [[2], [2]], [], "no such column", 0, 0),  # error
            _rec("i1", "dup", [[1]], [[1]], None, 1, 1),  # duplicate
            _rec("i1", "p", [[1]], [[1]], None, 1, 1, pert={"name": "typo"}),  # perturbed
            _rec("zz", "x", [], [], None, 0, 0),  # not test
        ]
        s = g.summarize_run(preds, info, gold_raw, gold_off, ex)
        self.assertEqual(s["counts"], {"n_records": 7, "perturbed": 1, "not_test": 1, "duplicate": 1, "kept": 4,
                                       "no_annotation": 0})
        self.assertEqual((s["acc_mismatch"], s["val_mismatch"], s["stored_missing"]), (0, 0, 0))
        self.assertEqual((s["credit"], s["abstain_credit"], s["slot_credit"]), (2, 1, 0))
        self.assertEqual((s["valid_answerable"], s["valid_answerable_empty"]), (2, 1))
        self.assertEqual(s["gclass"], {"i1": "rows", "i2": "slot", "i3": "empty", "i4": "rows"})
        self.assertEqual(s["pclass"], {"i1": "rows", "i2": "empty_result", "i3": "abstain", "i4": "error"})
        tr = s["trials"][0]
        self.assertEqual(tr["n"], 4)
        self.assertEqual((tr["pub"], tr["sql_only"], tr["fixed"], tr["official"]), (2, 1, 3, 3))
        self.assertEqual(g.run_mean(s["trials"], "pub"), Fraction(1, 2))
        self.assertEqual(g.run_mean(s["trials"], "fixed"), Fraction(3, 4))

    def test_mismatch_and_missing(self):
        info = {"i1": {"gq": "select 1", "value": {}, "impossible": False}}
        s = g.summarize_run([_rec("i1", "select 1", [[1]], [[1]], None, 0, 0)], info, {}, {}, lambda q: ("empty", []))
        self.assertEqual((s["acc_mismatch"], s["val_mismatch"]), (1, 1))
        s2 = g.summarize_run([_rec("i1", "select 1", [], [], None, None, None, ann=False)], info, {}, {},
                             lambda q: ("empty", []))
        self.assertEqual((s2["stored_missing"], s2["counts"]["no_annotation"]), (1, 1))

    def test_two_trials(self):
        info = {"i1": {"gq": "null", "value": {}, "impossible": True}}
        preds = [_rec("i1", "", [], [], "No query generated", 1, 0, t=0),
                 _rec("i1", "select 1", [], [[1]], None, 0, 1, t=1)]
        s = g.summarize_run(preds, info, {}, {}, lambda q: ("rows", [(1,)]))
        self.assertEqual(g.run_mean(s["trials"], "pub"), Fraction(1, 2))
        self.assertEqual(g.run_mean(s["trials"], "sql_only"), 0)


class Helpers(unittest.TestCase):
    def test_info_of(self):
        inst = {"id": "id1", "split": "test", "references": [{"output": {"text": " null "}, "tags": ["correct"]}],
                "extra_data": {"db_path": "eicu.sqlite", "value": {}, "is_impossible": True}}
        self.assertEqual(g.info_of(inst), {"gq": "null", "value": {}, "impossible": True})
        self.assertEqual(g.info_of({}), {"gq": "", "value": {}, "impossible": False})

    def test_release(self):
        run = "ehr_sql:model=openai_gpt-4o-2024-05-13,model_deployment=stanfordhealthcare_gpt-4o-2024-05-13"
        self.assertEqual(g.model_of(run), "openai_gpt-4o-2024-05-13")
        self.assertEqual(sorted(g.select_runs({run: "s", "ehrshot:x": "s"}, "ehr_sql:")), [run])

    def test_stat_entry(self):
        stats = [{"name": {"name": g.ACC, "split": "test", "perturbation": {"name": "r"}}, "mean": 9},
                 {"name": {"name": g.ACC, "split": "test"}, "count": 1, "sum": 0.32, "mean": 0.32}]
        self.assertEqual(g.stat_entry(stats, g.ACC), {"count": 1, "sum": 0.32, "mean": 0.32})
        self.assertIsNone(g.stat_entry(stats, g.VAL))

    def test_ranks_tau(self):
        self.assertEqual(g.ranks_high({"a": 3, "b": 1, "c": 3}), {"a": 1, "b": 3, "c": 1})
        self.assertAlmostEqual(g.kendall_tau_b([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertAlmostEqual(g.kendall_tau_b([1, 2, 3], [3, 2, 1]), -1.0)
        self.assertIsNone(g.kendall_tau_b([1, 1], [1, 2]))

    def test_group(self):
        doc = [{"header": [{"value": "Model"}, {"value": "EHRSQLExeAcc"}],
                "rows": [[{"value": "A"}, {"value": 0.32}], [{"value": "B"}, {"value": "-"}]]}]
        self.assertEqual(g.group_values(doc), [0.32])
        self.assertIsNone(g.group_values([{"header": [{"value": "X"}]}]))
        self.assertEqual(g.match_cells({"a": 0.3200000001, "b": 0.5}, [0.32, 0.6], 1e-6), 1)

    def test_class_counts(self):
        self.assertEqual(g.class_counts({"a": "rows", "b": "rows"}, g.GOLD_CLASSES),
                         {"rows": 2, "slot": 0, "empty": 0, "other": 0})


class Verdicts(unittest.TestCase):
    BASE = {"test_ids": 1000, "runs_listed": 13, "runs_included": 13, "cells_matched": 13, "answerable": 600,
            "slot_golds": 150, "db_rows": 9999, "gold_changed_official": 60, "stored_rows_golds": 20,
            "rows_reproduced": 19, "runs_abstain_majority": 7, "runs_fixed_gain3": 10,
            "leader_sql_only_first": False}

    def test_on_boundary_all_hold(self):
        v = g.verdicts(self.BASE)
        self.assertEqual(v, {k: True for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8")})

    def test_past_boundary_all_fail(self):
        s = dict(self.BASE, runs_included=11, slot_golds=149, db_rows=10000, gold_changed_official=59,
                 rows_reproduced=18, runs_abstain_majority=6, runs_fixed_gain3=9, leader_sql_only_first=True)
        v = g.verdicts(s)
        self.assertEqual(v, {k: False for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8")})
        self.assertFalse(g.verdicts(dict(self.BASE, cells_matched=11))["P1"])  # 110 < 117
        self.assertTrue(g.verdicts(dict(self.BASE, runs_included=12, cells_matched=11))["P1"])  # 110 >= 108

    def test_not_graded(self):
        s = dict(self.BASE, answerable=0, db_rows=None, stored_rows_golds=0, leader_sql_only_first=None)
        v = g.verdicts(s)
        self.assertEqual([v[k] for k in ("P2", "P3", "P4", "P5", "P8")], [None] * 5)
        self.assertEqual(g.verdict_word(None), "NOT GRADED")
        self.assertEqual(g.verdict_word(True), "HELD")
        self.assertEqual(g.verdict_word(False), "FAILED")


if __name__ == "__main__":
    unittest.main()
