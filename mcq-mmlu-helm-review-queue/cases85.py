"""Frozen inputs for audit 85: audit 77's flag rule, the tiers, the reproduction gates (audit 80's flag, audit 82's
no-key count), the 95% z, data sources and the hand-traced fixtures (traced in test_queue85.py). Apache-2.0."""

from fractions import Fraction

# ----- Audit 77's consensus flag on HELM's 10 most accurate models, unchanged -----
PANEL_SIZE = 10
MIN_AGREE = 6

# ----- Pre-registered constant -----
Z2 = Fraction(38416, 10000)   # 1.96 squared: a 95% normal interval

# ----- Reproduction gates (part of P1) -----
EXPECTED_80 = {
    "universe": 13984,
    "included": 78,
    "panel": ["anthropic_claude-3-5-sonnet-20241022", "anthropic_claude-3-5-sonnet-20240620",
              "deepseek-ai_deepseek-v3", "google_gemini-1.5-pro-002", "anthropic_claude-3-opus-20240229",
              "openai_gpt-4o-2024-08-06", "meta_llama-3.1-405b-instruct-turbo", "openai_gpt-4o-2024-05-13",
              "openai_gpt-4-0613", "qwen_qwen2.5-72b-instruct-turbo"],
    "flagged": {"all": 1207, "miskey": 80, "ok": 354, "other_error": 50, "unsure_or_conflict": 8,
                "unreviewed": 715},
    "precision": (130, 484),
}
# Audit 82, published post-hoc: 88 questions answered with the key by none of the 78 included models.
EXPECTED_82_NOKEY = {"all": 88, "miskey": 23, "ok": 10, "other_error": 4, "unsure_or_conflict": 0,
                     "unreviewed": 51}

# ----- HELM (as audits 80-83) -----
N_SUBJECTS = 57
HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/mmlu/benchmark_output"
HELM_RELEASE = "v1.13.0"
MIN_COVERAGE = Fraction(99, 100)
MIN_CONSISTENT = Fraction(99, 100)
MAX_EM_GAP = Fraction(5, 1000)
WORKERS = 12

# ----- MMLU-Redux 2.0 (as audits 80-83) -----
REDUX_DATASET = "edinburgh-dawg/mmlu-redux-2.0"
REDUX_SPLIT = "test"
ABORT_REDUX_JOINED = 4000

# ----- Fixture 1 (audit 77's, copied; letters are converted to indices in the test and in job.fixture_ok) -----
FIX_ACC = {"m1": (9, 10), "m2": (8, 10), "m3": (7, 10), "m4": (1, 10), "m5": (7, 10)}
FIX_PANEL_SIZE = 3
FIX_MIN_AGREE = 2
FIX_QUESTIONS = {1: (4, 0), 2: (4, 2), 3: (10, 0), 4: (4, 1), 5: (4, 3), 6: (4, 0), 7: (4, 0), 8: (4, 0)}
FIX_PREDS = {
    "m1": {1: "B", 2: "C", 3: "B", 4: "B", 5: "A", 6: "B", 7: "C", 8: "A"},
    "m2": {1: "B", 2: "D", 3: "C", 4: "B", 5: "A", 6: "Z", 7: "C", 8: "A"},
    "m3": {1: "A", 2: "D", 3: "A", 4: None, 5: "D", 6: "E", 7: "C", 8: "A"},
    "m4": {1: "C", 2: "D", 3: "B", 4: "A", 5: "A", 6: "B", 7: "B", 8: "A"},
    "m5": {1: "B", 2: "C", 3: "B", 4: "A", 5: "A", 6: "B", 7: "C", 8: "A"},
}
FIX_TARGET = {
    "panel": ["m1", "m2", "m3"],
    "flags": {1: (True, 1), 2: (True, 3), 3: (False, None), 4: (False, None), 5: (True, 0), 6: (False, 1),
              7: (True, 2), 8: (False, None)},
}

