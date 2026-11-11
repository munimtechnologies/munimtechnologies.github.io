"""Audit 106 constants and hand-traced fixtures (frozen before the sealed run). Apache-2.0.
Authored by AI agents working in the name of MV2, Munim, Inc. All fixture values are invented."""

import grade106 as g

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/capabilities/benchmark_output"
HELM_RELEASE = "v1.15.0"
LAST_SUITE = "v1.15.0"
SPLIT = "test"
TOL_RUN = 1e-6            # our run mean vs stats.json
TOL_CELL = 1e-6           # our cell vs a published group-page value
UNSCORED_SHARE = 0.01     # a run is excluded if more than 1% of kept records have no HELM score
STORED_MISMATCH = 0.005   # ... or if more than 0.5% of stored per-record scores differ from ours
PRESENT_SHARE = 0.5       # a judge "rated a run" if it has a value on at least half its non-empty records
FULL_SHARE = 0.95         # P2: each of the three judges on at least 95% of non-empty records
MIN_FULL = 50             # a run enters the judge-offset analysis with at least 50 fully rated records
PLACES = 3
PLACES_V115 = 2
PERM_ITERS = 10000
PERM_SEED = 106
WORKERS = 2

WB = g.SCENARIOS["wildbench"]
OM = g.SCENARIOS["omni_math"]

# ----- parse_annotation -----
A1 = {"prompt_text": "x", "gpt_strengths": "s", "gpt_weaknesses": "w", "gpt_score": 8.0, "claude_strengths": "s",
      "claude_weaknesses": "w", "claude_score": 6.0, "llama_strengths": "s", "llama_weaknesses": "w",
      "llama_score": 7.0}
A2 = {"prompt_text": None, "empty_output_score": 1.0}
A3 = {"prompt_text": "x", "gpt_score": 9.0, "claude_score": None, "llama_score": 6.0}
A4 = {"gpt_score": None, "claude_score": None}
A5 = {"gpt_score": "7", "llama_score": 5}
A6 = {"gpt_score": 4.0, "claude_score": 2.0, "llama_score": 3.0}
B1 = {"prompt_text": "x", "gpt_student_final_answer": "3", "gpt_justification": "j",
      "gpt_equivalence_judgement": True, "claude_equivalence_judgement": False, "llama_equivalence_judgement": True}
B2 = {"prompt_text": None, "empty_output_equivalence_judgement": False}
B3 = {"gpt_equivalence_judgement": True, "claude_equivalence_judgement": True, "llama_equivalence_judgement": True}
B4 = {"gpt_equivalence_judgement": False, "claude_equivalence_judgement": None, "llama_equivalence_judgement": False}

FIX_PARSE = [
    ((A1, "wildbench"), ({"claude": 6.0, "gpt": 8.0, "llama": 7.0}, False, 7.0, 0)),
    ((A2, "wildbench"), ({}, True, 1.0, 0)),
    ((A3, "wildbench"), ({"claude": None, "gpt": 9.0, "llama": 6.0}, False, 7.5, 0)),
    ((A4, "wildbench"), ({"claude": None, "gpt": None}, False, None, 0)),
    ((A5, "wildbench"), ({"gpt": None, "llama": 5.0}, False, 5.0, 1)),
    ((A6, "wildbench"), ({"claude": 2.0, "gpt": 4.0, "llama": 3.0}, False, 3.0, 0)),
    ((B1, "omni_math"), ({"claude": 0.0, "gpt": 1.0, "llama": 1.0}, False, 2.0 / 3, 0)),
    ((B2, "omni_math"), ({}, True, 0.0, 0)),
    ((B4, "omni_math"), ({"claude": None, "gpt": 0.0, "llama": 0.0}, False, 0.0, 0)),
]

