"""Audit 75 configuration: datasets, pinned numbers from earlier audits, thresholds and the hand-traced fixture.

Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

REDUX_DATASET = "edinburgh-dawg/mmlu-redux-2.0"
REDUX_SPLIT = "test"
MMLU = {"hf": "cais/mmlu", "config": "all", "splits": ["test"], "cols": ["subject", "question", "choices", "answer"]}
PRO = {"hf": "TIGER-Lab/MMLU-Pro", "config": "default", "splits": ["test"],
       "cols": ["question_id", "question", "options", "answer_index", "category", "src"]}

# Pinned from earlier audits (P1 structural gate).
EXPECTED_PRO_N = 12032            # audits 59/61
EXPECTED_PRO_ORI = 6810           # audits 59/62
EXPECTED_MMLU_TEST = 14042        # audits 70-74
EXPECTED_REDUX_N = 5700           # audits 58/69
EXPECTED_REDUX_SUBJECTS = 57
EXPECTED_LABELS = {"bad_options_clarity": 25, "bad_question_clarity": 132, "expert": 32,
                   "multiple_correct_answers": 39, "no_correct_answer": 36, "ok": 5330, "wrong_groundtruth": 106}

# Thresholds, frozen before any real number was seen.
P1_MIN_JOIN = 0.99      # Redux rows joined to MMLU test by (subject, question, options)
P2_MIN_IN_PRO = 0.30    # share of the 5,700 Redux rows found in MMLU-Pro (one or several matching rows)
P3_MIN_KEPT = 0.75      # miskeyed rows in MMLU-Pro whose MMLU-Pro key is MMLU's (disputed) key
P3_MIN_N = 10
P5_MIN_PRESENT = 0.80   # inherited miskeys whose expert answer (letters/text) is still an MMLU-Pro option
P5_MIN_N = 10
P6_MIN_FLAGGED = 0.50   # MMLU-Pro keys moved to another MMLU option that Redux had flagged (any non-ok label)
P6_MIN_N = 5


def _r(subject, question, choices, answer, label, correct):
    return {"subject": subject, "question": question, "choices": choices, "answer": answer, "label": label,
            "correct": correct}


def _m(subject, question, choices, answer):
    return {"subject": subject, "question": question, "choices": choices, "answer": answer}


def _p(qid, question, options, ai, src):
    return {"question_id": qid, "question": question, "options": options, "answer_index": ai, "category": "c",
            "src": src}


FIXTURE_REDUX = [
    _r("S1", "Q one?", ["a", "b", "c", "d"], 0, "ok", None),
    _r("S1", "Q two?", ["e", "f", "g", "h"], 1, "wrong_groundtruth", "C"),
    _r("S1", "Q three?", ["i", "j", "k", "l"], 2, "wrong_groundtruth", "0"),
    _r("S2", "Q four?", ["m", "n", "o", "p"], 3, "ok", None),
    _r("S2", "Q five?", ["q", "r", "s", "t"], 0, "bad_question_clarity", None),
    _r("S2", "Same stem?", ["u", "v", "w", "x"], 0, "ok", None),
    _r("S2", "Q seven?", ["aa", "bb", "cc", "dd"], 0, "ok", None),
    _r("S1", "Q eight?", ["a8", "b8", "c8", "d8"], 0, "expert", None),
    _r("S1", "Q nine?", ["a9", "b9", "c9", "d9"], 1, "no_correct_answer", None),
]

FIXTURE_MMLU = [
    _m("S1", "Q one?", ["a", "b", "c", "d"], 0),
    _m("S1", "Q two?", ["e", "f", "g", "h"], 1),
    _m("S1", "Q three?", ["i", "j", "k", "l"], 2),
    _m("S2", "Q four?", ["m", "n", "o", "p"], 3),
    _m("S2", "Q five?", ["q", "r", "s", "t"], 0),
    _m("S2", "Same stem?", ["u", "v", "w", "x"], 0),
    _m("S2", "Same stem?", ["u2", "v2", "w2", "x2"], 1),
    _m("S1", "Q eight?", ["a8", "b8", "c8", "d8"], 0),
    _m("S1", "Q nine?", ["a9", "b9", "c9", "d9"], 1),
    _m("S1", "Q ten?", ["x1", "x2"], 5),
]

FIXTURE_PRO = [
    _p(101, "Q one?", ["a", "b", "c", "d", "z1"], 0, "ori_mmlu-S1"),
    _p(102, "Q two?", ["e", "f", "g", "h", "y1"], 1, "ori_mmlu-S1"),
    _p(103, "Q three?", ["i", "j", "k", "l"], 0, "ori_mmlu-S1"),
    _p(105, "Q  five?", ["q ", "r", "s", "t", "extra"], 0, "ori_mmlu-S1"),
    _p(106, "Same stem?", ["u2", "v2", "w2", "x2", "y2"], 1, "ori_mmlu-S2"),
    _p(108, "Q eight?", ["NEW", "b8", "c8", "d8"], 0, "ori_mmlu-S1"),
    _p(109, "Q nine?", ["a9", "b9", "c9", "d9"], 1, "ori_mmlu-S1"),
    _p(110, "Q nine?", ["d9", "c9", "b9", "a9", "e9"], 2, "ori_mmlu-S1"),
    _p(200, "Q four?", ["m", "n", "o", "p"], 3, "stemez-Biology"),
]

# Hand-traced (see test_redux_pro.py for the reasoning row by row).
FIXTURE_TARGET = {
    "redux_mmlu": {"joined": 8, "no_match": 1, "ambiguous": 0},
    "redux_answer_equals_mmlu_key": 8,
    "pro_join": {"in_pro": 5, "ambiguous_pro": 1, "not_in_pro": 2, "stem_only": 1, "cross_subject": 1},
    "by_label": {
        "ok": {"n": 3, "in_pro": 1, "kept": 1, "moved": 0, "new": 0},
        "wrong_groundtruth": {"n": 2, "in_pro": 2, "kept": 1, "moved": 1, "new": 0},
        "bad_question_clarity": {"n": 1, "in_pro": 1, "kept": 1, "moved": 0, "new": 0},
        "expert": {"n": 1, "in_pro": 1, "kept": 0, "moved": 0, "new": 1},
        "no_correct_answer": {"n": 1, "in_pro": 1, "kept": 0, "moved": 0, "new": 0},
    },
    "moved_labels": {"wrong_groundtruth": 1},
    "new_labels": {"expert": 1},
    "miskey": {"in_pro_unique": 2, "kept": 1, "moved": 1, "new": 0,
               "corrections": {
                   "primary": {"resolved": 1, "resolved_kept": 1, "kept_present": 1, "pro_key_is_correction": 0},
                   "digits_0_based": {"resolved": 2, "resolved_kept": 1, "kept_present": 1,
                                      "pro_key_is_correction": 1},
                   "digits_1_based": {"resolved": 1, "resolved_kept": 1, "kept_present": 1,
                                      "pro_key_is_correction": 0}}},
    "inclusion_table": [[4, 0], [1, 2]],
    "inclusion_rr": 3.0,
    "inclusion_chi2": 3.733333,
    "cmh_o_minus_e": 0.666667,
    "cmh_stat": 2.0,
    "cmh_mh_or": None,
    "cmh_informative": 1,
    "strata": {"S1": [3, 0, 1, 0], "S2": [1, 0, 0, 2]},
    "flags": [
        (102, "wrong_groundtruth", "kept", "B", "C", "C", "C", "letters"),
        (103, "wrong_groundtruth", "moved", "A", None, "A", None, "digits"),
        (105, "bad_question_clarity", "kept", "A", None, None, None, "none"),
        (108, "expert", "new", "A", None, None, None, "none"),
    ],
}
