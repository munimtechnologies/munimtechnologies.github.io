"""Hand-traced fixture for the MCQ gold-answer-length census.

Two synthetic benchmarks ('alpha', 'beta') of a few questions each, worked out by hand into a TARGET so the
length accounting (per-question longest/shortest, tie-aware credit, char vs token, the random-choice baseline,
and the valid/bad_key/degenerate split) is checked against a known answer before it touches real benchmark
files. The fixture deliberately exercises: a gold that is the unique longest option; a gold tied for longest
(credit split); a gold that is the unique shortest; a 3-option question; digit answer labels ("1".."4") with
leading/trailing whitespace on the gold text (to test stripping); a question whose answerKey is absent from
the labels (bad_key); and a single-option question (degenerate). Every option here is a single token, so the
token view is deliberately uninformative (gold never uniquely longest/shortest) -- a sanity contrast to char.

Apache-2.0.
"""

from fractions import Fraction

# (benchmark, labels, texts, answer_key)
FIXTURE_ROWS = [
    # alpha: gold unique-longest, gold tied-longest, gold unique-shortest, digit labels + whitespace strip
    ("alpha", ["A", "B", "C", "D"], ["aa", "bbbb", "c", "dd"], "B"),        # gold 4 > {2,1,2}, unique longest
    ("alpha", ["A", "B", "C", "D"], ["xxxx", "yy", "zzzz", "w"], "A"),      # gold 4 tied with C(4); credit 1/2
    ("alpha", ["A", "B", "C"], ["m", "nnn", "oo"], "A"),                    # gold 1 < {3,2}, unique shortest
    ("alpha", ["1", "2", "3", "4"], [" ppp ", "q", "rr", "s"], "1"),        # gold strips to 3 > {1,2,1}

    # beta: a gold shorter than its distractors on average (no length bias), plus two unusable rows
    ("beta", ["A", "B", "C", "D"], ["aaaa", "bb", "cc", "dd"], "A"),        # gold 4, unique longest
    ("beta", ["A", "B", "C", "D"], ["ee", "ffff", "gggg", "hhhh"], "A"),    # gold 2 < {4,4,4}, unique shortest
    ("beta", ["A", "B", "C"], ["ii", "jj", "kk"], "B"),                     # all 2; gold neither uniq long/short
    ("beta", ["A", "B", "C", "D"], ["p", "q", "r", "s"], "Z"),             # bad_key: "Z" not a label
    ("beta", ["A"], ["only"], "A"),                                         # degenerate: single option
]


# Hand-traced TARGET: exactly the structure gold_length.run_census returns.
TARGET = {
    "alpha": {
        "n_valid": 4,
        "n_bad_key": 0,
        "n_degenerate": 0,
        "option_count_hist": {4: 3, 3: 1},
        "chance_sum": Fraction(13, 12),            # 1/4 + 1/4 + 1/3 + 1/4
        "char": {
            "n_valid": 4,
            "unique_longest": 2,                   # Q1, Q4
            "unique_shortest": 1,                  # Q3
            "sum_gold": 12,                        # 4 + 4 + 1 + 3
            "sum_distractor": 21,                  # 5 + 7 + 5 + 4
            "n_distractor": 11,                    # 3 + 3 + 2 + 3
            "longest_credit": Fraction(5, 2),      # 1 + 1/2 + 0 + 1
            "shortest_credit": Fraction(1),        # 0 + 0 + 1 + 0
        },
        "token": {
            "n_valid": 4,
            "unique_longest": 0,
            "unique_shortest": 0,
            "sum_gold": 4,
            "sum_distractor": 11,
            "n_distractor": 11,
            "longest_credit": Fraction(13, 12),    # 1/4 + 1/4 + 1/3 + 1/4
            "shortest_credit": Fraction(13, 12),
        },
    },
    "beta": {
        "n_valid": 3,
        "n_bad_key": 1,
        "n_degenerate": 1,
        "option_count_hist": {4: 2, 3: 1},
        "chance_sum": Fraction(5, 6),              # 1/4 + 1/4 + 1/3
        "char": {
            "n_valid": 3,
            "unique_longest": 1,                   # Q1
            "unique_shortest": 1,                  # Q2
            "sum_gold": 8,                         # 4 + 2 + 2
            "sum_distractor": 22,                  # 6 + 12 + 4
            "n_distractor": 8,                     # 3 + 3 + 2
            "longest_credit": Fraction(4, 3),      # 1 + 0 + 1/3
            "shortest_credit": Fraction(4, 3),     # 0 + 1 + 1/3
        },
        "token": {
            "n_valid": 3,
            "unique_longest": 0,
            "unique_shortest": 0,
            "sum_gold": 3,
            "sum_distractor": 8,
            "n_distractor": 8,
            "longest_credit": Fraction(5, 6),      # 1/4 + 1/4 + 1/3
            "shortest_credit": Fraction(5, 6),
        },
    },
}


# ----- Real-data configuration and expected split sizes (sanity check, not a hard prediction) -----
# allenai/* auto-converted parquet, read via the datasets-server parquet API. OBQA uses the canonical "main"
# config (the leaderboard split), not "additional".
SPECS = [
    ("allenai/openbookqa", "main", "openbookqa"),
    ("allenai/ai2_arc", "ARC-Easy", "arc-easy"),
    ("allenai/ai2_arc", "ARC-Challenge", "arc-challenge"),
]

EXPECTED_SPLIT_COUNTS = {
    "openbookqa": {"train": 4957, "validation": 500, "test": 500},
    "arc-easy": {"train": 2251, "validation": 570, "test": 2376},
    "arc-challenge": {"train": 1119, "validation": 299, "test": 1172},
}
