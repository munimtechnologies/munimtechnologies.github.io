"""Audit 108 helpers: does HELM Finance's FinanceBench prompt leave out evidence its questions need?

HELM's FinanceBenchScenario (src/helm/benchmark/scenarios/financebench_scenario.py, Stanford CRFM, Apache-2.0) builds
each prompt as "Evidence: <evidence[0].evidence_text_full_page>\nQuestion: <question>": only the FIRST evidence item's
page goes into the prompt. Many FinanceBench questions cite two or three pages (for example a capital-intensity
question that needs the income statement, the balance sheet and the cash-flow statement). A GPT-4o judge then labels
each answer correct_answer, incorrect_answer or failure_to_answer against the gold answer, and the leaderboard column
"Correct Answer" is the share labelled correct_answer.

This module holds the stdlib-only parts of the audit: the evidence classes, the prompt check, the run census, run
means, ranks, Kendall tau-b, the group-page column and the verdicts. Apache-2.0.
"""

import hashlib
import math
from fractions import Fraction

ANN = "financebench"
LABELS = ("correct_answer", "incorrect_answer", "failure_to_answer")
STAT_CORRECT = "annotation_financebench_label_correct_answer"
STAT_NAMES = {lab: "annotation_financebench_label_" + lab for lab in LABELS}
CELL_HEADER = "Correct Answer"
COMPLETE = ("single", "covered")
CLASSES = ("single", "covered", "missing", "unverifiable", "no_evidence")


# ---------------- Evidence classes ----------------
def squash(text):
    """Text with every run of whitespace removed (PDF page text differs from snippets mainly in spacing)."""
    return "".join((text or "").split())


def snippet_in_own_page(ev):
    """Whether an evidence item's snippet is found (whitespace-insensitive) in its own full-page text."""
    s = squash((ev or {}).get("evidence_text"))
    return bool(s) and s in squash((ev or {}).get("evidence_text_full_page"))


def doc_of(ev):
    """An evidence item's document name (the data file says doc_name; FinanceBench's README says evidence_doc_name)."""
    ev = ev or {}
    return ev.get("doc_name") if ev.get("doc_name") is not None else ev.get("evidence_doc_name")


def evidence_class(evidence):
    """Class of a FinanceBench record's evidence list, given that HELM puts only evidence[0]'s full page in the prompt.

    single: one evidence item. For each later item: skipped if it is on the same page as item 0 (same doc_name and
    page number, or the same squashed page text) or if its snippet is found in item 0's page ('covered'); otherwise it
    is 'missing' when its snippet is found in its own page, else 'unverifiable'. A record is 'missing' if any item is,
    else 'unverifiable' if any item is, else 'covered'. Returns (class, info)."""
    ev = [e for e in (evidence or []) if isinstance(e, dict)]
    if not ev:
        return "no_evidence", {"n": 0, "other_pages": 0, "missing": [], "unverifiable": []}
    given = squash(ev[0].get("evidence_text_full_page"))
    missing, unver, other = [], [], 0
    for k in range(1, len(ev)):
        e = ev[k]
        same = ((doc_of(e) == doc_of(ev[0])
                 and e.get("evidence_page_num") == ev[0].get("evidence_page_num"))
                or squash(e.get("evidence_text_full_page")) == given)
        if same:
            continue
        other += 1
        snip = squash(e.get("evidence_text"))
        if snip and snip in given:
            continue
        if snippet_in_own_page(e):
            missing.append(k)
        else:
            unver.append(k)
    if len(ev) == 1:
        cls = "single"
    elif missing:
        cls = "missing"
    elif unver:
        cls = "unverifiable"
    else:
        cls = "covered"
    return cls, {"n": len(ev), "other_pages": other, "missing": missing, "unverifiable": unver}


def prompt_matches(input_text, record):
    """Whether a HELM instance's input text is exactly what FinanceBenchScenario builds from this record."""
    ev = [e for e in (record.get("evidence") or []) if isinstance(e, dict)]
    if not ev:
        return False
    return input_text == "Evidence: %s\nQuestion: %s" % (ev[0].get("evidence_text_full_page"), record.get("question"))


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


def label_of(record):
    ann = (record.get("annotations") or {}).get(ANN) or {}
    return ann.get("label") if isinstance(ann, dict) else None


