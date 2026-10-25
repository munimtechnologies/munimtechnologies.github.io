"""Hand-traced fixture for the ANLI verifier-tiebreak census.

Eight synthetic verifier lines and seven synthetic main examples, worked out by hand into a TARGET for
the totals plus the overall / per-class / per-round tiebreak tallies, so the join + tiebreak logic is
checked against a known answer before it touches the real ANLI files. The fixture deliberately includes:
a clean tiebreak the third verifier resolves TO the gold (u1), a tiebreak resolved to the OTHER first
label so the majority differs from gold (u2), a three-distinct-label line with no majority (u3), a line
whose gold is in NEITHER of the first two verifiers (u4), a k=3 line whose first two verifiers in fact
AGREE -- a protocol anomaly (u5), two k=2 lines (u6 agree, u7 split) and an orphan verifier line (u8).

Verifier lines (uid -> labels) joined to main (uid -> round/split/gold):
  u1 [e,n,e]  R1/dev  gold e -> k3: first two differ (e,n); l3=e; maj e == gold MATCH; tiebreak -> GOLD
  u2 [n,c,n]  R2/dev  gold c -> k3: first two differ (n,c); l3=n; maj n != gold DIFFER; tiebreak -> OTHER
  u3 [e,n,c]  R3/test gold e -> k3: first two differ (e,n); l3=c; NO MAJORITY; tiebreak -> THIRD
  u4 [n,c,n]  R3/train gold e -> k3: first two differ (n,c); l3=n; maj n != gold DIFFER; gold NOT in first two
  u5 [c,c,n]  R1/train gold c -> k3: first two AGREE (c,c) [anomaly]; l3=n; maj c == gold MATCH; not a tiebreak
  u6 [e,e]    R2/train gold e -> k2: maj e == gold (all-lines MATCH)
  u7 [n,c]    R1/dev  gold n -> k2: split, no majority (all-lines NO_MAJORITY)
  u8 [e,e]    (no main example)                                                                 -> ORPHAN

Apache-2.0.
"""

LETTERS = ("e", "n", "c")
ROUNDS = ("R1", "R2", "R3")
SPLITS = ("train", "dev", "test")

FIXTURE_VERIFIER_RAW = [
    {"uid": "u1", "verifier labels": ["e", "n", "e"]},
    {"uid": "u2", "verifier labels": ["n", "c", "n"]},
    {"uid": "u3", "verifier labels": ["e", "n", "c"]},
    {"uid": "u4", "verifier labels": ["n", "c", "n"]},
    {"uid": "u5", "verifier labels": ["c", "c", "n"]},
    {"uid": "u6", "verifier labels": ["e", "e"]},
    {"uid": "u7", "verifier labels": ["n", "c"]},
    {"uid": "u8", "verifier labels": ["e", "e"]},
]


def _main(uid, rnd, split, gold):
    return {"uid": uid, "label": gold, "premise": "a premise", "hypothesis": "a hypothesis",
            "_round": rnd, "_split": split}


FIXTURE_MAIN_RAW = [
    _main("u1", "R1", "dev", "e"),
    _main("u2", "R2", "dev", "c"),
    _main("u3", "R3", "test", "e"),
    _main("u4", "R3", "train", "e"),
    _main("u5", "R1", "train", "c"),
    _main("u6", "R2", "train", "e"),
    _main("u7", "R1", "dev", "n"),
]


def build_gold_index(main_raw):
    """Build the uid -> {round, split, gold} index the census joins against (fixture + real share this)."""
    idx = {}
    for obj in main_raw:
        idx[obj["uid"]] = {"round": obj["_round"], "split": obj["_split"], "gold": obj.get("label")}
    return idx


# Hand-traced TARGET. Totals first, then the overall / per-class / per-round tiebreak tallies (only the
# non-zero cells are spelled out here; build_target_flat() zero-fills the rest).
TARGET_TOTALS = {
    "n_verifier_lines": 8, "n_joined": 7, "n_orphan": 1, "n_gold_unexpected": 0,
    "k2": 2, "k3": 5, "k_other": 0,
    "all_lines_match": 3, "all_lines_differ": 2, "all_lines_no_majority": 2,
}

