"""Audit 100: data source, gates, thresholds and hand-traced fixtures (all invented; none copied from HELM data).
Apache-2.0."""

from fractions import Fraction

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/classic/benchmark_output"
HELM_RELEASE = "v0.4.0"
PREFIX = "dyck_language"
GROUP = "dyck_language"
CAP = 5  # max_tokens in HELM's Dyck run spec
TOL_RUN = 1e-6
TOL_CELL = 1e-9
PLACES = 3
WORKERS = 8
PRINT_PER_CLASS = 8

# (gold, prediction) -> (ind, strict, lenient, class)
FIX_GRADES = [
    ((" ) ] }", ") ] }"), (1, 1, 1, None)),
    ((" ) ] }", "}"), (1, 0, 0, "missing_leading")),
    ((" ) ] }", "] ) }"), (1, 0, 0, "wrong_same_length")),
    ((" ] }", ") ] }"), (1, 0, 0, "extra_leading")),
    ((" ) ] }", "] }"), (1, 0, 0, "missing_leading")),
    ((" ) ] }", "( }"), (1, 0, 0, "other")),
    ((" ) ] }", ")]}"), (0, 1, 1, None)),
    ((" ) ] }", ") ] ]"), (0, 0, 0, None)),
    ((" }", ""), (0, 0, 0, None)),
    ((" }", "  }  "), (1, 1, 1, None)),
    ((" ) ] }", ") ] } )"), (0, 0, 0, None)),
    ((" ) }", ")  }"), (1, 1, 1, None)),
    ((" )", "so )"), (1, 0, 1, "format_only")),
    ((" ] )", "( ] ] )"), (1, 0, 0, "extra_leading")),
    ((" ] )", "( ] ) )"), (1, 0, 0, "other")),
]

FIX_INSTANCES = [
    {"id": "id1", "split": "test", "references": [{"output": {"text": " ) ] }"}, "tags": ["correct"]}]},
    {"id": "id2", "split": "test", "references": [{"output": {"text": " }"}, "tags": ["correct"]}]},
    {"id": "id3", "split": "valid", "references": [{"output": {"text": " )"}, "tags": ["correct"]}]},
    {"id": "id4", "split": "test", "references": [{"output": {"text": " ] )"}, "tags": ["correct"]}]},
]

FIX_PREDS = [
    {"instance_id": "id1", "train_trial_index": 0, "predicted_text": " ) ] }",
     "stats": {"exact_match_indicator": 1.0, "num_output_tokens": 3}},
    {"instance_id": "id1", "train_trial_index": 1, "predicted_text": " ] ] }",
     "stats": {"exact_match_indicator": 1.0, "num_output_tokens": 3}},
    {"instance_id": "id2", "train_trial_index": 0, "predicted_text": " }",
     "stats": {"exact_match_indicator": 1.0, "num_output_tokens": 1}},
    {"instance_id": "id2", "train_trial_index": 1, "predicted_text": " )}", "stats": {}},
    {"instance_id": "id4", "train_trial_index": 0, "predicted_text": " )",
     "stats": {"exact_match_indicator": 1.0, "num_output_tokens": 5}},
    {"instance_id": "id4", "train_trial_index": 1, "predicted_text": " ])",
     "stats": {"exact_match_indicator": 1.0, "num_output_tokens": 2}},
    {"instance_id": "id3", "train_trial_index": 0, "predicted_text": " )",
     "stats": {"exact_match_indicator": 1.0}},
    {"instance_id": "id1", "train_trial_index": 0, "predicted_text": " x",
     "stats": {"exact_match_indicator": 0.0}},
    {"instance_id": "id2", "train_trial_index": 0, "predicted_text": " }", "perturbation": {"name": "typo"},
     "stats": {"exact_match_indicator": 1.0}},
]

FIX_RUN = {
    "counts": {"n_records": 9, "perturbed": 1, "not_test": 1, "duplicate": 1, "kept": 6},
    "trials": {0: {"n": 3, "ind": 3, "strict": 2, "lenient": 2}, 1: {"n": 3, "ind": 1, "strict": 1, "lenient": 1}},
    "stat_missing": 1,
    "stat_mismatch": 1,
    "classes": {"format_only": 0, "missing_leading": 1, "extra_leading": 0, "wrong_same_length": 1, "other": 0},
    "by_depth": {3: {"records": 2, "ind": 2, "strict": 1, "lenient": 1, "wrong": 1},
                 1: {"records": 2, "ind": 1, "strict": 1, "lenient": 1, "wrong": 0},
                 2: {"records": 2, "ind": 1, "strict": 1, "lenient": 1, "wrong": 1}},
    "under": 1,
    "cap_records": 1,
    "cap_wrong": 1,
}
FIX_RUN_KEYS = {"missing_leading": [("id4", 0)], "wrong_same_length": [("id1", 1)], "under": [("id4", 1)],
                "format_only": [], "extra_leading": [], "other": []}
FIX_RUN_MEANS = {"ind": Fraction(2, 3), "strict": Fraction(1, 2), "lenient": Fraction(1, 2)}

FIX_GROUP = [{"header": [{"value": "Model/adapter"}, {"value": "EM"}],
              "rows": [[{"value": "A"}, {"value": 0.5}], [{"value": "B"}, {"value": 0.25}], [{"value": "C"}]]}]
FIX_GROUP_VALUES = [0.5, 0.25]


def _base():
    return {"fixtures": True, "runs_listed": 60, "runs_included": 54, "cells_matched": 49, "ind_credits": 100,
            "wrong": 5, "by_depth": {2: {"ind": 10, "wrong": 1}, 3: {"ind": 10, "wrong": 2}},
            "max_fall": Fraction(1, 20), "movers": 5, "tau": 0.8, "missing_leading": 2}


FIX_VERDICT_ON = _base()  # every prediction exactly on its boundary -> all HELD
FIX_VERDICT_PAST = dict(_base(), runs_included=53, wrong=4, by_depth={2: {"ind": 10, "wrong": 2},
                                                                      3: {"ind": 10, "wrong": 2}},
                        max_fall=Fraction(49, 1000), movers=4, tau=0.79, missing_leading=2)
FIX_VERDICT_NONE = dict(_base(), cells_matched=48, ind_credits=0, wrong=0, by_depth={}, max_fall=None, tau=None,
                        missing_leading=0)
