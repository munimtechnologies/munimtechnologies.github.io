"""Audit 112 helpers: how MedHELM's MEDEC scorer reads gold sentence ids and model answers.

HELM's MedecMetric (src/helm/benchmark/metrics/medec_metrics.py, Stanford CRFM, Apache-2.0) builds the gold from the
reference text, which MedecScenario writes as "<sentence id> <corrected sentence>" (or "CORRECT"). It removes every '.'
and then calls int() on the WHOLE text, so for every note with an error int("7 The patient ...") raises ValueError and
the gold sentence id becomes -1; a predicted id can never equal -1, so medec_error_sentence_accuracy can only credit
notes without an error. On the prediction side, only the exact string "CORRECT" (after strip) means "no error"; any
answer that neither equals "CORRECT" nor starts with a digit ("CORRECT.", "**7**", an empty answer, prose) is read as
"there is an error" with an invalid id, so it earns flag credit on every note that has an error.

This module holds the stdlib-only parts of the audit: HELM's parsing and scoring (transcribed), the fixed gold id, the
answer classes, the lenient reading, the run census, run means, ranks, Kendall tau-b, the group-page column and the
verdicts. Apache-2.0.
"""

import hashlib
import math
import re
import sys
from fractions import Fraction

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)  # answers may start with very long digit strings

FLAG = "medec_error_flag_accuracy"
SENT = "medec_error_sentence_accuracy"
CELL_HEADER = "MedecFlagAcc"
N_TEST = 597
CLASSES = ("exact", "digit", "correct_variant", "id_variant", "empty", "other")
INVALID = ("correct_variant", "id_variant", "empty", "other")  # HELM: flag 1, id -2
VARIANTS = ("pub_flag", "pub_sent", "fixed_sent", "noinv_flag", "noinv_sent", "len_flag", "len_sent")

LEAD_DIGITS = re.compile(r"^(\d+)")
CORRECT_START = re.compile(r"[\s*_`\"'#>]*correct\b", re.I)
ANY_DIGIT = re.compile(r"\d")
ID_LINE = re.compile(r"[\s*_`\"'#>(\[]*(?:sentence\s*(?:id)?|id)?\s*[:#]?\s*[*_`\"'(\[]*(\d+)\b", re.I)


# ---------------- HELM's scorer (transcribed from MedecMetric.evaluate_generation) ----------------
def gold_flag_id(ref_text):
    """HELM's ground truth, bug kept: drop '.', strip; 'CORRECT' -> (0, -1); else (1, int(text)) or (1, -1)."""
    gt = (ref_text or "").replace(".", "").strip()
    if gt == "CORRECT":
        return 0, -1
    try:
        return 1, int(gt)
    except ValueError:
        return 1, -1


def helm_pred(pred):
    """HELM's reading of an answer: exact 'CORRECT' -> (0, -1); leading digits -> (1, id); else (1, -2)."""
    p = (pred or "").strip()
    if p == "CORRECT":
        return 0, -1
    m = LEAD_DIGITS.match(p)
    if m:
        return 1, int(m.group(1))
    return 1, -2


def score(gold, pred):
    """(flag accuracy, sentence accuracy) as HELM computes them; a prediction flag of None (no answer) scores (0, 0)."""
    gf, gid = gold
    pf, pid = pred
    if pf is None:
        return 0, 0
    flag = 1 if pf == gf else 0
    if gf == 1 and pf == 1:
        sent = 1 if pid == gid else 0
    else:
        sent = 1 if (gf == 0 and pf == 0) else 0
    return flag, sent


# ---------------- Fixed gold, answer classes, lenient reading ----------------
def gold_fixed_id(ref_text):
    """The gold as the scenario writes it: 'CORRECT' -> (0, -1); else (1, the leading sentence id) or (1, -1)."""
    gt = (ref_text or "").replace(".", "").strip()
    if gt == "CORRECT":
        return 0, -1
    m = LEAD_DIGITS.match(gt)
    return 1, (int(m.group(1)) if m else -1)


def classify(pred):
    """(class, id). exact: 'CORRECT' after strip; digit: starts with a digit (HELM reads its id); for all others
    HELM's id is -2. correct_variant: the first non-empty line starts (after markdown or quote marks) with the word
    'correct' in any case and holds no digit ('CORRECT.', '**Correct**'); id_variant: the first non-empty line starts
    with a sentence id behind markdown or a label ('**7**', 'Sentence 7:', 'ID: 7'); empty; other."""
    p = (pred or "").strip()
    if p == "CORRECT":
        return "exact", None
    m = LEAD_DIGITS.match(p)
    if m:
        return "digit", int(m.group(1))
    if not p:
        return "empty", None
    first = next(line for line in p.splitlines() if line.strip())
    if CORRECT_START.match(first) and not ANY_DIGIT.search(first):
        return "correct_variant", None
    m = ID_LINE.match(first)
    if m:
        return "id_variant", int(m.group(1))
    return "other", None


