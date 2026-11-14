# SPDX-License-Identifier: Apache-2.0
# Unit tests for audit 119 (synthetic records only). Made with AI agents working in MV2's name (Munim, Inc.).
import unittest
from decimal import Decimal
from fractions import Fraction

import grade119 as g


class TestHelmTranscription(unittest.TestCase):
    def test_exact_match_strips(self):
        self.assertEqual(g.exact_match("5", " 5 "), 1)
        self.assertEqual(g.exact_match("5", "5."), 0)
        self.assertEqual(g.exact_match("5", ""), 0)

    def test_max_over_golds(self):
        self.assertEqual(g.helm_score(("5", "5 years"), "5 years"), 1)
        self.assertEqual(g.helm_score(("5", "5 years"), "5 yrs"), 0)


class TestOfficial(unittest.TestCase):
    def test_official_float_and_int(self):
        self.assertEqual(g.official_float("0.618", 2), "0.62")
        self.assertEqual(g.official_int("2.7"), "2")
        self.assertIsNone(g.official_float("abc", 1))


class TestParse(unittest.TestCase):
    def test_latex_wrapper(self):
        d, s, tags = g.parse_answer("\\( 4.3 \\)")
        self.assertEqual((d, s, tags), (Decimal("4.3"), "4.3", {"wrapped"}))

    def test_separator(self):
        self.assertEqual(g.parse_answer("7,873"), (Decimal("7873"), "7873", {"separator"}))

    def test_period_symbol_unit(self):
        self.assertEqual(g.parse_answer("27."), (Decimal("27"), "27", {"period"}))
        self.assertEqual(g.parse_answer("45°"), (Decimal("45"), "45", {"symbol"}))
        self.assertEqual(g.parse_answer("3 years", "years"), (Decimal("3"), "3", {"unit"}))
        self.assertEqual(g.parse_answer("$0.06"), (Decimal("0.06"), "0.06", {"symbol"}))

    def test_not_a_number(self):
        d, s, _ = g.parse_answer("## Step 1 The plot")
        self.assertIsNone(d)
        self.assertIsNone(s)

    def test_gold_info(self):
        self.assertEqual(g.gold_info(("5", "5 years")), ("5", Decimal("5"), 0, "years"))
        self.assertEqual(g.gold_info(("[0, 2]",)), (None, None, None, None))


class TestClassify(unittest.TestCase):
    def test_classes(self):
        self.assertEqual(g.classify(("13.8",), "13.80", 0), ("num_equal", {"number_form"}, 2))
        self.assertEqual(g.classify(("0.62",), "0.618", 0), ("rounds_to_gold", set(), 3))
        self.assertEqual(g.classify(("2",), "2.7", 0), ("int_trunc_official", set(), 1))
        self.assertEqual(g.classify(("1.2",), "0.018", 0), ("wrong_number", set(), 3))
        self.assertEqual(g.classify(("12",), "The answer is 12", 0), ("last_number_equal", set(), None))
        self.assertEqual(g.classify(("[0, 2]",), "[0, 2", 0), ("nonnumeric_gold", set(), None))
        self.assertEqual(g.classify(("5",), "", 0), ("empty", set(), None))
        self.assertEqual(g.classify(("5",), "five", 0), ("no_number", set(), None))
        self.assertEqual(g.classify(("5",), "5", 1), ("exact", set(), 0))
        self.assertEqual(g.classify(("4",), "There are 3 or 5", 0), ("other", set(), None))
        self.assertEqual(g.classify(("7873",), "7,873", 0), ("num_equal", {"separator"}, 0))


def _inst(iid, q, golds, split="test"):
    return {"id": iid, "split": split,
            "input": {"multimedia_content": {"media_objects": [
                {"content_type": "text/plain", "text": q}, {"content_type": "image/jpeg", "location": "x"}]}},
            "references": [{"output": {"text": t}, "tags": ["correct"]} for t in golds]}


