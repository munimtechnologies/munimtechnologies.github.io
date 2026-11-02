"""Frozen inputs for audit 77: the panel rule, pre-registered thresholds, audit 76's 46 targets and audit 75's 55
miskey ids (validation), data sources, structural numbers and the hand-traced fixtures. Apache-2.0."""

from fractions import Fraction

# ----- The flag (frozen before any real data is read) -----
PANEL_SIZE = 10     # the 10 included models with the highest MMLU-Pro accuracy on their joined questions
MIN_AGREE = 6       # flagged: >= 6 of the 10 pick the same non-key option, and more of them pick it than the key
CURVE_MS = (4, 5, 6, 7, 8, 9, 10)   # exploratory threshold curve

# ----- Pre-registered thresholds -----
THRESHOLDS = {
    "P2_ratio": 5,                    # flag rate on Redux-miskeyed >= 5x the flag rate on Redux-OK questions
    "P3_recall": Fraction(2, 5),      # >= 40% of audit 76's 46 targets flagged ...
    "P3_match": Fraction(4, 5),       # ... and on >= 80% of the flagged ones the consensus is the experts' answer
    "P4_precision": Fraction(1, 5),   # >= 20% of flagged Redux-judged questions carry a Redux error label
}
MIN_INCLUDED_ARCHIVES = 30

# ----- Validation sets -----
# Audit 76's targets (from audit 75's pro_flags.json): (question_id, src, MMLU-Pro key letter, experts' answer letter
# among MMLU-Pro's options, basis). basis "primary" = Redux letter / exact-text correction; "digits_0_based" = Redux
# digit read 0-based.
TARGETS = [
    (1418, "ori_mmlu-professional_law", "B", "G", "digits_0_based"),
    (2454, "ori_mmlu-professional_psychology", "B", "C", "digits_0_based"),
    (2933, "ori_mmlu-college_biology", "D", "F", "digits_0_based"),
    (3538, "ori_mmlu-college_chemistry", "C", "D", "primary"),
    (3636, "ori_mmlu-college_chemistry", "J", "C", "primary"),
    (3637, "ori_mmlu-college_chemistry", "H", "E", "primary"),
    (3725, "ori_mmlu-college_chemistry", "A", "I", "primary"),
    (3811, "ori_mmlu-college_chemistry", "A", "J", "primary"),
    (3814, "ori_mmlu-college_chemistry", "D", "C", "primary"),
    (3894, "ori_mmlu-college_chemistry", "B", "A", "primary"),
    (3990, "ori_mmlu-college_chemistry", "B", "E", "primary"),
    (4084, "ori_mmlu-college_chemistry", "E", "D", "primary"),
    (4088, "ori_mmlu-college_chemistry", "H", "D", "primary"),
    (4089, "ori_mmlu-college_chemistry", "C", "D", "primary"),
    (4341, "ori_mmlu-college_chemistry", "G", "C", "primary"),
    (4346, "ori_mmlu-college_chemistry", "J", "A", "primary"),
    (4437, "ori_mmlu-college_chemistry", "A", "C", "primary"),
    (4438, "ori_mmlu-college_chemistry", "J", "C", "primary"),
    (4511, "ori_mmlu-college_chemistry", "H", "F", "primary"),
    (4607, "ori_mmlu-college_chemistry", "G", "F", "primary"),
    (4609, "ori_mmlu-college_chemistry", "B", "E", "primary"),
    (4752, "ori_mmlu-high_school_world_history", "A", "C", "digits_0_based"),
    (5726, "ori_mmlu-public_relations", "F", "B", "digits_0_based"),
    (5885, "ori_mmlu-global_facts", "J", "I", "digits_0_based"),
    (5949, "ori_mmlu-human_sexuality", "B", "C", "digits_0_based"),
    (6067, "ori_mmlu-virology", "A", "C", "primary"),
    (6068, "ori_mmlu-virology", "C", "A", "primary"),
    (6224, "ori_mmlu-anatomy", "B", "D", "digits_0_based"),
    (6277, "ori_mmlu-virology", "G", "A", "primary"),
    (6278, "ori_mmlu-virology", "C", "B", "primary"),
    (6639, "ori_mmlu-virology", "B", "A", "primary"),
    (6640, "ori_mmlu-virology", "C", "B", "primary"),
    (7306, "ori_mmlu-high_school_microeconomics", "A", "B", "digits_0_based"),
    (7687, "ori_mmlu-abstract_algebra", "H", "A", "digits_0_based"),
    (7791, "ori_mmlu-abstract_algebra", "C", "A", "digits_0_based"),
    (8972, "ori_mmlu-abstract_algebra", "A", "B", "digits_0_based"),
    (9547, "ori_mmlu-conceptual_physics", "B", "G", "digits_0_based"),
    (9677, "ori_mmlu-astronomy", "C", "J", "digits_0_based"),
    (9733, "ori_mmlu-conceptual_physics", "A", "B", "digits_0_based"),
    (9814, "ori_mmlu-high_school_physics", "D", "I", "digits_0_based"),
    (9947, "ori_mmlu-conceptual_physics", "G", "I", "digits_0_based"),
    (10365, "ori_mmlu-machine_learning", "J", "F", "digits_0_based"),
    (10458, "ori_mmlu-computer_security", "D", "A", "digits_0_based"),
    (10533, "ori_mmlu-computer_security", "B", "C", "digits_0_based"),
    (10666, "ori_mmlu-machine_learning", "D", "F", "digits_0_based"),
    (11579, "ori_mmlu-electrical_engineering", "E", "G", "digits_0_based"),
]
N_TARGETS = 46
N_PRIMARY = 24

