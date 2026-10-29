"""Standard-library unit tests for the MMLU per-subject gold-answer-length census (audit 60).

Covers the reused length-census core, the audit-52 hand-traced fixture, the modal-option-count additions to
to_report, the pooled reproduction gate, and the cross-subject length predictions. No network access.
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

    def test_report_values_and_modal(self):
        rep = gl.to_report(gl.run_census(cases.FIXTURE_ROWS))
        # chance baselines: cs5 = (2/5)/2 = 1/5 ; mc4 = 1/3
        self.assertAlmostEqual(rep["cs5"]["chance_accuracy"], 0.2)
        self.assertAlmostEqual(rep["mc4"]["chance_accuracy"], 1.0 / 3.0)
        # modal option count: cs5 is all 5-option (coverage 1.0); mc4 is 2x4-option + 1x2-option -> modal 4
        self.assertEqual(rep["cs5"]["modal_option_count"], 5)
        self.assertAlmostEqual(rep["cs5"]["modal_coverage"], 1.0)
        self.assertEqual(rep["mc4"]["modal_option_count"], 4)
        self.assertAlmostEqual(rep["mc4"]["modal_coverage"], 2.0 / 3.0)
        # gold is longer than distractors (mean) in both synthetic keys
        self.assertGreater(rep["cs5"]["char"]["mean_gold_len"], rep["cs5"]["char"]["mean_distractor_len"])
        self.assertGreater(rep["mc4"]["char"]["mean_gold_len"], rep["mc4"]["char"]["mean_distractor_len"])
        # token view is deliberately uninformative (all single-token options)
        self.assertEqual(rep["cs5"]["token"]["unique_longest_count"], 0)
        self.assertEqual(rep["mc4"]["token"]["unique_longest_count"], 0)


class TestPooledReproductionGate(unittest.TestCase):
    def _pooled(self, **over):
        base = {
            "n_valid": 15858,
            "chance_accuracy": 0.25,
            "char": {"unique_longest_count": 3727, "unique_shortest_count": 2871,
                     "unique_longest_rate": 0.235, "unique_shortest_rate": 0.181,
                     "longest_accuracy": 0.2804998528608063, "shortest_accuracy": 0.22646823895405052,
                     "mean_gold_len": 43.14692899482911, "mean_distractor_len": 41.47181233446841},
            "token": {"longest_accuracy": 0.2806417370832808},
        }
        base.update(over)
        return base

    def test_exact_reproduction_passes(self):
        ok, detail = job.pooled_reproduction_check(self._pooled(), cases.EXPECTED_POOLED_MMLU)
        self.assertTrue(ok)
        self.assertTrue(all(d["match"] for d in detail.values()))

    def test_count_mismatch_fails(self):
        bad = self._pooled()
        bad["char"] = dict(bad["char"], unique_longest_count=3728)  # off by one
        ok, detail = job.pooled_reproduction_check(bad, cases.EXPECTED_POOLED_MMLU)
        self.assertFalse(ok)
        self.assertFalse(detail["char_unique_longest_count"]["match"])

    def test_float_drift_fails(self):
        bad = self._pooled()
        bad["char"] = dict(bad["char"], longest_accuracy=0.2810)  # well beyond tolerance
        ok, _ = job.pooled_reproduction_check(bad, cases.EXPECTED_POOLED_MMLU)
        self.assertFalse(ok)

    def test_tiny_float_noise_within_tolerance_passes(self):
        noisy = self._pooled()
        noisy["char"] = dict(noisy["char"], longest_accuracy=0.2804998528608063 + 1e-12)
        ok, _ = job.pooled_reproduction_check(noisy, cases.EXPECTED_POOLED_MMLU)
        self.assertTrue(ok)


class TestCrossSubjectPredictions(unittest.TestCase):
    def _subj(self, longest_acc, gold_len, distr_len, n=400, chance=0.25, bad=0, deg=0, k=4, cover=1.0):
        return {
            "n_valid": n, "n_bad_key": bad, "n_degenerate": deg,
            "modal_option_count": k, "modal_coverage": cover, "chance_accuracy": chance,
            "char": {"longest_accuracy": longest_acc, "mean_gold_len": gold_len, "mean_distractor_len": distr_len,
                     "unique_longest_rate": 0.2},
        }

    def test_p1_partition_and_clean(self):
        # two subjects, both clean 4-option, counts summing to the expected total
        rep = {"a": self._subj(0.27, 40, 38, n=10000), "b": self._subj(0.26, 41, 39, n=5858)}
        preds = job.cross_subject_predictions(rep, 15858)
        self.assertTrue(preds["P1_clean_well_defined_and_complete_partition"])

    def test_p1_fails_on_partition_mismatch(self):
        rep = {"a": self._subj(0.27, 40, 38, n=100), "b": self._subj(0.26, 41, 39, n=100)}
        preds = job.cross_subject_predictions(rep, 15858)
        self.assertFalse(preds["P1_clean_well_defined_and_complete_partition"])
        self.assertFalse(preds["P1_detail"]["partition_ok"])

    def test_p2_p3_pervasive_when_majority_positive(self):
        rep = {
            "a": self._subj(0.30, 44, 40),   # lift +0.05, gold longer
            "b": self._subj(0.27, 42, 41),   # lift +0.02, gold longer
            "c": self._subj(0.24, 39, 40),   # lift -0.01, gold shorter
        }
        preds = job.cross_subject_predictions(rep, 1200)
        self.assertTrue(preds["P2_length_shortcut_pervasive"])            # 2/3 beat chance
        self.assertTrue(preds["P3_gold_longer_than_distractors_pervasive"])  # 2/3 gold longer
        self.assertEqual(preds["P2_detail"]["n_subjects_pick_longest_beats_chance"], 2)

    def test_p4_concentration(self):
        # one strongly leaking subject out of five -> 1/5 < 5/4 is true; but test the boundary logic:
        rep = {
            "a": self._subj(0.40, 50, 40),   # lift +0.15 (strong)
            "b": self._subj(0.26, 41, 40),
            "c": self._subj(0.26, 41, 40),
            "d": self._subj(0.26, 41, 40),
            "e": self._subj(0.26, 41, 40),
        }
        preds = job.cross_subject_predictions(rep, 2000)
        self.assertEqual(preds["P4_detail"]["n_subjects_lift_ge_0.05"], 1)
        self.assertTrue(preds["P4_lift_is_diffuse_not_concentrated"])     # 1 < 5/4

    def test_p4_fails_when_many_strong(self):
        rep = {
            "a": self._subj(0.40, 50, 40),
            "b": self._subj(0.35, 48, 40),
            "c": self._subj(0.26, 41, 40),
            "d": self._subj(0.26, 41, 40),
        }
        preds = job.cross_subject_predictions(rep, 1600)
        self.assertEqual(preds["P4_detail"]["n_subjects_lift_ge_0.05"], 2)
        self.assertFalse(preds["P4_lift_is_diffuse_not_concentrated"])    # 2 < 4/4=1 is False


if __name__ == "__main__":
    unittest.main()