# ----- Fixture 2 (audit 80's, copied): run selection -----
FIX_RUNS = {
    "mmlu:subject=anatomy,method=multiple_choice_joint,model=x_a,eval_split=test,groups=mmlu_anatomy": "v1.0.0",
    "mmlu:subject=anatomy,method=multiple_choice_joint,model=x_a,eval_split=test,groups=mmlu_anatomy,"
    "model_deployment=d": "v1.2.0",
    "mmlu:subject=virology,method=multiple_choice_joint,model=y_b:0,eval_split=test,groups=mmlu_virology": "v1.13.0",
    "mmlu:subject=virology,method=multiple_choice_separate_original,model=x_a,eval_split=test,groups=mmlu_virology":
        "v1.0.0",
    "mmlu:subject=virology,method=multiple_choice_joint,model=x_a,eval_split=valid,groups=mmlu_virology": "v1.0.0",
    "gsm:model=x_a": "v1.0.0",
}
FIX_RUNS_TARGET = (
    {("x_a", "anatomy"): ("mmlu:subject=anatomy,method=multiple_choice_joint,model=x_a,eval_split=test,"
                          "groups=mmlu_anatomy", "v1.0.0"),
     ("y_b:0", "virology"): ("mmlu:subject=virology,method=multiple_choice_joint,model=y_b:0,eval_split=test,"
                             "groups=mmlu_virology", "v1.13.0")},
    1,
)


def _ref(text, correct=False):
    return {"output": {"text": text}, "tags": ["correct"] if correct else []}


# ----- Fixture 3 (audit 80's, copied): instances and the question universe -----
FIX_INST = {
    "anatomy": [
        {"input": {"text": "Q1"}, "references": [_ref("a"), _ref("b", True), _ref("c"), _ref("d")], "split": "test",
         "id": "id5"},
        {"input": {"text": "Q2 "}, "references": [_ref("e", True), _ref("f"), _ref("g"), _ref("h")], "split": "test",
         "id": "id6"},
        {"input": {"text": "Q1"}, "references": [_ref("a"), _ref("b", True), _ref("c"), _ref("d")], "split": "test",
         "id": "id7"},
        {"input": {"text": "Q3"}, "references": [_ref("i"), _ref("j"), _ref("k"), _ref("l")], "split": "test",
         "id": "id8"},
        {"input": {"text": "Q4"}, "references": [_ref("m"), _ref("n"), _ref("o"), _ref("p", True)], "split": "valid",
         "id": "id1"},
    ],
    "virology": [
        {"input": {"text": "V1"}, "references": [_ref("q"), _ref("r"), _ref("s", True), _ref("t")], "split": "test",
         "id": "id20"},
        {"input": {"text": "V2"}, "references": [_ref("u"), _ref("v"), _ref("w"), _ref("x", True)], "split": "test",
         "id": "id21"},
    ],
}
FIX_UNIVERSE_TARGET = {
    "qids": {("anatomy", ("Q2", ("e", "f", "g", "h"))): 0,
             ("virology", ("V1", ("q", "r", "s", "t"))): 1,
             ("virology", ("V2", ("u", "v", "w", "x"))): 2},
    "info": [("anatomy", "id6", 4, 0, 1), ("virology", "id20", 4, 2, 0), ("virology", "id21", 4, 3, 1)],
    "counts": {"dup_dropped": 2, "no_gold": 1},
}

