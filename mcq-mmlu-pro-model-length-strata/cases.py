"""Hand-traced fixtures, real-data configuration and pinned audit-63 / audit-65 numbers for audit 66. Apache-2.0."""

from fractions import Fraction

# ----- length_rank fixtures (options, gold, pick, expected) -----
RANK_CASES = [
    # lens [1,2,3,4], gold 3 -> distractor lens [1,2,3]. Pick len 3: less 2, equal 1 -> (4+1-1)/(2*2) = 1.
    (["a", "bb", "ccc", "dddd"], 3, 2, Fraction(1)),
    # Pick len 1: less 0, equal 1 -> 0/4 = 0.
    (["a", "bb", "ccc", "dddd"], 3, 0, Fraction(0)),
    # Pick len 2: less 1, equal 1 -> 2/4 = 1/2.
    (["a", "bb", "ccc", "dddd"], 3, 1, Fraction(1, 2)),
    # lens [2,2,1,2], gold 2 -> distractor lens [2,2,2] all tied: less 0, equal 3 -> 2/4 = 1/2.
    (["aa", "bb", "c", "dd"], 2, 0, Fraction(1, 2)),
    # pick is the gold -> None
    (["a", "bb", "ccc"], 1, 1, None),
    # only one distractor (k = 2) -> None
    (["a", "bb"], 0, 1, None),
    # no pick -> None
    (["a", "bb", "ccc"], 0, None, None),
]

# ----- add_strata fixture: (src, options, gold, pred), traced by hand -----
STRATA_ROWS = [
    # S1 lens [1,2,3], gold 2 unique-longest; pred C correct -> s1 [1,1,0,0]; no rank.
    ("s1", ["a", "bb", "ccc"], 2, "C"),
    # S2 lens [3,1,2], gold 1 not UL; pred A wrong -> s1 [1,1,1,0]. Distractors [3,2], pick len 3:
    #    less 1, equal 1 -> (2+1-1)/(2*1) = 1. rank_n 1, sum 1.
    ("s1", ["aaa", "b", "cc"], 1, "A"),
    # S3 lens [2,1,1], gold 0 UL; pred B wrong -> s2 [1,0,0,0]. Distractors [1,1], pick len 1:
    #    less 0, equal 2 -> 1/2. rank_n 2, sum 3/2.
    ("s2", ["aa", "b", "c"], 0, "B"),
    # S4 lens [1,2,2], gold 0 not UL; pred None -> s2 [1,0,1,0]; no rank.
    ("s2", ["a", "bb", "cc"], 0, None),
    # S5 lens [1,1,2], gold 1 not UL; pred B correct -> s2 [1,0,2,1].
    ("s2", ["x", "y", "zz"], 1, "B"),
]
STRATA_TARGET = {"rank_n": 2, "rank_sum": Fraction(3, 2), "src": {"s1": [1, 1, 1, 0], "s2": [1, 0, 2, 1]}}

# Mantel-Haenszel by hand: s1 n1=1 c1=1 n0=1 c0=0, N=2 -> num 1/2, den 1/2;
# s2 n1=1 c1=0 n0=2 c0=1, N=3 -> num -1/3, den 2/3; s3 has no unique-longest group -> skipped.
# RD = (1/2 - 1/3) / (1/2 + 2/3) = (1/6) / (7/6) = 1/7; 2 strata, 5 questions.
MH_CELLS = [[1, 1, 1, 0], [1, 0, 2, 1], [0, 0, 3, 1]]
MH_TARGET = (Fraction(1, 7), 2, 5)
# Crude RD on STRATA_TARGET: 1/2 - 1/3 = 1/6. Mean rank: 3/4.
STRATA_REPORT = {"length_rank_n": 2, "length_rank_mean": 0.75, "mh_rd_gold_ul": 1 / 7, "mh_strata": 2,
                 "mh_n": 5, "crude_rd_gold_ul": 1 / 6}

# ----- Real-data configuration -----
MMLU_PRO = {
    "hf": "TIGER-Lab/MMLU-Pro",
    "config": "default",
    "splits": ["test"],
    "cols": ["question_id", "options", "answer_index", "category", "src"],
}

EVAL_RESULTS_URL = "https://github.com/TIGER-AI-Lab/MMLU-Pro/raw/refs/heads/main/eval_results/%s"

# Every archive listed in eval_results on 2026-10-30 (the listing was read; no archive opened beyond the 17 of
# audit 65). An archive whose records do not parse or join is reported and left out, never patched.
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

