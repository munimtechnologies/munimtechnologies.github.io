"""Audit 103 helpers: what does HELM Classic's WikiFact "EM" column measure for each model?

HELM Classic (release v0.4.0) asks every model for 5 completions per WikiFact prompt at temperature 1.0
(run spec `wikifact:k=5`, "We will measure accuracy@k"). The published "EM" column is quasi_exact_match computed on
ONE of the five: HELM sorts the completions by their log probability (highest first; Python's sort is stable) and
scores the first after sorting (src/helm/benchmark/metrics/evaluate_reference_metrics.py, score_1). That gives three
regimes:
  * ranked: the API returns real log probabilities and different samples -> EM = the most likely of five samples;
  * zero_logprob: the API returns log probability 0 for everything -> the sort changes nothing -> EM = the first
    sample, a single temperature-1 draw;
  * collapsed: all five completions are the same text -> EM = that one answer.
HELM's prediction pages show completions[0] (src/helm/benchmark/presentation/run_display.py) next to the score of the
sorted top completion, which can be a different answer.

Estimators per test record (gold = any reference tagged correct, HELM's normalisation):
  H  HELM's EM, transcribed and gated against every stored record score;
  F  the first completion's score (what the page shows);
  M  the mean score over all returned completions (single-sample accuracy; defined the same way for every model);
  K  any of the completions scores (HELM's quasi_exact_match@5, not shown on the leaderboard).
Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import hashlib
import math
import re
import string
from fractions import Fraction

# ----- HELM's quasi_exact_match, transcribed (stanford-crfm/helm, Apache-2.0) -----


def normalize_text(text, should_remove_articles=True):
    """Lower text and remove punctuation, articles and extra whitespace (HELM's normalize_text)."""

    def remove_articles(t):
        return re.sub(r"\b(a|an|the)\b", " ", t)

    def white_space_fix(t):
        return " ".join(t.split())

    def remove_punc(t):
        exclude = set(string.punctuation)
        return "".join(ch for ch in t if ch not in exclude)

    def lower(t):
        return t.lower()

    normalized_text = remove_punc(lower(text))
    if should_remove_articles:
        normalized_text = remove_articles(normalized_text)
    return white_space_fix(normalized_text)


def quasi_exact_match(gold, pred):
    if not pred:
        return 0
    return 1 if normalize_text(gold) == normalize_text(pred) else 0


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v))


# ----- One record -----


def golds_of_instance(inst):
    return [((r.get("output") or {}).get("text") or "") for r in (inst or {}).get("references") or []
            if isinstance(r, dict) and "correct" in (r.get("tags") or [])]


def completions_of(rs):
    """[(raw text, logprob)] in the order the API returned them (logprob 0.0 when absent)."""
    out = []
    for c in ((rs or {}).get("result") or {}).get("completions") or []:
        if isinstance(c, dict):
            lp = c.get("logprob")
            out.append((c.get("text") or "", float(lp) if is_number(lp) else 0.0))
    return out


def score_record(golds, comps):
    """None without golds or completions. Otherwise: n completions; h = score of the top completion after HELM's
    stable sort by -logprob; f = score of completions[0]; q_sum = number of completions that score; k = any scores;
    top = index of HELM's top completion; distinct = distinct stripped texts; zero_lp = every logprob is 0;
    equal_lp = all logprobs are equal."""
    if not golds or not comps:
        return None
    qs = [max(quasi_exact_match(g, t.strip()) for g in golds) for t, _ in comps]
    order = sorted(range(len(comps)), key=lambda i: -comps[i][1])
    top = order[0]
    return {"n": len(comps), "h": qs[top], "f": qs[0], "q_sum": sum(qs), "k": max(qs), "top": top,
            "distinct": len(set(t.strip() for t, _ in comps)), "zero_lp": all(lp == 0 for _, lp in comps),
            "equal_lp": len(set(lp for _, lp in comps)) == 1}


# ----- One run -----

REC_KEYS = ("n5", "collapsed", "zero_lp", "equal_lp", "top_not_first", "display_disagree")


