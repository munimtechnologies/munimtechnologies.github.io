"""Hand-traced fixture for the ANLI verifier-majority / gold-derivation census.

Five synthetic verifier lines and five synthetic main examples, worked out by hand into TARGET, so the
join + counting logic is checked against a known answer before it touches the real ANLI files. The
fixture exercises every path: a match, a unanimous-verifier-but-differs-from-gold case, a 2-1 majority
match, a no-majority (1-1-1) case, and an orphan verifier uid. The real-data predictions bet on the
structural facts (verification is dev/test only; every verifier line has 2 or 3 labels) and on the
family-contrast direction (ANLI gold differs from the verifier majority on a nonzero number of rows).

Verifier lines (uid -> labels):
  u1 [e,e]      joins dev/R1, gold e  -> unanimous; majority e == gold -> MATCH
  u2 [e,e]      joins dev/R1, gold n  -> unanimous; majority e != gold -> DIFFERS (unanimous-differs)
  u3 [c,n,c]    joins test/R2, gold c -> not unanimous; majority c == gold -> MATCH
  u4 [e,n,c]    joins test/R3, gold e -> 1-1-1, no majority -> NO_MAJORITY
  u6 [e,e]      no main example       -> ORPHAN

Main examples (uid -> split/round/gold): u1 dev/R1/e, u2 dev/R1/n, u3 test/R2/c, u4 test/R3/e,
u5 train/R1/n (has no verifier line).

n_verifier_lines=5 ; n_joined=4 ; n_orphan=1 ; n_join_train=0 ; n_join_dev=2 ; n_join_test=2
n_gold_matches_majority = u1,u3 = 2 ; n_gold_differs_from_majority = u2 = 1 ; n_no_majority = u4 = 1
n_gold_unexpected = 0 ; n_unanimous = u1,u2 = 2 ; n_unanimous_differs_from_gold = u2 = 1
n_k2 = u1,u2,u6 = 3 ; n_k3 = u3,u4 = 2 ; n_k_other = 0
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
    {"uid": "u6", "verifier labels": ["e", "e"]},
]

# raw main records carrying their split/round via the _split/_round helper keys
FIXTURE_MAIN_RAW = [
    _main("u1", "dev", "R1", "e"),
    _main("u2", "dev", "R1", "n"),
    _main("u3", "test", "R2", "c"),
    _main("u4", "test", "R3", "e"),
    _main("u5", "train", "R1", "n"),
]


def build_gold_index(main_raw):
    """Build the uid -> {split, round, gold} index the census joins against (fixture + real share this)."""
    idx = {}
    for obj in main_raw:
        idx[obj["uid"]] = {"split": obj["_split"], "round": obj["_round"], "gold": obj.get("label")}
    return idx


TARGET = {
    "n_verifier_lines": 5,
    "n_joined": 4,
    "n_orphan": 1,
    "n_join_train": 0,
    "n_join_dev": 2,
    "n_join_test": 2,
    "n_gold_matches_majority": 2,
    "n_gold_differs_from_majority": 1,
    "n_no_majority": 1,
    "n_gold_unexpected": 0,
    "n_unanimous": 2,
    "n_unanimous_differs_from_gold": 1,
    "n_k2": 3,
    "n_k3": 2,
    "n_k_other": 0,
}

ROUNDS = ("R1", "R2", "R3")
SPLITS = ("train", "dev", "test")
