"""Audit 106 helpers: the LLM-judge jury behind HELM Capabilities' WildBench and Omni-MATH columns.

HELM Capabilities scores WildBench (1-10 "WB Score", shown rescaled to 0-1) and Omni-MATH ("Acc") with LLM judges.
Since February 2025 (HELM PRs #3283, #3291, #3318, #3322) each record is judged by a jury: GPT-4o (2024-05-13),
Claude 3.5 Sonnet (2024-10-22) and Llama 3.1 405B Instruct Turbo. PR #3926 (2025-11-19) removed the Claude judge and
PR #4233 (2026-04-27) the Llama judge. A record's score is the mean of the judges' non-None values
(wildbench_metrics.py / omni_math_metrics.py: every annotation key ending in "_score" or "_equivalence_judgement",
the empty-output key included); a run's value is the mean over records.

This module reads the per-record jury from HELM's published annotations and computes: each record's HELM score, which
judges rated each run, each judge's offset from the other judges, own-family offsets (self-preference), the score
under another jury, and the eight pre-registered verdicts.
Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import math
import random

SCENARIOS = {
    "wildbench": {"prefix": "wildbench:", "ann": "wildbench", "suffix": "_score", "empty": "empty_output_score",
                  "stat": "wildbench_score", "cell_stat": "wildbench_score_rescaled", "column": "WB Score"},
    "omni_math": {"prefix": "omni_math:", "ann": "omni_math", "suffix": "_equivalence_judgement",
                  "empty": "empty_output_equivalence_judgement", "stat": "omni_math_accuracy",
                  "cell_stat": "omni_math_accuracy", "column": "Acc"},
}

THREE_FAMILIES = frozenset(("openai", "anthropic", "meta"))
JUDGE_FAMILIES = (("gpt", "openai"), ("openai", "openai"), ("claude", "anthropic"), ("anthropic", "anthropic"),
                  ("llama", "meta"), ("meta", "meta"))


# ----- One record -----


def _val(v):
    """(value, bad): a judge value as HELM uses it. None stays None; bools and numbers become floats; any other type
    is counted as bad and treated as None."""
    if v is None:
        return None, False
    if isinstance(v, bool):
        return float(int(v)), False
    if isinstance(v, (int, float)):
        return float(v), False
    return None, True


def parse_annotation(ann, scen):
    """(judges, empty, helm, bad) for one record's annotation dict.
    judges: {judge name: value or None} for every key ending in the scenario suffix except the empty-output key;
    empty: the empty-output key is present (no judge was asked);
    helm: HELM's record score = mean of every non-None value of a key ending in the suffix (empty-output key included),
    None when there is none (HELM raises in that case);
    bad: values of an unexpected type (ignored)."""
    sfx, ekey = scen["suffix"], scen["empty"]
    judges, vals, bad, empty = {}, [], 0, False
    for k in sorted(ann):
        if not isinstance(k, str) or not k.endswith(sfx):
            continue
        v, b = _val(ann[k])
        bad += 1 if b else 0
        if k == ekey:
            empty = True
        else:
            judges[k[:-len(sfx)]] = v
        if v is not None:
            vals.append(v)
    helm = sum(vals) / len(vals) if vals else None
    return judges, empty, helm, bad


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


# ----- One run -----


def summarize_run(predictions, scen):
    """Census of one run's display predictions (first per (instance id, trial), unperturbed only).
    records: [{"key", "j" (judges), "empty", "h" (HELM score)}]; stored_n / mismatch: records with a stored per-record
    stat, and how many of them differ from our HELM score by more than 1e-9."""
    counts = {"predictions": 0, "perturbed": 0, "duplicate": 0, "no_annotation": 0, "kept": 0, "empty": 0,
              "unscored": 0, "bad_values": 0}
    seen, records = set(), []
    stored_n = mismatch = 0
    for p in predictions or []:
        if not isinstance(p, dict):
            continue
        counts["predictions"] += 1
        if p.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        key = (p.get("instance_id"), p.get("train_trial_index", 0))
        if key in seen:
            counts["duplicate"] += 1
            continue
        seen.add(key)
        ann = (p.get("annotations") or {}).get(scen["ann"])
        if not isinstance(ann, dict):
            counts["no_annotation"] += 1
            continue
        judges, empty, helm, bad = parse_annotation(ann, scen)
        counts["bad_values"] += bad
        counts["kept"] += 1
        if empty:
            counts["empty"] += 1
        if helm is None:
            counts["unscored"] += 1
        stored = _num((p.get("stats") or {}).get(scen["stat"]))
        if stored is not None:
            stored_n += 1
            if helm is None or abs(helm - stored) > 1e-9:
                mismatch += 1
        records.append({"key": key, "j": judges, "empty": empty, "h": helm})
    return {"counts": counts, "records": records, "stored_n": stored_n, "mismatch": mismatch}


def predictions_from_state(state):
    """Display-prediction-like dicts from a HELM scenario_state.json (fallback when display predictions carry no
    annotations)."""
    out = []
    for rs in (state or {}).get("request_states") or []:
        if not isinstance(rs, dict):
            continue
        inst = rs.get("instance") or {}
        out.append({"instance_id": inst.get("id"), "train_trial_index": rs.get("train_trial_index", 0),
                    "perturbation": inst.get("perturbation"), "annotations": rs.get("annotations"), "stats": {}})
    return out


def run_mean(records, score_of):
    """HELM's run value: mean over trials of each trial's mean score (records scoring None are skipped)."""
    trials = {}
    for r in records:
        v = score_of(r)
        if v is None:
            continue
        t = trials.setdefault(r["key"][1], [0.0, 0])
        t[0] += v
        t[1] += 1
    vs = [a / n for a, n in (trials[k] for k in sorted(trials)) if n]
    return sum(vs) / len(vs) if vs else None


def rescale_wb(x):
    """WildBench 1-10 score to HELM's 0-1 'WB Score'."""
    return None if x is None else (x - 1.0) / 9.0


