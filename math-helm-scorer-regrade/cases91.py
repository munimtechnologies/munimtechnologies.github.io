"""Constants, gates, thresholds and hand-traced fixtures for audit 91 (math-helm-scorer-regrade). Every fixture
expectation is traced by hand in test_grade91.py. Apache-2.0. Authored by AI agents working in the name of MV2,
Munim, Inc.
"""

from fractions import Fraction

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/lite/benchmark_output"
HELM_RELEASE = "v1.13.0"
HELM_PREFIX = "math:"
STAT = "math_equiv_chain_of_thought"
SUBJECTS = ("algebra", "counting_and_probability", "geometry", "intermediate_algebra", "number_theory",
            "prealgebra", "precalculus")
WORKERS = 8

# ----- Gates (P1) -----
MIN_RUN_SCORED = Fraction(95, 100)        # a run must score at least this share of its test instances
MIN_RUN_CONSISTENT = Fraction(99, 100)    # our transcription of H must equal HELM's recorded score on this share
MIN_ALL_CONSISTENT = Fraction(999, 1000)  # ... and on this share of all included predictions
MIN_MODELS = 80                           # models with all 7 subject runs included
MIN_GOLD_AGREE = Fraction(99, 100)        # share of (subject, id) whose reference answer is the same in every run

# ----- Thresholds of P2-P7 -----
THRESHOLDS = {"P2_num": 5, "P2_den": 1000, "P3_min_unboxed": 100, "P4_min_value": 20, "P5_min_gold_none": 1,
              "P6_min_models": 5, "P6_min_move": 3, "P7_ratio": 5}

# ----- The hand-read sample for P8 (graded next run, by reading) -----
SAMPLE_SEED = 91
SAMPLE_UP = 30
SAMPLE_DOWN = 15
P8_MIN_GENUINE = 27

# ----- Fixture 1: H, A, route and class on nineteen (reference, output) pairs -----
# (gold, prediction, h, a, route, class)
FIX_GRADE = [
    ("so $x=\\boxed{5}$.", "Thus $x = \\boxed{5}$.", 1, 1, "boxed", None),
    ("$\\boxed{10001}$.", "$\\boxed{10,001}$.", 0, 1, "boxed", "value_format"),
    ("\\boxed{\\frac{3}{2}}", "\\boxed{1.5}", 0, 1, "boxed", "value_format"),
    ("\\boxed{21y+14}", "We get $7(3y+2) = 21y + 14$", 0, 1, "unboxed_math", "unboxed"),
    ("\\boxed{7}", "The answer is $7$.", 0, 1, "unboxed_phrase", "unboxed"),
    ("So the answer is $\\boxed 5$.", "The answer is 7.", 1, 0, "unboxed_phrase", "both_none"),
    ("$\\boxed 5$", "The answer is 5.", 1, 1, "unboxed_phrase", None),
    ("$\\boxed 5$", "$\\boxed{5}$", 0, 1, "boxed", "gold_fallback"),
    ("\\boxed{12}", "Final: \\fbox{12}", 0, 1, "fallback", "pred_fallback"),
    ("\\boxed{9901}", "$\\boxed{10001}$", 0, 0, "boxed", None),
    ("\\boxed{5}", "\\boxed{5\\text{cm}}", 0, 1, "boxed", "value_format"),
    ("\\boxed{3}", "\\boxed{3\\text{ cm}\\text{ m}}", 0, 1, "boxed", "value_format"),
    ("\\boxed{-\\frac{1}{3}}", "\\boxed{-1/3}", 0, 1, "boxed", "value_format"),
    ("\\boxed{(1,2)}", "\\boxed{(1, 2)}", 1, 1, "boxed", None),
    ("\\boxed{4}", "I think it is 4", 0, 0, "unboxed_none", None),
    ("\\boxed{2}", "We have $x^2 = 4$ so", 0, 0, "unboxed_math", None),
    ("\\boxed{6}", "Thus\n$$n = 6$$", 0, 1, "unboxed_math", "unboxed"),
    ("no box here", "nothing", 1, 0, "no_gold", "both_none"),
    ("\\boxed{\\frac12}", "\\boxed{0.5}", 1, 1, "boxed", None),
]

# ----- Fixture 2: value() -----
FIX_VALUE = [("10,001", Fraction(10001)), ("\\frac{3}{2}", Fraction(3, 2)), ("-\\frac{1}{3}", Fraction(-1, 3)),
             ("2/4", Fraction(1, 2)), ("5\\text{cm}", Fraction(5)), ("x+1", None), ("1,2", None),
             ("0.50", Fraction(1, 2)), ("\\$18.90", Fraction(189, 10)), ("", None), (None, None)]

# ----- Fixture 3: unboxed_candidate() -----
FIX_UNBOXED = [
    ("We get $7(3y+2) = 21y + 14$", ("21y + 14", "math")),
    ("The answer is $7$.", ("7", "phrase")),
    ("The answer is 7.", ("7", "phrase")),
    ("I think it is 4", ("", "none")),
    ("Thus\n$$n = 6$$", ("6", "math")),
    ("The final answer is: \\(\\frac{1}{2}\\)", ("\\frac{1}{2}", "phrase")),
    ("Cost is \\$5 and $x=3$", ("3", "math")),
    ("Answer is 4 apples\nso the answer is $x = 12$.", ("12", "phrase")),
]

# ----- Fixture 4: run selection, one run per (model, subject) -----
_R1 = "math:subject=algebra,level=1,use_official_examples=False,use_chain_of_thought=True,model=a_x"
_R2 = _R1 + ",stop=none"
_R3 = "math:subject=geometry,level=1,use_official_examples=False,use_chain_of_thought=True,model=a_x"
FIX_RUNS = {_R1: "v1.0.0", _R2: "v1.8.0", _R3: "v1.0.0", "gsm:model=a_x": "v1.0.0"}
FIX_RUNS_TARGET = ({("a_x", "algebra"): (_R2, "v1.8.0"), ("a_x", "geometry"): (_R3, "v1.0.0")}, 1)

# ----- Fixture 5: ranks and Kendall's tau-b (as audit 90) -----
FIX_ACC = {"a": Fraction(9, 10), "b": Fraction(8, 10), "c": Fraction(8, 10), "d": Fraction(1, 2)}
FIX_RANKS = {"a": 1, "b": 2, "c": 2, "d": 4}
FIX_TAU = [([1, 2, 3], [1, 2, 3], 1.0), ([1, 2, 3], [3, 2, 1], -1.0), ([1, 1, 2], [1, 2, 3], 2 / 6 ** 0.5),
           ([1, 1, 1], [1, 2, 3], None)]

# ----- Fixture 6: verdicts -----
# (net, n_pred, unboxed_up, value_up, n_gold_none, moved, up, down) -> verdicts
_ALL = ("P2_net_rescues", "P3_unboxed_rescues", "P4_value_rescues", "P5_gold_unextractable", "P6_rank_moves",
        "P7_down_flips_rare")
FIX_V_CASES = [
    ((50, 10000, 100, 20, 1, 5, 100, 20), {k: True for k in _ALL}),
    ((49, 10000, 99, 19, 0, 4, 100, 21), {k: False for k in _ALL}),
    ((0, 0, 0, 0, 0, 0, 0, 0), {k: False for k in _ALL}),
]
