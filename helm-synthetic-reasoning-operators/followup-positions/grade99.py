"""Audit 99 helpers: does HELM Classic's "Synthetic reasoning (abstract symbols)" column credit answers whose
operators are wrong?

The column's main metric is quasi_exact_match (HELM's schema_classic.yaml). HELM's quasi_exact_match compares
normalize_text(gold) with normalize_text(pred), and normalize_text (src/helm/benchmark/metrics/
evaluate_reference_metrics.py, copied from the QuAC scorer) lower-cases, removes every character in
string.punctuation, removes the articles a/an/the and collapses whitespace. The answers in this scenario are patterns
built from the variables X, Y, Z (or fruit and animal words) and the operators + - * =, and every operator is in
string.punctuation. So "X + Y = Y" and "X = Y + Y" normalise to the same "x y y" and score 1.

This module transcribes HELM's exact_match and quasi_exact_match, adds an operator-aware grade (quasi-exact match
AND the same sequence of operator characters), and provides census, cell, rank and verdict helpers. Apache-2.0
(normalize_text, exact_match and quasi_exact_match are transcribed from stanford-crfm/helm, Apache-2.0).

Copied from ../ (audit 99) so the follow-up folder runs on its own; every function is unchanged, and only
predictions99 (audit 99's verdicts, not used here) is left out.
"""

import math
import re
import string
from fractions import Fraction

OPS = "+-*="
PUNCT = set(string.punctuation)
STAT_QEM = "quasi_exact_match"
STAT_EM = "exact_match"
BLIND_CLASSES = ("ops_missing", "ops_reordered", "ops_other")


# ---------------- HELM transcriptions ----------------
def normalize_text(text, should_remove_articles=True):
    """HELM's normalize_text: lower, drop string.punctuation, drop articles, collapse whitespace."""

    def remove_articles(t):
        return re.sub(r"\b(a|an|the)\b", " ", t)

    def white_space_fix(t):
        return " ".join(t.split())

    def remove_punc(t):
        return "".join(ch for ch in t if ch not in PUNCT)

    normalized = remove_punc(text.lower())
    if should_remove_articles:
        normalized = remove_articles(normalized)
    return white_space_fix(normalized)


def exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if gold.strip() == pred.strip() else 0


def quasi_exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if normalize_text(gold) == normalize_text(pred) else 0


# ---------------- Our grade ----------------
def ops_of(text):
    """The operator characters of a text, in order."""
    return "".join(ch for ch in text if ch in OPS)


def operator_aware(gold, pred):
    """1 when HELM's quasi-exact match holds AND the prediction has the gold's operator sequence."""
    return 1 if quasi_exact_match(gold, pred) and ops_of(gold) == ops_of(pred) else 0


def blind_class(gold, pred):
    """Why a quasi-exact credit is not operator-aware: the prediction has no operators, the same operators in another
    order, or other operators."""
    po, go = ops_of(pred), ops_of(gold)
    if not po:
        return "ops_missing"
    if sorted(po) == sorted(go):
        return "ops_reordered"
    return "ops_other"


def grade_record(golds, pred_text):
    """HELM scores the stripped completion against every correct reference and keeps the max. Returns em, qem, oa
    (each a max over golds) and, for a quasi-exact credit that is not operator-aware, its class against the first gold
    that quasi-matches."""
    pred = (pred_text or "").strip()
    em = max((exact_match(g, pred) for g in golds), default=0)
    qem = max((quasi_exact_match(g, pred) for g in golds), default=0)
    oa = max((operator_aware(g, pred) for g in golds), default=0)
    cls = None
    if qem == 1 and oa == 0:
        first = next(g for g in golds if quasi_exact_match(g, pred))
        cls = blind_class(first, pred)
    return {"em": em, "qem": qem, "oa": oa, "cls": cls}


# ---------------- Run names and release ----------------
def model_of(run_name):
    """Text after 'model=' up to the next comma."""
    i = run_name.find("model=")
    return run_name[i + len("model="):].split(",")[0] if i >= 0 else ""


def mode_of(run_name):
    i = run_name.find("mode=")
    return run_name[i + len("mode="):].split(",")[0] if i >= 0 else ""


def select_runs(run_suites, prefix):
    return {r: s for r, s in (run_suites or {}).items() if r.startswith(prefix)}


def stat_entry(stats, name, split="test"):
    """{count, sum, mean} of the unperturbed stat `name` on `split` in a HELM stats.json list (None when absent)."""
    for s in stats or []:
        if not isinstance(s, dict):
            continue
        nm = s.get("name") or {}
        if (nm.get("name") == name and nm.get("split") == split and nm.get("perturbation") is None
                and nm.get("sub_split") is None):
            return {"count": s.get("count"), "sum": s.get("sum"), "mean": s.get("mean")}
    return None


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v))


