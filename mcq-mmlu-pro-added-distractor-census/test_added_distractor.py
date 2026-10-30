"""Standard-library unit tests for the MMLU-Pro added-vs-original distractor length census (audit 62).

Covers the reused length-census core, the new join + origin split (hand-traced fixture), the structural gate
against audits 59/61, and the prediction logic. No network access.
"""

import unittest
from fractions import Fraction

import cases
import gold_length as gl
import job
import provenance as pv


class TestCoreFixture(unittest.TestCase):
    def test_core_matches_hand_traced_target(self):
        self.assertEqual(gl.run_census(cases.FIXTURE_ROWS), cases.TARGET)


class TestHelpers(unittest.TestCase):
    def test_norm(self):
        self.assertEqual(pv.norm("  a   b \n c "), "a b c")
        self.assertEqual(pv.norm(None), "")

    def test_provenance(self):
        self.assertEqual(pv.provenance("ori_mmlu-business_ethics"), "ori_mmlu")
        self.assertEqual(pv.provenance("stemez-Physics"), "other")
        self.assertEqual(pv.provenance(None), "other")

    def test_longest_credit(self):
        self.assertEqual(pv.longest_credit(5, [3, 4]), Fraction(1))
        self.assertEqual(pv.longest_credit(5, [5, 4]), Fraction(1, 2))
        self.assertEqual(pv.longest_credit(5, [5, 5]), Fraction(1, 3))
        self.assertEqual(pv.longest_credit(3, [5]), Fraction(0))

    def test_build_index_skips_bad_answer(self):
        idx = pv.build_index(cases.JOIN_MMLU_ROWS)
        self.assertNotIn("Bad?", idx)
        self.assertIn("Spaced question", idx)
        self.assertEqual(len(idx["Dup?"]), 2)


class TestJoinFixture(unittest.TestCase):
    def setUp(self):
        self.index = pv.build_index(cases.JOIN_MMLU_ROWS)

    def test_status_and_accumulators(self):
        status, accs = pv.run_join(cases.JOIN_PRO_ROWS, self.index)
        self.assertEqual(status, cases.JOIN_STATUS_TARGET)
        self.assertEqual(accs, cases.JOIN_TARGET)

    def test_match_split(self):
        st, split = pv.match_question("Spaced question", ["three", "one ", "two", "four", "fiver"], 0, self.index)
        self.assertEqual(st, "matched")
        self.assertEqual(split, ("three", ["one ", "two", "four"], ["fiver"]))

    def test_summarize(self):
        _status, accs = pv.run_join(cases.JOIN_PRO_ROWS, self.index)
        s = pv.summarize(accs["ALL"])
        self.assertEqual(s["retained_hist"], {"2": 1, "3": 2})
        self.assertAlmostEqual(s["mean_gold_len"], 10 / 3)
        self.assertAlmostEqual(s["mean_original_len"], 20 / 8)
        self.assertAlmostEqual(s["mean_added_len"], 13 / 4)
        self.assertAlmostEqual(s["gold_longer_vs_original"], 6 / 8)
        self.assertAlmostEqual(s["gold_longer_vs_added"], 2.5 / 4)
        self.assertAlmostEqual(s["intact_pick_longest_full"], 0.75)
        self.assertAlmostEqual(s["intact_chance_full"], 11 / 60)
        self.assertAlmostEqual(s["intact_pick_longest_original4"], 1.0)


def _prov_rep(lift_ori, lift_other):
    return {
        "ori_mmlu": {"n_valid": 6810, "chance_accuracy": 0.1, "char": {"longest_accuracy": 0.1 + lift_ori}},
        "other": {"n_valid": 5222, "chance_accuracy": 0.1, "char": {"longest_accuracy": 0.1 + lift_other}},
    }


