"""Hand-traced fixture and real-data configuration for the MMLU-Pro per-CATEGORY gold-answer-LENGTH census (audit 61).

Audit 60 mapped MMLU's answer-LENGTH shortcut by subject: pooled, a tie-aware "pick the longest option" heuristic
scores 0.2805 on MMLU `all` (chance 0.250, a +3.0-point lift from the gold averaging +1.68 characters longer than
the mean distractor), concentrated in a law/clinical/social cluster. Audit 59 then showed that MMLU-Pro's deliberate
10-option expansion ERASES MMLU's gold-POSITION / meta-option artifact (the gold position becomes consistent with
uniform; "all of the above" drops from 59.6% gold to 6.25%). This audit asks the matching question on the LENGTH
axis: does the same 10-way expansion also erase the pick-longest length shortcut, or does the authoring length bias
survive into MMLU-Pro?

It censuses gold-vs-distractor length per MMLU-Pro CATEGORY over the `default` test split, reports each category's
tie-aware pick-longest accuracy, chance baseline (variable, since MMLU-Pro options run 3-10 per question),
unique-longest rate and mean length gap, and summarises the cross-category distribution. As a hard STRUCTURAL gate
it requires the pooled parse to reproduce audit 59's option-count histogram and n_valid EXACTLY before trusting the
by-category split (same dataset, same split -> identical parse). Pre-registers four predictions, each a finding
either way, decided before any real number was seen.

The FIXTURE_ROWS and TARGET are reused VERBATIM from audits 52/60 (keys "cs5"/"mc4"; the census treats any
first-element key the same, so they equally exercise a per-category grouping and the variable-k chance baseline).
This checks the shared exact census core against a known answer before any real file is read.

Apache-2.0.
"""

from fractions import Fraction

# (key, labels, texts, answer_key) -- the generic census keys on the first element (here a synthetic category).
FIXTURE_ROWS = [
    # cs5: 5-option questions, chance 1/5
    ("cs5", ["A", "B", "C", "D", "E"], ["a", "bb", "ccc", "dddd", "eeeee"], "E"),  # gold 5 > {1,2,3,4} uniq long
    ("cs5", ["A", "B", "C", "D", "E"], ["xx", "xx", "xx", "xx", "x"], "E"),        # gold 1 < {2,2,2,2} uniq short

    # mc4: 4-option plus a 2-option row and two unusable rows
    ("mc4", ["0", "1", "2", "3"], ["qqqq", "r", "ss", "t"], "0"),                  # gold 4 > {1,2,1} uniq long
    ("mc4", ["0", "1", "2", "3"], ["aa", "bbbb", "cccc", "d"], "2"),               # gold 4 tied with 1; credit 1/2
    ("mc4", ["0", "1"], [" pp ", "qqqq"], "0"),                                    # gold strips to 2 < 4 uniq short
    ("mc4", ["0", "1", "2", "3"], ["a", "b", "c", "d"], "9"),                      # bad_key: "9" not a label
    ("mc4", ["0"], ["x"], "0"),                                                    # degenerate: single option
]


# Hand-traced TARGET: exactly the structure gold_length.run_census returns (dict equality is order-free).
TARGET = {
    "cs5": {
        "n_valid": 2,
        "n_bad_key": 0,
        "n_degenerate": 0,
        "option_count_hist": {5: 2},
        "chance_sum": Fraction(2, 5),              # 1/5 + 1/5
        "char": {
            "n_valid": 2,
            "unique_longest": 1,                   # row1
            "unique_shortest": 1,                  # row2
            "sum_gold": 6,                         # 5 + 1
            "sum_distractor": 18,                  # 10 + 8
            "n_distractor": 8,                     # 4 + 4
            "longest_credit": Fraction(1),         # 1 + 0
            "shortest_credit": Fraction(1),        # 0 + 1
        },
        "token": {
            "n_valid": 2,
            "unique_longest": 0,
            "unique_shortest": 0,
            "sum_gold": 2,                         # 1 + 1
            "sum_distractor": 8,                   # 4 + 4
            "n_distractor": 8,
            "longest_credit": Fraction(2, 5),      # 1/5 + 1/5
            "shortest_credit": Fraction(2, 5),
        },
    },
    "mc4": {
        "n_valid": 3,
        "n_bad_key": 1,
        "n_degenerate": 1,
        "option_count_hist": {4: 2, 2: 1},
        "chance_sum": Fraction(1),                 # 1/4 + 1/4 + 1/2
        "char": {
            "n_valid": 3,
            "unique_longest": 1,                   # row3
            "unique_shortest": 1,                  # row5
            "sum_gold": 10,                        # 4 + 4 + 2
            "sum_distractor": 15,                  # 4 + 7 + 4
            "n_distractor": 7,                     # 3 + 3 + 1
            "longest_credit": Fraction(3, 2),      # 1 + 1/2 + 0
            "shortest_credit": Fraction(1),        # 0 + 0 + 1
        },
        "token": {
            "n_valid": 3,
            "unique_longest": 0,
            "unique_shortest": 0,
            "sum_gold": 3,                         # 1 + 1 + 1
            "sum_distractor": 7,                   # 3 + 3 + 1
            "n_distractor": 7,
            "longest_credit": Fraction(1),         # 1/4 + 1/4 + 1/2
            "shortest_credit": Fraction(1),
        },
    },
}


# ----- Real-data configuration, read via the HuggingFace datasets-server parquet API -----
# MMLU-Pro `default` test: parquet columns include "category" (str), "options" (list[str]) and "answer_index"
# (int). Each row becomes (category, option-labels "0".."k-1", option-texts, gold-index-as-str). Same dataset and
# split as audit 59; k runs 3..10 with a modal 10.
MMLU_PRO = {
    "hf": "TIGER-Lab/MMLU-Pro",
    "config": "default",
    "splits": ["test"],
    "category_col": "category",
    "choices_col": "options",
    "answer_col": "answer_index",
}

# Pre-registered STRUCTURAL gate (P1): re-keying every MMLU-Pro row under one pooled key must reproduce audit 59's
# parse EXACTLY -- the same n_valid and the same option-count histogram -- before the by-category split is trusted.
# Copied from audit 59's results.json (pooled_gold_position): n_valid 12,032, modal 10-option, hist below.
EXPECTED_N_VALID = 12032
EXPECTED_MODAL_K = 10
EXPECTED_OPTION_HIST = {"3": 21, "4": 606, "5": 52, "6": 93, "7": 158, "8": 320, "9": 801, "10": 9981}

# MMLU reference point for the headline comparison (P2): MMLU `all` pooled char pick-longest accuracy and its lift
# over chance, copied from audit 52/60's results.json (pooled_mmlu_all.char.longest_accuracy, chance 0.25).
MMLU_POOLED_LONGEST_ACCURACY = 0.2804998528608063
MMLU_POOLED_CHANCE = 0.25
MMLU_POOLED_LIFT = MMLU_POOLED_LONGEST_ACCURACY - MMLU_POOLED_CHANCE  # +0.03050 (+3.05 points)
