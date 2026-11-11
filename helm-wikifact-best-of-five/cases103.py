"""Audit 103: data source, gates, thresholds and hand-traced fixtures (all invented; none copied from HELM data).
Apache-2.0."""

from fractions import Fraction

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/classic/benchmark_output"
HELM_RELEASE = "v0.4.0"
GROUP = "wikifact"
COLUMN = "EM"
TOL_RUN = 1e-6
TOL_CELL = 1e-9
PLACES = 3
WORKERS = 3
PRINT_PER_CLASS = 8
KEYS_PER_RUN = 20

# quasi_exact_match: (gold, prediction) -> score
FIX_QEM = [
    (("The Beatles", "beatles"), 1),
    (("U.S.", "US"), 1),
    (("Paris", ""), 0),
    (("Paris", "Paris, France"), 0),
    (("New York", "new  york."), 1),
    (("A", "the"), 1),  # both normalise to the empty string
]

COMPS_A = [(" London", -3.0), (" Paris", -1.0), (" Paris.", -1.5), (" Rome", -4.0), (" London", -3.0)]
COMPS_B = [(" Rome", 0.0), (" Paris", 0.0), (" Paris", 0.0), (" Paris", 0.0), (" Paris", 0.0)]
COMPS_C = [(" paris", -1.2)] * 5
COMPS_D = [(" Rome", -2.0), (" Paris", -1.0), (" Lyon", -1.0)]
COMPS_E = [(" Paris", -5.0), (" Rome", -1.0)]

# score_record: (golds, completions) -> result
FIX_RECORD = [
    ((["Paris"], COMPS_A), {"n": 5, "h": 1, "f": 0, "q_sum": 2, "k": 1, "top": 1, "distinct": 4,
                            "zero_lp": False, "equal_lp": False}),
    ((["Paris"], COMPS_B), {"n": 5, "h": 0, "f": 0, "q_sum": 4, "k": 1, "top": 0, "distinct": 2,
                            "zero_lp": True, "equal_lp": True}),
    ((["Paris", "Paris, France"], COMPS_C), {"n": 5, "h": 1, "f": 1, "q_sum": 5, "k": 1, "top": 0, "distinct": 1,
                                             "zero_lp": False, "equal_lp": True}),
    ((["Lyon"], COMPS_D), {"n": 3, "h": 0, "f": 0, "q_sum": 1, "k": 1, "top": 1, "distinct": 3,
                           "zero_lp": False, "equal_lp": False}),
    (([], [(" x", 0.0)]), None),
    ((["x"], []), None),
]

FIX_COMPLETIONS = [
    ({"result": {"completions": [{"text": " a", "logprob": -1.5}, {"text": " b"}, "junk",
                                 {"text": " c", "logprob": True}]}}, [(" a", -1.5), (" b", 0.0), (" c", 0.0)]),
    ({"result": None}, []),
]
FIX_GOLDS = ({"references": [{"output": {"text": "x"}, "tags": ["correct"]}, {"output": {"text": "y"}, "tags": []},
                             {"tags": ["correct"]}]}, ["x", ""])


def _ref(t):
    return {"output": {"text": t}, "tags": ["correct"]}


def _rs(iid, split, trial, golds, comps, perturbation=None, no_result=False):
    inst = {"id": iid, "split": split, "references": [_ref(g) for g in golds]}
    if perturbation is not None:
        inst["perturbation"] = perturbation
    result = None if no_result else {"completions": [{"text": t, "logprob": lp} for t, lp in comps]}
    return {"instance": inst, "train_trial_index": trial, "result": result}


