"""Hand-traced fixtures and real-data configuration for the MMLU-Pro added-distractor length census (audit 62).

Audit 61 found that MMLU-Pro's 10-option expansion more than DOUBLED MMLU's pick-longest answer-length shortcut
(pooled lift +7.29 points vs MMLU's +3.05; biology 44.6% vs 11% chance). Audit 62 asks WHERE that comes from: it
joins every MMLU-Pro question inherited from MMLU back to MMLU, labels each distractor ORIGINAL (one of MMLU's
three) or ADDED (introduced by the expansion), and compares how often the gold is longer than each kind.

Two fixtures are checked for exact equality before any real file is read:
- FIXTURE_ROWS / TARGET: the shared length-census core, reused VERBATIM from audits 52/60/61;
- JOIN_MMLU_ROWS / JOIN_PRO_ROWS / JOIN_STATUS_TARGET / JOIN_TARGET: the new join + origin split, hand-traced
  row by row in the comments below.

Apache-2.0.
"""

from fractions import Fraction

# ----- Length-census core fixture (VERBATIM from audits 52/60/61) -----
# (key, labels, texts, answer_key) -- the generic census keys on the first element.
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

TARGET = {
    "cs5": {
        "n_valid": 2,
        "n_bad_key": 0,
        "n_degenerate": 0,
        "option_count_hist": {5: 2},
        "chance_sum": Fraction(2, 5),
        "char": {
            "n_valid": 2,
            "unique_longest": 1,
            "unique_shortest": 1,
            "sum_gold": 6,
            "sum_distractor": 18,
            "n_distractor": 8,
            "longest_credit": Fraction(1),
            "shortest_credit": Fraction(1),
        },
        "token": {
            "n_valid": 2,
            "unique_longest": 0,
            "unique_shortest": 0,
            "sum_gold": 2,
            "sum_distractor": 8,
            "n_distractor": 8,
            "longest_credit": Fraction(2, 5),
            "shortest_credit": Fraction(2, 5),
        },
    },
    "mc4": {
        "n_valid": 3,
        "n_bad_key": 1,
        "n_degenerate": 1,
        "option_count_hist": {4: 2, 2: 1},
        "chance_sum": Fraction(1),
        "char": {
            "n_valid": 3,
            "unique_longest": 1,
            "unique_shortest": 1,
            "sum_gold": 10,
            "sum_distractor": 15,
            "n_distractor": 7,
            "longest_credit": Fraction(3, 2),
            "shortest_credit": Fraction(1),
        },
        "token": {
            "n_valid": 3,
            "unique_longest": 0,
            "unique_shortest": 0,
            "sum_gold": 3,
            "sum_distractor": 7,
            "n_distractor": 7,
            "longest_credit": Fraction(1),
            "shortest_credit": Fraction(1),
        },
    },
}


# ----- Join + origin-split fixture (new in audit 62) -----
# MMLU rows: (subject, question, choices, answer_index)
JOIN_MMLU_ROWS = [
    ("s1", "What is X?", ["aa", "bbbb", "c", "dd"], 1),          # gold "bbbb"; distractors aa, c, dd
    ("s2", "Q two", ["p", "qq", "rrr", "ssss"], 0),              # gold "p"; distractors qq, rrr, ssss
    ("s3", "Dup?", ["x", "yy", "zzz", "w"], 0),                  # gold "x"; distractors w, yy, zzz
    ("s3", "Dup?", ["x", "y", "z", "v"], 0),                     # same text + gold, other distractors -> ambiguous
    ("s4", "  Spaced   question ", ["one", "two", "three", "four"], 2),  # normalises to "Spaced question"
    ("s5", "Bad?", ["a"], 5),                                    # invalid answer index: not indexed
]

