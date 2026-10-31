"""Pinned inputs for audit 70: the datasets, the structural expectations, and a hand-traced fixture.

Option lengths in the fixture are written next to each row; every expected value below was traced by hand before
any real data was read. Apache-2.0.
"""

from fractions import Fraction as F

GMMLU_DATASET = "CohereLabs/Global-MMLU"
GMMLU_SPLIT = "test"
GMMLU_COLUMNS = ("sample_id", "subject", "subject_category", "option_a", "option_b", "option_c", "option_d",
                 "answer", "cultural_sensitivity_label")
REFERENCE_LANGUAGE = "en"
MMLU_DATASET = "cais/mmlu"
MMLU_CONFIG = "all"
MMLU_SPLITS = ("test", "validation", "dev")
TOOL_URL = "https://raw.githubusercontent.com/munimtechnologies/mcq-length-floor/v0.1.0/mcq_length_floor.py"

# Structural expectations from the Global-MMLU dataset card and the datasets-server size endpoint (2026-10-30):
# 42 language configs, 14,042 test rows each; 2,850 annotated questions per language, 792 CS and 2,058 CA.
EXPECTED_N_CONFIGS = 42
EXPECTED_N_ROWS = 14042
EXPECTED_CS = 792
EXPECTED_CA = 2058

# Audit 52 / 60: MMLU `all` (test + validation + dev, 15,858 questions) pick-longest 0.2805 vs 0.25 chance.
MMLU_REFERENCE = {"n": 15858, "pick_longest_4dp": 0.2805, "chance": 0.25, "source": "eval-reliability-audits 52, 60"}

P3_MIN_JOIN_SHARE = 0.99           # share of English rows identical to MMLU test in options and key
P6_RATIO_RANGE = (0.80, 1.25)      # every language keeps this share of the English lift
Z_CRIT_0001 = 3.29
P9_MIN_SAME_SIGN = 38              # of 41 non-English languages, CS - CA has the English sign

O4 = ["a", "bb", "ccc", "dddd"]    # lengths 1, 2, 3, 4   unique longest 3
R4 = ["dddd", "ccc", "bb", "a"]    # lengths 4, 3, 2, 1   unique longest 0
T4 = ["pp", "qq", "r", "s"]        # lengths 2, 2, 1, 1   longest tied


def _g(sid, subject, category, options, answer, label):
    rec = {"sample_id": sid, "subject": subject, "subject_category": category, "answer": answer,
           "cultural_sensitivity_label": label}
    rec.update(zip(("option_a", "option_b", "option_c", "option_d"), options))
    return rec


FIXTURE_EN = [
    _g("s1/test/0", "s1", "STEM", O4, "D", "CS"),                     # E1  cl 1    cs 0
    _g("s1/test/1", "s1", "STEM", O4, "A", "CA"),                     # E2  cl 0    cs 1
    _g("s1/test/2", "s1", "STEM", T4, "b", " CA "),                   # E3  cl 1/2  cs 0
    _g("s2/test/0", "s2", "Humanities", R4, "A", "cs"),               # E4  cl 1    cs 0
    _g("s2/test/1", "s2", "Humanities", O4, "B", "-"),                # E5  cl 0    cs 0   unlabelled
    _g("s2/test/2", "s2", "Humanities", ["a", "", "c", "d"], "C", "-"),  # E6  invalid (blank option)
    _g("s2/test/3", "s2", "Humanities", R4, "D", "CA"),               # E7  cl 0    cs 1
]

FIXTURE_XX = [
    _g("s1/test/0", "s1", "STEM", O4, "D", "CS"),                     # X1  cl 1; same key, same unique longest
    _g("s1/test/1", "s1", "STEM", R4, "A", "CA"),                     # X2  cl 1; unique longest moved 3 -> 0
    _g("s1/test/2", "s1", "STEM", T4, "C", "CA"),                     # X3  cs 1/2; key C vs English B
    _g("s2/test/0", "s2", "Humanities", R4, "A", "CA"),               # X4  cl 1; label CA vs English CS
    _g("s9/test/0", "s9", "Other", O4, "A", "-"),                     # X5  cs 1; not in English
]

FIXTURE_MMLU = [
    {"subject": "s1", "options": O4, "key": 3},
    {"subject": "s1", "options": O4, "key": 0},
    {"subject": "s1", "options": T4, "key": 1},
    {"subject": "s2", "options": R4, "key": 0},
    {"subject": "s2", "options": O4, "key": 2},                     # E5 key B vs MMLU C
    {"subject": "s2", "options": ["a", "b", "c", "d"], "key": 2},   # E6 options differ, key and key text agree
    {"subject": "s2", "options": O4, "key": 0},                     # E7 reordered: same set, same key text 'a'
    {"subject": "s3", "options": O4, "key": 0},                     # unjoined
]

FIXTURE_TARGET = {
    "en_n_rows": 7,
    "en_n_invalid": 1,
    "en_labels": {"CS": 2, "CA": 3, "unlabelled": 2},
    "en_ALL": (6, F(5, 12), F(1, 3), F(1, 4)),
    "en_label=CS": (2, F(1), F(0), F(1, 4)),
    "en_label=CA": (3, F(1, 6), F(2, 3), F(1, 4)),
    "en_label=unlabelled": (1, F(0), F(0), F(1, 4)),
    "en_cat=STEM": (3, F(1, 2), F(1, 3), F(1, 4)),
    "en_cat=Humanities": (3, F(1, 3), F(1, 3), F(1, 4)),
    "en_label=CA|cat=STEM": (2, F(1, 4), F(1, 2), F(1, 4)),
    "en_diff_exact": F(5, 6),
    "en_stratified_exact": F(6, 7),
    "en_stratified_n_used": 2,
    "xx_compare": {"n_rows": 5, "missing_in_reference": 1, "key_mismatch": 1, "label_mismatch": 1,
                   "ref_unique_longest": 3, "same_unique_longest": 2, "reference_ids_absent": 3},
    "xx_ALL": (5, F(3, 5), F(3, 10), F(1, 4)),
    "xx_diff_exact": F(1, 2),
    "mmlu_join": {"n_rows": 7, "joined": 7, "not_found": 0, "options_equal": 5, "same_option_set": 6,
                  "key_equal": 5, "key_text_equal": 6, "all_equal": 4, "mmlu_unjoined": 1},
}
