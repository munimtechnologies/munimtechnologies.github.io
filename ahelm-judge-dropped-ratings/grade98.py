"""Audit 98 helpers: judge ratings that HELM drops silently from AHELM's GPT-4o-judged columns (HELM issue #4345).

HELM (stanford-crfm/helm, src/helm/benchmark/metrics/gpt4_audio_critique_metrics.py) asks a judge for a 1-5 rating and
reads it with re.search(r"Rating:\\s*([1-5])", ...). When the regex finds nothing, the helper returns None, and
Stat.add (src/helm/benchmark/metrics/statistic.py) skips None, so the rating is simply not counted; when the critique
request returns no responses, evaluate_generation returns no stat at all. Either way the instance leaves the run's
mean instead of lowering it, and the published mean is over fewer ratings than were requested.

This module counts those drops from the published archive and re-values each dropped rating at 1, the lowest
rating the rubric allows. Apache-2.0.

v2 (2026-11-10, after the v1 job): judge_cells also reads the run names from the row's first (model) cell when the
judge cell carries none. The AudioCaps group page of AHELM v1.0.0 stores run_spec_names only on the model cell, so
v1 listed no AudioCaps runs. Nothing else changed.
"""

import math
import re
from fractions import Fraction

JUDGE_METRIC = "gpt4_audio_critique"
JUDGE_CLASS_SUFFIX = "GPT4AudioCritiqueMetric"
LOW_RATING = 1
RATING_RE = re.compile(r"Rating:\s*([1-5])")  # HELM's extraction regex, applied here to the MODEL's output (#4344)
OUTPUT_CLASSES = ("missing", "empty", "rating_text", "text")
HIST_KEYS = ("1", "2", "3", "4", "5", "other")


def model_of(run_name):
    """'audiocaps:model=qwen_qwen2-audio-7b-instruct' -> 'qwen_qwen2-audio-7b-instruct' (text after the last 'model=')."""
    i = run_name.rfind("model=")
    return run_name[i + len("model="):] if i >= 0 else ""


def stat_entry(stats, name):
    """{count, sum, mean} of the unperturbed test-split stat `name` in a HELM stats.json list (None when absent)."""
    for s in stats or []:
        if not isinstance(s, dict):
            continue
        nm = s.get("name") or {}
        if (nm.get("name") == name and nm.get("split") == "test" and nm.get("perturbation") is None
                and nm.get("sub_split") is None):
            return {"count": s.get("count"), "sum": s.get("sum"), "mean": s.get("mean")}
    return None


def num_respondents(run_spec):
    """num_respondents of the run's GPT4AudioCritiqueMetric spec (None when the run has no such metric)."""
    for m in (run_spec or {}).get("metric_specs") or []:
        if isinstance(m, dict) and str(m.get("class_name", "")).endswith(JUDGE_CLASS_SUFFIX):
            return (m.get("args") or {}).get("num_respondents")
    return None


def output_class(text):
    """'missing' (no text field), 'empty' (empty after strip), 'rating_text' (the model's own output already contains
    a string HELM's judge regex would read, the pattern of HELM issue #4344) or 'text'."""
    if text is None:
        return "missing"
    t = text.strip()
    if not t:
        return "empty"
    if RATING_RE.search(t):
        return "rating_text"
    return "text"


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v))


def summarize_run(records):
    """Census of one run's display_predictions records (first trial, unperturbed, first record per instance id).

    judged = kept records whose stats carry a numeric judge value; unjudged = kept records without one (the dropped
    ratings, with the class of the model output). hist counts judged values 1..5 ('other' for anything else).
    """
    counts = {"n_records": 0, "other_trial": 0, "perturbed": 0, "duplicate": 0, "kept": 0}
    classes = {c: 0 for c in OUTPUT_CLASSES}
    unjudged_classes = {c: 0 for c in OUTPUT_CLASSES}
    hist = {k: 0 for k in HIST_KEYS}
    vals, unjudged, rating_text, seen = [], [], [], set()
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
        cls = output_class(r.get("predicted_text"))
        classes[cls] += 1
        v = (r.get("stats") or {}).get(JUDGE_METRIC)
        if is_number(v):
            v = float(v)
            vals.append(v)
            key = str(int(v)) if v == int(v) and 1 <= v <= 5 else "other"
            hist[key] += 1
        else:
            unjudged.append((iid, cls))
            unjudged_classes[cls] += 1
        if cls == "rating_text":
            rating_text.append((iid, v if is_number(v) else None))
    return {"counts": counts, "classes": classes, "judged": len(vals), "sum": math.fsum(vals), "hist": hist,
            "unjudged": unjudged, "unjudged_classes": unjudged_classes, "rating_text": rating_text}


