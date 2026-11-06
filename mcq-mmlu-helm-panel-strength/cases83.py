"""Frozen inputs for audit 83: audit 77's flag rule, the strata, audit 80's reproduction gate, the pre-registered
threshold, data sources and the hand-traced fixtures (traced in test_panel83.py). Apache-2.0."""

from fractions import Fraction

# ----- Audit 77's consensus flag, unchanged -----
PANEL_SIZE = 10
MIN_AGREE = 6

# ----- New in audit 83: the strata -----
N_STRATA = 7            # S1..S7 = ranks 1-10, 11-20, ..., 61-70 of the included models by accuracy
TOP20_SIZE = 20         # P6: ranks 1-20 as one panel
TOP20_MIN_AGREE = 12    # exploratory frozen-rule count for the 20-model panel (60%, as 6 of 10)
WINDOW_STARTS = list(range(0, 69, 4))   # exploratory: sliding 10-model windows starting at ranks 1, 5, ..., 69

# ----- Pre-registered threshold -----
THRESHOLDS = {
    "P5_mult": Fraction(2),   # S7's equal-budget precision >= 2x the base rate of error labels among judged questions
}

# ----- Audit 80's frozen outputs (reproduction gate, part of P1; S1 must equal audit 80's panel) -----
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

# ----- HELM (as audits 80-82) -----
N_SUBJECTS = 57
HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/mmlu/benchmark_output"
HELM_RELEASE = "v1.13.0"
MIN_COVERAGE = Fraction(99, 100)
MIN_CONSISTENT = Fraction(99, 100)
MAX_EM_GAP = Fraction(5, 1000)
WORKERS = 12

# ----- MMLU-Redux 2.0 (as audits 80-82) -----
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

# ----- Fixture 6 (audit 82's, copied): consensus margin and AUC -----
FIX_MARGIN = [(([2, 5, 3, 0], 0), 3), (([6, 1, 1, 2], 0), -4), (([0, 0, 10, 0], 2), -10), (([4, 4, 1, 1], 3), 3)]
FIX_AUC = [(([3, 1], [1, 0, -4]), Fraction(11, 12)), (([0.9, 0.2], [0.5, 0.3, -0.4, -0.6]), Fraction(3, 4)),
           (([6, 2], [4, 2, -8, -10]), Fraction(13, 16)), (([1], [1]), Fraction(1, 2)), (([], [1]), None)]

# ----- Fixture 7 (new): strata -----
FIX_S_ACC = {"a": (9, 10), "b": (8, 10), "c": (8, 10), "d": (5, 10), "e": (7, 10), "f": (1, 10), "g": (6, 10)}
FIX_S_TARGET = [["a", "b"], ["c", "e"], ["g", "d"]]

# ----- Fixture 8 (new): budget counts with ties shared -----
FIX_B_SCORE = {0: 3, 1: 3, 2: 1, 3: 1, 4: 1, 5: -2}
FIX_B_SETS = [{0, 2}, {0, 1, 2, 3}, {0}]
FIX_B_CASES = [(4, [Fraction(5, 3), Fraction(10, 3), Fraction(1)]),
               (2, [Fraction(1), Fraction(2), Fraction(1)]),
               (0, [Fraction(0), Fraction(0), Fraction(0)]),
               (10, [Fraction(2), Fraction(4), Fraction(1)])]

# ----- Fixture 9 (new): one panel's statistics -----
FIX_P_G = {"all": [0, 1, 2, 3, 4, 5], "miskey": [0, 1], "ok": [2, 3, 4], "other_error": [5],
           "unsure_or_conflict": [], "unreviewed": []}
FIX_P_FLAGS = {0: (True, 1), 1: (False, None), 2: (True, 2), 3: (False, None), 4: (False, None), 5: (True, 0)}
FIX_P_SCORE = {0: 4, 1: 0, 2: 4, 3: -6, 4: -2, 5: 1}
FIX_P_BUDGET = 3
FIX_P_TARGET = {"flags": 3, "prec": (2, 3), "miskeys": 1, "auc": Fraction(3, 4), "b_err": Fraction(2),
                "b_judged": Fraction(3), "b_miskey": Fraction(1)}


# ----- Fixture 10 (new): verdicts -----
def _st(flags, auc_v, b_err, b_judged):
    return {"flags": flags, "prec": (0, 0), "miskeys": 0, "auc": auc_v, "b_err": Fraction(b_err),
            "b_judged": Fraction(b_judged), "b_miskey": Fraction(0)}


FIX_V_ST = [_st(10, Fraction(4, 5), 3, 5), _st(12, Fraction(3, 4), 3, 5), _st(13, Fraction(3, 4), 2, 5),
            _st(15, Fraction(7, 10), 2, 5), _st(20, Fraction(7, 10), 1, 5), _st(25, Fraction(7, 10), 1, 5),
            _st(30, Fraction(7, 10), 1, 5)]
FIX_V_TOP20 = _st(9, Fraction(4, 5), 3, 5)
FIX_V_BASE = (1, 20)
FIX_VERDICTS = {
    "P2_weaker_flags_more": True, "P2_counts": [10, 30],
    "P3_auc_falls_with_strength": False, "P3_auc": [0.8, 0.7, 0.7],
    "P4_budget_precision_falls": True, "P4_precision": [0.6, 0.4, 0.2],
    "P5_weakest_still_informative": True, "P5_counts": [1.0, 5.0, 1, 20],
    "P6_top20_beats_top10": False, "P6_precision": [0.6, 0.6],
}
