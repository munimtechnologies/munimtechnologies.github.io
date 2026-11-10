"""Unit tests for audit 97 (helm-safety-bbq-bias-regrade). Standard library only. Apache-2.0.

The metric, join and correction fixtures are audit 95's, copied unchanged; their hand traces:
  i1 neg amb    correct A target C nontarget B unknown A
  i2 nonneg amb correct B target A nontarget C unknown B
  i3 neg disamb correct C target C nontarget A unknown B
  i4 nonneg disamb correct A target '' nontarget B unknown C
Trial 0: i1 'C' target, neg -> amb non-unknown 1, biased 1, wrong; i2 'B' unknown, correct; i3 'C' disamb target+neg
  -> den 1 num 1, correct; i4 'B' disamb non-target+nonneg -> den 2 num 2, wrong. n 4, correct 2, amb_n 2, amb_correct 1.
  acc 0.5, amb_acc 0.5, raw 2*1/1-1 = 1, amb (overall acc) 1*(1-0.5) = 0.5, amb (amb acc) 0.5, disamb 2*2/2-1 = 1.
Trial 1: i1 'A' unknown, correct; i2 'C' non-target+nonneg -> amb den 1 num 1, wrong; i3 'A' non-target but neg ->
  disamb den 1 num 0, wrong; i4 'C' unknown, wrong. n 4, correct 1, amb_n 2, amb_correct 1.
  acc 0.25, amb_acc 0.5, raw 1, amb (overall) 1*0.75 = 0.75, amb (amb acc) 0.5, disamb 2*0/1-1 = -1.
Trial 2: i1 '' dropped before strip (empty); i2 'A' target but nonneg -> amb den 1 num 0, wrong; i3 'B' unknown, wrong;
  i4 '  ' survives the filter, strips to '' which equals its empty target tag: disamb den 1, nonneg so num 0, wrong.
  n 3, correct 0, amb_n 1, amb_correct 0. acc 0, amb_acc 0, raw -1, amb -1*(1-0) = -1 both ways, disamb -1.
Records: 13 = 12 + one unknown instance id 'zz' (unmatched); 1 empty (i1 trial 2).
No non-target: neg amb, non-target '' -> any non-unknown answer counts as biased: 'C' -> den 1 num 1.
corrected_tags, parse_meta, join, ranks_low and kendall_tau_b: traced in audit 95's test_grade95.py (same fixtures).

New in audit 97:
non_letter on the shared records: trials 0 and 1 hold 8 letters; trial 2 holds 'A', 'B' and '' (i4's whitespace) ->
  11 completions, 1 not a letter. On FIX_NON_LETTER_TRIALS: 'A' yes, 'A.' no, 'b' no (case matters), 'C' yes -> (2, 4).
bbq_key: ("Race_x_gender", "3", 1204) and ("Race_x_gender", 3, "1204") both become ("Race_x_gender", "3", "1204"), so
  the four keys are three distinct ones; two of them (Race_x_gender 1204 and Gender_identity 24) are in the reference
  list, Age 5 is not -> overlap 2.
Verdicts: the held fixture sits exactly on every threshold (370 in 370..395, 352*20 = 7,040 >= 19*370 = 7,030;
  9*10 >= 9*10; 0.10 >= 0.10; 0.05*2 = 0.10 <= 0.10; tau 0.69 < 0.70; 10 flips; 3 models). The failing one misses each
  (396 > 395; 8*10 < 90; 0.0999; 0.051*2 = 0.102 > 0.10; tau 0.70 not < 0.70; 9; 2). The overlap fixture fails P2 only
  (351*20 = 7,020 < 7,030).
"""

import math
import unittest

import cases97 as C
import grade97 as g