# ----- WildBench run census -----
FIX_WB_PREDS = [
    {"instance_id": "i1", "train_trial_index": 0, "annotations": {"wildbench": A1}, "stats": {"wildbench_score": 7.0}},
    {"instance_id": "i2", "train_trial_index": 0, "annotations": {"wildbench": A2}, "stats": {"wildbench_score": 1.0}},
    {"instance_id": "i3", "train_trial_index": 0, "annotations": {"wildbench": A3}, "stats": {"wildbench_score": 7.0}},
    {"instance_id": "i4", "train_trial_index": 0, "annotations": {"wildbench": A6}, "stats": {}},
    {"instance_id": "i4", "train_trial_index": 0, "annotations": {"wildbench": A1}},
    {"instance_id": "i5", "train_trial_index": 0, "annotations": {}},
    {"instance_id": "i1", "train_trial_index": 0, "perturbation": {"name": "robustness"},
     "annotations": {"wildbench": A1}},
    "not a dict",
]
FIX_WB_COUNTS = {"predictions": 7, "perturbed": 1, "duplicate": 1, "no_annotation": 1, "kept": 4, "empty": 1,
                 "unscored": 0, "bad_values": 0}
FIX_WB_STORED = (3, 1)                     # stored_n, mismatch (i3: 7.5 against a stored 7.0)
FIX_WB_H = [7.0, 1.0, 7.5, 3.0]
FIX_WB_MEAN = 4.625
FIX_WB_RESCALED = 3.625 / 9.0              # assertAlmostEqual
FIX_WB_COVERAGE = (3, {"claude": 2, "gpt": 3, "llama": 3})
FIX_WB_PRESENT = {0.95: ["gpt", "llama"], 0.5: ["claude", "gpt", "llama"]}
FIX_WB_OFFSETS = {"n": 2, "mean": {"claude": 4.0, "gpt": 6.0, "llama": 5.0},
                  "offset": {"claude": -1.5, "gpt": 1.5, "llama": 0.0}, "agree": 0.0}
FIX_WB_JURY = {("gpt",): (5.5, 0), ("claude",): (4.125, 1)}   # run mean under the jury, records that fell back

# ----- Omni-MATH run census -----
FIX_OM_PREDS = [
    {"instance_id": "o1", "annotations": {"omni_math": B1}, "stats": {"omni_math_accuracy": 2.0 / 3}},
    {"instance_id": "o2", "annotations": {"omni_math": B2}},
    {"instance_id": "o3", "annotations": {"omni_math": B3}},
    {"instance_id": "o4", "annotations": {"omni_math": B4}},
]
FIX_OM_COUNTS = {"predictions": 4, "perturbed": 0, "duplicate": 0, "no_annotation": 0, "kept": 4, "empty": 1,
                 "unscored": 0, "bad_values": 0}
FIX_OM_STORED = (1, 0)
FIX_OM_MEAN = 5.0 / 12.0                   # assertAlmostEqual
FIX_OM_OFFSETS = {"n": 2, "mean": {"claude": 0.5, "gpt": 1.0, "llama": 1.0},
                  "offset": {"claude": -0.5, "gpt": 0.25, "llama": 0.25}, "agree": 0.5}

# ----- scenario_state fallback -----
FIX_STATE = {"request_states": [
    {"instance": {"id": "s1"}, "train_trial_index": 0, "annotations": {"wildbench": A1}},
    {"instance": {"id": "s1", "perturbation": {"name": "x"}}, "annotations": {"wildbench": A1}},
    "junk",
]}
FIX_STATE_PREDS = [
    {"instance_id": "s1", "train_trial_index": 0, "perturbation": None, "annotations": {"wildbench": A1}, "stats": {}},
    {"instance_id": "s1", "train_trial_index": 0, "perturbation": {"name": "x"}, "annotations": {"wildbench": A1},
     "stats": {}},
]

# ----- Families, composition, self-preference -----
FIX_JUDGE_FAMILY = [("gpt", "openai"), ("claude", "anthropic"), ("llama", "meta"), ("empty_output", None)]
FIX_MODEL = [
    ("wildbench:subset=v2,model=openai_gpt-4o-2024-11-20", "openai_gpt-4o-2024-11-20"),
    ("wildbench:subset=v2,num_output_tokens=2048,model=allenai_olmo-2-1124-7b-instruct",
     "allenai_olmo-2-1124-7b-instruct"),
    ("no model here", ""),
]
FIX_MODEL_FAMILY = [("openai_gpt-4o-2024-11-20", "openai"), ("meta_llama-3.1-8b-instruct-turbo", "meta"),
                    ("marin-community_marin-8b-instruct", "marin-community"), ("noprefix", "noprefix")]
