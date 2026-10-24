"""Does ANLI's writer-vs-verifier agreement depend on the gold class?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

Audit 39 (anli-verifier-majority-census) joined ANLI's writer-set gold to the separately released
verifier labels and found the writer's gold equals the strict verifier majority 99.87% of the time
overall, broken down only by round. Audits 42 (SNLI) and 44 (MultiNLI) found that *original 5-annotator*
decisiveness depends strongly on the gold class -- contradiction most decisive, neutral least -- on both
corpora. This module asks the question that bridges the two families: when the gold is the ANLI writer's
*adversarial* label and the votes come from *independent verifiers* (not the original annotators), does
decisiveness still depend on the gold class, and is neutral again the least decisive?

ANLI's verifier protocol: every example is checked by 2 verifiers; a 3rd is added only when the first 2
disagree. So a 2-label line means the two verifiers agreed immediately (a unanimous pair), and a 3-label
line means they disagreed and a tie-breaker was added. "Verifier unanimity" here = all verifier labels
identical, which for this protocol is equivalent to "the first two verifiers agreed, no third needed".

This module normalises labels to e/n/c, joins verifier lines to the main gold by uid, and tallies, per
gold class (and split-group), the verifier unanimity, the gold-vs-majority outcome, and the k=2/k=3 mix.
The logic is ANLI-specific; the label/majority primitives match audit 39 verbatim so the two audits are
directly comparable.

Apache-2.0.
"""

LETTERS = ("e", "n", "c")


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


# Per-class tally fields and the global totals the census emits.
_CLASS_FIELDS = ("n", "unanimous", "match", "differ", "no_majority", "k2", "k3", "k_other", "k2_split")
_TOTAL_KEYS = ("n_verifier_lines", "n_joined", "n_orphan", "n_train", "n_devtest", "n_gold_unexpected")


def _blank_class():
    return {f: 0 for f in _CLASS_FIELDS}


def _blank_class_table():
    return {g: _blank_class() for g in LETTERS}


def census_by_class(verifier_rows, gold_index):
    """Join verifier labels to gold by uid and tally the derivation outcome per gold class.

    ``verifier_rows``: iterable of {"uid": str, "labels": [raw_label, ...]}.
    ``gold_index``: uid -> {"split": "train"/"dev"/"test", "round": "R1"..,"gold": raw_label}.

    Returns totals plus three per-class tables: ``per_class`` over every joined example with a recognised
    gold, ``per_class_devtest`` over the dev/test subset, and ``per_class_train`` over the train subset
    (audit 39 showed the released verifier file also covers train). Each cell records n, verifier
    unanimity, the gold-vs-strict-majority outcome, and the k=2/k=3 verifier-count mix. ``k2_split`` counts
    2-label lines whose two verifiers in fact disagree -- expected 0 under the stated protocol, tracked as
    an anomaly check.
    """
    totals = {k: 0 for k in _TOTAL_KEYS}
    per_class = _blank_class_table()
    per_class_devtest = _blank_class_table()
    per_class_train = _blank_class_table()
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
        is_train = (split == "train")
        if is_train:
            totals["n_train"] += 1
        else:
            totals["n_devtest"] += 1

        gold = norm_label(main["gold"])
        if gold is None:
            totals["n_gold_unexpected"] += 1
            continue

        present = [x for x in vls if x is not None]
        unanimous = (k >= 2 and len(present) == k and len(set(present)) == 1)
        maj = strict_majority(vls)

        tables = [per_class]
        tables.append(per_class_train if is_train else per_class_devtest)
        for tbl in tables:
            cell = tbl[gold]
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
                                    "verifier_labels": vls, "split": split, "round": main["round"]})

    return {
        "totals": totals,
        "per_class": per_class,
        "per_class_devtest": per_class_devtest,
        "per_class_train": per_class_train,
        "examples_differ": examples_differ,
    }


def flatten(stats):
    """Integer keys only (drops examples), for comparison against a frozen hand-traced TARGET."""
    out = {k: stats["totals"][k] for k in _TOTAL_KEYS}
    for g in LETTERS:
        for f in _CLASS_FIELDS:
            out["%s_%s" % (g, f)] = stats["per_class"][g][f]
    for g in LETTERS:
        for f in ("n", "unanimous", "match", "differ", "no_majority"):
            out["dt_%s_%s" % (g, f)] = stats["per_class_devtest"][g][f]
            out["tr_%s_%s" % (g, f)] = stats["per_class_train"][g][f]
    return out
