"""Data source, gates, thresholds and hand-traced fixtures for audit 94 (traces in test_grade94.py). Apache-2.0."""

from fractions import Fraction

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/classic/benchmark_output"
RELEASE = "v0.4.0"
RUNS_INDEX = HELM_BASE + "/releases/" + RELEASE + "/runs_to_run_suites.json"
WORKERS = 3
TOL = 1e-6

# Gates
MIN_RUNS = 200                       # separate-method runs listed in the release
MIN_INCLUDED = Fraction(95, 100)     # P1: share of listed runs included
ABORT_INCLUDED = Fraction(1, 2)      # abort below this
MAX_INCONSISTENT = Fraction(1, 1000)  # P1: inconsistent records / records

THRESHOLDS = {"P4_max_share": Fraction(1, 100), "P5_top_models": 3, "P5_min_share": Fraction(1, 2),
              "P6_min_move": 0.01, "P7_min_share": Fraction(1, 2)}

PRINT_TIES = 60      # tie lines printed to the job log for the hand-read (stdout only, never published)
PER_RUN_PRINT = 3

# ---------------- fixtures ----------------

def _ref(text, ok=False):
    return {"output": {"text": text}, "tags": ["correct"] if ok else []}


FIX_INSTANCES = [
    {"id": "id1", "split": "valid", "references": [_ref("a"), _ref("b", True), _ref("c")]},
    {"id": "id2", "split": "valid", "references": [_ref("x", True), _ref("y"), _ref("x ")]},
    {"id": "id3", "split": "valid", "references": [_ref("p", True), _ref("q")]},
    {"id": "id4", "split": "valid", "references": [_ref("m"), _ref("n", True), _ref("o"), _ref("r")]},
    {"id": "id1", "split": "valid", "perturbation": {"name": "mild_mix"},
     "references": [_ref("A", True), _ref("B"), _ref("C")]},
]


def _rec(iid, em, pi, trial=0, pert=None):
    r = {"instance_id": iid, "train_trial_index": trial, "stats": {"exact_match": em, "predicted_index": pi}}
    if pert:
        r["perturbation"] = {"name": pert, "robustness": True}
    return r


FIX_PREDS = [
    _rec("id1", 1.0, 1.0),                  # r1 plain, F 1
    _rec("id2", 1.0, 2.0),                  # r2 old_tie (pred 'x ' duplicates correct 'x'), F 0
    _rec("id3", 0.5, 1.0),                  # r3 frac, F 0
    _rec("id4", 0.0, 0.0),                  # r4 plain, F 0
    _rec("id1", 0.0, 1.0, pert="mild_mix"),  # r5 inconsistent (perturbed; correct from the unperturbed copy)
    _rec("id4", 0.25, 1.0, pert="mild_mix"),  # r6 frac, F 1 (perturbed)
    _rec("id3", 1.0, 0.0, trial=1),         # r7 plain, F 1, second trial
    _rec("id9", 1.0, 0.0),                  # r8 unmatched, F = em
]

FIX_RUN_TARGET = {
    "counts": {"records": 8, "plain": 3, "old_tie": 1, "frac": 2, "inconsistent": 1, "unmatched": 1, "missing": 0},
    "unpert_all": {"n": 6, "pub": 4.5, "f": 3.0},
    "unpert_t0": {"n": 5, "pub": 3.5, "f": 2.0},
    "ties": [("id2", None, "old_tie", 1.0, True, 2, [0]), ("id3", None, "frac", 0.5, False, 1, [0]),
             ("id4", "mild_mix", "frac", 0.25, False, 1, [1])],
    "frac_values": {"0.5": 1, "0.25": 1},
}

FIX_STATS = [
    {"name": {"name": "exact_match", "split": "valid"}, "mean": 0.7},
    {"name": {"name": "exact_match", "split": "valid", "perturbation": {"name": "mild_mix"}}, "mean": 0.1},
    {"name": {"name": "num_instances", "split": "valid"}, "mean": 5.0},
    {"name": {"name": "exact_match", "split": "test"}, "mean": 0.3},
]
FIX_STAT_CASES = [(("exact_match", "valid"), 0.7), (("num_instances", "valid"), 5.0),
                  (("exact_match", "test"), 0.3), (("max_prob", "valid"), None)]

# (pub_em, num_instances) -> (basis, ok) for the FIX_RUN_TARGET summary
FIX_REPRO_CASES = [((0.75, 5.0), ("all", True)), ((0.7, 5.0), ("t0", True)), ((0.6, 5.0), (None, False)),
                   ((0.75, 4.0), (None, False)), ((None, 5.0), (None, False))]

FIX_NAMES = [
    ("commonsense:dataset=hellaswag,method=multiple_choice_separate_original,model=openai_ada,"
     "data_augmentation=canonical",
     "openai_ada", "multiple_choice_separate_original",
     "commonsense:dataset=hellaswag,method=multiple_choice_separate_original,data_augmentation=canonical",
     "commonsense:dataset=hellaswag"),
    ("blimp:phenomenon=binding,method=multiple_choice_separate_calibrated,model=together_bloom",
     "together_bloom", "multiple_choice_separate_calibrated",
     "blimp:phenomenon=binding,method=multiple_choice_separate_calibrated", "blimp:phenomenon=binding"),
    ("mmlu:subject=abstract_algebra,method=multiple_choice_joint,model=openai_davinci",
     "openai_davinci", "multiple_choice_joint", "mmlu:subject=abstract_algebra,method=multiple_choice_joint",
     "mmlu:subject=abstract_algebra"),
]

FIX_DUP_CASES = [((["x", "y", "x "], [0]), True), ((["p", "q"], [0]), False), ((["a", "a"], [0, 1]), False),
                 ((["a", "b", "b"], [1]), True), (([], []), False)]

FIX_RANKS_IN = {"a": 0.9, "b": 0.8, "c": 0.8, "d": 0.5}
FIX_RANKS_OUT = {"a": 1, "b": 2, "c": 2, "d": 4}

FIX_TOP_IN = {"m1": 5, "m2": 1, "m3": 3, "m4": 2}   # top 3 = 5 + 3 + 2 = 10
FIX_TOP_OUT = 10

# (old_tie, frac, records, topk, max_move, dup) -> verdicts
FIX_V_CASES = [
    ((5, 0, 1000, 4, 0.02, 3), {"P2_ties_exist": True, "P3_pre_fix_rule": True, "P4_rare": True,
                                "P5_concentrated": True, "P6_headline_moves": True, "P7_duplicates": True}),
    ((0, 0, 1000, 0, 0.0, 0), {"P2_ties_exist": False, "P3_pre_fix_rule": False, "P4_rare": True,
                               "P5_concentrated": False, "P6_headline_moves": False, "P7_duplicates": False}),
    ((3, 2, 100, 2, 0.005, 2), {"P2_ties_exist": True, "P3_pre_fix_rule": False, "P4_rare": False,
                                "P5_concentrated": False, "P6_headline_moves": False, "P7_duplicates": False}),
]
