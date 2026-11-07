"""Frozen inputs for audit 88: data sources, gates, thresholds and the hand-traced fixtures (traced in
test_fb88.py). Apache-2.0."""

from fractions import Fraction

# ----- Audit 77's consensus flag on HELM's 10 most accurate models, unchanged -----
PANEL_SIZE = 10
MIN_AGREE = 6

# ----- Reproduction gate: audit 80 (part of P1) -----
EXPECTED_80 = {
    "universe": 13984,
    "included": 78,
    "panel": ["anthropic_claude-3-5-sonnet-20241022", "anthropic_claude-3-5-sonnet-20240620",
              "deepseek-ai_deepseek-v3", "google_gemini-1.5-pro-002", "anthropic_claude-3-opus-20240229",
              "openai_gpt-4o-2024-08-06", "meta_llama-3.1-405b-instruct-turbo", "openai_gpt-4o-2024-05-13",
              "openai_gpt-4-0613", "qwen_qwen2.5-72b-instruct-turbo"],
    "flagged": {"all": 1207, "miskey": 80, "ok": 354, "other_error": 50, "unsure_or_conflict": 8,
                "unreviewed": 715},
    "precision": (130, 484),
}

# ----- HELM MMLU (as audits 80-87) -----
N_SUBJECTS = 57
HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/mmlu/benchmark_output"
HELM_RELEASE = "v1.13.0"
MIN_COVERAGE = Fraction(99, 100)
MIN_CONSISTENT = Fraction(99, 100)
MAX_EM_GAP = Fraction(5, 1000)
WORKERS = 12

# ----- MMLU-Redux 2.0 (as audits 80-87) -----
REDUX_DATASET = "edinburgh-dawg/mmlu-redux-2.0"
REDUX_SPLIT = "test"
ABORT_REDUX_JOINED = 4000

# ----- Fantastic Bugs (stair-lab/fantastic-bugs, MIT; viewer splits only, never raw/) -----
FB_DATASET = "stair-lab/fantastic-bugs"
FB_CONFIG = "default"
FB_COLS = ["question", "answer_key", "review"]
FB_EXPECTED_ROWS = {"mmlu_clinical_knowledge": 50, "mmlu_professional_medicine": 57, "mmlu_5subject": 74,
                    "mmlu_math": 8, "gsm": 16}
FB_MIN_PLACED = 170                   # P1: at least this many of the 189 MMLU rows placed in the HELM universe
FB_ABORT_PLACED = 100                 # below this, abort before any prediction (diagnostics in results.json)
MIN_FB_KEY_AGREE = Fraction(95, 100)  # P1: Fantastic Bugs' tagged key equals HELM's gold on this share of placed rows

# ----- GSM8K, GSM8K-Platinum, HELM Lite and audit 86's published candidates -----
GSM8K = {"hf": "openai/gsm8k", "config": "main", "split": "test", "cols": ["question", "answer"]}
PLATINUM = {"hf": "madrylab/gsm8k-platinum", "config": "main", "split": "test",
            "cols": ["question", "answer", "cleaning_status"]}
HELM_LITE_BASE = "https://storage.googleapis.com/crfm-helm-public/lite/benchmark_output"
HELM_LITE_RELEASE = "v1.13.0"
AUDIT86_CANDIDATES = ("https://raw.githubusercontent.com/munimtechnologies/munimtechnologies.github.io/main/"
                      "gsm8k-helm-consensus-platinum/candidates.json")
KEPT = ("consensus", "verified")

# ----- Pre-registered thresholds -----
THRESHOLDS = {"min_n": 5, "min_n_valid": 10, "P2_min_share": Fraction(1, 2), "P4_max_share": Fraction(1, 4),
              "P6_min_share": Fraction(1, 2)}

