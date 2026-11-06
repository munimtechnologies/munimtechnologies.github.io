"""Frozen inputs for audit 86: data sources, gates, the flag rule, thresholds and the hand-traced fixtures (traced in
test_gsm86.py). Apache-2.0."""

from fractions import Fraction

# ----- Data -----
GSM8K = {"hf": "openai/gsm8k", "config": "main", "split": "test", "cols": ["question", "answer"]}
PLATINUM = {"hf": "madrylab/gsm8k-platinum", "config": "main", "split": "test",
            "cols": ["question", "answer", "cleaning_status"]}
HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/lite/benchmark_output"
HELM_RELEASE = "v1.13.0"
HELM_PREFIX = "gsm:"
WORKERS = 8

# ----- Gates (P1) -----
# From the GSM8K-Platinum dataset card: 1,319 test questions, 219 flagged by a model, 110 removed, 10 relabelled,
# 99 verified, so 1,209 kept rows of which 1,100 were never flagged.
EXPECTED = {"gsm_rows": 1319, "plat_rows": 1209,
            "labels": {"consensus": 1100, "rejected": 110, "revised": 10, "verified": 99}}
ABORT_MAX_PLAT_UNMATCHED = 5          # more Platinum rows than this not found in GSM8K: abort
UNIVERSE_RANGE = (900, 1319)          # HELM Lite's GSM8K questions joined to GSM8K test
MIN_INSTANCE_JOIN = Fraction(99, 100)  # share of a run's instances that must join GSM8K by question text
MIN_KEY_AGREE = Fraction(99, 100)      # share of universe questions where HELM's key equals GSM8K's '####' answer
MIN_COVERAGE = Fraction(99, 100)       # a model must answer this share of the universe
MIN_CONSISTENT = Fraction(99, 100)     # our transcribed scorer must equal HELM's recorded score on this share
MIN_INCLUDED = 60

# ----- The flag (audit 77's rule, on free-response answers) -----
PANEL_SIZE = 10
MIN_AGREE = 6
N_STRATA = 5
NK_MIN_COV = 2
TOP20_SIZE = 20
TOP20_MIN_AGREE = 12

THRESHOLDS = {"P2_min_precision": Fraction(1, 2), "P4_min_auc": Fraction(3, 4), "P5_min_recall": Fraction(1, 4),
              "P6_min_flagged": 10}

# ----- Fixture 1: HELM's scorer, transcribed -----
FIX_FINAL = [("The answer is 15 eggs.", "15"), ("It costs $1,000.", "1000"), ("no number here", ""),
             ("x = 3.5.", "3.5"), ("Answer: -7", "-7"), ("12a34", "12a34"), ("so 4 apples, b", ""), ("", ""),
             (None, "")]
FIX_EM = [("15", "15", 1), ("15", "", 0), ("15", " 15 ", 1), ("15", "16", 0)]
FIX_FNEM = [("The answer is 120.", "so 120 minutes. The answer is 120.", 1),
            ("The answer is 5.", "The answer is 5, done", 1),
            ("The answer is 5.", "The answer is 6.", 0)]
FIX_GSM_FINAL = [("a <<1+1=2>>2\n#### 1,234", "1234"), ("no marker", ""), ("#### -3 ", "-3")]

# ----- Fixture 2: Platinum labels -----
FIX_GSM_ROWS = [("Q a", "x #### 5"), ("Q  b", "#### 7"), ("Q c", "#### 1,000"), ("Q d", "#### 2"), ("Q d", "#### 2")]
FIX_PLAT_ROWS = [("Q a", "#### 5", "consensus"), ("Q b", "#### 8", "revised"), ("Q d", "#### 2", "verified"),
                 ("Q z", "#### 1", "consensus")]
FIX_LABELS = {0: "consensus", 1: "revised", 2: "rejected", 3: "duplicate", 4: "duplicate"}
FIX_PLAT_ANSWER = {0: "5", 1: "8"}
FIX_LABEL_COUNTS = {"gsm_rows": 5, "plat_rows": 4, "matched": 2, "to_duplicate": 1, "unmatched": 1,
                    "matched_twice": 0,
                    "labels": {"consensus": 1, "duplicate": 2, "rejected": 1, "revised": 1}}