# Same inclusion rule as audit 65.
MIN_JOIN_SHARE = 0.95

# Structural gate 1: copied from audit 63's results.json (mcq-mmlu-pro-source-length-census-v1).
EXPECTED = {
    "n_valid": 12032,
    "family_n": {"ori_mmlu": 6810, "stemez": 4083, "scibench": 541, "theoremQA": 598},
    "src_pick_longest": {
        "stemez-Biology": (351, 0.6670736670736671),
        "stemez-Psychology": (305, 0.6700858704137392),
    },
}

# Structural gate 2: audit 65's pooled n and error pull per model, with the archive sha256 it read
# (mcq-mmlu-pro-model-length-pull-v1/out/results.json). Checked only where the archive is byte-identical.
AUDIT65 = {
    "Llama-2-7b-hf_5shots": (
        "57c47f6e70da9d5edf44a4803f75550c553feaadd94340dd9fef09afdeb82e09", 11813, 1.114871937027142),
    "Llama-2-70b-hf_5shots": (
        "1e3e50201339dfc25a4f2a009afecee6bc1d188f51c5fb4bd04b0b2bb683b9ce", 11813, 1.0743197045494894),
    "Meta-Llama-3-8B-Instruct_5shots": (
        "981b7216dd9075d86a832ac6900e2a0e6a6c9d16b278f03949fd149e0f9e7db8", 11813, 1.1044323801014728),
    "Meta-Llama-3_1-8B-Instruct_5shots": (
        "d5e76b2564b5baad90892c3664287a51f562a3be792a130acaec458b8560a1cf", 11821, 1.0546706250184932),
    "Meta-Llama-3_1-70B-Instruct_5shots": (
        "26573565138fcd27358a0945c9f525a7d9a75a756689058a0d5bfcbc64fa55cb", 11821, 1.0688979408423864),
    "Mistral-7B-Instruct-v0.2_5shots": (
        "ff1c5ae8a0f6412cca52537746f192476398c24590a3fb79e8f10c300ffa8248", 11813, 1.1396857711744222),
    "Mixtral-8x7B-Instruct-v0.1_5shots": (
        "4716478ca233a86baa39b1c99452589191d8db3df3b398c871ff2832959408aa", 11813, 1.0916112368686748),
    "Phi-3-mini-4k-instruct_5shots": (
        "7f45083108479ef586cc6c855325294c1220a9fcb614066abf22234a26d7037e", 11813, 1.1196282299651465),
    "gemma-7b_5shots": (
        "479a85f9f3598c5db75279e95452dd972a719f09eda983925be3595cb60767d9", 11813, 1.096134300279533),
    "Yi-34B_5shots": (
        "17e44df39275a324a250fee8b98f96d8cddcdc00e68f171f07996db9012c5f27", 11813, 1.0764535893412939),
    "Qwen1.5-72B-Chat_5shots": (
        "a87935dfe3c349c06115a3b82e299dea30929a3b25ababc879394b58cc93c0b9", 11813, 1.1071082036329405),
    "gpt-4o-mini_5shots": (
        "a7f1cee97f5fda4a0b16bd3798d1225d9cfc48d96c4d656401ff59d34fd74b0f", 11821, 1.0815818190743145),
    "gpt-4o-2024-08-06_5shots": (
        "dd48813a4bc40286a2d1c7aa42d288dac9a2b576bbb7b98bd8901f2556b1e9cf", 11854, 1.0699378571446607),
    "gemini-1.5-pro-002_5shots": (
        "7d95c116e999dc15012d753e871bbbc8fd4e74b9feb49b992ea55247576af370", 11842, 1.0600463483468325),
    "claude-3.5-sonnet_5shots": (
        "75694e83610ffa500531a34d28a82fa93062eaa284b134427ea69055e816ca60", 11819, 1.0796443990420463),
}

# Archives audit 65 attempted (included or not); everything else is "new" for P7.
AUDIT65_ATTEMPTED = set(AUDIT65) | {"Meta-Llama-3-70B-Instruct_5shots", "DeepSeek-Coder-V2_5shots"}


def model_name(zname):
    """'model_outputs_X_5shots.json.zip' -> 'X_5shots'."""
    s = zname[len("model_outputs_"):] if zname.startswith("model_outputs_") else zname
    for suffix in (".zip", ".json"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s
