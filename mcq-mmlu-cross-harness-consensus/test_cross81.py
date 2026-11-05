"""Unit tests for audit 81 (standard library only). Every expectation below is traced by hand in the comments.
Apache-2.0."""

import unittest
from fractions import Fraction

import cross81 as cm
import cases81 as C


def letters_to_indices(preds, questions):
    return {m: {q: cm.pred_index(p, questions[q][0]) for q, p in d.items()} for m, d in preds.items()}


class TestCopiedPanel(unittest.TestCase):
    def test_panel_and_flags(self):
        # Audit 77's fixture: letters become indices first (Z -> None; E is out of range for k=4 -> None).
        panel = cm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
        self.assertEqual(panel, ["m1", "m2", "m3"])
        idx = letters_to_indices(C.FIX_PREDS, C.FIX_QUESTIONS)
        self.assertIsNone(idx["m2"][6])
        self.assertIsNone(idx["m3"][6])
        flags, _t = cm.panel_flags(panel, idx, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
        self.assertEqual(flags, C.FIX_TARGET["flags"])

    def test_votes(self):
        self.assertEqual(cm.votes([0, 1, 1, None, 7], 4), ([1, 2, 0, 0], 2))


class TestCopiedHelm(unittest.TestCase):
    def test_select_runs(self):
        # As audit 80: x_a/anatomy keeps the run without model_deployment (1 duplicate dropped); the other method,
        # the valid split and the gsm run are ignored.
        self.assertEqual(cm.select_runs(C.FIX_RUNS), C.FIX_RUNS_TARGET)

    def test_universe_predictions_redux(self):
        # As audit 80: Q1 duplicated (dropped, 2 copies), Q3 without gold; qids anatomy/Q2 -> 0, V1 -> 1, V2 -> 2.
        parsed = {s: cm.parse_instances(items) for s, items in C.FIX_INST.items()}
        qids, info, counts = cm.build_universe(parsed)
        t = C.FIX_UNIVERSE_TARGET
        self.assertEqual((qids, info, counts), (t["qids"], t["info"], t["counts"]))
        for subj in ("virology", "anatomy"):
            self.assertEqual(cm.map_predictions(C.FIX_PRED[subj], parsed[subj], subj, qids),
                             C.FIX_PRED_TARGET[subj], subj)
        got = cm.redux_join(C.FIX_REDUX, qids, C.FIX_GOLD)
        self.assertEqual(got, C.FIX_REDUX_TARGET)
        self.assertEqual(cm.groups(3, got[0]), C.FIX_GROUPS_TARGET)


class TestJoin(unittest.TestCase):
    def test_helm_options_and_stems(self):
        self.assertEqual(cm.helm_options(C.FIX_J_QIDS), C.FIX_J_HELM_OPTS)
        self.assertEqual(cm.stem_index(C.FIX_J_QIDS), C.FIX_J_STEMS)

    def test_pro_subject(self):
        self.assertEqual(cm.pro_subject("ori_mmlu-high_school_biology"), "high_school_biology")
        self.assertIsNone(cm.pro_subject("stemez-Biology"))
        self.assertIsNone(cm.pro_subject(None))

    def test_join_pro_helm(self):
        # 10: virology/'V1' -> [0]; shares a, b, c with HELM 0 (3) -> claims 0.
        # 11: 'V2' -> [1, 2]; shares e, f, g with 1 (3) but only e, f with 2 (2) -> claims 1.
        # 12: 'V2' shares 4 with both 1 and 2 -> ambiguous_helm.
        # 13: anatomy/'A1' -> [3]; shares only i, j -> stem_only.
        # 14 and 15: anatomy/'A2' -> [4] (4 and 3 shared) -> both claim 4 -> pro_dup 2, HELM 4 not joined.
        # 16: stemez, skipped (not an MMLU-derived row). 17: 'Nope' -> no_stem. 18: virology/'A1' -> no_stem.
        # pro_mmlu_rows = 8 (all but 16); joined = 2.
        self.assertEqual(cm.join_pro_helm(C.FIX_J_PRO, C.FIX_J_STEMS, C.FIX_J_HELM_OPTS), C.FIX_J_TARGET)

    def test_same_key(self):
        self.assertTrue(cm.same_key(["a", "b"], 1, ["b ", "a"], 0))
        self.assertFalse(cm.same_key(["a", "b"], 0, ["b", "a"], 0))


class TestAgree(unittest.TestCase):
    def test_agree_flags(self):
        # q0: HELM consensus 1 = 'b', Pro consensus 1 = 'b' -> agreed (True, 1).
        # q1: HELM 2 = 'g', Pro 3 = 'z' -> different text -> (False, None).
        # q3: Pro does not flag -> (False, None).
        # q4: HELM 3 = 'p', Pro 0 = 'p' (options reordered in Pro) -> agreed (True, 3).
        got = cm.agree_flags(C.FIX_A_J, C.FIX_A_PAIRS, C.FIX_A_HELM_FLAGS, C.FIX_A_PRO_FLAGS, C.FIX_J_HELM_OPTS,
                             C.FIX_A_PRO_OPTS)
        self.assertEqual(got, C.FIX_A_TARGET)

    def test_restrict(self):
        self.assertEqual(cm.restrict({"miskey": [1, 2], "ok": [3, 5]}, {2, 3}), {"miskey": [2], "ok": [3]})


class TestVerdicts(unittest.TestCase):
    def test_precisions(self):
        # HELM: miskey 1, 2 + other 7 = 3 error-labelled; OK 3, 4, 5 flagged -> (3, 6).
        # Pro: miskey 1 = 1; other 7 not flagged; OK 3, 4, 6 -> (1, 4). Agree: miskey 1; OK 3 -> (1, 2).
        self.assertEqual(cm.flag_precision(C.FIX_V_HELM, C.FIX_V_GJ), (3, 6))
        self.assertEqual(cm.flag_precision(C.FIX_V_PRO, C.FIX_V_GJ), (1, 4))
        self.assertEqual(cm.flag_precision(C.FIX_V_AGREE, C.FIX_V_GJ), (1, 2))

    def test_verdicts(self):
        # P2: 1/2 > 3/6? no (equal). P3: 1/2 > 1/4 yes. P4: miskeys HELM-flagged 2 (q1, q2), agreed 1 -> 1/2 >= 1/2
        # yes. P5: OK HELM-flagged 3, agreed 1: 1*2*2 = 4 <= 1*3 = 3? no.
        # P6 (no virology groups): HELM miskey 1 + other 7 = 2, OK 3, 4, 5 -> (2, 5); agree (1, 2): 1/2 > 2/5 yes.
        v = cm.predictions81(C.FIX_V_GJ, C.FIX_V_GJX, C.FIX_V_HELM, C.FIX_V_PRO, C.FIX_V_AGREE, C.THRESHOLDS)
        self.assertEqual(v, C.FIX_VERDICTS)


class TestFrozen(unittest.TestCase):
    def test_rule_and_thresholds(self):
        self.assertEqual((C.PANEL_SIZE, C.MIN_AGREE), (10, 6))
        self.assertEqual(C.THRESHOLDS["P4_min_retention"], Fraction(1, 2))
        self.assertEqual(C.THRESHOLDS["P5_ratio"], Fraction(2))
        self.assertEqual(C.EXPECTED_80["precision"], (130, 484))
        self.assertEqual(len(C.EXPECTED_80["panel"]), 10)
        self.assertEqual(len(C.EXPECTED_77["panel"]), 10)
        self.assertEqual(len(C.ARCHIVES), 48)
        self.assertEqual(C.model_name("model_outputs_arx_0314_5shots.json.zip"), "arx_0314_5shots")


if __name__ == "__main__":
    unittest.main()
