"""Hand-traced fixtures, real-data configuration and pinned audit-63 numbers for audit 65. Apache-2.0."""

from fractions import Fraction

# ----- Accumulator fixtures (each traced by hand; see the comments) -----
ADD_ROWS = [
    # F1 lens [2,1,3], gold 0 not unique-longest; pred C (idx 2) wrong. Distractor lens [1,3]: max 3 once of 2.
    #    chosen len 3 == max -> obs +1; base +1/2.
    (["aa", "b", "ccc"], 0, "C"),
    # F2 lens [4,1,2], gold 0 unique-longest; pred A correct.
    (["dddd", "e", "ff"], 0, "A"),
    # F3 lens [1,2,2,1], gold 3 not unique-longest; pred A (idx 0) wrong. Distractor lens [1,2,2]: max 2 twice of 3.
    #    chosen len 1 != 2 -> obs +0; base +2/3.
    (["x", "yy", "zz", "w"], 3, "A"),
    # F4 lens [1,2], gold 1 unique-longest; pred None -> n_none.
    (["p", "qq"], 1, None),
    # F5 lens [1,2], gold 1 unique-longest; pred "Z" malformed -> n_none.
    (["p", "qq"], 1, "Z"),
    # F6 lens [1,1,1], gold 0 not unique-longest (three-way tie); pred "D" out of range for k=3 -> n_none.
    (["a", "b", "c"], 0, "D"),
    # F7 lens [2,2] after strip (" ab " -> "ab"), gold 1 not unique-longest; pred " b " -> idx 1 correct.
    ([" ab ", "cd"], 1, " b "),
]

ADD_TARGET = {
    "n": 7, "n_none": 3, "n_correct": 2, "n_wrong": 2,
    "obs_longest": 1, "base_longest": Fraction(7, 6),
    "n_gold_ul": 3, "correct_gold_ul": 1,          # F2 correct; F4, F5 not
    "n_gold_not_ul": 4, "correct_gold_not_ul": 1,  # F7 correct; F1, F3, F6 not
}

# Tie-aware pick-longest credit: [3,1,3] gold 0 -> 1/2; [1,2] gold 0 -> 0; [4,1] gold 0 -> 1.
CREDIT_CASES = [
    (["aaa", "b", "ccc"], 0, Fraction(1, 2)),
    (["a", "bb"], 0, Fraction(0)),
    (["aaaa", "b"], 0, Fraction(1)),
]

# ----- Join fixtures -----
JOIN_HF = {1: {"options": ["a", "b"], "answer_index": 0, "src": "stemez-Biology", "category": "biology"}}
JOIN_CASES = [
    ({"question_id": 1, "options": [" a", "b "], "answer_index": 0}, "ok"),
    ({"question_id": 2, "options": ["a", "b"], "answer_index": 0}, "no_id"),
    ({"question_id": 1, "options": ["a", "c"], "answer_index": 0}, "options_differ"),
    ({"question_id": 1, "options": ["a", "b"], "answer_index": 1}, "answer_differ"),
    ({"question_id": 1, "options": ["a", "b"], "answer": "A"}, "ok"),
    ({"question_id": 1, "options": ["a", "b"], "answer": "B"}, "answer_differ"),
    ({"question_id": "1", "options": ["a", "b"], "answer_index": 0}, "ok"),
]

# ----- keys_for fixtures -----
KEY_CASES = [
    ({"src": "stemez-Biology", "category": "biology"}, ["ALL", "fam:stemez", "sub:stemez-biopsy"]),
    ({"src": "stemez-Genetics", "category": "biology"}, ["ALL", "fam:stemez"]),
    ({"src": "ori_mmlu-high_school_psychology", "category": "psychology"},
     ["ALL", "fam:ori_mmlu", "sub:ori-biopsy"]),
    ({"src": "theoremQA-Math", "category": "math"}, ["ALL", "fam:theoremQA"]),
]

# ----- Real-data configuration -----
MMLU_PRO = {
    "hf": "TIGER-Lab/MMLU-Pro",
    "config": "default",
    "splits": ["test"],
    "cols": ["question_id", "options", "answer_index", "category", "src"],
}

EVAL_RESULTS_URL = "https://github.com/TIGER-AI-Lab/MMLU-Pro/raw/refs/heads/main/eval_results/%s"

# Per-question prediction archives published by TIGER-AI-Lab (5-shot CoT unless the name says otherwise), chosen
# before any was opened to span model families and sizes. An archive whose records do not parse or join is reported
# and left out, never patched.
MODEL_ZIPS = [
    "model_outputs_Llama-2-7b-hf_5shots.zip",
    "model_outputs_Llama-2-70b-hf_5shots.zip",
    "model_outputs_Meta-Llama-3-8B-Instruct_5shots.zip",
    "model_outputs_Meta-Llama-3-70B-Instruct_5shots.zip",
    "model_outputs_Meta-Llama-3_1-8B-Instruct_5shots.zip",
    "model_outputs_Meta-Llama-3_1-70B-Instruct_5shots.zip",
    "model_outputs_Mistral-7B-Instruct-v0.2_5shots.zip",
    "model_outputs_Mixtral-8x7B-Instruct-v0.1_5shots.zip",
    "model_outputs_Phi-3-mini-4k-instruct_5shots.zip",
    "model_outputs_gemma-7b_5shots.zip",
    "model_outputs_Yi-34B_5shots.zip",
    "model_outputs_Qwen1.5-72B-Chat_5shots.zip",
    "model_outputs_DeepSeek-Coder-V2_5shots.zip",
    "model_outputs_gpt-4o-mini_5shots.zip",
    "model_outputs_gpt-4o-2024-08-06_5shots.zip",
    "model_outputs_gemini-1.5-pro-002_5shots.zip",
    "model_outputs_claude-3.5-sonnet_5shots.zip",
]

# A model is included only if at least this share of its records join cleanly AND its clean records cover at
# least this share of the 12,032 test questions.
MIN_JOIN_SHARE = 0.95

# Structural gate: copied from audit 63's results.json (mcq-mmlu-pro-source-length-census-v1).
EXPECTED = {
    "n_valid": 12032,
    "family_n": {"ori_mmlu": 6810, "stemez": 4083, "scibench": 541, "theoremQA": 598},
    "src_pick_longest": {
        "stemez-Biology": (351, 0.6670736670736671),
        "stemez-Psychology": (305, 0.6700858704137392),
    },
}