def jury_score(r, names):
    """A record's score under the jury `names`: mean of those judges' values. An empty-output record keeps its fixed
    score; a record none of the jury rated keeps HELM's score (see jury_fallback)."""
    if r["empty"]:
        return r["h"]
    vals = [r["j"][n] for n in names if r["j"].get(n) is not None]
    return sum(vals) / len(vals) if vals else r["h"]


def jury_fallback(r, names):
    return (not r["empty"]) and not any(r["j"].get(n) is not None for n in names)


def judge_coverage(records):
    """(non-empty records, {judge: non-empty records with a value from that judge})."""
    n, cov = 0, {}
    for r in records:
        if r["empty"]:
            continue
        n += 1
        for name, v in r["j"].items():
            cov.setdefault(name, 0)
            if v is not None:
                cov[name] += 1
    return n, cov


def present_judges(n, cov, share):
    """Judges with a value on at least `share` of the n non-empty records (sorted)."""
    return sorted(k for k, c in cov.items() if n and c >= share * n)


def judge_offsets(records, names):
    """Over non-empty records where every judge in `names` (at least two) has a value: n, each judge's mean, each
    judge's mean offset from the mean of the other judges, and the share of records where all judges agree."""
    names = sorted(names)
    if len(names) < 2:
        return None
    n, same = 0, 0
    sums = {k: 0.0 for k in names}
    offs = {k: 0.0 for k in names}
    for r in records:
        if r["empty"]:
            continue
        vs = [r["j"].get(k) for k in names]
        if any(v is None for v in vs):
            continue
        n += 1
        tot = sum(vs)
        for k, v in zip(names, vs):
            sums[k] += v
            offs[k] += v - (tot - v) / (len(vs) - 1)
        if all(v == vs[0] for v in vs):
            same += 1
    if not n:
        return {"n": 0, "mean": {}, "offset": {}, "agree": None}
    return {"n": n, "mean": {k: sums[k] / n for k in names}, "offset": {k: offs[k] / n for k in names},
            "agree": same / n}


# ----- Families, self-preference -----


def judge_family(name):
    n = (name or "").lower()
    for sub, fam in JUDGE_FAMILIES:
        if sub in n:
            return fam
    return None


def model_part(name):
    i = name.find("model=")
    return name[i + len("model="):] if i >= 0 else ""


def model_family(model):
    """Creator prefix of a HELM model name ('openai_gpt-4o-2024-11-20' -> 'openai')."""
    return model.split("_", 1)[0]


