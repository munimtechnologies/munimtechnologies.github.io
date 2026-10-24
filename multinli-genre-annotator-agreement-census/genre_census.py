"""Per-genre annotator-agreement census of MultiNLI's validated development sets.

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

MultiNLI (Williams, Nangia, Bowman, NAACL 2018) assigns each validated development example a gold label
by majority vote over five individual annotator labels (the original writer's label plus four validators);
an example on which fewer than three of the five agreed is released with gold "-" and is customarily
discarded. The paper reports AGGREGATE agreement quality (e.g. 58.2% of pairs unanimous, 88.7% of
individual labels equal to gold), but does not break those numbers down by the ten genres that make up the
matched (fiction, government, slate, telephone, travel) and mismatched (facetoface, letters, nineeleven,
oup, verbatim) development sets.

This audit computes, PER GENRE over the released dev_matched + dev_mismatched files:
  - how many of the five annotators agreed with the released gold (5 unanimous / 4 / 3 / "-" = no majority),
  - the share of examples that are unanimous,
  - the share of individual annotator labels that equal the gold (the paper's "Agrmt." statistic), and
  - a by-construction check that the released gold equals the strict majority of the five labels.

The module operates on already-parsed records, so it is file-free and fully unit-testable. Apache-2.0.
"""

NAMES_3WAY = ("e", "n", "c")

# Per-genre integer tallies the census accumulates.
_GENRE_KEYS = ("n", "valid", "dash", "unanimous", "b5", "b4", "b3", "bother",
               "gold_eq_majority", "label_matches", "labels")


def norm_label(x):
    """Normalise an NLI label to e/n/c; blank / '-' / unrecognised -> None."""
    if x is None:
        return None
    s = str(x).strip().lower()
    if not s:
        return None
    if s[0] in ("e", "n", "c"):
        return s[0]
    return None


def majority_label(labels):
    """Label held by strictly more than half the (normalisable) annotator labels, else None.

    MultiNLI's gold is the majority of five labels; a 2-2-1 or 2-1-1-1 split has no majority ("-").
    Unnormalisable entries still count toward the denominator so a majority must truly exceed half.
    """
    total = len(labels)
    if total == 0:
        return None
    tally = {}
    for a in labels:
        n = norm_label(a)
        if n is not None:
            tally[n] = tally.get(n, 0) + 1
    for name, c in tally.items():
        if c * 2 > total:
            return name
    return None


def agreement_count(annotator_labels, gold):
    """How many annotator labels equal the (normalised) gold; None if gold is not a valid label."""
    g = norm_label(gold)
    if g is None:
        return None
    return sum(1 for a in (annotator_labels or []) if norm_label(a) == g)


def _bucket_of(gold, annotator_labels):
    """Agreement bucket for one example: 'dash' (no gold), '5'/'4'/'3', or 'other' (<3, unexpected)."""
    if norm_label(gold) is None:
        return "dash"
    n_agree = agreement_count(annotator_labels, gold)
    if n_agree == 5:
        return "5"
    if n_agree == 4:
        return "4"
    if n_agree == 3:
        return "3"
    return "other"


def _empty_genre():
    return {k: 0 for k in _GENRE_KEYS}


def census(records):
    """Tally per-genre annotator agreement.

    Each record: ``genre`` (str), ``gold`` (raw gold_label), ``annotator_labels`` (list of raw labels).
    Returns {"genres": {genre: {<_GENRE_KEYS>}}, "totals": {<_GENRE_KEYS>}}.
    """
    genres = {}
    totals = _empty_genre()
    for r in records:
        g = r.get("genre") or "UNKNOWN"
        labels = r.get("annotator_labels") or []
        gold = r.get("gold")
        cell = genres.setdefault(g, _empty_genre())

        for d in (cell, totals):
            d["n"] += 1

        b = _bucket_of(gold, labels)
        if b == "dash":
            for d in (cell, totals):
                d["dash"] += 1
            continue

        # Valid (non-dash) gold from here on.
        gold_n = norm_label(gold)
        matches = agreement_count(labels, gold)       # >= 3 for a valid gold
        norm_count = sum(1 for a in labels if norm_label(a) is not None)
        is_majority = (majority_label(labels) == gold_n)
        for d in (cell, totals):
            d["valid"] += 1
            d["b%s" % b] += 1
            if b == "5":
                d["unanimous"] += 1
            if is_majority:
                d["gold_eq_majority"] += 1
            d["label_matches"] += matches
            d["labels"] += norm_count

    return {"genres": genres, "totals": totals}


def flatten(stats):
    """Flatten per-genre tallies into a single integer dict keyed ``<genre>_<field>``."""
    out = {}
    for genre, cell in stats["genres"].items():
        for k in _GENRE_KEYS:
            out["%s_%s" % (genre, k)] = cell[k]
    return out


def unanimous_rate(stats, genre):
    """Share of a genre's valid-gold examples whose five annotators were unanimous (0.0 if empty)."""
    c = stats["genres"].get(genre)
    if not c or c["valid"] == 0:
        return 0.0
    return c["unanimous"] / c["valid"]


def individual_agreement_rate(stats, genre):
    """Share of a genre's individual annotator labels that equal the gold (the paper's Agrmt.)."""
    c = stats["genres"].get(genre)
    if not c or c["labels"] == 0:
        return 0.0
    return c["label_matches"] / c["labels"]
