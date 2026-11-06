"""Unit tests for audit 86 (standard library only). Every expected value in cases86.py was traced by hand against
gsm86.py before the sealed job ran. Apache-2.0."""

import unittest
from fractions import Fraction

import cases86 as C
import gsm86 as g


class TestHelmScorer(unittest.TestCase):
    def test_get_final_number(self):
        for text, want in C.FIX_FINAL:
            self.assertEqual(g.get_final_number(text), want, text)

    def test_unescaped_dot_kept(self):
        # HELM's regex has an unescaped '.', so '12a34' is one "number"; the transcription must keep that.
        self.assertEqual(g.get_final_number("12a34"), "12a34")

    def test_exact_match(self):
        for gold, pred, want in C.FIX_EM:
            self.assertEqual(g.exact_match(gold, pred), want)

    def test_final_number_exact_match(self):
        for gold, pred, want in C.FIX_FNEM:
            self.assertEqual(g.final_number_exact_match(gold, pred), want)

    def test_gsm_final(self):
        for text, want in C.FIX_GSM_FINAL:
            self.assertEqual(g.gsm_final(text), want)


class TestLabels(unittest.TestCase):
    def test_platinum_labels(self):
        labels, ans, counts = g.platinum_labels(C.FIX_GSM_ROWS, C.FIX_PLAT_ROWS)
        self.assertEqual(labels, C.FIX_LABELS)
        self.assertEqual(ans, C.FIX_PLAT_ANSWER)
        self.assertEqual(counts, C.FIX_LABEL_COUNTS)

    def test_norm(self):
        self.assertEqual(g.norm_q("  a \n b\t"), "a b")


class TestRuns(unittest.TestCase):
    def test_select_runs(self):
        self.assertEqual(g.select_runs(C.FIX_RUNS), C.FIX_RUNS_TARGET)

    def test_run_model_with_colon(self):
        self.assertEqual(g.run_model("gsm:model=amazon_nova-lite-v1:0,stop=none"), "amazon_nova-lite-v1:0")


class TestFlags(unittest.TestCase):
    def setUp(self):
        self.view = g.panel_view(C.FIX_PANEL, C.FIX_ANSWERS, C.FIX_KEYS)
        self.cons, self.unan, self.anyw, self.score = g.flags_from_view(self.view, C.FIX_KEYS, 3, 2)
        self.nokey = g.no_key_flags(self.view, 2)

    def test_view(self):
        self.assertEqual(self.view, C.FIX_VIEW)

    def test_flags(self):
        self.assertEqual(self.cons, C.FIX_CONS)
        self.assertEqual(self.unan, C.FIX_UNAN)
        self.assertEqual(self.anyw, C.FIX_ANYW)
        self.assertEqual(self.score, C.FIX_SCORE)
        self.assertEqual(self.nokey, C.FIX_NOKEY)

    def test_precision_recall(self):
        self.assertEqual(g.precision(self.cons, C.FIX_LAB4), C.FIX_PREC["cons"])
        self.assertEqual(g.precision(self.anyw, C.FIX_LAB4), C.FIX_PREC["anyw"])
        self.assertEqual(g.precision(self.nokey, C.FIX_LAB4), C.FIX_PREC["nokey"])
        self.assertEqual(g.precision(self.anyw, C.FIX_LAB4, kinds_all=g.REVIEWED), C.FIX_PREC["anyw_reviewed"])
        self.assertEqual(g.recall(self.cons, C.FIX_LAB4), C.FIX_RECALL["cons"])
        self.assertEqual(g.recall(self.nokey, C.FIX_LAB4), C.FIX_RECALL["nokey"])

    def test_auc(self):
        pos = [self.score[q] for q in self.score if C.FIX_LAB4[q] in g.ERR]
        neg = [self.score[q] for q in self.score if C.FIX_LAB4[q] in g.CLEAN]
        self.assertEqual(g.auc(pos, neg), C.FIX_AUC)
        self.assertIsNone(g.auc([], [1]))

    def test_budget(self):
        budget, want = C.FIX_BUDGET
        self.assertEqual(g.budget_precision(self.score, C.FIX_LAB4, budget), want)

    def test_ranked(self):
        self.assertEqual(g.ranked_models(C.FIX_ACC), C.FIX_RANKED)


class TestVerdicts(unittest.TestCase):
    def test_cases(self):
        for args, want in C.FIX_V_CASES:
            self.assertEqual(g.predictions86(*args, C.THRESHOLDS), want)

    def test_thresholds_frozen(self):
        self.assertEqual(C.THRESHOLDS["P2_min_precision"], Fraction(1, 2))
        self.assertEqual(C.THRESHOLDS["P4_min_auc"], Fraction(3, 4))
        self.assertEqual(C.THRESHOLDS["P5_min_recall"], Fraction(1, 4))
        self.assertEqual(C.THRESHOLDS["P6_min_flagged"], 10)
        self.assertEqual((C.PANEL_SIZE, C.MIN_AGREE, C.N_STRATA), (10, 6, 5))


if __name__ == "__main__":
    unittest.main()
