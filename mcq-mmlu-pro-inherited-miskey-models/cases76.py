"""Frozen inputs for audit 76: the 46 target questions (from audit 75's pro_flags.json), the 55 miskey ids, data
sources, pre-registered thresholds and the hand-traced fixture. Apache-2.0."""

from fractions import Fraction

# ----- Targets: audit 75 (mcq-mmlu-pro-redux-inheritance-v1/out/pro_flags.json), rows with label
# wrong_groundtruth, key_status kept, and an experts' answer that is one of MMLU-Pro's options.
# (question_id, src, MMLU-Pro key letter, experts' answer letter among MMLU-Pro's options, basis)
# basis "primary" = Redux letter or exact-text correction; "digits_0_based" = Redux digit read 0-based.
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

# All 55 Redux-miskeyed questions MMLU-Pro holds with one match (audit 75), kept, moved or unresolved; they are
# left out of the control set.
MISKEY_IDS = frozenset([
    1418, 1989, 2454, 2817, 2933, 3538, 3636, 3637, 3725, 3811, 3814, 3894, 3990, 4084, 4088, 4089, 4341, 4346,
    4437, 4438, 4511, 4607, 4609, 4752, 5225, 5726, 5885, 5949, 6067, 6068, 6224, 6277, 6278, 6586, 6639, 6640,
    6642, 7306, 7687, 7791, 8122, 8780, 8876, 8972, 9547, 9677, 9733, 9814, 9947, 10365, 10458, 10533, 10666,
    10859, 11579])
N_MISKEY_IDS = 55

# ----- Pre-registered thresholds -----
MIN_TARGETS_PER_MODEL = 40      # a model counts for P3/P5 only with joined predictions on >= 40 of the 46
MIN_TARGETS_STILL_KEYED = 44    # P1: at least 44 of 46 targets still carry audit 75's key letter in the HF data
MIN_INCLUDED_ARCHIVES = 30      # P1: at least 30 archives pass the audit-65 join rule
THRESHOLDS = {"P3_share": Fraction(3, 4), "P4_ratio": 3, "P6_share": Fraction(3, 5)}

# ----- Data (as audits 65/66) -----
MMLU_PRO = {"hf": "TIGER-Lab/MMLU-Pro", "config": "default", "splits": ["test"],
            "cols": ["question_id", "options", "answer_index", "category", "src"]}
EXPECTED = {"n_valid": 12032, "family_n": {"ori_mmlu": 6810, "stemez": 4083, "scibench": 541, "theoremQA": 598}}
EVAL_RESULTS_URL = "https://github.com/TIGER-AI-Lab/MMLU-Pro/raw/refs/heads/main/eval_results/%s"
MIN_JOIN_SHARE = 0.95

# The 48 archives audit 66 listed in eval_results on 2026-10-30.
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


# ----- Hand-traced fixture (traced line by line in test_inherit_models.py) -----
# Two questions: q1 has 4 options, key A (0), experts' answer B (1), basis primary;
#                q2 has 10 options, key C (2), experts' answer F (5), basis digits_0_based.
FIX_QUESTIONS = {1: (4, 0, 1, "primary"), 2: (10, 2, 5, "digits_0_based")}
# (model, qid, pred)
FIX_PREDS = [
    ("m1", 1, "B"), ("m1", 2, "F"),     # expert, expert
    ("m2", 1, "A"), ("m2", 2, "J"),     # key, other (k=10 -> 1/8)
    ("m3", 1, "C"), ("m3", 2, None),    # other (k=4 -> 1/2), none
]
FIX_CONTROL_ACCURACY = {"m1": 0.5, "m2": 0.6, "m3": 0.1}
FIX_MIN_TARGETS = 2
FIX_TARGET = {
    "models": {
        "m1": {"n": 2, "key": 0, "expert": 2, "other": 0, "none": 0, "other_per_distractor": Fraction(0)},
        "m2": {"n": 2, "key": 1, "expert": 0, "other": 1, "none": 0, "other_per_distractor": Fraction(1, 8)},
        "m3": {"n": 2, "key": 0, "expert": 0, "other": 1, "none": 1, "other_per_distractor": Fraction(1, 2)},
    },
    "per_question": {
        1: {"n": 3, "key": 1, "expert": 1, "other": 1, "none": 0, "other_per_distractor": Fraction(1, 2)},
        2: {"n": 3, "key": 0, "expert": 1, "other": 1, "none": 1, "other_per_distractor": Fraction(1, 8)},
    },
    "verdicts": {
        "P2_pooled_expert_over_key": True, "P2_counts": [2, 1],
        "P3_most_models_expert_over_key": False, "P3_counts": [1, 3],
        "P4_expert_vs_average_distractor": True, "P4_counts": [2, 0.625],
        "P5_key_rate_below_control_every_model": True, "P5_counts": [3, 3],
        "P6_questions_expert_over_key": False, "P6_counts": [1, 2],
        "P7_primary_subset_expert_over_key": False, "P7_counts": [1, 1],
    },
}
