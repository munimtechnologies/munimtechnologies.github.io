"""Configuration, pinned numbers, pre-registered thresholds and hand-traced fixtures for audit 73. Apache-2.0.
Authored by AI agents working in the name of MV2, Munim, Inc."""

SPLIT = "test"
MMLU_DATASET = "cais/mmlu"
MMLU_CONFIG = "all"
MMLU_COLUMNS = ("question", "subject", "choices", "answer")
MMMLU_DATASET = "openai/MMMLU"
MMMLU_CONFIGS = ("AR_XY", "BN_BD", "DE_DE", "ES_LA", "FR_FR", "HI_IN", "ID_ID", "IT_IT", "JA_JP", "KO_KR", "PT_BR",
                 "SW_KE", "YO_NG", "ZH_CN")
MMMLU_COLUMNS = ("Question", "A", "B", "C", "D", "Answer", "Subject")
GMMLU_DATASET = "CohereLabs/Global-MMLU"
GMMLU_COLUMNS = ("sample_id", "question", "option_a", "option_b", "option_c", "option_d", "answer")
# Global-MMLU languages taken from MMMLU (arXiv 2412.03304: "we utilized the remaining 10 languages").
GMMLU_FROM_MMMLU = {"bn": "BN_BD", "de": "DE_DE", "id": "ID_ID", "it": "IT_IT", "ja": "JA_JP", "ko": "KO_KR",
                    "pt": "PT_BR", "sw": "SW_KE", "yo": "YO_NG", "zh": "ZH_CN"}

EXPECTED_N_ROWS = 14042
FOCUS = ("ZH_CN", "KO_KR")
FOCUS_GMMLU = ("zh", "ko")
FOCUS_SUBJECT = "high_school_world_history"
FOCUS_START = 5852          # first position of the subject in MMLU 'all' test (datasets-server rows API)
FOCUS_N = 237

# Audits 70/71 (descriptive comparison only, not a gate): Global-MMLU same-id key differences from English there.
AUDIT71_FOCUS_KEY_DIFFS = {"zh": 176, "ko": 116}

# Pre-registered thresholds (written before any audit-73 number was seen).
P1_MIN_SUBJECT_AGREE = 0.99      # MMMLU rows whose own Subject equals MMLU's subject at the same position
P2_MIN_MISALIGNED_SHARE = 0.25   # misaligned rows / 237 in each of ZH_CN and KO_KR high_school_world_history
P3_MIN_N = 20
P3_MIN_CONTENT_KEY = 0.95        # misaligned MMMLU rows whose key equals the key of the MMLU question they hold
P4_MIN_N = 20
P4_MIN_INHERITED = 0.95          # Global-MMLU zh/ko rows on MMMLU-misaligned positions: same fingerprint and key
FLAG_MIN_MISALIGNED = 5          # (config, subject) cells with at least this many misaligned rows are flagged
P6_MIN_IDENTICAL = 0.95          # each of the ten languages: Global-MMLU rows identical to MMMLU at the same position
P7_MIN_SMALL_OFFSET = 0.90       # misaligned rows whose offset (content position - own position) is -1, -2 or -3
SMALL_OFFSETS = ("-1", "-2", "-3")

# ----- hand-traced fixture -----
_OPT = {"A": "a", "B": "b", "C": "c", "D": "d"}
_CHOICES = ["a", "b", "c", "d"]

FIXTURE_EN_RECORDS = [
    {"subject": "s1", "question": "Speech 1955", "choices": _CHOICES, "answer": 0},
    {"subject": "s1", "question": "Poem 1904", "choices": _CHOICES, "answer": 2},
    {"subject": "s1", "question": "Text 1450", "choices": _CHOICES, "answer": 1},
    {"subject": "s1", "question": "Year 2000", "choices": _CHOICES, "answer": 3},
    {"subject": "s2", "question": "Sum 123", "choices": _CHOICES, "answer": 1},
    {"subject": "s2", "question": "No digits", "choices": _CHOICES, "answer": 0},
]


def _mm(question, answer, subject):
    rec = {"Question": question, "Answer": answer, "Subject": subject}
    rec.update(_OPT)
    return rec


# Positions 1-3 of s1 rotated: position 1 holds English 3, position 2 English 1, position 3 English 2; keys follow
# the content. Position 4 carries a malformed file-name subject.
FIXTURE_MM_RECORDS = [
    _mm("演讲 1955", "A", "s1"),
    _mm("2000 年", "D", "s1"),
    _mm("诗 1904", "C", "s1"),
    _mm("文本 1450", "B", "s1"),
    _mm("和 123", "B", "s2_test.csv_sw-KE.csv"),
    _mm("无", "A", "s2"),
]


