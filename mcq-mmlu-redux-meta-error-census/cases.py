"""Hand-traced fixtures and real-data configuration for the MMLU-Redux META-OPTION x ERROR census (audit 58).

Audit 56 found that 4.86% of MMLU questions carry an "all of the above"-type META option, that these sit last and
cue the gold, and that they explain most of MMLU's "the answer is D" tilt. MMLU-Redux 2.0 (Gema et al. 2024,
arXiv 2406.04127; CC BY 4.0) has expert error labels for 100 questions from each of MMLU's 57 subjects. This
audit asks whether meta-option questions are flagged as erroneous more often than plain ones, within subject.

Three fixtures, all checked for exact equality before any real file is read:
  FIXTURE_ROWS / TARGET              the gold-position census fixture, verbatim from audits 53-57
  META_FIXTURE_ROWS / META_TARGET    the meta-option census fixture, verbatim from audits 56/57
  ERROR_FIXTURE_ROWS / ERROR_TARGET  the new meta x error census fixture (hand-traced below)

Apache-2.0.
"""

from fractions import Fraction

# ----- Gold-position census fixture (verbatim from audits 53-57) -----
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


# ----- Meta-option fixture (verbatim from audits 56/57) -----
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


# ----- Meta x error fixture (new in audit 58) -----
# (subject, labels, texts, answer_key, error_type)
ERROR_FIXTURE_ROWS = [
    ("s1", L4, ["red", "blue", "green", "yellow"], "0", "ok"),                          # plain, ok
    ("s1", L4, ["a", "b", "c", "d"], "1", "wrong_groundtruth"),                         # plain, error
    ("s1", L4, ["p", "q", "r", "s"], "2", "ok"),                                         # plain, ok
    ("s1", L4, ["w", "x", "y", "z"], "3", "expert"),                                     # plain, unsure
    ("s2", L4, ["cats", "dogs", "birds", "All of the above"], "3", "multiple_correct_answers"),  # aota, error
    ("s2", L4, ["cats", "dogs", "birds", "All of the above"], "3", "ok"),                # aota, ok
    ("s2", L4, ["p", "q", "r", "None of the above"], "0", "no_correct_answer"),         # nota, error
    ("s2", L4, ["I only", "II only", "I and II", "I, II, and III"], "3", " OK "),        # roman, ok (normalised)
    ("s3", L4, ["a", "b", "c", "d"], "9", "ok"),                                         # bad_key -> n_invalid
    ("s3", L4, ["a", "b", "c", "d"], "0", "typo_label"),                                 # plain, undocumented
]

# Hand-traced ERROR_TARGET: exactly what error_census.run_error_census returns.
#   n_rows 10; row 9 invalid -> n_invalid 1 and counted nowhere else.
#   s1 plain {ok 2, wrong_groundtruth 1, expert 1}
#   s2 aota {multiple_correct_answers 1, ok 1}; nota {no_correct_answer 1}; roman {ok 1}
#   s3 plain {typo_label 1}
ERROR_TARGET = {
    "n_rows": 10,
    "n_invalid": 1,
    "by_subject": {
        "s1": {"plain": {"ok": 2, "wrong_groundtruth": 1, "expert": 1}},
        "s2": {"aota": {"multiple_correct_answers": 1, "ok": 1}, "nota": {"no_correct_answer": 1},
               "roman": {"ok": 1}},
        "s3": {"plain": {"typo_label": 1}},
    },
}


# ----- Real-data configuration, read via the HuggingFace datasets-server parquet API -----
# edinburgh-dawg/mmlu-redux-2.0: one config per MMLU subject (57), a single "test" split; columns question,
# choices (list[str]), answer (int64 gold index), error_type, source, correct_answer, potential_reason.
HF_DATASET = "edinburgh-dawg/mmlu-redux-2.0"
SPLIT = "test"
EXPECTED_N_SUBJECTS = 57
EXPECTED_N_ROWS = 5700

# MMLU reference numbers (audit 56; NOT recomputed here, cited for comparison only).
MMLU_REFERENCE = {"meta_option_rate": 0.0486, "aota_is_gold_rate": 0.596, "pooled_last_rate_all": 0.267,
                  "note": "see audit 56 (mcq-mmlu-meta-option-census)"}

# Pre-registered thresholds for the real-data predictions (decided before any real number was seen).
P3_MIN_N = 30               # P3 power floor: fewer judged aota questions than this -> vacuous
