"""Audit 104: data source, thresholds and hand-traced fixtures (all invented). Apache-2.0."""

import math

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/classic/benchmark_output"
HELM_RELEASE = "v0.4.0"
GROUP = "boolq"
COLUMN = "ECE (10-bin)"
NUM_BINS = 10
TOL_RUN = 1e-9
TOL_CELL = 1e-9
PLACES = 3
DELTA = 0.02
EXCESS = -0.1
WORKERS = 2
PRINT_PER_CLASS = 4

e = math.exp

# ----- Token decoding and stop trimming -----
FIX_BYTES = [("Ċ", b"\n"), ("ĠYes", b" Yes"), ("▁Yes", b" Yes"), ("<0x0A>", b"\n"),
             ("<|newline|>", b"\n"), (" No", b" No"), ("\n", b"\n"), ("", b"")]
FIX_DECODE = [(["ĠYes", "Ċ", "Ċ", "Pass"], " Yes\n\nPass"), ([], "")]
FIX_KEEP = [
    ((["ĠYes", "Ċ", "Ċ", "Pass", "age"], ["\n"]), 1),
    ((["ĠNo"], ["\n"]), 1),
    ((["Ċ", "ĠYes"], ["\n"]), 0),
    ((["▁Yes", "<0x0A>", "▁Pass"], ["\n"]), 1),
    (([" Yes", "<|newline|>"], ["\n"]), 1),
    ((["Ġ#", "##", "ĠNo"], ["###"]), 1),
    ((["ĠYes", "Ċ"], []), 2),
    (([], ["\n"]), 0),
]
FIX_EM = [(("Yes", "Yes"), 1), (("Yes", " Yes "), 1), (("Yes", "yes"), 0), (("Yes", ""), 0)]


def comp(text, lp, toks):
    return {"text": text, "logprob": lp, "tokens": list(toks)}


C1 = comp(" Yes", -1.0, [("ĠYes", -0.25), ("Ċ", -0.125), ("Ċ", -0.125), ("Pass", -0.25),
                         ("age", -0.25)])
C2 = comp(" Yes", -0.5, [("ĠYes", -0.5)])
C3 = comp("", -2.0, [("Ċ", -1.0), ("ĠYes", -1.0)])
C4 = comp(" Yes", -0.75, [("▁Yes", -0.5), ("<0x0A>", -0.25)])
C7 = comp(" Yes", -0.5, [("ĠNo", -0.25), ("Ċ", -0.25)])
NL = ["\n"]

FIX_RECORD = [
    ((["Yes"], C1, NL), {"em": 1, "p": e(-1.0), "t": e(-0.25), "overrun": True, "excess": -0.75,
                         "consistent": True, "kept": 1, "n_tokens": 5}),
    ((["No"], C2, NL), {"em": 0, "p": e(-0.5), "t": e(-0.5), "overrun": False, "excess": 0.0,
                        "consistent": True, "kept": 1, "n_tokens": 1}),
    ((["Yes"], C3, NL), {"em": 0, "p": e(-2.0), "t": 1.0, "overrun": True, "excess": -2.0,
                         "consistent": True, "kept": 0, "n_tokens": 2}),
    ((["Yes"], C4, NL), {"em": 1, "p": e(-0.75), "t": e(-0.5), "overrun": True, "excess": -0.25,
                         "consistent": True, "kept": 1, "n_tokens": 2}),
    ((["Yes"], C7, NL), {"em": 1, "p": e(-0.5), "t": e(-0.25), "overrun": True, "excess": -0.25,
                         "consistent": False, "kept": 1, "n_tokens": 2}),
    (([], C2, NL), None),
    ((["Yes"], None, NL), None),
]


def _raw(c):
    return {"text": c["text"], "logprob": c["logprob"], "tokens": [{"text": t, "logprob": lp} for t, lp in c["tokens"]]}


FIX_TOP = [
    ({"result": {"completions": [{"text": "a", "logprob": -2.0, "tokens": [{"text": "a", "logprob": -2.0}]},
                                 {"text": "b", "logprob": -1.0, "tokens": [{"text": "b"}]}]}},
     {"text": "b", "logprob": -1.0, "tokens": [("b", 0.0)]}),
    ({"result": {"completions": []}}, None),
    ({}, None),
]


def rs(iid, trial, split, golds, c, pert=None):
    refs = [{"output": {"text": "Yes"}, "tags": ["correct"] if "Yes" in golds else []},
            {"output": {"text": "No"}, "tags": ["correct"] if "No" in golds else []}]
    out = {"instance": {"id": iid, "split": split, "references": refs}, "train_trial_index": trial,
           "result": {"completions": [] if c is None else [_raw(c)]}}
    if pert is not None:
        out["instance"]["perturbation"] = pert
    return out