def corrected_mean(total, judged, dropped, low=LOW_RATING):
    """Mean with every dropped rating counted at `low` (None when there is nothing to average)."""
    n = judged + dropped
    return (total + low * dropped) / n if n else None


def judge_cells(group_doc):
    """The judge column of a group's first (aggregate) table: [(model label, published value, run names)].
    The column is the first header whose value contains 'Judge Critique'; rows without a numeric value are skipped.
    Run names come from the judge cell's run_spec_names, or (v2) from the row's first cell when the judge cell has
    none, as on AHELM's AudioCaps page."""
    if not isinstance(group_doc, list) or not group_doc or not isinstance(group_doc[0], dict):
        return None
    t = group_doc[0]
    header = t.get("header") or []
    col = next((j for j, h in enumerate(header)
                if isinstance(h, dict) and "Judge Critique" in str(h.get("value", ""))), None)
    if col is None:
        return None
    out = []
    for row in t.get("rows") or []:
        if not isinstance(row, list) or len(row) <= col or not row:
            continue
        cell = row[col] if isinstance(row[col], dict) else {}
        v = cell.get("value")
        if not is_number(v):
            continue
        first = row[0] if isinstance(row[0], dict) else {}
        label = first.get("value") if first else None
        names = cell.get("run_spec_names") or first.get("run_spec_names") or []
        out.append((str(label), float(v), list(names)))
    return out


def cell_rule(value, runs, tol):
    """Which aggregation reproduces a published cell from its runs' [(count, sum)]: 'pooled' (sum of sums over sum of
    counts, checked first because HELM's cell description shows a pooled sum and count), 'mean_of_means', or None."""
    if not runs or any(c is None or c <= 0 for c, _ in runs):
        return None
    pooled = math.fsum(s for _, s in runs) / sum(c for c, _ in runs)
    if abs(pooled - value) <= tol:
        return "pooled"
    mom = math.fsum(s / c for c, s in runs) / len(runs)
    if abs(mom - value) <= tol:
        return "mean_of_means"
    return None


def cell_value(rule, runs, low=LOW_RATING):
    """A cell's value under `rule` from [(count, sum, dropped)]: dropped ratings counted at `low` (pass dropped 0 for
    the published value)."""
    if rule == "pooled":
        n = sum(c + d for c, _, d in runs)
        return (math.fsum(s for _, s, _ in runs) + low * sum(d for _, _, d in runs)) / n if n else None
    if rule == "mean_of_means":
        return math.fsum(corrected_mean(s, c, d, low) for c, s, d in runs) / len(runs) if runs else None
    return None


def ranks_high(values, tol=1e-12):
    """Higher is better: rank = 1 + the number of entries strictly higher (by more than tol)."""
    return {k: 1 + sum(1 for w in values.values() if w > v + tol) for k, v in values.items()}


def top_k_sum(per_model, k):
    return sum(sorted(per_model.values(), reverse=True)[:k])


def predictions98(dropped, requested, top3, max_cell_fall, models_rank_changed, unjudged_empty, unjudged, th):
    """The six data predictions (P1, structural, is decided in job.py)."""
    return {
        "P2_drops_live": dropped >= 1,
        "P3_drops_rare": requested > 0 and Fraction(dropped, requested) <= th["P3_share"],
        "P4_concentrated": dropped >= 1 and Fraction(top3, dropped) >= th["P4_share"],
        "P5_headline_falls": max_cell_fall is not None and max_cell_fall >= th["P5_fall"],
        "P6_rank_changes": models_rank_changed >= th["P6_min"],
        "P7_not_mainly_empty": unjudged >= 1 and Fraction(unjudged_empty, unjudged) < th["P7_share"],
    }
