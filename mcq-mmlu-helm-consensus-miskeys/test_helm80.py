"""Unit tests for audit 80 (standard library only). Every expectation below is traced by hand in the comments.
Apache-2.0."""

import unittest
from fractions import Fraction

import helm80 as hm
import cases80 as C


def letters_to_indices(preds, questions):
    return {m: {q: hm.pred_index(p, questions[q][0]) for q, p in d.items()} for m, d in preds.items()}


class TestCopiedPanel(unittest.TestCase):
    def test_panel_and_flags(self):
        # Audit 77's fixture: letters become indices first (Z -> None; E is out of range for k=4 -> None).
        panel = hm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
        self.assertEqual(panel, ["m1", "m2", "m3"])
        idx = letters_to_indices(C.FIX_PREDS, C.FIX_QUESTIONS)
        self.assertIsNone(idx["m2"][6])
        self.assertIsNone(idx["m3"][6])
        flags, _t = hm.panel_flags(panel, idx, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
        self.assertEqual(flags, C.FIX_TARGET["flags"])

    def test_votes(self):
        self.assertEqual(hm.votes([0, 1, 1, None, 7], 4), ([1, 2, 0, 0], 2))


class TestRuns(unittest.TestCase):
    def test_parse_run(self):
        a = hm.parse_run("mmlu:subject=virology,method=multiple_choice_joint,model=amazon_nova-pro-v1:0,"
                         "eval_split=test,groups=mmlu_virology")
        self.assertEqual(a["model"], "amazon_nova-pro-v1:0")
        self.assertEqual(a["subject"], "virology")
        self.assertIsNone(hm.parse_run("gsm:model=x"))
        self.assertIsNone(hm.parse_run("mmlu:subject"))

    def test_select_runs(self):
        # x_a/anatomy has two runs: the one without model_deployment (0 extra args) wins, 1 duplicate dropped;
        # the separate-method run, the valid-split run and the gsm run are ignored.
        self.assertEqual(hm.select_runs(C.FIX_RUNS), C.FIX_RUNS_TARGET)

    def test_suite_version(self):
        self.assertLess(hm.suite_version("v1.2.0"), hm.suite_version("v1.13.0"))
        self.assertEqual(hm.suite_version("v1.0.0"), (1, 0, 0))


class TestUniverse(unittest.TestCase):
    def test_build_universe(self):
        # anatomy test ids 5,6,7,8 (positions 0-3; id1 is valid split, skipped). Q1 occurs twice (id5, id7) ->
        # both dropped (dup_dropped 2); Q3 has no correct tag -> no_gold 1; Q2 -> qid 0 at position 1.
        # virology: V1 (id20, gold 2, position 0) -> qid 1; V2 (id21, gold 3, position 1) -> qid 2.
        parsed = {s: hm.parse_instances(items) for s, items in C.FIX_INST.items()}
        self.assertNotIn("id1", parsed["anatomy"])
        qids, info, counts = hm.build_universe(parsed)
        t = C.FIX_UNIVERSE_TARGET
        self.assertEqual(qids, t["qids"])
        self.assertEqual(info, t["info"])
        self.assertEqual(counts, t["counts"])

    def test_map_predictions(self):
        # virology: id20 'C' -> 2, mapped 's' = option 2 (consistent, exact_match 1); id21 ' B' -> 1, mapped 'u'
        # is option 0 -> inconsistent; id99 unknown -> unmapped; the trial-1 row is skipped.
        # anatomy: id6 'The answer' is no letter, mapped 'g' is option 2 -> from_mapped; id5 (dropped duplicate)
        # and id8 (no gold) -> unmapped.
        parsed = {s: hm.parse_instances(items) for s, items in C.FIX_INST.items()}
        qids, _info, _c = hm.build_universe(parsed)
        for subj in ("virology", "anatomy"):
            got = hm.map_predictions(C.FIX_PRED[subj], parsed[subj], subj, qids)
            self.assertEqual(got, C.FIX_PRED_TARGET[subj], subj)

    def test_question_hash(self):
        self.assertEqual(hm.question_hash(" Q2 "), hm.question_hash("Q2"))
        self.assertEqual(len(hm.question_hash("Q2")), 16)


class TestRedux(unittest.TestCase):
    def test_redux_join_and_groups(self):
        # Rows 1-3 and 5 join (row 4 is the dropped duplicate Q1 -> no_match). Keys agree on rows 1, 3, 5
        # (row 2 publishes 1, HELM's gold is 2). V2 is labelled bad_question_clarity then ok -> conflict.
        parsed = {s: hm.parse_instances(items) for s, items in C.FIX_INST.items()}
        qids, _info, _c = hm.build_universe(parsed)
        got = hm.redux_join(C.FIX_REDUX, qids, C.FIX_GOLD)
        self.assertEqual(got, C.FIX_REDUX_TARGET)
        self.assertEqual(hm.groups(3, got[0]), C.FIX_GROUPS_TARGET)


class TestVerdicts(unittest.TestCase):
    def test_precision(self):
        # miskey flagged 2 (q1, q2) + other_error flagged 1 (q7) = 3; OK flagged 1 (q3) -> (3, 4).
        self.assertEqual(hm.flag_precision(C.FIX_FLAGS, C.FIX_G), (3, 4))

    def test_verdicts(self):
        # P2: 2*4 = 8 >= 5*1*2 = 10? no. P3: 2/2 >= 1/2 yes. P4: 3/4 > 65/359 yes.
        # P5: 1*4 = 4 >= 2*1*2 = 4 yes. P6: 1/2 > 3/4? no.
        v = hm.predictions80(C.FIX_G, C.FIX_FLAGS, C.FIX_CURVE, C.THRESHOLDS)
        self.assertEqual(v, C.FIX_VERDICTS)

    def test_empty_curve_is_false(self):
        v = hm.predictions80(C.FIX_G, C.FIX_FLAGS, {}, C.THRESHOLDS)
        self.assertFalse(v["P6_unanimous_more_precise"])


class TestFrozen(unittest.TestCase):
    def test_rule_and_thresholds(self):
        self.assertEqual((C.PANEL_SIZE, C.MIN_AGREE), (10, 6))
        self.assertEqual(C.THRESHOLDS["P4_baseline"], Fraction(65, 359))
        self.assertEqual(C.THRESHOLDS["P3_min_recall"], Fraction(1, 2))
        self.assertEqual((C.N_REDUX_ROWS, C.N_REDUX_MISKEY_ROWS, C.N_SUBJECTS), (5700, 106, 57))


if __name__ == "__main__":
    unittest.main()
