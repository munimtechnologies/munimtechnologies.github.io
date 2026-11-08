"""Unit tests for audit 89 v2 (standard library only). Run: python -m unittest -v. Apache-2.0.

Hand traces (v1, unchanged):
- Categories: 'Valid. Two ...' lower-cases to first token 'valid.' -> stripped 'valid' -> valid (MedQA);
  'Incorrect\\nRelease energy' normalises to 'incorrect release energy' -> first word 'incorrect' -> invalid
  (OpenBookQA); 'Validity unclear' -> 'validity' -> unclear; 'Correct' in MedQA is not a MedQA word -> unclear;
  'Correctly keyed?' -> 'correctly' -> unclear; any other split -> unclear; '' -> unclear.
- Suggested option: 'incorrect release energy' -> rest 'release energy' equals option 1 after normalising
  'Release  energy' -> 1. 'incorrect: slow, because it cools' -> first token 'incorrect:' strips to 'incorrect',
  rest 'slow, because it cools' equals no option; only 'slow' is a prefix ('slower' is not: 'slow,' differs at the
  fifth character) -> 1. 'incorrect slower one': 'slow' and 'slower' are both prefixes -> None. 'correct' -> None.
  'incorrect' alone -> rest '' -> no option equals '' and no non-empty option is a prefix of '' -> None.
- Instances: id5 is not a test item and is dropped; id3 sorts before id7 by number, so id3 is qid 0 (position 0,
  gold 0) and id7 is qid 1 (position 1, gold 1).
- Mapping: id7 predicts ' B' -> letter index 1, mapped_output 'b' agrees; id3 predicts 'none of these' (not a
  letter) but mapped_output 'd' equals option 1 -> 1; the train_trial_index 1 item is ignored -> {1: 1, 0: 1}.
  em_correct: id7 exact_match 1 -> 1; id3 exact_match 0 is present, so no quasi fallback -> em_correct 1,
  em_from_quasi 0.
- Placement: 'What  is X?' normalises to qid 0's key -> exact; 'Dup Q' with unknown options matches two questions
  by text -> ambiguous; 'Missing' -> none.
- Verdicts case 1: 8/20 > 2/25; AUC 7/10 >= 3/5; 2/25 <= 1/4; 3/40 <= 1/4; 8/20 >= 1/3 -> all held.
  Case 2: 4 invalid < 5 (P2, P3, P6 undecidable), 9 valid < 10 (P4 undecidable); 12/40 > 1/4 -> P5 false.
  Case 3: boundaries: 1/3 > 1/4; 3/5 >= 3/5; 1/4 <= 1/4; 10/40 = 1/4 <= 1/4; 5/15 = 1/3 >= 1/3 -> all held.
  Case 4: 2/10 is not > 2/10; a missing AUC is undecidable; 2/10 <= 1/4; 0/48 <= 1/4; 2/10 < 1/3.

Hand traces (v2 additions):
- Splits ('valid', 'test'): id3, id5 and id7 are all kept. Positions by instance number: id3 0, id5 1, id7 2; the
  universe orders by the same numbers, so qids are id3 0 (2 options, gold 0), id5 1 (1 option 'e', gold 0), id7 2
  (2 options, gold 1).
- Quasi fallback on that universe: id7 'B' -> 1, mapped 'b' = option 1 (consistent), no exact_match -> quasi 1.0
  counts (em_correct 1, em_from_quasi 1); id5 'A' -> 0 of 1 option, mapped 'e' = option 0 (consistent), quasi 1.0
  (em_correct 2, em_from_quasi 2); id3 'B' -> 1, mapped 'd' = option 1 (consistent), exact_match 0 is present and
  wins over quasi 1.0 -> not counted. Result {2: 1, 1: 0, 0: 1}; valid 3, consistent 3, em_correct 2,
  em_from_quasi 2.
- The benchmark settings: med_qa uses ('valid', 'test'); openbookqa keeps ('test',) as in v1.
"""

import unittest
from fractions import Fraction

import base89 as qm
import cases89 as C
import fb89 as fb


class TestReviews(unittest.TestCase):
    def test_categories(self):
        for split, review, want in C.FIX_CAT:
            self.assertEqual(fb.fb_category(split, review), want, (split, review))

    def test_suggested_option(self):
        for review, options, want in C.FIX_SUGGEST:
            self.assertEqual(fb.suggested_option(review, options), want, review)

    def test_answer_keys_copied(self):
        for s, want in C.FIX_AK:
            self.assertEqual(qm.parse_answer_key(s), want, s)


