"""Frozen inputs for audit 89 v2: data sources, gates, thresholds and the hand-traced fixtures (traced in
test_fb89.py). Identical to v1 except the per-benchmark HELM splits ("splits") and the v2 fixtures at the end.
Apache-2.0."""

from fractions import Fraction

# ----- Audit 77's consensus flag on the 10 most accurate included models, unchanged -----
PANEL_SIZE = 10
MIN_AGREE = 6

# ----- HELM Lite release v1.13.0 (Stanford CRFM) -----
HELM_LITE_BASE = "https://storage.googleapis.com/crfm-helm-public/lite/benchmark_output"
HELM_LITE_RELEASE = "v1.13.0"
# v2: med_qa keeps both splits HELM Lite evaluates (MedQA valid and test); openbookqa is unchanged from v1.
BENCHES = {
    "med_qa": {"prefix": "med_qa:", "fb_split": "med_qa", "splits": ("valid", "test")},
    "openbookqa": {"prefix": "commonsense:dataset=openbookqa,method=multiple_choice_joint,", "fb_split": "openbookqa",
                   "splits": ("test",)},
}
MIN_COVERAGE = Fraction(99, 100)   # a model must answer this share of the benchmark's universe
MIN_CONSISTENT = Fraction(99, 100)  # predicted letter agrees with HELM's mapped_output
MAX_EM_GAP = Fraction(5, 1000)     # our correct count vs HELM's own exact_match (v2: or quasi_exact_match)
MIN_INCLUDED = 50                  # P1: at least this many included models per benchmark
WORKERS = 12

# ----- Fantastic Bugs (stair-lab/fantastic-bugs, MIT; viewer splits only, never raw/) -----
FB_DATASET = "stair-lab/fantastic-bugs"
FB_CONFIG = "default"
FB_COLS = ["question", "answer_key", "review"]
FB_EXPECTED_ROWS = {"med_qa": 49, "openbookqa": 50}
FB_MIN_PLACED = {"med_qa": 45, "openbookqa": 45}  # P1
FB_ABORT_PLACED = 20                              # per split; below this, abort before any prediction
MIN_FB_KEY_AGREE = Fraction(95, 100)              # P1: Fantastic Bugs' key equals HELM's gold on this share

# ----- Pre-registered thresholds (unchanged) -----
THRESHOLDS = {"min_n": 5, "min_n_valid": 10, "P3_min_auc": Fraction(3, 5), "P4_max_share": Fraction(1, 4),
              "P5_max_share": Fraction(1, 4), "P6_min_share": Fraction(1, 3)}

# ----- v1 results this v2 must reproduce for OpenBookQA (nothing about OpenBookQA changed) -----
V1_OPENBOOKQA = {"universe": 500, "included": 91, "flagged_in_universe": 6, "flag_valid": (4, 48),
                 "flag_invalid": (2, 2)}

# ----- Fixture 1: review categories -----
FIX_CAT = [
    ("med_qa", "Valid. Two answers could be argued", "valid"),
    ("med_qa", "Invalid. The answer should be C", "invalid"),
    ("med_qa", "  invalid question", "invalid"),
    ("med_qa", "Validity unclear", "unclear"),
    ("med_qa", "Correct", "unclear"),
    ("med_qa", "", "unclear"),
    ("openbookqa", "Correct", "valid"),
    ("openbookqa", "Incorrect\nRelease energy", "invalid"),
    ("openbookqa", "Correctly keyed? unsure", "unclear"),
    ("mmlu_math", "Valid.", "unclear"),
]

# ----- Fixture 2: the reviewer's suggested option -----
FIX_SUGGEST = [
    ("Incorrect\nRelease energy", ["absorb energy", "Release  energy", "x", "y"], 1),
    ("Incorrect: Slow, because it cools", ["fast", "slow", "slower", "still"], 1),
    ("Incorrect slower one", ["slow", "slower", "a", "b"], None),
    ("Correct", ["a", "b"], None),
    ("Incorrect", ["a", "b"], None),
]

