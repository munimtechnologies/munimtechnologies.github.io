# SPDX-License-Identifier: Apache-2.0
"""Audit 123: a census of empty answers across VHELM suite v2.1.2, and what the metrics give them.

Lists every run of VHELM's run suite v2.1.2 in HELM's public bucket (crfm-helm-public), reads each run's
display_predictions.json, counts the unperturbed records whose answer is empty, and, for runs scored by the
Prometheus-Vision judge, tallies the judge's scores on empty and non-empty answers and reads the stored run mean
from stats.json. Only run names, counts, metric names and public model names go to results.json; no model text.
Usage: python job.py --out-dir /out (network required). Standard library only. Apache-2.0.
Made with AI agents working in MV2's name (MV2 of Munim, Inc.).
"""
import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import grade123 as g

BUCKET = "crfm-helm-public"
SUITE = "v2.1.2"
RUNS_PREFIX = "vhelm/benchmark_output/runs/%s/" % SUITE
UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research)"}
WORKERS = 6
TOL = 1e-6


def _get(url, tries=4):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry transient network errors
            last = e
    raise RuntimeError("GET failed after %d tries: %s (%s)" % (tries, url, last))


def _json(url):
    return json.loads(_get(url).decode("utf-8"))


def list_runs():
    runs, other, token = [], [], None
    while True:
        q = {"prefix": RUNS_PREFIX, "delimiter": "/", "maxResults": "1000"}
        if token:
            q["pageToken"] = token
        doc = _json("https://storage.googleapis.com/storage/v1/b/%s/o?%s" % (BUCKET, urllib.parse.urlencode(q)))
        for p in doc.get("prefixes") or []:
            name = p[len(RUNS_PREFIX):].rstrip("/")
            (runs if ":" in name else other).append(name)
        token = doc.get("nextPageToken")
        if not token:
            return sorted(runs), sorted(other)


def run_url(run, fname):
    return "https://storage.googleapis.com/%s/%s%s/%s" % (
        BUCKET, RUNS_PREFIX, urllib.parse.quote(run, safe=":,=@-_."), fname)