class TestHelm(unittest.TestCase):
    def test_instances_and_universe(self):
        inst = qm.parse_instances(C.FIX_INSTANCES)
        self.assertEqual(sorted(inst), ["id3", "id7"])
        qids, info, counts = qm.build_universe({"med_qa": inst})
        self.assertEqual(info, C.FIX_UNIVERSE_INFO)
        self.assertEqual(counts, {"dup_dropped": 0, "no_gold": 0})
        self.assertEqual(qids[("med_qa", ("Q one", ("a", "b")))], 1)

    def test_map_predictions(self):
        inst = qm.parse_instances(C.FIX_INSTANCES)
        qids, _info, _c = qm.build_universe({"med_qa": inst})
        out, c = qm.map_predictions(C.FIX_PREDS, inst, "med_qa", qids)
        self.assertEqual(out, C.FIX_MAPPED)
        self.assertEqual((c["valid"], c["from_mapped"], c["other_trial"], c["consistent"], c["em_correct"],
                          c["em_from_quasi"]), (1, 1, 1, 1, 1, 0))

    def test_v2_both_splits(self):
        inst = qm.parse_instances(C.FIX_INSTANCES, C.FIX_SPLITS_VT)
        self.assertEqual(sorted(inst), ["id3", "id5", "id7"])
        qids, info, counts = qm.build_universe({"med_qa": inst})
        self.assertEqual(info, C.FIX_UNIVERSE_INFO_VT)
        self.assertEqual(counts, {"dup_dropped": 0, "no_gold": 0})
        self.assertEqual(qids[("med_qa", ("Q three", ("e",)))], 1)

    def test_v2_quasi_fallback(self):
        inst = qm.parse_instances(C.FIX_INSTANCES, C.FIX_SPLITS_VT)
        qids, _info, _c = qm.build_universe({"med_qa": inst})
        out, c = qm.map_predictions(C.FIX_PREDS_QUASI, inst, "med_qa", qids)
        self.assertEqual(out, C.FIX_MAPPED_QUASI)
        for k, v in C.FIX_QUASI_COUNTS.items():
            self.assertEqual(c[k], v, k)

    def test_v2_bench_splits(self):
        self.assertEqual(C.BENCHES["med_qa"]["splits"], ("valid", "test"))
        self.assertEqual(C.BENCHES["openbookqa"]["splits"], ("test",))

    def test_select_runs_prefix(self):
        rs = {"med_qa:model=a_x": "v1.0.0", "med_qa:model=a_x,extra=1": "v1.2.0", "med_qa:model=b_y": "v1.1.0",
              "commonsense:dataset=openbookqa,method=multiple_choice_joint,model=a_x": "v1.0.0"}
        best, dropped = qm.select_gsm_runs(rs, C.BENCHES["med_qa"]["prefix"])
        self.assertEqual(best, {"a_x": ("med_qa:model=a_x,extra=1", "v1.2.0"), "b_y": ("med_qa:model=b_y", "v1.1.0")})
        self.assertEqual(dropped, 1)
        best2, _d = qm.select_gsm_runs(rs, C.BENCHES["openbookqa"]["prefix"])
        self.assertEqual(sorted(best2), ["a_x"])

    def test_place(self):
        out, counts = qm.place(C.FIX_PLACE_ROWS, C.FIX_QIDS)
        self.assertEqual(out, C.FIX_PLACE)
        self.assertEqual(counts, C.FIX_PLACE_COUNTS)


class TestStats(unittest.TestCase):
    def test_consensus_flag_copied(self):
        self.assertEqual(qm.flag_question([1, 6, 3, 0], 0, 6), (True, 1, 6))
        self.assertEqual(qm.flag_question([6, 3, 1, 0], 0, 6), (False, 1, 3))
        self.assertEqual(qm.margin([2, 6, 1, 1], 0), 4)

    def test_auc_copied(self):
        self.assertEqual(qm.auc([3, 2], [1, 2]), Fraction(7, 8))
        self.assertIsNone(qm.auc([], [1]))

    def test_verdicts(self):
        for args, want in C.FIX_V_CASES:
            self.assertEqual(fb.predictions89(*args, C.THRESHOLDS), want)


if __name__ == "__main__":
    unittest.main()
