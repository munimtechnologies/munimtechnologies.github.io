"""Frozen inputs for audit 82: audit 77's consensus flag rule, audit 80's reproduction gate, the pre-registered
threshold, data sources and the hand-traced fixtures (traced in test_disc82.py). Apache-2.0."""

from fractions import Fraction

# ----- Audit 77's consensus flag, unchanged (the comparison flag) -----
PANEL_SIZE = 10
MIN_AGREE = 6

# ----- Pre-registered threshold -----
THRESHOLDS = {
    "P2_ratio": Fraction(5),   # r < 0 on Redux miskeys at >= 5x its rate on Redux-OK questions
}
CURVE_BUDGETS = [100, 200, 300, 500, 750, 1000, 1500, 2000]   # exploratory precision curve

# ----- Audit 80's frozen outputs (reproduction gate, part of P1) -----
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

# ----- HELM (as audits 80-81) -----
N_SUBJECTS = 57
HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/mmlu/benchmark_output"
HELM_RELEASE = "v1.13.0"
MIN_COVERAGE = Fraction(99, 100)
MIN_CONSISTENT = Fraction(99, 100)
MAX_EM_GAP = Fraction(5, 1000)
WORKERS = 12

# ----- MMLU-Redux 2.0 (as audits 80-81) -----
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

# ----- Fixture 6 (new): item-rest discrimination (traced in test_disc82.py) -----
FIX_D_MODELS = ["A", "B", "C", "D"]
FIX_D_ACC = {"A": (8, 10), "B": (6, 10), "C": (4, 10), "D": (2, 10)}
FIX_D_GOLD = [0, 1, 2, 0, 0]
FIX_D_PREDS = {
    "A": {0: 0, 1: 3, 2: 2, 3: 0, 4: 1},
    "B": {0: 0, 1: None, 2: 2, 3: 1, 4: 1},
    "C": {0: 1, 1: 1, 2: 2, 3: 0, 4: 2},
    "D": {0: 3, 1: 1, 2: 2, 4: None},
}
FIX_D_R = [3 / 13 ** 0.5, -5 / 29 ** 0.5, 1.0, -1 / 13 ** 0.5, -1.0]
FIX_D_N_MODELS = [4, 4, 4, 3, 4]
FIX_D_N_KEY = [2, 2, 4, 2, 0]
FIX_D_COUNTS = {"defined": 3, "all_correct": 1, "all_wrong": 1, "too_few": 0, "flat": 0}
FIX_D_ORDER = [4, 1, 3, 0, 2]
FIX_D_RANK2 = {0: (False, None), 1: (True, None), 2: (False, None), 3: (False, None), 4: (True, None)}
FIX_D_NEG = {0: (False, None), 1: (True, None), 2: (False, None), 3: (True, None), 4: (True, None)}

# ----- Fixture 7 (new): consensus margin and AUC -----
FIX_MARGIN = [(([2, 5, 3, 0], 0), 3), (([6, 1, 1, 2], 0), -4), (([0, 0, 10, 0], 2), -10), (([4, 4, 1, 1], 3), 3)]
FIX_AUC = [(([3, 1], [1, 0, -4]), Fraction(11, 12)), (([0.9, 0.2], [0.5, 0.3, -0.4, -0.6]), Fraction(3, 4)),
           (([6, 2], [4, 2, -8, -10]), Fraction(13, 16)), (([1], [1]), Fraction(1, 2)), (([], [1]), None)]

# ----- Fixture 8 (new): verdicts -----
FIX_V_G = {"miskey": [1, 2], "ok": [3, 4, 5, 6], "other_error": [7], "unreviewed": [8]}
FIX_V_GX = {"miskey": [1], "ok": [3, 4, 5], "other_error": [7], "unreviewed": []}
FIX_V_CONS = {1: (True, 0), 2: (True, 1), 3: (True, 2), 4: (True, 1), 5: (False, None), 6: (False, None),
              7: (False, None), 8: (True, 1)}
FIX_V_BUDGET = {1: (True, None), 2: (False, None), 3: (False, None), 4: (True, None), 5: (False, None),
                6: (False, None), 7: (True, None), 8: (True, None)}
FIX_V_NEG = {1: (True, None), 2: (True, None), 3: (True, None), 4: (False, None), 5: (False, None),
             6: (False, None), 7: (True, None), 8: (True, None)}
FIX_V_SDISC = {1: 0.9, 2: 0.2, 3: 0.5, 4: 0.3, 5: -0.4, 6: -0.6, 7: 0.1, 8: 0.7}
FIX_V_SCONS = {1: 6, 2: 2, 3: 4, 4: 2, 5: -8, 6: -10, 7: -2, 8: 5}
FIX_VERDICTS = {
    "P2_negative_discriminates": False, "P2_counts": [2, 2, 1, 4],
    "P3_budget_beats_consensus": True, "P3_counts": [2, 3, 2, 4],
    "P4_auc_beats_consensus": False, "P4_auc": [0.75, 0.8125],
    "P5_both_beats_each": False, "P5_counts": [1, 2],
    "P6_budget_beats_consensus_no_virology": True, "P6_counts": [2, 3, 1, 3],
}
