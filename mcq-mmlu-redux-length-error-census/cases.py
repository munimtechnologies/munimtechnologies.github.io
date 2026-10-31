"""Pinned inputs for audit 69: the dataset, the structural gate from audit 58, and a hand-traced fixture.

Option lengths in the fixture are written next to each row; every expected value below was traced by hand before
any real data was read. Apache-2.0.
"""

from fractions import Fraction as F

HF_DATASET = "edinburgh-dawg/mmlu-redux-2.0"
SPLIT = "test"
TOOL_URL = "https://raw.githubusercontent.com/munimtechnologies/mcq-length-floor/v0.1.0/mcq_length_floor.py"

# Structural gate: audit 58 (mcq-mmlu-redux-meta-error-census-v1) read the same 5,700 rows; its per-category label
# counts sum to these totals (0 invalid rows there).
EXPECTED_N_SUBJECTS = 57
EXPECTED_N_ROWS = 5700
EXPECTED_LABELS = {"ok": 5330, "bad_question_clarity": 132, "bad_options_clarity": 25,
                   "multiple_correct_answers": 39, "no_correct_answer": 36, "wrong_groundtruth": 106, "expert": 32}

# Reference: audit 52 / 60, MMLU `all` (15,858 questions) pick-longest 0.2805 vs 0.25 chance.
MMLU_REFERENCE = {"n": 15858, "pick_longest": 0.2805, "chance": 0.25, "source": "eval-reliability-audits 52, 60"}

P4_MIN_N = 30          # below this many usable miskeyed pairs, P4 is vacuous (reported as FAILED, vacuous)
P6_MAX_SHIFT = 0.005   # |pick-longest(OK only) - pick-longest(all rows)| must stay under half a point

O4 = ["a", "bb", "ccc", "dddd"]  # lengths 1, 2, 3, 4


def _r(subject, options, key, label, correct=None):
    return {"subject": subject, "options": options, "key": key, "label": label, "correct": correct}


FIXTURE_ROWS = [
    _r("S1", O4, 3, "ok"),                                            # R1  cl 1    cs 0
    _r("S1", O4, 0, "ok"),                                            # R2  cl 0    cs 1   key unique shortest
    _r("S1", ["pp", "qq", "r", "s"], 1, "ok"),                        # R3  2,2,1,1  cl 1/2  cs 0
    _r("S1", O4, 1, "wrong_groundtruth", "D"),                        # R4  letters -> 3
    _r("S2", ["dddd", "ccc", "bb", "a"], 0, "wrong_groundtruth", "C"),  # R5  4,3,2,1 cl 1; letters -> 2
    _r("S2", ["a", "b", "c", "eeeee"], 2, "wrong_groundtruth", "3"),  # R6  1,1,1,5 cs 1/3; digits
    _r("S2", ["ccc", "a", "bb", "xx"], 0, "bad_question_clarity"),    # R7  3,1,2,2 cl 1
    _r("S2", O4, 2, "expert"),                                        # R8  unsure, not judged
    _r("S2", ["x", "yy", "zzz", "wwww"], 1, "wrong_groundtruth", "zzz"),  # R9  text -> 2
    _r("S1", O4, 3, "no_correct_answer", "something else"),           # R10 cl 1; unmatched
    _r("S1", ["bb", "a", "ccc", "dddd"], 0, "multiple_correct_answers", "A,C"),  # R11 2,1,3,4; letters 0,2
]

# (n, pick-longest, pick-shortest, chance) as exact fractions
FIXTURE_TARGET = {
    "n_rows": 11,
    "n_invalid": 0,
    "labels": {"ok": 3, "wrong_groundtruth": 4, "bad_question_clarity": 1, "expert": 1, "no_correct_answer": 1,
               "multiple_correct_answers": 1},
    "ALL": (11, F(9, 22), F(4, 33), F(1, 4)),
    "class=ok": (3, F(1, 2), F(1, 3), F(1, 4)),
    "class=error": (7, F(3, 7), F(1, 21), F(1, 4)),
    "class=unsure": (1, F(0), F(0), F(1, 4)),
    "label=wrong_groundtruth": (4, F(1, 4), F(1, 12), F(1, 4)),
    "ok|subject=S1": (3, F(1, 2), F(1, 3), F(1, 4)),
    # miskey pairs: (n, sum of corrected-minus-published pick-longest credit, sum of length-rank differences)
    "pairs_digits_unresolved": (3, F(0), F(1, 3)),
    "pairs_digits_0_based": (4, F(1), F(1)),
    "why_digits_unresolved": {"unresolved_digits": 1},
    "why_digits_1_based": {"same_as_key": 1},
    "detector_key_shortest_vs_miskey": [[0, 1], [4, 5]],
    "detector_other_longest_vs_miskey": [[3, 2], [1, 4]],
    "detector_other_longest_vs_any_error": [[4, 1], [3, 2]],
}
