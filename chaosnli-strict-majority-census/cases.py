"""Hand-traced fixture for the ChaosNLI strict-majority / old-gold-stability census.

Five synthetic 3-way (e/n/c) records, worked out by hand into TARGET, so the counting logic is checked
against a known answer before it touches the real ChaosNLI files. The fixture exercises every path: old
gold matching the 100-vote plurality and a strict majority; old gold differing from the plurality and
from a strict majority; and three records with NO strict majority (no label > 50 of 100), one of which
is also a tie at the top. Label counts are ordered [E, N, C] and each sums to 100, matching the released
`label_count` field.

Records (old gold ; counts [E,N,C] ; plurality ; strict):
  r1 old=e [70,20,10] -> plurality e, strict e      ; old==maj, strict exists, old==strict
  r2 old=n [55,30,15] -> plurality e, strict e      ; old!=maj, strict exists, old!=strict
  r3 old=e [40,35,25] -> plurality e, no strict      ; old==maj, no strict, old on no-strict
  r4 old=c [30,30,40] -> plurality c, no strict      ; old==maj, no strict, old on no-strict
  r5 old=n [45,50,5]  -> plurality n, no strict(50)  ; old==maj, no strict, old on no-strict

n_records=5 ; n_sum100=5 ; n_old_eq_majority=4 ; n_old_differs_majority=1 ; n_majority_eq_plurality=5
n_strict_exists=2 ; n_no_strict_majority=3 ; n_old_eq_strict=1 ; n_old_differs_strict=1
n_old_on_no_strict=3
"""

NAMES_3WAY = ("e", "n", "c")
NAMES_2WAY = ("1", "2")


def _rec(uid, old, counts, majority, names=NAMES_3WAY):
    return {"uid": uid, "old": old, "majority": majority, "counts": counts, "names": names}


# majority is set to each record's computed plurality, so n_majority_eq_plurality == n_records here.
FIXTURE = [
    _rec("r1", "e", [70, 20, 10], "e"),
    _rec("r2", "n", [55, 30, 15], "e"),
    _rec("r3", "e", [40, 35, 25], "e"),
    _rec("r4", "c", [30, 30, 40], "c"),
    _rec("r5", "n", [45, 50, 5], "n"),
]


TARGET = {
    "n_records": 5,
    "n_sum100": 5,
    "n_old_eq_majority": 4,
    "n_old_differs_majority": 1,
    "n_majority_eq_plurality": 5,
    "n_strict_exists": 2,
    "n_no_strict_majority": 3,
    "n_old_eq_strict": 1,
    "n_old_differs_strict": 1,
    "n_old_on_no_strict": 3,
}

# Documented ChaosNLI card figures the real-data run verifies (old_label != majority_label counts).
CARD_OLD_DIFFERS_MAJORITY = {"snli": 378, "mnli_m": 508}

# Released subset row counts (Nie, Zhou, Bansal 2020).
SUBSET_ROWS = {"snli": 1514, "mnli_m": 1599, "alphanli": 1532}

# Which label-name tuple and count ordering each subset uses.
SUBSET_NAMES = {"snli": NAMES_3WAY, "mnli_m": NAMES_3WAY, "alphanli": NAMES_2WAY}
