"""Hand-traced fixture and real-data configuration for the MMLU per-SUBJECT gold-position census (audit 54).

Audit 53 found MMLU's whole-'all' gold position is skewed toward the LAST option (position 3, 26.7%; the
distribution rises monotonically 23.1 -> 24.7 -> 25.5 -> 26.7% and rejects uniformity at alpha=0.001). This
audit asks whether that pooled "answer tends to be last" tilt is a pervasive authoring convention spread across
MMLU's ~57 subjects, or an aggregate of a few strongly skewed subjects. It censuses the 0-based gold position
per SUBJECT over MMLU `all` (test+validation+dev), tests each subject against uniform with a chi-square
goodness-of-fit, and summarises the cross-subject distribution of tilts.

The fixture is reused verbatim from audit 53 (two synthetic keys, hand-traced to an exact TARGET) so the shared
census core is checked against a known answer before any real file is touched. It exercises: 4-option questions
with the gold at positions 0/2/3, numeric labels, a second option-count bucket, a bad answer key, a
duplicate-label row and a single-option row.

Apache-2.0.
"""

from fractions import Fraction  # noqa: F401 - imported for parity with the census module's exactness contract

# (key, labels, texts, answer_key) -- the generic census keys on the first element (here a synthetic subject).
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
# MMLU `all`: parquet columns include "subject" (str), "choices" (list[str]) and "answer" (int index). Each row
# becomes (subject, option-labels, option-texts, gold-index). auxiliary_train is excluded as a mix of other
# datasets; the test+validation+dev splits are MMLU-authored.
MMLU = {
    "hf": "cais/mmlu",
    "config": "all",
    "splits": ["test", "validation", "dev"],
    "subject_col": "subject",
    "choices_col": "choices",
    "answer_col": "answer",
}

# Canonical split sizes (sanity gate, not a hard prediction); reproduce audit 53's MMLU-all totals.
EXPECTED_SPLIT_COUNTS = {"test": 14042, "validation": 1531, "dev": 285}
EXPECTED_TOTAL_VALID = 15858  # audit 53's MMLU n_valid (all 4-option, 0 bad_key, 0 degenerate)