# ----- Fixture 4 (audit 80's, copied): mapping one run's predictions -----
FIX_PRED = {
    "virology": [
        {"instance_id": "id20", "train_trial_index": 0, "predicted_text": "C", "mapped_output": "s",
         "stats": {"exact_match": 1.0}},
        {"instance_id": "id21", "train_trial_index": 0, "predicted_text": " B", "mapped_output": "u",
         "stats": {"exact_match": 0.0}},
        {"instance_id": "id99", "train_trial_index": 0, "predicted_text": "A", "mapped_output": "q",
         "stats": {"exact_match": 0.0}},
        {"instance_id": "id20", "train_trial_index": 1, "predicted_text": "A", "mapped_output": "q",
         "stats": {"exact_match": 0.0}},
    ],
    "anatomy": [
        {"instance_id": "id6", "train_trial_index": 0, "predicted_text": "The answer", "mapped_output": "g",
         "stats": {"exact_match": 0.0}},
        {"instance_id": "id5", "train_trial_index": 0, "predicted_text": "B", "mapped_output": "b",
         "stats": {"exact_match": 1.0}},
        {"instance_id": "id8", "train_trial_index": 0, "predicted_text": "Z", "mapped_output": None,
         "stats": {"exact_match": 0.0}},
    ],
}
FIX_PRED_TARGET = {
    "virology": ({1: 2, 2: 1},
                 {"n": 4, "other_trial": 1, "unmapped": 1, "valid": 2, "from_mapped": 0, "invalid": 0,
                  "consistent": 1, "inconsistent": 1, "no_mapped_output": 0, "em_correct": 1}),
    "anatomy": ({0: 2},
                {"n": 3, "other_trial": 0, "unmapped": 2, "valid": 0, "from_mapped": 1, "invalid": 0,
                 "consistent": 0, "inconsistent": 0, "no_mapped_output": 0, "em_correct": 0}),
}

# ----- Fixture 5 (audit 80's, copied): the Redux join -----
FIX_REDUX = [
    {"subject": "anatomy", "question": "Q2", "choices": ["e", "f", "g", "h"], "answer": 0, "label": "ok"},
    {"subject": "virology", "question": "V1 ", "choices": ["q", "r", "s", "t"], "answer": 1,
     "label": "wrong_groundtruth"},
    {"subject": "virology", "question": "V2", "choices": ["u", "v", "w", "x"], "answer": 3,
     "label": "bad_question_clarity"},
    {"subject": "anatomy", "question": "Q1", "choices": ["a", "b", "c", "d"], "answer": 1, "label": "ok"},
    {"subject": "virology", "question": "V2", "choices": ["u", "v", "w", "x"], "answer": 3, "label": "ok"},
]
FIX_GOLD = [0, 2, 3]
FIX_REDUX_TARGET = ({0: "ok", 1: "wrong_groundtruth", 2: "conflict"},
                    {"joined": 4, "no_match": 1, "conflict": 1}, 3)
FIX_GROUPS_TARGET = {"all": [0, 1, 2], "miskey": [1], "ok": [0], "other_error": [], "unsure_or_conflict": [2],
                     "unreviewed": []}

# ----- Fixture 6 (new): key pickers and tiers, on fixture 1 -----
FIX_KEY_COUNTS = {1: (5, 1), 2: (5, 2), 3: (5, 1), 4: (5, 2), 5: (5, 1), 6: (5, 0), 7: (5, 0), 8: (5, 5)}
FIX_NOKEY = {6, 7}
FIX_TIER_NOKEY = {6}      # passed to assign_tiers so that q7 shows tier 2
FIX_TIERS = {1: 3, 2: 3, 3: 0, 4: 0, 5: 3, 6: 1, 7: 2, 8: 0}
FIX_TIER_OF = [((True, 10, 10, True), 1), ((False, 3, 10, True), 1), ((True, 10, 10, False), 2),
               ((True, 7, 10, False), 3), ((False, 10, 10, False), 0), ((False, 0, 10, False), 0)]

# ----- Fixture 7 (new): the queue, on fixtures 1 and 6 -----
FIX_Q_INFO = {q: ("s", "id%d" % q, k, key, q) for q, (k, key) in FIX_QUESTIONS.items()}
FIX_Q_ORDER = [6, 7, 1, 5, 2]
FIX_Q_FIRST = {"qid": 6, "tier": 1, "subject": "s", "helm_instance_id": "id6", "helm_test_position": 6,
               "helm_key": "A", "consensus_letter": "B", "top10_votes": [0, 1, 0, 0], "top10_no_answer": 2,
               "margin": 1, "n_models": 5, "n_models_picking_key": 0, "rank": 1}