# All 55 Redux-miskeyed questions MMLU-Pro holds with one match (audit 75). The re-run join must reproduce this set.
MISKEY_IDS = frozenset([
    1418, 1989, 2454, 2817, 2933, 3538, 3636, 3637, 3725, 3811, 3814, 3894, 3990, 4084, 4088, 4089, 4341, 4346,
    4437, 4438, 4511, 4607, 4609, 4752, 5225, 5726, 5885, 5949, 6067, 6068, 6224, 6277, 6278, 6586, 6639, 6640,
    6642, 7306, 7687, 7791, 8122, 8780, 8876, 8972, 9547, 9677, 9733, 9814, 9947, 10365, 10458, 10533, 10666,
    10859, 11579])
N_MISKEY_IDS = 55

# MMLU-Pro ids named as mislabelled in Land & Bikel, "Auditing LLM Benchmarks with Item Response Theory" (arXiv
# 2605.30504, JudgeBench appendix). Exploratory: their flag status is reported, nothing is predicted.
EXTERNAL_IDS = (6643, 8762)

# ----- Data -----
MMLU_PRO = {"hf": "TIGER-Lab/MMLU-Pro", "config": "default", "splits": ["test"],
            "cols": ["question_id", "question", "options", "answer_index", "category", "src"]}
MMLU = {"hf": "cais/mmlu", "config": "all", "splits": ["test"], "cols": ["subject", "question", "choices", "answer"]}
REDUX_DATASET = "edinburgh-dawg/mmlu-redux-2.0"
REDUX_SPLIT = "test"
EXPECTED = {"n_valid": 12032, "family_n": {"ori_mmlu": 6810, "stemez": 4083, "scibench": 541, "theoremQA": 598}}
EXPECTED_REDUX = {"joined": 5690, "in_pro": 2758, "ambiguous_pro": 71}   # audit 75
EVAL_RESULTS_URL = "https://github.com/TIGER-AI-Lab/MMLU-Pro/raw/refs/heads/main/eval_results/%s"
MIN_JOIN_SHARE = 0.95

