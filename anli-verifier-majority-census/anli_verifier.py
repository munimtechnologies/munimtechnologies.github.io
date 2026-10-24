"""Does ANLI's gold label agree with the strict majority of its verifier labels?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

The gold-label-derivation family (audits 37 SNLI, 38 MultiNLI) checks that a benchmark's gold label *is*
the strict majority of its per-annotator votes. SNLI and MultiNLI pass by construction: their gold is
defined as that majority. ANLI (Nie, Williams, Dinan, Bansal, Weston and Kiela, 2020) is built the
opposite way. A human writer invents a (premise, hypothesis, label) triple that fools a model in the
loop; the writer's label becomes the gold and is kept whether or not later readers agree with it. Every
dev and test example was then checked by 2 verifiers (a 3rd is added when the first 2 disagree), and
those verifier labels were released separately (verifier_labels_R1-3.jsonl, May 2022).

So for ANLI the question is genuinely open and the opposite of a tautology: how often does the writer's
gold label equal the strict majority of the independent verifiers, how often do the verifiers agree with
each other but disagree with the gold, and how often do they reach no majority at all?

This module normalises labels to a single letter (e/n/c), builds a uid -> verifier-label map, joins it to
the main gold labels, and counts the derivation outcome per round and split. The logic is ANLI-specific
(the join and the writer-vs-verifier framing) rather than reused from audits 37/38.

Apache-2.0.
"""

LETTERS = ("e", "n", "c")


def norm_label(x):
    """Normalise an NLI label to a single lowercase letter in {e, n, c}, else None.

    Handles both ANLI's abbreviated labels ("e"/"n"/"c") and spelled-out forms
    ("entailment"/"neutral"/"contradiction"); anything else (e.g. "-") returns None.
    """
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
    """Return the label held by strictly more than half the (normalised) votes, else None.

    Empty -> None. Two equal votes -> that label (2*2 > 2). Two unequal -> None (1-1 tie).
    Three votes 2-1 -> the pair; three votes all different (1-1-1) -> None.
    """
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


_FLAT_KEYS = (
    "n_verifier_lines", "n_joined", "n_orphan", "n_join_train", "n_join_dev", "n_join_test",
    "n_gold_matches_majority", "n_gold_differs_from_majority", "n_no_majority", "n_gold_unexpected",
    "n_unanimous", "n_unanimous_differs_from_gold", "n_k2", "n_k3", "n_k_other",
)


def census(verifier_rows, gold_index, max_examples=5):
    """Join verifier labels to gold labels and count the derivation outcome.

    ``verifier_rows`` is an iterable of {"uid": str, "labels": [raw_label, ...]}.
    ``gold_index`` maps uid -> {"split": "train"/"dev"/"test", "round": "R1".., "gold": raw_label}.

    For every verifier line we record whether its uid joins to a main example and, if so, to which
    split; then, for joined dev/test examples, whether the writer's gold equals the strict verifier
    majority, differs from it, or the verifiers reach no majority. ``n_unanimous_differs_from_gold`` is
    the striking case: every verifier agreed with each other but none agreed with the gold.
    """
    s = {k: 0 for k in _FLAT_KEYS}
    per_round = {}
    examples_differ = []
    examples_unanimous_differ = []
    for row in verifier_rows:
        s["n_verifier_lines"] += 1
        uid = row.get("uid")
        vls = [norm_label(x) for x in (row.get("labels") or [])]
        k = len(vls)
        if k == 2:
            s["n_k2"] += 1
        elif k == 3:
            s["n_k3"] += 1
        else:
            s["n_k_other"] += 1

        main = gold_index.get(uid)
        if main is None:
            s["n_orphan"] += 1
            continue
        s["n_joined"] += 1
        split = main["split"]
        rnd = main["round"]
        s["n_join_%s" % split] = s.get("n_join_%s" % split, 0) + 1
        bucket = per_round.setdefault(rnd, {"joined": 0, "match": 0, "differ": 0, "no_majority": 0})
        bucket["joined"] += 1

        gold = norm_label(main["gold"])
        maj = strict_majority(vls)
        unanimous = (k >= 2 and len({x for x in vls if x is not None}) == 1
                     and all(x is not None for x in vls))
        if unanimous:
            s["n_unanimous"] += 1

        if gold is None:
            s["n_gold_unexpected"] += 1
            continue
        if maj is None:
            s["n_no_majority"] += 1
            bucket["no_majority"] += 1
        elif maj == gold:
            s["n_gold_matches_majority"] += 1
            bucket["match"] += 1
        else:
            s["n_gold_differs_from_majority"] += 1
            bucket["differ"] += 1
            if len(examples_differ) < max_examples:
                examples_differ.append({"uid": uid, "gold": gold, "verifier_majority": maj,
                                        "verifier_labels": vls, "split": split, "round": rnd})
            if unanimous:
                s["n_unanimous_differs_from_gold"] += 1
                if len(examples_unanimous_differ) < max_examples:
                    examples_unanimous_differ.append({"uid": uid, "gold": gold,
                                                      "verifier_labels": vls, "split": split,
                                                      "round": rnd})
    out = dict(s)
    out["per_round"] = {r: per_round[r] for r in sorted(per_round)}
    out["examples_differ"] = examples_differ
    out["examples_unanimous_differ"] = examples_unanimous_differ
    return out


def flatten(stats):
    """Integer census keys only (drops per_round and examples) for comparison against a frozen TARGET."""
    return {k: stats[k] for k in _FLAT_KEYS}
