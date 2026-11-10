"""Data source, gates, stated expectations and hand-traced fixtures for the audit 99 follow-up. Apache-2.0."""

from fractions import Fraction

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/classic/benchmark_output"
HELM_RELEASE = "v0.4.0"
PREFIX = "synthetic_reasoning:"
GROUP = "synthetic_reasoning"
MODES = ("induction", "pattern_match", "variable_substitution")
WORKERS = 8
TOL_RUN = 1e-6
TOL_CELL = 1e-9

# Gate: this job must reproduce audit 99's published totals exactly (helm-synreason-operators-v1, 2026-11-10).
V1_TOTALS = {"em": 33282, "qem": 58270, "oa": 39125, "blind": 19145, "other_norm": 5843}
V1_RUNS = 207
V1_CELLS = 69

# Stated expectations (written before this job runs, after reading 10 of audit 99's 5,843 OA-but-not-exact credits,
# all from induction mode, all of which had the operators in the wrong places). Not blind pre-registrations.
EXPECT = {"E1_misplaced_share_of_other_norm": Fraction(1, 2), "E2_tau_published_vs_px": 0.8}
PLACES = 3
PRINT_PER_MODE_CLASS = 8

FIX_TOKENS = [
    ("Rule: X + Y = Z", ["rule", "x", "+", "y", "=", "z"]),
    ("The apple + a Pear", ["apple", "+", "pear"]),
    ("X+Y", ["x", "+", "y"]),
    ("ice-cream", ["ice", "-", "cream"]),
    (None, []),
]
# (gold, pred) -> (em, qem, oa, px, class)
FIX_GRADES_B = [
    (("X + Y = Y", " X + Y = Y"), (1, 1, 1, 1, "exact")),
    (("X + Y = Y", "x + y = y"), (0, 1, 1, 1, "format_only")),
    (("Rule: X Y + Z", "Rule: X + Y Z"), (0, 1, 1, 0, "ops_misplaced")),
    (("X + Y = Y", "X = Y + Y"), (0, 1, 0, 0, "ops_blind")),
    (("X + Y = Y", "X - Y = Z"), (0, 0, 0, 0, None)),
    (("X + Y = Y", "X + Y = Y."), (0, 1, 1, 1, "format_only")),
    (("apple + the pear", "apple + pear"), (0, 1, 1, 1, "format_only")),
    (("X + Y", ""), (0, 0, 0, 0, None)),
    (("Rule: X + Y = Z", "Rule: X + Y = Z ="), (0, 1, 0, 0, "ops_blind")),
]
FIX_MULTI_B = ((["A + B", "X + Y"], "x + y"), (0, 1, 1, 1, "format_only"))

FIX_INSTANCES_B = [
    {"id": "i1", "split": "test", "references": [{"output": {"text": "X + Y = Y"}, "tags": ["correct"]},
                                                 {"output": {"text": "X = Y"}, "tags": []}]},
    {"id": "i2", "split": "test", "references": [{"output": {"text": "Rule: X Y + Z"}, "tags": ["correct"]}]},
    {"id": "i3", "split": "valid", "references": [{"output": {"text": "X"}, "tags": ["correct"]}]},
]
FIX_PREDS_B = [
    {"instance_id": "i1", "train_trial_index": 0, "predicted_text": " X + Y = Y", "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "i1", "train_trial_index": 1, "predicted_text": " X = Y + Y", "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "i2", "train_trial_index": 0, "predicted_text": " Rule: X + Y Z",
     "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "i2", "train_trial_index": 1, "predicted_text": " rule: x y + z",
     "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "i3", "train_trial_index": 0, "predicted_text": " X", "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "i1", "train_trial_index": 0, "predicted_text": " nope", "stats": {"quasi_exact_match": 0.0}},
    {"instance_id": "i2", "train_trial_index": 0, "predicted_text": " Rule: X Y + Z", "perturbation": {"name": "p"},
     "stats": {"quasi_exact_match": 1.0}},
]
FIX_RUN_B = {
    "counts": {"n_records": 7, "perturbed": 1, "not_test": 1, "duplicate": 1, "kept": 4},
    "trials": {0: {"n": 2, "em": 1, "qem": 2, "oa": 2, "px": 1}, 1: {"n": 2, "em": 0, "qem": 2, "oa": 1, "px": 1}},
    "classes": {"exact": 1, "format_only": 1, "ops_misplaced": 1, "ops_blind": 1},
    "keys": {"format_only": [("i2", 1)], "ops_misplaced": [("i2", 0)], "ops_blind": [("i1", 1)]},
    "stat_missing": 0,
    "stat_mismatch": 0,
}
FIX_V1_TOTALS = {"em": 1, "qem": 4, "oa": 3, "blind": 1, "other_norm": 2}
FIX_PICK = [(([], "x"), None), ((["a", "b", "c"], "ab"), "b")]