def _gm(sid, question, answer):
    rec = {"sample_id": sid, "question": question, "answer": answer}
    rec.update({"option_a": "a", "option_b": "b", "option_c": "c", "option_d": "d"})
    return rec


# Global-MMLU: 0 identical; 1 identical after stripping a trailing space; 2 edited text, same digits and key;
# 3 different key; 4 an id MMMLU does not have.
FIXTURE_GM_RECORDS = [
    _gm("s1/test/0", "演讲 1955", "A"),
    _gm("s1/test/1", "2000 年 ", "D"),
    _gm("s1/test/2", "诗歌 1904", "C"),
    _gm("s1/test/3", "文本 1450", "C"),
    _gm("s9/test/0", "x", "A"),
]

FIXTURE_EN_IDS = ["s1/test/0", "s1/test/1", "s1/test/2", "s1/test/3", "s2/test/0", "s2/test/1"]
FIXTURE_EN_KEYS = [0, 2, 1, 3, 1, 0]
FIXTURE_EN_FPS = [("1955",), ("1904",), ("1450",), ("2000",), ("123",), ()]
FIXTURE_MM_KEYS = [0, 3, 2, 1, 1, 0]
FIXTURE_MM_TALLY = {"n": 6, "subject_agree": 6, "subject_malformed": 1}

_ZERO_LABELS = {"mis_label_wrong_for_content": 0, "mis_label_differs": 0, "mis_label_follows_id": 0,
                "mis_label_follows_content": 0, "mis_annot_differs": 0, "mis_annot_follows_id": 0,
                "mis_knowledge_differs": 0, "mis_knowledge_follows_id": 0}

FIXTURE_S1_REPORT = dict({
    "n": 4, "no_fingerprint": 0, "count_differs": 0, "mapped": 4, "aligned": 1, "misaligned": 3,
    "same_id_fp_both": 4, "same_id_fp_agree": 1,
    "key_differs_same_id": 3, "key_differs_misaligned": 3, "key_differs_aligned": 0, "key_differs_unmapped": 0,
    "mis_key_equals_content": 3, "mis_key_equals_id": 0,
    "label_wrong_detail": {}, "offsets": {"2": 1, "-1": 2},
}, **_ZERO_LABELS)

FIXTURE_TOTAL = dict({
    "n": 6, "no_fingerprint": 1, "count_differs": 0, "mapped": 5, "aligned": 2, "misaligned": 3,
    "same_id_fp_both": 5, "same_id_fp_agree": 2,
    "key_differs_same_id": 3, "key_differs_misaligned": 3, "key_differs_aligned": 0, "key_differs_unmapped": 0,
    "mis_key_equals_content": 3, "mis_key_equals_id": 0,
}, **_ZERO_LABELS)

FIXTURE_MISALIGNED = ["s1/test/1", "s1/test/2", "s1/test/3"]
FIXTURE_FLAGGED = ["s1"]
FIXTURE_FOCUS_MAPPING = {"s1/test/0": "s1/test/0", "s1/test/1": "s1/test/3", "s1/test/2": "s1/test/1",
                         "s1/test/3": "s1/test/2"}
FIXTURE_FLAG_MIN = 2
FIXTURE_FOCUS = "s1"

FIXTURE_INHERIT = {"n": 5, "not_in_mmmlu": 1, "identical": 2, "fp_key_equal": 3, "on_misaligned": 3,
                   "on_misaligned_identical": 1, "on_misaligned_fp_key_equal": 2}

# What job.py checks before reading any real data.
FIXTURE_TARGET = {
    "en_ids": FIXTURE_EN_IDS, "en_keys": FIXTURE_EN_KEYS, "en_fps": FIXTURE_EN_FPS,
    "mm_keys": FIXTURE_MM_KEYS, "mm_tally": FIXTURE_MM_TALLY,
    "total": FIXTURE_TOTAL, "cells": {"s1": FIXTURE_S1_REPORT}, "misaligned": FIXTURE_MISALIGNED,
    "flagged": FIXTURE_FLAGGED, "focus_mapping": FIXTURE_FOCUS_MAPPING, "inherit": FIXTURE_INHERIT,
}
