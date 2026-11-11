"""Audit 102: data source, gates, thresholds and hand-traced fixtures (all invented; none copied from HELM data).
Apache-2.0."""

from fractions import Fraction

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/classic/benchmark_output"
HELM_RELEASE = "v0.4.0"
GROUPS = {"reg": "math_regular", "cot": "math_chain_of_thought"}
SUBJECTS = ("algebra", "counting_and_probability", "geometry", "intermediate_algebra", "number_theory",
            "prealgebra", "precalculus")
CAP = {"reg": 20, "cot": 400}  # max_tokens in HELM's MATH run spec
TOL_RUN = 1e-6
TOL_CELL = 1e-9
PLACES = 3
WORKERS = 8
PRINT_PER_CLASS = 8
FLIPS_PER_RUN = 400

# Regular column: (gold, prediction) -> (h, a, cls)
FIX_REG = [
    (("5", "5"), (1, 1, None)),
    (("5", "5$"), (0, 1, "dollar_tail")),
    (("1000", "1,000"), (0, 1, "value_format")),
    (("\\frac{1}{2}", "0.5"), (1, 1, None)),
    (("\\frac{1}{4}", "0.25"), (0, 1, "value_format")),
    (("7", "8"), (0, 0, None)),
    (("7", ""), (0, 0, None)),
    (("\\$5", "\\$5"), (1, 1, None)),
    (("a$b", "a$b"), (1, 0, "other")),
]

G = "So $x=5$. Thus the answer is $\\boxed{5}$."
# Chain-of-thought column: (gold, prediction) -> (h, a, cls)
FIX_COT = [
    ((G, "The answer is $\\boxed{5}$."), (1, 1, None)),
    ((G, "The answer is $5$."), (0, 1, "unboxed")),
    ((G, "So $\\boxed{5.0}$"), (0, 1, "value_format")),
    ((G, "\\boxed 5"), (0, 1, "pred_fallback")),
    ((G, "The answer is $\\boxed{6}$."), (0, 0, None)),
    (("x is 5.", "I think 5."), (1, 0, "both_none")),
    ((G, ""), (0, 0, None)),
]

# grade_record: (mode, golds, prediction) -> {h, a, cls}
FIX_RECORD = [
    (("reg", ["7", "5"], " 5$"), {"h": 0, "a": 1, "cls": "up:dollar_tail"}),
    (("reg", ["5"], " 5\n"), {"h": 1, "a": 1, "cls": None}),
    (("cot", [G], " The answer is $5$."), {"h": 0, "a": 1, "cls": "up:unboxed"}),
    (("cot", ["x is 5."], "I think 5."), {"h": 1, "a": 0, "cls": "down:both_none"}),
]

RUN_REG = "math:subject=algebra,level=1,use_official_examples=True,use_chain_of_thought=False,model=together_glm,stop=hash"
RUN_COT = "math:subject=algebra,level=1,use_official_examples=False,use_chain_of_thought=True,model=openai_davinci"
RUN_OTHER = "math:subject=algebra,level=1,use_official_examples=False,use_chain_of_thought=False,model=x"
FIX_NAMES = {
    "mode": [(RUN_REG, "reg"), (RUN_COT, "cot"), (RUN_OTHER, None), ("gsm:model=openai_davinci", None)],
    "subject": [(RUN_REG, "algebra"), ("gsm:model=openai_davinci", None)],
    "adapter": [(RUN_REG, "math:level=1,use_official_examples=True,use_chain_of_thought=False,model=together_glm,"
                          "stop=hash")],
    "model": [(RUN_REG, "together_glm,stop=hash"), ("gsm:x", "")],
}
FIX_SUITES = {RUN_REG: "v0.3.0", RUN_COT: "v0.3.0", RUN_OTHER: "v0.3.0", "gsm:model=openai_davinci": "v0.3.0"}
FIX_SELECT = {RUN_REG: ("reg", "v0.3.0"), RUN_COT: ("cot", "v0.3.0")}

