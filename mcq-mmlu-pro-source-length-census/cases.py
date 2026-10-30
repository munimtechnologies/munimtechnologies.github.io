"""Hand-traced fixtures and real-data configuration for the MMLU-Pro source length census (audit 63).

Audit 62 found that MMLU-Pro's doubled pick-longest shortcut (audit 61) sits in its new-source questions
(STEM website, TheoremQA, SciBench), not in the questions inherited from MMLU, and derived by subtraction that
the new-source biology and psychology questions must score about 56% and 61%. Audit 63 measures that directly by
keying the length census by source family, by (category, provenance) and by (category, family).

Two fixtures are checked for exact equality before any real file is read:
- FIXTURE_ROWS / TARGET: the shared length-census core, reused VERBATIM from audits 52/60/61/62;
- KEY_ROWS / KEY_TARGET_*: the new source keys, hand-traced row by row in the comments below.

Apache-2.0.
"""

from fractions import Fraction

# ----- Length-census core fixture (VERBATIM from audits 52/60/61/62) -----
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


# ----- Source-key fixture (new in audit 63) -----
# MMLU-Pro-shaped rows. Digest = (n_valid, n_degenerate, chance_sum, char longest_credit).
KEY_ROWS = [
    # K1 ori_mmlu / biology: "aa"=2 > "b"=1 -> credit 1, chance 1/2.
    {"category": "biology", "src": "ori_mmlu-high_school_biology", "options": ["aa", "b"], "answer_index": 0},
    # K2 stemez / biology: "ccc"=3 > 1, 1 -> credit 1, chance 1/3.
    {"category": "biology", "src": "stemez-Biology", "options": ["ccc", "d", "e"], "answer_index": 0},
    # K3 theoremQA / physics: gold "22"=2 > "1"=1 -> credit 1, chance 1/2.
    {"category": "physics", "src": "theoremQA-Physics", "options": ["1", "22"], "answer_index": 1},
    # K4 scibench / physics: single option -> degenerate (not valid, no chance, no credit).
    {"category": "physics", "src": "scibench-thermo", "options": ["x"], "answer_index": 0},
    # K5 empty src / math: family "unknown", provenance "new"; "a"=1 ties "b"=1 -> credit 1/2, chance 1/2.
    {"category": "math", "src": "", "options": ["a", "b"], "answer_index": 0},
]

KEY_TARGET_FAMILY = {
    "ori_mmlu": (1, 0, Fraction(1, 2), Fraction(1)),
    "stemez": (1, 0, Fraction(1, 3), Fraction(1)),
    "theoremQA": (1, 0, Fraction(1, 2), Fraction(1)),
    "scibench": (0, 1, Fraction(0), Fraction(0)),
    "unknown": (1, 0, Fraction(1, 2), Fraction(1, 2)),
}

KEY_TARGET_PROV = {
    "ori_mmlu": (1, 0, Fraction(1, 2), Fraction(1)),                 # K1
    "new": (3, 1, Fraction(4, 3), Fraction(5, 2)),                   # K2+K3+K5 valid, K4 degenerate
}

KEY_TARGET_CATPROV = {
    "biology|ori_mmlu": (1, 0, Fraction(1, 2), Fraction(1)),         # K1
    "biology|new": (1, 0, Fraction(1, 3), Fraction(1)),              # K2
    "physics|new": (1, 1, Fraction(1, 2), Fraction(1)),              # K3 valid, K4 degenerate
    "math|new": (1, 0, Fraction(1, 2), Fraction(1, 2)),              # K5
}


# ----- Real-data configuration (HuggingFace datasets-server parquet API) -----
MMLU_PRO = {
    "hf": "TIGER-Lab/MMLU-Pro",
    "config": "default",
    "splits": ["test"],
    "cols": ["question_id", "question", "options", "answer_index", "category", "src"],
}

# Structural gate, copied from the results.json of audits 61 (pooled, per category) and 62 (by provenance).
EXPECTED = {
    "n_valid": 12032,
    "unique_longest": 1655,
    "longest_accuracy": 0.18376805370862884,
    "provenance": {
        "ori_mmlu": (6810, 0.13011671677971237),
        "new": (5222, 0.2537346574018347),
    },
    "category": {
        "biology": (717, 0.4460804498461402),
        "psychology": (798, 0.3299966185304531),
    },
}
