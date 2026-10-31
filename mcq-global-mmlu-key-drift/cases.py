"""Configuration, pinned audit-69/70 numbers and hand-traced fixtures for audit 71. Apache-2.0.
Authored by AI agents working in the name of MV2, Munim, Inc."""

GMMLU_DATASET = "CohereLabs/Global-MMLU"
GMMLU_SPLIT = "test"
GMMLU_COLUMNS = ("sample_id", "subject", "subject_category", "question", "option_a", "option_b", "option_c",
                 "option_d", "answer", "cultural_sensitivity_label", "is_annotated")
REFERENCE_LANGUAGE = "en"
REDUX_DATASET = "edinburgh-dawg/mmlu-redux-2.0"
REDUX_SPLIT = "test"

EXPECTED_N_CONFIGS = 42
EXPECTED_N_ROWS = 14042

# Audit 70 (mcq-global-mmlu-length-census-v1): key letters differing from English, per language, over all rows.
AUDIT70_KEY_MISMATCH = {"zh": 176, "ko": 116, "de": 5, "it": 3, "yo": 2, "ja": 1}

# Audit 69 / 58: MMLU-Redux 2.0 test, 57 subjects x 100 rows, label counts.
EXPECTED_REDUX_ROWS = 5700
EXPECTED_REDUX_LABELS = {"ok": 5330, "bad_question_clarity": 132, "bad_options_clarity": 25,
                         "multiple_correct_answers": 39, "no_correct_answer": 36, "wrong_groundtruth": 106,
                         "expert": 32}

FOCUS = ("zh", "ko")             # the two languages with many disagreements
P2_MIN_SAME_ORDER = 0.99         # control: share of resolvable key-agreeing rows whose options keep their places
P3_MIN_RESOLVED = 10             # below this many resolvable zh+ko disagreements P3 is vacuous
P4_MIN_SHARED = 10               # zh and ko disagreements shared (chance: about 176 * 116 / 14,042 = 1.5)
P4_MIN_SAME_KEY = 0.80           # share of shared disagreements where zh and ko give the same key
P5_MIN_JOINED = 10               # below this many Redux-joined zh/ko disagreements P5 is vacuous
P5_MIN_RATIO = 2.0               # error-label share among disagreements vs among all joined rows
P6_MIN_N = 5                     # below this many letter-corrected miskeys among zh/ko disagreements P6 is vacuous
P7_MIN_JOIN_SHARE = 0.95         # MMLU-Redux rows joined to Global-MMLU English


def _e(sid, options, key, subject="s", question="q"):
    return {"sample_id": sid, "subject": subject, "options": options, "key": key, "question": question}


# English rows (key as index).
FIXTURE_EN = [
    _e("s/test/0", ["1", "2", "3", "4"], 0),                    # E1
    _e("s/test/1", ["10 m", "20 m", "30 m", "40 m"], 1),        # E2
    _e("s/test/2", ["red", "green", "blue", "black"], 2),       # E3
    _e("s/test/3", ["5", "6", "7", "8"], 3),                    # E4
    _e("s/test/4", ["x", "y", "z", "w"], 0),                    # E5
    _e("s/test/5", ["a", "b", "c", "d"], 0),                    # E6
]

# Translated rows.
FIXTURE_XX = [
    _e("s/test/0", ["1", "2", "3", "4"], 0),                    # X1 letter same, same order, same answer
    _e("s/test/1", ["30 米", "10 米", "20 米", "40 米"], 2),      # X2 reordered (2,0,1,3); perm[2] = 1 = E2 key
    _e("s/test/2", ["红", "绿", "蓝", "黑"], 3),                  # X3 nothing matches -> unresolved
    _e("s/test/3", ["5", "6", "7", "8"], 1),                    # X4 same order, key moved 3 -> 1
    _e("s/test/4", ["y", "x", "z", "w"], 0),                    # X5 letter same but reordered (1,0,2,3): answer moved
    _e("s/test/9", ["1", "2", "3", "4"], 0),                    # X6 not in English
    _e("s/test/5", ["a", "", "c", "d"], 1),                     # X7 blank option -> invalid; letter differs
]

FIXTURE_TALLY = {
    "n_rows": 7, "missing_in_reference": 1, "invalid": 1, "compared": 5, "key_mismatch_all": 4,
    "key_equal": 2, "key_mismatch": 3,
    "cells": {"letter_same|same_order|answer_same": 1, "letter_differs|reordered|answer_same": 1,
              "letter_differs|unresolved|answer_unknown": 1, "letter_differs|same_order|answer_different": 1,
              "letter_same|reordered|answer_different": 1},
    "kinds": {"same_answer_new_letter": 1, "unresolved": 1, "different_answer_same_order": 1},
}
FIXTURE_MISMATCHES = {"s/test/1": (2, "same_answer_new_letter"), "s/test/2": (3, "unresolved"),
                      "s/test/3": (1, "different_answer_same_order")}


def _x(options, key, label, correct=None, subject="s", question="q"):
    return {"subject": subject, "options": options, "key": key, "label": label, "correct": correct,
            "question": question}


FIXTURE_REDUX = [
    _x(["1", "2", "3", "4"], 0, "ok"),                                       # R1 -> s/test/0, question equal
    _x(["red", "green", "blue", "black"], 2, "wrong_groundtruth", "D",
       question="q changed"),                                                # R2 -> s/test/2, question differs
    _x(["p", "q", "r", "s"], 1, "ok"),                                       # R3 not found
]
FIXTURE_JOIN_STATS = {"n_redux": 3, "joined": 2, "not_found": 1, "ambiguous": 0, "question_equal": 1,
                      "key_equal": 2}

# What job.py checks before reading any real data: the tally, the mismatches and the join on the fixtures.
FIXTURE_TARGET = {"tally": FIXTURE_TALLY, "mismatches": FIXTURE_MISMATCHES, "join": FIXTURE_JOIN_STATS,
                  "correction": {"n": 1, "equals_correction": 1, "equals_published": 0, "other": 0}}
