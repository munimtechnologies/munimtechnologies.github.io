# cases.py -- pre-registered evaluator fixture for the ANLI gold-conflict census.
#
# Written BEFORE any real ANLI data is read. The 7-row fixture exercises every branch:
#   * an exact-duplicate pair with CONFLICTING labels            (rows 1,2: e vs n)
#   * an exact-duplicate pair with the SAME label (not a conflict) (rows 3,4: e, e)
#   * a pair that becomes a duplicate only after normalization,
#     with a conflicting label vs its twin (rows 5,6: n vs c, via
#     double-space + case folding)
#   * a unique pair                                              (row 7)
#
# The fixture uses the "premise" key; the real ANLI v1.0 raw jsonl names that field
# "context" (job.py detects the real key -- see detect_premise_key).

ROWS = [
    {"premise": "A man is playing guitar.", "hypothesis": "A person makes music.", "label": "e"},
    {"premise": "A man is playing guitar.", "hypothesis": "A person makes music.", "label": "n"},
    {"premise": "The dog ran fast.", "hypothesis": "An animal moved.", "label": "e"},
    {"premise": "The dog ran fast.", "hypothesis": "An animal moved.", "label": "e"},
    {"premise": "Birds fly south.", "hypothesis": "Creatures travel.", "label": "n"},
    {"premise": "Birds  fly  south.", "hypothesis": "creatures travel.", "label": "c"},
    {"premise": "Rain falls down.", "hypothesis": "Water descends.", "label": "e"},
]

PREMISE_KEY = "premise"
HYPOTHESIS_KEY = "hypothesis"
LABEL_KEY = "label"

# Hand-traced expected counts (integer-only public summary).
TARGET = {
    "rows_valid": 7,
    "distinct_exact_pairs": 5,
    "distinct_norm_pairs": 4,
    "exact_conflict_pairs": 1,
    "norm_conflict_pairs": 2,
}