def load_run(run):
    rec = {"run": run, "scenario": g.scenario_of(run), "model": g.model_of(run), "group": g.group_of(run)}
    try:
        preds = _json(run_url(run, "display_predictions.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    if not isinstance(preds, list):
        rec["error"] = "display_predictions.json is not a list"
        return run, rec
    s = g.summarize_preds(preds)
    del preds
    rec["summary"] = s
    rec["judge_mean"] = g.judge_mean(s)
    if rec["judge_mean"] is not None:
        try:
            e = g.stat_entry(_json(run_url(run, "stats.json")), g.JUDGE)
            rec["judge_stored"] = None if e is None else e.get("mean")
        except Exception as ex:  # noqa: BLE001
            rec["judge_stored"] = None
            rec["stats_error"] = str(ex)[:200]
    return run, rec


def f(x):
    return None if x is None else float(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    runs, other = list_runs()
    print("[suite] %s runs listed=%d (prefixes without ':' skipped=%d: %s)" % (SUITE, len(runs), len(other),
                                                                            other[:10]))
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        loaded = dict(ex.map(load_run, runs))

    failed = sorted(r for r in runs if "error" in loaded[r])
    rows = []
    for run in runs:
        r = loaded[run]
        if "error" in r:
            continue
        c = r["summary"]["counts"]
        rows.append({"run": run, "scenario": r["scenario"], "model": r["model"], "group": r["group"],
                     "n": c["n"], "empty": c["empty"], "judge_mean": r["judge_mean"]})
    print("[runs] listed=%d parsed=%d failed=%d" % (len(runs), len(rows), len(failed)))
    for run in failed[:50]:
        print("[failed] %s %s" % (run, loaded[run]["error"]))

    totals = g.model_totals(rows)
    n_all = sum(r["n"] for r in rows)
    e_all = sum(r["empty"] for r in rows)
    print("[pooled] records=%d empty=%d models=%d" % (n_all, e_all, len(totals)))
    for m in sorted(totals, key=lambda k: (-Fraction(totals[k]["empty"], totals[k]["n"] or 1), k)):
        t = totals[m]
        top = sorted(((v[1], s) for s, v in t["by_scenario"].items() if v[1]), reverse=True)[:6]
        print("[model] %s n=%d empty=%d share=%.4f runs=%d runs_empty5=%d top=%s" % (
            m, t["n"], t["empty"], t["empty"] / t["n"] if t["n"] else 0.0, t["runs"], t["runs_empty5"], top))

    # Scenario table: records, empty answers and models with any empty answer.
    scen = {}
    for r in rows:
        s = scen.setdefault(r["scenario"], {"runs": 0, "n": 0, "empty": 0, "models_with_empty": set()})
        s["runs"] += 1
        s["n"] += r["n"]
        s["empty"] += r["empty"]
        if r["empty"]:
            s["models_with_empty"].add(r["model"])
    scen_out = {k: {"runs": v["runs"], "n": v["n"], "empty": v["empty"],
                    "models_with_empty": sorted(v["models_with_empty"])} for k, v in sorted(scen.items())}
    for k, v in scen_out.items():
        print("[scenario] %s runs=%d n=%d empty=%d models_with_empty=%d" % (
            k, v["runs"], v["n"], v["empty"], len(v["models_with_empty"])))

    # What each metric gives an empty answer, per scenario (descriptive).
    metric_empty = {}
    for run in runs:
        r = loaded[run]
        if "error" in r:
            continue
        for k, (cnt, sm) in r["summary"]["metric_empty"].items():
            key = r["scenario"] + "|" + k
            a = metric_empty.setdefault(key, [0, 0.0])
            a[0] += cnt
            a[1] += sm
    metric_empty_out = {k: {"n": v[0], "mean": v[1] / v[0] if v[0] else None} for k, v in sorted(metric_empty.items())}
    for k, v in metric_empty_out.items():
        print("[metric on empty] %s n=%d mean=%s" % (k, v["n"], v["mean"]))

    # Judge: pooled scores on empty and non-empty answers, and the stored-mean check.
    jp = {k: {"n": 0, "sum": 0.0, "hist": {}} for k in ("empty", "answered")}
    judge_runs, judge_match, judge_rows = 0, 0, []
    for run in runs:
        r = loaded[run]
        if "error" in r or r.get("judge_mean") is None:
            continue
        judge_runs += 1
        st = r.get("judge_stored")
        ok = st is not None and abs(st - r["judge_mean"]) <= TOL
        judge_match += 1 if ok else 0
        jj = r["summary"]["judge"]
        for k in ("empty", "answered"):
            jp[k]["n"] += jj[k]["n"]
            jp[k]["sum"] += jj[k]["sum"]
            for h, cnt in jj[k]["hist"].items():
                jp[k]["hist"][h] = jp[k]["hist"].get(h, 0) + cnt
        c = r["summary"]["counts"]
        judge_rows.append({"run": run, "model": r["model"], "group": r["group"], "n": c["n"], "empty": c["empty"],
                           "judge_mean": r["judge_mean"], "judge_stored": st, "stored_match": ok,
                           "judge_empty": jj["empty"], "judge_answered_n": jj["answered"]["n"]})
    for k in ("empty", "answered"):
        n = jp[k]["n"]
        print("[judge %s] n=%d mean=%s hist=%s" % (k, n, jp[k]["sum"] / n if n else None,
                                                 json.dumps(jp[k]["hist"], sort_keys=True)))
    print("[judge check] judged runs=%d stored mean reproduced=%d" % (judge_runs, judge_match))

    pairs = g.p7_pairs([r for r in rows if r["judge_mean"] is not None])
    for p in pairs:
        print("[p7] %s" % json.dumps(p, sort_keys=True))

    # Per-group judge ranks (descriptive): where does each >=95%-empty run rank among its group?
    groups = {}
    for r in rows:
        if r["judge_mean"] is not None:
            groups.setdefault(r["group"], []).append(r)
    empty_ranks = []
    for grp in sorted(groups):
        rs = groups[grp]
        for e in rs:
            if e["n"] and e["empty"] * 100 >= 95 * e["n"]:
                rank = 1 + sum(1 for x in rs if x["judge_mean"] > e["judge_mean"])
                empty_ranks.append({"group": grp, "model": e["model"], "judge_mean": e["judge_mean"],
                                    "rank": rank, "of": len(rs)})
                print("[empty rank] %s %s judge=%.4f rank %d of %d" % (grp, e["model"], e["judge_mean"], rank,
                                                                       len(rs)))

    others = [m for m in totals if m != g.THINK_CLAUDE and totals[m]["n"]]
    tc = totals.get(g.THINK_CLAUDE, {"n": 0, "empty": 0, "runs": 0})
    gem = [r for r in rows if r["model"] == g.THINK_GEMINI]
    stats = {
        "runs_listed": len(runs), "runs_parsed": len(rows),
        "think_n": tc["n"], "think_empty": tc["empty"], "think_runs": tc["runs"],
        "others_max_share": max((Fraction(totals[m]["empty"], totals[m]["n"]) for m in others), default=None),
        "gemini_nonunicorn_runs50": (sum(1 for r in gem if r["scenario"] != "unicorn" and r["n"]
                                         and r["empty"] * 2 >= r["n"]) if gem else None),
        "claude_plain_empty": sum(r["empty"] for r in rows if r["model"] in g.CLAUDE_PLAIN),
        "claude_plain_empty_unicorn": sum(r["empty"] for r in rows
                                          if r["model"] in g.CLAUDE_PLAIN and r["scenario"] == "unicorn"),
        "judge_empty_n": jp["empty"]["n"], "judge_empty_sum": jp["empty"]["sum"],
        "judge_empty_fives": jp["empty"]["hist"].get("5", 0),
        "p7_pairs": len(pairs),
        "models_run_empty5": sum(1 for m in totals if totals[m]["runs_empty5"]),
    }
    print("[stats] %s" % json.dumps({k: (f(v) if isinstance(v, Fraction) else v) for k, v in stats.items()},
                                    sort_keys=True))
    verdicts = g.verdicts(stats)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, g.verdict_word(v)))

    out = {
        "audit": 123,
        "slug": "vhelm-empty-answers",
        "dataset": ("Per-instance outputs of HELM's VHELM run suite %s (Stanford CRFM), every run in the public "
                    "bucket. Only run names, counts, metric names and public model names are published." % SUITE),
        "runs_listed": len(runs),
        "runs_parsed": len(rows),
        "prefixes_skipped": other,
        "failed_runs": {r: loaded[r]["error"] for r in failed},
        "pooled": {"records": n_all, "empty": e_all},
        "stats": {k: (f(v) if isinstance(v, Fraction) else v) for k, v in stats.items()},
        "verdicts": {k: g.verdict_word(v) for k, v in verdicts.items()},
        "models": {m: {"n": t["n"], "empty": t["empty"], "runs": t["runs"], "runs_empty5": t["runs_empty5"],
                       "by_scenario": {s: v for s, v in sorted(t["by_scenario"].items()) if v[1]}}
                   for m, t in sorted(totals.items())},
        "scenarios": scen_out,
        "metric_on_empty": metric_empty_out,
        "judge_pooled": jp,
        "judge_runs": judge_runs,
        "judge_stored_reproduced": judge_match,
        "judge_table": judge_rows,
        "p7_pairs": pairs,
        "empty_run_judge_ranks": empty_ranks,
        "runs_with_empty": [[r["run"], r["n"], r["empty"]] for r in rows if r["empty"]],
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=True, separators=(",", ":"))
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