# ---------------- Run census ----------------
def summarize_run(instances, preds):
    """Grade every test-split record of one run (all trials, unperturbed, first record per (instance, trial)).

    trials: {trial: {n, em, qem, oa}}; stat_missing / stat_mismatch: records whose stored quasi_exact_match is absent
    or differs from our transcription; blind: [(instance id, trial, class)] for quasi-exact credits that are not
    operator-aware; other_norm: quasi-exact credits that are operator-aware but not exact (case, spacing, other
    punctuation); qem_not_em: quasi-exact credits that are not exact.
    """
    gold = {}
    for inst in instances or []:
        if isinstance(inst, dict) and inst.get("split") == "test":
            gold[inst.get("id")] = [((r.get("output") or {}).get("text") or "")
                                    for r in inst.get("references") or []
                                    if isinstance(r, dict) and "correct" in (r.get("tags") or [])]
    counts = {"n_records": 0, "perturbed": 0, "not_test": 0, "duplicate": 0, "kept": 0}
    trials, seen, blind, other_norm = {}, set(), [], []
    stat_missing = stat_mismatch = qem_not_em = 0
    classes = {c: 0 for c in BLIND_CLASSES}
    for r in preds or []:
        if not isinstance(r, dict):
            continue
        counts["n_records"] += 1
        if r.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        iid, t = r.get("instance_id"), r.get("train_trial_index", 0)
        if iid not in gold:
            counts["not_test"] += 1
            continue
        if (iid, t) in seen:
            counts["duplicate"] += 1
            continue
        seen.add((iid, t))
        counts["kept"] += 1
        gr = grade_record(gold[iid], r.get("predicted_text"))
        acc = trials.setdefault(t, {"n": 0, "em": 0, "qem": 0, "oa": 0})
        acc["n"] += 1
        for k in ("em", "qem", "oa"):
            acc[k] += gr[k]
        stored = (r.get("stats") or {}).get(STAT_QEM)
        if not is_number(stored):
            stat_missing += 1
        elif int(round(stored)) != gr["qem"]:
            stat_mismatch += 1
        if gr["qem"] == 1 and gr["em"] == 0:
            qem_not_em += 1
        if gr["cls"] is not None:
            blind.append((iid, t, gr["cls"]))
            classes[gr["cls"]] += 1
        elif gr["qem"] == 1 and gr["em"] == 0:
            other_norm.append((iid, t))
    return {"counts": counts, "trials": trials, "stat_missing": stat_missing, "stat_mismatch": stat_mismatch,
            "blind": blind, "classes": classes, "other_norm": other_norm, "qem_not_em": qem_not_em}


def run_mean(trials, key):
    """HELM's run-level mean: the mean over trials of each trial's mean (exact Fraction; None without trials)."""
    ms = [Fraction(v[key], v["n"]) for _, v in sorted(trials.items()) if v["n"]]
    return sum(ms, Fraction(0)) / len(ms) if ms else None


def cell(trials_list, key):
    """A group-table cell: the mean of all trial-level means of the model's runs (HELM's 'sum=... (9)')."""
    ms = [Fraction(v[key], v["n"]) for tr in trials_list for _, v in sorted(tr.items()) if v["n"]]
    return sum(ms, Fraction(0)) / len(ms) if ms else None


def ranks_high(values):
    """Higher is better: rank = 1 + the number of entries strictly higher (exact values)."""
    return {k: 1 + sum(1 for w in values.values() if w > v) for k, v in values.items()}


def kendall_tau_b(xs, ys):
    """Kendall's tau-b of two equal-length sequences (None when either is constant or shorter than 2)."""
    n = len(xs)
    c = d = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = (xs[i] > xs[j]) - (xs[i] < xs[j])
            dy = (ys[i] > ys[j]) - (ys[i] < ys[j])
            if dx == 0:
                tx += 1
            if dy == 0:
                ty += 1
            if dx and dy:
                if dx == dy:
                    c += 1
                else:
                    d += 1
    n0 = n * (n - 1) // 2
    den = (n0 - tx) * (n0 - ty)
    return (c - d) / math.sqrt(den) if den > 0 else None


def group_em_values(group_doc):
    """Numeric values of the 'EM' column of a group page's first table (None when there is no such column)."""
    if not isinstance(group_doc, list) or not group_doc or not isinstance(group_doc[0], dict):
        return None
    t = group_doc[0]
    header = t.get("header") or []
    col = next((j for j, h in enumerate(header) if isinstance(h, dict) and h.get("value") == "EM"), None)
    if col is None:
        return None
    out = []
    for row in t.get("rows") or []:
        if isinstance(row, list) and len(row) > col and isinstance(row[col], dict) and is_number(row[col].get("value")):
            out.append(float(row[col]["value"]))
    return out


def match_cells(ours, published, tol):
    """How many of our cell values find a distinct published value within tol (greedy, both sorted)."""
    pub = sorted(published)
    used = [False] * len(pub)
    hit = 0
    for v in sorted(ours.values()):
        for j, p in enumerate(pub):
            if not used[j] and abs(p - v) <= tol:
                used[j] = True
                hit += 1
                break
    return hit
