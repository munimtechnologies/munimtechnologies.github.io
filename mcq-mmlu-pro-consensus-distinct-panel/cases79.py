"""Frozen inputs for audit 79: audit 77's panel rule and frozen outputs (reproduction gate), the model lines, the
expected one-archive-per-line panel, pre-registered thresholds, data sources, archives and the hand-traced fixtures.
Apache-2.0."""

from fractions import Fraction

# ----- Audit 77's flag, unchanged -----
PANEL_SIZE = 10
MIN_AGREE = 6

# ----- Model lines: archives of the same model (repeated runs or dated versions of one model). Every archive not
# listed here is its own line. -----
LINES = {
    "claude-3-5-sonnet-20241022_5shots": "claude-3.5-sonnet",
    "claude-3.5-sonnet_5shots": "claude-3.5-sonnet",
    "sonnet-3.5_0shots_09_34_29": "claude-3.5-sonnet",
    "gpt-4o-2024-08-06_5shots": "gpt-4o",
    "gpt4o(2024-05-13)_5shots": "gpt-4o",
    "arx_0314_5shots": "arx",
    "arx_3_5shots": "arx",
}

# ----- Pre-registered thresholds -----
THRESHOLDS = {
    "P2_ratio": Fraction(5),   # the distinct panel flags Redux-miskeyed questions >= 5x as often as Redux-OK ones
    "P4_min_miskeys": 30,      # the distinct panel flags at least 30 of the 55 Redux-miskeyed questions
}
MIN_INCLUDED_ARCHIVES = 30

# ----- Audit 77's frozen outputs (reproduction gate, part of P1) -----
EXPECTED_PANEL = [
    "gemini-3.1-pro_5-shots", "arx_0314_5shots", "iask_pro_5shots", "arx_3_5shots",
    "claude-3-5-sonnet-20241022_5shots", "claude-3.5-sonnet_5shots", "gpt-4o-2024-08-06_5shots",
    "sonnet-3.5_0shots_09_34_29", "gpt4o(2024-05-13)_5shots", "gemini-1.5-pro-002_5shots",
]
EXPECTED_77_FLAGGED = {"all": 1210, "miskey": 36, "ok": 294, "other_error": 29, "unreviewed_ori_mmlu": 501,
                       "ori_mmlu": 874, "stemez": 271}
EXPECTED_77_PRECISION = (65, 359)

# The one-archive-per-line panel implied by audit 78's published accuracies (results.json, 2026-11-02). Part of P1.
EXPECTED_DISTINCT_PANEL = [
    "gemini-3.1-pro_5-shots", "arx_0314_5shots", "iask_pro_5shots", "claude-3-5-sonnet-20241022_5shots",
    "gpt-4o-2024-08-06_5shots", "gemini-1.5-pro-002_5shots", "opus_2shots_00_37_14", "deepseek-chat-v2_5_5shots",
    "gemini-1.5-flash-002_5shots", "gpt-4o-mini_5shots",
]

# ----- Data (as audits 77 and 78) -----
MMLU_PRO = {"hf": "TIGER-Lab/MMLU-Pro", "config": "default", "splits": ["test"],
            "cols": ["question_id", "question", "options", "answer_index", "category", "src"]}
MMLU = {"hf": "cais/mmlu", "config": "all", "splits": ["test"], "cols": ["subject", "question", "choices", "answer"]}
REDUX_DATASET = "edinburgh-dawg/mmlu-redux-2.0"
REDUX_SPLIT = "test"
EXPECTED = {"n_valid": 12032, "family_n": {"ori_mmlu": 6810, "stemez": 4083, "scibench": 541, "theoremQA": 598}}
EXPECTED_REDUX = {"joined": 5690, "in_pro": 2758, "ambiguous_pro": 71}   # audit 75
N_MISKEY_IDS = 55
EVAL_RESULTS_URL = "https://github.com/TIGER-AI-Lab/MMLU-Pro/raw/refs/heads/main/eval_results/%s"
MIN_JOIN_SHARE = 0.95

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
    """'model_outputs_X_5shots.json.zip' -> 'X_5shots' (as audits 66, 77 and 78)."""
    s = zname[len("model_outputs_"):] if zname.startswith("model_outputs_") else zname
    for suffix in (".zip", ".json"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s


# ----- Fixture 1 (audit 77's, copied): panel and flags -----
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

# ----- Fixture 2 (audit 77's, copied): the Redux -> MMLU -> MMLU-Pro join -----
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

# ----- Fixture 3 (new): one archive per line (traced in test_distinct79.py) -----
FIX_D_ACC = {"a1": (9, 10), "a2": (8, 10), "b1": (7, 10), "c1": (6, 10), "e1": (6, 10), "d1": (5, 10)}
FIX_D_LINES = {"a1": "A", "a2": "A"}
FIX_D_SIZE = 3
FIX_D_TARGET = ["a1", "b1", "c1"]

# ----- Fixture 4 (new): shared wrong answers (traced in test_distinct79.py) -----
FIX_W_QUESTIONS = {1: (4, 0), 2: (4, 0), 3: (4, 1), 4: (4, 0), 5: (3, 2)}
FIX_W_PREDS = {
    "a1": {1: "B", 2: "C", 3: "A", 4: "A", 5: "D"},
    "a2": {1: "B", 2: "D", 3: "A", 4: "B", 5: "A"},
    "b1": {1: "C", 2: "C", 3: "C", 4: "C", 5: "B"},
}
FIX_W_TARGET = {
    "a1_a2": (2, 3),
    "within": {"a1|a2": (2, 3, Fraction(2, 3))},
    "cross": {"a1|b1": (1, 3, Fraction(1, 3)), "a2|b1": (0, 5, Fraction(0))},
}

# ----- Fixture 5 (new): verdicts (traced in test_distinct79.py) -----
FIX_G = {"miskey": [1, 2], "ok": [3, 4, 5, 6], "other_error": [7], "stemez": [8, 9],
         "ori_mmlu": [1, 2, 3, 4, 5, 6, 7]}
FIX_FLAGS_D = {1: (True, 1), 2: (False, None), 3: (True, 2), 4: (False, None), 5: (False, 1), 6: (False, None),
               7: (True, 3), 8: (True, 1), 9: (False, None)}
FIX_FLAGS_A = {1: (True, 1), 2: (True, 2), 3: (True, 2), 4: (True, 1), 5: (False, None), 6: (False, None),
               7: (False, None), 8: (False, None), 9: (False, None)}
FIX_VERDICTS = {
    "P2_distinct_ratio": False, "P2_counts": [1, 2, 1, 4],
    "P3_distinct_precision_higher": True, "P3_counts": [2, 3, 2, 4],
    "P4_distinct_recall": False, "P4_counts": [1, 2],
    "P5_within_line_above_cross_median": True, "P5_counts": ["2/3", "1/6", 1, 2],
    "P6_stemez_below_mmlu": False, "P6_counts": [1, 2, 3, 7],
}
