"""Constants, gates, thresholds and hand-traced fixtures for audit 90 (gsm8k-helm-scorer-regrade). Every fixture
expectation is traced by hand in test_grade90.py. Apache-2.0. Authored by AI agents working in the name of MV2,
Munim, Inc.
"""

from fractions import Fraction

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/lite/benchmark_output"
HELM_RELEASE = "v1.13.0"
HELM_PREFIX = "gsm:"
WORKERS = 6

# ----- Gates (P1) -----
EXPECTED_RUNS = 90                       # gsm: runs in HELM Lite v1.13.0 (audit 86 loaded 90)
MIN_PREDICTIONS = 990                    # a run must carry at least this many scored first-trial predictions
MIN_RUN_CONSISTENT = Fraction(99, 100)   # our transcription of H must equal HELM's recorded score on this share
MIN_ALL_CONSISTENT = Fraction(999, 1000)  # ... and on this share of all included predictions
MIN_INCLUDED = 85

# ----- Replication of HELM issue #4337 (reported, not a prediction): F vs H over all 90 runs -----
REPLICATION_4337 = {"up": 130, "down": 1}

# ----- Thresholds of P2-P6 -----
THRESHOLDS = {"P2_min_net": 900, "P3_min_decimal": 100, "P4_min_group": 5, "P5_min_models": 5, "P5_min_move": 5,
              "P6_ratio": 5}

# ----- The hand-read sample for P7 (graded next run, by reading) -----
SAMPLE_SEED = 90
SAMPLE_UP = 30
SAMPLE_DOWN = 15
P7_MIN_GENUINE = 27

# ----- Fixture 1: the four graders and the flip classes on fourteen outputs -----
# (gold, prediction, (h, f, n, a), helm_final, fixed_final, stated, source, class)
FIX_GRADE = [
    ("The answer is 18.", "So she makes 9 * 2 = 18 dollars.\n\nThe answer is 18.",
     (1, 1, 1, 1), "18", "18", "18", "phrase", None),
    ("The answer is 72.", "The answer is 72, in total, so the farmer earns that much.",
     (0, 1, 1, 1), "", "72", "72", "phrase", "comma_only"),
    ("The answer is 4.", "Counting the boxes: 3 4",
     (0, 1, 1, 1), "3 4", "4", "4", "last", "dot_merge"),
    ("The answer is 7.", "Total is $4.00 + $3.00 = $7.00.\n\nThe answer is \\$7.00.",
     (0, 0, 1, 1), "7.00", "7.00", "7.00", "phrase", "decimal_format"),
    ("The answer is 5.", "18R + 70 = 160, so R = 5. The answer is 5.\n\nQuestion: Tom has 3 apples and buys 4 more. "
     "How many? Answer: 3 + 4 = 7. The answer is 7.",
     (0, 0, 0, 1), "7", "7", "5", "phrase", "run_on"),
    ("The answer is 5.", "He makes 1/2.5 hours",
     (1, 0, 0, 0), "5", "2.5", "2.5", "last", "helm_regex_only"),
    ("The answer is 12.", "The answer is 10. Note: each box holds 12",
     (1, 1, 1, 0), "12", "12", "10", "phrase", "stated_differs"),
    ("The answer is 160000.", "Total likes:\n\\[ \\boxed{160,000} \\]",
     (1, 1, 1, 1), "160000", "160000", "160000", "boxed", None),
    ("The answer is 3.", "I am not sure.",
     (0, 0, 0, 0), "", "", "", "last", None),
    ("The answer is 1000.", "Therefore, the answer is 1000 people. Check: (2/5) * 5000 = 2000 people.",
     (0, 0, 0, 1), "2000", "2000", "1000", "phrase", "run_on"),
    ("The answer is 60.", "The answer is 60%.",
     (1, 1, 1, 1), "60", "60", "60", "phrase", None),
    ("The answer is 9.", "The answer is not obvious at first, but the answer is 9.",
     (1, 1, 1, 1), "9", "9", "9", "phrase", None),
    ("The answer is 18.", "The answer is \\(\\boxed{18}\\).",
     (1, 1, 1, 1), "18", "18", "18", "phrase", None),
    ("The answer is -3.", "So the change is -3 degrees. The answer is -3.",
     (1, 1, 1, 1), "-3", "-3", "-3", "phrase", None),
]

# ----- Fixture 2: numbers -----
FIX_TO_NUM = [("7.00", Fraction(7)), ("1,500", Fraction(1500)), ("-3", Fraction(-3)), ("2.5", Fraction(5, 2)),
              ("", None), ("3 4", None), ("1/2", Fraction(1, 2))]

# ----- Fixture 3: run selection (as audit 86) and the stop=none test -----
FIX_RUNS = {"gsm:model=a_x": "v1.0.0", "gsm:model=a_x,stop=none": "v1.4.0", "gsm:model=b_y": "v1.2.0",
            "gsm:model=b_y,stop=none": "v1.2.0", "mmlu:subject=x,model=a_x": "v1.0.0",
            "gsm:model=c_z,stop=none": "v1.10.0"}
FIX_RUNS_TARGET = ({"a_x": ("gsm:model=a_x,stop=none", "v1.4.0"), "b_y": ("gsm:model=b_y", "v1.2.0"),
                    "c_z": ("gsm:model=c_z,stop=none", "v1.10.0")}, 2)
FIX_STOP = [("gsm:model=a_x,stop=none", True), ("gsm:model=b_y", False), ("gsm:model=stop=none_q", False)]

# ----- Fixture 4: ranks and Kendall's tau-b -----
FIX_ACC = {"a": Fraction(9, 10), "b": Fraction(8, 10), "c": Fraction(8, 10), "d": Fraction(1, 2)}
FIX_RANKS = {"a": 1, "b": 2, "c": 2, "d": 4}
FIX_TAU = [([1, 2, 3], [1, 2, 3], 1.0), ([1, 2, 3], [3, 2, 1], -1.0), ([1, 1, 2], [1, 2, 3], 2 / 6 ** 0.5),
           ([1, 1, 1], [1, 2, 3], None)]

# ----- Fixture 5: verdicts -----
# (net, decimal_only, gain_stop, gain_other, moved, up, down) -> verdicts
FIX_V_CASES = [
    ((900, 100, (Fraction(36, 100), 36), (Fraction(54, 1000), 54), 5, 1000, 200),
     {"P2_net_rescues": True, "P3_decimal_rescues": True, "P4_stop_none_gains_more": True, "P5_rank_moves": True,
      "P6_down_flips_rare": True}),
    ((899, 99, (Fraction(4, 100), 4), (Fraction(54, 100), 54), 4, 1000, 201),
     {"P2_net_rescues": False, "P3_decimal_rescues": False, "P4_stop_none_gains_more": False, "P5_rank_moves": False,
      "P6_down_flips_rare": False}),
    ((1000, 150, (Fraction(5, 100), 5), (Fraction(6, 100), 6), 10, 0, 0),
     {"P2_net_rescues": True, "P3_decimal_rescues": True, "P4_stop_none_gains_more": False, "P5_rank_moves": True,
      "P6_down_flips_rare": False}),
]