def summarize_run(state, preds, cap_keys=20):
    """Score every test-split, unperturbed request state of one run (first per (instance id, trial)).
    trials {trial: {n, h, f, m (Fraction sum of per-record means), k}}; rec: record counts by REC_KEYS;
    stat_missing / stat_mismatch: stored quasi_exact_match absent / different from H; stored_eq_first: mismatches
    where the stored score equals F; shown_mismatch / shown_missing: display_predictions' predicted_text differs from
    completions[0] / is absent; disagree_keys: up to cap_keys (instance id, trial) where F != H."""
    stored, shown = {}, {}
    for r in preds or []:
        if not isinstance(r, dict) or r.get("perturbation") is not None:
            continue
        key = (r.get("instance_id"), r.get("train_trial_index", 0))
        if key not in stored:
            stored[key] = (r.get("stats") or {}).get("quasi_exact_match")
            shown[key] = r.get("predicted_text")
    counts = {"request_states": 0, "perturbed": 0, "not_test": 0, "duplicate": 0, "no_result": 0, "kept": 0}
    rec = {k: 0 for k in REC_KEYS}
    trials, seen, disagree_keys = {}, set(), []
    stat_missing = stat_mismatch = stored_eq_first = shown_mismatch = shown_missing = 0
    for rs in (state or {}).get("request_states") or []:
        if not isinstance(rs, dict):
            continue
        counts["request_states"] += 1
        inst = rs.get("instance") or {}
        if inst.get("perturbation") is not None:
            counts["perturbed"] += 1
            continue
        if inst.get("split") != "test":
            counts["not_test"] += 1
            continue
        key = (inst.get("id"), rs.get("train_trial_index", 0))
        if key in seen:
            counts["duplicate"] += 1
            continue
        seen.add(key)
        comps = completions_of(rs)
        s = score_record(golds_of_instance(inst), comps)
        if s is None:
            counts["no_result"] += 1
            continue
        counts["kept"] += 1
        acc = trials.setdefault(key[1], {"n": 0, "h": 0, "f": 0, "m": Fraction(0), "k": 0})
        acc["n"] += 1
        acc["h"] += s["h"]
        acc["f"] += s["f"]
        acc["m"] += Fraction(s["q_sum"], s["n"])
        acc["k"] += s["k"]
        rec["n5"] += 1 if s["n"] == 5 else 0
        rec["collapsed"] += 1 if (s["n"] > 1 and s["distinct"] == 1) else 0
        rec["zero_lp"] += 1 if s["zero_lp"] else 0
        rec["equal_lp"] += 1 if s["equal_lp"] else 0
        rec["top_not_first"] += 1 if s["top"] != 0 else 0
        if s["f"] != s["h"]:
            rec["display_disagree"] += 1
            if len(disagree_keys) < cap_keys:
                disagree_keys.append(key)
        st = stored.get(key)
        if not is_number(st):
            stat_missing += 1
        elif int(round(st)) != s["h"]:
            stat_mismatch += 1
            if int(round(st)) == s["f"]:
                stored_eq_first += 1
        if key not in shown or shown[key] is None:
            shown_missing += 1
        elif shown[key] != comps[0][0]:
            shown_mismatch += 1
    return {"counts": counts, "trials": trials, "rec": rec, "stat_missing": stat_missing,
            "stat_mismatch": stat_mismatch, "stored_eq_first": stored_eq_first, "shown_mismatch": shown_mismatch,
            "shown_missing": shown_missing, "disagree_keys": disagree_keys}


def run_class(rec, kept):
    """'zero_logprob' when at least 90% of records have every logprob 0, else 'collapsed' when at least 90% have one
    distinct text, else 'ranked'; None without records."""
    if not kept:
        return None
    if rec["zero_lp"] * 10 >= 9 * kept:
        return "zero_logprob"
    if rec["collapsed"] * 10 >= 9 * kept:
        return "collapsed"
    return "ranked"