FIX_STATE = {"request_states": [
    _rs("id1", "test", 0, ["Paris"], COMPS_A),
    _rs("id6", "test", 1, ["Paris", "Paris, France"], COMPS_C),
    _rs("id2", "test", 0, ["Paris"], COMPS_B),
    _rs("id3", "valid", 0, ["Paris"], COMPS_A),
    _rs("id1", "test", 0, ["Paris"], COMPS_B),
    _rs("id2", "test", 1, ["Paris"], COMPS_B, perturbation={"name": "typos"}),
    _rs("id2", "test", 1, ["Paris"], [], no_result=True),
    _rs("id4", "test", 1, ["Lyon"], COMPS_D),
    _rs("id5", "test", 0, ["Paris"], COMPS_E),
]}
FIX_PREDS = [
    {"instance_id": "id1", "train_trial_index": 0, "predicted_text": " London", "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "id6", "train_trial_index": 1, "predicted_text": " paris", "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "id2", "train_trial_index": 0, "predicted_text": " Rome", "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "id4", "train_trial_index": 1, "predicted_text": " Paris", "stats": {}},
    {"instance_id": "id5", "train_trial_index": 0, "predicted_text": " Paris", "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "id3", "train_trial_index": 0, "predicted_text": " London", "stats": {"quasi_exact_match": 0.0}},
    {"instance_id": "id2", "train_trial_index": 1, "perturbation": {"name": "typos"}, "predicted_text": "x",
     "stats": {"quasi_exact_match": 0.0}},
    {"instance_id": "id1", "train_trial_index": 0, "predicted_text": "dup", "stats": {"quasi_exact_match": 0.0}},
]
FIX_RUN = {
    "counts": {"request_states": 9, "perturbed": 1, "not_test": 1, "duplicate": 1, "no_result": 1, "kept": 5},
    "trials": {0: {"n": 3, "h": 1, "f": 1, "m": Fraction(17, 10), "k": 3},
               1: {"n": 2, "h": 1, "f": 1, "m": Fraction(4, 3), "k": 2}},
    "rec": {"n5": 3, "collapsed": 1, "zero_lp": 1, "equal_lp": 2, "top_not_first": 3, "display_disagree": 2},
    "stat_missing": 1,
    "stat_mismatch": 2,
    "stored_eq_first": 1,
    "shown_mismatch": 1,
    "shown_missing": 0,
    "disagree_keys": [("id1", 0), ("id5", 0)],
}
FIX_MEANS = {"h": Fraction(5, 12), "f": Fraction(5, 12), "m": Fraction(37, 60), "k": Fraction(1)}
FIX_RUN_CLASS_OF_FIXTURE = "ranked"

FIX_RUN_CLASS = [
    (({"zero_lp": 9, "collapsed": 0}, 10), "zero_logprob"),
    (({"zero_lp": 10, "collapsed": 10}, 10), "zero_logprob"),
    (({"zero_lp": 0, "collapsed": 9}, 10), "collapsed"),
    (({"zero_lp": 8, "collapsed": 8}, 10), "ranked"),
    (({"zero_lp": 0, "collapsed": 0}, 0), None),
]
FIX_ADAPTER_CLASS = [(["ranked", "ranked"], "ranked"), (["ranked", "collapsed"], "mixed"), ([], None)]

R1 = "wikifact:k=5,subject=plaintiff,model=openai_text-davinci-003"
R2 = "wikifact:k=5,subject=part_of,model=together_ul2,stop=hash,global_prefix=nlg"
R3 = "wikifact:k=1,subject=plaintiff,model=x"
R4 = "math:subject=algebra,model=x"
FIX_NAMES = {
    "k5": [(R1, True), (R2, True), (R3, False), (R4, False)],
    "subject": [(R1, "plaintiff"), (R2, "part_of"), ("wikifact:k=5,model=x", None)],
    "adapter": [(R1, "wikifact:k=5,model=openai_text-davinci-003"),
                (R2, "wikifact:k=5,model=together_ul2,stop=hash,global_prefix=nlg")],
    "model": [(R2, "together_ul2,stop=hash,global_prefix=nlg"), ("gsm:x", "")],
}
FIX_SUITES = {R1: "v0.3.0", R2: "v0.3.0", R3: "v0.3.0", R4: "v0.3.0"}
FIX_SELECT = {R1: "v0.3.0", R2: "v0.3.0"}

FIX_CELL_RUNS = {
    "x1": {"adapter": "X", "trials": {0: {"n": 2, "h": 1, "f": 0, "m": Fraction(1, 2), "k": 1}}},
    "x2": {"adapter": "X", "trials": {0: {"n": 1, "h": 0, "f": 1, "m": Fraction(1), "k": 1}}},
    "y1": {"adapter": "Y", "trials": {0: {"n": 1, "h": 1, "f": 1, "m": Fraction(1), "k": 1}}},
}
FIX_CELL_LISTED = {"X": ["x1", "x2"], "Y": ["y1", "y2"]}
FIX_CELLS = {"X": {"h": Fraction(1, 4), "f": Fraction(1, 2), "m": Fraction(5, 8), "k": Fraction(3, 4), "runs": 2}}

FIX_MEDIAN = [([3, 1, 2], 2), ([4, 1, 3, 2], 2.5), ([], None)]
FIX_RANKS = ({"a": 3, "b": 5, "c": 3}, {"a": 2, "b": 1, "c": 2})
FIX_TAU = [(([1, 2, 3], [1, 3, 2]), 1.0 / 3.0), (([1, 1, 2], [1, 2, 2]), 0.5), (([1, 1], [1, 2]), None)]
FIX_MATCH = ({"a": 0.5, "b": 0.25000000001, "c": 0.1}, [0.25, 0.5, 0.5], 2)
FIX_GROUP = [{"header": [{"value": "Model/adapter"}, {"value": "EM"}, {"value": "EM@5"}],
              "rows": [[{"value": "A"}, {"value": 0.5}, {"value": 0.6}], [{"value": "B"}, {"value": 0.25},
                                                                             {"value": 0.3}], [{"value": "C"}]]}]
FIX_GROUP_VALUES = [0.5, 0.25]
FIX_GROUP_NO_COLUMN = [{"header": [{"value": "Model/adapter"}, {"value": "EM@5"}], "rows": []}]


def _base():
    return {"fixtures": True, "runs_listed": 100, "runs_included": 90, "cells": 60, "matched": 54,
            "unranked_adapters": 4, "ranked_n": 1000, "ranked_h": 520, "ranked_m": Fraction(500),
            "ranked_bonus_median": 0.02, "unranked_bonus_median": 0.0, "movers": 5, "tau": 0.9,
            "ranked_disagree": 50, "unranked_rise_or_stay": 3}


FIX_VERDICT_ON = _base()  # every prediction exactly on its boundary -> all HELD
FIX_VERDICT_PAST = dict(_base(), runs_included=89, unranked_adapters=3, ranked_h=519, ranked_bonus_median=0.0,
                        movers=4, tau=0.89, ranked_disagree=49, unranked_rise_or_stay=2)
