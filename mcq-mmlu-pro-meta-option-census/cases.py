"""Hand-traced fixtures and real-data configuration for the MMLU-Pro META-OPTION + POSITION census (audit 59).

Audit 56 found that in 4-option MMLU the gold leans toward the LAST option (pooled 26.7%) and that "all/none of
the above"-type options sit last in >=90% of the questions carrying one and are the gold above chance -- a
construction artifact. MMLU-Pro (Wang et al., 2024) rebuilt the same questions with up to TEN options, most of
them GPT-4-generated distractors, as a deliberately harder and (its authors hoped) more robust benchmark. This
audit asks, with the SAME instrument: did the 4->10 expansion remove or keep those two artifacts? Where does the
gold sit across up to ten positions, and do "all of the above"-style cues survive?

Two fixtures, both checked for exact equality before any real file is read, are REUSED VERBATIM from audit 56:
  FIXTURE_ROWS / TARGET            the gold-position census fixture (verbatim from audits 53/54/55/56)
  META_FIXTURE_ROWS / META_TARGET  the meta-option fixture (verbatim from audit 56)

The only genuinely new pieces here are the real-data configuration (MMLU-Pro instead of MMLU) and the audit-59
predictions in job.py. position_census.py extends only the chi-square critical table to df 12 (10-option
questions need df 9); the census/classifier logic is unchanged, so these fixtures pin it exactly as before.

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
# MMLU-Pro (TIGER-Lab/MMLU-Pro) parquet columns: "options" (list[str]), "answer_index" (int, 0-based gold),
# "category" (str, one of 14 subject groups) and "src" (str, provenance tag, e.g. "ori_mmlu-business_ethics").
# Each row becomes (category, option-labels "0".."k-1", option-texts, gold-index-as-string, src). Only the
# authored TEST split is used (the small 70-item validation split exists only to seed 5-shot CoT prompts).
MMLU_PRO = {
    "hf": "TIGER-Lab/MMLU-Pro",
    "config": "default",
    "splits": ["test"],
    "subject_col": "category",
    "choices_col": "options",
    "answer_col": "answer_index",
    "src_col": "src",
}

# Documented size of the MMLU-Pro test split (Wang et al., 2024). Reported as a sanity check, NOT gated on, so a
# dataset revision that changed the count by a few rows will not fail the run.
EXPECTED_SPLIT_COUNTS = {"test": 12032}

# Prefix of the `src` tag for questions inherited from the original 4-option MMLU.
ORI_MMLU_PREFIX = "ori_mmlu"
