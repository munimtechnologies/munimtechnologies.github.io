"""Hand-traced fixture and real-data configuration for the MCQ answer-length GENERALIZATION census (audit 52).

Audit 51 censused the gold-answer-length shortcut in OpenBookQA, ARC-Easy and ARC-Challenge and found it
strong in crowd-authored OpenBookQA but absent in exam-sourced ARC. Audit 52 tests whether that crowd-vs-exam
split generalizes, on a fresh, disjoint set: two crowd-authored benchmarks (CommonsenseQA, HellaSwag) and one
exam/textbook-sourced benchmark (MMLU `all`).

The fixture is two synthetic benchmarks worked out by hand into a TARGET so the length accounting is checked
against a known answer before any real file is touched. It deliberately exercises: a 5-option question (the
new CommonsenseQA shape, chance 1/5); a gold tied for longest (credit split 1/2); a unique-shortest gold; a
2-option question with leading/trailing whitespace to strip; a question whose answerKey is absent from the
labels (bad_key); and a single-option question (degenerate). Every option is a single whitespace token, so the
token view is deliberately uninformative (gold never uniquely longest/shortest) -- a sanity contrast to char.

Apache-2.0.
"""

from fractions import Fraction

# (benchmark, labels, texts, answer_key)
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


# Hand-traced TARGET: exactly the structure gold_length.run_census returns.
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
# Each spec names the HF dataset, the parquet config, the GOLD-BEARING splits to read (test/aux splits with no
# usable gold label are excluded), the schema adapter, and the authoring group (crowd vs exam).
#   choices_key    : parquet "choices" = {label:[...], text:[...]} (dict-of-arrays) + "answerKey" letter.
#   endings_label  : parquet "endings" = list[str] (n=4) + "label" = str index.
#   choices_answer : parquet "choices" = list[str] + "answer" = int index.
SPECS = [
    {"benchmark": "commonsenseqa", "hf": "tau/commonsense_qa", "config": "default",
     "splits": ["train", "validation"], "schema": "choices_key", "group": "crowd"},
    {"benchmark": "hellaswag", "hf": "Rowan/hellaswag", "config": "default",
     "splits": ["train", "validation"], "schema": "endings_label", "group": "crowd"},
    {"benchmark": "mmlu", "hf": "cais/mmlu", "config": "all",
     "splits": ["test", "validation", "dev"], "schema": "choices_answer", "group": "exam"},
]

# Canonical split sizes (sanity gate, not a hard prediction). CommonsenseQA test (1,140) has no gold and is
# excluded; MMLU auxiliary_train is a mix of other datasets, not MMLU-authored, and is excluded.
EXPECTED_SPLIT_COUNTS = {
    "commonsenseqa": {"train": 9741, "validation": 1221},
    "hellaswag": {"train": 39905, "validation": 10042},
    "mmlu": {"test": 14042, "validation": 1531, "dev": 285},
}

# Authoring groups for the grouped prediction (audit 51's crowd-vs-exam hypothesis).
CROWD_BENCHMARKS = ["commonsenseqa", "hellaswag"]
EXAM_BENCHMARKS = ["mmlu"]
