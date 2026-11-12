"""Audit 109 helpers: does HELM Finance's BANKING77 scorer miss correct answers given as the label's list number?

HELM's banking77 run spec (src/helm/benchmark/run_specs/finance_run_specs.py, Stanford CRFM, Apache-2.0) uses RAFT's
banking_77 instructions, which end with "Possible labels:" and a NUMBERED list "1. Refund_not_showing_up" ... "77.
wrong_exchange_rate_for_cash_withdrawal". The main metric is quasi_exact_match against the label text only, so an
answer such as "71" (the number of the right label) or "verify source of funds" (the right label with spaces, which
normalize_text cannot join because it deletes the underscores) scores 0.

This module holds the stdlib-only parts of the audit: HELM's normalize_text / quasi_exact_match (copied), the label
list parser, the answer classes, the run census, run means, ranks, Kendall tau-b, the group-page column and the
verdicts. Apache-2.0.
"""

import hashlib
import math
import re
import string
from fractions import Fraction

MAIN = "quasi_exact_match"
CELL_HEADER = "EM"
N_LABELS = 77
CLASSES = ("match", "number_gold", "number_other", "numbered_gold", "spacing_gold", "contains_gold", "empty",
           "other")
MISREAD = ("number_gold", "numbered_gold", "spacing_gold")
LENIENT = ("match",) + MISREAD
LIST_HEAD = "Possible labels:\n"


# ---------------- HELM's scorer (copied from evaluate_reference_metrics.py) ----------------
def normalize_text(text, should_remove_articles=True):
    """HELM's normalize_text: lower, drop ASCII punctuation (incl. '_'), drop articles, collapse whitespace."""
    exclude = set(string.punctuation)
    t = "".join(ch for ch in text.lower() if ch not in exclude)
    if should_remove_articles:
        t = re.sub(r"\b(a|an|the)\b", " ", t)
    return " ".join(t.split())


def quasi_exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if normalize_text(gold) == normalize_text(pred) else 0


# ---------------- Label list and answer classes ----------------
ITEM = re.compile(r"^(\d+)\. (.+)$")
NUM_ONLY = re.compile(r"^#?(\d{1,3})[.):]?$")
NUM_LEAD = re.compile(r"^#?(\d{1,3})(?:[.):-] *| +)(\S.*)$")


def parse_labels(instructions):
    """{number: label} from the numbered list after 'Possible labels:' (None unless numbered 1..n without gaps)."""
    if not isinstance(instructions, str) or LIST_HEAD not in instructions:
        return None
    out = {}
    for line in instructions.split(LIST_HEAD, 1)[1].split("\n"):
        m = ITEM.match(line)
        if not m:
            if line.strip():
                return None
            continue
        n = int(m.group(1))
        if n in out:
            return None
        out[n] = m.group(2)
    if not out or sorted(out) != list(range(1, len(out) + 1)):
        return None
    return out


def alnum(text):
    """Lower-cased text with every non-alphanumeric character removed ('verify source of funds' -> 'verifysourceoffunds')."""
    return "".join(ch for ch in (text or "").lower() if ch.isalnum())


def same_label(a, b):
    return normalize_text(a) == normalize_text(b)


def classify(pred, gold, labels):
    """Class of one answer. match: HELM's quasi_exact_match is 1. Otherwise (all scored 0 by HELM):
    number_gold: the answer is only a list number (optionally '#', or a trailing '.', ')' or ':') and that number's label
    is the gold label; number_other: a list number for another label (or out of range); numbered_gold: a number then a
    label text, where the number's label is gold AND the text is gold (exactly or up to spacing/punctuation);
    spacing_gold: the gold label up to spacing and punctuation only (same letters and digits in the same order);
    contains_gold: the normalized gold label is one of the answer's normalized words (diagnostic only, not credited);
    empty: nothing after stripping; other: everything else."""
    p = (pred or "").strip()
    if quasi_exact_match(gold, p):
        return "match"
    if not p:
        return "empty"
    m = NUM_ONLY.match(p)
    if m:
        lab = labels.get(int(m.group(1)))
        return "number_gold" if lab is not None and same_label(lab, gold) else "number_other"
    m = NUM_LEAD.match(p)
    if m:
        lab = labels.get(int(m.group(1)))
        rest = m.group(2)
        if (lab is not None and same_label(lab, gold)
                and (same_label(rest, gold) or alnum(rest) == alnum(gold))):
            return "numbered_gold"
    if alnum(p) and alnum(p) == alnum(gold):
        return "spacing_gold"
    g = normalize_text(gold)
    if g and g in normalize_text(p).split():
        return "contains_gold"
    return "other"


