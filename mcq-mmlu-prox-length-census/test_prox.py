"""Unit tests for audit 67 (hand-traced fixtures in cases.py). Apache-2.0."""

import unittest

import cases
import prox


def _reports(spec):
    """{lang: (lift, stemez_biopsy_pl, retention, ul_agreement, pick_longest, en_pick_longest)}"""
    out = {}
    for lang, (lift, bp, ret, agr, pl, en) in spec.items():
        out[lang] = {
            "ALL": {"n": 100, "lift": lift, "retention": ret, "ul_agreement": agr, "pick_longest": pl,
                    "en_pick_longest": en},
            "sub:stemez-biopsy": {"pick_longest": bp},
        }
    return out


def _join(langs, share=0.99):
    return {l: {"ok_share": share} for l in langs}


class TestJoinAndAccumulate(unittest.TestCase):
    def setUp(self):
        self.pro = {r["question_id"]: r for r in cases.PRO_ROWS}

    def test_unique_longest(self):
        self.assertEqual(prox.unique_longest(["a", "bbb", "cc"]), 1)
        self.assertIsNone(prox.unique_longest(["aa", "bb", "c"]))
        self.assertEqual(prox.unique_longest([" a ", "bb"]), 1)  # lengths after strip

    def test_join_statuses(self):
        best, status = prox.best_key(cases.X_ROWS, self.pro)
        self.assertEqual(best, cases.JOIN_TARGET["best"])
        self.assertEqual(status, cases.JOIN_TARGET["status"])

    def test_padding_and_empty(self):
        row = cases._x(10, 1, ["aa", "b", "cccc"], 2, "stemez-Biology")
        self.assertEqual(prox.join_row(row, self.pro, "question_id_src")[0], "ok")
        row["option_9"] = ""
        self.assertEqual(prox.join_row(row, self.pro, "question_id_src")[0], "ok")  # blank padding is fine
        row["option_1"] = "  "
        self.assertEqual(prox.join_row(row, self.pro, "question_id_src")[0], "empty_option")
        row = cases._x(10, 1, ["aa", "b"], 2, "stemez-Biology")  # slot 2 is N/A but k = 3
        self.assertEqual(prox.join_row(row, self.pro, "question_id_src")[0], "ok")

    def test_analyse_language(self):
        info, accs = prox.analyse_language(cases.X_ROWS, self.pro)
        self.assertEqual(accs, cases.ACC_TARGETS)
        self.assertEqual(info["key"], "question_id_src")
        self.assertEqual(info["joined"], 3)
        self.assertEqual(info["duplicates"], 1)
        self.assertEqual(info["src_match"], 3)
        self.assertEqual(info["options_identical_to_english"], 0)
        self.assertAlmostEqual(info["ok_share"], 3 / 7)

    def test_reports(self):
        _, accs = prox.analyse_language(cases.X_ROWS, self.pro)
        for key, want in cases.REPORT_TARGETS.items():
            got = prox.report(accs[key])
            self.assertEqual(set(got), set(want), key)
            for f, v in want.items():
                self.assertAlmostEqual(got[f], v, places=12, msg="%s %s" % (key, f))
        self.assertEqual(prox.report(prox.new_acc()), {"n": 0})


class TestPredictions(unittest.TestCase):
    def test_all_held(self):
        rep = _reports({
            "en": (0.07, 0.66, 1.00, 0.95, 0.180, 0.181),
            "de": (0.06, 0.60, 0.90, 0.80, 0.170, 0.181),
            "fr": (0.06, 0.62, 0.85, 0.75, 0.170, 0.181),
            "zh": (0.04, 0.55, 0.50, 0.60, 0.150, 0.181),
            "ja": (0.04, 0.52, 0.55, 0.60, 0.150, 0.181),
            "ko": (0.05, 0.51, 0.60, 0.65, 0.160, 0.181),
            "es": (0.07, 0.64, 0.95, 0.85, 0.175, 0.181),
        })
        p = prox.predictions(rep, _join(rep), n_expected=7, min_langs=5, p3_min=5)
        self.assertTrue(p["P1_every_language_joins_95pct"])
        self.assertTrue(p["P2_pick_longest_beats_chance_in_every_language"])
        self.assertTrue(p["P3_stemez_biopsy_at_least_half_in_25_languages"])     # 7 of 7 >= 0.5
        self.assertTrue(p["P4_median_retention_in_0_6_1_2"])                     # median 0.85
        self.assertTrue(p["P5_median_unique_longest_agreement_at_least_0_70"])   # median 0.75
        self.assertTrue(p["P6_en_config_reproduces_english_within_0_005"])       # gap 0.001
        self.assertTrue(p["P7_zh_ja_ko_below_median_retention"])                 # 0.50, 0.55, 0.60 < 0.85

    def test_all_failed(self):
        rep = _reports({
            "en": (0.07, 0.40, 1.00, 0.50, 0.170, 0.181),
            "de": (-0.01, 0.45, 0.40, 0.60, 0.170, 0.181),
            "zh": (0.04, 0.55, 0.50, 0.60, 0.150, 0.181),
            "ja": (0.04, 0.42, 0.55, 0.65, 0.150, 0.181),
            "ko": (0.05, 0.41, 1.10, 0.68, 0.160, 0.181),
        })
        join = _join(rep)
        join["de"]["ok_share"] = 0.90
        p = prox.predictions(rep, join, n_expected=5, min_langs=5, p3_min=3)
        self.assertFalse(p["P1_every_language_joins_95pct"])                     # de 0.90
        self.assertFalse(p["P2_pick_longest_beats_chance_in_every_language"])    # de lift < 0
        self.assertFalse(p["P3_stemez_biopsy_at_least_half_in_25_languages"])    # only zh
        self.assertFalse(p["P4_median_retention_in_0_6_1_2"])                    # median 0.55
        self.assertFalse(p["P5_median_unique_longest_agreement_at_least_0_70"])  # median 0.60
        self.assertFalse(p["P6_en_config_reproduces_english_within_0_005"])      # gap 0.011
        self.assertFalse(p["P7_zh_ja_ko_below_median_retention"])                # ko 1.10, ja = median

    def test_too_few_languages(self):
        rep = _reports({"de": (0.06, 0.60, 0.90, 0.80, 0.170, 0.181)})
        p = prox.predictions(rep, _join(rep), n_expected=29)
        self.assertFalse(p["P1_every_language_joins_95pct"])   # 1 of 29 attempted
        self.assertFalse(p["P2_pick_longest_beats_chance_in_every_language"])
        self.assertFalse(p["P6_en_config_reproduces_english_within_0_005"])  # no 'en'
        self.assertFalse(p["P7_zh_ja_ko_below_median_retention"])

    def test_langs(self):
        self.assertEqual(len(cases.LANGS), 29)
        self.assertEqual(len(set(cases.LANGS)), 29)
        for l in prox.NO_SPACE + ("en",):
            self.assertIn(l, cases.LANGS)


if __name__ == "__main__":
    unittest.main()
