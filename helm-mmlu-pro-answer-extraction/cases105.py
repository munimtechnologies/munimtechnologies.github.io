"""Audit 105 constants and hand-traced fixtures (frozen before the sealed run). Apache-2.0.
Authored by AI agents working in the name of MV2, Munim, Inc."""

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/capabilities/benchmark_output"
HELM_RELEASE = "v1.15.0"
GROUP = "mmlu_pro"
COLUMN_PREFIX = "COT correct"
STAT = "chain_of_thought_correctness"
SPLIT = "test"
TOL_RUN = 0.0005          # run mean vs stats.json (half a record in 1,000)
TOL_CELL = 1e-6           # our cell vs a published group-page value
REPRO_SHARE = 0.995       # reproducing version must agree with >= 99.5% of stored per-record scores
STORED_SHARE = 0.99       # >= 99% of kept records must carry a stored score
PLACES = 3
GAIN_OTHER = 0.01
GAIN_GEMINI = 0.02
WORKERS = 2
PRINT_PER_CLASS = 6

# ----- Texts (Python literals; "\\boxed" is one backslash in the text) -----
T1 = "The correct answer is (C). Because the area is half the base times the height."
T2 = "Let's compute.\n\nThe final answer is $\\boxed{C}$."
T3 = "Answer: B"
T4 = "The answer is Because of x, the correct answer is (D)."
T5 = "I think the answer is A. Wait, re-checking: the answer is E."
T6 = "The correct answer is likely option G based on the data."
T7 = "No answer can be determined."
T8 = "**Answer:** (J)"
T9 = "Option C. The answer is \\boxed{\\text{(H)}}"
T10 = ""
T11 = "The correct answer is - (F)"
T13 = "The answer is (A). Final: \\boxed{B}"
T14 = "ANSWER: **G**"
T15 = "the answer is choice B."
T16 = "So the answer is 42, i.e. E"

FIX_EXTRACT = [
    ((T1, "v4"), ("C", 1, False)),
    ((T1, "v2"), ("C", 1, False)),
    ((T2, "v4"), (None, 0, False)),
    ((T2, "pr4323"), (None, 0, False)),
    ((T3, "v4"), (None, 0, False)),
    ((T3, "pr4323"), ("B", 2, False)),
    ((T4, "v4"), ("B", 1, True)),
    ((T4, "v2"), ("B", 1, True)),
    ((T5, "v4"), ("A", 1, False)),
    ((T6, "v4"), ("G", 4, False)),
    ((T6, "v3"), (None, 0, False)),
    ((T6, "v2"), (None, 0, False)),
    ((T6, "pr4323"), ("G", 4, False)),
    ((T7, "v4"), (None, 0, False)),
    ((T8, "v4"), (None, 0, False)),
    ((T8, "pr4323"), (None, 0, False)),
    ((T9, "v4"), (None, 0, False)),
    ((T10, "v4"), (None, 0, False)),
    ((T11, "v4"), ("F", 3, False)),
    ((T11, "v3"), ("F", 3, False)),
    ((T11, "v2"), (None, 0, False)),
    ((T13, "v4"), ("A", 1, False)),
    ((T14, "v4"), (None, 0, False)),
    ((T15, "v4"), (None, 0, False)),
    ((T16, "v4"), (None, 0, False)),
]

FIX_STATED = [
    (T1, ("C", "phrase")),
    (T2, ("C", "boxed")),
    (T3, ("B", "phrase")),
    (T4, ("D", "phrase")),
    (T5, ("E", "phrase")),
    (T6, (None, None)),
    (T7, (None, None)),
    (T8, ("J", "phrase")),
    (T9, ("H", "boxed")),
    (T10, (None, None)),
    (T11, (None, None)),
    (T13, ("B", "boxed")),
    (T14, ("G", "phrase")),
    (T15, ("B", "phrase")),
    (T16, (None, None)),
]

FIX_CLASS = [
    (("C", 1, False, "C", "phrase", "C"), "both_right"),
    ((None, 0, False, "C", "boxed", "C"), "up_boxed"),
    ((None, 0, False, "B", "phrase", "B"), "up_phrase"),
    (("B", 1, True, "D", "phrase", "B"), "down_spurious_capital"),
    (("B", 1, True, "D", "phrase", "D"), "up_other_letter"),
    (("A", 1, False, "E", "phrase", "A"), "down_other_letter"),
    (("G", 4, False, None, None, "G"), "down_fallback"),
    (("F", 3, False, None, None, "F"), "down_fallback"),
    ((None, 0, False, None, None, "A"), "both_wrong"),
    (("A", 1, False, None, None, "A"), "down_no_statement"),
    (("A", 1, False, "B", "phrase", "C"), "both_wrong"),
]

FIX_GOLD = [
    ([{"output": {"text": "x"}, "tags": []}, {"output": {"text": "y"}, "tags": ["correct"]}], "B"),
    ([], None),
    ([{"tags": ["correct"]}, {"tags": ["correct"]}], "A"),
]

_E = {"tags": []}
FIX_INSTANCES = [
    {"id": "i1", "references": [_E, _E, {"tags": ["correct"]}]},
    {"id": "i2", "references": [_E, {"tags": ["correct"]}]},
    {"id": "i3", "references": [_E, _E, _E, _E, _E, _E, {"tags": ["correct"]}]},
    {"id": "i4", "references": [{"tags": ["correct"]}]},
    {"id": "i5", "references": [{"tags": ["correct"]}], "perturbation": {"name": "robustness"}},
]
FIX_GOLDS = {"i1": "C", "i2": "B", "i3": "G", "i4": "A"}