# ----- Fixture 1: review categories -----
FIX_CAT = [
    ("mmlu_clinical_knowledge", "Valid question. Classic presentation", "valid"),
    ("mmlu_clinical_knowledge", "  valid", "valid"),
    ("mmlu_professional_medicine", "Poor question: None of the options fit", "other"),
    ("mmlu_clinical_knowledge", "Incorrect answer, should be B", "key"),
    ("mmlu_professional_medicine", "Poor question. The key is debatable", "key"),
    ("mmlu_clinical_knowledge", "Validity unclear", "other"),
    ("mmlu_5subject", "key", "key"),
    ("mmlu_5subject", "key bad key", "key"),
    ("mmlu_5subject", "item bad key bad item due to formatting", "key"),
    ("mmlu_5subject", "construct all above/all True", "other"),
    ("mmlu_5subject", "item missing information", "other"),
    ("mmlu_5subject", "keyboard issue", "other"),
    ("mmlu_5subject", "Key, wrong option", "key"),
    ("mmlu_math", "bad key, multiple correct", "key"),
    ("mmlu_math", "formatting", "other"),
    ("gsm", "Incorrect Answer Key, should be 5", "key"),
    ("gsm", "Ambiguous Question, could be read two ways", "other"),
    ("gsm", "HELM grades incorrectly. Subject: x", "other"),
]

# ----- Fixture 2: Mac Roman mojibake -----
FIX_MOJI = [
    ("Caf√©‚Äôs Q", "Café’s Q"),
    ("plain text", "plain text"),
    ("Raoult’s law", "Raoult’s law"),
    ("μ = 2", "μ = 2"),
]

# ----- Fixture 3: answer keys -----
FIX_AK = [
    ('[{"output": {"text": "a"}, "tags": []}, {"output": {"text": " b  c "}, "tags": ["correct"]}]',
     (["a", "b c"], 1)),
    ('[{"output": {"text": "a"}, "tags": ["correct"]}, {"output": {"text": "b"}, "tags": ["correct"]}]',
     (["a", "b"], None)),
    ("[{'output': {'text': 'a'}, 'tags': ['correct']}]", (["a"], 0)),
    ("not a list", (None, None)),
    ('{"a": 1}', (None, None)),
    ("[1, 2]", (None, None)),
    (None, (None, None)),
]

# ----- Fixture 4: placement -----
FIX_QIDS = {("s1", ("What is X?", ("a", "b"))): 0, ("s1", ("Café’s Q", ("c", "d"))): 1,
            ("s2", ("Dup Q", ("e", "f"))): 2, ("s3", ("Dup Q", ("g", "h"))): 3,
            ("s2", ("Only text", ("i", "j"))): 4}
FIX_PLACE_ROWS = [("What  is X?", ["a", "b"]), ("Caf√©‚Äôs Q", ["c", "d"]),
                  ("Dup Q", ["e", "f"]), ("Dup Q", ["x", "y"]), ("Only text", ["i", "J"]), ("Missing", ["a"])]
FIX_PLACE = [(0, "exact"), (1, "repaired"), (2, "exact"), (None, "ambiguous"), (4, "question_only"), (None, "none")]
FIX_PLACE_COUNTS = {"exact": 2, "repaired": 1, "question_only": 1, "ambiguous": 1, "none": 1}

# ----- Fixture 5: Redux groups, units, kappa -----
FIX_RGROUP = [(None, "unreviewed"), ("wrong_groundtruth", "miskey"), ("ok", "ok"),
              ("no_correct_answer", "other_error"), ("expert", "unsure"), ("conflict", "unsure")]
FIX_UNITS = [{"qid": 3}, {"qid": None}, {"qid": 3}, {"qid": 1}]
FIX_UNITS_KEPT = ([{"qid": 3}, {"qid": 1}], 1)
FIX_KAPPA = [([(True, True), (True, True), (True, False), (False, False)], Fraction(1, 2)),
             ([(True, True), (True, True)], None),
             ([], None),
             ([(True, False), (False, True)], Fraction(-1))]

# ----- Fixture 6: verdicts -----
_P = ("P2_redux_confirms_fb_keys", "P3_key_type_agrees", "P4_redux_clears_fb_valid", "P5_consensus_separates",
      "P6_consensus_catches_fb_keys", "P7_gsm_kept_flag_confirmed")
FIX_V_CASES = [
    (((6, 10), (4, 10), (1, 8), (2, 20), (7, 12), (5, 40), (1, 3)),
     dict(zip(_P, (True, True, True, True, True, True)), undecidable=[])),
    (((2, 4), (1, 4), (0, 9), (3, 9), (3, 10), (3, 10), (0, 3)),
     dict(zip(_P, (False, False, False, False, False, False)), undecidable=list(_P[:3]))),
    (((5, 10), (5, 10), (5, 10), (5, 20), (5, 10), (0, 5), (0, 0)),
     dict(zip(_P, (True, False, True, True, True, False)), undecidable=[_P[5]])),
]
