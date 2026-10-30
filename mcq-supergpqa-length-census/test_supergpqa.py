"""Unit tests for the SuperGPQA answer-length census (audit 64). Standard library only. Apache-2.0."""

import copy
import unittest
from fractions import Fraction

import cases
import gold_length as gl
import supergpqa as sg


def E(n, chance, acc, gold=10.0, dist=10.0, ul=0, us=0):
    """Minimal report entry for the prediction logic."""
    return {"n_valid": n, "chance_accuracy": chance,
            "char": {"longest_accuracy": acc, "mean_gold_len": gold, "mean_distractor_len": dist,
                     "unique_longest_count": ul, "unique_shortest_count": us}}


class CoreFixture(unittest.TestCase):
    def test_core_matches_target(self):
        self.assertEqual(gl.run_census(cases.FIXTURE_ROWS), cases.TARGET)


class Conversion(unittest.TestCase):
    def test_letter_index(self):
        self.assertEqual(sg.letter_index("A"), 0)
        self.assertEqual(sg.letter_index(" J "), 9)
        self.assertIsNone(sg.letter_index("b"))
        self.assertIsNone(sg.letter_index("AB"))
        self.assertIsNone(sg.letter_index(""))
        self.assertIsNone(sg.letter_index(None))

    def test_calc_key(self):
        self.assertEqual(sg.calc_key(True), "calculation")
        self.assertEqual(sg.calc_key(False), "text")
        self.assertEqual(sg.calc_key(None), "unknown")

    def test_unparseable_letter_is_bad_key(self):
        rows = sg.census_rows([{"options": ["a", "bb"], "answer_letter": "x"}], lambda r: "K")
        self.assertEqual(rows, [("K", ["0", "1"], ["a", "bb"], "?")])
        self.assertEqual(gl.run_census(rows)["K"]["n_bad_key"], 1)

    def test_discipline_digest(self):
        rows = sg.census_rows(cases.SG_ROWS, lambda r: r["discipline"])
        self.assertEqual(sg.digest(gl.run_census(rows)), cases.SG_TARGET_DISCIPLINE)

    def test_calc_digest(self):
        rows = sg.census_rows(cases.SG_ROWS, lambda r: sg.calc_key(r["is_calculation"]))
        self.assertEqual(sg.digest(gl.run_census(rows)), cases.SG_TARGET_CALC)

    def test_difficulty_digest(self):
        rows = sg.census_rows(cases.SG_ROWS, lambda r: r["difficulty"])
        self.assertEqual(sg.digest(gl.run_census(rows)), cases.SG_TARGET_DIFFICULTY)

    def test_mmlu_pro_rows(self):
        rows = sg.mmlu_pro_rows([{"options": ["a", "bb", "c"], "answer_index": 1}], lambda r: "ALL")
        self.assertEqual(rows, [("ALL", ["0", "1", "2"], ["a", "bb", "c"], "1")])


class Quality(unittest.TestCase):
    def test_quality_fixture(self):
        self.assertEqual(sg.quality(cases.SG_ROWS), (cases.SG_QUALITY_TARGET, cases.SG_QUALITY_EXAMPLES))

    def test_unparseable_counts_as_mismatch(self):
        q, ex = sg.quality([{"uuid": "u", "options": ["a", "b"], "answer_letter": "?", "answer": "a"}])
        self.assertEqual(q["letter_unparseable"], 1)
        self.assertEqual(q["letter_text_mismatch"], 1)
        self.assertEqual(ex["letter_text_mismatch"], ["u"])


class Position(unittest.TestCase):
    def test_chi2_fixture(self):
        self.assertEqual(sg.position_chi2(cases.CHI_INDICES, cases.CHI_K), cases.CHI_TARGET)

    def test_uniform_is_zero(self):
        self.assertEqual(sg.position_chi2([0, 1, 2, 3], 4)["chi2"], Fraction(0))

    def test_ten_option_positions(self):
        rows = [{"options": list("abcdefghij"), "answer_letter": "C"},     # kept: index 2
                {"options": list("abcdefghi"), "answer_letter": "C"},      # 9 options: skipped
                {"options": list("abcdefghij"), "answer_letter": "?"}]     # unparseable: skipped
        self.assertEqual(sg.ten_option_positions(rows), [2])


def _gate_input():
    ex = cases.EXPECTED_MMLU_PRO
    return {"n_valid": ex["n_valid"], "n_bad_key": 0, "n_degenerate": 0,
            "char": {"unique_longest_count": ex["unique_longest"], "longest_accuracy": ex["longest_accuracy"]}}


