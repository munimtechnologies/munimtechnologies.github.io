"""Constants, gates, thresholds and hand-traced fixtures for audit 92 (mcq-helm-option-collisions). Every fixture
expectation is traced by hand in test_grade92.py. Apache-2.0. Authored by AI agents working in the name of MV2,
Munim, Inc.
"""

from fractions import Fraction

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/lite/benchmark_output"
HELM_RELEASE = "v1.13.0"
# HELM Lite's three multiple_choice_joint benchmarks and the main metric HELM records per item for each.
BENCHES = {
    "mmlu": {"prefix": "mmlu:", "must_contain": "method=multiple_choice_joint", "metric": "exact_match",
             "subjects": ("abstract_algebra", "college_chemistry", "computer_security", "econometrics",
                          "us_foreign_policy")},
    "med_qa": {"prefix": "med_qa:", "must_contain": None, "metric": "quasi_exact_match", "subjects": ("-",)},
    "openbookqa": {"prefix": "commonsense:dataset=openbookqa,method=multiple_choice_joint,", "must_contain": None,
                   "metric": "exact_match", "subjects": ("-",)},
}
WORKERS = 8

# ----- Gates (P1) -----
MAX_RUN_NO_GOLD = Fraction(1, 100)        # first-trial predictions without a parsable gold, per run
MIN_RUN_SCORED_VS_MEDIAN = Fraction(95, 100)  # a run scores at least this share of the median run of its subject
MIN_RUN_CONSISTENT = Fraction(99, 100)    # our H equals HELM's recorded main metric on this share of a run
MIN_ALL_CONSISTENT = Fraction(999, 1000)  # ... and on this share of all included predictions
MIN_ALL_MAPPED = Fraction(999, 1000)      # HELM's mapped_output equals our letter -> option text on this share
MIN_MODELS = 80                           # per benchmark: models with every subject run included

# ----- Thresholds of P2-P7 -----
THRESHOLDS = {"P2_min_questions": 1, "P3_num": 2, "P3_den": 1000, "P4_min_move": 3, "P5_min_prefix": 5,
              "P5_ratio": 2, "P6_min_identical": 1, "P7_share": Fraction(1, 100), "P7_min_models": 3}

# ----- Printed for the hand-read (stdout only, never published) -----
PRINT_COLLISIONS = 40   # identical and quasi_only collision questions, all benchmarks
PRINT_PREFIX = 15       # prefix_only collision questions, for illustration

# ----- Fixture 1: HELM's normalisation and metrics -----
# (text, normalize_text(text))
FIX_NORM = [("-7", "7"), ("1.25", "125"), ("The heart", "heart"), ("  An  Apple. ", "apple"), ("a b", "b"),
            ("?", ""), ("Type II", "type ii"), ("then", "then")]
# (metric function name, gold, pred, score)
FIX_METRIC = [
    ("exact_match", "-7", "7", 0), ("quasi_exact_match", "-7", "7", 1), ("exact_match", " x ", "x", 1),
    ("exact_match", "x", "", 0), ("quasi_exact_match", "?", "!", 1), ("quasi_prefix_exact_match", "red", "red blue", 1),
    ("quasi_prefix_exact_match", "red blue", "red", 0), ("quasi_prefix_exact_match", "2", "24", 1),
]

# ----- Fixture 2: grade() on (options, gold index, output, metric) -----
# (opts, gold_i, pred, metric, idx, h, i, cls, unmapped)
FIX_GRADE = [
    (["-7", "7", "0", "1"], 0, "B", "quasi_exact_match", 1, 1, 0, "quasi_only", None),
    (["-7", "7", "0", "1"], 0, "B", "exact_match", 1, 0, 0, None, None),
    (["Aspirin", "Ibuprofen", "Aspirin", "Heparin"], 0, "C", "exact_match", 2, 1, 0, "identical", None),
    (["Aspirin", "Ibuprofen"], 1, " B\n", "quasi_exact_match", 1, 1, 1, None, None),
    (["", "x"], 0, "A", "exact_match", 0, 0, 1, "under", None),
    (["p", "q", "r", "s"], 1, "b", "quasi_exact_match", None, 0, 0, None, "lowercase_letter"),
    (["p", "q", "r", "s"], 1, "E", "quasi_exact_match", None, 0, 0, None, "letter_out_of_range"),
    (["p", "q", "r", "s"], 1, "The", "quasi_exact_match", None, 0, 0, None, "other"),
    (["p", "q", "r", "s"], 1, " ", "exact_match", None, 0, 0, None, "empty"),
    (["The heart", "heart", "lung"], 1, "A", "quasi_exact_match", 0, 1, 0, "quasi_only", None),
    (["2", "24", "4"], 0, "B", "quasi_exact_match", 1, 0, 0, None, None),
]