FIX_PREDICTIONS = [
    {"instance_id": "i1", "train_trial_index": 0, "predicted_text": T2, "stats": {STAT: 0.0}},
    {"instance_id": "i2", "train_trial_index": 0, "predicted_text": T3, "stats": {STAT: 0.0}},
    {"instance_id": "i3", "train_trial_index": 0, "predicted_text": T6, "stats": {STAT: 0.0}},
    {"instance_id": "i4", "train_trial_index": 0, "predicted_text": T5, "stats": {STAT: 1.0}},
    {"instance_id": "i4", "train_trial_index": 0, "predicted_text": "dup", "stats": {STAT: 1.0}},
    {"instance_id": "i5", "train_trial_index": 0, "predicted_text": T1, "stats": {STAT: 1.0}},
    {"instance_id": "i1", "train_trial_index": 0, "predicted_text": T1, "stats": {STAT: 1.0},
     "perturbation": {"name": "robustness"}},
    {"instance_id": "i1", "train_trial_index": 1, "predicted_text": T1, "stats": {}},
    "not a dict",
]
FIX_RUN_COUNTS = {"predictions": 8, "perturbed": 1, "duplicate": 1, "no_gold": 1, "kept": 5}
FIX_RUN_STORED_N = 4
FIX_RUN_MISMATCH = {"v2": 0, "v3": 0, "v4": 1, "pr4323": 2}
FIX_RUN_VERSION = "v3"
FIX_RUN_MEAN_V3 = 0.625
FIX_RUN_MEAN_STATED = 0.75
FIX_RUN_CLASSES_V3 = {"up_boxed": 1, "up_phrase": 1, "both_wrong": 1, "down_other_letter": 1, "both_right": 1}
FIX_RUN_CLASSES_V4 = {"up_boxed": 1, "up_phrase": 1, "down_fallback": 1, "down_other_letter": 1, "both_right": 1}
FIX_RUN_PR_UP_V3 = (2, 0)

FIX_SUITES = {
    "mmlu_pro:subset=all,use_chain_of_thought=true,use_few_shot=false,model=a_b": "v1.0.0",
    "gpqa:subset=gpqa_main,use_chain_of_thought=true,use_few_shot=false,model=a_b": "v1.0.0",
    "ifeval:model=a_b": "v1.1.0",
}
FIX_SELECT = {"mmlu_pro:subset=all,use_chain_of_thought=true,use_few_shot=false,model=a_b": "v1.0.0"}
FIX_MODEL = [
    ("mmlu_pro:subset=all,use_chain_of_thought=true,use_few_shot=false,model=google_gemini-2.5-flash-lite",
     "google_gemini-2.5-flash-lite"),
    ("no model here", ""),
]

FIX_STATS = [
    {"name": {"name": STAT, "split": "test"}, "count": 1, "sum": 0.277, "mean": 0.277},
    {"name": {"name": STAT, "split": "test", "perturbation": {"name": "robustness"}}, "count": 1, "sum": 0.1,
     "mean": 0.1},
]
FIX_STAT_ENTRY = [
    ((STAT, "test"), {"count": 1, "sum": 0.277, "mean": 0.277}),
    ((STAT, "valid"), None),
]

FIX_GROUP = [{"header": [{"value": "Model"}, {"value": "COT correct"}, {"value": "# eval"}],
              "rows": [[{"value": "m1"}, {"value": 0.5}, {"value": 1000}],
                       [{"value": "m2"}, {"value": 0.25}, {"value": 1000}],
                       [{"value": "m3"}, {"value": "-"}, {"value": 1000}]]}]
FIX_GROUP_VALUES = [0.5, 0.25]

FIX_RANKS = ({"a": 0.5, "b": 0.75, "c": 0.5}, {"a": 2, "b": 1, "c": 2})
FIX_TAU = [
    (([1, 2, 3], [1, 2, 3]), 1.0),
    (([1, 2, 3], [3, 2, 1]), -1.0),
    (([1, 1], [1, 2]), None),
    (([1, 2, 3], [1, 3, 2]), 1.0 / 3.0),
]
FIX_MATCH = ({"a": 0.5, "b": 0.25}, [0.25, 0.5000000001, 0.9], 2)

FIX_VERDICT_ON = {"fixtures": True, "runs_listed": 60, "runs_included": 60, "cells": 60, "matched": 60,
                  "flash_lite_gain": 0.15, "gainers_other": 5, "up": 300, "down": 50, "up_boxed": 200,
                  "up_phrase": 50, "up_other_letter": 50, "pr_up": 10, "movers": 5, "tau": 0.95,
                  "gemini_other_gainers": 3}
FIX_VERDICT_PAST = {"fixtures": False, "runs_listed": 60, "runs_included": 10, "cells": 0, "matched": 0,
                    "flash_lite_gain": None, "gainers_other": 2, "up": 0, "down": 5, "up_boxed": 0,
                    "up_phrase": 0, "up_other_letter": 0, "pr_up": 0, "movers": 1, "tau": None,
                    "gemini_other_gainers": 1}
