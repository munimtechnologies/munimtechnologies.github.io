"""Hand-traced fixture for the MultiNLI per-genre annotator-agreement census.

Seven synthetic records across two genres (government, telephone), worked out by hand into TARGET so the
per-genre tally logic is checked against a known answer before it touches the real MultiNLI files. Each
record pairs a genre, a released gold label, and the five individual annotator labels.

government:
  g1 gold=e labels[e,e,e,e,e] -> agree5 (unanimous), majority e==gold, matches 5
  g2 gold=n labels[n,n,n,n,e] -> agree4,           majority n==gold, matches 4
  g3 gold=e labels[e,e,e,n,c] -> agree3,           majority e==gold, matches 3
    government: n=3 valid=3 dash=0 unanimous=1 b5=1 b4=1 b3=1 gold_eq_majority=3 label_matches=12 labels=15
telephone:
  t1 gold=c labels[c,c,c,n,n] -> agree3,           majority c==gold, matches 3
  t2 gold=-  labels[e,e,n,n,c] -> dash (2-2-1, no majority)
  t3 gold=n labels[n,n,n,n,c] -> agree4,           majority n==gold, matches 4
  t4 gold=e labels[e,e,e,c,c] -> agree3,           majority e==gold, matches 3
    telephone:  n=4 valid=3 dash=1 unanimous=0 b5=0 b4=1 b3=2 gold_eq_majority=3 label_matches=10 labels=15
"""

NAMES_3WAY = ("e", "n", "c")


def _rec(genre, gold, labels):
    return {"genre": genre, "gold": gold, "annotator_labels": labels}


FIXTURE = [
    _rec("government", "entailment", ["entailment"] * 5),
    _rec("government", "neutral", ["neutral", "neutral", "neutral", "neutral", "entailment"]),
    _rec("government", "entailment", ["entailment", "entailment", "entailment", "neutral", "contradiction"]),
    _rec("telephone", "contradiction", ["contradiction", "contradiction", "contradiction", "neutral", "neutral"]),
    _rec("telephone", "-", ["entailment", "entailment", "neutral", "neutral", "contradiction"]),
    _rec("telephone", "neutral", ["neutral", "neutral", "neutral", "neutral", "contradiction"]),
    _rec("telephone", "entailment", ["entailment", "entailment", "entailment", "contradiction", "contradiction"]),
]


TARGET = {
    "government_n": 3, "government_valid": 3, "government_dash": 0, "government_unanimous": 1,
    "government_b5": 1, "government_b4": 1, "government_b3": 1, "government_bother": 0,
    "government_gold_eq_majority": 3, "government_label_matches": 12, "government_labels": 15,
    "telephone_n": 4, "telephone_valid": 3, "telephone_dash": 1, "telephone_unanimous": 0,
    "telephone_b5": 0, "telephone_b4": 1, "telephone_b3": 2, "telephone_bother": 0,
    "telephone_gold_eq_majority": 3, "telephone_label_matches": 10, "telephone_labels": 15,
}

# P3 threshold: genres must span more than this in unanimous rate for "meaningful variation" to hold.
P3_SPREAD_THRESHOLD = 0.05

# The two raw dev files together are 10,000 + 10,000 rows (familiar 9,815 / 9,832 are the POST-dash-filter
# evaluation counts). Used only as a sanity flag (rows_as_expected), never bet on.
EXPECTED_TOTAL_DEV_ROWS = 20000

# The ten MultiNLI dev genres: five matched (in-training-domain) and five mismatched (out-of-domain).
MATCHED_GENRES = ("fiction", "government", "slate", "telephone", "travel")
MISMATCHED_GENRES = ("facetoface", "letters", "nineeleven", "oup", "verbatim")
