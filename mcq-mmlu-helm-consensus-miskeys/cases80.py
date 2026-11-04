"""Frozen inputs for audit 80: audit 77's flag rule, the pre-registered thresholds and gates, data sources and the
hand-traced fixtures (traced in test_helm80.py). Apache-2.0."""

from fractions import Fraction

# ----- Audit 77's flag, unchanged -----
PANEL_SIZE = 10
MIN_AGREE = 6

# ----- Pre-registered thresholds -----
THRESHOLDS = {
    "P2_ratio": Fraction(5),              # Redux-miskey flag rate >= 5x the Redux-OK flag rate
    "P3_min_recall": Fraction(1, 2),      # at least half of the joined Redux miskeys flagged
    "P4_baseline": Fraction(65, 359),     # audit 77's precision on MMLU-Pro (18.1%)
    "P5_ratio": Fraction(2),              # other-error flag rate >= 2x the Redux-OK flag rate
}

# ----- Gates (P1) -----
N_SUBJECTS = 57
MIN_UNIVERSE = 14000          # MMLU test has 14,042 questions
N_REDUX_ROWS = 5700
N_REDUX_MISKEY_ROWS = 106     # audit 69
MIN_REDUX_JOINED = 5600
MIN_KEY_AGREE = Fraction(99, 100)
MIN_INCLUDED_MODELS = 20
# Inclusion of a model: all 57 subjects, coverage >= 99% of the universe, >= 99% of valid letters consistent with
# HELM's mapped_output, and our accuracy within 0.5 points of HELM's own exact_match on the same items.
MIN_COVERAGE = Fraction(99, 100)
MIN_CONSISTENT = Fraction(99, 100)
MAX_EM_GAP = Fraction(5, 1000)
ABORT_REDUX_JOINED = 4000     # below this the join is broken: abort

# ----- Data -----
HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/mmlu/benchmark_output"
HELM_RELEASE = "v1.13.0"
REDUX_DATASET = "edinburgh-dawg/mmlu-redux-2.0"
REDUX_SPLIT = "test"
WORKERS = 12

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

# ----- Fixture 2 (new): run selection -----
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


# ----- Fixture 3 (new): instances and the question universe -----
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

# ----- Fixture 4 (new): mapping one run's predictions -----
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

# ----- Fixture 5 (new): the Redux join -----
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

# ----- Fixture 6 (new): verdicts -----
FIX_G = {"miskey": [1, 2], "ok": [3, 4, 5, 6], "other_error": [7, 8]}
FIX_FLAGS = {1: (True, 1), 2: (True, 0), 3: (True, 2), 4: (False, None), 5: (False, None), 6: (False, None),
             7: (True, 3), 8: (False, None)}
FIX_CURVE = {10: (1, 2), 6: (3, 4)}
FIX_VERDICTS = {
    "P2_miskey_ratio": False, "P2_counts": [2, 2, 1, 4],
    "P3_recall": True, "P3_counts": [2, 2],
    "P4_precision_above_77": True, "P4_counts": [3, 4],
    "P5_other_error_ratio": True, "P5_counts": [1, 2, 1, 4],
    "P6_unanimous_more_precise": False, "P6_counts": [1, 2, 3, 4],
}