# The 48 archives audit 66 listed in eval_results on 2026-10-30 (45 passed the join rule in audit 76).
ARCHIVES = [
    "model_outputs_DeepSeek-Coder-V2_5shots.zip",
    "model_outputs_Llama-2-13b-hf_5shots.zip",
    "model_outputs_Llama-2-70b-hf_5shots.zip",
    "model_outputs_Llama-2-7b-hf_5shots.zip",
    "model_outputs_Meta-Llama-3-70B-Instruct_5shots.zip",
    "model_outputs_Meta-Llama-3-70B_5shots.zip",
    "model_outputs_Meta-Llama-3-8B-Instruct_5shots.zip",
    "model_outputs_Meta-Llama-3-8B_5shots.zip",
    "model_outputs_Meta-Llama-3_1-70B-Instruct_5shots.zip",
    "model_outputs_Meta-Llama-3_1-70B_5shots.zip",
    "model_outputs_Meta-Llama-3_1-8B-Instruct_5shots.zip",
    "model_outputs_Meta-Llama-3_1-8B_5shots.zip",
    "model_outputs_Mistral-7B-Instruct-v0.1_5shots.zip",
    "model_outputs_Mistral-7B-Instruct-v0.2_5shots.zip",
    "model_outputs_Mistral-7B-v0.1_5shots.zip",
    "model_outputs_Mistral-7B-v0.2-hf_5shots.zip",
    "model_outputs_Mixtral-8x7B-Instruct-v0.1_5shots.zip",
    "model_outputs_Mixtral-8x7B-v0.1_5shots.zip",
    "model_outputs_Phi-3-mini-4k-instruct_5shots.zip",
    "model_outputs_Qwen1.5-110B_5shots.zip",
    "model_outputs_Qwen1.5-14B-Chat_5shots.zip",
    "model_outputs_Qwen1.5-72B-Chat_5shots.zip",
    "model_outputs_Qwen1.5-7B-Chat_5shots.zip",
    "model_outputs_Yi-34B_5shots.zip",
    "model_outputs_Yi-6B_5shots.zip",
    "model_outputs_Yi-6b-Chat_5shots.zip",
    "model_outputs_arx_0314_5shots.json.zip",
    "model_outputs_arx_3_5shots.zip",
    "model_outputs_c4ai-command-r-v01_5shots.zip",
    "model_outputs_claude-3-5-haiku-20241022_5shots.json.zip",
    "model_outputs_claude-3-5-sonnet-20241022_5shots.json.zip",
    "model_outputs_claude-3.5-sonnet_5shots.zip",
    "model_outputs_deepseek-chat-v2_5_5shots.zip",
    "model_outputs_deepseek_5shots.zip",
    "model_outputs_flash_0shots_00_35_03.zip",
    "model_outputs_gemini-1.5-flash-002_5shots.zip",
    "model_outputs_gemini-1.5-pro-002_5shots.zip",
    "model_outputs_gemini-3.1-pro_5-shots.zip",
    "model_outputs_gemma-7b_5shots.zip",
    "model_outputs_gpt-4o-2024-08-06_5shots.zip",
    "model_outputs_gpt-4o-mini_5shots.zip",
    "model_outputs_gpt4o(2024-05-13)_5shots.zip",
    "model_outputs_iask_pro_5shots.json.zip",
    "model_outputs_jamba-1.5-large_5shots.zip",
    "model_outputs_mathstral-7B_5shots.zip",
    "model_outputs_opus_2shots_00_37_14.zip",
    "model_outputs_sonnet-3.5_0shots_09_34_29.zip",
    "model_outputs_sonnet_0shots_12_01_18.zip",
]