FIX_REG_INSTANCES = [
    {"id": "id1", "split": "test", "references": [{"output": {"text": "5"}, "tags": ["correct"]}]},
    {"id": "id2", "split": "test", "references": [{"output": {"text": "1000"}, "tags": ["correct"]}]},
    {"id": "id3", "split": "valid", "references": [{"output": {"text": "5"}, "tags": ["correct"]}]},
]
FIX_REG_PREDS = [
    {"instance_id": "id1", "train_trial_index": 0, "predicted_text": " 5",
     "stats": {"math_equiv": 1.0, "num_output_tokens": 2}},
    {"instance_id": "id1", "train_trial_index": 1, "predicted_text": " 5$\n",
     "stats": {"math_equiv": 0.0, "num_output_tokens": 20}},
    {"instance_id": "id2", "train_trial_index": 0, "predicted_text": "1,000",
     "stats": {"math_equiv": 0.0, "num_output_tokens": 3}},
    {"instance_id": "id2", "train_trial_index": 1, "predicted_text": "999",
     "stats": {"math_equiv": 1.0, "num_output_tokens": 2}},
    {"instance_id": "id3", "train_trial_index": 0, "predicted_text": "5", "stats": {"math_equiv": 1.0}},
    {"instance_id": "id1", "train_trial_index": 0, "predicted_text": "x", "stats": {"math_equiv": 0.0}},
    {"instance_id": "id2", "train_trial_index": 0, "predicted_text": "1000", "perturbation": {"name": "typo"},
     "stats": {"math_equiv": 1.0}},
    {"instance_id": "id1", "train_trial_index": 2, "predicted_text": "6", "stats": {}},
    {"instance_id": "id2", "train_trial_index": 2, "predicted_text": "1000", "stats": {"math_equiv": 1.0}},
]
FIX_REG_RUN = {
    "counts": {"n_records": 9, "perturbed": 1, "not_test": 1, "duplicate": 1, "kept": 6},
    "trials": {0: {"n": 2, "h": 1, "a": 2}, 1: {"n": 2, "h": 0, "a": 1}, 2: {"n": 2, "h": 1, "a": 1}},
    "stat_missing": 1,
    "stat_mismatch": 1,
    "up": {"dollar_tail": 1, "value_format": 1},
    "down": {"other": 0},
    "keys": {"up:dollar_tail": [("id1", 1)], "up:value_format": [("id2", 0)], "down:other": []},
    "cap_records": 1,
    "cap_up": 1,
}
FIX_REG_MEANS = {"h": Fraction(1, 3), "a": Fraction(2, 3)}

FIX_COT_INSTANCES = [{"id": "idA", "split": "test", "references": [{"output": {"text": G}, "tags": ["correct"]}]}]
FIX_COT_PREDS = [
    {"instance_id": "idA", "train_trial_index": 0, "predicted_text": "The answer is $\\boxed{5}$.",
     "stats": {"math_equiv_chain_of_thought": 1.0, "num_output_tokens": 10}},
    {"instance_id": "idA", "train_trial_index": 1, "predicted_text": "The answer is $5$.",
     "stats": {"math_equiv_chain_of_thought": 0.0, "num_output_tokens": 400}},
]
FIX_COT_RUN = {
    "counts": {"n_records": 2, "perturbed": 0, "not_test": 0, "duplicate": 0, "kept": 2},
    "trials": {0: {"n": 1, "h": 1, "a": 1}, 1: {"n": 1, "h": 0, "a": 1}},
    "stat_missing": 0,
    "stat_mismatch": 0,
    "up": {"gold_fallback": 0, "pred_fallback": 0, "value_format": 0, "unboxed": 1, "other": 0},
    "down": {"both_none": 0, "other": 0},
    "cap_records": 1,
    "cap_up": 1,
}
FIX_COT_MEANS = {"h": Fraction(1, 2), "a": Fraction(1)}

FIX_CELL_RUNS = {
    "r1": {"mode": "reg", "adapter": "X", "subject": "s1", "trials": {0: {"n": 2, "h": 1, "a": 2}}},
    "r2": {"mode": "reg", "adapter": "X", "subject": "s2", "trials": {0: {"n": 4, "h": 0, "a": 1}}},
    "r3": {"mode": "reg", "adapter": "Y", "subject": "s1", "trials": {0: {"n": 1, "h": 1, "a": 1}}},
}
FIX_CELL_SUBJECTS = ("s1", "s2")
FIX_CELLS = {("reg", "X"): {"h": Fraction(1, 4), "a": Fraction(5, 8)}}

FIX_RANKS = ({"a": 3, "b": 5, "c": 3}, {"a": 2, "b": 1, "c": 2})
FIX_TAU = [(([1, 2, 3], [1, 3, 2]), 1.0 / 3.0), (([1, 1, 2], [1, 2, 2]), 0.5), (([1, 1], [1, 2]), None)]
FIX_MATCH = ({"a": 0.5, "b": 0.25000000001, "c": 0.1}, [0.25, 0.5, 0.5], 2)
FIX_GROUP = [{"header": [{"value": "Model/adapter"}, {"value": "Equivalent (CoT)"}],
              "rows": [[{"value": "A"}, {"value": 0.5}], [{"value": "B"}, {"value": 0.25}], [{"value": "C"}]]}]
FIX_GROUP_VALUES = [0.5, 0.25]


def _base():
    return {"fixtures": True, "runs_listed": 100, "runs_included": 90, "cells_reg": 60, "cells_cot": 60,
            "matched_reg": 54, "matched_cot": 54, "cot_n": 1000, "cot_net": 10,
            "cot_up_classes": {"gold_fallback": 0, "pred_fallback": 1, "value_format": 1, "unboxed": 2, "other": 0},
            "cot_movers": 5, "cot_tau": 0.9, "reg_n": 1000, "reg_up": 2, "reg_net": 9, "hash_rise": True}


FIX_VERDICT_ON = _base()  # every prediction exactly on its boundary -> all HELD
FIX_VERDICT_PAST = dict(_base(), runs_included=89, cot_net=9,
                        cot_up_classes={"gold_fallback": 0, "pred_fallback": 1, "value_format": 1, "unboxed": 1,
                                        "other": 0},
                        cot_movers=4, cot_tau=0.89, reg_up=1, reg_net=10, hash_rise=False)
