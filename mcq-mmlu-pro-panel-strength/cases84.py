"""Frozen inputs for audit 84: audit 77's flag rule and frozen outputs (reproduction gate), the strata, the no-key
rule, pre-registered thresholds, data sources, archives and the hand-traced fixtures (traced in test_panel84.py).
Apache-2.0."""

from fractions import Fraction

# ----- Audit 77's consensus flag, unchanged -----
PANEL_SIZE = 10
MIN_AGREE = 6

# ----- New in audit 84 -----
N_STRATA = 4            # S1..S4 = ranks 1-10, 11-20, 21-30, 31-40 of the included archives by accuracy
TOP20_SIZE = 20         # P6: ranks 1-20 as one panel
TOP20_MIN_AGREE = 12    # exploratory frozen-rule count for the 20-archive panel (60%, as 6 of 10)
UNANIMOUS = 10          # P7 comparator: S1's flag at 10 of 10
NK_MIN_COV = 2          # no-key flag: at least 2 included archives cover the question and none picks the key
WINDOW_STARTS = list(range(0, 36, 5))   # exploratory: sliding 10-archive windows starting at ranks 1, 6, ..., 36

# ----- Pre-registered thresholds -----
THRESHOLDS = {
    "P5_mult": Fraction(2),   # S4's equal-budget precision >= 2x the base rate of error labels among judged questions
    "P7_min_judged": 10,      # P7 is decidable only with at least 10 Redux-judged no-key questions
}
MIN_INCLUDED_ARCHIVES = 40

# ----- Audit 77's frozen outputs (reproduction gate, part of P1; S1 must equal audit 77's panel) -----
EXPECTED_PANEL = [
    "gemini-3.1-pro_5-shots", "arx_0314_5shots", "iask_pro_5shots", "arx_3_5shots",
    "claude-3-5-sonnet-20241022_5shots", "claude-3.5-sonnet_5shots", "gpt-4o-2024-08-06_5shots",
    "sonnet-3.5_0shots_09_34_29", "gpt4o(2024-05-13)_5shots", "gemini-1.5-pro-002_5shots",
]
EXPECTED_77_FLAGGED = {"all": 1210, "miskey": 36, "ok": 294, "other_error": 29, "unreviewed_ori_mmlu": 501,
                       "ori_mmlu": 874, "stemez": 271}
EXPECTED_77_PRECISION = (65, 359)

# ----- Data (as audits 77-79) -----
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
    """'model_outputs_X_5shots.json.zip' -> 'X_5shots' (as audits 66, 77-79)."""
    s = zname[len("model_outputs_"):] if zname.startswith("model_outputs_") else zname
    for suffix in (".zip", ".json"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s


# ----- Fixture 1 (audit 77's, copied): panel and flags on letter predictions -----
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

# ----- Fixture 3 (audit 82's, copied via audit 83): consensus margin and AUC -----
FIX_MARGIN = [(([2, 5, 3, 0], 0), 3), (([6, 1, 1, 2], 0), -4), (([0, 0, 10, 0], 2), -10), (([4, 4, 1, 1], 3), 3)]
FIX_AUC = [(([3, 1], [1, 0, -4]), Fraction(11, 12)), (([0.9, 0.2], [0.5, 0.3, -0.4, -0.6]), Fraction(3, 4)),
           (([6, 2], [4, 2, -8, -10]), Fraction(13, 16)), (([1], [1]), Fraction(1, 2)), (([], [1]), None)]

# ----- Fixture 4 (audit 83's, copied): strata -----
FIX_S_ACC = {"a": (9, 10), "b": (8, 10), "c": (8, 10), "d": (5, 10), "e": (7, 10), "f": (1, 10), "g": (6, 10)}
FIX_S_TARGET = [["a", "b"], ["c", "e"], ["g", "d"]]

# ----- Fixture 5 (audit 83's, copied): budget counts with ties shared -----
FIX_B_SCORE = {0: 3, 1: 3, 2: 1, 3: 1, 4: 1, 5: -2}
FIX_B_SETS = [{0, 2}, {0, 1, 2, 3}, {0}]
FIX_B_CASES = [(4, [Fraction(5, 3), Fraction(10, 3), Fraction(1)]),
               (2, [Fraction(1), Fraction(2), Fraction(1)]),
               (0, [Fraction(0), Fraction(0), Fraction(0)]),
               (10, [Fraction(2), Fraction(4), Fraction(1)])]

# ----- Fixture 6 (audit 83's, copied): one panel's statistics -----
FIX_P_G = {"all": [0, 1, 2, 3, 4, 5], "miskey": [0, 1], "ok": [2, 3, 4], "other_error": [5],
           "unsure_or_conflict": [], "unreviewed": []}
FIX_P_FLAGS = {0: (True, 1), 1: (False, None), 2: (True, 2), 3: (False, None), 4: (False, None), 5: (True, 0)}
FIX_P_SCORE = {0: 4, 1: 0, 2: 4, 3: -6, 4: -2, 5: 1}
FIX_P_BUDGET = 3
FIX_P_TARGET = {"flags": 3, "prec": (2, 3), "miskeys": 1, "auc": Fraction(3, 4), "b_err": Fraction(2),
                "b_judged": Fraction(3), "b_miskey": Fraction(1)}

# ----- Fixture 7 (new): key counts, the no-key flag and the key-share score -----
FIX_K_MODELS = ["a", "b", "c"]
FIX_K_QUESTIONS = {1: (4, 0), 2: (4, 1), 3: (3, 2), 4: (4, 3), 5: (4, 0)}
FIX_K_PREDS = {
    "a": {1: "B", 2: "B", 3: "A", 4: "D", 5: "B"},
    "b": {1: "C", 2: None, 3: "D"},
    "c": {1: "B", 2: "A", 3: "B"},
}
FIX_K_COUNTS = {1: (3, 0), 2: (3, 1), 3: (3, 0), 4: (1, 1), 5: (1, 0)}
FIX_K_NK = {1: (True, None), 2: (False, None), 3: (True, None), 4: (False, None), 5: (False, None)}
FIX_K_SHARE = {1: Fraction(0), 2: Fraction(-1, 3), 3: Fraction(0), 4: Fraction(-1), 5: Fraction(0)}


# ----- Fixture 8 (new): verdicts -----
def _st(flags, auc_v, b_err, b_judged):
    return {"flags": flags, "prec": (0, 0), "miskeys": 0, "auc": auc_v, "b_err": Fraction(b_err),
            "b_judged": Fraction(b_judged), "b_miskey": Fraction(0)}


FIX_V_ST = [_st(10, Fraction(4, 5), 3, 5), _st(12, Fraction(3, 4), 2, 5), _st(14, Fraction(3, 4), 2, 5),
            _st(20, Fraction(7, 10), 1, 5)]
FIX_V_TOP20 = _st(9, Fraction(4, 5), 3, 5)
FIX_V_BASE = (1, 20)
FIX_V_NK = (4, 6)
FIX_V_UNAN = (3, 6)
FIX_VERDICTS = {
    "P2_weaker_flags_more": True, "P2_counts": [10, 20],
    "P3_budget_precision_falls": True, "P3_precision": [0.6, 0.4, 0.2],
    "P4_auc_s1_above_s4": True, "P4_auc": [0.8, 0.7],
    "P5_weakest_still_informative": True, "P5_counts": [1.0, 5.0, 1, 20],
    "P6_top20_not_better": True, "P6_precision": [0.6, 0.6],
    "P7_no_key_beats_unanimous": False, "P7_counts": [4, 6, 3, 6],
}
