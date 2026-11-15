# SPDX-License-Identifier: Apache-2.0
# Unit tests for audit 123 (MV2 of Munim, Inc.; made with AI agents). Standard library only.
import unittest
from fractions import Fraction

import grade123 as g

J = g.JUDGE


class Names(unittest.TestCase):
    def test_blink(self):
        run = "blink:category=Counting,model=anthropic_claude-3-haiku-20240307,groups=blink_perception"
        self.assertEqual(g.scenario_of(run), "blink")
        self.assertEqual(g.model_of(run), "anthropic_claude-3-haiku-20240307")
        self.assertEqual(g.group_of(run), "blink:category=Counting,groups=blink_perception")

    def test_model_last_and_only(self):
        self.assertEqual(g.group_of("bingo:subject=OCR,model=x"), "bingo:subject=OCR")
        self.assertEqual(g.group_of("vibe_eval:model=y"), "vibe_eval:")
        self.assertEqual(g.model_of("vibe_eval:model=y"), "y")
        self.assertEqual(g.model_of("nocolon"), "")


class Empty(unittest.TestCase):
    def test_is_empty(self):
        self.assertTrue(g.is_empty(""))
        self.assertTrue(g.is_empty("  \n"))
        self.assertTrue(g.is_empty(None))
        self.assertFalse(g.is_empty("A"))
        self.assertFalse(g.is_empty(" 0"))

    def test_fmt(self):
        self.assertEqual(g.fmt(5), "5")
        self.assertEqual(g.fmt(5.0), "5")
        self.assertEqual(g.fmt(2.5), "2.5")


class Summary(unittest.TestCase):
    def test_summarize(self):
        preds = [
            {"instance_id": "a", "predicted_text": "", "stats": {J: 5, "num_output_tokens": 0}},
            {"instance_id": "b", "predicted_text": "Cat", "stats": {J: 2}},
            {"instance_id": "c", "predicted_text": "  ", "stats": {J: 1, "quasi_exact_match": 0}},
            {"instance_id": "a", "predicted_text": "", "perturbation": {"name": "robustness"}, "stats": {J: 5}},
            {"instance_id": "d", "stats": {}},
            "not a record",
        ]
        s = g.summarize_preds(preds)
        self.assertEqual(s["counts"], {"records": 5, "perturbed": 1, "n": 4, "empty": 3, "missing_text": 1})
        self.assertEqual(s["judge"]["empty"], {"n": 2, "sum": 6.0, "hist": {"5": 1, "1": 1}})
        self.assertEqual(s["judge"]["answered"], {"n": 1, "sum": 2.0, "hist": {"2": 1}})
        self.assertEqual(s["metric_empty"], {J: [2, 6.0], "quasi_exact_match": [1, 0.0]})
        self.assertEqual(g.judge_mean(s), 8.0 / 3)

    def test_no_judge(self):
        s = g.summarize_preds([{"predicted_text": "B", "stats": {"exact_match": 1}}])
        self.assertIsNone(g.judge_mean(s))
        self.assertEqual(s["counts"]["empty"], 0)

    def test_stat_entry(self):
        stats = [{"name": {"name": J, "split": "valid"}, "count": 1, "sum": 2.0, "mean": 2.0},
                 {"name": {"name": J, "split": "test", "perturbation": {"name": "x"}}, "count": 1, "sum": 9.0,
                  "mean": 9.0}]
        self.assertEqual(g.stat_entry(stats, J)["mean"], 2.0)
        stats.append({"name": {"name": J, "split": "test"}, "count": 1, "sum": 3.0, "mean": 3.0})
        self.assertEqual(g.stat_entry(stats, J)["mean"], 3.0)
        self.assertIsNone(g.stat_entry(stats, "other"))


def row(model, group, n, empty, jm=None):
    return {"run": group + model, "scenario": group.split(":")[0], "model": model, "group": group, "n": n,
            "empty": empty, "judge_mean": jm}


class Aggregates(unittest.TestCase):
    def test_model_totals(self):
        rows = [row("m1", "s:a", 100, 5), row("m1", "t:b", 100, 4), row("m2", "s:a", 0, 0)]
        t = g.model_totals(rows)
        self.assertEqual((t["m1"]["n"], t["m1"]["empty"], t["m1"]["runs"], t["m1"]["runs_empty5"]), (200, 9, 2, 1))
        self.assertEqual(t["m1"]["by_scenario"], {"s": [100, 5], "t": [100, 4]})
        self.assertEqual(t["m2"]["runs_empty5"], 0)

    def test_p7_pairs(self):
        rows = [row("E", "G:", 10, 10, 3.0), row("A1", "G:", 10, 0, 2.0), row("A2", "G:", 10, 0, 4.0),
                row("M", "G:", 10, 5, 1.0),
                row("E2", "H:", 10, 10, 1.0), row("A3", "H:", 10, 0, 3.0),
                row("E3", "K:", 10, 10, None), row("A4", "K:", 10, 0, 1.0)]
        p = g.p7_pairs(rows)
        self.assertEqual(len(p), 1)
        self.assertEqual((p[0]["group"], p[0]["empty_model"], p[0]["answering_below"], p[0]["answering_runs"]),
                         ("G:", "E", ["A1"], 2))


class Verdicts(unittest.TestCase):
    S = {"runs_listed": 3000, "runs_parsed": 2900, "think_n": 1000, "think_empty": 995, "think_runs": 30,
         "others_max_share": Fraction(49, 100), "gemini_nonunicorn_runs50": 1, "claude_plain_empty": 100,
         "claude_plain_empty_unicorn": 80, "judge_empty_n": 10, "judge_empty_sum": 20.0, "judge_empty_fives": 2,
         "p7_pairs": 1, "models_run_empty5": 10}

    def test_all_held(self):
        self.assertTrue(all(g.verdicts(self.S).values()))

    def test_failed_and_ungraded(self):
        s = dict(self.S, runs_parsed=2849, others_max_share=Fraction(1, 2), judge_empty_n=0,
                 gemini_nonunicorn_runs50=None, think_runs=29, p7_pairs=0, models_run_empty5=9)
        v = g.verdicts(s)
        self.assertFalse(v["P1"])
        self.assertFalse(v["P2"])
        self.assertFalse(v["P3"])
        self.assertIsNone(v["P4"])
        self.assertTrue(v["P5"])
        self.assertIsNone(v["P6"])
        self.assertFalse(v["P7"])
        self.assertFalse(v["P8"])
        self.assertEqual(g.verdict_word(None), "NOT GRADED")


if __name__ == "__main__":
    unittest.main()
