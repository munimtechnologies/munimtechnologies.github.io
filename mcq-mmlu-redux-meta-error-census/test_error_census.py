"""Tests for the META-OPTION x ANNOTATION-ERROR census (audit 58). Standard library unittest only.

Checks the hand-traced error fixture for EXACT equality against ERROR_TARGET, then the derived report values
(rates over judged questions, pooled 2x2 chi-square, subject-stratified CMH) against hand computations.
"""

import unittest

import error_census as ec
import cases


class TestErrorFixtureExact(unittest.TestCase):
    def test_run_error_census_equals_target(self):
        self.assertEqual(ec.run_error_census(cases.ERROR_FIXTURE_ROWS), cases.ERROR_TARGET)


class TestHelpers(unittest.TestCase):
    def test_normalise_and_class(self):
        self.assertEqual(ec.normalise_label(" OK "), "ok")
        self.assertEqual(ec.normalise_label(None), "")
        self.assertEqual(ec.error_class("ok"), "ok")
        self.assertEqual(ec.error_class("wrong_groundtruth"), "error")
        self.assertEqual(ec.error_class("bad_options_clarity"), "error")
        self.assertEqual(ec.error_class("expert"), "unsure")
        self.assertEqual(ec.error_class("typo_label"), "unknown")
        self.assertEqual(ec.error_class(""), "unknown")

    def test_shape_mmlu(self):
        self.assertEqual(ec.shape_mmlu(["a", "b", "c", "d"], 2), (["0", "1", "2", "3"], ["a", "b", "c", "d"], "2"))
        self.assertEqual(ec.shape_mmlu(["a", None], 0), (["0", "1"], ["a", ""], "0"))
        self.assertEqual(ec.shape_mmlu(None, 1), (None, None, None))
        self.assertEqual(ec.shape_mmlu(["a", "b"], None), (["0", "1"], ["a", "b"], None))

    def test_two_by_two_hand_computed(self):
        # N=200, ad-bc=-1000 -> 200*1e6 / (100*100*30*170) = 200/51
        t = ec.two_by_two(10, 90, 20, 80)
        self.assertAlmostEqual(t["chi_square_stat"], 200 / 51)
        self.assertAlmostEqual(t["rate_1"], 0.1)
        self.assertAlmostEqual(t["rate_2"], 0.2)
        self.assertAlmostEqual(t["risk_ratio"], 0.5)
        self.assertAlmostEqual(t["min_expected_cell"], 15.0)
        self.assertEqual(t["rejected_0.05"], True)
        self.assertEqual(t["rejected_0.001"], False)

    def test_two_by_two_empty_margin(self):
        t = ec.two_by_two(0, 0, 3, 4)
        self.assertIsNone(t["chi_square_stat"])
        self.assertIsNone(t["rate_1"])
        self.assertIsNone(t["risk_ratio"])

    def test_cmh_hand_computed(self):
        # S1 (2,2,1,2): N=7, E=12/7, a-E=2/7, V=144/294.  S2 (1,0,0,1): N=2, E=1/2, a-E=1/2, V=1/4.
        # stat = (11/14)^2 / (145/196) = 121/145.  MH OR = (4/7 + 1/2) / (2/7 + 0) = 15/4.
        r = ec.cmh([(2, 2, 1, 2), (1, 0, 0, 1), (0, 0, 0, 1)])   # third stratum N=1 -> skipped
        self.assertAlmostEqual(r["cmh_stat"], 121 / 145)
        self.assertAlmostEqual(r["sum_observed_minus_expected"], 11 / 14)
        self.assertAlmostEqual(r["sum_variance"], 145 / 196)
        self.assertAlmostEqual(r["mh_odds_ratio"], 15 / 4)
        self.assertEqual(r["n_strata"], 3)
        self.assertEqual(r["n_informative_strata"], 2)
        self.assertEqual(r["rejected_0.05"], False)

    def test_cmh_uninformative(self):
        r = ec.cmh([(0, 0, 1, 2), (2, 2, 0, 0)])
        self.assertIsNone(r["cmh_stat"])
        self.assertIsNone(r["mh_odds_ratio"])
        self.assertEqual(r["n_informative_strata"], 0)


