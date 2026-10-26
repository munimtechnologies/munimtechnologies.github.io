"""ANLI per-(genre, class) verifier agreement WITHIN R3: is neutral the least decisive class in every domain?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

Audit 49 showed that, once the adversary round is held fixed at R3, the text domain (`genre`) barely
predicts how decisively ANLI's verifiers back the writer's gold (R3 cross-genre gold-support spread only
0.0175). Audits 42/44/45 showed the opposite for the gold CLASS: neutral is the least decisively
verified relation on SNLI, MultiNLI and (pooled) ANLI. This audit crosses the two inside the single
round where all six genres coexist -- R3 -- and asks whether the class effect (neutral least decisive)
holds INSIDE each genre, with the round held fixed so neither a round nor a round*genre confound can
masquerade as a class effect.

Per (genre, class) cell, restricted to R3, it tallies: the strict-majority agreement rate (gold == strict
verifier majority), the gold-support rate (fraction of individual verifier votes equalling the writer
gold -- a continuous decisiveness measure), and the unanimous rate (all verifiers on the line agree). The
all-lines match/differ/no-majority totals (over every joined line, any round/genre) reproduce audits
39/48/49 as a cross-check.

The label / majority primitives below match audits 39/45/46/47/48/49 verbatim.

Apache-2.0.
"""

LETTERS = ("e", "n", "c")
ROUNDS = ("R1", "R2", "R3")


def norm_label(x):
    """Normalise an NLI label to a single lowercase letter in {e, n, c}, else None."""
    if x is None:
        return None
    s = str(x).strip().lower()
    if not s:
        return None
    first = s[0]
    return first if first in LETTERS else None


def parse_verifier_row(obj):
    """Pull uid and the raw verifier-label list from one verifier_labels_R1-3.jsonl record.

    The released file spells the key with a space ("verifier labels"); tolerate an underscore form too.
    """
    labels = obj.get("verifier labels")
    if labels is None:
        labels = obj.get("verifier_labels")
    if not isinstance(labels, list):
        labels = []
    return {"uid": obj.get("uid"), "labels": list(labels)}


def strict_majority(labels):
    """Return the label held by strictly more than half the (normalised, non-None) votes, else None."""
    labels = [x for x in labels if x is not None]
    if not labels:
        return None
    best = None
    best_n = 0
    for lab in set(labels):
        n = labels.count(lab)
        if n > best_n:
            best_n, best = n, lab
    return best if best_n * 2 > len(labels) else None


def genre_key(x):
    """Non-empty stripped genre string, else None (so '' / whitespace / None are 'absent')."""
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None


CELL_FIELDS = ("n", "gold_majority", "no_majority", "gold_votes", "total_votes", "unanimous")

TOTAL_KEYS = ("n_verifier_lines", "n_joined", "n_orphan", "n_gold_unexpected", "n_genre_absent",
              "n_not_r3", "all_lines_match", "all_lines_differ", "all_lines_no_majority")


def _blank():
    return {f: 0 for f in CELL_FIELDS}


def _update(cell, gold, vls):
    """Fold one joined, gold-known, R3, genre-present verifier line into a per-(genre,class) tally."""
    cell["n"] += 1
    nn = [x for x in vls if x is not None]
    cell["total_votes"] += len(nn)
    cell["gold_votes"] += sum(1 for x in nn if x == gold)
    if len(nn) >= 2 and len(set(nn)) == 1:
        cell["unanimous"] += 1
    maj = strict_majority(vls)
    if maj is None:
        cell["no_majority"] += 1
    elif maj == gold:
        cell["gold_majority"] += 1


def census_genre_class(verifier_rows, gold_index):
    """Join verifier labels to gold/genre/round by uid and tally agreement per (genre, class) within R3.

    ``verifier_rows``: iterable of {"uid": str, "labels": [raw_label, ...]}.
    ``gold_index``: uid -> {"round": str, "split": str, "gold": raw_label, "genre": raw_genre}.

    Returns totals plus ``by_cell`` keyed "<genre>|<class>" over R3 lines whose genre is present. The
    all-lines match/differ/no-majority totals (over EVERY joined line, any round/genre) reproduce audits
    39/48/49 as a cross-check. Non-R3 lines and genre-absent lines are counted in totals but not attributed
    to any cell.
    """
    totals = {k: 0 for k in TOTAL_KEYS}
    by_cell = {}

    for row in verifier_rows:
        totals["n_verifier_lines"] += 1
        uid = row.get("uid")
        vls = [norm_label(x) for x in (row.get("labels") or [])]

        main = gold_index.get(uid)
        if main is None:
            totals["n_orphan"] += 1
            continue
        totals["n_joined"] += 1

        gold = norm_label(main.get("gold"))
        if gold is None:
            totals["n_gold_unexpected"] += 1
            continue

        maj = strict_majority(vls)
        if maj is None:
            totals["all_lines_no_majority"] += 1
        elif maj == gold:
            totals["all_lines_match"] += 1
        else:
            totals["all_lines_differ"] += 1

        if main.get("round") != "R3":
            totals["n_not_r3"] += 1
            continue
        g = genre_key(main.get("genre"))
        if g is None:
            totals["n_genre_absent"] += 1
            continue
        key = "%s|%s" % (g, gold)
        by_cell.setdefault(key, _blank())
        _update(by_cell[key], gold, vls)

    return {"totals": totals, "by_cell": by_cell}


def flatten(stats):
    """Integer-only flat view (totals + per-cell tallies) for TARGET comparison, deterministic order."""
    out = {k: stats["totals"][k] for k in TOTAL_KEYS}
    for key in sorted(stats["by_cell"]):
        g, c = key.split("|")
        for f in CELL_FIELDS:
            out["gc_%s_%s_%s" % (g, c, f)] = stats["by_cell"][key][f]
    return out
