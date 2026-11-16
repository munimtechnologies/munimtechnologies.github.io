"""Audit 124: data source, thresholds and hand-traced fixtures (all invented). Apache-2.0.

Record-level fixtures (token decoding, stop trimming, exact match, records, top completion, equal-mass ECE, parsing
hook, ranks, tau-b, matching, group column, medians) are audit 104's, unchanged. New: the (split, trial) run census,
per-split values, pooled cells, mean confidence, the three-scenario run names, the per-split stats lookup, flagged
models and the eight new verdicts.
"""

import math

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/classic/benchmark_output"
HELM_RELEASE = "v0.4.0"
GROUPS = {"imdb": "imdb", "civil_comments": "civil_comments", "raft": "raft"}
COLUMN = "ECE (10-bin)"
NUM_BINS = 10
TOL_RUN = 1e-9
TOL_CELL = 1e-9
PLACES = 3
DELTA = 0.02
WORKERS = 1
PRINT_PER_SCENARIO = 3

e = math.exp

# ----- Token decoding and stop trimming (audit 104) -----
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


# ----- Run census keyed by (split, trial) (new) -----
FIX_STATE = {"adapter_spec": {"stop_sequences": ["\n"]}, "request_states": [
    rs("id1", 0, "valid", ["Yes"], C1),
    rs("id2", 0, "valid", ["No"], C2),
    rs("id1", 0, "test", ["Yes"], C4),
    rs("id3", 1, "test", ["Yes"], C7),
    rs("id1", 0, "valid", ["Yes"], C2),
    rs("id2", 1, "valid", ["No"], C2, pert={"name": "mild_mix"}),
    rs("id4", 0, "train", ["Yes"], C2),
    rs("id5", 1, "test", ["Yes"], None),
]}
FIX_RUN = {
    "counts": {"request_states": 8, "perturbed": 1, "not_eval": 1, "duplicate": 1, "no_result": 1, "kept": 4},
    "trials": {("valid", 0): {"p": [e(-1.0), e(-0.5)], "t": [e(-0.25), e(-0.5)], "y": [1, 0]},
               ("test", 0): {"p": [e(-0.75)], "t": [e(-0.5)], "y": [1]},
               ("test", 1): {"p": [e(-0.5)], "t": [e(-0.25)], "y": [1]}},
    "rec": {"overrun": 3, "consistent": 3, "overrun_consistent": 2, "tokens": 10},
    "excess": [-0.75, -0.25, -0.25],
    "splits": {"valid": 2, "test": 2},
    "stops": ["\n"],
}
FIX_SPLIT_VALUES = {
    "p": {"valid": (((1 - e(-1.0)) + e(-0.5)) / 2, 1), "test": (((1 - e(-0.75)) + (1 - e(-0.5))) / 2, 2)},
    "t": {"valid": ((e(-0.5) + (1 - e(-0.25))) / 2, 1), "test": (((1 - e(-0.5)) + (1 - e(-0.25))) / 2, 2)},
    "em": {"valid": (0.5, 1), "test": (1.0, 2)},
}
FIX_MEAN_CONF = {"p": (e(-1.0) + e(-0.5) + e(-0.75) + e(-0.5)) / 4, "t": (e(-0.25) + e(-0.5) + e(-0.5) + e(-0.25)) / 4}
FIX_RUN_CLASS_OF_FIXTURE = "overrun"
FIX_RUN_CLASS = [((3, 4), "overrun"), ((2, 4), "overrun"), ((1, 4), "clean"), ((0, 0), None)]
FIX_POOLED = [([(0.2, 3), (0.4, 1)], 0.25), ([], None), ([(0.2, 3), (None, 3)], None), ([(0.5, 0)], None)]

# ----- Equal-mass ECE (audit 104) -----
FIX_BINS = [(([0.875, 0.75, 0.25, 0.625], 2), [0.6875, 1.0]), (([0.5, 0.5, 0.5], 10), [0.5, 1.0]),
            (([0.125, 0.25, 0.5, 0.75, 1.0], 2), [0.625, 1.0])]
FIX_ECE = [(([0.875, 0.75, 0.25, 0.625], [1, 0, 0, 1], 2), 0.1875), (([0.5, 0.5, 0.5], [1, 1, 0], 10), 1.0 / 6.0),
           (([0.125, 0.25, 0.5, 0.75, 1.0], [0, 0, 1, 1, 1], 2), 0.075), (([], [], 10), None)]