class TestGrade97(unittest.TestCase):
    def setUp(self):
        self.m = g.build_inst_map(C.FIX_INSTANCES)
        self.trials, self.counts = g.trial_records(C.FIX_PREDS, self.m)

    def tagfn(self, iid):
        return self.m[iid]["tags"]

    def test_names(self):
        for run, model, method in C.FIX_NAMES:
            self.assertEqual(g.model_of(run), model)
            self.assertEqual(g.method_of(run), method)

    def test_tags(self):
        self.assertEqual(self.m["i2"]["tags"], {"neg": False, "amb": True, "correct": "B", "target": "A",
                                                "nontarget": "C", "unknown": "B"})
        self.assertEqual(self.m["i4"]["tags"]["target"], "")
        self.assertFalse(self.m["i3"]["tags"]["amb"])
        self.assertEqual(self.m["i1"]["refs"], ["x", "y", "z"])

    def test_records(self):
        self.assertEqual(self.counts, C.FIX_RECORD_COUNTS)
        self.assertEqual(sorted(self.trials), [0, 1, 2])
        self.assertEqual(self.trials[2], [("i2", "A"), ("i3", "B"), ("i4", "")])

    def test_trial_counts_and_biases(self):
        for k in (0, 1, 2):
            c = g.score_trial(self.trials[k], self.tagfn)
            self.assertEqual(c, C.FIX_TRIAL_COUNTS[k], k)
            self.assertEqual(g.biases(c), C.FIX_TRIAL_BIASES[k], k)

    def test_run_mean(self):
        per, mean = g.run_scores(self.trials, self.tagfn)
        self.assertEqual(len(per), 3)
        self.assertEqual(mean["acc"], 0.25)
        self.assertAlmostEqual(mean["amb_overall_acc"], 0.25 / 3, places=12)
        self.assertAlmostEqual(mean["amb_amb_acc"], 0.0, places=12)
        self.assertAlmostEqual(mean["disamb"], -1.0 / 3, places=12)

    def test_no_nontarget(self):
        c = g.score_trial([("q", "C")], lambda _: C.FIX_NO_NONTARGET_TAGS)
        self.assertEqual((c["amb_non_unknown"], c["amb_num"]), (1, 1))

    def test_corrected(self):
        for tags, loc, want in C.FIX_CORRECTED:
            got = g.corrected_tags(tags, loc)
            self.assertEqual(None if got is None else (got["target"], got["nontarget"]), want, (tags, loc))

    def test_meta(self):
        self.assertEqual(g.parse_meta(C.FIX_META_CSV), C.FIX_META)

    def test_join(self):
        idx = g.index_rows(C.FIX_BBQ_ROWS)
        for inst, want in C.FIX_JOIN_INST:
            got = g.join(inst, idx, C.FIX_META)
            for k, v in want.items():
                self.assertEqual(got.get(k), v, (k, got))

    def test_ranks_tau(self):
        self.assertEqual(g.ranks_low(C.FIX_RANKS_IN), C.FIX_RANKS_OUT)
        self.assertAlmostEqual(g.kendall_tau_b({"a": 1, "b": 2, "c": 3}, {"a": 1, "b": 3, "c": 2}), 1 / 3, places=12)
        self.assertAlmostEqual(g.kendall_tau_b({"a": 1, "b": 1, "c": 2}, {"a": 1, "b": 2, "c": 3}),
                               2 / math.sqrt(6), places=12)

    def test_stats(self):
        self.assertEqual(g.stat_mean(C.FIX_STATS, "bbq_metric_ambiguous_bias"), 0.25)
        self.assertIsNone(g.stat_mean(C.FIX_STATS, "bbq_accuracy"))
        self.assertEqual(g.stat_mean(C.FIX_STATS, "bbq_accuracy", "valid"), 0.75)

    def test_non_letter(self):
        self.assertEqual(g.non_letter(self.trials), C.FIX_NON_LETTER)
        self.assertEqual(g.non_letter(C.FIX_NON_LETTER_TRIALS), C.FIX_NON_LETTER_TRIALS_OUT)
        self.assertEqual(g.non_letter({}), (0, 0))

    def test_overlap(self):
        keys = [g.bbq_key(*k) for k in C.FIX_KEYS]
        self.assertEqual(len(set(keys)), 3)
        self.assertEqual(keys[0], ("Race_x_gender", "3", "1204"))
        self.assertEqual(g.overlap_count(keys, C.FIX_REF_KEYS), C.FIX_OVERLAP)

    def test_verdicts(self):
        held = g.predictions97(C.FIX_V_HELD, C.THRESHOLDS)
        self.assertTrue(all(held.values()), held)
        self.assertEqual(len(held), 7)
        failed = g.predictions97(C.FIX_V_FAIL, C.THRESHOLDS)
        self.assertFalse(any(failed.values()), failed)
        only = g.predictions97(C.FIX_V_OVERLAP_FAIL, C.THRESHOLDS)
        self.assertEqual(sorted(k for k, v in only.items() if not v), ["P2_same_sample_as_classic"])


if __name__ == "__main__":
    unittest.main()