FIX_COMPOSITION = [
    (("v1.0.0", 10, {"gpt": 10, "claude": 10, "llama": 10}), True),
    (("v1.0.0", 10, {"gpt": 10, "claude": 9, "llama": 10}), False),
    (("v1.15.0", 10, {"gpt": 10, "llama": 10}), True),
    (("v1.15.0", 10, {"gpt": 10, "claude": 1, "llama": 10}), False),
    (("v1.15.0", 10, {"gpt": 10, "claude": 0, "llama": 10}), True),
]
FIX_SP_ROWS = [
    ("openai", {"claude": -0.5, "gpt": 1.0, "llama": -0.5}),
    ("openai", {"claude": -0.25, "gpt": 0.5, "llama": -0.25}),
    ("anthropic", {"claude": 0.5, "gpt": 0.0, "llama": -0.5}),
    ("meta", {"claude": 0.0, "gpt": -0.5, "llama": 0.5}),
]
FIX_SP = {"gpt": (1.0, 2, 2), "claude": (0.75, 1, 3), "llama": (0.5 + 1.25 / 3.0, 1, 3)}   # assertAlmostEqual

FIX_SUITES = {
    "wildbench:subset=v2,model=a_b": "v1.0.0",
    "omni_math:subset=all,model=a_b": "v1.0.0",
    "ifeval:model=a_b": "v1.1.0",
}
FIX_SELECT = {"wildbench": {"wildbench:subset=v2,model=a_b": "v1.0.0"},
              "omni_math": {"omni_math:subset=all,model=a_b": "v1.0.0"}}

FIX_STATS = [
    {"name": {"name": "wildbench_score", "split": "test"}, "count": 1, "sum": 7.5, "mean": 7.5},
    {"name": {"name": "wildbench_score", "split": "test", "perturbation": {"name": "robustness"}}, "count": 1,
     "sum": 7.0, "mean": 7.0},
]
FIX_STAT_ENTRY = [
    (("wildbench_score", "test"), {"count": 1, "sum": 7.5, "mean": 7.5}),
    (("wildbench_score", "valid"), None),
]

FIX_GROUP = [{"header": [{"value": "Model"}, {"value": "WB Score"}, {"value": "# eval"}],
              "rows": [[{"value": "m1"}, {"value": 0.5}, {"value": 1000}],
                       [{"value": "m2"}, {"value": 0.25}, {"value": 1000}],
                       [{"value": "m3"}, {"value": "-"}, {"value": 1000}]]}]
FIX_GROUP_VALUES = [0.5, 0.25]

FIX_RANKS = ({"a": 0.5, "b": 0.75, "c": 0.5}, {"a": 2, "b": 1, "c": 2})
FIX_TAU = [
    (([1, 2, 3], [1, 2, 3]), 1.0),
    (([1, 2, 3], [3, 2, 1]), -1.0),
    (([1, 1], [1, 2]), None),
    (([1, 2, 3], [1, 3, 2]), 1.0 / 3.0),
]
FIX_MATCH = ({"a": 0.5, "b": 0.25}, [0.25, 0.5000000001, 0.9], 2)

_L = {"wildbench": 68, "omni_math": 68}
FIX_VERDICT_ON = {"fixtures": True, "listed": _L, "included": _L, "cells": _L, "matched": _L, "composition_ok": True,
                  "sp_wb": {"gpt": 0.2, "claude": 0.10, "llama": -0.1}, "lenience_spread_wb": 0.30,
                  "agree_omni": 0.85, "sp_omni": {"gpt": 0.019, "claude": -0.019, "llama": 0.0},
                  "tau_gpt_wb": 0.85, "movers_gpt_wb": 3, "v115_movers_common_wb": 1}
FIX_VERDICT_PAST = {"fixtures": False, "listed": _L, "included": {"wildbench": 68, "omni_math": 61}, "cells": _L,
                    "matched": _L, "composition_ok": False,
                    "sp_wb": {"gpt": 0.05, "claude": -0.1, "llama": None}, "lenience_spread_wb": 0.29,
                    "agree_omni": 0.84, "sp_omni": {"gpt": 0.02, "claude": 0.0, "llama": 0.0},
                    "tau_gpt_wb": 0.95, "movers_gpt_wb": 2, "v115_movers_common_wb": 0}
