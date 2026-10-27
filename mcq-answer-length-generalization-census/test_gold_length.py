"""Standard-library unit tests for the MCQ answer-length generalization census (audit 52).

Covers the reused census core, the hand-traced fixture, and the three per-benchmark schema adapters
(normalize), with no network access.
"""

import unittest
from fractions import Fraction

import gold_length as gl
import cases
import job


class TestLengthFunctions(unittest.TestCase):
    def test_strip_and_count(self):
        self.assertEqual(gl.char_len("  abc  "), 3)
        self.assertEqual(gl.char_len(""), 0)
        self.assertEqual(gl.char_len(None), 0)
        self.assertEqual(gl.token_len("  one two  three "), 3)
        self.assertEqual(gl.token_len("word"), 1)
        self.assertEqual(gl.token_len(""), 0)


class TestValidity(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(gl.question_validity(["A", "B"], ["x", "y"], "A"), "valid")

    def test_bad_key(self):
        self.assertEqual(gl.question_validity(["A", "B"], ["x", "y"], "Z"), "bad_key")

    def test_degenerate_single_option(self):
        self.assertEqual(gl.question_validity(["A"], ["x"], "A"), "degenerate")

    def test_degenerate_length_mismatch(self):
        self.assertEqual(gl.question_validity(["A", "B"], ["x"], "A"), "degenerate")

    def test_degenerate_duplicate_labels(self):
        self.assertEqual(gl.question_validity(["A", "A"], ["x", "y"], "A"), "degenerate")


class TestPerQuestion(unittest.TestCase):
    def test_unique_longest_five_options(self):
        r = gl._per_question(["A", "B", "C", "D", "E"], ["a", "bb", "ccc", "dddd", "eeeee"], "E", gl.char_len)
        self.assertEqual(r["gold"], 5)
        self.assertEqual(r["unique_longest"], 1)
        self.assertEqual(r["unique_shortest"], 0)
        self.assertEqual(r["longest_credit"], Fraction(1))

    def test_tie_longest_credit(self):
        r = gl._per_question(["0", "1", "2", "3"], ["aa", "bbbb", "cccc", "d"], "2", gl.char_len)
        self.assertEqual(r["unique_longest"], 0)
        self.assertEqual(r["longest_credit"], Fraction(1, 2))

    def test_unique_shortest(self):
        r = gl._per_question(["0", "1"], ["pp", "qqqq"], "0", gl.char_len)
        self.assertEqual(r["unique_shortest"], 1)
        self.assertEqual(r["shortest_credit"], Fraction(1))


class TestFixtureCensus(unittest.TestCase):
    def test_matches_hand_traced_target(self):
        got = gl.run_census(cases.FIXTURE_ROWS)
        self.assertEqual(got, cases.TARGET)

    def test_report_values(self):
        rep = gl.to_report(gl.run_census(cases.FIXTURE_ROWS))
        # chance baselines: cs5 = (2/5)/2 = 1/5 ; mc4 = 1/3
        self.assertAlmostEqual(rep["cs5"]["chance_accuracy"], 0.2)
        self.assertAlmostEqual(rep["mc4"]["chance_accuracy"], 1.0 / 3.0)
        # gold is longer than distractors (mean) in both synthetic benchmarks
        self.assertGreater(rep["cs5"]["char"]["mean_gold_len"], rep["cs5"]["char"]["mean_distractor_len"])
        self.assertGreater(rep["mc4"]["char"]["mean_gold_len"], rep["mc4"]["char"]["mean_distractor_len"])
        # token view is deliberately uninformative (all single-token options)
        self.assertEqual(rep["cs5"]["token"]["unique_longest_count"], 0)
        self.assertEqual(rep["mc4"]["token"]["unique_longest_count"], 0)


class TestNormalizeAdapters(unittest.TestCase):
    def test_choices_key_dict_of_arrays(self):
        row = {"choices": {"label": ["A", "B", "C"], "text": ["x", "yy", "zzz"]}, "answerKey": " C "}
        labels, texts, key = job.normalize("choices_key", row)
        self.assertEqual(labels, ["A", "B", "C"])
        self.assertEqual(texts, ["x", "yy", "zzz"])
        self.assertEqual(key, "C")

    def test_choices_key_list_of_structs(self):
        row = {"choices": [{"label": "A", "text": "x"}, {"label": "B", "text": "yy"}], "answerKey": "B"}
        labels, texts, key = job.normalize("choices_key", row)
        self.assertEqual((labels, texts, key), (["A", "B"], ["x", "yy"], "B"))

    def test_endings_label(self):
        row = {"endings": ["e0", "e1", "e2", "e3"], "label": "2"}
        labels, texts, key = job.normalize("endings_label", row)
        self.assertEqual(labels, ["0", "1", "2", "3"])
        self.assertEqual(texts, ["e0", "e1", "e2", "e3"])
        self.assertEqual(key, "2")
        # a valid question: gold label present
        self.assertEqual(gl.question_validity(labels, texts, key), "valid")

    def test_choices_answer_int_index(self):
        row = {"choices": ["c0", "c1", "c2", "c3"], "answer": 3}
        labels, texts, key = job.normalize("choices_answer", row)
        self.assertEqual(labels, ["0", "1", "2", "3"])
        self.assertEqual(texts, ["c0", "c1", "c2", "c3"])
        self.assertEqual(key, "3")
        self.assertEqual(gl.question_validity(labels, texts, key), "valid")


class TestGroupedPredictions(unittest.TestCase):
    def _rep(self, uniq, chance, longest_acc):
        # minimal report shape for the three real benchmarks
        def b(u, c, la):
            return {"n_bad_key": 0, "n_degenerate": 0, "chance_accuracy": c,
                    "char": {"unique_longest_rate": u, "longest_accuracy": la}}
        return {
            "commonsenseqa": b(uniq[0], chance[0], longest_acc[0]),
            "hellaswag": b(uniq[1], chance[1], longest_acc[1]),
            "mmlu": b(uniq[2], chance[2], longest_acc[2]),
        }

    def test_p2_holds_when_crowd_high_exam_low(self):
        rep = self._rep(uniq=[0.40, 0.35, 0.22], chance=[0.20, 0.25, 0.25], longest_acc=[0.45, 0.40, 0.25])
        preds = job.grouped_predictions(rep)
        self.assertTrue(preds["P1_clean_parse_every_benchmark"])
        self.assertTrue(preds["P2_crowd_shortcut_and_no_exam_shortcut"])
        self.assertTrue(all(preds["P3_crowd_pick_longest_beats_chance"].values()))

    def test_p2_fails_when_exam_also_high(self):
        rep = self._rep(uniq=[0.40, 0.35, 0.30], chance=[0.20, 0.25, 0.25], longest_acc=[0.45, 0.40, 0.33])
        preds = job.grouped_predictions(rep)
        self.assertFalse(preds["P2_crowd_shortcut_and_no_exam_shortcut"])
        self.assertFalse(preds["P2_detail"]["exam_gold_unique_longest_at_or_below_chance"]["mmlu"])


if __name__ == "__main__":
    unittest.main()
