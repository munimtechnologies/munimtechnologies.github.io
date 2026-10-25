"""Hand-traced fixture for the ANLI per-(round, class) verifier-agreement census.

Six synthetic verifier lines and six synthetic main examples, worked out by hand into a per-(round, class)
TARGET, so the join + round x class counting logic is checked against a known answer before it touches the
real ANLI files. The fixture reuses audit 45's six records (so the two audits' counting stays comparable)
and distributes them across rounds R1/R2/R3 to exercise the round dimension.

Verifier lines (uid -> labels) joined to main (uid -> split/round/gold):
  u1 [e,e]      dev/R1   gold e  -> (R1, e): unanimous pair, k2, majority e == gold -> MATCH
  u2 [e,e]      dev/R1   gold n  -> (R1, n): unanimous pair, k2, majority e != gold -> DIFFER
  u3 [c,n,c]    test/R2  gold c  -> (R2, c): not unanimous, k3, majority c == gold -> MATCH
  u4 [e,n,c]    test/R3  gold e  -> (R3, e): not unanimous, k3, 1-1-1 -> NO_MAJORITY
  u7 [n,n]      train/R1 gold n  -> (R1, n): unanimous pair, k2, majority n == gold -> MATCH (train)
  u6 [e,e]      (no main example)               -> ORPHAN

u5 train/R1/n has no verifier line (not counted).

Non-zero per-(round, class) cells (every unlisted cell is all zeros):
  (R1, e): n=1 unanimous=1 match=1 differ=0 no_majority=0 k2=1 k3=0 k_other=0 k2_split=0
  (R1, n): n=2 unanimous=2 match=1 differ=1 no_majority=0 k2=2 k3=0 k_other=0 k2_split=0  (u2 + u7)
  (R2, c): n=1 unanimous=0 match=1 differ=0 no_majority=0 k2=0 k3=1 k_other=0 k2_split=0
  (R3, e): n=1 unanimous=0 match=0 differ=0 no_majority=1 k2=0 k3=1 k_other=0 k2_split=0
Totals: n_verifier_lines=6 n_joined=5 n_orphan=1 n_train=1 n_devtest=4 n_gold_unexpected=0
"""

LETTERS = ("e", "n", "c")
ROUNDS = ("R1", "R2", "R3")
SPLITS = ("train", "dev", "test")
_CLASS_FIELDS = ("n", "unanimous", "match", "differ", "no_majority", "k2", "k3", "k_other", "k2_split")


def _main(uid, split, rnd, gold):
    return {"uid": uid, "label": gold, "premise": "a premise", "hypothesis": "a hypothesis",
            "_split": split, "_round": rnd}


FIXTURE_VERIFIER_RAW = [
    {"uid": "u1", "verifier labels": ["e", "e"]},
    {"uid": "u2", "verifier labels": ["e", "e"]},
    {"uid": "u3", "verifier labels": ["c", "n", "c"]},
    {"uid": "u4", "verifier labels": ["e", "n", "c"]},
    {"uid": "u7", "verifier labels": ["n", "n"]},
    {"uid": "u6", "verifier labels": ["e", "e"]},
]

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


TARGET_TOTALS = {
    "n_verifier_lines": 6, "n_joined": 5, "n_orphan": 1, "n_train": 1, "n_devtest": 4,
    "n_gold_unexpected": 0,
}

# Hand-traced non-zero (round, class) cells; all unlisted cells are zero.
_TARGET_NONZERO = {
    ("R1", "e"): {"n": 1, "unanimous": 1, "match": 1, "differ": 0, "no_majority": 0,
                  "k2": 1, "k3": 0, "k_other": 0, "k2_split": 0},
    ("R1", "n"): {"n": 2, "unanimous": 2, "match": 1, "differ": 1, "no_majority": 0,
                  "k2": 2, "k3": 0, "k_other": 0, "k2_split": 0},
    ("R2", "c"): {"n": 1, "unanimous": 0, "match": 1, "differ": 0, "no_majority": 0,
                  "k2": 0, "k3": 1, "k_other": 0, "k2_split": 0},
    ("R3", "e"): {"n": 1, "unanimous": 0, "match": 0, "differ": 0, "no_majority": 1,
                  "k2": 0, "k3": 1, "k_other": 0, "k2_split": 0},
}


def build_target_flat():
    """Full flat TARGET (round x class x field + totals) built from the hand-traced non-zero cells."""
    out = dict(TARGET_TOTALS)
    for r in ROUNDS:
        for g in LETTERS:
            cell = _TARGET_NONZERO.get((r, g), {f: 0 for f in _CLASS_FIELDS})
            for f in _CLASS_FIELDS:
                out["%s_%s_%s" % (r, g, f)] = cell[f]
    return out


TARGET = build_target_flat()

# Pre-registered thresholds.
MIN_MATCH_RATE = 0.95  # P1: writer gold == strict verifier majority on >95% of each round's examples.