# ----- Fixture 3: answer keys and placement (copied functions, re-checked) -----
FIX_AK = [
    ('[{"output": {"text": "a"}, "tags": []}, {"output": {"text": " b  c "}, "tags": ["correct"]}]',
     (["a", "b c"], 1)),
    ('[{"output": {"text": "a"}, "tags": ["correct"]}, {"output": {"text": "b"}, "tags": ["correct"]}]',
     (["a", "b"], None)),
    ("not a list", (None, None)),
]
FIX_QIDS = {("med_qa", ("What is X?", ("a", "b"))): 0, ("med_qa", ("Dup Q", ("e", "f"))): 1,
            ("med_qa", ("Dup Q", ("g", "h"))): 2}
FIX_PLACE_ROWS = [("What  is X?", ["a", "b"]), ("Dup Q", ["x", "y"]), ("Missing", ["a"])]
FIX_PLACE = [(0, "exact"), (None, "ambiguous"), (None, "none")]
FIX_PLACE_COUNTS = {"exact": 1, "repaired": 0, "question_only": 0, "ambiguous": 1, "none": 1}

# ----- Fixture 4: HELM instance parsing and prediction mapping (copied functions, re-checked) -----
FIX_INSTANCES = [
    {"id": "id7", "split": "test", "input": {"text": "Q one"},
     "references": [{"output": {"text": "a"}, "tags": []}, {"output": {"text": "b"}, "tags": ["correct"]}]},
    {"id": "id3", "split": "test", "input": {"text": "Q two"},
     "references": [{"output": {"text": "c"}, "tags": ["correct"]}, {"output": {"text": "d"}, "tags": []}]},
    {"id": "id5", "split": "valid", "input": {"text": "Q three"},
     "references": [{"output": {"text": "e"}, "tags": ["correct"]}]},
]
FIX_UNIVERSE_INFO = [("med_qa", "id3", 2, 0, 0), ("med_qa", "id7", 2, 1, 1)]
FIX_PREDS = [
    {"instance_id": "id7", "train_trial_index": 0, "predicted_text": " B", "mapped_output": "b",
     "stats": {"exact_match": 1}},
    {"instance_id": "id3", "train_trial_index": 0, "predicted_text": "none of these", "mapped_output": "d",
     "stats": {"exact_match": 0}},
    {"instance_id": "id3", "train_trial_index": 1, "predicted_text": "A", "mapped_output": "c",
     "stats": {"exact_match": 1}},
]
FIX_MAPPED = {1: 1, 0: 1}

# ----- Fixture 5: verdicts -----
_P = ("P2_consensus_separates_medqa", "P3_margin_auc_medqa", "P4_medqa_valid_quiet", "P5_openbookqa_valid_quiet",
      "P6_medqa_invalid_caught")
FIX_V_CASES = [
    (((8, 20), (2, 25), (Fraction(7, 10), 20, 25), (3, 40)),
     dict(zip(_P, (True, True, True, True, True)), undecidable=[])),
    (((1, 4), (3, 9), (Fraction(1, 2), 4, 9), (12, 40)),
     dict(zip(_P, (False, False, False, False, False)), undecidable=[_P[0], _P[1], _P[2], _P[4]])),
    (((5, 15), (5, 20), (Fraction(3, 5), 15, 20), (10, 40)),
     dict(zip(_P, (True, True, True, True, True)), undecidable=[])),
    (((2, 10), (2, 10), (None, 10, 10), (0, 48)),
     dict(zip(_P, (False, False, True, True, False)), undecidable=[_P[1]])),
]

# ----- Fixture 6 (v2): both splits, and quasi_exact_match when exact_match is missing -----
FIX_SPLITS_VT = ("valid", "test")
FIX_UNIVERSE_INFO_VT = [("med_qa", "id3", 2, 0, 0), ("med_qa", "id5", 1, 0, 1), ("med_qa", "id7", 2, 1, 2)]
FIX_PREDS_QUASI = [
    {"instance_id": "id7", "train_trial_index": 0, "predicted_text": "B", "mapped_output": "b",
     "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "id5", "train_trial_index": 0, "predicted_text": "A", "mapped_output": "e",
     "stats": {"quasi_exact_match": 1.0}},
    {"instance_id": "id3", "train_trial_index": 0, "predicted_text": "B", "mapped_output": "d",
     "stats": {"exact_match": 0, "quasi_exact_match": 1.0}},
]
FIX_MAPPED_QUASI = {2: 1, 1: 0, 0: 1}
FIX_QUASI_COUNTS = {"valid": 3, "consistent": 3, "em_correct": 2, "em_from_quasi": 2}
