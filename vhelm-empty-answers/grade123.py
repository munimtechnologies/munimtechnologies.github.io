# SPDX-License-Identifier: Apache-2.0
# Audit 123 (pre-registered) by MV2 of Munim, Inc. Made with AI agents working in MV2's name.
"""VHELM suite v2.1.2: which stored answers are empty, and what do the metrics give an empty answer?

A census over every run of HELM's vision-language leaderboard suite v2.1.2 in the public bucket. For each run we read
display_predictions.json and count the unperturbed records whose predicted_text is empty (blank after strip). Where a
run is scored by the Prometheus-Vision judge (stat `prometheus_vision`, 1 to 5), we tally the judge's scores on empty
and on non-empty answers, and compare runs of the same group. Standard library only.
"""
import math
from fractions import Fraction

JUDGE = "prometheus_vision"
THINK_CLAUDE = "anthropic_claude-3-7-sonnet-20250219-thinking-64k"
THINK_GEMINI = "google_gemini-2.0-flash-thinking-exp-01-21"
CLAUDE_PLAIN = (
    "anthropic_claude-3-haiku-20240307",
    "anthropic_claude-3-sonnet-20240229",
    "anthropic_claude-3-opus-20240229",
    "anthropic_claude-3-5-sonnet-20240620",
    "anthropic_claude-3-5-sonnet-20241022",
    "anthropic_claude-3-7-sonnet-20250219",
)
# Counters that are not quality metrics; left out of the "what does an empty answer earn" tally.
SKIP_PREFIXES = ("num_", "prompt_truncated", "inference_", "batch_", "training_", "finish_reason", "logprob",
                 "max_prob", "predicted_index")


def scenario_of(run):
    return run.split(":", 1)[0]


def _args(run):
    return run.split(":", 1)[1].split(",") if ":" in run else []


def model_of(run):
    for p in _args(run):
        if p.startswith("model="):
            return p[len("model="):]
    return ""


def group_of(run):
    """The run name without its model argument: runs of one leaderboard cell share it."""
    return scenario_of(run) + ":" + ",".join(p for p in _args(run) if not p.startswith("model="))


def is_empty(text):
    return not isinstance(text, str) or text.strip() == ""


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (isinstance(v, float) and math.isnan(v))


def fmt(v):
    v = float(v)
    return str(int(v)) if v.is_integer() else "%.3g" % v


def summarize_preds(preds):
    """Census of one run's display_predictions (unperturbed records only)."""
    c = {"records": 0, "perturbed": 0, "n": 0, "empty": 0, "missing_text": 0}
    judge = {k: {"n": 0, "sum": 0.0, "hist": {}} for k in ("empty", "answered")}
    metric_empty = {}
    for r in preds or []:
        if not isinstance(r, dict):
            continue
        c["records"] += 1
        if r.get("perturbation") is not None:
            c["perturbed"] += 1
            continue
        c["n"] += 1
        t = r.get("predicted_text")
        if not isinstance(t, str):
            c["missing_text"] += 1
        e = is_empty(t)
        if e:
            c["empty"] += 1
        st = r.get("stats") or {}
        v = st.get(JUDGE)
        if is_number(v):
            j = judge["empty" if e else "answered"]
            j["n"] += 1
            j["sum"] += v
            key = fmt(v)
            j["hist"][key] = j["hist"].get(key, 0) + 1
        if e:
            for k, val in st.items():
                if is_number(val) and not str(k).startswith(SKIP_PREFIXES):
                    m = metric_empty.setdefault(k, [0, 0.0])
                    m[0] += 1
                    m[1] += val
    return {"counts": c, "judge": judge, "metric_empty": metric_empty}


def judge_mean(summary):
    j = summary["judge"]
    n = j["empty"]["n"] + j["answered"]["n"]
    return (j["empty"]["sum"] + j["answered"]["sum"]) / n if n else None


def stat_entry(stats, name, splits=("test", "valid")):
    """{count, sum, mean} of the unperturbed stat `name` (test split first, then valid); None when absent."""
    for split in splits:
        for s in stats or []:
            if not isinstance(s, dict):
                continue
            nm = s.get("name") or {}
            if (nm.get("name") == name and nm.get("split") == split and nm.get("perturbation") is None
                    and nm.get("sub_split") is None):
                return {"count": s.get("count"), "sum": s.get("sum"), "mean": s.get("mean"), "split": split}
    return None


def model_totals(rows):
    """{model: {n, empty, runs, runs_empty5, by_scenario: {scenario: [n, empty]}}} over parsed runs."""
    out = {}
    for r in rows:
        m = out.setdefault(r["model"], {"n": 0, "empty": 0, "runs": 0, "runs_empty5": 0, "by_scenario": {}})
        m["n"] += r["n"]
        m["empty"] += r["empty"]
        m["runs"] += 1
        if r["n"] and r["empty"] * 20 >= r["n"]:
            m["runs_empty5"] += 1
        b = m["by_scenario"].setdefault(r["scenario"], [0, 0])
        b[0] += r["n"]
        b[1] += r["empty"]
    return out


def p7_pairs(rows):
    """Judge-scored groups where a run with >=95% empty answers has a higher judge mean than a run with <=5%."""
    by = {}
    for r in rows:
        by.setdefault(r["group"], []).append(r)
    out = []
    for grp in sorted(by):
        rs = by[grp]
        ans = [r for r in rs if r["n"] and r.get("judge_mean") is not None and r["empty"] * 20 <= r["n"]]
        for e in sorted(rs, key=lambda x: x["model"]):
            if e["n"] and e.get("judge_mean") is not None and e["empty"] * 100 >= 95 * e["n"]:
                below = sorted(a["model"] for a in ans if a["judge_mean"] < e["judge_mean"])
                if below:
                    out.append({"group": grp, "empty_model": e["model"], "judge_mean": e["judge_mean"],
                                "answering_below": below, "answering_runs": len(ans)})
    return out


def verdicts(s):
    """The eight pre-registered predictions (True = HELD, False = FAILED, None = not gradable)."""
    listed, parsed = s["runs_listed"], s["runs_parsed"]
    tn, te, tr = s["think_n"], s["think_empty"], s["think_runs"]
    om = s.get("others_max_share")
    g50 = s.get("gemini_nonunicorn_runs50")
    ct, cu = s["claude_plain_empty"], s["claude_plain_empty_unicorn"]
    jn, js, j5 = s["judge_empty_n"], s["judge_empty_sum"], s["judge_empty_fives"]
    return {
        "P1": listed >= 2000 and parsed * 100 >= 95 * listed,
        "P2": None if not tn else (te * 100 >= 99 * tn and tr >= 30),
        "P3": None if om is None else om < Fraction(1, 2),
        "P4": None if g50 is None else g50 >= 1,
        "P5": None if not ct else cu * 5 >= ct * 4,
        "P6": None if not jn else (js >= 2 * jn and j5 * 5 >= jn),
        "P7": s["p7_pairs"] >= 1,
        "P8": s["models_run_empty5"] >= 10,
    }


def verdict_word(v):
    return "NOT GRADED" if v is None else ("HELD" if v else "FAILED")
