"""The ANLI verifier tiebreaker: what happens on the lines where a third verifier was added?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

ANLI's verification protocol adds a *third* verifier only when the first two disagree, so every
three-label verifier line (k=3) is a tiebreak: two independent verifiers split, and a third was
brought in to settle it. Audits 39/45/46 counted the k=2 / k=3 mix but never looked *inside* the
tiebreak subset. This module isolates the k=3 lines and asks, per round and per gold class:

- is the tiebreak subset really the disagreement subset (do the first two verifiers in fact differ)?
- when a third verifier breaks the tie, does it side with the writer's gold, with the other first
  verifier, or introduce a third distinct label (leaving no strict majority)?
- how decisively does the writer's adversarial gold survive the tiebreak?

The label / majority primitives below match audits 39/45/46/47 verbatim.

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


TB_FIELDS = ("n", "firsttwo_differ", "firsttwo_agree", "majority_formed", "no_majority",
             "match", "differ", "gold_in_firsttwo", "gold_not_in_firsttwo",
             "n_tiebreak", "tiebreak_gold", "tiebreak_other", "tiebreak_third")

TOTAL_KEYS = ("n_verifier_lines", "n_joined", "n_orphan", "n_gold_unexpected",
              "k2", "k3", "k_other", "all_lines_match", "all_lines_differ", "all_lines_no_majority")


def _blank_tally():
    return {f: 0 for f in TB_FIELDS}


def _update_tiebreak(tally, gold, l1, l2, l3, maj):
    """Update one tiebreak tally with a single k=3 (joined, gold-known) verifier line."""
    tally["n"] += 1
    differ = (l1 is not None and l2 is not None and l1 != l2)
    if differ:
        tally["firsttwo_differ"] += 1
    else:
        tally["firsttwo_agree"] += 1
    if maj is None:
        tally["no_majority"] += 1
    else:
        tally["majority_formed"] += 1
        if maj == gold:
            tally["match"] += 1
        else:
            tally["differ"] += 1
    gold_in = gold in (l1, l2)
    if gold_in:
        tally["gold_in_firsttwo"] += 1
    else:
        tally["gold_not_in_firsttwo"] += 1
    # The tiebreak proper: first two genuinely disagree AND the writer's gold is one of them, so the
    # third verifier's vote decides whether the gold becomes the majority.
    if differ and gold_in:
        tally["n_tiebreak"] += 1
        other = l1 if l2 == gold else l2
        if l3 == gold:
            tally["tiebreak_gold"] += 1
        elif l3 == other:
            tally["tiebreak_other"] += 1
        else:
            tally["tiebreak_third"] += 1


def census_tiebreak(verifier_rows, gold_index):
    """Join verifier labels to gold by uid and tally the k=3 tiebreak outcome overall / by round / by class.

    ``verifier_rows``: iterable of {"uid": str, "labels": [raw_label, ...]}.
    ``gold_index``: uid -> {"split": str, "round": str, "gold": raw_label}.

    Returns totals plus ``overall`` (one tiebreak tally over all k=3 lines), ``by_round`` and
    ``by_class`` (tiebreak tallies keyed by round / gold class), and a small sample of tiebreak lines
    whose final majority differs from the writer's gold. The all-lines match/differ/no-majority totals
    (over every joined line, any k) reproduce audit 39 as a cross-check.
    """
    totals = {k: 0 for k in TOTAL_KEYS}
    overall = _blank_tally()
    by_round = {r: _blank_tally() for r in ROUNDS}
    by_class = {g: _blank_tally() for g in LETTERS}
    examples_tiebreak_differ = []

    for row in verifier_rows:
        totals["n_verifier_lines"] += 1
        uid = row.get("uid")
        raw = row.get("labels") or []
        k = len(raw)
        vls = [norm_label(x) for x in raw]

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

        if k == 2:
            totals["k2"] += 1
        elif k == 3:
            totals["k3"] += 1
            l1, l2, l3 = vls[0], vls[1], vls[2]
            _update_tiebreak(overall, gold, l1, l2, l3, maj)
            rnd = main.get("round")
            if rnd in by_round:
                _update_tiebreak(by_round[rnd], gold, l1, l2, l3, maj)
            _update_tiebreak(by_class[gold], gold, l1, l2, l3, maj)
            if maj != gold and len(examples_tiebreak_differ) < 10:
                examples_tiebreak_differ.append(
                    {"uid": uid, "gold": gold, "verifier_labels": vls,
                     "verifier_majority": maj, "round": rnd, "split": main.get("split")})
        else:
            totals["k_other"] += 1

    return {"totals": totals, "overall": overall, "by_round": by_round, "by_class": by_class,
            "examples_tiebreak_differ": examples_tiebreak_differ}


def flatten(stats):
    """Integer-only flat view (totals + overall/class/round tallies) for comparison to a TARGET."""
    out = {k: stats["totals"][k] for k in TOTAL_KEYS}
    for f in TB_FIELDS:
        out["overall_%s" % f] = stats["overall"][f]
    for g in LETTERS:
        for f in TB_FIELDS:
            out["class_%s_%s" % (g, f)] = stats["by_class"][g][f]
    for r in ROUNDS:
        for f in TB_FIELDS:
            out["round_%s_%s" % (r, f)] = stats["by_round"][r][f]
    return out
