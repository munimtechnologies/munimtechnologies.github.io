"""Hand-traced fixture and real-data configuration for the MCQ gold-answer-POSITION census (audit 53).

Audit 51 found OpenBookQA's gold is reliably the LONGEST option (a length shortcut) while exam-sourced ARC is
not. This audit asks a sibling question on the construction side: where in the released option list does the
gold sit? It censuses the 0-based gold POSITION per benchmark over OpenBookQA, ARC-Easy, ARC-Challenge,
CommonsenseQA and MMLU, tests each against a uniform distribution with a chi-square goodness-of-fit, and
reports the accuracy of a constant "always pick position p" heuristic versus the random-choice baseline.

The fixture is two synthetic benchmarks worked out by hand into a TARGET so the position accounting is checked
against a known answer before any real file is touched. It deliberately exercises: 4-option questions with the
gold at positions 0, 2 and 3; a numeric-label question (gold position still read by index); a mixed 3-option
question (a second option-count bucket); a question whose answerKey is absent (bad_key); a duplicate-label
question (degenerate); and a single-option question (degenerate).

Apache-2.0.
"""

from fractions import Fraction  # noqa: F401 - imported for parity with the census module's exactness contract

# (benchmark, labels, texts, answer_key)
FIXTURE_ROWS = [
    # exam4: mostly 4-option, one 3-option, one bad_key
    ("exam4", ["A", "B", "C", "D"], ["w", "x", "y", "z"], "A"),   # k=4, gold pos 0
    ("exam4", ["A", "B", "C", "D"], ["w", "x", "y", "z"], "D"),   # k=4, gold pos 3
    ("exam4", ["A", "B", "C", "D"], ["w", "x", "y", "z"], "A"),   # k=4, gold pos 0
    ("exam4", ["0", "1", "2", "3"], ["w", "x", "y", "z"], "2"),   # k=4, numeric labels, gold pos 2
    ("exam4", ["A", "B", "C", "D"], ["w", "x", "y", "z"], "Z"),   # bad_key: "Z" not a label
    ("exam4", ["A", "B", "C"], ["w", "x", "y"], "B"),             # k=3, gold pos 1 (second bucket)

    # crowd5: 5-option plus two unusable rows
    ("crowd5", ["A", "B", "C", "D", "E"], ["a", "b", "c", "d", "e"], "E"),   # k=5, gold pos 4
    ("crowd5", ["A", "B", "C", "D", "E"], ["a", "b", "c", "d", "e"], "E"),   # k=5, gold pos 4
    ("crowd5", ["A", "A", "C", "D", "E"], ["a", "b", "c", "d", "e"], "C"),   # degenerate: duplicate label "A"
    ("crowd5", ["A"], ["x"], "A"),                                          # degenerate: single option
]


# Hand-traced TARGET: exactly the structure position_census.run_census returns (dict equality is order-free).
TARGET = {
    "exam4": {
        "n_valid": 5,
        "n_bad_key": 1,
        "n_degenerate": 0,
        "by_option_count": {
            4: {"n": 4, "pos_counts": {0: 2, 3: 1, 2: 1}},   # rows 1,3 -> pos0; row2 -> pos3; row4 -> pos2
            3: {"n": 1, "pos_counts": {1: 1}},               # row6 -> pos1
        },
    },
    "crowd5": {
        "n_valid": 2,
        "n_bad_key": 0,
        "n_degenerate": 2,
        "by_option_count": {
            5: {"n": 2, "pos_counts": {4: 2}},               # rows 7,8 -> pos4
        },
    },
}


# ----- Real-data configuration, read via the HuggingFace datasets-server parquet API -----
# Each spec names the HF dataset, parquet config, the GOLD-BEARING splits, the schema adapter, and the
# authoring group (crowd-authored vs exam/textbook-sourced).
#   choices_key    : parquet "choices" = {label:[...], text:[...]} (dict-of-arrays) + "answerKey" letter/digit.
#   choices_answer : parquet "choices" = list[str] + "answer" = int index.
SPECS = [
    {"benchmark": "openbookqa", "hf": "allenai/openbookqa", "config": "main",
     "splits": ["train", "validation", "test"], "schema": "choices_key", "group": "crowd"},
    {"benchmark": "arc_easy", "hf": "allenai/ai2_arc", "config": "ARC-Easy",
     "splits": ["train", "validation", "test"], "schema": "choices_key", "group": "exam"},
    {"benchmark": "arc_challenge", "hf": "allenai/ai2_arc", "config": "ARC-Challenge",
     "splits": ["train", "validation", "test"], "schema": "choices_key", "group": "exam"},
    {"benchmark": "commonsenseqa", "hf": "tau/commonsense_qa", "config": "default",
     "splits": ["train", "validation"], "schema": "choices_key", "group": "crowd"},
    {"benchmark": "mmlu", "hf": "cais/mmlu", "config": "all",
     "splits": ["test", "validation", "dev"], "schema": "choices_answer", "group": "exam"},
]

# Canonical split sizes (sanity gate, not a hard prediction). CommonsenseQA test (1,140) has no gold and is
# excluded; MMLU auxiliary_train is a mix of other datasets, not MMLU-authored, and is excluded.
EXPECTED_SPLIT_COUNTS = {
    "openbookqa": {"train": 4957, "validation": 500, "test": 500},
    "arc_easy": {"train": 2251, "validation": 570, "test": 2376},
    "arc_challenge": {"train": 1119, "validation": 299, "test": 1172},
    "commonsenseqa": {"train": 9741, "validation": 1221},
    "mmlu": {"test": 14042, "validation": 1531, "dev": 285},
}

# Authoring groups. OpenBookQA and CommonsenseQA were crowd-authored; ARC and MMLU come from real exams /
# textbooks. The headline contrast is OpenBookQA (crowd, known length shortcut) vs MMLU (exam).
CROWD_BENCHMARKS = ["openbookqa", "commonsenseqa"]
EXAM_BENCHMARKS = ["arc_easy", "arc_challenge", "mmlu"]
