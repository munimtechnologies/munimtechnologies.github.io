"""Data source, gates, thresholds and hand-traced fixtures for audit 96 (medcalc-helm-scorer-regrade). Apache-2.0."""

from fractions import Fraction as F

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/medhelm/benchmark_output"
HELM_RELEASE = "v4.0.0"
PREFIX = "medcalc_bench:"
METRIC = "medcalc_bench_accuracy"
WORKERS = 4

# Gates: a run is included when it has scored predictions, at most 1% of its first-trial predictions lack an
# instance with a reference, it scores at least 95% of the median run's count, every scored prediction carries
# HELM's metric, and our H equals HELM's on at least 99% of them. P1 also needs at least 12 included models and
# H == HELM on at least 99.9% of all included predictions.
MAX_RUN_NO_GOLD = F(1, 100)
MIN_RUN_SCORED_VS_MEDIAN = F(95, 100)
MIN_RUN_CONSISTENT = F(99, 100)
MIN_MODELS = 12
MIN_ALL_CONSISTENT = F(999, 1000)
SAMPLE_PER_CLASS = 10

THRESHOLDS = {"P3_mean": F(1, 20), "P3_min": F(1, 50), "P4_lo": 120, "P4_hi": 175, "P5_num": 1, "P5_den": 100,
              "P6_min": 3, "P7_share": F(1, 10), "P7_min": 3}

LIM = {"lower_limit": "287.8766", "upper_limit": "318.1794"}
PHY = {"lower_limit": "4.75", "upper_limit": "5.25"}
DUR = "('18 weeks', '1 days')"
DURL = {"lower_limit": DUR, "upper_limit": DUR}
DATE = {"lower_limit": "12/04/2020", "upper_limit": "12/04/2020"}
NINE = {"lower_limit": "9", "upper_limit": "9"}

# (predicted_text, reference, extra, category, HELM's score)
FIX_HELM = [
    ("303", "303.03", LIM, "physical", 1),
    ("303", "303.03", LIM, "lab", 0),                       # #4351: lab is not a supported category
    ("303", "303.03", LIM, "dosage", 0),                    # #4351: nor is dosage
    (" 9\n", "9", NINE, "risk", 1),                         # the output is stripped
    ("9.0", "9", NINE, "risk", 0),                          # exact string match only
    (DUR, DUR, DURL, "date", 1),
    ("(18, 1)", DUR, DURL, "date", 0),                      # #4365: only the quoted plural form parses
    (DUR + " exactly", DUR, DURL, "date", 1),               # re.match is not anchored at the end
    ("12/04/2020", "12/04/2020", DATE, "date", 1),
    ("12/4/2020", "12/04/2020", DATE, "date", 1),           # strptime accepts a one-digit day
    ("abc", "5.0", PHY, "physical", 0),                     # ValueError -> 0
    ("5 mg", "5.0", PHY, "physical", 0),
    ("4.75", "5.0", PHY, "physical", 1),                    # limits are inclusive
]

# (predicted_text, reference, extra, category, H, R, C, class)
FIX_GRADE = [
    ("303", "303.03", LIM, "lab", 0, 1, 1, "range_lab"),
    ("303", "303.03", LIM, "dosage", 0, 1, 1, "range_dosage"),
    ("250", "303.03", LIM, "lab", 0, 0, 0, None),
    ("303 mg", "303.03", LIM, "lab", 0, 0, 0, None),
    ("303", "303.03", LIM, "physical", 1, 1, 1, None),
    ("(18, 1)", DUR, DURL, "date", 0, 0, 1, "duration_format"),
    ("(18 weeks, 1 day)", DUR, DURL, "date", 0, 0, 1, "duration_format"),
    ("('18 weeks', '1 day')", DUR, DURL, "date", 0, 0, 1, "duration_format"),
    ("(18, 2)", DUR, DURL, "date", 0, 0, 0, None),
    ("(18 weeks, 1)", DUR, DURL, "date", 0, 0, 0, None),    # one part labelled, one not: ambiguous
    ("18 weeks and 1 day", DUR, DURL, "date", 0, 0, 0, None),
    ("9.0", "9", NINE, "risk", 0, 0, 1, "same_value"),
    ("9.4", "9", NINE, "risk", 0, 0, 0, None),              # rounding is not in C
    ("9", "9", NINE, "risk", 1, 1, 1, None),
    ("nine", "9", NINE, "risk", 0, 0, 0, None),
    ("4.50", "4.5", {"lower_limit": "4.5", "upper_limit": "4.5"}, "severity", 0, 0, 1, "same_value"),
    ("nan", "NaN", NINE, "diagnosis", 0, 0, 0, None),       # not finite: never the same value
]

# (predicted_text, reference, rounded_only)
FIX_ROUND = [("9.4", "9", 1), ("9.6", "9", 0), ("9", "9", 0), ("9.4", "9.5", 0), ("x", "9", 0)]

# (predicted_text, total days or None)
FIX_DAYS = [("(18, 1)", 127), (" ( '2 weeks' , '3 days' ) ", 17), ('("2 week", "3 day")', 17), ("('2 weeks', 3)", None),
            ("('2 weeks\", '3 days')", None), ("(2, 3, 4)", None), ("2, 3", None)]

FIX_RUNS = {
    "medcalc_bench:model=a_x,model_deployment=s_x": "v4.0.0",
    "medcalc_bench:num_output_tokens=4000,model=b_y,model_deployment=s_y": "v4.0.0",
    "med_qa:model=a_x": "v4.0.0",
    "medcalc_bench:model=a_x,model_deployment=s_x,extra=1": "v3.0.0",
}
FIX_RUNS_TARGET = ({("a_x", "-"): ("medcalc_bench:model=a_x,model_deployment=s_x", "v4.0.0"),
                    ("b_y", "-"): ("medcalc_bench:num_output_tokens=4000,model=b_y,model_deployment=s_y", "v4.0.0")},
                   1)

FIX_ACC = {"a": F(1, 2), "b": F(1, 2), "c": F(1, 4)}
FIX_RANKS = {"a": 1, "b": 1, "c": 3}
FIX_TAU = [([1, 2, 3], [1, 2, 3], 1.0), ([1, 2, 3], [3, 2, 1], -1.0), ([1, 2, 3], [1, 3, 2], 1 / 3),
           ([1, 1, 1], [1, 2, 3], None)]

ALL_P = ("P2_lab_dosage_zero", "P3_range_fix_size", "P4_duration_replicates", "P5_same_value_rare",
         "P6_ranks_change", "P7_format_loss")


def _v(*held):
    return {k: (k in held) for k in ALL_P}


# (args to predictions96 without th, expected verdicts)
FIX_V_CASES = [
    ((0, [F(1, 10), F(1, 20)], 148, 10, 4719, 3, 3), _v(*ALL_P)),
    ((1, [F(1, 20), F(1, 50)], 119, 48, 4719, 2, 2), _v()),
    ((0, [F(1, 20), F(1, 20)], 175, 47, 4719, 3, 3), _v(*ALL_P)),
    ((0, [F(1, 10), F(1, 100)], 120, 0, 4719, 0, 0), _v("P2_lab_dosage_zero", "P4_duration_replicates",
                                                        "P5_same_value_rare")),
]
