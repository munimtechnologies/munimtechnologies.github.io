"""Hand-traced fixture for the ChaosNLI x original-agreement cross-link census.

Seven synthetic joined records, worked out by hand into TARGET, so the cross-tabulation logic is checked
against a known answer before it touches the real SNLI/MNLI/ChaosNLI files. Each record pairs an original
example (its gold and up to 5 annotator votes) with its ChaosNLI 100-vote record (old_label + counts
[E,N,C]). The fixture exercises every bucket (unanimous 5, four, bare-majority 3, original "-" = dash) and
both ChaosNLI outcomes (old == / != 100-vote plurality; strict / no strict majority), plus one record
whose old_label deliberately differs from the original gold (to exercise n_old_eq_origgold).

  r1 og=e votes[e,e,e,e,e] (5) old=e counts[90,5,5]  -> plur e, strict e   ; old==plur, strict
  r2 og=n votes[n,n,n,n,n] (5) old=n counts[10,80,10] -> plur n, strict n   ; old==plur, strict
  r3 og=c votes[c,c,c,c,n] (4) old=c counts[5,40,55]  -> plur c, strict c   ; old==plur, strict
  r4 og=e votes[e,e,e,n,c] (3) old=e counts[45,30,25] -> plur e, no strict  ; old==plur, no strict
  r5 og=n votes[n,n,n,e,c] (3) old=n counts[48,46,6]  -> plur e, no strict  ; old!=plur, no strict
  r6 og=e votes[e,e,e,e,n] (4) old=c counts[20,20,60] -> plur c, strict c   ; old==plur, strict; old!=og
  r7 og=-  votes[e,n,c,e,n] (dash) old=e counts[55,30,15] -> plur e, strict e; old==plur, strict

n_joined=7 ; n_orig_gold_valid=6 ; n_orig_gold_dash=1 ; n_old_eq_origgold=5 (r1-r5; r6's old=c!=og=e)
b5: n=2 old_eq_plur=2 old_diff_plur=0 strict=2 no_strict=0
b4: n=2 old_eq_plur=2 old_diff_plur=0 strict=2 no_strict=0
b3: n=2 old_eq_plur=1 old_diff_plur=1 strict=0 no_strict=2
bdash: n=1 old_eq_plur=1 old_diff_plur=0 strict=1 no_strict=0
bother: all 0
"""

NAMES_3WAY = ("e", "n", "c")


def _rec(uid, og, votes, old, counts):
    return {"uid": uid, "subset": "snli", "orig_gold": og, "annotator_labels": votes,
            "old": old, "counts": counts, "names": NAMES_3WAY}


FIXTURE = [
    _rec("r1", "entailment", ["entailment"] * 5, "entailment", [90, 5, 5]),
    _rec("r2", "neutral", ["neutral"] * 5, "neutral", [10, 80, 10]),
    _rec("r3", "contradiction", ["contradiction", "contradiction", "contradiction", "contradiction", "neutral"], "contradiction", [5, 40, 55]),
    _rec("r4", "entailment", ["entailment", "entailment", "entailment", "neutral", "contradiction"], "entailment", [45, 30, 25]),
    _rec("r5", "neutral", ["neutral", "neutral", "neutral", "entailment", "contradiction"], "neutral", [48, 46, 6]),
    _rec("r6", "entailment", ["entailment", "entailment", "entailment", "entailment", "neutral"], "contradiction", [20, 20, 60]),
    _rec("r7", "-", ["entailment", "neutral", "contradiction", "entailment", "neutral"], "entailment", [55, 30, 15]),
]


TARGET = {
    "n_joined": 7,
    "n_orig_gold_valid": 6,
    "n_orig_gold_dash": 1,
    "n_old_eq_origgold": 5,
    "b5_n": 2, "b5_old_eq_plur": 2, "b5_old_diff_plur": 0, "b5_strict": 2, "b5_no_strict": 0,
    "b4_n": 2, "b4_old_eq_plur": 2, "b4_old_diff_plur": 0, "b4_strict": 2, "b4_no_strict": 0,
    "b3_n": 2, "b3_old_eq_plur": 1, "b3_old_diff_plur": 1, "b3_strict": 0, "b3_no_strict": 2,
    "bdash_n": 1, "bdash_old_eq_plur": 1, "bdash_old_diff_plur": 0, "bdash_strict": 1, "bdash_no_strict": 0,
    "bother_n": 0, "bother_old_eq_plur": 0, "bother_old_diff_plur": 0, "bother_strict": 0, "bother_no_strict": 0,
}

# Minimum fraction of ChaosNLI SNLI+MNLI records we expect to join to a loaded original example (P1).
MIN_JOIN_COVERAGE = 0.99

# ChaosNLI subset -> which original files its uids (== pairID) should be found in.
#   SNLI uids look like "3948003394.jpg#1r1n" (SNLI dev and test both carry 5 annotator_labels);
#   MNLI-matched uids look like "20648n" (MNLI matched dev carries 5 annotator_labels).
# We load dev+test for SNLI and both dev files for MNLI to maximise join coverage; orphans are reported.
EXPECTED_SUBSET_ROWS = {"snli": 1514, "mnli_m": 1599}
