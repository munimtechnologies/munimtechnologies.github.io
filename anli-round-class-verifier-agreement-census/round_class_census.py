"""Does ANLI's per-class verifier decisiveness hold WITHIN each adversarial round?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

Audit 39 (anli-verifier-majority-census) broke ANLI writer-vs-verifier agreement down by ROUND and
found the match rate rising to a near-perfect R3. Audit 45 (anli-class-verifier-agreement-census)
broke it down by gold CLASS, pooling all rounds, and found neutral the least decisively verified class
(unanimous 67.3%) with the full ordering entailment > contradiction > neutral. ANLI's three rounds are
collected against progressively stronger model-in-the-loop adversaries (R1 against a BERT-style model,
R2/R3 against models trained on the prior rounds), so pooling rounds risks a Simpson's-paradox artifact:
an aggregate "neutral least decisive" could be produced by round composition rather than being true
within each round. This module crosses the two dimensions -- per (round, class) -- to test whether the
per-class ordering is a WITHIN-round effect and whether verifier decisiveness shifts as the adversary
strengthens.

ANLI's verifier protocol: every example is checked by 2 verifiers; a 3rd is added only when the first 2
disagree. "Verifier unanimity" = all verifier labels identical (for a 2-label line, the two agreed and
no third was needed). The label / majority primitives below match audits 39 and 45 verbatim, so the
per-class aggregate here reproduces audit 45 exactly as a built-in cross-check.

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


_CLASS_FIELDS = ("n", "unanimous", "match", "differ", "no_majority", "k2", "k3", "k_other", "k2_split")
_TOTAL_KEYS = ("n_verifier_lines", "n_joined", "n_orphan", "n_train", "n_devtest", "n_gold_unexpected")


def _blank_class():
    return {f: 0 for f in _CLASS_FIELDS}


def _blank_rc_table():
    return {r: {g: _blank_class() for g in LETTERS} for r in ROUNDS}


def census_by_round_class(verifier_rows, gold_index):
    """Join verifier labels to gold by uid and tally the outcome per (round, gold class).

    ``verifier_rows``: iterable of {"uid": str, "labels": [raw_label, ...]}.
    ``gold_index``: uid -> {"split": str, "round": "R1".."R3", "gold": raw_label}.

    Returns totals plus ``per_round_class[round][class]`` cells, each recording n, verifier unanimity,
    the gold-vs-strict-majority outcome, and the k=2/k=3 verifier-count mix. Examples whose round is not
    in ROUNDS, or whose gold is unrecognised, are counted in totals but not placed in a cell.
    """
    totals = {k: 0 for k in _TOTAL_KEYS}
    per_round_class = _blank_rc_table()
    examples_differ = []
    for row in verifier_rows:
        totals["n_verifier_lines"] += 1
        uid = row.get("uid")
        raw = row.get("labels") or []
        vls = [norm_label(x) for x in raw]
        k = len(raw)

        main = gold_index.get(uid)
        if main is None:
            totals["n_orphan"] += 1
            continue
        totals["n_joined"] += 1
        split = main["split"]
        if split == "train":
            totals["n_train"] += 1
        else:
            totals["n_devtest"] += 1

        gold = norm_label(main["gold"])
        if gold is None:
            totals["n_gold_unexpected"] += 1
            continue
        rnd = main["round"]
        if rnd not in ROUNDS:
            continue

        present = [x for x in vls if x is not None]
        unanimous = (k >= 2 and len(present) == k and len(set(present)) == 1)
        maj = strict_majority(vls)

        cell = per_round_class[rnd][gold]
        cell["n"] += 1
        if k == 2:
            cell["k2"] += 1
            if not unanimous:
                cell["k2_split"] += 1
        elif k == 3:
            cell["k3"] += 1
        else:
            cell["k_other"] += 1
        if unanimous:
            cell["unanimous"] += 1
        if maj is None:
            cell["no_majority"] += 1
        elif maj == gold:
            cell["match"] += 1
        else:
            cell["differ"] += 1

        if maj is not None and maj != gold and len(examples_differ) < 10:
            examples_differ.append({"uid": uid, "gold": gold, "verifier_majority": maj,
                                    "verifier_labels": vls, "split": split, "round": rnd})

    return {"totals": totals, "per_round_class": per_round_class, "examples_differ": examples_differ}


def aggregate_over_rounds(per_round_class):
    """Sum per_round_class into a per-class table (across rounds): reproduces audit 45's per_class."""
    out = {g: _blank_class() for g in LETTERS}
    for r in ROUNDS:
        for g in LETTERS:
            for f in _CLASS_FIELDS:
                out[g][f] += per_round_class[r][g][f]
    return out


def aggregate_over_classes(per_round_class):
    """Sum per_round_class into a per-round table (across classes): reproduces audit 39's per-round."""
    out = {r: _blank_class() for r in ROUNDS}
    for r in ROUNDS:
        for g in LETTERS:
            for f in _CLASS_FIELDS:
                out[r][f] += per_round_class[r][g][f]
    return out


def flatten_rc(per_round_class, totals):
    """Integer-only flat view (round x class x field + totals) for comparison to a hand-traced TARGET."""
    out = {k: totals[k] for k in _TOTAL_KEYS}
    for r in ROUNDS:
        for g in LETTERS:
            for f in _CLASS_FIELDS:
                out["%s_%s_%s" % (r, g, f)] = per_round_class[r][g][f]
    return out
