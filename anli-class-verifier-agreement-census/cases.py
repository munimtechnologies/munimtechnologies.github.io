"""Hand-traced fixture for the ANLI per-gold-class verifier-agreement census.

Six synthetic verifier lines and six synthetic main examples, worked out by hand into TARGET, so the join
+ per-class counting logic is checked against a known answer before it touches the real ANLI files. The
fixture exercises every path: a unanimous-pair match, a unanimous-pair that differs from gold, a 2-1
majority match (k=3), a 1-1-1 no-majority (k=3), an orphan verifier uid, and a train example with a
verifier line (audit 39 showed the verifier file also covers train).

Verifier lines (uid -> labels) joined to main (uid -> split/round/gold):
  u1 [e,e]      dev/R1  gold e  -> class e: unanimous, k2, majority e == gold -> MATCH
  u2 [e,e]      dev/R1  gold n  -> class n: unanimous, k2, majority e != gold -> DIFFER
  u3 [c,n,c]    test/R2 gold c  -> class c: not unanimous, k3, majority c == gold -> MATCH
  u4 [e,n,c]    test/R3 gold e  -> class e: not unanimous, k3, 1-1-1 -> NO_MAJORITY
  u7 [n,n]      train/R1 gold n -> class n: unanimous, k2, majority n == gold -> MATCH (train)
  u6 [e,e]      (no main example)              -> ORPHAN

u5 train/R1/n has no verifier line (not counted).

Per class over ALL joined (u1,u2,u3,u4,u7):
  e: n=2 unanimous=1 match=1 differ=0 no_majority=1 k2=1 k3=1 k_other=0 k2_split=0
  n: n=2 unanimous=2 match=1 differ=1 no_majority=0 k2=2 k3=0 k_other=0 k2_split=0
  c: n=1 unanimous=0 match=1 differ=0 no_majority=0 k2=0 k3=1 k_other=0 k2_split=0
Dev/test subset (u1,u2,u3,u4):
  e: n=2 unanimous=1 match=1 differ=0 no_majority=1
  n: n=1 unanimous=1 match=0 differ=1 no_majority=0
  c: n=1 unanimous=0 match=1 differ=0 no_majority=0
Train subset (u7):
  e: all 0 ; n: n=1 unanimous=1 match=1 differ=0 no_majority=0 ; c: all 0
Totals: n_verifier_lines=6 n_joined=5 n_orphan=1 n_train=1 n_devtest=4 n_gold_unexpected=0
"""


def _main(uid, split, rnd, gold):
    return {"uid": uid, "label": gold, "premise": "a premise", "hypothesis": "a hypothesis",
            "_split": split, "_round": rnd}


# raw verifier records, in the released {"uid", "verifier labels"} shape
FIXTURE_VERIFIER_RAW = [
    {"uid": "u1", "verifier labels": ["e", "e"]},
    {"uid": "u2", "verifier labels": ["e", "e"]},
    {"uid": "u3", "verifier labels": ["c", "n", "c"]},
    {"uid": "u4", "verifier labels": ["e", "n", "c"]},
    {"uid": "u7", "verifier labels": ["n", "n"]},
    {"uid": "u6", "verifier labels": ["e", "e"]},
]

# raw main records carrying their split/round via the _split/_round helper keys
FIXTURE_MAIN_RAW = [
    _main("u1", "dev", "R1", "e"),
    _main("u2", "dev", "R1", "n"),
    _main("u3", "test", "R2", "c"),
    _main("u4", "test", "R3", "e"),
    _main("u7", "train", "R1", "n"),
    _main("u5", "train", "R1", "n"),
]


def build_gold_index(main_raw):
    """Build the uid -> {split, round, gold} index the census joins against (fixture + real share this)."""
    idx = {}
    for obj in main_raw:
        idx[obj["uid"]] = {"split": obj["_split"], "round": obj["_round"], "gold": obj.get("label")}
    return idx


TARGET = {
    "n_verifier_lines": 6, "n_joined": 5, "n_orphan": 1, "n_train": 1, "n_devtest": 4,
    "n_gold_unexpected": 0,
    # all joined, per class
    "e_n": 2, "e_unanimous": 1, "e_match": 1, "e_differ": 0, "e_no_majority": 1,
    "e_k2": 1, "e_k3": 1, "e_k_other": 0, "e_k2_split": 0,
    "n_n": 2, "n_unanimous": 2, "n_match": 1, "n_differ": 1, "n_no_majority": 0,
    "n_k2": 2, "n_k3": 0, "n_k_other": 0, "n_k2_split": 0,
    "c_n": 1, "c_unanimous": 0, "c_match": 1, "c_differ": 0, "c_no_majority": 0,
    "c_k2": 0, "c_k3": 1, "c_k_other": 0, "c_k2_split": 0,
    # dev/test subset
    "dt_e_n": 2, "dt_e_unanimous": 1, "dt_e_match": 1, "dt_e_differ": 0, "dt_e_no_majority": 1,
    "dt_n_n": 1, "dt_n_unanimous": 1, "dt_n_match": 0, "dt_n_differ": 1, "dt_n_no_majority": 0,
    "dt_c_n": 1, "dt_c_unanimous": 0, "dt_c_match": 1, "dt_c_differ": 0, "dt_c_no_majority": 0,
    # train subset
    "tr_e_n": 0, "tr_e_unanimous": 0, "tr_e_match": 0, "tr_e_differ": 0, "tr_e_no_majority": 0,
    "tr_n_n": 1, "tr_n_unanimous": 1, "tr_n_match": 1, "tr_n_differ": 0, "tr_n_no_majority": 0,
    "tr_c_n": 0, "tr_c_unanimous": 0, "tr_c_match": 0, "tr_c_differ": 0, "tr_c_no_majority": 0,
}

# Minimum per-class unanimous-rate spread we pre-register as "meaningfully class-dependent" (P3).
MIN_UNANIMOUS_SPREAD = 0.05
# Minimum per-class match rate we pre-register (P1): ANLI's gold survives verification in every class.
MIN_MATCH_RATE = 0.95

ROUNDS = ("R1", "R2", "R3")
SPLITS = ("train", "dev", "test")
