"""Hand-traced fixtures and real-data configuration for the CROSS-BENCHMARK meta-option census (audit 57).

Audit 56 found that MMLU carries "all of the above"-type META options in 4.86% of questions, that they sit last
in 92.5% of the questions that have one, that "all of the above" is the gold 59.6% of the time, and that
removing them shifts MMLU's modal gold position off the LAST slot -- i.e. MMLU's "the answer is D" tilt is mostly
a meta-option artifact. Audit 53 separately found ARC-Easy, ARC-Challenge and CommonsenseQA are POSITIONALLY
UNIFORM (no last-tilt), while OpenBookQA tilts first and MMLU tilts last.

This audit ports audit 56's meta-option census to four other benchmarks -- ARC-Easy, ARC-Challenge,
CommonsenseQA and HellaSwag -- to ask whether the meta-option mechanism is MMLU-specific or a general
exam-authoring convention, and whether its (near-)absence lines up with those benchmarks' lack of a position
tilt. HellaSwag options are free-text sentence completions and CommonsenseQA options are short noun phrases, so
both are predicted to carry essentially NO meta options; ARC is grade-school science-exam material like MMLU, so
whether it carries them is the open question.

Three fixtures, all checked for exact equality before any real file is read:
  FIXTURE_ROWS / TARGET            the gold-position census fixture, reused verbatim from audits 53/54/55/56
  META_FIXTURE_ROWS / META_TARGET  the meta-option census fixture, reused verbatim from audit 56
  (the per-schema row-shaping is covered by test_loaders.py against loaders.py)

Apache-2.0.
"""

from fractions import Fraction

# ----- Gold-position census fixture (verbatim from audits 53/54/55/56) -----
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


# ----- Meta-option fixture (verbatim from audit 56) -----
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
# Two parquet schemas:
#   "choices_struct"  ARC (allenai/ai2_arc) and CommonsenseQA (tau/commonsense_qa): the "choices" column is a
#                     struct of parallel lists {"text": [...], "label": [...]}; "answerKey" is a label string.
#   "endings"         HellaSwag (Rowan/hellaswag): "endings" is a list[str]; "label" is the gold index as a
#                     string ("0".."3"). Labels are synthesised as "0".."k-1".
# Goldless test splits are EXCLUDED: CommonsenseQA test and HellaSwag test have an empty answer; ARC test keeps a
# real answerKey, so all three ARC splits are used.
DATASETS = [
    {"name": "arc_easy", "display": "ARC-Easy", "hf": "allenai/ai2_arc", "config": "ARC-Easy",
     "splits": ["train", "validation", "test"], "schema": "choices_struct"},
    {"name": "arc_challenge", "display": "ARC-Challenge", "hf": "allenai/ai2_arc", "config": "ARC-Challenge",
     "splits": ["train", "validation", "test"], "schema": "choices_struct"},
    {"name": "commonsense_qa", "display": "CommonsenseQA", "hf": "tau/commonsense_qa", "config": "default",
     "splits": ["train", "validation"], "schema": "choices_struct"},
    {"name": "hellaswag", "display": "HellaSwag", "hf": "Rowan/hellaswag", "config": "default",
     "splits": ["train", "validation"], "schema": "endings"},
]

# Canonical split sizes (sanity gate, not a hard prediction). The gold-bearing splits only; standard HF sizes.
EXPECTED_SPLIT_COUNTS = {
    "arc_easy": {"train": 2251, "validation": 570, "test": 2376},
    "arc_challenge": {"train": 1119, "validation": 299, "test": 1172},
    "commonsense_qa": {"train": 9741, "validation": 1221},
    "hellaswag": {"train": 39905, "validation": 10042},
}
# Expected valid totals (reported; CommonsenseQA 10,962 and HellaSwag 49,947 reproduce run-186 / audit-52 counts).
EXPECTED_TOTAL_VALID = {
    "arc_easy": 5197, "arc_challenge": 2590, "commonsense_qa": 10962, "hellaswag": 49947,
}

# MMLU reference numbers (audit 56; NOT recomputed here, cited for comparison only).
MMLU_REFERENCE = {
    "meta_option_rate": 0.0486, "aota_nota_last_rate": 0.925, "aota_is_gold_rate": 0.596,
    "pooled_last_rate_all": 0.267, "note": "see audit 56 (mcq-mmlu-meta-option-census)",
}

# Pre-registered thresholds for the real-data predictions (decided before any real number was seen).
NO_META_THRESHOLD = 0.005   # P2/P3: "essentially zero" meta options
ARC_META_THRESHOLD = 0.01   # P4 (headline): ARC carries meta options like an exam benchmark
LAST_RATE_THRESHOLD = 0.90  # P5: meta options sit last
P5_MIN_N = 30               # P5 power floor: fewer than this many aota/nota questions -> vacuous