class TestErrorReport(unittest.TestCase):
    def setUp(self):
        self.rep = ec.error_report(ec.run_error_census(cases.ERROR_FIXTURE_ROWS))

    def test_counts_and_labels(self):
        self.assertEqual(self.rep["n_rows"], 10)
        self.assertEqual(self.rep["n_invalid"], 1)
        self.assertEqual(self.rep["n_subjects"], 3)
        self.assertEqual(self.rep["undocumented_labels"], ["typo_label"])

    def test_plain_group(self):
        p = self.rep["by_group"]["plain"]
        self.assertEqual((p["n"], p["n_ok"], p["n_error"], p["n_unsure"], p["n_unknown"], p["n_judged"]),
                         (5, 2, 1, 1, 1, 3))
        self.assertAlmostEqual(p["error_rate"], 1 / 3)
        self.assertAlmostEqual(p["answer_set_error_rate"], 0.0)
        self.assertAlmostEqual(p["error_type_rates"]["wrong_groundtruth"], 1 / 3)

    def test_meta_and_all_groups(self):
        m = self.rep["by_group"]["any_meta"]
        self.assertEqual((m["n"], m["n_ok"], m["n_error"], m["n_judged"], m["n_answer_set_error"]), (4, 2, 2, 4, 2))
        self.assertAlmostEqual(m["error_rate"], 0.5)
        a = self.rep["by_group"]["all"]
        self.assertEqual((a["n"], a["n_ok"], a["n_error"], a["n_unsure"], a["n_unknown"]), (9, 4, 3, 1, 1))
        self.assertAlmostEqual(a["error_rate"], 3 / 7)

    def test_by_category(self):
        c = self.rep["by_category"]
        self.assertEqual(sorted(c), ["aota", "nota", "plain", "roman"])
        self.assertEqual((c["aota"]["n_judged"], c["aota"]["n_error"], c["aota"]["n_answer_set_error"]), (2, 1, 1))
        self.assertEqual((c["nota"]["n_judged"], c["nota"]["n_error"]), (1, 1))
        self.assertEqual((c["roman"]["n_judged"], c["roman"]["n_error"]), (1, 0))

    def test_pooled_and_stratified(self):
        t = self.rep["meta_vs_plain_error_pooled"]
        self.assertEqual(t["table"], [[2, 2], [1, 2]])
        self.assertAlmostEqual(t["chi_square_stat"], 28 / 144)    # 7*(4-2)^2 / (4*3*3*4)
        self.assertAlmostEqual(t["risk_ratio"], 1.5)
        self.assertAlmostEqual(t["min_expected_cell"], 9 / 7)
        u = self.rep["aota_vs_plain_answer_set_pooled"]
        self.assertEqual(u["table"], [[1, 1], [0, 3]])
        self.assertAlmostEqual(u["chi_square_stat"], 45 / 24)     # 5*(3-0)^2 / (2*3*1*4)
        self.assertIsNone(u["risk_ratio"])                        # plain rate is 0
        # meta and plain never share a subject in the fixture -> no informative stratum
        s = self.rep["meta_vs_plain_error_by_subject_cmh"]
        self.assertIsNone(s["cmh_stat"])
        self.assertEqual(s["n_strata"], 3)
        self.assertEqual(s["n_informative_strata"], 0)

    def test_by_subject(self):
        b = self.rep["by_subject"]
        self.assertEqual((b["s1"]["n_meta"], b["s1"]["n_plain"]), (0, 4))
        self.assertIsNone(b["s1"]["meta_error_rate"])
        self.assertAlmostEqual(b["s1"]["plain_error_rate"], 1 / 3)
        self.assertEqual((b["s2"]["n_meta"], b["s2"]["meta_judged"]), (4, 4))
        self.assertAlmostEqual(b["s2"]["meta_error_rate"], 0.5)
        self.assertIsNone(b["s3"]["plain_error_rate"])            # only an undocumented label


if __name__ == "__main__":
    unittest.main()
