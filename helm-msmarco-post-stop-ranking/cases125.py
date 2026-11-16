"""Audit 125: data source, thresholds and hand-traced fixtures (all invented). Apache-2.0.

Token decoding and stop trimming fixtures are audit 104's, unchanged. New: the first-completion pick, the
answer-only log probability, reference tags, HELM's binary ranking key and stable order, RR@k with and without the
BM25 top-k filter, the (instance, trial) run census, trial means, MS MARCO run names and the eight verdicts.
"""

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/classic/benchmark_output"
HELM_RELEASE = "v0.4.0"
GROUP = "msmarco_regular"
COLUMN = "RR@10"
STAT = "RR@10"
STAT_TOPK = "RR@10 (topk=30)"
TOL_RUN = 1e-9
TOL_CELL = 1e-9
PLACES = 3
DELTA = 0.01
WORKERS = 1
PRINT_RUNS = 3

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
NL = ["\n"]
G = "Ġ"   # GPT-2 space
C = "Ċ"   # GPT-2 newline


def comp(text, lp, toks):
    return {"text": text, "logprob": lp, "tokens": list(toks)}


MISSING = {"text": "missing", "logprob": 0.0, "tokens": []}

# ----- One passage request -----
FIX_FIRST = [
    ({"result": {"completions": [
        {"text": " Yes", "logprob": -1.0, "tokens": [{"text": G + "Yes", "logprob": -1.0}]},
        {"text": " No", "logprob": -0.1, "tokens": []}]}},
     {"text": " Yes", "logprob": -1.0, "tokens": [(G + "Yes", -1.0)]}),
    ({"result": {"completions": []}}, MISSING),
    ({"result": None}, MISSING),
    ({}, MISSING),
    ({"result": {"completions": [{"text": None, "logprob": None, "tokens": [{"text": "x"}]}]}},
     {"text": "", "logprob": 0.0, "tokens": [("x", 0.0)]}),
]

A0 = comp(" Yes", -1.0, [(G + "Yes", -0.25), (C, -0.25), (C, -0.25), ("Pass", -0.25)])
A1 = comp(" Yes", -0.5, [(G + "Yes", -0.5)])
A2 = comp(" No", -0.25, [(G + "No", -0.125), (C, -0.125)])
A3 = comp(" No", -2.0, [(G + "No", -1.0), (C, -1.0)])
B0 = comp(" No", -0.5, [(G + "No", -0.5)])
B1 = comp(" Yes", -0.25, [(G + "Yes", -0.25)])
B2 = comp(" Maybe", -3.0, [(G + "Maybe", -3.0)])
D0 = comp(" Yes", -2.0, [(G + "Yes", -2.0)])
D2 = comp(" Yes", -1.25, [(G + "Yes", -0.5), (C, -0.5)])   # stored value is not the token sum (-1.0)
D3 = comp(" no", -0.5, [(G + "no", -0.5)])

FIX_ANSWER = [
    ((A0, NL), (-0.25, True, 1, True)),
    ((A1, NL), (-0.5, False, 1, True)),
    ((MISSING, NL), (0.0, False, 0, False)),
    ((comp(" Yes", -0.5, [(G + "No", -0.25), (C, -0.25)]), NL), (-0.25, True, 1, False)),
    ((comp("", -2.0, [(C, -1.0), (G + "Yes", -1.0)]), NL), (0.0, True, 0, True)),
    ((A0, []), (-1.0, False, 4, False)),
]

FIX_TAGS = [
    ({"tags": ["docid=12", "correct", "relevance=1", "rank=2"]}, (True, 1, 2)),
    ({"tags": ["docid=11", "rank=7"]}, (False, None, 7)),
    ({"tags": []}, (False, None, None)),
    ({}, (False, None, None)),
    (None, (False, None, None)),
]

# ----- HELM's binary ranking and RR@k -----
FIX_SCORE_KEY = [((" Yes", -1.0), (2, -1.0)), (("yes ", -1.0), (2, -1.0)), ((" No", -1.0), (1, 1.0)),
                 (("missing", 0.0), (0, 0.0)), (("Yes, it does", -0.5), (0, 0.5)), ((None, -0.5), (0, 0.5))]
# a and b tie: a stable descending sort keeps a first (sorting ascending and reversing would not)
FIX_ORDER = ([{"id": "a", "text": " Yes", "p": -1.0}, {"id": "b", "text": " Yes", "p": -1.0},
              {"id": "c", "text": " No", "p": -3.0}, {"id": "d", "text": " No", "p": -0.5},
              {"id": "e", "text": "x", "p": -0.1}], ["a", "b", "c", "d", "e"])