# ----- Names and files (new) -----
R1 = "raft:subset=ade_corpus_v2,model=together_opt-175b,data_augmentation=canonical"
R2 = "civil_comments:demographic=all,model=together_opt-175b,data_augmentation=canonical"
R3 = "civil_comments:demographic=all,model=together_opt-175b,groups=ablation_prompts"
R4 = "imdb:model=together_t5-11b,data_augmentation=canonical,stop=hash"
R5 = "boolq:model=openai_ada,data_augmentation=canonical"
R6 = "imdb:only_contrast=True,model=openai_ada,data_augmentation=contrast_sets,groups=robustness_contrast_sets"
FIX_NAMES = {
    "canonical": [(R1, True), (R2, True), (R3, False), (R4, True), (R5, False), (R6, False)],
    "scenario": [(R1, "raft"), (R5, "boolq"), ("x", "")],
    "adapter": [(R1, "model=together_opt-175b"), (R2, "model=together_opt-175b"),
                (R4, "model=together_t5-11b,stop=hash")],
    "model": [("model=together_glm,stop=hash", "together_glm,stop=hash"), ("x", "")],
    "flagged": [("model=together_t5-11b,stop=hash", True), ("model=together_opt-175b", False),
                ("model=meta_llama-2-70b", False), ("model=meta_llama-2-7b", True)],
}
FIX_SUITES = {R1: "v0.3.0", R2: "v0.3.0", R3: "v0.3.0", R4: "v0.3.0", R5: "v0.3.0", R6: "v0.3.0"}
FIX_SELECT = {R1: "v0.3.0", R2: "v0.3.0", R4: "v0.3.0"}
FIX_STATS = [{"name": {"name": "ece_10_bin", "split": "valid"}, "count": 3, "sum": 0.6, "mean": 0.2},
             {"name": {"name": "ece_10_bin", "split": "test", "sub_split": "toxic"}, "count": 3, "sum": 0.3,
              "mean": 0.1},
             {"name": {"name": "ece_10_bin", "split": "test"}, "count": 3, "sum": 0.9, "mean": 0.3},
             {"name": {"name": "ece_10_bin", "split": "valid", "perturbation": {"name": "x"}}, "count": 3, "sum": 3,
              "mean": 1.0}]
FIX_STAT_ENTRY = [(("ece_10_bin", "valid"), {"count": 3, "sum": 0.6, "mean": 0.2}),
                  (("ece_10_bin", "test"), {"count": 3, "sum": 0.9, "mean": 0.3}),
                  (("exact_match", "valid"), None)]
FIX_SLIM = [({"prompt": "x", "temperature": 0}, {"temperature": 0}),
            ({"text": "a", "logprob": -1.0, "top_logprobs": {"b": -2.0}}, {"text": "a", "logprob": -1.0}),
            ({"input": {"text": "q"}, "references": [], "id": "id1"}, {"references": [], "id": "id1"}),
            ({"input": {"text": "q"}}, {"input": {"text": "q"}})]

# ----- Aggregates (audit 104) -----
FIX_RANKS = ({"a": 0.1, "b": 0.2, "c": 0.1, "d": 0.3}, {"a": 1, "b": 3, "c": 1, "d": 4})
FIX_TAU = [(([1, 2, 3], [1, 3, 2]), 1.0 / 3.0), (([1, 1, 2], [1, 2, 2]), 0.5), (([1, 1], [1, 2]), None)]
FIX_MATCH = ({"a": 0.19, "b": 0.0600000001, "c": 0.5}, [0.06, 0.19], 2)
FIX_GROUP = [{"title": "IMDB", "header": [{"value": "Model/adapter"}, {"value": "EM"}, {"value": "ECE (10-bin)"}],
              "rows": [[{"value": "A"}, {"value": 0.7}, {"value": 0.19}],
                       [{"value": "B"}, {"value": 0.6}, {"description": "no"}],
                       [{"value": "C"}, {"value": 0.5}, {"value": 0.06}]]}]
FIX_GROUP_VALUES = [0.19, 0.06]
FIX_GROUP_NO_COLUMN = [{"header": [{"value": "Model/adapter"}, {"value": "EM"}], "rows": []}]
FIX_MEDIAN = [([3, 1, 2], 2), ([4, 1, 3, 2], 2.5), ([], None)]


# ----- Verdicts: every prediction on (or just inside) its boundary, then just past it -----
def _by(**kw):
    base = {"runs_with_ece": 10, "runs_included": 9, "published": 10, "matched": 9, "overrun": 15, "delta_hits": 8,
            "better": 1, "worse": 0, "better10": 8, "median_excess": -2.0, "tau": 0.79, "movers": 5}
    base.update(kw)
    return base


FIX_VERDICT_ON = {"fixtures": True, "flag_records": 20, "flag_consistent": 19,
                  "by": {"imdb": _by(), "civil_comments": _by(), "raft": _by()}}
_PAST = dict(runs_included=8, matched=8, overrun=14, delta_hits=6, better=1, worse=1, better10=6,
             median_excess=-1.99, tau=0.8, movers=5)
FIX_VERDICT_PAST = {"fixtures": False, "flag_records": 20, "flag_consistent": 18,
                    "by": {"imdb": _by(**_PAST), "civil_comments": _by(**_PAST), "raft": _by(**_PAST)}}
