"""Audit 99: data source, gates, thresholds and the hand-traced fixtures (traces in test_grade99.py). Apache-2.0."""

from fractions import Fraction

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/classic/benchmark_output"
HELM_RELEASE = "v0.4.0"  # HELM Classic's latest release (checked 2026-11-10)
PREFIX = "synthetic_reasoning:"  # not synthetic_reasoning_natural (its main metric is f1_set_match)
GROUP = "synthetic_reasoning"  # group page releases/v0.4.0/groups/synthetic_reasoning.json, column "EM"
MODES = ("induction", "pattern_match", "variable_substitution")
WORKERS = 8

# Gates
TOL_RUN = 1e-6    # |our run mean - stats.json test mean| for quasi_exact_match and exact_match
TOL_CELL = 1e-9   # |our model cell - a published EM cell|
MIN_RUNS = 200
MIN_RUNS_INCLUDED = Fraction(90, 100)
MIN_CELLS_MATCHED = Fraction(90, 100)
ABORT_RUNS_INCLUDED = Fraction(1, 2)

THRESHOLDS = {"P2_share": Fraction(1, 20), "P4_fall": Fraction(1, 20), "P5_movers": 5, "P5_places": 3,
              "P6_tau": 0.8, "P7_share": Fraction(1, 2)}
PRINT_BLIND = 40
PRINT_OTHER = 10

# ---- Fixtures ----
# (gold, pred) -> (em, qem, oa, class)
FIX_GRADES = [
    (("X + Y = Y", "X + Y = Y"), (1, 1, 1, None)),
    (("X + Y = Y", "X = Y + Y"), (0, 1, 0, "ops_reordered")),
    (("X + Y = Y", "X Y Y"), (0, 1, 0, "ops_missing")),
    (("X + Y = Y", "X - Y = Y"), (0, 1, 0, "ops_other")),
    (("X + Y = Y", "x + y = y"), (0, 1, 1, None)),
    (("X + Y = Y", "X + Z = Y"), (0, 0, 0, None)),
    (("X + Y = Y", "   "), (0, 0, 0, None)),
    (("Rule: X * Y", "Rule: X * Y."), (0, 1, 1, None)),
    (("lion apple + kiwi = kiwi", "lion apple + kiwi = kiwi"), (1, 1, 1, None)),
    (("X + Y = Y", " X + Y = Y "), (1, 1, 1, None)),
    (("X - Y", "X-Y"), (0, 0, 0, None)),
    (("X = Y", "X == Y"), (0, 1, 0, "ops_other")),
]
FIX_MULTI = ((["A + B", "X + Y"], "X - Y"), (0, 1, 0, "ops_other"))
FIX_NORMALIZE = [("X + Y = Y", "x y y"), ("A + B", "b"), ("Rule: X * Y", "rule x y"), ("X-Y", "xy")]
FIX_MODEL_MODE = [
    ("synthetic_reasoning:mode=induction,model=together_ul2,stop=hash,global_prefix=nlg", "together_ul2", "induction"),
    ("synthetic_reasoning:mode=pattern_match,model=openai_text-davinci-003", "openai_text-davinci-003",
     "pattern_match"),
    ("nothing", "", ""),
]
FIX_SUITES = {"synthetic_reasoning:mode=a,model=m": "v0.3.0",
              "synthetic_reasoning_natural:difficulty=easy,model=m": "v0.3.0",
              "boolq:model=m": "v0.2.0"}