def _join(added, original, g_added, g_orig, full=0.2, chance_full=0.1, orig4=0.3, n_intact=10):
    return {
        "n_questions": 100, "mean_gold_len": 40.0, "mean_added_len": added, "mean_original_len": original,
        "gold_longer_vs_added": g_added, "gold_longer_vs_original": g_orig,
        "n_intact": n_intact, "intact_pick_longest_full": full, "intact_chance_full": chance_full,
        "intact_pick_longest_original4": orig4, "intact_chance_original4": 0.25,
    }


class TestPredictions(unittest.TestCase):
    def test_all_held(self):
        rep = {"ALL": _join(30.0, 35.0, 0.7, 0.5, full=0.2, chance_full=0.1, orig4=0.3),
               "biology": _join(30.0, 35.0, 0.8, 0.6), "psychology": _join(30.0, 35.0, 0.75, 0.6)}
        status = {"matched": 95, "no_question": 3, "no_gold": 2, "ambiguous": 0, "bad_key": 0}
        p = job.predictions(status, rep, _prov_rep(0.08, 0.05))
        self.assertTrue(p["P1_join_coverage_at_least_90pct"])
        self.assertTrue(p["P2_added_distractors_shorter_than_original"])
        self.assertTrue(p["P3_gold_longer_vs_added_exceeds_vs_original"])
        self.assertTrue(p["P4_expansion_amplifies_pick_longest_on_intact"])   # 2.0 > 1.2
        self.assertTrue(p["P5_gap_at_least_0p10_in_biology_and_psychology"])  # 0.2 and 0.15
        self.assertTrue(p["P6_ori_mmlu_lift_exceeds_other"])

    def test_all_failed(self):
        rep = {"ALL": _join(36.0, 35.0, 0.5, 0.6, full=0.1, chance_full=0.1, orig4=0.3),
               "biology": _join(30.0, 35.0, 0.65, 0.6)}  # psychology missing -> P5 fails
        status = {"matched": 80, "no_question": 20, "no_gold": 0, "ambiguous": 0, "bad_key": 0}
        p = job.predictions(status, rep, _prov_rep(0.03, 0.05))
        self.assertFalse(p["P1_join_coverage_at_least_90pct"])
        self.assertFalse(p["P2_added_distractors_shorter_than_original"])
        self.assertFalse(p["P3_gold_longer_vs_added_exceeds_vs_original"])
        self.assertFalse(p["P4_expansion_amplifies_pick_longest_on_intact"])  # 1.0 < 1.2
        self.assertFalse(p["P5_gap_at_least_0p10_in_biology_and_psychology"])
        self.assertFalse(p["P6_ori_mmlu_lift_exceeds_other"])


class TestStructuralGate(unittest.TestCase):
    def _pooled(self, **over):
        base = {"n_valid": cases.EXPECTED_N_VALID, "n_bad_key": 0, "n_degenerate": 0,
                "char": {"unique_longest_count": cases.EXPECTED_POOLED_UNIQUE_LONGEST,
                         "longest_accuracy": cases.EXPECTED_POOLED_LONGEST_ACCURACY}}
        base.update(over)
        return base

    def test_gate_passes(self):
        ok, _detail = job.structural_gate(self._pooled(), _prov_rep(0.0, 0.0))
        self.assertTrue(ok)

    def test_gate_fails_on_accuracy(self):
        pooled = self._pooled(char={"unique_longest_count": cases.EXPECTED_POOLED_UNIQUE_LONGEST,
                                    "longest_accuracy": 0.1838})
        ok, detail = job.structural_gate(pooled, _prov_rep(0.0, 0.0))
        self.assertFalse(ok)
        self.assertFalse(detail["pooled_longest_accuracy"]["match"])

    def test_gate_fails_on_provenance(self):
        prov = _prov_rep(0.0, 0.0)
        prov["other"]["n_valid"] = 5221
        ok, detail = job.structural_gate(self._pooled(), prov)
        self.assertFalse(ok)
        self.assertFalse(detail["provenance_counts"]["match"])


if __name__ == "__main__":
    unittest.main()