# MMLU-Pro rows: (category, src, question, options, answer_index)
JOIN_PRO_ROWS = [
    # R1 matched. gold "bbbb"=4; original aa=2, c=1, dd=2 (all 3 kept, intact); added e=1, f=1.
    #    vs original 1+1+1=3; vs added 1+1=2. full pick-longest: 4 unique max -> 1, chance 1/6. orig4: 1.
    ("bio", "ori_mmlu-s1", "What is X?", ["aa", "bbbb", "c", "dd", "e", "f"], 1),
    # R2 matched. gold "p"=1; original qq=2, rrr=3 (ssss dropped, not intact); added zzzzzz=6.
    #    vs original 0+0=0; vs added 0.
    ("bio", "ori_mmlu-s2", "Q two", ["p", "qq", "zzzzzz", "rrr"], 0),
    # R3 ambiguous: "Dup?" with gold "x" has two different MMLU distractor sets.
    ("psy", "ori_mmlu-s3", "Dup?", ["x", "yy", "zzz", "w"], 0),
    # R4 matched. gold "three"=5; original "one "=3 (strips), two=3, four=4 (intact); added fiver=5.
    #    vs original 1+1+1=3; vs added tie=1/2. full pick-longest: max 5 shared by gold+fiver -> 1/2, chance 1/5.
    #    orig4: 5 > 3,3,4 -> 1.
    ("psy", "ori_mmlu-s4", "Spaced question", ["three", "one ", "two", "four", "fiver"], 0),
    # R5 no_gold: question found but gold text "BBBB" differs from MMLU's "bbbb" (case kept).
    ("psy", "ori_mmlu-s1", "What is X?", ["aa", "BBBB", "c", "dd"], 1),
    # R6 no_question: text not in MMLU.
    ("bio", "ori_mmlu-x", "Unknown?", ["a", "b"], 0),
    # R7 not ori_mmlu: skipped entirely (not counted in any status).
    ("bio", "stemez-Bio", "What is X?", ["aa", "bbbb"], 1),
    # R8 bad_key: answer index outside the option list.
    ("psy", "ori_mmlu-s1", "What is X?", ["aa", "bbbb", "c"], 7),
]

JOIN_STATUS_TARGET = {"matched": 3, "no_question": 1, "no_gold": 1, "ambiguous": 1, "bad_key": 1}

JOIN_TARGET = {
    "ALL": {  # R1 + R2 + R4
        "n_questions": 3,
        "retained_hist": {3: 2, 2: 1},
        "n_with_added": 3,
        "sum_gold": 10,                            # 4 + 1 + 5
        "n_original": 8,                           # 3 + 2 + 3
        "sum_original": 20,                        # (2+1+2) + (2+3) + (3+3+4)
        "gold_vs_original": Fraction(6),           # 3 + 0 + 3
        "n_added": 4,                              # 2 + 1 + 1
        "sum_added": 13,                           # (1+1) + 6 + 5
        "gold_vs_added": Fraction(5, 2),           # 2 + 0 + 1/2
        "n_intact": 2,                             # R1, R4
        "intact_full_longest": Fraction(3, 2),     # 1 + 1/2
        "intact_full_chance": Fraction(11, 30),    # 1/6 + 1/5
        "intact_orig_longest": Fraction(2),        # 1 + 1
    },
    "bio": {  # R1 + R2
        "n_questions": 2,
        "retained_hist": {3: 1, 2: 1},
        "n_with_added": 2,
        "sum_gold": 5,
        "n_original": 5,
        "sum_original": 10,
        "gold_vs_original": Fraction(3),
        "n_added": 3,
        "sum_added": 8,
        "gold_vs_added": Fraction(2),
        "n_intact": 1,
        "intact_full_longest": Fraction(1),
        "intact_full_chance": Fraction(1, 6),
        "intact_orig_longest": Fraction(1),
    },
    "psy": {  # R4
        "n_questions": 1,
        "retained_hist": {3: 1},
        "n_with_added": 1,
        "sum_gold": 5,
        "n_original": 3,
        "sum_original": 10,
        "gold_vs_original": Fraction(3),
        "n_added": 1,
        "sum_added": 5,
        "gold_vs_added": Fraction(1, 2),
        "n_intact": 1,
        "intact_full_longest": Fraction(1, 2),
        "intact_full_chance": Fraction(1, 5),
        "intact_orig_longest": Fraction(1),
    },
}


# ----- Real-data configuration (HuggingFace datasets-server parquet API) -----
MMLU_PRO = {
    "hf": "TIGER-Lab/MMLU-Pro",
    "config": "default",
    "splits": ["test"],
    "cols": ["question_id", "question", "options", "answer_index", "category", "src"],
}

# MMLU `all` without auxiliary_train (same three splits as audits 52/54/60).
MMLU = {
    "hf": "cais/mmlu",
    "config": "all",
    "splits": ["test", "validation", "dev"],
    "cols": ["subject", "question", "choices", "answer"],
}

# Structural gate: the pooled MMLU-Pro length census must reproduce audit 61 exactly, and the provenance split
# must reproduce audit 59's ori_mmlu / other counts. Copied from those audits' results.json.
EXPECTED_N_VALID = 12032
EXPECTED_POOLED_UNIQUE_LONGEST = 1655
EXPECTED_POOLED_LONGEST_ACCURACY = 0.18376805370862884
EXPECTED_PROVENANCE_COUNTS = {"ori_mmlu": 6810, "other": 5222}

# Categories with the largest pick-longest lift in audit 61 (P5 localisation).
FOCUS_CATEGORIES = ("biology", "psychology")