FIX_STATE = {"adapter_spec": {"stop_sequences": ["\n"]}, "request_states": [
    rs("id1", 0, "valid", ["Yes"], C1),
    rs("id2", 0, "valid", ["No"], C2),
    rs("id1", 1, "valid", ["Yes"], C4),
    rs("id3", 1, "valid", ["Yes"], C7),
    rs("id1", 0, "valid", ["Yes"], C2),
    rs("id2", 1, "valid", ["No"], C2, pert={"name": "mild_mix"}),
    rs("id4", 0, "train", ["Yes"], C2),
    rs("id5", 1, "valid", ["Yes"], None),
]}
FIX_RUN = {
    "counts": {"request_states": 8, "perturbed": 1, "not_eval": 1, "duplicate": 1, "no_result": 1, "kept": 4},
    "trials": {0: {"p": [e(-1.0), e(-0.5)], "t": [e(-0.25), e(-0.5)], "y": [1, 0]},
               1: {"p": [e(-0.75), e(-0.5)], "t": [e(-0.5), e(-0.25)], "y": [1, 1]}},
    "rec": {"overrun": 3, "consistent": 3, "overrun_consistent": 2, "tokens": 10},
    "excess": [-0.75, -0.25, -0.25],
    "splits": {"valid": 4},
    "stops": ["\n"],
}
FIX_RUN_ECE = {
    "p": (((1 - e(-1.0)) + e(-0.5)) / 2 + ((1 - e(-0.75)) + (1 - e(-0.5))) / 2) / 2,
    "t": ((e(-0.5) + (1 - e(-0.25))) / 2 + ((1 - e(-0.5)) + (1 - e(-0.25))) / 2) / 2,
}
FIX_RUN_EM = 0.75  # (1/2 + 2/2) / 2
FIX_RUN_CLASS_OF_FIXTURE = "overrun"
FIX_RUN_CLASS = [((3, 4), "overrun"), ((2, 4), "overrun"), ((1, 4), "clean"), ((0, 0), None)]

# ----- Equal-mass ECE -----
FIX_BINS = [(([0.875, 0.75, 0.25, 0.625], 2), [0.6875, 1.0]), (([0.5, 0.5, 0.5], 10), [0.5, 1.0]),
            (([0.125, 0.25, 0.5, 0.75, 1.0], 2), [0.625, 1.0])]
FIX_ECE = [(([0.875, 0.75, 0.25, 0.625], [1, 0, 0, 1], 2), 0.1875), (([0.5, 0.5, 0.5], [1, 1, 0], 10), 1.0 / 6.0),
           (([0.125, 0.25, 0.5, 0.75, 1.0], [0, 0, 1, 1, 1], 2), 0.075), (([], [], 10), None)]

# ----- Names and files -----
R1 = "boolq:model=together_opt-175b,data_augmentation=canonical"
R2 = "boolq:model=together_glm,data_augmentation=canonical,stop=hash"
R3 = "boolq:only_contrast=True,model=openai_ada,data_augmentation=contrast_sets,groups=robustness_contrast_sets"
R4 = "imdb:model=openai_ada,data_augmentation=canonical"
FIX_NAMES = {
    "canonical": [(R1, True), (R2, True), (R3, False), (R4, False)],
    "adapter": [(R1, "model=together_opt-175b"), (R2, "model=together_glm,stop=hash")],
    "model": [("model=together_glm,stop=hash", "together_glm,stop=hash"), ("x", "")],
}
FIX_SUITES = {R1: "v0.3.0", R2: "v0.3.0", R3: "v0.3.0", R4: "v0.3.0"}
FIX_SELECT = {R1: "v0.3.0", R2: "v0.3.0"}
FIX_STATS = [{"name": {"name": "ece_10_bin", "split": "valid"}, "count": 3, "sum": 0.6, "mean": 0.2},
             {"name": {"name": "ece_10_bin", "split": "valid", "perturbation": {"name": "x"}}, "count": 3, "sum": 3,
              "mean": 1.0}]
FIX_STAT_ENTRY = [(("ece_10_bin", "valid"), {"count": 3, "sum": 0.6, "mean": 0.2}), (("ece_10_bin", "test"), None)]
FIX_SLIM = [({"prompt": "x", "temperature": 0}, {"temperature": 0}),
            ({"text": "a", "logprob": -1.0, "top_logprobs": {"b": -2.0}}, {"text": "a", "logprob": -1.0}),
            ({"input": {"text": "q"}, "references": [], "id": "id1"}, {"references": [], "id": "id1"}),
            ({"input": {"text": "q"}}, {"input": {"text": "q"}})]

# ----- Aggregates -----
FIX_RANKS = ({"a": 0.1, "b": 0.2, "c": 0.1, "d": 0.3}, {"a": 1, "b": 3, "c": 1, "d": 4})
FIX_TAU = [(([1, 2, 3], [1, 3, 2]), 1.0 / 3.0), (([1, 1, 2], [1, 2, 2]), 0.5), (([1, 1], [1, 2]), None)]
FIX_MATCH = ({"a": 0.19, "b": 0.0600000001, "c": 0.5}, [0.06, 0.19], 2)
FIX_GROUP = [{"title": "BoolQ", "header": [{"value": "Model/adapter"}, {"value": "EM"}, {"value": "ECE (10-bin)"}],
              "rows": [[{"value": "A"}, {"value": 0.7}, {"value": 0.19}],
                       [{"value": "B"}, {"value": 0.6}, {"description": "no"}],
                       [{"value": "C"}, {"value": 0.5}, {"value": 0.06}]]}]
FIX_GROUP_VALUES = [0.19, 0.06]
FIX_GROUP_NO_COLUMN = [{"header": [{"value": "Model/adapter"}, {"value": "EM"}], "rows": []}]
FIX_MEDIAN = [([3, 1, 2], 2), ([4, 1, 3, 2], 2.5), ([], None)]

# ----- Verdicts: every prediction exactly on its boundary, then just past it -----
FIX_VERDICT_ON = {"fixtures": True, "runs_with_ece": 60, "runs_included": 54, "cells": 55, "matched": 50,
                  "overrun_adapters": 8, "excess_hits": 4, "delta_hits": 4, "overrun_records": 20,
                  "overrun_consistent": 19, "movers": 3, "tau": 0.8, "better": 2, "worse": 1}
FIX_VERDICT_PAST = {"fixtures": False, "runs_with_ece": 60, "runs_included": 53, "cells": 54, "matched": 0,
                    "overrun_adapters": 7, "excess_hits": 3, "delta_hits": 3, "overrun_records": 20,
                    "overrun_consistent": 18, "movers": 2, "tau": 0.79, "better": 1, "worse": 1}
