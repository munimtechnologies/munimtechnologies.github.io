"""Audit 100 helpers: does HELM Classic's Dyck column score the whole closing sequence, or only its last bracket?

HELM's Dyck scenario (dyck_language_scenario.py) asks a model to write the closing brackets that complete a Dyck-3
prefix; the gold is 1 to 3 closers joined by single spaces (with a leading space), e.g. " ) ] }". The run spec scores
it with exact_match_indicator (classic_run_specs.py), and HELM's exact_match_indicator
(src/helm/benchmark/metrics/evaluate_reference_metrics.py) keeps only the text after the LAST occurrence of its
indicator, whose default is a single space, in both gold and prediction. So for " ) ] }" only "}" is compared, and a
prediction such as "] ) }" or "}" scores 1. The HELM paper (arXiv 2211.09110) says Dyck reports strict exact match.

This module transcribes exact_match and exact_match_indicator, adds a strict grade (the whole closing sequence,
ignoring whitespace) and a lenient grade (the prediction's bracket characters equal the gold's sequence, so other
text around a right answer is forgiven), classes every indicator credit that is not strict, and provides census,
cell, rank, tau and verdict helpers. Apache-2.0 (exact_match and exact_match_indicator are transcribed from
stanford-crfm/helm, Apache-2.0).
"""

import hashlib
import math
from fractions import Fraction

STAT = "exact_match_indicator"
BRACKETS = set("()[]{}<>")
WRONG_CLASSES = ("missing_leading", "extra_leading", "wrong_same_length", "other")
CLASSES = ("format_only",) + WRONG_CLASSES


# ---------------- HELM transcriptions ----------------
def exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if gold.strip() == pred.strip() else 0


def exact_match_indicator(gold, pred, indicator=" "):
    """HELM: exact match of the text after the last indicator (default: a single space) in gold and prediction."""
    pred = pred.split(indicator)[-1].strip()
    gold = gold.split(indicator)[-1].strip()
    return exact_match(gold, pred)


# ---------------- Our grades ----------------
def seq(text):
    """The text with all whitespace removed."""
    return "".join((text or "").split())


def brackets(text):
    """The bracket characters of a text, in order."""
    return "".join(ch for ch in (text or "") if ch in BRACKETS)


def strict_match(gold, pred):
    """1 when the prediction is the gold's whole closing sequence (whitespace ignored)."""
    if not pred:
        return 0
    return 1 if seq(gold) == seq(pred) else 0


def lenient_match(gold, pred):
    """1 when the prediction's bracket characters are exactly the gold's closing sequence (other text ignored)."""
    if not pred:
        return 0
    return 1 if brackets(pred) == seq(gold) else 0


def depth(gold):
    """Number of closers in a gold."""
    return len(gold.split())


def credit_class(gold, pred):
    """Class of an indicator credit that is not a strict match: format_only (the right closers plus other text), or,
    by the prediction's bracket characters pb against the gold sequence g: missing_leading (pb is a proper suffix of
    g), extra_leading (g is a proper suffix of pb), wrong_same_length, other."""
    if lenient_match(gold, pred):
        return "format_only"
    g, pb = seq(gold), brackets(pred)
    if len(pb) < len(g) and g.endswith(pb):
        return "missing_leading"
    if len(pb) > len(g) and pb.endswith(g):
        return "extra_leading"
    if len(pb) == len(g):
        return "wrong_same_length"
    return "other"


def grade_record(golds, pred_text):
    """HELM strips the completion and keeps the max over correct references. Returns ind (HELM), strict, lenient (each a
    max over golds) and, for an indicator credit that is not strict, its class against the first gold it matches."""
    pred = (pred_text or "").strip()
    ind = max((exact_match_indicator(g, pred) for g in golds), default=0)
    strict = max((strict_match(g, pred) for g in golds), default=0)
    lenient = max((lenient_match(g, pred) for g in golds), default=0)
    cls = None
    if ind == 1 and strict == 0:
        first = next(g for g in golds if exact_match_indicator(g, pred))
        cls = credit_class(first, pred)
    return {"ind": ind, "strict": strict, "lenient": lenient, "cls": cls}