FIX_SUITES_OUT = {"synthetic_reasoning:mode=a,model=m": "v0.3.0"}
FIX_INSTANCES = [
    {"id": "i1", "split": "test", "references": [{"output": {"text": "X + Y = Y"}, "tags": ["correct"]},
                                                 {"output": {"text": "Y = X"}, "tags": []}]},
    {"id": "i2", "split": "test", "references": [{"output": {"text": "Rule: X * Y"}, "tags": ["correct"]}]},
    {"id": "v1", "split": "valid", "references": [{"output": {"text": "Z"}, "tags": ["correct"]}]},
]
FIX_PREDS = [
    {"instance_id": "i1", "train_trial_index": 0, "predicted_text": " X + Y = Y", "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "i2", "train_trial_index": 0, "predicted_text": "Rule: X = Y", "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "i1", "train_trial_index": 1, "predicted_text": "X = Y + Y", "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "i2", "train_trial_index": 1, "predicted_text": "rule: x * y", "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "i1", "train_trial_index": 1, "predicted_text": "dup", "stats": {"quasi_exact_match": 0.0}},
    {"instance_id": "v1", "train_trial_index": 0, "predicted_text": "Z", "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "i1", "train_trial_index": 2, "predicted_text": "X + Z = Y", "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "i2", "train_trial_index": 2, "predicted_text": "Rule: X * Y", "perturbation": {"name": "typos"},
     "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "i2", "train_trial_index": 2, "predicted_text": None, "stats": {}},
    "junk",
]
FIX_RUN_TARGET = {
    "counts": {"n_records": 9, "perturbed": 1, "not_test": 1, "duplicate": 1, "kept": 6},
    "trials": {0: {"n": 2, "em": 1, "qem": 2, "oa": 1}, 1: {"n": 2, "em": 0, "qem": 2, "oa": 1},
               2: {"n": 2, "em": 0, "qem": 0, "oa": 0}},
    "stat_missing": 1, "stat_mismatch": 1,
    "blind": [("i2", 0, "ops_other"), ("i1", 1, "ops_reordered")],
    "classes": {"ops_missing": 0, "ops_reordered": 1, "ops_other": 1},
    "other_norm": [("i2", 1)],
    "qem_not_em": 3,
}
FIX_RUN_MEANS = {"qem": Fraction(2, 3), "oa": Fraction(1, 3), "em": Fraction(1, 6)}
FIX_CELL = ([{0: {"n": 2, "qem": 2}, 1: {"n": 2, "qem": 1}}, {0: {"n": 4, "qem": 1}}], Fraction(7, 12))
FIX_STATS = [
    {"name": {"name": "quasi_exact_match", "split": "test", "perturbation": {"name": "robustness"}},
     "count": 3, "sum": 0.9, "mean": 0.3},
    {"name": {"name": "quasi_exact_match", "split": "valid"}, "count": 3, "sum": 1.2, "mean": 0.4},
    {"name": {"name": "quasi_exact_match", "split": "test"}, "count": 3, "sum": 1.5, "mean": 0.5},
    "junk",
]
FIX_STAT_TARGET = {"quasi_exact_match": {"count": 3, "sum": 1.5, "mean": 0.5}, "exact_match": None}
FIX_RANKS_IN = {"a": Fraction(1, 2), "b": Fraction(1, 3), "c": Fraction(1, 2), "d": Fraction(3, 4)}
FIX_RANKS_OUT = {"d": 1, "a": 2, "c": 2, "b": 4}
FIX_TAU = [(([1, 2, 3, 4], [1, 3, 2, 4]), 4 / 6), (([1, 1, 2], [1, 2, 2]), 0.5), (([1, 1], [1, 2]), None)]
FIX_GROUP = [{"title": "Synthetic reasoning (abstract symbols)",
              "header": [{"value": "Model/adapter"}, {"value": "EM"}, {"value": "# eval"}],
              "rows": [[{"value": "M1"}, {"value": 0.25}, {"value": 1}],
                       [{"value": "M2"}, {"value": None}, {"value": 1}],
                       [{"value": "M3"}, {"value": 0.5}, {"value": 1}]]}]
FIX_GROUP_VALUES = [0.25, 0.5]
FIX_GROUP_NO_COL = [{"header": [{"value": "Model/adapter"}, {"value": "F1"}], "rows": []}]
FIX_MATCH = (({"a": 0.25, "b": 0.5, "c": 0.7}, [0.5, 0.25000000001, 0.9], 1e-9), 2)
# predictions99(blind, credits, mode_shares, max_fall, movers3, tau, qem_not_em)
FIX_V_CASES = [
    ((5, 100, {"pattern_match": (3, 10), "induction": (1, 10), "variable_substitution": (1, 80)}, Fraction(1, 20),
      5, 0.8, 10),
     {"P2_blind_credits": True, "P3_pattern_match_most": True, "P4_cell_falls": True, "P5_rank_movers": True,
      "P6_order_kept": True, "P7_gap_mostly_operators": True}),
    ((4, 100, {"pattern_match": (1, 10), "induction": (1, 10), "variable_substitution": (0, 80)},
      Fraction(49, 1000), 4, 0.79, 9),
     {"P2_blind_credits": False, "P3_pattern_match_most": False, "P4_cell_falls": False, "P5_rank_movers": False,
      "P6_order_kept": False, "P7_gap_mostly_operators": False}),
    ((0, 0, {}, None, 0, None, 0),
     {"P2_blind_credits": False, "P3_pattern_match_most": False, "P4_cell_falls": False, "P5_rank_movers": False,
      "P6_order_kept": False, "P7_gap_mostly_operators": False}),
]
