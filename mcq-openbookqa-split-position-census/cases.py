"""Hand-traced fixture and real-data configuration for the OpenBookQA per-SPLIT gold-position census (audit 55).

Audit 53 found OpenBookQA's gold position (pooled over all of `main`) is skewed toward the FIRST option
(position 0 / "A", 27.6%; rejects uniformity at alpha=0.001). That pooled number mixes train, validation and
test. But people report OpenBookQA *test* accuracy (500 questions), so this audit asks: is the pos-0/A skew a
property of the reported TEST split, or a train-only construction artifact that washes out of the small
evaluation splits? It censuses the 0-based gold position per SPLIT (train / validation / test), tests each
split against uniform with a chi-square goodness-of-fit, and reproduces audit 53's pooled OpenBookQA numbers as
a cross-check.

The synthetic fixture is reused verbatim from audits 53/54 (two synthetic keys, hand-traced to an exact TARGET)
so the shared census core is checked against a known answer before any real file is touched. It exercises:
4-option questions with the gold at positions 0/2/3, numeric labels, a second option-count bucket, a bad answer
key, a duplicate-label row and a single-option row.

Apache-2.0.
"""

from fractions import Fraction  # noqa: F401 - imported for parity with the census module's exactness contract

# (key, labels, texts, answer_key) -- the generic census keys on the first element (here a synthetic split).
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
# OpenBookQA `main`: parquet columns include "question_stem" (str), "choices" (struct of text:list[str] +
# label:list[str]) and "answerKey" (str letter, e.g. "A"). Each row becomes (split, option-labels,
# option-texts, gold-letter). labels.index(answerKey) is the 0-based gold position.
OBQA = {
    "hf": "allenai/openbookqa",
    "config": "main",
    "splits": ["train", "validation", "test"],
    "choices_col": "choices",
    "answer_col": "answerKey",
}

# Canonical split sizes (sanity gate, not a hard prediction); the three sum to audit 53's OpenBookQA main total.
EXPECTED_SPLIT_COUNTS = {"train": 4957, "validation": 500, "test": 500}
EXPECTED_TOTAL_VALID = 5957  # audit 53's OpenBookQA `main` n_valid (all 4-option, 0 bad_key, 0 degenerate)