def lenient_pred(pred):
    """Our reading: exact or correct_variant -> (0, -1); digit or id_variant -> (1, id); empty/other -> no answer."""
    c, i = classify(pred)
    if c in ("exact", "correct_variant"):
        return 0, -1
    if c in ("digit", "id_variant"):
        return 1, i
    return None, None


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
            return (ref.get("output") or {}).get("text")
    return None


def summarize_run(preds, refs):
    """Census of one run's display_predictions (unperturbed, test ids only, first record per (instance, trial)).

    refs: {test instance id: reference text}. trials: {t: {n, <VARIANTS>}} where pub_* sum the stored stats and the
    others our re-scores (fixed gold id throughout): fixed_sent = HELM's answer reading; noinv_* = HELM's reading but an
    answer HELM marks invalid (id -2) counts as no answer; len_* = lenient_pred. stored_missing counts absent stored
    values (two per record when both are absent); flag_mismatch / sent_mismatch: stored value != our transcription of
    HELM. tn: notes without an error that HELM reads as answered 'CORRECT'; err_sent_credit: notes with an error whose
    stored sentence accuracy is above 0; invalid_flag_credit: answers HELM marks invalid that still earn flag credit."""
    counts = {"n_records": 0, "perturbed": 0, "not_test": 0, "duplicate": 0, "kept": 0}
    tally = {"stored_missing": 0, "flag_mismatch": 0, "sent_mismatch": 0, "error_notes": 0, "err_sent_credit": 0,
             "tn": 0, "invalid_flag_credit": 0}
    trials, classes, texts, golds, seen = {}, {}, {}, {}, set()
    for r in preds or []:
        if not isinstance(r, dict):
            continue
        counts["n_records"] += 1
        if r.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        iid, t = r.get("instance_id"), r.get("train_trial_index", 0)
        if iid not in refs:
            counts["not_test"] += 1
            continue
        if (iid, t) in seen:
            counts["duplicate"] += 1
            continue
        seen.add((iid, t))
        counts["kept"] += 1
        pred = r.get("predicted_text") or ""
        ref = refs[iid] or ""
        hp = helm_pred(pred)
        hf, hs = score(gold_flag_id(ref), hp)
        st = r.get("stats") or {}
        stored = {}
        for key, ours, mis in ((FLAG, hf, "flag_mismatch"), (SENT, hs, "sent_mismatch")):
            v = st.get(key)
            if not is_number(v):
                tally["stored_missing"] += 1
                stored[key] = 0
            else:
                stored[key] = v
                if abs(v - ours) > 1e-9:
                    tally[mis] += 1
        gfix = gold_fixed_id(ref)
        _, fs = score(gfix, hp)
        nf, ns = score(gfix, (None, None) if hp[1] == -2 else hp)
        lf, ls = score(gfix, lenient_pred(pred))
        if gfix[0] == 1:
            tally["error_notes"] += 1
            if stored[SENT] > 0:
                tally["err_sent_credit"] += 1
        elif hp[0] == 0:
            tally["tn"] += 1
        if hp[1] == -2 and hf == 1:
            tally["invalid_flag_credit"] += 1
        acc = trials.setdefault(t, dict({"n": 0}, **{k: Fraction(0) for k in VARIANTS}))
        acc["n"] += 1
        acc["pub_flag"] += Fraction(stored[FLAG]).limit_denominator(10 ** 6)
        acc["pub_sent"] += Fraction(stored[SENT]).limit_denominator(10 ** 6)
        acc["fixed_sent"] += fs
        acc["noinv_flag"] += nf
        acc["noinv_sent"] += ns
        acc["len_flag"] += lf
        acc["len_sent"] += ls
        if t == 0:
            classes[iid] = classify(pred)[0]
            texts[iid] = pred[:200]
            golds[iid] = gfix
    return dict({"counts": counts, "trials": trials, "classes": classes, "texts": texts, "golds": golds}, **tally)


def run_mean(trials, key):
    """HELM's run-level mean: the mean over trials of each trial's mean (exact Fraction; None without trials)."""
    ms = [Fraction(v[key]) / v["n"] for _, v in sorted(trials.items()) if v["n"]]
    return sum(ms, Fraction(0)) / len(ms) if ms else None


def class_counts(classes):
    out = {c: 0 for c in CLASSES}
    for c in classes.values():
        out[c] = out.get(c, 0) + 1
    return out


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
        "P1": (s["test_ids"] == N_TEST and s["runs_listed"] >= 13 and inc >= 12
               and s["cells_matched"] * 10 >= 9 * inc),
        "P2": s["sent_rise10"] >= 8,
        "P3": s["max_fixed_sent"] is not None and s["max_fixed_sent"] >= Fraction(2, 5),
        "P4": s["pooled_n"] > 0 and s["pooled_invalid"] * 20 >= s["pooled_n"],
        "P5": s["runs_invalid20"] >= 1,
        "P6": s["max_noinv_drop"] is not None and s["max_noinv_drop"] >= Fraction(1, 20),
        "P7": s["movers_len"] >= 1,
        "P8": bool(s["leader_ok_len"]),
    }


def verdict_word(v):
    return "NOT GRADED" if v is None else ("HELD" if v else "FAILED")
