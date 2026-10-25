"""Hand-traced fixture for the ANLI per-(gold class, model_label) verifier-agreement census.

Eight synthetic verifier lines and seven synthetic main examples, worked out by hand into a
per-(gold, model_label) TARGET, so the join + cross-tabulation logic is checked against a known answer
before it touches the real ANLI files. The fixture deliberately includes: a row the model got right
(model_label == gold, u6), a row whose model_label is missing (u7 -> bucket "x"), an orphan verifier
line (u8), and a gold-vs-verifier DIFFER (u5), so every totals counter and the "x" bucket are exercised.

Verifier lines (uid -> labels) joined to main (uid -> split/gold/model_label):
  u1 [e,e]    dev/gold e/model c   -> (e, c): unanimous pair, k2, maj e == gold -> MATCH;  fooled (c!=e)
  u2 [e,n,e]  dev/gold e/model n   -> (e, n): not unanimous, k3, maj e == gold -> MATCH;   fooled (n!=e)
  u3 [n,n]    test/gold n/model e  -> (n, e): unanimous pair, k2, maj n == gold -> MATCH;  fooled (e!=n)
  u4 [c,e,c]  test/gold c/model e  -> (c, e): not unanimous, k3, maj c == gold -> MATCH;   fooled (e!=c)
  u5 [c,c]    train/gold e/model c -> (e, c): unanimous pair, k2, maj c != gold -> DIFFER; fooled (c!=e)
  u6 [n,n]    train/gold n/model n -> (n, n): unanimous pair, k2, maj n == gold -> MATCH;  AGREED (n==n)
  u7 [c,c]    train/gold c/model - -> (c, x): unanimous pair, k2, maj c == gold -> MATCH;  model_label MISSING
  u8 [e,e]    (no main example)                                                           -> ORPHAN

Non-zero per-(gold, model_label) cells (every unlisted cell is all zeros):
  (e, c): n=2 unanimous=2 match=1 differ=1 no_majority=0 k2=2 k3=0 k_other=0 k2_split=0   (u1 + u5)
  (e, n): n=1 unanimous=0 match=1 differ=0 no_majority=0 k2=0 k3=1 k_other=0 k2_split=0   (u2)
  (n, e): n=1 unanimous=1 match=1 differ=0 no_majority=0 k2=1 k3=0 k_other=0 k2_split=0   (u3)
  (n, n): n=1 unanimous=1 match=1 differ=0 no_majority=0 k2=1 k3=0 k_other=0 k2_split=0   (u6)
  (c, e): n=1 unanimous=0 match=1 differ=0 no_majority=0 k2=0 k3=1 k_other=0 k2_split=0   (u4)
  (c, x): n=1 unanimous=1 match=1 differ=0 no_majority=0 k2=1 k3=0 k_other=0 k2_split=0   (u7)
Totals: n_verifier_lines=8 n_joined=7 n_orphan=1 n_gold_unexpected=0
        n_model_label_recognised=6 n_model_label_missing=1 n_model_fooled=5 n_model_agreed=1
"""

LETTERS = ("e", "n", "c")
MLABELS = ("e", "n", "c", "x")
SPLITS = ("train", "dev", "test")
_CLASS_FIELDS = ("n", "unanimous", "match", "differ", "no_majority", "k2", "k3", "k_other", "k2_split")


def _main(uid, split, gold, model_label):
    rec = {"uid": uid, "label": gold, "premise": "a premise", "hypothesis": "a hypothesis",
           "_split": split}
    if model_label is not None:
        rec["model_label"] = model_label
    return rec


FIXTURE_VERIFIER_RAW = [
    {"uid": "u1", "verifier labels": ["e", "e"]},
    {"uid": "u2", "verifier labels": ["e", "n", "e"]},
    {"uid": "u3", "verifier labels": ["n", "n"]},
    {"uid": "u4", "verifier labels": ["c", "e", "c"]},
    {"uid": "u5", "verifier labels": ["c", "c"]},
    {"uid": "u6", "verifier labels": ["n", "n"]},
    {"uid": "u7", "verifier labels": ["c", "c"]},
    {"uid": "u8", "verifier labels": ["e", "e"]},
]

FIXTURE_MAIN_RAW = [
    _main("u1", "dev", "e", "c"),
    _main("u2", "dev", "e", "n"),
    _main("u3", "test", "n", "e"),
    _main("u4", "test", "c", "e"),
    _main("u5", "train", "e", "c"),
    _main("u6", "train", "n", "n"),
    _main("u7", "train", "c", None),
]


def build_gold_index(main_raw):
    """Build the uid -> {split, gold, model_label} index the census joins against (fixture + real share)."""
    idx = {}
    for obj in main_raw:
        idx[obj["uid"]] = {"split": obj["_split"], "gold": obj.get("label"),
                           "model_label": obj.get("model_label")}
    return idx


TARGET_TOTALS = {
    "n_verifier_lines": 8, "n_joined": 7, "n_orphan": 1, "n_gold_unexpected": 0,
    "n_model_label_recognised": 6, "n_model_label_missing": 1, "n_model_fooled": 5, "n_model_agreed": 1,
}

# Hand-traced non-zero (gold, model_label) cells; all unlisted cells are zero.
_TARGET_NONZERO = {
    ("e", "c"): {"n": 2, "unanimous": 2, "match": 1, "differ": 1, "no_majority": 0,
                 "k2": 2, "k3": 0, "k_other": 0, "k2_split": 0},
    ("e", "n"): {"n": 1, "unanimous": 0, "match": 1, "differ": 0, "no_majority": 0,
                 "k2": 0, "k3": 1, "k_other": 0, "k2_split": 0},
    ("n", "e"): {"n": 1, "unanimous": 1, "match": 1, "differ": 0, "no_majority": 0,
                 "k2": 1, "k3": 0, "k_other": 0, "k2_split": 0},
    ("n", "n"): {"n": 1, "unanimous": 1, "match": 1, "differ": 0, "no_majority": 0,
                 "k2": 1, "k3": 0, "k_other": 0, "k2_split": 0},
    ("c", "e"): {"n": 1, "unanimous": 0, "match": 1, "differ": 0, "no_majority": 0,
                 "k2": 0, "k3": 1, "k_other": 0, "k2_split": 0},
    ("c", "x"): {"n": 1, "unanimous": 1, "match": 1, "differ": 0, "no_majority": 0,
                 "k2": 1, "k3": 0, "k_other": 0, "k2_split": 0},
}


def build_target_flat():
    """Full flat TARGET (gold x mlabel x field + totals) built from the hand-traced non-zero cells."""
    out = dict(TARGET_TOTALS)
    for g in LETTERS:
        for m in MLABELS:
            cell = _TARGET_NONZERO.get((g, m), {f: 0 for f in _CLASS_FIELDS})
            for f in _CLASS_FIELDS:
                out["%s_%s_%s" % (g, m, f)] = cell[f]
    return out


TARGET = build_target_flat()

# Pre-registered thresholds.
MIN_FOOLED_RATE = 0.95  # P1: among rows with a recognised model_label, model_label != gold on >95%.
MIN_SPREAD = 0.03       # P2: in >=1 gold class, verifier unanimous rate spans >0.03 across model_label buckets.
MIN_MATCH_RATE = 0.95   # P3: gold == strict verifier majority on >95% in every cell with n >= MIN_CELL_N.
MIN_CELL_N = 100        # P3 only tested on cells with at least this many examples.
