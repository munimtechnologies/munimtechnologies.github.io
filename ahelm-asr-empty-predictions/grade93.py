"""Audit 93 helpers: HELM's empty-prediction guard in its ASR error rates, the census arithmetic, ranks and verdicts.

HELM (stanford-crfm/helm, src/helm/benchmark/metrics/evaluate_reference_metrics.py) scores ASR with wer_score,
mer_score and cer_score (lower is better) and their chinese_* variants (jieba segmentation, then the same functions).
compute_reference_metrics strips the completion, and each function starts with `if not pred: return 0`, so an empty
or whitespace-only output gets the best possible error rate. jiwer itself returns 1.0 (every reference word deleted)
for an empty hypothesis, which is the value HELM issue #4359 and PR #4361 propose.

normalize_text is transcribed from HELM (Apache-2.0), which takes it from the QuAC scorer. Apache-2.0.
"""

import math
import re
import string
from fractions import Fraction

ERROR_METRICS = ("wer_score", "mer_score", "cer_score", "chinese_wer_score", "chinese_mer_score", "chinese_cer_score")
MAIN_METRICS = ("wer_score", "chinese_wer_score")
CORRECTED_EMPTY = 1.0  # jiwer's value for an empty hypothesis against a non-empty reference (all deletions)


def normalize_text(text, should_remove_articles=True):
    """HELM's normalize_text: lower-case, drop ASCII punctuation, (optionally) articles, collapse whitespace."""

    def remove_articles(t):
        return re.sub(r"\b(a|an|the)\b", " ", t)

    def white_space_fix(t):
        return " ".join(t.split())

    def remove_punc(t):
        exclude = set(string.punctuation)
        return "".join(ch for ch in t if ch not in exclude)

    normalized = remove_punc(text.lower())
    if should_remove_articles:
        normalized = remove_articles(normalized)
    return white_space_fix(normalized)


def pred_class(predicted_text):
    """'missing' (no text field), 'empty' (HELM's guard fires: the stripped output is empty), 'punct_only' (passes the
    guard but HELM's normalisation, articles kept as the ASR metrics call it, leaves nothing) or 'text'."""
    if predicted_text is None:
        return "missing"
    p = predicted_text.strip()
    if not p:
        return "empty"
    if not normalize_text(p, should_remove_articles=False):
        return "punct_only"
    return "text"


def model_of(run_name):
    """'librispeech:model=google_gemini-1.5-pro-001' -> 'google_gemini-1.5-pro-001' (text after the last 'model=')."""
    i = run_name.rfind("model=")
    return run_name[i + len("model="):] if i >= 0 else ""


def is_gemini(model):
    return "gemini" in model.lower()


def stat_mean(stats, name):
    """Mean of the unperturbed test-split stat `name` in a HELM stats.json list (None when absent)."""
    for s in stats or []:
        if not isinstance(s, dict):
            continue
        nm = s.get("name") or {}
        if (nm.get("name") == name and nm.get("split") == "test" and nm.get("perturbation") is None
                and nm.get("sub_split") is None):
            return s.get("mean")
    return None