class Gate(unittest.TestCase):
    def test_passes_on_expected(self):
        ok, _detail = sg.structural_gate(_gate_input(), cases.EXPECTED_MMLU_PRO)
        self.assertTrue(ok)

    def test_fails_on_drift(self):
        p = _gate_input()
        p["char"]["longest_accuracy"] += 1e-6
        ok, detail = sg.structural_gate(p, cases.EXPECTED_MMLU_PRO)
        self.assertFalse(ok)
        self.assertFalse(detail["pooled_longest_accuracy"]["match"])

    def test_fails_on_bad_key(self):
        p = _gate_input()
        p["n_bad_key"] = 1
        ok, detail = sg.structural_gate(p, cases.EXPECTED_MMLU_PRO)
        self.assertFalse(ok)
        self.assertFalse(detail["clean_parse"]["match"])


class Predictions(unittest.TestCase):
    def setUp(self):
        self.pooled = E(1000, .1, .13, 50.0, 48.0, 150, 80)
        self.calc = {"text": E(600, .1, .15), "calculation": E(400, .1, .10)}
        self.diff = {"easy": E(300, .1, .12), "middle": E(400, .1, .13), "hard": E(300, .1, .14)}
        # Tiny has n < 100 and is left out of P8. Eligible: Engineering, Law, Philosophy.
        self.disc = {"Engineering": E(500, .1, .12), "Philosophy": E(200, .1, .09),
                     "Law": E(150, .1, .11), "Tiny": E(10, .1, .5)}
        self.qual = {"letter_text_mismatch": 0}
        self.pos = {"n": 500, "chi2": 12.0}

    def test_hand_traced(self):
        p = sg.predictions(self.pooled, self.calc, self.diff, self.disc, self.qual, self.pos)
        self.assertTrue(p["P1_pooled_pick_longest_under_1_5x_chance"])       # 1.3
        self.assertTrue(p["P2_pooled_lift_at_least_1pp"])                    # .03
        self.assertTrue(p["P3_text_lift_exceeds_calculation_lift"])          # .05 > 0
        self.assertFalse(p["P4_easy_lift_exceeds_hard_lift"])                # .02 < .04
        self.assertTrue(p["P5_gold_longer_than_mean_distractor"])            # 50 > 48
        self.assertTrue(p["P6_unique_longest_exceeds_unique_shortest"])      # 150 > 80
        self.assertTrue(p["P7_ten_option_positions_uniform"])                # 12 < 27.877
        self.assertEqual(p["P8_detail"]["eligible"], ["Engineering", "Law", "Philosophy"])
        self.assertEqual(p["P8_detail"]["positive"], ["Engineering", "Law"])
        self.assertTrue(p["P8_lift_positive_in_majority_of_disciplines"])    # 2 of 3
        self.assertTrue(p["P9_answer_text_matches_letter_everywhere"])

    def test_failures(self):
        pooled = E(1000, .1, .16, 40.0, 45.0, 50, 60)
        calc = {"text": E(600, .1, .15)}                                     # no calculation cell
        p = sg.predictions(pooled, calc, self.diff, self.disc, {"letter_text_mismatch": 3},
                           {"n": 500, "chi2": 30.0})
        self.assertFalse(p["P1_pooled_pick_longest_under_1_5x_chance"])      # 1.6
        self.assertTrue(p["P2_pooled_lift_at_least_1pp"])
        self.assertFalse(p["P3_text_lift_exceeds_calculation_lift"])
        self.assertIsNone(p["P3_detail"]["calculation"])
        self.assertFalse(p["P5_gold_longer_than_mean_distractor"])
        self.assertFalse(p["P6_unique_longest_exceeds_unique_shortest"])
        self.assertFalse(p["P7_ten_option_positions_uniform"])               # 30 > 27.877
        self.assertFalse(p["P9_answer_text_matches_letter_everywhere"])

    def test_small_position_sample_and_tie(self):
        disc = copy.deepcopy(self.disc)
        del disc["Law"]                                                      # 1 of 2 positive: not a majority
        p = sg.predictions(self.pooled, self.calc, self.diff, disc, self.qual, {"n": 50, "chi2": 1.0})
        self.assertFalse(p["P7_ten_option_positions_uniform"])               # n < 100
        self.assertFalse(p["P8_lift_positive_in_majority_of_disciplines"])


if __name__ == "__main__":
    unittest.main()
