"""Configuration, pinned audit-70/71 numbers, thresholds and hand-traced fixtures for audit 72. Apache-2.0.
Authored by AI agents working in the name of MV2, Munim, Inc."""

import align as al

GMMLU_DATASET = "CohereLabs/Global-MMLU"
LITE_DATASET = "CohereLabs/Global-MMLU-Lite"
SPLIT = "test"
COLUMNS = ("sample_id", "subject", "question", "option_a", "option_b", "option_c", "option_d", "answer",
           "cultural_sensitivity_label", "is_annotated", "required_knowledge")
REFERENCE_LANGUAGE = "en"

EXPECTED_N_CONFIGS = 42
EXPECTED_N_ROWS = 14042

# Audits 70 and 71: answer letters differing from English at the same sample_id, per language, over all rows.
AUDIT70_KEY_MISMATCH = {"zh": 176, "ko": 116, "de": 5, "it": 3, "yo": 2, "ja": 1}

FOCUS = ("zh", "ko")
FOCUS_SUBJECT = "high_school_world_history"

# Pre-registered thresholds (written before any audit-72 number was seen).
P2_MIN_MAPPED_SHARE = 0.60     # zh and ko high_school_world_history rows matched to an English row by fingerprint
P3_MIN_N = 20                  # below this many matched zh+ko key differences P3 is vacuous
P3_MIN_MISALIGNED_SHARE = 0.90 # matched key differences that are misaligned rows
P4_MIN_N = 20                  # below this many misaligned zh+ko rows P4 is vacuous
P4_MIN_CONTENT_KEY = 0.95      # misaligned rows whose key equals the key of the English question they hold
P5_MIN_N = 3                   # below this many misaligned rows where the two English labels differ P5 is vacuous
P5_MIN_FOLLOWS_ID = 0.95       # of those, the translation carries the label of its sample_id's English question
FLAG_MIN_MISALIGNED = 5        # a (language, subject) cell with at least this many misaligned rows is flagged
FP_MIN_BOTH = 10               # cells with fewer same-id fingerprint pairs are left out of the agreement minimum
P7_MIN_IDENTICAL = 0.99        # Lite zh / ko rows identical (options and key) to the full-set row with the same id

OPTIONS = ("a", "b", "c", "d")


def _r(sid, question, key, label="-", annotated=False, knowledge=""):
    return {"sample_id": sid, "fp": al.fingerprint(question, OPTIONS), "key": key, "label": label,
            "annotated": annotated, "knowledge": knowledge}


# One subject. English E0..E6; E0 and E3 share a passage (same fingerprint), E4 has no digits.
FIXTURE_EN = [
    _r("s/test/0", "Speech, 1955", 0),
    _r("s/test/1", "Text, 1450", 1),
    _r("s/test/2", "Poem, 1904", 3),
    _r("s/test/3", "Speech, 1955. Again", 2, "CS", True, "k3"),
    _r("s/test/4", "No digits here", 0),
    _r("s/test/5", "Text 1066 and 1450", 1, "CA", True, "k5"),
    _r("s/test/6", "Year 2000", 2),
]

# The translation: rows 1 and 2 swapped, row 4 holds English row 5's question, row 5 holds row 4's (no digits, so
# unmatched), row 6's translation adds a number (its fingerprint has no English partner). Annotation fields follow
# the sample_id, keys follow the content.
FIXTURE_XX = [
    _r("s/test/0", "演讲，1955", 0),
    _r("s/test/1", "诗，1904", 3),
    _r("s/test/2", "文本，1450", 1),
    _r("s/test/3", "演讲，1955。", 2, "CS", True, "k3"),
    _r("s/test/4", "文本 1066 和 1450", 1),
    _r("s/test/5", "没有数字", 0, "CA", True, "k5"),
    _r("s/test/6", "2000 年和 2001 年", 2),
]

FIXTURE_MAPPING = {"s/test/0": "s/test/0", "s/test/1": "s/test/2", "s/test/2": "s/test/1", "s/test/3": "s/test/3",
                   "s/test/4": "s/test/5"}

FIXTURE_REPORT = {
    "n": 7, "no_fingerprint": 1, "count_differs": 1, "mapped": 5, "aligned": 2, "misaligned": 3,
    "same_id_fp_both": 5, "same_id_fp_agree": 2,
    "key_differs_same_id": 4, "key_differs_misaligned": 3, "key_differs_aligned": 0, "key_differs_unmapped": 1,
    "mis_key_equals_content": 3, "mis_key_equals_id": 0,
    "mis_label_wrong_for_content": 1, "mis_label_differs": 1, "mis_label_follows_id": 1,
    "mis_label_follows_content": 0, "mis_annot_differs": 1, "mis_annot_follows_id": 1,
    "mis_knowledge_differs": 1, "mis_knowledge_follows_id": 1,
    "label_wrong_detail": {"-|CA": 1}, "offsets": {"1": 2, "-1": 1},
}

FIXTURE_MAP_B = {"s/test/0": "s/test/0", "s/test/1": "s/test/2", "s/test/2": "s/test/2", "s/test/4": "s/test/4",
                 "s/test/9": "s/test/1"}
FIXTURE_AGREEMENT = {"both_mapped": 4, "same_content": 2, "both_misaligned": 1, "both_misaligned_same_content": 1}

FIXTURE_LITE_FULL = {
    "s/test/1": {"options": ("p", "q", "r", "s"), "key": 3, "label": "-", "fp": ("1904",)},
    "s/test/4": {"options": ("a", "b", "c", "d"), "key": 1, "label": "CS", "fp": ()},
}
FIXTURE_LITE_EN = {"s/test/1": {"key": 1, "fp": ("1450",)}, "s/test/4": {"key": 0, "fp": ()}}
FIXTURE_LITE_MISALIGNED = {"s/test/1", "s/test/4"}
FIXTURE_LITE_ROWS = [
    {"sample_id": "s/test/1", "options": ("p", "q", "r", "s"), "key": 3, "label": "-", "fp": ("1904",)},
    {"sample_id": "s/test/4", "options": ("a", "b", "c", "x"), "key": 1, "label": "CA", "fp": ()},
    {"sample_id": "s/test/9", "options": ("a", "b", "c", "d"), "key": 0, "label": "-", "fp": ()},
]
FIXTURE_LITE = {"n": 3, "not_in_full": 1, "identical_to_full": 1, "key_equal_full": 2, "label_equal_full": 1,
                "on_misaligned_ids": 2, "on_misaligned_identical_to_full": 1,
                "on_misaligned_key_equals_en_same_id": 0, "on_misaligned_fp_equals_en_same_id": 1}

# What job.py checks before reading any real data.
FIXTURE_TARGET = {"report": FIXTURE_REPORT, "mapping": FIXTURE_MAPPING, "agreement": FIXTURE_AGREEMENT,
                  "lite": FIXTURE_LITE}