class TestRun(unittest.TestCase):
    def test_instance_map(self):
        m = g.instance_map([_inst("id0", "How many?", ["5", "5 years"]), _inst("id1", "x", ["1"], split="train"),
                            _inst("id2", "Hint: be exact. Q?", ["0.62"])])
        self.assertEqual(m, {"id0": ("integer", ("5", "5 years"), False), "id2": ("float", ("0.62",), True)})

    def test_summarize(self):
        imap = {"id0": ("integer", ("5", "5 years"), False), "id1": ("float", ("0.62",), False),
                "id2": ("integer", ("3",), False)}
        preds = [
            {"instance_id": "id0", "predicted_text": "5 years", "stats": {"exact_match": 1, "num_output_tokens": 2}},
            {"instance_id": "id1", "predicted_text": "0.618", "stats": {"exact_match": 0, "num_output_tokens": 3}},
            {"instance_id": "id2", "predicted_text": "## Step 1 First",
             "stats": {"exact_match": 0, "num_output_tokens": 20}},
            {"instance_id": "id2", "predicted_text": "3", "stats": {"exact_match": 1, "num_output_tokens": 1}},
            {"instance_id": "id9", "predicted_text": "3", "stats": {"exact_match": 0, "num_output_tokens": 1}},
            {"instance_id": "id0", "perturbation": {"name": "x"}, "predicted_text": "5", "stats": {}},
        ]
        s = g.summarize_run(preds, imap, 20)
        c = s["counts"]
        self.assertEqual((c["n_records"], c["perturbed"], c["not_test"], c["duplicate"], c["kept"]), (6, 1, 1, 1, 3))
        self.assertEqual((c["credit"], c["mismatch"], c["stored_missing"], c["cap"]), (1, 0, 0, 1))
        self.assertEqual(s["classes"]["exact"], 1)
        self.assertEqual(s["classes"]["rounds_to_gold"], 1)
        self.assertEqual(s["classes"]["other"], 1)
        self.assertEqual(s["cap_by_class"]["other"], 1)
        self.assertEqual(s["lenient"], 2)
        self.assertEqual(s["by_kind"]["integer"], {"n": 2, "credit": 1, "lenient": 1})
        self.assertEqual(s["by_kind"]["float"], {"n": 1, "credit": 0, "lenient": 1})
        self.assertEqual(s["float_single"], {"n": 1, "other_decimals": 1})

    def test_mismatch(self):
        imap = {"id0": ("integer", ("5",), False)}
        s = g.summarize_run([{"instance_id": "id0", "predicted_text": "6", "stats": {"exact_match": 1}}], imap, 20)
        self.assertEqual(s["counts"]["mismatch"], 1)
        self.assertEqual(s["counts"]["cap"], 0)

    def test_run_field_and_stat(self):
        rn = "math_vista:grade=college,question_type=free_form,model=openai_gpt-4o"
        self.assertEqual(g.run_field(rn, "grade"), "college")
        self.assertEqual(g.run_field(rn, "model"), "openai_gpt-4o")
        stats = [{"name": {"name": "exact_match", "split": "test"}, "count": 1, "sum": 20, "mean": 0.35}]
        self.assertEqual(g.stat_entry(stats, "exact_match"), {"count": 1, "sum": 20, "mean": 0.35})
        self.assertIsNone(g.stat_entry(stats, "quasi_exact_match"))


class TestStats(unittest.TestCase):
    def test_tau(self):
        self.assertEqual(g.kendall_tau_b([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertEqual(g.kendall_tau_b([1, 2, 3], [3, 2, 1]), -1.0)

    def test_verdicts(self):
        s = {"runs_listed": 204, "runs_included": 204, "models_complete": 51, "pooled_records": 23460,
             "pooled_num_equal": 100, "pooled_rounds_to_gold": 30, "float_single_n": 100, "float_single_other": 20,
             "models_cap2": 10, "tau_b": 0.95, "max_gain": Fraction(3, 100)}
        v = g.verdicts(s)
        self.assertTrue(all(v[k] for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8")))
        s2 = dict(s, runs_listed=203, tau_b=None, float_single_other=19)
        v2 = g.verdicts(s2)
        self.assertFalse(v2["P1"])
        self.assertIsNone(v2["P7"])
        self.assertFalse(v2["P5"])
        self.assertEqual(g.verdict_word(None), "NOT GRADED")


if __name__ == "__main__":
    unittest.main()