# ----- Fixture 3: collisions() and gold_norm_empty() -----
# (opts, gold_i, collisions, gold_norm_empty)
FIX_COLL = [
    (["-7", "7", "0", "1"], 0, {"identical": [], "quasi_only": [1], "prefix_only": []}, False),
    (["2", "24", "4", "20"], 0, {"identical": [], "quasi_only": [], "prefix_only": [1, 3]}, False),
    (["Aspirin", "Ibuprofen", "Aspirin ", " aspirin."], 0, {"identical": [2], "quasi_only": [3], "prefix_only": []},
     False),
    (["red", "red blue", "blue"], 0, {"identical": [], "quasi_only": [], "prefix_only": [1]}, False),
    (["?", "a b", ""], 0, {"identical": [], "quasi_only": [], "prefix_only": [1]}, True),
    (["red blue", "red", "blue"], 0, {"identical": [], "quasi_only": [], "prefix_only": []}, False),
]

# ----- Fixture 4: run selection -----
_MQ = "med_qa:model=a_x"
_MMLU_J = "mmlu:subject=econometrics,method=multiple_choice_joint,model=a_x"
_MMLU_S = "mmlu:subject=econometrics,method=multiple_choice_separate_original,model=a_x"
_OBQA = "commonsense:dataset=openbookqa,method=multiple_choice_joint,model=a_x"
FIX_RUNS = {_MQ: "v1.0.0", _MQ + ",stop=none": "v1.0.0", "med_qa:model=b_y": "v1.0.0",
            "med_qa:model=b_y,stop=none": "v1.9.0", _MMLU_J: "v1.0.0", _MMLU_S: "v1.0.0",
            "mmlu_pro:subset=all,model=a_x": "v1.0.0", _OBQA: "v1.2.0"}
FIX_RUNS_TARGET = {
    "med_qa": ({("a_x", "-"): (_MQ, "v1.0.0"), ("b_y", "-"): ("med_qa:model=b_y,stop=none", "v1.9.0")}, 2),
    "mmlu": ({("a_x", "econometrics"): (_MMLU_J, "v1.0.0")}, 0),
    "openbookqa": ({("a_x", "-"): (_OBQA, "v1.2.0")}, 0),
}

# ----- Fixture 5: ranks and Kendall's tau-b (as audits 90 and 91) -----
FIX_ACC = {"a": Fraction(9, 10), "b": Fraction(8, 10), "c": Fraction(8, 10), "d": Fraction(1, 2)}
FIX_RANKS = {"a": 1, "b": 2, "c": 2, "d": 4}
FIX_TAU = [([1, 2, 3], [1, 2, 3], 1.0), ([1, 2, 3], [3, 2, 1], -1.0), ([1, 1, 2], [1, 2, 3], 2 / 6 ** 0.5),
           ([1, 1, 1], [1, 2, 3], None)]

# ----- Fixture 6: verdicts -----
# (q_quasi_medqa, over_medqa, n_medqa, moved_medqa, q_prefix_all, q_quasi_all, q_identical_all,
#  models_unmapped_medqa) -> verdicts
_ALL = ("P2_quasi_collision_medqa", "P3_overcredit_small_medqa", "P4_medqa_ranks_stable", "P5_prefix_hazard_larger",
        "P6_identical_duplicates", "P7_format_loss_medqa")
FIX_V_CASES = [
    ((1, 20, 10000, 0, 6, 3, 1, 3), {k: True for k in _ALL}),
    ((0, 21, 10000, 1, 5, 3, 0, 2), {k: False for k in _ALL}),
    ((0, 0, 0, 0, 0, 0, 0, 0), dict(zip(_ALL, (False, False, True, False, False, False)))),
]
