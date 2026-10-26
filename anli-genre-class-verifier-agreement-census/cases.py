"""Hand-traced fixture for the ANLI per-(genre, class) verifier-agreement census (within R3).

Nine synthetic verifier lines and eight synthetic main examples, worked out by hand into a TARGET so the
join + per-(genre,class) R3 tally logic is checked against a known answer before it touches the real ANLI
files. The fixture deliberately exercises: two genres (wiki, news) x three classes (e, n, c) all within
R3; one R1 line (excluded from the cells but counted in all-lines totals and n_not_r3); one genre-absent
R3 line (counted in totals and n_genre_absent); k=2 and k=3 verifier lines; unanimous and non-unanimous
lines; a strict majority that matches gold and a tie with no majority; and one orphan verifier line.

Main examples (uid, round, split, gold, genre) -> verifier labels:
  w_e  R3 train wiki e -> [e,e]      maj e==gold; unanimous; gold_votes 2/2
  w_n  R3 dev   wiki n -> [n,c]      tie NO_MAJORITY; not unanimous; gold_votes 1/2
  w_c  R3 test  wiki c -> [c,c,c]    maj c==gold; unanimous; gold_votes 3/3
  n_e  R3 train news e -> [e,e,e]    maj e==gold; unanimous; gold_votes 3/3
  n_n  R3 dev   news n -> [n,n]      maj n==gold; unanimous; gold_votes 2/2
  n_c  R3 test  news c -> [c,e,c]    maj c==gold; not unanimous; gold_votes 2/3
  r1x  R1 train wiki e -> [e,e]      NOT R3 -> excluded from cells (all-lines match, n_not_r3)
  abs  R3 dev   ""   c -> [c,c]      genre ABSENT -> excluded from cells (all-lines match, n_genre_absent)
  (x9 verifier line has no main example -> ORPHAN)

Apache-2.0.
"""

LETTERS = ("e", "n", "c")
ROUNDS = ("R1", "R2", "R3")
SPLITS = ("train", "dev", "test")

FIXTURE_VERIFIER_RAW = [
    {"uid": "w_e", "verifier labels": ["e", "e"]},
    {"uid": "w_n", "verifier labels": ["n", "c"]},
    {"uid": "w_c", "verifier labels": ["c", "c", "c"]},
    {"uid": "n_e", "verifier labels": ["e", "e", "e"]},
    {"uid": "n_n", "verifier labels": ["n", "n"]},
    {"uid": "n_c", "verifier labels": ["c", "e", "c"]},
    {"uid": "r1x", "verifier labels": ["e", "e"]},
    {"uid": "abs", "verifier labels": ["c", "c"]},
    {"uid": "x9", "verifier labels": ["e"]},
]


def _main(uid, rnd, split, gold, genre):
    return {"uid": uid, "label": gold, "premise": "a premise", "hypothesis": "a hypothesis",
            "_round": rnd, "_split": split, "genre": genre}


FIXTURE_MAIN_RAW = [
    _main("w_e", "R3", "train", "e", "wiki"),
    _main("w_n", "R3", "dev", "n", "wiki"),
    _main("w_c", "R3", "test", "c", "wiki"),
    _main("n_e", "R3", "train", "e", "news"),
    _main("n_n", "R3", "dev", "n", "news"),
    _main("n_c", "R3", "test", "c", "news"),
    _main("r1x", "R1", "train", "e", "wiki"),
    _main("abs", "R3", "dev", "c", ""),
]


def build_gold_index(main_raw):
    """Build the uid -> {round, split, gold, genre} index the census joins against (fixture + real share)."""
    idx = {}
    for obj in main_raw:
        idx[obj["uid"]] = {"round": obj["_round"], "split": obj["_split"],
                           "gold": obj.get("label"), "genre": obj.get("genre")}
    return idx


# Hand-traced TARGET. Totals, then the per-(genre,class) R3 cells (sorted key order).
TARGET_TOTALS = {
    "n_verifier_lines": 9, "n_joined": 8, "n_orphan": 1, "n_gold_unexpected": 0, "n_genre_absent": 1,
    "n_not_r3": 1, "all_lines_match": 7, "all_lines_differ": 0, "all_lines_no_majority": 1,
}

_CELL_FIELDS = ("n", "gold_majority", "no_majority", "gold_votes", "total_votes", "unanimous")

# Per-(genre,class) R3 cells. Keys "<genre>|<class>".
_BY_CELL = {
    "news|c": {"n": 1, "gold_majority": 1, "no_majority": 0, "gold_votes": 2, "total_votes": 3, "unanimous": 0},
    "news|e": {"n": 1, "gold_majority": 1, "no_majority": 0, "gold_votes": 3, "total_votes": 3, "unanimous": 1},
    "news|n": {"n": 1, "gold_majority": 1, "no_majority": 0, "gold_votes": 2, "total_votes": 2, "unanimous": 1},
    "wiki|c": {"n": 1, "gold_majority": 1, "no_majority": 0, "gold_votes": 3, "total_votes": 3, "unanimous": 1},
    "wiki|e": {"n": 1, "gold_majority": 1, "no_majority": 0, "gold_votes": 2, "total_votes": 2, "unanimous": 1},
    "wiki|n": {"n": 1, "gold_majority": 0, "no_majority": 1, "gold_votes": 1, "total_votes": 2, "unanimous": 0},
}


def build_target_flat():
    out = dict(TARGET_TOTALS)
    for key in sorted(_BY_CELL):
        g, c = key.split("|")
        for f in _CELL_FIELDS:
            out["gc_%s_%s_%s" % (g, c, f)] = _BY_CELL[key][f]
    return out


TARGET = build_target_flat()

# Pre-registered thresholds / expectations (evaluated on the REAL data, not the fixture).
# P1 (structural, finding either way): in EVERY (genre, class) cell with at least MIN_CELL_N R3 examples the
# writer's gold equals the strict verifier majority on more than this share -- gold derivation robust to
# domain AND class at a fixed round.
MIN_GOLD_MAJORITY_RATE = 0.99
# Only cells with at least this many R3 examples enter P1 and the P2 class ranking (guards tiny cells).
MIN_CELL_N = 100
# P2 (directional, finding either way): WITHIN R3, neutral is the LEAST decisively verified class (lowest
# gold-support rate of {e, n, c}) in at least this many of the six genres (those with all three classes
# present at n >= MIN_CELL_N). Tests whether the "neutral is hardest" class effect is robust across domains
# once the adversary round is held fixed. A failure (class ordering domain-dependent) is itself a finding.
MIN_GENRES_NEUTRAL_LOWEST = 4
# P3 (cross-check, reproduces audits 39/48/49): all joined lines with gold == strict majority, and join size.
EXPECTED_ALL_LINES_MATCH = 29765
EXPECTED_N_JOINED = 29803
