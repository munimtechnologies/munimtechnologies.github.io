"""Unit tests for audit 76 (standard library only). Apache-2.0."""

import unittest
from fractions import Fraction

import cases76 as C
import inherit_models as im


class TestClassify(unittest.TestCase):
    def test_pred_index(self):
        self.assertEqual(im.pred_index("A", 4), 0)
        self.assertEqual(im.pred_index(" j ", 10), 9)
        self.assertIsNone(im.pred_index("E", 4))      # out of range for 4 options
        self.assertIsNone(im.pred_index(None, 10))
        self.assertIsNone(im.pred_index("AB", 10))
        self.assertIsNone(im.pred_index("K", 10))

    def test_classify(self):
        self.assertEqual(im.classify("A", 0, 1, 4), "key")
        self.assertEqual(im.classify("B", 0, 1, 4), "expert")
        self.assertEqual(im.classify("C", 0, 1, 4), "other")
        self.assertEqual(im.classify(None, 0, 1, 4), "none")
        self.assertEqual(im.classify("J", 2, 5, 10), "other")
        self.assertEqual(im.classify("F", 2, 5, 10), "expert")


class TestTally(unittest.TestCase):
    def test_other_per_distractor(self):
        t = im.new_tally()
        im.add_tally(t, "other", 10)   # 1/8
        im.add_tally(t, "other", 4)    # 1/2
        im.add_tally(t, "expert", 4)
        self.assertEqual(t["other_per_distractor"], Fraction(5, 8))
        self.assertEqual((t["n"], t["key"], t["expert"], t["other"], t["none"]), (3, 0, 1, 2, 0))
        r = im.tally_report(t)
        self.assertAlmostEqual(r["expert_vs_average_distractor"], 1.6)   # 1 / (5/8)
        self.assertAlmostEqual(r["expert_rate"], 1 / 3)

    def test_ctrl(self):
        c = im.new_ctrl()
        im.add_ctrl(c, "A", 0, 4)
        im.add_ctrl(c, "B", 0, 4)
        im.add_ctrl(c, None, 0, 4)
        im.add_ctrl(c, "C", 2, 10)
        self.assertEqual(c, {"n": 4, "correct": 2})
        self.assertEqual(im.ctrl_accuracy(c), 0.5)


class TestFixture(unittest.TestCase):
    """Trace: m1 picks the expert on q1 (B) and q2 (F); m2 the key on q1 (A) and J on q2 (other, k=10 -> 1/8);
    m3 C on q1 (other, k=4 -> 1/2) and nothing on q2. Pooled: expert 2, key 1, other-per-distractor 5/8.
    P2 2 > 1 HELD; P3 only m1 has expert > key (1 of 3 < 3/4) FAILED; P4 2 >= 3 * 5/8 = 1.875 HELD;
    P5 key rates 0, .5, 0 vs control .5, .6, .1 -> 3 of 3 HELD; P6 q1 1 vs 1 no, q2 1 vs 0 yes -> 1 of 2 < 3/5
    FAILED; P7 primary = q1 only: expert 1 vs key 1 FAILED."""

    def run_fixture(self):
        models, per_q = {}, {}
        for m, q, pred in C.FIX_PREDS:
            k, key_i, exp_i, basis = C.FIX_QUESTIONS[q]
            cls = im.classify(pred, key_i, exp_i, k)
            rec = models.setdefault(m, {"all": im.new_tally(), "primary": im.new_tally()})
            im.add_tally(rec["all"], cls, k)
            if basis == "primary":
                im.add_tally(rec["primary"], cls, k)
            im.add_tally(per_q.setdefault(q, im.new_tally()), cls, k)
        for m in models:
            models[m]["control_accuracy"] = C.FIX_CONTROL_ACCURACY[m]
        return models, per_q

    def test_models_and_questions(self):
        models, per_q = self.run_fixture()
        self.assertEqual({m: models[m]["all"] for m in models}, C.FIX_TARGET["models"])
        self.assertEqual(per_q, C.FIX_TARGET["per_question"])

    def test_verdicts(self):
        models, per_q = self.run_fixture()
        verdicts, pooled, pooled_primary = im.predictions(models, per_q, C.FIX_MIN_TARGETS, C.THRESHOLDS)
        self.assertEqual(verdicts, C.FIX_TARGET["verdicts"])
        self.assertEqual((pooled["expert"], pooled["key"]), (2, 1))
        self.assertEqual(pooled["other_per_distractor"], Fraction(5, 8))
        self.assertEqual((pooled_primary["expert"], pooled_primary["key"]), (1, 1))

    def test_min_targets_excludes_small_models(self):
        models, per_q = self.run_fixture()
        verdicts, _p, _pp = im.predictions(models, per_q, 3, C.THRESHOLDS)
        self.assertEqual(verdicts["P3_counts"], [0, 0])
        self.assertFalse(verdicts["P3_most_models_expert_over_key"])
        self.assertFalse(verdicts["P5_key_rate_below_control_every_model"])


class TestFrozenTargets(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(len(C.TARGETS), C.N_TARGETS)
        self.assertEqual(len(set(t[0] for t in C.TARGETS)), C.N_TARGETS)
        self.assertEqual(sum(1 for t in C.TARGETS if t[4] == "primary"), C.N_PRIMARY)
        self.assertEqual(sum(1 for t in C.TARGETS if t[4] == "digits_0_based"), C.N_TARGETS - C.N_PRIMARY)
        self.assertEqual(len(C.MISKEY_IDS), C.N_MISKEY_IDS)

    def test_rows_are_valid(self):
        for qid, src, key, exp, basis in C.TARGETS:
            self.assertIn(qid, C.MISKEY_IDS)
            self.assertTrue(src.startswith("ori_mmlu-"))
            self.assertIn(key, im.LETTERS)
            self.assertIn(exp, im.LETTERS)
            self.assertNotEqual(key, exp)
            self.assertIn(basis, ("primary", "digits_0_based"))

    def test_audit75_categories(self):
        # audit 75: 18 college_chemistry and 6 virology targets carry primary corrections; all 24 primary rows
        # come from those two subjects.
        prim = [t for t in C.TARGETS if t[4] == "primary"]
        self.assertEqual(sum(1 for t in prim if t[1] == "ori_mmlu-college_chemistry"), 18)
        self.assertEqual(sum(1 for t in prim if t[1] == "ori_mmlu-virology"), 6)

    def test_model_name(self):
        self.assertEqual(C.model_name("model_outputs_claude-3-5-haiku-20241022_5shots.json.zip"),
                         "claude-3-5-haiku-20241022_5shots")
        self.assertEqual(C.model_name("model_outputs_gemini-3.1-pro_5-shots.zip"), "gemini-3.1-pro_5-shots")
        self.assertEqual(len(C.ARCHIVES), 48)


if __name__ == "__main__":
    unittest.main()
