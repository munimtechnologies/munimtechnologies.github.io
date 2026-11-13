# Audit 116 unit tests. MV2 of Munim, Inc. -- made by AI agents working in MV2's name. Licence: Apache-2.0.
# Every expected value below was traced by hand from HELM's formulas (see README).
import io
import unittest
from contextlib import redirect_stdout

import kpi_edgar_check as k

GOLD4 = "total net revenue [kpi], 100 [cy], 90 [py], 80 [py1]"


class TestIssueExample(unittest.TestCase):
    def test_issue_4348_numbers(self):
        rec = [("revenue increased [kpi], 100 [cy], 90 [py]", "revenue [kpi], 100 [cy]")]
        self.assertAlmostEqual(k.score(rec, "helm")["adjusted_macro_f1_score"], 0.45)
        self.assertAlmostEqual(k.score(rec, "fixed")["adjusted_macro_f1_score"], 5 / 12)
        self.assertAlmostEqual(k.score(rec, "helm")["word_macro_f1_score"], 5 / 12)
        self.assertAlmostEqual(k.score(rec, "fixed")["word_macro_f1_score"], 5 / 12)


class TestFloors(unittest.TestCase):
    def test_copy_sentence(self):
        rec = [("Revenue [kpi], 100 [cy], 90 [py], 80 [py1]", k.copy_answer("Revenue was 100 , 90 and 80 ."))]
        per = k.tag_scores(rec, "fixed")
        for tag in k.TAGS:
            self.assertEqual((per[tag]["overlap"], per[tag]["pred"], per[tag]["gold"]), (1, 8, 1))
        self.assertAlmostEqual(k.score(rec, "fixed")["adjusted_macro_f1_score"], 16 / 23)
        self.assertAlmostEqual(k.score(rec, "helm")["adjusted_macro_f1_score"], 2 / 9)
        self.assertAlmostEqual(k.score(rec, "fixed")["word_macro_f1_score"], 2 / 9)

    def test_single_word_of_ten(self):
        rec = [("a b c d e f g h i j [kpi]", "a [kpi]")]
        self.assertAlmostEqual(k.tag_scores(rec, "helm")["kpi"]["adjusted"], 2 / 2.9)
        self.assertAlmostEqual(k.tag_scores(rec, "fixed")["kpi"]["adjusted"], 2 / 11)
        self.assertAlmostEqual(k.tag_scores(rec, "fixed")["kpi"]["word"], 2 / 11)
        self.assertAlmostEqual(k.tag_scores(rec, "helm")["cy"]["adjusted"], 0.0)

    def test_floor_closed_form(self):
        grid = [i / 10 for i in range(1, 11)]
        for x in grid:
            self.assertGreaterEqual(k.adjusted_fixed(1.0, x), 2 / 3 - 1e-12)
            self.assertGreaterEqual(k.adjusted_helm(x, 1.0), 2 / 3 - 1e-12)
        self.assertAlmostEqual(k.adjusted_helm(1e-9, 1.0), 2 / 3, places=6)
        self.assertAlmostEqual(k.adjusted_fixed(1.0, 1e-9), 2 / 3, places=6)


class TestOrientation(unittest.TestCase):
    def test_under_and_over_tagging(self):
        under = [(GOLD4, "revenue [kpi], 100 [cy], 90 [py], 80 [py1]")]
        over = [(GOLD4, "the total net revenue was [kpi], 100 [cy], 90 [py], 80 [py1]")]
        self.assertAlmostEqual(k.score(under, "helm")["adjusted_macro_f1_score"], 0.9375)
        self.assertAlmostEqual(k.score(under, "fixed")["adjusted_macro_f1_score"], 0.875)
        self.assertAlmostEqual(k.score(under, "fixed")["word_macro_f1_score"], 0.875)
        self.assertAlmostEqual(k.score(over, "helm")["adjusted_macro_f1_score"], 0.9375)
        self.assertAlmostEqual(k.score(over, "fixed")["adjusted_macro_f1_score"], 23 / 24)
        self.assertAlmostEqual(k.score(over, "fixed")["word_macro_f1_score"], 0.9375)

    def test_closed_forms_match_code(self):
        for o, p, g in [(1, 6, 1), (1, 1, 3), (3, 5, 3), (2, 7, 4)]:
            r_, p_ = o / g, o / p
            fixed = k.compute_f1_score(k.counts_to_rates(k.Counts(o, p, g), True))
            helm = k.compute_f1_score(k.counts_to_rates(k.Counts(o, g, p), True))
            word = k.compute_f1_score(k.counts_to_rates(k.Counts(o, p, g), False))
            self.assertAlmostEqual(fixed, k.adjusted_fixed(r_, p_))
            self.assertAlmostEqual(helm, k.adjusted_helm(r_, p_))
            self.assertAlmostEqual(word, k.word_f1(r_, p_))

    def test_sign_rule_and_bracket(self):
        grid = [i / 10 for i in range(1, 11)]
        for r in grid:
            for p in grid:
                h, f, w = k.adjusted_helm(r, p), k.adjusted_fixed(r, p), k.word_f1(r, p)
                if abs(p - r) < 1e-9:
                    self.assertAlmostEqual(h, f)
                    self.assertAlmostEqual(h, w)
                elif p > r:
                    self.assertGreater(h, f)
                    self.assertGreaterEqual(h + 1e-12, w)
                    self.assertGreaterEqual(w + 1e-12, f)
                else:
                    self.assertGreater(f, h)
                    self.assertGreaterEqual(f + 1e-12, w)
                    self.assertGreaterEqual(w + 1e-12, h)


class TestParsing(unittest.TestCase):
    def test_gold_as_answer(self):
        rec = [(GOLD4, GOLD4)]
        for o in ("helm", "fixed"):
            self.assertAlmostEqual(k.score(rec, o)["adjusted_macro_f1_score"], 1.0)
            self.assertAlmostEqual(k.score(rec, o)["word_macro_f1_score"], 1.0)

    def test_absent_tag_scores_zero(self):
        rec = [("revenue [kpi], 100 [cy]", "revenue [kpi], 100 [cy]")]
        for o in ("helm", "fixed"):
            self.assertAlmostEqual(k.score(rec, o)["adjusted_macro_f1_score"], 0.5)

    def test_unknown_tag_raises(self):
        rec = [("revenue [kpi], 100 [cy]", "revenue [kpi], 2021 [year]")]
        for o in ("helm", "fixed"):
            with self.assertRaises(KeyError):
                k.score(rec, o)

    def test_upper_case_tag_ignored(self):
        self.assertEqual(k.parse_entities("revenue [KPI], 100 [cy]"), [k.Entity("100", "cy")])

    def test_hyphenated_tag_ignored(self):
        self.assertEqual(k.parse_entities("revenue [kpi-coref], 100 [cy]"), [k.Entity("100", "cy")])

    def test_trailing_period_drops_last(self):
        self.assertEqual(k.parse_entities("revenue [kpi], 100 [cy]."), [k.Entity("revenue", "kpi")])

    def test_copy_answer_parses(self):
        ents = k.parse_entities(k.copy_answer("x , y"))
        self.assertEqual([e.tag for e in ents], list(k.TAGS))
        self.assertTrue(all(e.phrase == "x , y" for e in ents))

    def test_main_runs(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            k.main()
        self.assertIn("KeyError", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