# ---------------- Release, stats, census ----------------
def model_of(run_name):
    i = run_name.find("model=")
    return run_name[i + len("model="):].split(",")[0] if i >= 0 else ""


def select_runs(run_suites, prefix):
    return {r: s for r, s in (run_suites or {}).items() if r.startswith(prefix)}


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v))


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


def gold_of(instance):
    """Text of the first reference tagged 'correct' (None when there is none)."""
    for ref in (instance or {}).get("references") or []:
        if isinstance(ref, dict) and "correct" in (ref.get("tags") or []):
            return ((ref.get("output") or {}).get("text"))
    return None


def summarize_run(preds, gold, labels):
    """Census of one run's display_predictions (unperturbed, test ids only, first record per (instance, trial)).

    gold: {test instance id: gold label}. classes: {instance id: class} (trial 0); trials: {t: {n, published,
    lenient}} where published sums the stored quasi_exact_match and lenient counts LENIENT classes;
    stored_missing / recompute_mismatch: stored stat absent / not equal to our quasi_exact_match."""
    counts = {"n_records": 0, "perturbed": 0, "not_test": 0, "duplicate": 0, "kept": 0}
    tally = {"stored_missing": 0, "recompute_mismatch": 0}
    trials, classes, texts, seen = {}, {}, {}, set()
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
        pred = r.get("predicted_text") or ""
        ours = quasi_exact_match(gold[iid] or "", pred.strip())
        stored = (r.get("stats") or {}).get(MAIN)
        if not is_number(stored):
            tally["stored_missing"] += 1
            stored_v = 0
        else:
            stored_v = stored
            if int(round(stored)) != ours or abs(stored - ours) > 1e-9:
                tally["recompute_mismatch"] += 1
        c = classify(pred, gold[iid] or "", labels)
        acc = trials.setdefault(t, {"n": 0, "published": Fraction(0), "lenient": 0})
        acc["n"] += 1
        acc["published"] += Fraction(stored_v).limit_denominator(10 ** 6)
        acc["lenient"] += 1 if c in LENIENT else 0
        if t == 0:
            classes[iid] = c
            texts[iid] = pred[:120]
    return dict({"counts": counts, "trials": trials, "classes": classes, "texts": texts}, **tally)


def run_mean(trials, key):
    """HELM's run-level mean: the mean over trials of each trial's mean (exact Fraction; None without trials)."""
    ms = [Fraction(v[key]) / v["n"] for _, v in sorted(trials.items()) if v["n"]]
    return sum(ms, Fraction(0)) / len(ms) if ms else None


def class_counts(classes):
    out = {c: 0 for c in CLASSES}
    for c in classes.values():
        out[c] = out.get(c, 0) + 1
    return out


def labels_cover_gold(labels, golds):
    """Whether every gold label (normalized) is one of the listed labels (normalized)."""
    listed = {normalize_text(v) for v in (labels or {}).values()}
    return all(normalize_text(g or "") in listed for g in golds)


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


def group_values(doc, header_name=CELL_HEADER):
    """Numeric values of the column `header_name` in a HELM group page (list of tables or a single table)."""
    tables = doc if isinstance(doc, list) else [doc]
    for t in tables:
        if not isinstance(t, dict):
            continue
        header = t.get("header") or []
        col = next((j for j, h in enumerate(header) if isinstance(h, dict) and h.get("value") == header_name), None)
        if col is None:
            continue
        out = []
        for row in t.get("rows") or []:
            if (isinstance(row, list) and len(row) > col and isinstance(row[col], dict)
                    and is_number(row[col].get("value"))):
                out.append(float(row[col]["value"]))
        return out
    return None


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


# ---------------- Verdicts ----------------
def verdicts(s):
    """The eight pre-registered predictions (True = HELD, False = FAILED) from pooled stats `s`."""
    inc = s["runs_included"]
    return {
        "P1": (s["test_ids"] == 1000 and s["runs_listed"] >= 22 and inc >= 20 and s["lists_ok"]
               and s["cells_matched"] * 10 >= 9 * inc),
        "P2": bool(s["labels_cover_gold"]),
        "P3": s["runs_misread_2pct"] >= 3,
        "P4": s["pooled_n"] > 0 and s["pooled_misread"] * 200 >= s["pooled_n"],
        "P5": s["max_gain"] is not None and s["max_gain"] >= Fraction(5, 100),
        "P6": s["tau"] is not None and s["tau"] >= 0.8,
        "P7": s["movers"] >= 1,
        "P8": bool(s["leader_ok"]),
    }


def verdict_word(v):
    return "NOT GRADED" if v is None else ("HELD" if v else "FAILED")
