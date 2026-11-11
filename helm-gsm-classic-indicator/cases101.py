"""Audit 101: data source, gates, thresholds and hand-traced fixtures (all invented; none copied from HELM data).
Apache-2.0."""

from fractions import Fraction

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/classic/benchmark_output"
HELM_RELEASE = "v0.4.0"
PREFIX = "gsm:"
GROUP = "gsm"
CAP = 400  # max_tokens in HELM's GSM8K run spec
TOL_RUN = 1e-6
TOL_CELL = 1e-9
PLACES = 3
WORKERS = 4
PRINT_PER_CLASS = 8

G1 = "He has 3 + 4 = <<3+4=7>>7 apples. The answer is 7."
G2 = "2 * 500 = <<2*500=1000>>1000. The answer is 1000."

# (gold, prediction) -> (ind, fnem, corr, class)
FIX_GRADES = [
    ((G1, "3 + 4 = 7. The answer is 7."), (1, 1, 1, None)),
    ((G1, "The answer is 7"), (0, 1, 1, "no_period")),
    ((G1, "The answer is $7."), (0, 1, 1, "number_form")),
    ((G1, "The answer is 7 apples."), (0, 1, 1, "words_after")),
    ((G1, "The answer is 7.\nQ: Tom has 5 pens. How many?"), (0, 0, 1, "continued")),
    ((G1, "So she has 7."), (1, 1, 1, None)),
    ((G1, "So she has 7"), (0, 1, 1, "no_phrase")),
    ((G1, "The answer is 6. Wait, 7."), (1, 1, 0, "changed")),
    ((G1, ""), (0, 0, 0, None)),
    ((G1, "The answer is 8."), (0, 0, 0, None)),
    ((G2, "The answer is 1,000 apples, all told."), (0, 0, 1, "words_after")),
    ((G2, "The answer is 1,000."), (0, 1, 1, "number_form")),
    ((G1, "The answer is: 7."), (1, 1, 1, None)),
    ((G1, "The answer is seven. 3 + 4 = 7."), (1, 1, 1, None)),
    ((G1, "the answer is 7.0"), (0, 0, 1, "no_period")),
    ((G1, "The answer is -7."), (0, 0, 0, None)),
]
# predictions whose HELM final number is empty (#4337) -> True
FIX_LONE_COMMA = [
    ("The answer is 1,000 apples, all told.", True),
    ("The answer is 6. Wait, 7.", False),
    ("", False),
    ("no digits, here", False),
]

FIX_INSTANCES = [
    {"id": "id1", "split": "test", "references": [{"output": {"text": G1}, "tags": ["correct"]}]},
    {"id": "id2", "split": "test", "references": [{"output": {"text": G2}, "tags": ["correct"]}]},
    {"id": "id3", "split": "valid", "references": [{"output": {"text": G1}, "tags": ["correct"]}]},
]

FIX_PREDS = [
    {"instance_id": "id1", "train_trial_index": 0, "predicted_text": " The answer is 7.",
     "stats": {"exact_match_indicator": 1.0, "num_output_tokens": 5}},
    {"instance_id": "id1", "train_trial_index": 1, "predicted_text": " The answer is 7",
     "stats": {"exact_match_indicator": 0.0, "num_output_tokens": 400}},
    {"instance_id": "id2", "train_trial_index": 0, "predicted_text": " The answer is 1,000.",
     "stats": {"exact_match_indicator": 0.0, "num_output_tokens": 6}},
    {"instance_id": "id2", "train_trial_index": 1, "predicted_text": " The answer is 6. Wait, 1000.",
     "stats": {"exact_match_indicator": 1.0, "num_output_tokens": 10}},
    {"instance_id": "id3", "train_trial_index": 0, "predicted_text": " The answer is 7.",
     "stats": {"exact_match_indicator": 1.0}},
    {"instance_id": "id1", "train_trial_index": 0, "predicted_text": " x",
     "stats": {"exact_match_indicator": 0.0}},
    {"instance_id": "id2", "train_trial_index": 0, "predicted_text": " The answer is 1000.",
     "perturbation": {"name": "typo"}, "stats": {"exact_match_indicator": 1.0}},
    {"instance_id": "id2", "train_trial_index": 2, "predicted_text": " The answer is 1,000 apples, all told.",
     "stats": {}},
    {"instance_id": "id1", "train_trial_index": 2, "predicted_text": " So she has 8.",
     "stats": {"exact_match_indicator": 1.0, "num_output_tokens": 3}},
]

FIX_RUN = {
    "counts": {"n_records": 9, "perturbed": 1, "not_test": 1, "duplicate": 1, "kept": 6},
    "trials": {0: {"n": 2, "ind": 1, "fnem": 2, "corr": 2}, 1: {"n": 2, "ind": 1, "fnem": 2, "corr": 1},
               2: {"n": 2, "ind": 0, "fnem": 0, "corr": 1}},
    "stat_missing": 1,
    "stat_mismatch": 1,
    "classes": {"continued": 0, "words_after": 1, "no_period": 1, "number_form": 1, "no_phrase": 0},
    "under": 3,
    "over": 1,
    "fnem_gain": 2,
    "fnem_loss": 0,
    "lone_comma": 1,
    "cap_records": 1,
    "cap_under": 1,
}
FIX_RUN_KEYS = {"no_period": [("id1", 1)], "number_form": [("id2", 0)], "words_after": [("id2", 2)],
                "continued": [], "no_phrase": [], "changed": [("id2", 1)]}
FIX_RUN_MEANS = {"ind": Fraction(1, 3), "fnem": Fraction(2, 3), "corr": Fraction(2, 3)}

FIX_GROUP = [{"header": [{"value": "Model/adapter"}, {"value": "EM"}],
              "rows": [[{"value": "A"}, {"value": 0.5}], [{"value": "B"}, {"value": 0.25}], [{"value": "C"}]]}]
FIX_GROUP_VALUES = [0.5, 0.25]


def _base():
    return {"fixtures": True, "runs_listed": 60, "runs_included": 54, "cells_matched": 49, "ind_credits": 300,
            "under": 3, "over": 2, "max_rise": Fraction(1, 100), "movers": 5, "tau": 0.9,
            "under_classes": {"continued": 2, "words_after": 1, "no_period": 0, "number_form": 0, "no_phrase": 0}}


FIX_VERDICT_ON = _base()  # every prediction exactly on its boundary -> all HELD
FIX_VERDICT_PAST = dict(_base(), runs_included=53, ind_credits=301, over=3, max_rise=Fraction(99, 10000), movers=4,
                        tau=0.89, under_classes={"continued": 1, "words_after": 1, "no_period": 1, "number_form": 0,
                                                 "no_phrase": 0})
FIX_VERDICT_NONE = dict(_base(), cells_matched=48, ind_credits=0, under=0, over=0, max_rise=None, tau=None,
                        under_classes={c: 0 for c in ("continued", "words_after", "no_period", "number_form",
                                                      "no_phrase")})
