"""Hand-traced fixture and real-data configuration for the MMLU per-SUBJECT gold-answer-LENGTH census (audit 60).

Audit 52 measured MMLU's whole-'all' answer-length signal: across 15,858 MMLU questions (test+validation+dev,
chance 0.250) the gold option was the UNIQUE longest 23.5% of the time and a tie-aware "pick the longest"
heuristic scored 0.2805 -- a +3-point lift over chance, with the mean gold option +1.68 characters longer than
the mean distractor. Audit 52 reported this only POOLED. This audit asks whether that length cue is a pervasive
authoring tendency spread across MMLU's ~57 subjects, or an aggregate of a few subjects: it censuses the
gold-vs-distractor length per SUBJECT over MMLU `all`, reports each subject's pick-longest accuracy, chance
baseline, length gap, and summarises the cross-subject distribution.

The FIXTURE_ROWS and TARGET are reused VERBATIM from audit 52 (they key on synthetic names "cs5"/"mc4"; the
census treats any first-element key the same, so they equally exercise a per-subject grouping). This checks the
shared exact census core against a known answer before any real file is read. It exercises: a 5-option question
(chance 1/5); a gold tied for longest (credit split 1/2); a unique-shortest gold; a 2-option question with
leading/trailing whitespace to strip; a bad_key row; a single-option degenerate row; and single-token options
that make the token view deliberately uninformative -- a sanity contrast to the char view.

Apache-2.0.
"""

from fractions import Fraction

# (key, labels, texts, answer_key) -- the generic census keys on the first element (here a synthetic subject).
FIXTURE_ROWS = [
    # cs5: 5-option questions (CommonsenseQA shape), chance 1/5
    ("cs5", ["A", "B", "C", "D", "E"], ["a", "bb", "ccc", "dddd", "eeeee"], "E"),  # gold 5 > {1,2,3,4} uniq long
    ("cs5", ["A", "B", "C", "D", "E"], ["xx", "xx", "xx", "xx", "x"], "E"),        # gold 1 < {2,2,2,2} uniq short

    # mc4: 4-option (MMLU / HellaSwag shape) plus a 2-option row and two unusable rows
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
# MMLU `all`: parquet columns include "subject" (str), "choices" (list[str]) and "answer" (int index). Each row
# becomes (subject, option-labels "0".."k-1", option-texts, gold-index-as-str). auxiliary_train is excluded as a
# mix of other datasets; the test+validation+dev splits are MMLU-authored. Same reader and splits as audit 54.
MMLU = {
    "hf": "cais/mmlu",
    "config": "all",
    "splits": ["test", "validation", "dev"],
    "subject_col": "subject",
    "choices_col": "choices",
    "answer_col": "answer",
}

# Canonical split sizes (sanity gate, not a hard prediction); reproduce audit 52/53's MMLU-all totals.
EXPECTED_SPLIT_COUNTS = {"test": 14042, "validation": 1531, "dev": 285}
EXPECTED_TOTAL_VALID = 15858  # audit 52/53's MMLU n_valid (all 4-option, 0 bad_key, 0 degenerate)

# Pre-registered POOLED reproduction gate: re-keying every MMLU row under one key must reproduce audit 52's
# pooled MMLU numbers EXACTLY (same data, same core). These are copied from audit 52's results.json (mmlu entry).
# If any of these fail to match, the audit aborts before trusting the by-subject split -- a hard validity check.
EXPECTED_POOLED_MMLU = {
    "n_valid": 15858,
    "char_unique_longest_count": 3727,
    "char_unique_shortest_count": 2871,
    "char_longest_accuracy": 0.2804998528608063,
    "char_shortest_accuracy": 0.22646823895405052,
    "char_mean_gold_len": 43.14692899482911,
    "char_mean_distractor_len": 41.47181233446841,
    "token_longest_accuracy": 0.2806417370832808,
}
