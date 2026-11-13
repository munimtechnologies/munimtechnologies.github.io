# Unit tests for audit 115's job (standard library only). Apache-2.0. MV2 of Munim, Inc.
import sqlite3
import unittest

import job


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (a integer, b text)")
    conn.executemany("INSERT INTO t VALUES (?, ?)", [(1, "x"), (2, "y"), (2, "y")])
    conn.commit()
    return conn


class TestHelmTranscription(unittest.TestCase):
    def test_clean_strips_fences_only(self):
        self.assertEqual(job.helm_clean("```sql\nSELECT 1\n```"), "\nSELECT 1\n")
        self.assertEqual(job.helm_clean("Here is the query: SELECT 1"), "Here is the query: SELECT 1")

    def test_error_flag(self):
        self.assertEqual(job.error_rate_flag(None), 0.0)
        self.assertEqual(job.error_rate_flag("no such table: x"), 1.0)

    def test_result_string_like_helm(self):
        r = job.run_query(make_db(), "SELECT a FROM t ORDER BY a")
        self.assertEqual(r["result"], "[(1,), (2,), (2,)]")
        self.assertIsNone(r["error"])
        self.assertEqual(r["status"], "ok")

    def test_syntax_error(self):
        r = job.run_query(make_db(), "SELEC a FROM t")
        self.assertIsNotNone(r["error"])
        self.assertEqual(r["status"], "error")
        self.assertIsNone(r["result"])

    def test_two_statements_is_an_error(self):
        r = job.run_query(make_db(), "SELECT 1; SELECT 2")
        self.assertIsNotNone(r["error"])
        self.assertEqual(r["status"], "error")

    def test_write_is_refused(self):
        conn = make_db()
        r = job.run_query(conn, "DELETE FROM t")
        self.assertIsNotNone(r["error"])
        self.assertEqual(conn.execute("SELECT count(*) FROM t").fetchone()[0], 3)

    def test_trivial_query_runs(self):
        r = job.run_query(make_db(), "SELECT 1")
        self.assertIsNone(r["error"])
        self.assertEqual(r["result"], "[(1,)]")
        self.assertEqual(job.error_rate_flag(r["error"]), 0.0)

    def test_timeout(self):
        q = "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT count(*) FROM c"
        r = job.run_query(make_db(), q, seconds=0.2)
        self.assertEqual(r["status"], "timeout")
        self.assertIsNotNone(r["error"])

    def test_row_cap(self):
        old = job.ROW_CAP
        job.ROW_CAP = 2
        try:
            r = job.run_query(make_db(), "SELECT a FROM t")
        finally:
            job.ROW_CAP = old
        self.assertEqual(r["status"], "row_cap")
        self.assertIsNone(r["result"])
        self.assertIsNone(r["error"])


class TestMatching(unittest.TestCase):
    def test_string_vs_set(self):
        conn = make_db()
        g = job.run_query(conn, "SELECT a FROM t ORDER BY a DESC")
        p = job.run_query(conn, "SELECT DISTINCT a FROM t")
        self.assertFalse(job.string_match(p["result"], g["result"], g["error"]))
        self.assertTrue(job.set_match(p["rows"], g["rows"]))

    def test_string_match_needs_gold_without_error(self):
        self.assertTrue(job.string_match("[(1,)]", "[(1,)]", None))
        self.assertFalse(job.string_match("[(1,)]", "[(1,)]", "boom"))
        self.assertFalse(job.string_match(None, None, None))

    def test_set_match_none(self):
        self.assertFalse(job.set_match(None, [(1,)]))
        self.assertTrue(job.set_match([], []))


class TestHelpers(unittest.TestCase):
    def test_kendall(self):
        self.assertEqual(job.kendall_tau_b([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertEqual(job.kendall_tau_b([1, 2, 3], [3, 2, 1]), -1.0)
        self.assertAlmostEqual(job.kendall_tau_b([1, 2, 2], [1, 2, 3]), 2 / 6 ** 0.5)

    def test_published_error_rate(self):
        stats = [
            {"name": {"name": "error_rate", "split": "test", "perturbation": {"name": "x"}}, "count": 1, "sum": 1, "mean": 0.9},
            {"name": {"name": "num_prompt_tokens", "split": "test"}, "count": 4, "sum": 8, "mean": 2.0},
            {"name": {"name": "error_rate", "split": "test"}, "count": 4, "sum": 1.0, "mean": 0.25},
        ]
        self.assertEqual(job.published_error_rate(stats), 0.25)
        self.assertIsNone(job.published_error_rate([]))

    def test_model_from_run(self):
        self.assertEqual(job.model_from_run("czech_bank_qa:model=meta_llama-3.1-8b-instruct-turbo"),
                         "meta_llama-3.1-8b-instruct-turbo")
        self.assertEqual(job.model_from_run("czech_bank_qa:config_name=x,model=a_b"), "a_b")

    def test_grade_without_leaderboard(self):
        p, graded = job.grade({"golds": 100, "gold_error_or_timeout": 0, "empty_results": 3}, {"runs": []})
        self.assertTrue(p["P1"]["held"])
        self.assertTrue(p["P2"]["held"])
        self.assertIsNone(p["P3"]["held"])
        self.assertEqual(graded, [])

    def test_grade_with_runs(self):
        def run(name, err, acc):
            return {"run": name, "annotated_records": 100, "published_error_rate": err,
                    "recomputed_error_rate_stored": err, "exec_acc_string_stored": acc,
                    "records_rerun": 100, "flag_reproduced": 100, "string_match_ours": int(acc * 100),
                    "set_match_ours": int(acc * 100) + 2, "ran_stored": int((1 - err) * 100),
                    "ran_but_wrong_stored": int((1 - err) * 100) - int(acc * 100)}
        info = {"runs": [run("m1", 0.02, 0.30), run("m2", 0.10, 0.50), run("m3", 0.05, 0.40)]}
        p, graded = job.grade({"golds": 10, "gold_error_or_timeout": 1, "empty_results": 1}, info)
        self.assertFalse(p["P1"]["held"])
        self.assertFalse(p["P2"]["held"])
        self.assertTrue(p["P3"]["held"])
        self.assertTrue(p["P4"]["held"])   # gaps 0.68, 0.40, 0.55
        self.assertTrue(p["P5"]["held"])   # m1 lowest error, m2 best accuracy
        self.assertTrue(p["P6"]["held"])   # order m1 m3 m2 against m2 m3 m1: tau -1
        self.assertTrue(p["P7"]["held"])   # 126 >= 1.02 * 120
        self.assertTrue(p["P8"]["held"])   # 163 of 283 ran but wrong


if __name__ == "__main__":
    unittest.main()