_TB_FIELDS = ("n", "firsttwo_differ", "firsttwo_agree", "majority_formed", "no_majority",
              "match", "differ", "gold_in_firsttwo", "gold_not_in_firsttwo",
              "n_tiebreak", "tiebreak_gold", "tiebreak_other", "tiebreak_third")

_OVERALL = {"n": 5, "firsttwo_differ": 4, "firsttwo_agree": 1, "majority_formed": 4, "no_majority": 1,
            "match": 2, "differ": 2, "gold_in_firsttwo": 4, "gold_not_in_firsttwo": 1,
            "n_tiebreak": 3, "tiebreak_gold": 1, "tiebreak_other": 1, "tiebreak_third": 1}

_BY_CLASS = {
    "e": {"n": 3, "firsttwo_differ": 3, "firsttwo_agree": 0, "majority_formed": 2, "no_majority": 1,
          "match": 1, "differ": 1, "gold_in_firsttwo": 2, "gold_not_in_firsttwo": 1,
          "n_tiebreak": 2, "tiebreak_gold": 1, "tiebreak_other": 0, "tiebreak_third": 1},
    "n": {f: 0 for f in _TB_FIELDS},
    "c": {"n": 2, "firsttwo_differ": 1, "firsttwo_agree": 1, "majority_formed": 2, "no_majority": 0,
          "match": 1, "differ": 1, "gold_in_firsttwo": 2, "gold_not_in_firsttwo": 0,
          "n_tiebreak": 1, "tiebreak_gold": 0, "tiebreak_other": 1, "tiebreak_third": 0},
}

_BY_ROUND = {
    "R1": {"n": 2, "firsttwo_differ": 1, "firsttwo_agree": 1, "majority_formed": 2, "no_majority": 0,
           "match": 2, "differ": 0, "gold_in_firsttwo": 2, "gold_not_in_firsttwo": 0,
           "n_tiebreak": 1, "tiebreak_gold": 1, "tiebreak_other": 0, "tiebreak_third": 0},
    "R2": {"n": 1, "firsttwo_differ": 1, "firsttwo_agree": 0, "majority_formed": 1, "no_majority": 0,
           "match": 0, "differ": 1, "gold_in_firsttwo": 1, "gold_not_in_firsttwo": 0,
           "n_tiebreak": 1, "tiebreak_gold": 0, "tiebreak_other": 1, "tiebreak_third": 0},
    "R3": {"n": 2, "firsttwo_differ": 2, "firsttwo_agree": 0, "majority_formed": 1, "no_majority": 1,
           "match": 0, "differ": 1, "gold_in_firsttwo": 1, "gold_not_in_firsttwo": 1,
           "n_tiebreak": 1, "tiebreak_gold": 0, "tiebreak_other": 0, "tiebreak_third": 1},
}


def build_target_flat():
    out = dict(TARGET_TOTALS)
    for f in _TB_FIELDS:
        out["overall_%s" % f] = _OVERALL[f]
    for g in LETTERS:
        for f in _TB_FIELDS:
            out["class_%s_%s" % (g, f)] = _BY_CLASS[g][f]
    for r in ROUNDS:
        for f in _TB_FIELDS:
            out["round_%s_%s" % (r, f)] = _BY_ROUND[r][f]
    return out


TARGET = build_target_flat()

# Pre-registered thresholds (evaluated on the REAL data, not the fixture).
MIN_FIRSTTWO_DIFFER_RATE = 0.99  # P1: among k=3 lines the first two verifiers differ on >99% (protocol).
MIN_TIEBREAK_GOLD_RATE = 0.50    # P2: among genuine tiebreaks the third verifier sides with gold on >50%.
MIN_ALL_LINES_MATCH_RATE = 0.99  # P3 (cross-check audit 39): gold == strict majority on >99% of all lines.