OA = {"relevance": None, "rank": 1}
OB = {"relevance": 1, "rank": None}
OC = {"relevance": 1, "rank": 5}
OD = {"relevance": 0, "rank": 2}
FIX_RR = [(([OA, OB, OC], 10, None), 0.5), (([OA, OB, OC], 10, 30), 0.5), (([OA, OB, OC], 1, None), 0.0),
          (([OA, OD], 10, None), 0.0), (([OA, OC], 10, 3), 0.0), (([], 10, None), 0.0), (([OC, OB], 10, None), 1.0)]
FIX_FIRST_GOLD = [([OA, OB, OC], 2), ([OA, OD], None), ([], None)]
FIX_OUTSIDE = [(([OB], 30), True), (([{"relevance": 1, "rank": 31}], 30), True),
               (([{"relevance": 1, "rank": 30}, OA], 30), False), (([], 30), False),
               (([OD, {"relevance": None, "rank": None}], 30), False)]

# ----- Run census -----
Q1 = [{"tags": ["docid=11", "rank=1"]}, {"tags": ["docid=12", "correct", "relevance=1", "rank=2"]},
      {"tags": ["docid=13", "rank=3"]}, {"tags": ["docid=14", "correct", "relevance=1"]}]
Q2 = [{"tags": ["docid=21", "rank=1"]}, {"tags": ["docid=22", "correct", "relevance=1"]},
      {"tags": ["docid=23", "rank=2"]}]


def _raw(c):
    return {"text": c["text"], "logprob": c["logprob"], "tokens": [{"text": t, "logprob": lp} for t, lp in c["tokens"]]}


def rq(iid, trial, ri, refs, c, split="valid", pert=None):
    inst = {"id": iid, "split": split, "references": refs}
    if pert is not None:
        inst["perturbation"] = pert
    return {"instance": inst, "train_trial_index": trial, "reference_index": ri,
            "result": {"completions": [] if c is None else [_raw(c)]}}


FIX_STATE = {"adapter_spec": {"stop_sequences": ["\n"]}, "request_states": [
    rq("q1", 0, 0, Q1, A0), rq("q1", 0, 1, Q1, A1), rq("q1", 0, 2, Q1, A2), rq("q1", 0, 3, Q1, A3),
    rq("q2", 0, 0, Q2, B0), rq("q2", 0, 1, Q2, B1), rq("q2", 0, 2, Q2, B2),
    rq("q1", 1, 0, Q1, D0), rq("q1", 1, 1, Q1, None), rq("q1", 1, 2, Q1, D2), rq("q1", 1, 3, Q1, D3),
    rq("q1", 0, 0, Q1, A1, pert={"name": "mild_mix"}),
    rq("q9", 0, 0, Q2, A1, split="train"),
    rq("q2", 0, None, Q2, A1),
    rq("q2", 0, 0, Q2, A1),
]}
FIX_RUN = {
    "counts": {"request_states": 15, "perturbed": 1, "not_eval": 1, "no_reference_index": 1, "duplicate": 1,
               "kept": 11},
    "rec": {"records": 11, "overrun": 4, "consistent": 10, "overrun_consistent": 4, "tokens": 16, "lp_mismatch": 1},
    "grp": {"groups": 3, "no_gold": 0, "gold_outside_topk": 3, "rr_changed": 1, "first_gold_moved": 1},
    "trials": {0: {"p10": [1.0, 1.0], "t10": [0.5, 1.0], "pk": [1.0, 0.0], "tk": [0.5, 0.0]},
               1: {"p10": [1.0 / 3], "t10": [1.0 / 3], "pk": [1.0 / 3], "tk": [1.0 / 3]}},
    "excess": [-0.75, -0.125, -1.0, -0.75],
    "stops": ["\n"],
}
FIX_TRIAL_MEAN = {"p10": ((1.0 + 1.0 / 3) / 2, 2), "t10": ((0.75 + 1.0 / 3) / 2, 2),
                  "pk": ((0.5 + 1.0 / 3) / 2, 2), "tk": ((0.25 + 1.0 / 3) / 2, 2)}
FIX_RUN_CLASS_OF_FIXTURE = "clean"
FIX_RUN_CLASS = [((3, 4), "overrun"), ((2, 4), "overrun"), ((1, 4), "clean"), ((0, 0), None)]

