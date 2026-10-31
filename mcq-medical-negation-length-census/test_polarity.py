"""Unit tests for audit 68 (hand-traced fixtures in cases.py). Apache-2.0."""

import unittest

import cases
import polarity as pol


def _rep(n, lift, se=0.01):
    return {"n": n, "lift": lift, "se_lift": se}


class TestPolarity(unittest.TestCase):
    def test_polarity(self):
        for q, want in cases.POLARITY_CASES:
            self.assertEqual(pol.polarity(q), want, q)

    def test_last_sentence(self):
        self.assertEqual(pol.last_sentence("A b. C d? E f"), "E f")
        self.assertEqual(pol.last_sentence("  One only.  "), "One only.")

    def test_meta(self):
        for o, want in cases.META_CASES:
            self.assertEqual(pol.is_meta(o), want, o)

    def test_credits(self):
        for options, gold, lc, sc in cases.CREDIT_CASES:
            self.assertEqual(pol.longest_credit(options, gold), lc, options)
            self.assertEqual(pol.shortest_credit(options, gold), sc, options)

    def test_family(self):
        self.assertEqual(pol.family("stemez-Biology"), "stemez")
        self.assertEqual(pol.family("ori_mmlu-high_school_psychology"), "ori_mmlu")
        self.assertEqual(pol.family(""), "unknown")


class TestAccumulate(unittest.TestCase):
    def test_accumulators(self):
        self.assertEqual(pol.accumulate(cases.ROWS), cases.ACC_TARGETS)

    def test_reports(self):
        accs = pol.accumulate(cases.ROWS)
        for key, want in cases.REPORT_TARGETS.items():
            got = pol.report(accs[key])
            self.assertEqual(set(got), set(want), key)
            for f, v in want.items():
                self.assertAlmostEqual(got[f], v, places=12, msg="%s %s" % (key, f))

    def test_single_question_has_no_se(self):
        accs = pol.accumulate(cases.ROWS)
        self.assertIsNone(pol.report(accs["toy|split=s1|pol=pos"])["se_lift"])
        self.assertEqual(pol.report(pol.new_acc()), {"n": 0})

    def test_contrast(self):
        accs = pol.accumulate(cases.ROWS)
        c = pol.contrast(pol.report(accs["toy|pol=neg"]), pol.report(accs["toy|pol=pos"]))
        self.assertAlmostEqual(c["lift_diff"], -1 / 12, places=12)
        self.assertAlmostEqual(c["z"], cases.CONTRAST_Z, places=12)
        self.assertEqual(pol.contrast({}, {"n": 3}), {"lift_diff": None, "z": None})


class TestPredictions(unittest.TestCase):
    def test_mixed(self):
        r = {"medmcqa|split=validation": _rep(4000, 0.02), "medqa|split=test": _rep(1200, 0.01)}
        for d in pol.DATASETS:
            r[d + "|pol=neg"] = _rep(50, -0.01)
            r[d + "|pol=pos"] = _rep(100, 0.03)
        r["medmcqa|subject=A"] = _rep(1500, 0.01)
        r["medmcqa|subject=B"] = _rep(2000, -0.01)
        r["medmcqa|subject=C"] = _rep(50, -0.5)
        r["medmcqa|subject=A|pol=neg"] = _rep(1200, -0.2)
        r["medmcqa|nometa|pol=neg"] = _rep(40, 0.05)
        r["medmcqa|nometa|pol=pos"] = _rep(100, 0.02)
        p = pol.predictions(r)
        self.assertTrue(p["P1_medmcqa_validation_beats_chance"])
        self.assertTrue(p["P2_medqa_test_within_5_points_of_chance"])
        self.assertTrue(p["P3_negative_stems_lower_lift_in_all_three"])
        self.assertTrue(p["P4_medmcqa_negative_stems_below_chance"])
        self.assertTrue(p["P5_mmlu_pro_negative_lift_below_half_positive"])
        self.assertTrue(p["P6_medmcqa_validation_lift_at_least_medqa_test"])
        self.assertFalse(p["P7_medmcqa_80pct_of_large_subjects_beat_chance"])
        self.assertEqual(sorted(p["P7_detail"]["subjects"]), ["A", "B"])
        self.assertFalse(p["P8_medmcqa_contrast_survives_without_meta_options"])

    def test_too_few_negative_stems_is_not_held(self):
        r = {}
        for d in pol.DATASETS:
            r[d + "|pol=neg"] = _rep(10, -0.5)
            r[d + "|pol=pos"] = _rep(100, 0.03)
        p = pol.predictions(r)
        self.assertFalse(p["P3_negative_stems_lower_lift_in_all_three"])
        self.assertFalse(p["P4_medmcqa_negative_stems_below_chance"])
        self.assertFalse(p["P3_detail"]["medmcqa"]["scored"])

    def test_empty(self):
        p = pol.predictions({})
        for k, v in p.items():
            if not k.endswith("_detail"):
                self.assertFalse(v, k)


if __name__ == "__main__":
    unittest.main()