# ---------------- Run names and release ----------------
def model_of(run_name):
    """Text after 'model=' up to the next comma."""
    i = run_name.find("model=")
    return run_name[i + len("model="):].split(",")[0] if i >= 0 else ""


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
def summarize_run(instances, preds, cap):
    """Grade every test-split record of one run (all trials, unperturbed, first record per (instance, trial)).

    trials: {trial: {n, ind, strict, lenient}}; classes: counts of non-strict indicator credits by class; keys: the
    (instance id, trial) of each class and of 'under' (lenient but not credited by HELM); by_depth: {closers: {records,
    ind, strict, lenient, wrong}}; cap_records / cap_wrong: records, and wrong credits, whose stored
    num_output_tokens reached the run's max_tokens `cap`.
    """
    gold = {}
    for inst in instances or []:
        if isinstance(inst, dict) and inst.get("split") == "test":
            gold[inst.get("id")] = [((r.get("output") or {}).get("text") or "")
                                    for r in inst.get("references") or []
                                    if isinstance(r, dict) and "correct" in (r.get("tags") or [])]
    counts = {"n_records": 0, "perturbed": 0, "not_test": 0, "duplicate": 0, "kept": 0}
    trials, seen = {}, set()
    classes = {c: 0 for c in CLASSES}
    keys = {c: [] for c in CLASSES + ("under",)}
    by_depth = {}
    stat_missing = stat_mismatch = under = cap_records = cap_wrong = 0
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
        acc = trials.setdefault(t, {"n": 0, "ind": 0, "strict": 0, "lenient": 0})
        acc["n"] += 1
        for k in ("ind", "strict", "lenient"):
            acc[k] += gr[k]
        st = r.get("stats") or {}
        stored = st.get(STAT)
        if not is_number(stored):
            stat_missing += 1
        elif int(round(stored)) != gr["ind"]:
            stat_mismatch += 1
        wrong = gr["ind"] == 1 and gr["lenient"] == 0
        nout = st.get("num_output_tokens")
        at_cap = is_number(nout) and nout >= cap
        if at_cap:
            cap_records += 1
            if wrong:
                cap_wrong += 1
        d = depth(gold[iid][0]) if gold[iid] else 0
        bd = by_depth.setdefault(d, {"records": 0, "ind": 0, "strict": 0, "lenient": 0, "wrong": 0})
        bd["records"] += 1
        for k in ("ind", "strict", "lenient"):
            bd[k] += gr[k]
        bd["wrong"] += 1 if wrong else 0
        if gr["cls"] is not None:
            classes[gr["cls"]] += 1
            keys[gr["cls"]].append((iid, t))
        if gr["lenient"] == 1 and gr["ind"] == 0:
            under += 1
            keys["under"].append((iid, t))
    return {"counts": counts, "trials": trials, "stat_missing": stat_missing, "stat_mismatch": stat_mismatch,
            "classes": classes, "keys": keys, "by_depth": by_depth, "under": under, "cap_records": cap_records,
            "cap_wrong": cap_wrong}


def run_mean(trials, key):
    """HELM's run-level mean: the mean over trials of each trial's mean (exact Fraction; None without trials)."""
    ms = [Fraction(v[key], v["n"]) for _, v in sorted(trials.items()) if v["n"]]
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


def stable_hash(text):
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def pick(lst, salt):
    """One element of a list of (instance id, trial) keys, chosen by a stable hash (None for an empty list)."""
    if not lst:
        return None
    return min(lst, key=lambda k: (stable_hash("%s|%s|%s" % (salt, k[0], k[1])), str(k)))


# ---------------- Verdicts ----------------
def verdicts(s):
    """The seven pre-registered predictions (True = HELD) from the job's pooled statistics `s`."""
    bd = s.get("by_depth") or {}
    d2, d3 = bd.get(2) or {}, bd.get(3) or {}
    p3 = bool(d2.get("ind")) and bool(d3.get("ind")) and (
        Fraction(d3.get("wrong", 0), d3["ind"]) > Fraction(d2.get("wrong", 0), d2["ind"]))
    return {
        "P1": bool(s["fixtures"]) and s["runs_listed"] >= 60 and s["runs_included"] * 10 >= 9 * s["runs_listed"]
        and s["runs_included"] > 0 and s["cells_matched"] * 10 >= 9 * s["runs_included"],
        "P2": s["ind_credits"] > 0 and Fraction(s["wrong"], s["ind_credits"]) >= Fraction(1, 20),
        "P3": p3,
        "P4": s["max_fall"] is not None and s["max_fall"] >= Fraction(1, 20),
        "P5": s["movers"] >= 5,
        "P6": s["tau"] is not None and s["tau"] >= 0.8,
        "P7": s["wrong"] > 0 and s["missing_leading"] * 2 < s["wrong"],
    }
