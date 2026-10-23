"""Is SNLI's gold_label really the strict majority of its annotator_labels, and are the '-' rows the
ones with no majority?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

SNLI (Bowman, Angeli, Potts and Manning, 2015) ships, for each premise/hypothesis pair, an
``annotator_labels`` list and a single ``gold_label``. The release documents two rules it assumes but
never checks row-by-row on the published files:

1. ``gold_label`` is the *strict majority* of ``annotator_labels`` (a label held by more than half the
   annotators). The train split carries the single author label; the dev and test splits were validated
   by five annotators, so there the majority rule is non-trivial.
2. When no label reaches a strict majority, ``gold_label`` is ``-`` (no consensus) and the row is meant
   to be dropped before training or scoring. Forgetting to drop ``-`` rows is a well-known loader trap.

This module counts, per split: labeled vs no-consensus rows; whether every labeled row's gold equals the
strict majority of its annotators (and whether a labeled row ever lacks a majority at all); whether any
``-`` row actually *does* have a strict majority (a filter anomaly); and the multi-annotator agreement
profile (how many five-way rows are unanimous).

Apache-2.0.
"""
from collections import Counter

LABELS = ("entailment", "neutral", "contradiction")
NO_CONSENSUS = "-"


def strict_majority(labels):
    """Return the label held by strictly more than half the annotators, else None.

    An empty list has no majority. A single label is trivially its own majority (1 > 0.5). A five-way
    2-2-1 split has none; a 3-2 split has one.
    """
    if not labels:
        return None
    label, n = Counter(labels).most_common(1)[0]
    return label if n * 2 > len(labels) else None


def parse_row(obj):
    """Pull the two fields the census needs from one SNLI record: gold_label and annotator_labels."""
    ann = obj.get("annotator_labels") or []
    if not isinstance(ann, list):
        ann = []
    return {"gold": obj.get("gold_label"), "annotators": [str(a) for a in ann]}


_FLAT_KEYS = (
    "n_total", "n_labeled", "n_no_consensus", "n_no_annotators",
    "n_gold_matches_majority", "n_gold_mismatch_majority",
    "n_labeled_without_majority", "n_no_consensus_with_majority",
    "n_multi", "n_unanimous_multi",
)


def agreement_stats(rows, max_examples=5):
    """Census of gold-label derivation and annotator agreement over one split.

    A *labeled* row has gold in LABELS; a *no-consensus* row has gold ``-``. ``n_gold_mismatch_majority``
    counts labeled rows whose gold differs from the strict annotator majority; ``n_labeled_without_majority``
    counts labeled rows whose annotators have no strict majority at all; ``n_no_consensus_with_majority``
    counts ``-`` rows that nonetheless have a strict majority. All three should be 0 if the two
    documented rules hold. ``n_multi`` is rows with >= 2 annotators and ``n_unanimous_multi`` those among
    them whose annotators all agree.
    """
    s = {k: 0 for k in _FLAT_KEYS}
    agreement_hist = {}
    examples_mismatch = []
    examples_consensus_with_majority = []
    for r in rows:
        s["n_total"] += 1
        gold = r["gold"]
        ann = r["annotators"]
        k = len(ann)
        agreement_hist[k] = agreement_hist.get(k, 0) + 1
        if k == 0:
            s["n_no_annotators"] += 1
        if k >= 2:
            s["n_multi"] += 1
            if len(set(ann)) == 1:
                s["n_unanimous_multi"] += 1
        maj = strict_majority(ann)
        if gold == NO_CONSENSUS:
            s["n_no_consensus"] += 1
            if maj is not None:
                s["n_no_consensus_with_majority"] += 1
                if len(examples_consensus_with_majority) < max_examples:
                    examples_consensus_with_majority.append({"gold": gold, "annotators": ann})
        elif gold in LABELS:
            s["n_labeled"] += 1
            if maj is None:
                s["n_labeled_without_majority"] += 1
            elif maj == gold:
                s["n_gold_matches_majority"] += 1
            else:
                s["n_gold_mismatch_majority"] += 1
                if len(examples_mismatch) < max_examples:
                    examples_mismatch.append({"gold": gold, "majority": maj, "annotators": ann})
    out = dict(s)
    out["agreement_hist"] = {str(k): v for k, v in sorted(agreement_hist.items())}
    out["examples_mismatch"] = examples_mismatch
    out["examples_consensus_with_majority"] = examples_consensus_with_majority
    return out


def flatten(stats):
    """Integer census keys only (drops hist and examples) for comparison against a frozen TARGET."""
    return {k: stats[k] for k in _FLAT_KEYS}