def model_name(zname):
    """'model_outputs_X_5shots.json.zip' -> 'X_5shots' (as audit 66)."""
    s = zname[len("model_outputs_"):] if zname.startswith("model_outputs_") else zname
    for suffix in (".zip", ".json"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s


# ----- Hand-traced fixture 1: panel, flags, verdicts (traced in test_consensus77.py) -----
FIX_ACC = {"m1": (9, 10), "m2": (8, 10), "m3": (7, 10), "m4": (1, 10), "m5": (7, 10)}
FIX_PANEL_SIZE = 3
FIX_MIN_AGREE = 2
FIX_QUESTIONS = {1: (4, 0), 2: (4, 2), 3: (10, 0), 4: (4, 1), 5: (4, 3), 6: (4, 0), 7: (4, 0), 8: (4, 0)}
FIX_FAMILY = {1: "ori_mmlu", 2: "ori_mmlu", 3: "ori_mmlu", 4: "ori_mmlu", 5: "stemez", 6: "ori_mmlu",
              7: "ori_mmlu", 8: "ori_mmlu"}
FIX_PREDS = {
    "m1": {1: "B", 2: "C", 3: "B", 4: "B", 5: "A", 6: "B", 7: "C", 8: "A"},
    "m2": {1: "B", 2: "D", 3: "C", 4: "B", 5: "A", 6: "Z", 7: "C", 8: "A"},
    "m3": {1: "A", 2: "D", 3: "A", 4: None, 5: "D", 6: "E", 7: "C", 8: "A"},
    "m4": {1: "C", 2: "D", 3: "B", 4: "A", 5: "A", 6: "B", 7: "B", 8: "A"},
    "m5": {1: "B", 2: "C", 3: "B", 4: "A", 5: "A", 6: "B", 7: "C", 8: "A"},
}
FIX_LABELS = {1: "wrong_groundtruth", 2: "ok", 3: "ok", 4: "ok", 6: "multiple_correct_answers"}
FIX_AMBIGUOUS = {8}
FIX_TARGETS = {1: 1}
FIX_TARGET = {
    "panel": ["m1", "m2", "m3"],
    "flags": {1: (True, 1), 2: (True, 3), 3: (False, None), 4: (False, None), 5: (True, 0), 6: (False, 1),
              7: (True, 2), 8: (False, None)},
    "verdicts": {
        "P2_miskey_flag_rate_5x_ok": False, "P2_counts": [1, 1, 1, 3],
        "P3_recall_and_match_on_targets": True, "P3_counts": [1, 1, 1],
        "P4_flag_precision_on_judged": True, "P4_counts": [1, 2],
        "P5_unreviewed_above_ok": True, "P5_counts": [1, 1, 1, 3],
        "P6_stemez_above_mmlu_derived": True, "P6_counts": [1, 1, 3, 7],
    },
}

# ----- Hand-traced fixture 2: the Redux -> MMLU -> MMLU-Pro join -----
FIX_MMLU = [
    {"subject": "virology", "question": "Q one", "choices": ["a", "b", "c", "d"], "answer": 0},
    {"subject": "virology", "question": "Q two", "choices": ["e", "f", "g", "h"], "answer": 1},
    {"subject": "anatomy", "question": "Q three", "choices": ["i", "j", "k", "l"], "answer": 2},
]
FIX_REDUX = [
    {"subject": "virology", "question": "Q  one", "choices": ["a", "b", "c", "d"], "answer": 0,
     "label": "wrong_groundtruth", "correct": "B"},
    {"subject": "virology", "question": "Q two", "choices": ["e", "f", "g", "h"], "answer": 1, "label": "ok",
     "correct": None},
    {"subject": "anatomy", "question": "Q three", "choices": ["i", "j", "k", "l"], "answer": 2, "label": "ok",
     "correct": None},
    {"subject": "anatomy", "question": "Q four", "choices": ["w", "x", "y", "z"], "answer": 0, "label": "ok",
     "correct": None},
]
FIX_PRO = [
    {"question_id": 10, "question": "Q one", "options": ["a", "b", "c", "x1", "x2"], "answer_index": 0,
     "category": "health", "src": "ori_mmlu-virology"},
    {"question_id": 20, "question": "Q two", "options": ["e", "f", "y1", "y2"], "answer_index": 1,
     "category": "health", "src": "ori_mmlu-virology"},
    {"question_id": 30, "question": "Q three", "options": ["i", "j", "k", "l", "m1"], "answer_index": 2,
     "category": "health", "src": "ori_mmlu-anatomy"},
    {"question_id": 31, "question": "Q three", "options": ["i", "j", "k", "z9"], "answer_index": 2,
     "category": "health", "src": "ori_mmlu-anatomy"},
    {"question_id": 40, "question": "Q one", "options": ["a", "b", "c", "d"], "answer_index": 0,
     "category": "biology", "src": "stemez-Biology"},
]
FIX_REDUX_TARGET = {
    "labels": {10: "wrong_groundtruth"},
    "ambiguous_ids": {30, 31},
    "miskey_ids": {10},
    "counts": {"redux_mmlu": {"joined": 3, "no_match": 1, "ambiguous": 0},
               "pro_join": {"in_pro": 1, "ambiguous_pro": 1, "not_in_pro": 1, "stem_only": 1, "cross_subject": 0},
               "label_conflicts": 0},
}
