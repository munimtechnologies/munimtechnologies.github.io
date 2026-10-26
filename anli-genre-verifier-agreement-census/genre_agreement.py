"""ANLI per-genre verifier agreement: does the text domain predict how decisively verifiers back gold?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

The coverage diagnostic that preceded this audit confirmed ANLI's `genre` field is populated on all
169,265 main examples (and all 29,803 verified-subset rows), taking six values: wikipedia, rte,
procedural/causal, news, legal/formal and fiction. Crucially, `genre` is NOT an R3-only phenomenon --
wikipedia spans R1/R2/R3 while the other five values are R3-only -- so a naive per-genre breakdown
confounds genre with the adversary round (audit 46 showed verifier unanimity falls R1 76.9% -> R2
69.1% -> R3 68.1%). This audit therefore tallies, per genre, how decisively ANLI's verifiers back the
writer's adversarial gold BOTH pooled across rounds AND within R3 only (round held fixed), so a pooled
genre effect can be checked against a Simpson's-paradox artifact of round composition.

Two per-genre measures are reported: the strict-majority agreement rate (does gold == the strict
verifier majority?) and the gold-support rate (the fraction of individual verifier votes that equal the
writer's gold -- a continuous decisiveness measure that is well defined for k=2 and k=3 lines alike).

The label / majority primitives below match audits 39/45/46/47/48 verbatim.

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


GENRE_FIELDS = ("n", "gold_majority", "no_majority", "majority_differs", "gold_votes", "total_votes")

TOTAL_KEYS = ("n_verifier_lines", "n_joined", "n_orphan", "n_gold_unexpected", "n_genre_absent",
              "all_lines_match", "all_lines_differ", "all_lines_no_majority")


def _blank():
    return {f: 0 for f in GENRE_FIELDS}


def _update(tally, gold, vls):
    """Fold one joined, gold-known verifier line (list of normalised labels) into a per-genre tally."""
    tally["n"] += 1
    nn = [x for x in vls if x is not None]
    tally["total_votes"] += len(nn)
    tally["gold_votes"] += sum(1 for x in nn if x == gold)
    maj = strict_majority(vls)
    if maj is None:
        tally["no_majority"] += 1
    elif maj == gold:
        tally["gold_majority"] += 1
    else:
        tally["majority_differs"] += 1


def census_genre(verifier_rows, gold_index):
    """Join verifier labels to gold/genre/round by uid and tally agreement per genre.

    ``verifier_rows``: iterable of {"uid": str, "labels": [raw_label, ...]}.
    ``gold_index``: uid -> {"round": str, "split": str, "gold": raw_label, "genre": raw_genre}.

    Returns totals plus ``by_genre`` (one tally per genre, pooled over all rounds) and ``by_genre_r3``
    (the same restricted to R3 lines, so genre is compared with the adversary round held fixed). The
    all-lines match/differ/no-majority totals (over every joined line) reproduce audit 39/48 as a
    cross-check. Lines with an absent genre are counted in totals but not attributed to any genre.
    """
    totals = {k: 0 for k in TOTAL_KEYS}
    by_genre = {}
    by_genre_r3 = {}

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

        g = genre_key(main.get("genre"))
        if g is None:
            totals["n_genre_absent"] += 1
            continue
        by_genre.setdefault(g, _blank())
        _update(by_genre[g], gold, vls)
        if main.get("round") == "R3":
            by_genre_r3.setdefault(g, _blank())
            _update(by_genre_r3[g], gold, vls)

    return {"totals": totals, "by_genre": by_genre, "by_genre_r3": by_genre_r3}


def flatten(stats):
    """Integer-only flat view (totals + per-genre and per-R3-genre tallies) for TARGET comparison."""
    out = {k: stats["totals"][k] for k in TOTAL_KEYS}
    for g in sorted(stats["by_genre"]):
        for f in GENRE_FIELDS:
            out["genre_%s_%s" % (g, f)] = stats["by_genre"][g][f]
    for g in sorted(stats["by_genre_r3"]):
        for f in GENRE_FIELDS:
            out["genre_r3_%s_%s" % (g, f)] = stats["by_genre_r3"][g][f]
    return out
