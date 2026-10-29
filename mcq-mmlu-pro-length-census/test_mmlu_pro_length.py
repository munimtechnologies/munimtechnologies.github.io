"""Standard-library unit tests for the MMLU-Pro per-category gold-answer-length census (audit 61).

Covers the reused length-census core, the audits-52/60 hand-traced fixture, the variable-k chance baseline, the
structural reproduction gate (vs audit 59's parse), and the per-category length predictions. No network access.
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


class TestValidity(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(gl.question_validity(["0", "1"], ["x", "y"], "0"), "valid")

    def test_bad_key(self):
        self.assertEqual(gl.question_validity(["0", "1"], ["x", "y"], "7"), "bad_key")

    def test_degenerate_single_option(self):
        self.assertEqual(gl.question_validity(["0"], ["x"], "0"), "degenerate")


class TestFixtureCensus(unittest.TestCase):
    def test_matches_hand_traced_target(self):
        got = gl.run_census(cases.FIXTURE_ROWS)
        self.assertEqual(got, cases.TARGET)

    def test_variable_k_chance_baseline(self):
        rep = gl.to_report(gl.run_census(cases.FIXTURE_ROWS))
        # cs5 all 5-option -> chance 1/5; mc4 is 4,4,2-option valid -> chance (1/4+1/4+1/2)/3 = 1/3
        self.assertAlmostEqual(rep["cs5"]["chance_accuracy"], 0.2)
        self.assertAlmostEqual(rep["mc4"]["chance_accuracy"], 1.0 / 3.0)
        self.assertEqual(rep["cs5"]["modal_option_count"], 5)
        self.assertEqual(rep["mc4"]["modal_option_count"], 4)


class TestStructuralGate(unittest.TestCase):
    def _pooled(self, **over):
        base = {
            "n_valid": cases.EXPECTED_N_VALID,
            "n_bad_key": 0,
            "n_degenerate": 0,
            "modal_option_count": cases.EXPECTED_MODAL_K,
            "option_count_hist": dict(cases.EXPECTED_OPTION_HIST),
            "chance_accuracy": 0.102,
            "char": {"longest_accuracy": 0.108, "mean_gold_len": 44.0, "mean_distractor_len": 43.0,
                     "unique_longest_rate": 0.1},
        }
        base.update(over)
        return base

    def test_gate_passes_on_match(self):
        ok, detail = job.structural_gate_check(self._pooled())
        self.assertTrue(ok)
        self.assertTrue(all(d["match"] for d in detail.values()))

    def test_gate_fails_on_count(self):
        ok, detail = job.structural_gate_check(self._pooled(n_valid=12031))
        self.assertFalse(ok)
        self.assertFalse(detail["n_valid"]["match"])

    def test_gate_fails_on_hist(self):
        bad_hist = dict(cases.EXPECTED_OPTION_HIST)
        bad_hist["10"] = 9980
        ok, detail = job.structural_gate_check(self._pooled(option_count_hist=bad_hist))
        self.assertFalse(ok)
        self.assertFalse(detail["option_count_hist"]["match"])

    def test_gate_fails_on_dirty_parse(self):
        ok, detail = job.structural_gate_check(self._pooled(n_bad_key=1))
        self.assertFalse(ok)
        self.assertFalse(detail["clean_parse"]["match"])


class TestCategoryPredictions(unittest.TestCase):
    def _pooled(self, longest_acc=0.108, chance=0.102, gold_len=44.0, distr_len=43.0, **over):
        base = {
            "n_valid": cases.EXPECTED_N_VALID, "n_bad_key": 0, "n_degenerate": 0,
            "modal_option_count": cases.EXPECTED_MODAL_K, "option_count_hist": dict(cases.EXPECTED_OPTION_HIST),
            "chance_accuracy": chance,
            "char": {"longest_accuracy": longest_acc, "mean_gold_len": gold_len, "mean_distractor_len": distr_len,
                     "unique_longest_rate": 0.1},
        }
        base.update(over)
        return base

    def _cat(self, longest_acc, chance=0.1, gold_len=44.0, distr_len=43.0, bad=0, deg=0):
        return {
            "n_valid": 500, "n_bad_key": bad, "n_degenerate": deg, "chance_accuracy": chance,
            "char": {"longest_accuracy": longest_acc, "mean_gold_len": gold_len, "mean_distractor_len": distr_len,
                     "unique_longest_rate": 0.1},
        }

    def test_p1_held_when_gate_ok_and_clean(self):
        rep = {"a": self._cat(0.11), "b": self._cat(0.09)}
        preds = job.category_predictions(rep, self._pooled())
        self.assertTrue(preds["P1_structural_gate_and_clean"])

    def test_p1_fails_when_category_dirty(self):
        rep = {"a": self._cat(0.11, bad=2), "b": self._cat(0.09)}
        preds = job.category_predictions(rep, self._pooled())
        self.assertFalse(preds["P1_structural_gate_and_clean"])

    def test_p2_held_when_pooled_lift_below_mmlu(self):
        # pooled lift = 0.108 - 0.102 = +0.006 < MMLU +0.0305 -> HELD
        preds = job.category_predictions({"a": self._cat(0.11)}, self._pooled(longest_acc=0.108, chance=0.102))
        self.assertTrue(preds["P2_expansion_weakens_length_shortcut"])

    def test_p2_fails_when_pooled_lift_exceeds_mmlu(self):
        # pooled lift = 0.14 - 0.102 = +0.038 > MMLU +0.0305 -> FAILED
        preds = job.category_predictions({"a": self._cat(0.11)}, self._pooled(longest_acc=0.14, chance=0.102))
        self.assertFalse(preds["P2_expansion_weakens_length_shortcut"])

    def test_p3_direction(self):
        held = job.category_predictions({"a": self._cat(0.11)}, self._pooled(gold_len=44.0, distr_len=43.0))
        self.assertTrue(held["P3_gold_still_longer_than_distractors_pooled"])
        failed = job.category_predictions({"a": self._cat(0.11)}, self._pooled(gold_len=42.0, distr_len=43.0))
        self.assertFalse(failed["P3_gold_still_longer_than_distractors_pooled"])

    def test_p4_minority_positive_lift(self):
        # 1 of 4 categories has positive lift (chance 0.1): 1 < 4/2 -> HELD
        rep = {"a": self._cat(0.13), "b": self._cat(0.09), "c": self._cat(0.08), "d": self._cat(0.07)}
        preds = job.category_predictions(rep, self._pooled())
        self.assertEqual(preds["P4_detail"]["n_categories_positive_lift"], 1)
        self.assertTrue(preds["P4_length_cue_not_pervasive_across_categories"])

    def test_p4_fails_when_majority_positive(self):
        # 3 of 4 categories positive -> 3 < 2 is False -> FAILED
        rep = {"a": self._cat(0.13), "b": self._cat(0.12), "c": self._cat(0.11), "d": self._cat(0.07)}
        preds = job.category_predictions(rep, self._pooled())
        self.assertEqual(preds["P4_detail"]["n_categories_positive_lift"], 3)
        self.assertFalse(preds["P4_length_cue_not_pervasive_across_categories"])


if __name__ == "__main__":
    unittest.main()