# ----- Fixture 8 (new): rates, cross-fold test -----
FIX_SUBJ = {0: "a", 1: "a", 2: "a", 3: "a", 4: "a", 5: "b", 6: "b", 7: "b", 8: "b", 9: "b"}
FIX_CF_TIERS = {0: 1, 1: 2, 2: 3, 3: 0, 4: 0, 5: 3, 6: 0, 7: 0, 8: 0, 9: 2}
FIX_CF_TARGET = {0, 5, 9}
FIX_CF_JUDGED = {0, 1, 2, 3, 5, 6, 7, 8, 9}
FIX_FOLD = {0: 0, 1: 1, 2: 0, 3: 1, 4: 0, 5: 1, 6: 0, 7: 1, 8: 0, 9: 0}
FIX_RATES_F0 = ({2: Fraction(0), 0: Fraction(0), 3: Fraction(1)}, Fraction(1, 4), {2: 1, 0: 2, 3: 1})
FIX_CF = [
    {"fold": 0, "n_test": 5, "actual": 2, "tier_expected": Fraction(5, 4), "tier_var": Fraction(3, 16),
     "subj_expected": Fraction(3, 2), "mae_tier": Fraction(5, 4), "mae_subject": Fraction(3, 2)},
    {"fold": 1, "n_test": 4, "actual": 1, "tier_expected": Fraction(1), "tier_var": Fraction(0),
     "subj_expected": Fraction(5, 3), "mae_tier": Fraction(2), "mae_subject": Fraction(4, 3)},
]

# ----- Fixture 9 (new): estimate with an interval -----
FIX_E_CELLS = {2: 1, 3: 0, 6: 3, 7: 0}
FIX_E_RATE = {1: Fraction(1, 2), 0: Fraction(1, 10)}
FIX_E_POOLED = Fraction(1, 5)
FIX_E_DEN = {1: 2, 0: 10}
FIX_E_QS = [2, 3, 6, 7]
FIX_E_TARGET = (Fraction(9, 10), Fraction(751, 1000),
                [{"cell": 0, "n": 2, "rate": Fraction(1, 10), "expected": Fraction(1, 5)},
                 {"cell": 1, "n": 1, "rate": Fraction(1, 2), "expected": Fraction(1, 2)},
                 {"cell": 3, "n": 1, "rate": Fraction(1, 5), "expected": Fraction(1, 5)}])

# ----- Fixture 10 (new): transport -----
FIX_T_SUBJ = {0: "a", 1: "a", 2: "a", 3: "a", 4: "b", 5: "b", 6: "b", 7: "c"}
FIX_T_FLAGGED = {0, 2, 3, 6}
FIX_T_REVIEWED = {0, 1, 4, 5}
FIX_T_UNREVIEWED = {2, 3, 6, 7}
FIX_T_TARGET = (3, Fraction(1), Fraction(1), ["c"])

# ----- Fixture 11 (new): verdicts, from fixtures 8 and 10 -----
FIX_V_RATES = [Fraction(2, 3), Fraction(1, 2), Fraction(1, 4), Fraction(0)]
FIX_VERDICTS = {
    "P2_tier_beats_subject": False, "P2_mae": [3.25, float(Fraction(17, 6))],
    "P3_tier_calibrated": True, "P3_folds": [[2, 1.25, 0.1875], [1, 1.0, 0.0]],
    "P4_transport": False, "P4_counts": [3, 1.0, 1.0],
    "P5_tiers_ordered": True, "P5_rates": [float(Fraction(2, 3)), 0.5, 0.25, 0.0],
}
