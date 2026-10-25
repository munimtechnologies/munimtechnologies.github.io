"""Does ANLI verifier decisiveness depend on WHICH wrong label the adversary model predicted?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

ANLI is adversarial: a human writer, shown a premise and a target label, writes a hypothesis meant to
FOOL a model-in-the-loop, and the retained examples are (by construction) ones the model got wrong. Each
main example therefore carries a `model_label` -- the label the target model predicted -- alongside the
writer's `label` (gold). Audits 39, 45 and 46 measured how decisively ANLI's 2-3 independent verifiers
agree with the writer's gold, broken down by round (39), by gold class (45) and by (round, class) (46).
None of them looked at `model_label`. This module crosses the writer gold with the model's predicted
label: for each (gold, model_label) cell it tallies verifier unanimity and the writer-gold-vs-verifier
agreement, to ask whether the specific error the adversary made predicts how decisively the verifiers
then endorse the writer's label -- and, as a structural check, to confirm at the data level that the
retained examples really did fool the model (model_label != gold).

The label / majority primitives below match audits 39/45/46 verbatim. A missing or unrecognised
model_label is bucketed as "x" so nothing is silently dropped.

Apache-2.0.
"""

LETTERS = ("e", "n", "c")
MLABELS = ("e", "n", "c", "x")  # x = model_label missing or unrecognised


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


def get_model_label(obj):
    """Pull the adversary model's predicted label from a main ANLI record (underscore or space key)."""
    v = obj.get("model_label")
    if v is None:
        v = obj.get("model label")
    return v


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
_TOTAL_KEYS = ("n_verifier_lines", "n_joined", "n_orphan", "n_gold_unexpected",
               "n_model_label_recognised", "n_model_label_missing", "n_model_fooled", "n_model_agreed")


def _blank_class():
    return {f: 0 for f in _CLASS_FIELDS}


def _blank_gm_table():
    return {g: {m: _blank_class() for m in MLABELS} for g in LETTERS}


def mlabel_bucket(model_label):
    """Bucket a raw model_label into one of {e, n, c, x}; x = missing/unrecognised."""
    m = norm_label(model_label)
    return m if m is not None else "x"


def census_by_gold_modellabel(verifier_rows, gold_index):
    """Join verifier labels to gold by uid and tally the outcome per (gold class, model_label bucket).

    ``verifier_rows``: iterable of {"uid": str, "labels": [raw_label, ...]}.
    ``gold_index``: uid -> {"split": str, "gold": raw_label, "model_label": raw_label}.

    Returns totals plus ``per_gold_mlabel[gold][mlabel]`` cells, each recording n, verifier unanimity,
    the gold-vs-strict-majority outcome, and the k=2/k=3 verifier-count mix. Examples whose gold is
    unrecognised are counted in totals (n_gold_unexpected) but not placed in a cell.
    """
    totals = {k: 0 for k in _TOTAL_KEYS}
    per_gold_mlabel = _blank_gm_table()
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

        gold = norm_label(main["gold"])
        if gold is None:
            totals["n_gold_unexpected"] += 1
            continue

        ml = norm_label(main.get("model_label"))
        mbucket = ml if ml is not None else "x"
        if ml is None:
            totals["n_model_label_missing"] += 1
        else:
            totals["n_model_label_recognised"] += 1
            if ml == gold:
                totals["n_model_agreed"] += 1
            else:
                totals["n_model_fooled"] += 1

        present = [x for x in vls if x is not None]
        unanimous = (k >= 2 and len(present) == k and len(set(present)) == 1)
        maj = strict_majority(vls)

        cell = per_gold_mlabel[gold][mbucket]
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
            examples_differ.append({"uid": uid, "gold": gold, "model_label": mbucket,
                                    "verifier_majority": maj, "verifier_labels": vls,
                                    "split": main.get("split")})

    return {"totals": totals, "per_gold_mlabel": per_gold_mlabel, "examples_differ": examples_differ}


def aggregate_over_mlabels(per_gold_mlabel):
    """Sum per_gold_mlabel over model_label buckets into a per-gold-class table (cross-checks audit 45)."""
    out = {g: _blank_class() for g in LETTERS}
    for g in LETTERS:
        for m in MLABELS:
            for f in _CLASS_FIELDS:
                out[g][f] += per_gold_mlabel[g][m][f]
    return out


def flatten_gm(per_gold_mlabel, totals):
    """Integer-only flat view (gold x mlabel x field + totals) for comparison to a hand-traced TARGET."""
    out = {k: totals[k] for k in _TOTAL_KEYS}
    for g in LETTERS:
        for m in MLABELS:
            for f in _CLASS_FIELDS:
                out["%s_%s_%s" % (g, m, f)] = per_gold_mlabel[g][m][f]
    return out
