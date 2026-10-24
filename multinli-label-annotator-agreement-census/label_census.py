"""Does NLI annotator agreement depend on the gold label class (entailment / neutral / contradiction)?

Part of MV2's eval-reliability-audits catalogue (Munim, Inc.). This research is carried out by
AI agents working in MV2's name.

This is the dataset-agnostic per-gold-class agreement module first used for SNLI (audit 42). It operates
on already-parsed {gold, annotators} records, so it is file-free and fully unit-testable, and is reused
here unchanged for MultiNLI's validated dev sets. For each valid-gold row we bucket by the normalised gold
(e / n / c) and tally, per class: n (rows with that gold), unanimous (all five annotators chose the gold),
the total individual annotator labels and how many equal the gold (the paper's "Agrmt" statistic), and a
by-construction check that the gold equals the strict majority of the five labels. Rows whose gold is "-"
(no majority) are counted separately. Apache-2.0.
"""
from collections import Counter

LABELS = ("e", "n", "c")
_PER_KEYS = ("n", "unanimous", "labels_total", "labels_agree", "gold_eq_majority")
_TOTAL_KEYS = ("n_total", "n_dash", "n_valid")


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


def strict_majority_of_labels(labels):
    """Label held by strictly more than half of ``labels`` (already normalised); else None."""
    total = len(labels)
    if total <= 0:
        return None
    for lab, cnt in Counter(labels).items():
        if cnt * 2 > total:
            return lab
    return None


def agreement_count(annotator_labels, gold):
    """How many of the annotator labels equal the (normalised) gold."""
    g = norm_label(gold)
    if g is None:
        return None
    return sum(1 for a in (annotator_labels or []) if norm_label(a) == g)


def _empty_cell():
    return {k: 0 for k in _PER_KEYS}


def census(records):
    """Per-gold-label agreement census.

    Each record: ``gold`` (raw gold_label) and ``annotators`` (list of raw annotator labels). Returns
    per-class counts plus overall totals. ``unanimous`` means all five annotators chose the gold.
    """
    per = {L: _empty_cell() for L in LABELS}
    totals = {k: 0 for k in _TOTAL_KEYS}
    for r in records:
        totals["n_total"] += 1
        g = norm_label(r.get("gold"))
        annot = r.get("annotators") or []
        valid = [norm_label(a) for a in annot]
        valid = [a for a in valid if a is not None]
        if g is None:
            totals["n_dash"] += 1
            continue
        totals["n_valid"] += 1
        cell = per[g]
        cell["n"] += 1
        n_agree = sum(1 for a in valid if a == g)
        cell["labels_total"] += len(valid)
        cell["labels_agree"] += n_agree
        if n_agree == 5:
            cell["unanimous"] += 1
        if strict_majority_of_labels(valid) == g:
            cell["gold_eq_majority"] += 1
    return {"per_label": per, "totals": totals}


def flatten(stats):
    """Flatten the census into a single integer dict for comparison against a frozen TARGET."""
    out = {}
    for k in _TOTAL_KEYS:
        out[k] = stats["totals"][k]
    for L in LABELS:
        for k in _PER_KEYS:
            out["%s_%s" % (L, k)] = stats["per_label"][L][k]
    return out


def unanimous_rate(stats, label):
    """Share of a class's valid-gold rows on which all five annotators agreed (0.0 if empty)."""
    c = stats["per_label"][label]
    return (c["unanimous"] / c["n"]) if c["n"] else 0.0


def individual_agreement_rate(stats, label):
    """Share of a class's individual annotator labels that equal the gold (0.0 if empty)."""
    c = stats["per_label"][label]
    return (c["labels_agree"] / c["labels_total"]) if c["labels_total"] else 0.0


def aggregate_individual_agreement(stats):
    """Overall individual-agreement rate across all classes (the paper's 'Agrmt')."""
    agree = sum(stats["per_label"][L]["labels_agree"] for L in LABELS)
    total = sum(stats["per_label"][L]["labels_total"] for L in LABELS)
    return (agree / total) if total else 0.0