def summarize_run(records):
    """Census of one run's display_predictions records (first trial, first record per instance id, unperturbed).

    Returns {"counts", "classes", "metrics", "empties", "punct"}: per error-rate stat m present in a record, n, the
    published sum, n_empty (HELM's guard fired), empty_nonzero (an empty output whose published value is not 0, which
    the guard says cannot happen), sum_empty, corrected_sum (empty outputs re-valued at 1.0), zeros (published 0) and
    zero_empty (published 0 from an empty output). empties/punct list (instance_id, {metric: published}) for the log.
    """
    counts = {"n_records": 0, "other_trial": 0, "duplicate": 0, "perturbed": 0, "kept": 0}
    classes = {"missing": 0, "empty": 0, "punct_only": 0, "text": 0}
    acc, empties, punct, seen = {}, [], [], set()
    for r in records or []:
        if not isinstance(r, dict):
            continue
        counts["n_records"] += 1
        if r.get("train_trial_index", 0) != 0:
            counts["other_trial"] += 1
            continue
        if r.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        iid = r.get("instance_id")
        if iid in seen:
            counts["duplicate"] += 1
            continue
        seen.add(iid)
        counts["kept"] += 1
        cls = pred_class(r.get("predicted_text"))
        classes[cls] += 1
        st = r.get("stats") or {}
        vals = {m: float(st[m]) for m in ERROR_METRICS if m in st and st[m] is not None}
        for m, v in vals.items():
            a = acc.setdefault(m, {"n": 0, "vals": [], "n_empty": 0, "empty_nonzero": 0, "empty_vals": [],
                                   "zeros": 0, "zero_empty": 0})
            a["n"] += 1
            a["vals"].append(v)
            if v == 0.0:
                a["zeros"] += 1
            if cls == "empty":
                a["n_empty"] += 1
                a["empty_vals"].append(v)
                if v != 0.0:
                    a["empty_nonzero"] += 1
                if v == 0.0:
                    a["zero_empty"] += 1
        if cls == "empty":
            empties.append((iid, vals))
        elif cls == "punct_only":
            punct.append((iid, vals, r.get("predicted_text")))
    metrics = {}
    for m, a in acc.items():
        s = math.fsum(a["vals"])
        se = math.fsum(a["empty_vals"])
        metrics[m] = {"n": a["n"], "sum": s, "n_empty": a["n_empty"], "empty_nonzero": a["empty_nonzero"],
                      "sum_empty": se, "corrected_sum": s - se + CORRECTED_EMPTY * a["n_empty"],
                      "zeros": a["zeros"], "zero_empty": a["zero_empty"]}
    return {"counts": counts, "classes": classes, "metrics": metrics, "empties": empties, "punct": punct}


def collect_run_names(obj):
    """Every string listed under a 'run_spec_names' key anywhere in a HELM groups/<group>.json document."""
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "run_spec_names" and isinstance(v, list):
                out.update(x for x in v if isinstance(x, str))
            else:
                out |= collect_run_names(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= collect_run_names(v)
    return out


def wer_cells(group_doc):
    """The headline WER column of a group's first (aggregate) table: [(model label, published value, run names)].
    The column is the first header whose value is exactly 'WER'; rows without a numeric value are skipped."""
    if not isinstance(group_doc, list) or not group_doc or not isinstance(group_doc[0], dict):
        return None
    t = group_doc[0]
    header = t.get("header") or []
    col = next((j for j, h in enumerate(header) if isinstance(h, dict) and str(h.get("value", "")).strip() == "WER"),
               None)
    if col is None:
        return None
    out = []
    for row in t.get("rows") or []:
        if not isinstance(row, list) or len(row) <= col or not row:
            continue
        cell = row[col] if isinstance(row[col], dict) else {}
        v = cell.get("value")
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        label = (row[0] or {}).get("value") if isinstance(row[0], dict) else None
        out.append((str(label), float(v), list(cell.get("run_spec_names") or [])))
    return out


def min_ranks_low(values, tol=1e-12):
    """Lower is better: rank = 1 + the number of entries strictly lower (by more than tol)."""
    return {k: 1 + sum(1 for w in values.values() if w < v - tol) for k, v in values.items()}


def mean(xs):
    xs = list(xs)
    return math.fsum(xs) / len(xs) if xs else None


def predictions93(n_empty, empty_all_zero, n_empty_gemini, n_records, max_cell_rise, models_rank_changed,
                  runs_multi_ref, th):
    """The six data predictions (P1, structural, is decided in job.py)."""
    return {
        "P2_guard_live": n_empty >= 1 and bool(empty_all_zero),
        "P3_gemini_majority": n_empty >= 1 and Fraction(n_empty_gemini, n_empty) >= th["P3_share"],
        "P4_rare": n_records > 0 and Fraction(n_empty, n_records) <= th["P4_share"],
        "P5_headline_moves": max_cell_rise is not None and max_cell_rise >= th["P5_rise"],
        "P6_rank_changes": models_rank_changed >= th["P6_min"],
        "P7_single_reference": runs_multi_ref == 0,
    }