def adapter_class(classes):
    """The common class of an adapter's runs; 'mixed' when they differ; None without runs."""
    cs = set(classes)
    if not cs:
        return None
    return cs.pop() if len(cs) == 1 else "mixed"


def run_mean(trials, key):
    """HELM's run-level mean: the mean over trials of each trial's mean (exact Fraction; None without trials)."""
    ms = [Fraction(v[key], v["n"]) for _, v in sorted(trials.items()) if v["n"]]
    return sum(ms, Fraction(0)) / len(ms) if ms else None


# ----- Run names -----

def _parts(run):
    return run.split(":", 1)[1].split(",") if ":" in run else run.split(",")


def is_wikifact_k5(run):
    return run.startswith("wikifact:") and "k=5" in _parts(run)


def subject_of(run):
    for p in _parts(run):
        if p.startswith("subject="):
            return p[len("subject="):]
    return None


def adapter_of(run):
    """The run name without its subject= part: one HELM table row per adapter."""
    head = run.split(":", 1)[0] if ":" in run else ""
    return head + ":" + ",".join(p for p in _parts(run) if not p.startswith("subject="))


def model_part(name):
    """Everything after 'model=' (keeps later parts such as stop=hash); '' when absent."""
    i = name.find("model=")
    return name[i + len("model="):] if i >= 0 else ""


def select_runs(run_suites):
    """{run: suite} for every wikifact k=5 run."""
    return {r: s for r, s in (run_suites or {}).items() if is_wikifact_k5(r)}


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


# ----- Cells, ranks, matching -----

EST = ("h", "f", "m", "k")


def build_cells(runs, listed):
    """runs {run: {adapter, trials}} (included runs only); listed {adapter: [every listed run]} ->
    {adapter: {h, f, m, k (Fractions), runs}}: the mean over the adapter's runs of each run's mean, only for adapters
    whose every listed run is included."""
    cells = {}
    for ad, names in listed.items():
        if not names or any(n not in runs for n in names):
            continue
        cells[ad] = {k: sum((run_mean(runs[n]["trials"], k) for n in names), Fraction(0)) / len(names) for k in EST}
        cells[ad]["runs"] = len(names)
    return cells


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


def group_values(group_doc, name="EM"):
    """Numeric values of the column whose header is exactly `name` in a group page's first table."""
    if not isinstance(group_doc, list) or not group_doc or not isinstance(group_doc[0], dict):
        return None
    t = group_doc[0]
    header = t.get("header") or []
    col = next((j for j, h in enumerate(header) if isinstance(h, dict) and str(h.get("value") or "") == name), None)
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


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def stable_hash(text):
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def pick(lst, salt):
    """One element of a list of (instance id, trial) keys, chosen by a stable hash (None for an empty list)."""
    if not lst:
        return None
    return min(lst, key=lambda k: (stable_hash("%s|%s|%s" % (salt, k[0], k[1])), str(k)))


# ----- Verdicts -----

def verdicts(s):
    """The eight pre-registered predictions (True = HELD) from the job's pooled statistics `s`."""
    rb, ub = s.get("ranked_bonus_median"), s.get("unranked_bonus_median")
    return {
        "P1": (bool(s["fixtures"]) and s["runs_listed"] > 0 and s["runs_included"] * 10 >= 9 * s["runs_listed"]
               and s["cells"] >= 60 and s["matched"] * 10 >= 9 * s["cells"]),
        "P2": s["unranked_adapters"] >= 4,
        "P3": s["ranked_n"] > 0 and (s["ranked_h"] - s["ranked_m"]) * 50 >= s["ranked_n"],
        "P4": rb is not None and ub is not None and rb > ub,
        "P5": s["movers"] >= 5,
        "P6": s["tau"] is not None and s["tau"] >= 0.9,
        "P7": s["ranked_n"] > 0 and s["ranked_disagree"] * 20 >= s["ranked_n"],
        "P8": s["unranked_adapters"] > 0 and 4 * s["unranked_rise_or_stay"] >= 3 * s["unranked_adapters"],
    }