# ----- Names and files -----
M1 = "msmarco:track=regular,valid_topk=30,model=together_gpt-j-6b,data_augmentation=canonical"
M2 = "msmarco:track=trec,valid_topk=30,model=together_gpt-j-6b,data_augmentation=canonical"
M3 = "boolq:model=together_gpt-j-6b,data_augmentation=canonical"
M4 = "msmarco:track=regular,valid_topk=30,model=openai_ada,data_augmentation=canonical"
M5 = "msmarco:track=regular,valid_topk=30,model=openai_ada,groups=ablation"
FIX_NAMES = {
    "selected": [(M1, True), (M2, False), (M3, False), (M4, True), (M5, False)],
    "scenario": [(M1, "msmarco"), (M3, "boolq"), ("x", "")],
    "adapter": [(M1, "model=together_gpt-j-6b"), (M4, "model=openai_ada")],
    "model": [("model=together_gpt-j-6b", "together_gpt-j-6b"), ("x", "")],
}
FIX_SUITES = {M1: "v0.3.0", M2: "v0.3.0", M3: "v0.3.0", M4: "v0.3.0", M5: "v0.3.0"}
FIX_SELECT = {M1: "v0.3.0", M4: "v0.3.0"}
FIX_STATS = [{"name": {"name": "RR@10", "split": "valid", "perturbation": {"name": "dialect"}}, "count": 3,
              "sum": 0.3, "mean": 0.1},
             {"name": {"name": "RR@10", "split": "valid"}, "count": 3, "sum": 0.6, "mean": 0.2},
             {"name": {"name": "RR@10 (topk=30)", "split": "valid"}, "count": 3, "sum": 0.3, "mean": 0.1}]
FIX_STAT_ENTRY = [(("RR@10", "valid"), {"count": 3, "sum": 0.6, "mean": 0.2}),
                  (("RR@10 (topk=30)", "valid"), {"count": 3, "sum": 0.3, "mean": 0.1}),
                  (("RR@10", "test"), None)]
FIX_SLIM = [({"prompt": "x", "temperature": 0}, {"temperature": 0}),
            ({"text": "a", "logprob": -1.0, "top_logprobs": {"b": -2.0}}, {"text": "a", "logprob": -1.0}),
            ({"input": {"text": "q"}, "references": [], "id": "id1"}, {"references": [], "id": "id1"}),
            ({"output": {"text": "passage"}, "tags": ["rank=1"]}, {"tags": ["rank=1"]}),
            ({"input": {"text": "q"}}, {"input": {"text": "q"}})]

# ----- Aggregates -----
FIX_RANKS = ({"a": 0.1, "b": 0.2, "c": 0.1, "d": 0.3}, {"a": 3, "b": 2, "c": 3, "d": 1})
FIX_TAU = [(([1, 2, 3], [1, 3, 2]), 1.0 / 3.0), (([1, 1, 2], [1, 2, 2]), 0.5), (([1, 1], [1, 2]), None)]
FIX_MATCH = ({"a": 0.19, "b": 0.0600000001, "c": 0.5}, [0.06, 0.19], 2)
FIX_GROUP = [{"title": "MS MARCO", "header": [{"value": "Model/adapter"}, {"value": "RR@10"}, {"value": "x"}],
              "rows": [[{"value": "A"}, {"value": 0.19}, {"value": 1}],
                       [{"value": "B"}, {"description": "no"}, {"value": 2}],
                       [{"value": "C"}, {"value": 0.06}, {"value": 3}]]}]
FIX_GROUP_VALUES = [0.19, 0.06]
FIX_GROUP_NO_COLUMN = [{"header": [{"value": "Model/adapter"}, {"value": "EM"}], "rows": []}]
FIX_MEDIAN = [([3, 1, 2], 2), ([4, 1, 3, 2], 2.5), ([], None)]

# ----- Verdicts: every prediction on its boundary, then just past it -----
EXPECTED = ["together_bloom", "together_gpt-j-6b", "together_gpt-neox-20b", "together_opt-175b", "together_opt-66b"]
FIX_VERDICT_ON = {"fixtures": True, "runs_listed": 10, "runs_included": 9, "published": 10, "matched": 9,
                  "overrun_set": list(reversed(EXPECTED)), "overrun": 5, "median_excess": -0.1,
                  "overrun_records": 20, "overrun_consistent": 19, "delta_hits": 3, "better": 1, "worse": 0,
                  "movers": 1, "groups_overrun": 100, "groups_changed": 10}
FIX_VERDICT_PAST = {"fixtures": False, "runs_listed": 10, "runs_included": 8, "published": 10, "matched": 8,
                    "overrun_set": EXPECTED[:4], "overrun": 4, "median_excess": -0.099,
                    "overrun_records": 20, "overrun_consistent": 18, "delta_hits": 1, "better": 1, "worse": 1,
                    "movers": 0, "groups_overrun": 100, "groups_changed": 9}