def composition_check(suite, n, cov, last_suite, share):
    """Pre-registered jury composition: runs before `last_suite` have a GPT, a Claude and a Llama judge each on at
    least `share` of non-empty records; runs of `last_suite` have no value at all from a Claude judge."""
    if suite == last_suite:
        return sum(c for k, c in cov.items() if judge_family(k) == "anthropic") == 0
    fams = {judge_family(k) for k in present_judges(n, cov, share)}
    return THREE_FAMILIES <= fams


def self_preference(rows, judge):
    """(diff, n_own, n_other, own, other): mean offset of `judge` on runs of its own family minus its mean offset on
    the other runs. rows: [(model family, {judge: offset})]; rows without the judge are skipped."""
    fam = judge_family(judge)
    own = [o[judge] for f, o in rows if judge in o and f == fam]
    other = [o[judge] for f, o in rows if judge in o and f != fam]
    if not own or not other:
        return None, len(own), len(other), own, other
    return sum(own) / len(own) - sum(other) / len(other), len(own), len(other), own, other


def perm_p(own, other, iters, seed):
    """One-sided permutation p-value of mean(own) - mean(other): (hits + 1) / (iters + 1) over label shuffles with a
    fixed seed. None when either group is empty."""
    if not own or not other:
        return None
    k = len(own)
    obs = sum(own) / k - sum(other) / len(other)
    pool = list(own) + list(other)
    rng = random.Random(seed)
    hits = 0
    for _ in range(iters):
        rng.shuffle(pool)
        d = sum(pool[:k]) / k - sum(pool[k:]) / (len(pool) - k)
        if d >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (iters + 1)


# ----- Release files -----


def select_runs(run_suites, prefix):
    return {r: s for r, s in (run_suites or {}).items() if r.startswith(prefix)}


def stat_entry(stats, name, split):
    """{count, sum, mean} of the unperturbed stat `name` on `split` in a HELM stats.json list (None when absent)."""
    for s in stats or []:
        if not isinstance(s, dict):
            continue
        nm = s.get("name") or {}
        if (nm.get("name") == name and nm.get("split") == split and nm.get("perturbation") is None
                and nm.get("sub_split") is None):
            return {"count": s.get("count"), "sum": s.get("sum"), "mean": s.get("mean")}
    return None


def group_values(group_doc, prefix):
    """Numeric values of the first column whose header starts with `prefix` in a group page's first table."""
    if not isinstance(group_doc, list) or not group_doc or not isinstance(group_doc[0], dict):
        return None
    t = group_doc[0]
    header = t.get("header") or []
    col = next((j for j, h in enumerate(header)
                if isinstance(h, dict) and str(h.get("value") or "").startswith(prefix)), None)
    if col is None:
        return None
    out = []
    for row in t.get("rows") or []:
        if isinstance(row, list) and len(row) > col and isinstance(row[col], dict):
            v = row[col].get("value")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append(float(v))
    return out


# ----- Ranks, matching -----


def ranks_high(values):
    """Higher is better: rank = 1 + the number of entries strictly higher."""
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


# ----- Verdicts -----


def verdicts(s):
    """The eight pre-registered predictions (True = HELD) from the job's pooled statistics `s`."""
    sc = ("wildbench", "omni_math")
    sp_wb = [v for v in (s["sp_wb"] or {}).values() if v is not None]
    sp_om = [v for v in (s["sp_omni"] or {}).values() if v is not None]
    return {
        "P1": (bool(s["fixtures"])
               and all(s["listed"][k] > 0 and s["included"][k] * 10 >= 9 * s["listed"][k] and s["cells"][k] > 0
                       and s["matched"][k] * 10 >= 9 * s["cells"][k] for k in sc)),
        "P2": bool(s["composition_ok"]),
        "P3": sum(1 for v in sp_wb if v > 0) >= 2 and bool(sp_wb) and max(sp_wb) >= 0.10 - 1e-12,
        "P4": s["lenience_spread_wb"] is not None and s["lenience_spread_wb"] >= 0.30 - 1e-12,
        "P5": s["agree_omni"] is not None and s["agree_omni"] >= 0.85 - 1e-12,
        "P6": len(sp_om) == 3 and all(abs(v) < 0.02 for v in sp_om),
        "P7": (s["tau_gpt_wb"] is not None and s["tau_gpt_wb"] >= 0.85 - 1e-12 and s["movers_gpt_wb"] >= 3),
        "P8": s["v115_movers_common_wb"] >= 1,
    }