def summarize_run(preds, test_ids):
    """Census of one run's display_predictions (unperturbed, test ids only, first record per (instance, trial)).

    labels: {instance id: label} (trial 0 only); trials: {t: {n, <label>: count}}; label_bad: label not one of the
    three; stored_missing / stored_mismatch: the per-record stored correct_answer stat absent / not equal to ours."""
    counts = {"n_records": 0, "perturbed": 0, "not_test": 0, "duplicate": 0, "kept": 0}
    tally = {"label_bad": 0, "stored_missing": 0, "stored_mismatch": 0}
    trials, labels, seen = {}, {}, set()
    for r in preds or []:
        if not isinstance(r, dict):
            continue
        counts["n_records"] += 1
        if r.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        iid, t = r.get("instance_id"), r.get("train_trial_index", 0)
        if iid not in test_ids:
            counts["not_test"] += 1
            continue
        if (iid, t) in seen:
            counts["duplicate"] += 1
            continue
        seen.add((iid, t))
        counts["kept"] += 1
        lab = label_of(r)
        acc = trials.setdefault(t, dict({"n": 0}, **{k: 0 for k in LABELS}))
        acc["n"] += 1
        if lab in LABELS:
            acc[lab] += 1
        else:
            tally["label_bad"] += 1
        if t == 0:
            labels[iid] = lab
        stored = (r.get("stats") or {}).get(STAT_CORRECT)
        if not is_number(stored):
            tally["stored_missing"] += 1
        elif int(round(stored)) != (1 if lab == "correct_answer" else 0):
            tally["stored_mismatch"] += 1
    return dict({"counts": counts, "trials": trials, "labels": labels}, **tally)


def run_mean(trials, key):
    """HELM's run-level mean: the mean over trials of each trial's mean (exact Fraction; None without trials)."""
    ms = [Fraction(v[key], v["n"]) for _, v in sorted(trials.items()) if v["n"]]
    return sum(ms, Fraction(0)) / len(ms) if ms else None


def by_class(labels, cls_of):
    """{class: {n, <label>: count}} over the instances of one run (instances without a class are skipped)."""
    out = {}
    for iid, lab in labels.items():
        c = cls_of.get(iid)
        if c is None:
            continue
        acc = out.setdefault(c, dict({"n": 0}, **{k: 0 for k in LABELS}))
        acc["n"] += 1
        if lab in LABELS:
            acc[lab] += 1
    return out


def merge(tallies, classes):
    """Sum {n, labels} over several by_class() results, restricted to `classes`."""
    acc = dict({"n": 0}, **{k: 0 for k in LABELS})
    for t in tallies:
        for c in classes:
            v = t.get(c)
            if v:
                for k in acc:
                    acc[k] += v[k]
    return acc


def share(t, label):
    return Fraction(t[label], t["n"]) if t and t.get("n") else None


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
MIN_SUBSET = 10


def verdicts(s):
    """The eight pre-registered predictions (True = HELD, False = FAILED, None = NOT GRADED) from pooled stats `s`."""
    inc = s["runs_included"]
    nt = s["test_ids"]
    m, c = s["pooled_missing"], s["pooled_complete"]
    p3 = (m["n"] > 0 and c["n"] > 0 and m["failure_to_answer"] > 0
          and m["failure_to_answer"] * c["n"] >= 2 * c["failure_to_answer"] * m["n"])
    mm, mc = s["metrics_missing"], s["metrics_complete"]
    if s["metrics_missing_q"] >= MIN_SUBSET and s["metrics_complete_q"] >= MIN_SUBSET and mm["n"] and mc["n"]:
        p5 = share(mc, "correct_answer") - share(mm, "correct_answer") >= Fraction(1, 10)
    else:
        p5 = None
    return {
        "P1": (nt == 140 and s["test_ids_found"] == nt and s["prompt_ok_min"] is not None
               and s["prompt_ok_min"] >= Fraction(95, 100) and s["own_page_share"] is not None
               and s["own_page_share"] >= Fraction(9, 10) and s["runs_listed"] >= 22 and inc >= 20
               and s["cells_matched"] * 10 >= 9 * inc),
        "P2": nt > 0 and s["missing"] * 5 >= nt,
        "P3": p3,
        "P4": inc > 0 and s["runs_lower"] * 5 >= 4 * inc,
        "P5": p5,
        "P6": s["tau"] is not None and s["tau"] >= 0.8,
        "P7": s["movers"] >= 1,
        "P8": bool(s["leader_ok"]),
    }


def verdict_word(v):
    return "NOT GRADED" if v is None else ("HELD" if v else "FAILED")