# ----- Fixture 3: run selection -----
FIX_RUNS = {"gsm:model=a_x": "v1.0.0", "gsm:model=a_x,stop=none": "v1.4.0", "gsm:model=b_y": "v1.2.0",
            "gsm:model=b_y,stop=none": "v1.2.0", "mmlu:subject=x,model=a_x": "v1.0.0",
            "gsm:model=c_z,stop=none": "v1.10.0"}
FIX_RUNS_TARGET = ({"a_x": ("gsm:model=a_x,stop=none", "v1.4.0"), "b_y": ("gsm:model=b_y", "v1.2.0"),
                    "c_z": ("gsm:model=c_z,stop=none", "v1.10.0")}, 2)

# ----- Fixture 4: votes, flags, precision, recall, AUC, budget -----
FIX_PANEL = ["m1", "m2", "m3"]
FIX_KEYS = {1: "5", 2: "5", 3: "5", 4: "5", 5: "5", 6: "5"}
FIX_ANSWERS = {"m1": {1: "6", 2: "5", 3: "6", 4: "6", 5: "6", 6: "9"},
               "m2": {1: "6", 2: "5", 3: "7", 4: "6", 5: "5", 6: "9"},
               "m3": {1: "5", 2: "5", 3: "", 5: "7", 6: "9"}}
FIX_VIEW = {1: ({"6": 2, "5": 1}, 1, 0, 3), 2: ({"5": 3}, 3, 0, 3), 3: ({"6": 1, "7": 1}, 0, 1, 3),
            4: ({"6": 2}, 0, 1, 2), 5: ({"6": 1, "5": 1, "7": 1}, 1, 0, 3), 6: ({"9": 3}, 0, 0, 3)}
FIX_CONS = {1: True, 2: False, 3: False, 4: True, 5: False, 6: True}
FIX_UNAN = {1: False, 2: False, 3: False, 4: False, 5: False, 6: True}
FIX_ANYW = {1: True, 2: False, 3: True, 4: True, 5: True, 6: True}
FIX_SCORE = {1: 1, 2: -3, 3: 1, 4: 2, 5: 0, 6: 3}
FIX_NOKEY = {1: False, 2: False, 3: True, 4: True, 5: False, 6: True}
FIX_LAB4 = {1: "revised", 2: "consensus", 3: "verified", 4: "rejected", 5: "consensus", 6: "duplicate"}
FIX_PREC = {"cons": (2, 2), "anyw": (2, 4), "nokey": (1, 2), "anyw_reviewed": (2, 3)}
FIX_RECALL = {"cons": (2, 2), "nokey": (1, 2)}
FIX_AUC = Fraction(11, 12)
FIX_BUDGET = (3, (Fraction(3, 2), Fraction(2)))
FIX_ACC = {"a": (9, 10), "b": (8, 10), "c": (9, 10), "d": (0, 0)}
FIX_RANKED = ["a", "c", "b", "d"]

# ----- Fixture 5: verdicts -----
FIX_V_CASES = [
    (((6, 10), (8, 40), Fraction(4, 5), (6, 20), (9, 12), 12, (Fraction(6), Fraction(10)),
      (Fraction(3), Fraction(10))),
     {"P2_consensus_precision": True, "P3_consensus_beats_any_wrong": True, "P4_margin_auc": True,
      "P5_recall": True, "P6_no_key_at_least_consensus": True, "P7_strength_matters": True}),
    (((4, 10), (8, 10), None, (4, 20), (9, 9), 9, (Fraction(1), Fraction(10)), (Fraction(2), Fraction(10))),
     {"P2_consensus_precision": False, "P3_consensus_beats_any_wrong": False, "P4_margin_auc": False,
      "P5_recall": False, "P6_no_key_at_least_consensus": False, "P7_strength_matters": False}),
]
