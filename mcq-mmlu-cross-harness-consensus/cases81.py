"""Frozen inputs for audit 81: audit 77's flag rule, the reproduction gates for audits 77 and 80, the pre-registered
thresholds, data sources, TIGER-AI-Lab's archive list and the hand-traced fixtures (traced in test_cross81.py).
Apache-2.0."""

from fractions import Fraction

# ----- Audit 77's flag, unchanged (used by both panels) -----
PANEL_SIZE = 10
MIN_AGREE = 6

# ----- Pre-registered thresholds -----
THRESHOLDS = {
    "P4_min_retention": Fraction(1, 2),   # the agreement flag keeps >= half of HELM's flagged Redux miskeys in J
    "P5_ratio": Fraction(2),              # Redux-OK retention <= half of Redux-miskey retention
}
MIN_PAIRS_SAME_KEY = 5500                 # P1: joined pairs whose two keys have the same option text
MIN_SAME_KEY_SHARE = Fraction(97, 100)    # P1: share of joined pairs with the same key text

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

# ----- Audit 77's frozen outputs (reproduction gate, part of P1) -----
EXPECTED_77 = {
    "panel": ["gemini-3.1-pro_5-shots", "arx_0314_5shots", "iask_pro_5shots", "arx_3_5shots",
              "claude-3-5-sonnet-20241022_5shots", "claude-3.5-sonnet_5shots", "gpt-4o-2024-08-06_5shots",
              "sonnet-3.5_0shots_09_34_29", "gpt4o(2024-05-13)_5shots", "gemini-1.5-pro-002_5shots"],
    "flagged": {"all": 1210, "ori_mmlu": 874, "stemez": 271},
}

# ----- HELM (as audit 80) -----
N_SUBJECTS = 57
HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/mmlu/benchmark_output"
HELM_RELEASE = "v1.13.0"
MIN_COVERAGE = Fraction(99, 100)
MIN_CONSISTENT = Fraction(99, 100)
MAX_EM_GAP = Fraction(5, 1000)
WORKERS = 12

# ----- MMLU-Redux 2.0 (as audit 80) -----
REDUX_DATASET = "edinburgh-dawg/mmlu-redux-2.0"
REDUX_SPLIT = "test"
ABORT_REDUX_JOINED = 4000

# ----- MMLU-Pro and TIGER-AI-Lab's archives (as audits 77-79) -----
MMLU_PRO = {"hf": "TIGER-Lab/MMLU-Pro", "config": "default", "splits": ["test"],
            "cols": ["question_id", "question", "options", "answer_index", "category", "src"]}
EXPECTED_PRO = {"n_valid": 12032, "family_n": {"ori_mmlu": 6810, "stemez": 4083, "scibench": 541, "theoremQA": 598}}
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

# ----- Fixture 6 (new): the MMLU-Pro -> HELM join (traced in test_cross81.py) -----
FIX_J_QIDS = {
    ("virology", ("V1", ("a", "b", "c", "d"))): 0,
    ("virology", ("V2", ("e", "f", "g", "h"))): 1,
    ("virology", ("V2", ("e", "f", "x", "y"))): 2,
    ("anatomy", ("A1", ("i", "j", "k", "l"))): 3,
    ("anatomy", ("A2", ("m", "n", "o", "p"))): 4,
}
FIX_J_HELM_OPTS = [["a", "b", "c", "d"], ["e", "f", "g", "h"], ["e", "f", "x", "y"], ["i", "j", "k", "l"],
                   ["m", "n", "o", "p"]]
FIX_J_STEMS = {("virology", "V1"): [0], ("virology", "V2"): [1, 2], ("anatomy", "A1"): [3], ("anatomy", "A2"): [4]}
FIX_J_PRO = [
    {"question_id": 10, "question": "V1 ", "options": ["a", "b", "c", "z1", "z2"], "src": "ori_mmlu-virology"},
    {"question_id": 11, "question": "V2", "options": ["e", "f", "g", "z"], "src": "ori_mmlu-virology"},
    {"question_id": 12, "question": "V2", "options": ["e", "f", "x", "y", "g", "h"], "src": "ori_mmlu-virology"},
    {"question_id": 13, "question": "A1", "options": ["i", "j", "q", "r"], "src": "ori_mmlu-anatomy"},
    {"question_id": 14, "question": "A2", "options": ["m", "n", "o", "p"], "src": "ori_mmlu-anatomy"},
    {"question_id": 15, "question": "A2", "options": ["m", "n", "o", "s"], "src": "ori_mmlu-anatomy"},
    {"question_id": 16, "question": "V1", "options": ["a", "b", "c", "d"], "src": "stemez-Biology"},
    {"question_id": 17, "question": "Nope", "options": ["a", "b", "c", "d"], "src": "ori_mmlu-anatomy"},
    {"question_id": 18, "question": "A1", "options": ["i", "j", "k", "l"], "src": "ori_mmlu-virology"},
]
FIX_J_TARGET = ({0: 10, 1: 11},
                {"pro_mmlu_rows": 8, "no_stem": 2, "stem_only": 1, "ambiguous_helm": 1, "pro_dup": 2, "joined": 2})

# ----- Fixture 7 (new): the agreement flag -----
FIX_A_J = [0, 1, 3, 4]
FIX_A_PAIRS = {0: 10, 1: 11, 3: 13, 4: 14}
FIX_A_PRO_OPTS = {10: ["a", "b", "c", "z1", "z2"], 11: ["e", "f", "g", "z"], 13: ["i", "j", "k", "l"],
                  14: ["p", "o", "n", "m"]}
FIX_A_HELM_FLAGS = {0: (True, 1), 1: (True, 2), 2: (False, None), 3: (True, 0), 4: (True, 3)}
FIX_A_PRO_FLAGS = {10: (True, 1), 11: (True, 3), 13: (False, 0), 14: (True, 0)}
FIX_A_TARGET = {0: (True, 1), 1: (False, None), 3: (False, None), 4: (True, 3)}

# ----- Fixture 8 (new): verdicts -----
FIX_V_GJ = {"miskey": [1, 2], "ok": [3, 4, 5, 6], "other_error": [7], "unreviewed": [8]}
FIX_V_GJX = {"miskey": [1], "ok": [3, 4, 5], "other_error": [7], "unreviewed": []}
FIX_V_HELM = {1: (True, 0), 2: (True, 1), 3: (True, 2), 4: (True, 1), 5: (True, 0), 6: (False, None),
              7: (True, 3), 8: (True, 1)}
FIX_V_PRO = {1: (True, 0), 2: (False, None), 3: (True, 2), 4: (True, 3), 5: (False, None), 6: (True, 1),
             7: (False, None), 8: (True, 1)}
FIX_V_AGREE = {1: (True, 0), 2: (False, None), 3: (True, 2), 4: (False, None), 5: (False, None), 6: (False, None),
               7: (False, None), 8: (True, 1)}
FIX_VERDICTS = {
    "P2_agree_beats_helm": False, "P2_counts": [1, 2, 3, 6],
    "P3_agree_beats_pro": True, "P3_counts": [1, 2, 1, 4],
    "P4_miskey_retention": True, "P4_counts": [1, 2],
    "P5_ok_retention_low": False, "P5_counts": [1, 3, 1, 2],
    "P6_agree_beats_helm_no_virology": True, "P6_counts": [1, 2, 2, 5],
}
