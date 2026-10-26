"""Hand-traced fixture for the ANLI per-genre verifier-agreement census.

Seven synthetic verifier lines and six synthetic main examples, worked out by hand into a TARGET so the
join + per-genre tally logic is checked against a known answer before it touches the real ANLI files.
The fixture deliberately exercises: two genres (wiki, news) plus one genre-absent line; k=2 and k=3
verifier lines; strict majorities that match gold, and ties with no majority; lines spread across R1/R2/R3
so the R3-only breakdown differs from the pooled one; and one orphan verifier line with no main example.

Main examples (uid, round, split, gold, genre):
  m1 R3/train gold e genre "wiki"  -> verifier [e,e]     maj e==gold GOLD_MAJORITY; gold_votes 2/2
  m2 R3/dev   gold c genre "wiki"  -> verifier [c,e,c]   maj c==gold GOLD_MAJORITY; gold_votes 2/3
  m3 R3/test  gold n genre "news"  -> verifier [n,c]     tie -> NO_MAJORITY;         gold_votes 1/2
  m4 R1/train gold e genre "wiki"  -> verifier [e,e,e]   maj e==gold GOLD_MAJORITY; gold_votes 3/3   (R1)
  m5 R3/dev   gold c genre ""      -> verifier [c,c]     genre ABSENT (counted in totals only)
  m6 R2/train gold n genre "wiki"  -> verifier [n,e]     tie -> NO_MAJORITY;         gold_votes 1/2   (R2)
  (x9 verifier line has no main example -> ORPHAN)

Pooled wiki gets m1,m2,m4,m6; R3-only wiki gets m1,m2. news is R3-only (m3). m5 is genre-absent.

Apache-2.0.
"""

LETTERS = ("e", "n", "c")
ROUNDS = ("R1", "R2", "R3")
SPLITS = ("train", "dev", "test")

FIXTURE_VERIFIER_RAW = [
    {"uid": "m1", "verifier labels": ["e", "e"]},
    {"uid": "m2", "verifier labels": ["c", "e", "c"]},
    {"uid": "m3", "verifier labels": ["n", "c"]},
    {"uid": "m4", "verifier labels": ["e", "e", "e"]},
    {"uid": "m5", "verifier labels": ["c", "c"]},
    {"uid": "m6", "verifier labels": ["n", "e"]},
    {"uid": "x9", "verifier labels": ["e"]},
]


def _main(uid, rnd, split, gold, genre):
    return {"uid": uid, "label": gold, "premise": "a premise", "hypothesis": "a hypothesis",
            "_round": rnd, "_split": split, "genre": genre}


FIXTURE_MAIN_RAW = [
    _main("m1", "R3", "train", "e", "wiki"),
    _main("m2", "R3", "dev", "c", "wiki"),
    _main("m3", "R3", "test", "n", "news"),
    _main("m4", "R1", "train", "e", "wiki"),
    _main("m5", "R3", "dev", "c", ""),
    _main("m6", "R2", "train", "n", "wiki"),
]


def build_gold_index(main_raw):
    """Build the uid -> {round, split, gold, genre} index the census joins against (fixture + real share)."""
    idx = {}
    for obj in main_raw:
        idx[obj["uid"]] = {"round": obj["_round"], "split": obj["_split"],
                           "gold": obj.get("label"), "genre": obj.get("genre")}
    return idx


# Hand-traced TARGET. Totals, then the pooled-genre and R3-only-genre tallies (only genres that occur).
TARGET_TOTALS = {
    "n_verifier_lines": 7, "n_joined": 6, "n_orphan": 1, "n_gold_unexpected": 0, "n_genre_absent": 1,
    "all_lines_match": 4, "all_lines_differ": 0, "all_lines_no_majority": 2,
}

_GENRE_FIELDS = ("n", "gold_majority", "no_majority", "majority_differs", "gold_votes", "total_votes")

# Pooled per-genre (wiki = m1,m2,m4,m6 ; news = m3).
_BY_GENRE = {
    "news": {"n": 1, "gold_majority": 0, "no_majority": 1, "majority_differs": 0,
             "gold_votes": 1, "total_votes": 2},
    "wiki": {"n": 4, "gold_majority": 3, "no_majority": 1, "majority_differs": 0,
             "gold_votes": 8, "total_votes": 10},
}

# R3-only per-genre (wiki = m1,m2 ; news = m3).
_BY_GENRE_R3 = {
    "news": {"n": 1, "gold_majority": 0, "no_majority": 1, "majority_differs": 0,
             "gold_votes": 1, "total_votes": 2},
    "wiki": {"n": 2, "gold_majority": 2, "no_majority": 0, "majority_differs": 0,
             "gold_votes": 4, "total_votes": 5},
}


def build_target_flat():
    out = dict(TARGET_TOTALS)
    for g in sorted(_BY_GENRE):
        for f in _GENRE_FIELDS:
            out["genre_%s_%s" % (g, f)] = _BY_GENRE[g][f]
    for g in sorted(_BY_GENRE_R3):
        for f in _GENRE_FIELDS:
            out["genre_r3_%s_%s" % (g, f)] = _BY_GENRE_R3[g][f]
    return out


TARGET = build_target_flat()

# Pre-registered thresholds / expectations (evaluated on the REAL data, not the fixture).
# P1 (structural, finding either way): in EVERY genre the writer's gold equals the strict verifier
# majority on more than this share -- the gold derivation is robust to text domain, no genre is an outlier.
MIN_GOLD_MAJORITY_RATE = 0.99
# P2 (directional, finding either way): WITHIN R3 (adversary round held fixed), the gold-support rate
# (fraction of individual verifier votes equalling gold) varies across genres by more than this spread --
# i.e. text domain predicts how decisively verifiers back the adversarial gold even at a single round.
MIN_R3_SUPPORT_SPREAD = 0.03
# Only genres with at least this many R3 verified examples enter the P2 spread (guards tiny cells).
MIN_GENRE_N = 200
# P3 (cross-check, reproduces audits 39/48): all joined lines with gold == strict majority, and the join size.
EXPECTED_ALL_LINES_MATCH = 29765
EXPECTED_N_JOINED = 29803
