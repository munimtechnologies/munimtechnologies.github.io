"""Hand-traced fixtures and real-data configuration for the MMLU META-OPTION census (audit 56).

Audits 53/54 found MMLU's gold position is tilted toward the LAST option (pooled 26.7%; 7 of the 8 subjects
that individually reject uniformity skew last). This audit tests one concrete mechanism: options that refer to
the other options ("All of the above", "None of these", "Both A and B", Roman-numeral statement sets) are
conventionally placed last and cannot be shuffled. Where do they sit, how often are they the gold, and does the
pooled last-tilt survive once every question carrying one is removed?

Two fixtures, both checked for exact equality before any real file is read:
  FIXTURE_ROWS / TARGET            the gold-position census fixture, reused verbatim from audits 53/54/55
  META_FIXTURE_ROWS / META_TARGET  new: one or more rows per meta category, a quadrant-style I/II/III/IV
                                   question that must stay plain, a long answer containing "all of the above"
                                   that must stay plain (token guard), a multi-meta row, a 3-option row and a
                                   bad-key row that must be skipped.

Apache-2.0.
"""

from fractions import Fraction

# ----- Gold-position census fixture (verbatim from audits 53/54/55) -----
# (key, labels, texts, answer_key) -- the generic census keys on the first element.
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


# ----- Meta-option fixture (new in audit 56) -----
# MMLU-style rows: labels are "0".."k-1" and the answer key is the gold index as a string.
L4 = ["0", "1", "2", "3"]
L3 = ["0", "1", "2"]
LONG = ("The committee reviewed all of the above-mentioned documents before voting on the final proposal")  # 14 tokens

META_FIXTURE_ROWS = [
    ("m01", L4, ["red", "blue", "green", "yellow"], "3"),                     # plain
    ("m02", L4, ["1", "2", "3", "4"], "0"),                                   # plain (Arabic digits)
    ("m03", L4, ["cats", "dogs", "birds", "All of the above"], "3"),          # aota, meta at 3 (last), gold
    ("m04", L4, ["All the above", "x", "y", "z"], "1"),                       # aota, meta at 0, not gold
    ("m05", L4, ["p", "q", "r", "None of these"], "0"),                       # nota, meta at 3 (last), not gold
    ("m06", L4, ["water", "ice", "Both A and B", "steam"], "2"),              # letterref, meta at 2, gold
    ("m07", L4, ["I only", "II only", "I and II", "I, II, and III"], "3"),    # roman, unique most-inclusive 3, gold
    ("m08", L4, ["I", "II", "III", "IV"], "1"),                               # plain: quadrant-style, no combo
    ("m09", L4, ["Both of these", "x", "y", "All of the above"], "3"),        # aota, metas at 0 and 3, gold
    ("m10", L4, ["a", "b", "c", "d"], "7"),                                   # bad_key -> skipped
    ("m11", L3, ["Neither of those", "m", "n"], "0"),                         # nota, k=3, meta at 0, gold
    ("m12", L4, [LONG, "x", "y", "z"], "0"),                                  # plain: long text, token guard
]

# Hand-traced META_TARGET: exactly what meta_option.run_meta_census returns.
#   plain     m01 m02 m08 m12                    n=4
#   aota      m03 (idx[3]) m04 (idx[0]) m09 (idx[0,3])
#             first-pos {3:1, 0:2}; last: m03 m09 = 2; gold: m03 m09 = 2; multi: m09 = 1;
#             expected = 1/4 + 1/4 + 2/4 = 1
#   nota      m05 (idx[3], k=4) m11 (idx[0], k=3)
#             first-pos {3:1, 0:1}; last: m05 = 1; gold: m11 = 1; expected = 1/4 + 1/3 = 7/12
#   letterref m06 (idx[2]) first-pos {2:1}; last 0; gold 1; expected 1/4
#   roman     m07: numeral counts 1,1,2,3 -> unique most-inclusive idx 3 == gold; expected 1/4
META_TARGET = {
    "plain": {"n": 4, "meta_pos_counts": {}, "n_meta_last": 0, "n_meta_gold": 0, "n_multi_meta": 0,
              "expected_meta_gold": Fraction(0), "n_inclusive_unique": 0, "n_gold_inclusive": 0,
              "expected_gold_inclusive": Fraction(0)},
    "aota": {"n": 3, "meta_pos_counts": {3: 1, 0: 2}, "n_meta_last": 2, "n_meta_gold": 2, "n_multi_meta": 1,
             "expected_meta_gold": Fraction(1), "n_inclusive_unique": 0, "n_gold_inclusive": 0,
             "expected_gold_inclusive": Fraction(0)},
    "nota": {"n": 2, "meta_pos_counts": {3: 1, 0: 1}, "n_meta_last": 1, "n_meta_gold": 1, "n_multi_meta": 0,
             "expected_meta_gold": Fraction(7, 12), "n_inclusive_unique": 0, "n_gold_inclusive": 0,
             "expected_gold_inclusive": Fraction(0)},
    "letterref": {"n": 1, "meta_pos_counts": {2: 1}, "n_meta_last": 0, "n_meta_gold": 1, "n_multi_meta": 0,
                  "expected_meta_gold": Fraction(1, 4), "n_inclusive_unique": 0, "n_gold_inclusive": 0,
                  "expected_gold_inclusive": Fraction(0)},
    "roman": {"n": 1, "meta_pos_counts": {}, "n_meta_last": 0, "n_meta_gold": 0, "n_multi_meta": 0,
              "expected_meta_gold": Fraction(0), "n_inclusive_unique": 1, "n_gold_inclusive": 1,
              "expected_gold_inclusive": Fraction(1, 4)},
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

# Audit 54's subjects that individually reject a uniform gold position at alpha=0.001 (reported, not bet on).
AUDIT54_SIGNIFICANT = [
    "college_chemistry", "high_school_government_and_politics", "high_school_macroeconomics",
    "high_school_psychology", "high_school_statistics", "human_aging", "professional_medicine",
    "security_studies",
]
