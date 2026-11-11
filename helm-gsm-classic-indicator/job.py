"""Audit 101: does HELM Classic's GSM8K column score right answers 0 because it compares only the last token?

Downloads every gsm run of HELM Classic release v0.4.0, re-grades every test record of every trial with HELM's
exact_match_indicator (transcribed; must reproduce every stored score), HELM's final_number_exact_match (transcribed;
the metric HELM Lite uses for GSM8K) and our stated-answer grade (CORR), classes every disagreement between the
indicator and CORR, rebuilds each run's published cell, re-ranks the column under CORR and writes the seven
pre-registered verdicts. Only run names, instance ids, trials, classes, counts and public model names go to
results.json; gold answers and prediction tails go to the job log only, for the hand-read.
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import cases101 as C
import grade101 as g

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
KEYS = ("ind", "fnem", "corr")


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


def run_url(suite, run, fname):
    return "%s/runs/%s/%s/%s" % (C.HELM_BASE, suite, urllib.parse.quote(run, safe=":,=@-_."), fname)


def fixture_ok():
    def grades_ok():
        for (gold, pred), want in C.FIX_GRADES:
            r = g.grade_record([gold], pred)
            if (r["ind"], r["fnem"], r["corr"], r["cls"]) != want:
                return False
        return all(g.lone_comma(p) == w for p, w in C.FIX_LONE_COMMA)

    s = g.summarize_run(C.FIX_INSTANCES, C.FIX_PREDS, C.CAP)
    return {
        "grades": grades_ok(),
        "run": all(s[k] == w for k, w in C.FIX_RUN.items()),
        "keys": all(s["keys"][k] == w for k, w in C.FIX_RUN_KEYS.items()),
        "means": all(g.run_mean(s["trials"], k) == w for k, w in C.FIX_RUN_MEANS.items()),
        "group": g.group_em_values(C.FIX_GROUP) == C.FIX_GROUP_VALUES,
        "verdicts": (all(g.verdicts(C.FIX_VERDICT_ON).values())
                     and not any(g.verdicts(C.FIX_VERDICT_PAST).values())),
    }


def load_run(item):
    run, suite = item
    rec = {"run": run, "suite": suite, "model": g.model_of(run)}
    try:
        inst = _json(run_url(suite, run, "instances.json"))
        preds = _json(run_url(suite, run, "display_predictions.json"))
        stats = _json(run_url(suite, run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    s = g.summarize_run(inst, preds, C.CAP)
    gold = {i.get("id"): [((r.get("output") or {}).get("text") or "") for r in i.get("references") or []
                          if "correct" in (r.get("tags") or [])]
            for i in inst if isinstance(i, dict) and i.get("split") == "test"}
    want = {}
    for cls, lst in s["keys"].items():
        k = g.pick(lst, run + "|" + cls)
        if k is not None:
            want[k] = cls
    texts = {}
    for r in preds:
        if isinstance(r, dict) and r.get("perturbation") is None:
            key = (r.get("instance_id"), r.get("train_trial_index", 0))
            if key in want and key not in texts:
                gv = [g.gold_value(x) for x in gold.get(key[0], [])]
                texts[key] = (want[key], " | ".join(str(v) for v in gv), r.get("predicted_text"))
    ni = g.stat_entry(stats, "num_instances")
    rec.update({"summary": s, "texts": texts, "ind_stat": g.stat_entry(stats, g.STAT),
                "num_instances_sum": None if ni is None else ni.get("sum")})
    del inst, preds, stats
    return run, rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    fx = fixture_ok()
    print("[fixture] %s" % fx)
    if not all(fx.values()):
        raise SystemExit("fixture mismatch -- aborting before real data")

    run_suites = _json("%s/releases/%s/runs_to_run_suites.json" % (C.HELM_BASE, C.HELM_RELEASE))
    chosen = g.select_runs(run_suites, C.PREFIX)
    print("[release] %s runs listed=%d" % (C.HELM_RELEASE, len(chosen)))
    try:
        published = g.group_em_values(_json("%s/releases/%s/groups/%s.json" % (C.HELM_BASE, C.HELM_RELEASE,
                                                                                C.GROUP))) or []
        group_err = None
    except Exception as e:  # noqa: BLE001
        published, group_err = [], str(e)[:200]
    print("[group] EM cells published=%d error=%s" % (len(published), group_err))

    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(load_run, sorted(chosen.items())))

    # ----- Run gates -----
    runs_out, inc = {}, {}
    for run in sorted(chosen):
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "error": r["error"]}
            continue
        s = r["summary"]
        im = g.run_mean(s["trials"], "ind")
        reasons = []
        if s["stat_missing"] or s["stat_mismatch"]:
            reasons.append("record_stats")
        nis = r["num_instances_sum"]
        if nis is None or s["counts"]["kept"] != int(round(nis)):
            reasons.append("instances")
        st = r["ind_stat"]
        if st is None or st.get("mean") is None or im is None or abs(float(im) - st["mean"]) > C.TOL_RUN:
            reasons.append("ind_mean")
        runs_out[run] = {"status": "included" if not reasons else "excluded", "reasons": reasons,
                         "model": r["model"], "kept": s["counts"]["kept"], "trials": len(s["trials"]),
                         "stat_missing": s["stat_missing"], "stat_mismatch": s["stat_mismatch"],
                         "classes": s["classes"], "under": s["under"], "over": s["over"],
                         "fnem_gain": s["fnem_gain"], "fnem_loss": s["fnem_loss"], "lone_comma": s["lone_comma"],
                         "cap_records": s["cap_records"], "cap_under": s["cap_under"]}
        if not reasons:
            inc[run] = r
    print("[runs] listed=%d included=%d" % (len(chosen), len(inc)))
    for run in sorted(chosen):
        if runs_out[run]["status"] != "included":
            print("[excluded] %s %s" % (run, runs_out[run].get("reasons") or runs_out[run].get("error")))

    # ----- Pooled totals over included runs -----
    tot = {"records": 0, "ind": 0, "fnem": 0, "corr": 0}
    classes = {c: 0 for c in g.UNDER_CLASSES}
    pooled = {"under": 0, "over": 0, "fnem_gain": 0, "fnem_loss": 0, "lone_comma": 0, "cap_records": 0,
              "cap_under": 0}
    for r in inc.values():
        s = r["summary"]
        for v in s["trials"].values():
            tot["records"] += v["n"]
            for k in KEYS:
                tot[k] += v[k]
        for c, v in s["classes"].items():
            classes[c] += v
        for k in pooled:
            pooled[k] += s[k]
    print("[totals] %s classes=%s %s" % (tot, classes, pooled))

    # ----- Cells (one per run, as HELM's 'Model/adapter' rows) and ranks -----
    cells = {k: {} for k in KEYS}
    for run, r in inc.items():
        for k in KEYS:
            cells[k][run] = g.run_mean(r["summary"]["trials"], k)
    matched = g.match_cells({m: float(v) for m, v in cells["ind"].items()}, published, C.TOL_CELL)
    rp, rc, rf = g.ranks_high(cells["ind"]), g.ranks_high(cells["corr"]), g.ranks_high(cells["fnem"])
    order = sorted(inc)
    tau = g.kendall_tau_b([cells["ind"][m] for m in order], [cells["corr"][m] for m in order])
    tau_fnem = g.kendall_tau_b([cells["ind"][m] for m in order], [cells["fnem"][m] for m in order])
    movers = sorted(m for m in order if abs(rp[m] - rc[m]) >= C.PLACES)
    movers_fnem = sorted(m for m in order if abs(rp[m] - rf[m]) >= C.PLACES)
    rises = {m: cells["corr"][m] - cells["ind"][m] for m in order}
    max_rise = max(rises.values()) if rises else None
    table = [{"run": m, "model": inc[m]["model"], "published": float(cells["ind"][m]),
              "corr": float(cells["corr"][m]), "fnem": float(cells["fnem"][m]), "rise_corr": float(rises[m]),
              "rank_published": rp[m], "rank_corr": rc[m], "rank_fnem": rf[m]}
             for m in sorted(order, key=lambda k: (rp[k], k))]
    print("[cells] matched %d of %d (published %d)" % (matched, len(order), len(published)))
    print("[ranks] tau_b published vs corr=%s fnem=%s movers(>=%d) corr=%d fnem=%d max_rise=%s" % (
        tau, tau_fnem, C.PLACES, len(movers), len(movers_fnem), None if max_rise is None else float(max_rise)))
    for row in table:
        print("[cell] %s" % row)

    stats = {"fixtures": all(fx.values()), "runs_listed": len(chosen), "runs_included": len(inc),
             "cells_matched": matched, "ind_credits": tot["ind"], "under": pooled["under"], "over": pooled["over"],
             "max_rise": max_rise, "movers": len(movers), "tau": tau, "under_classes": classes}
    verdicts = g.verdicts(stats)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, "HELD" if v else "FAILED"))

    # ----- Hand-read lines (stdout only): up to N per class, at most one per run, runs spread by a stable hash -----
    shown = {}
    for run in sorted(inc, key=lambda x: (g.stable_hash(x), x)):
        for key, (cls, gold, pred) in sorted(inc[run]["texts"].items(), key=lambda kv: (kv[1][0], str(kv[0][0]))):
            n = shown.get(cls, 0)
            if n >= C.PRINT_PER_CLASS:
                continue
            shown[cls] = n + 1
            print("[read %s %d] run=%s id=%s trial=%s gold_answer=%s pred_tail=%r" % (
                cls, n + 1, run, key[0], key[1], gold, (pred or "")[-160:]))

    def frac(a, b):
        return None if not b else float(Fraction(a, b))

    out = {
        "audit": 101,
        "slug": "helm-gsm-classic-indicator",
        "dataset": ("Per-instance outputs of HELM Classic release %s (Stanford CRFM): every gsm run listed in "
                    "runs_to_run_suites.json, test split, all trials. Only run names, instance ids, trials, classes, "
                    "counts and public model names are published." % C.HELM_RELEASE),
        "fixture": fx,
        "group_error": group_err,
        "runs_listed": len(chosen),
        "runs_included": len(inc),
        "cells_matched": [matched, len(order)],
        "published_cells": len(published),
        "totals": dict(tot, **pooled, under_share_of_ind=frac(pooled["under"], tot["ind"]),
                       over_share_of_ind=frac(pooled["over"], tot["ind"])),
        "under_classes": classes,
        "tau_b": {"published_vs_corr": tau, "published_vs_fnem": tau_fnem},
        "movers_3plus_corr": movers,
        "movers_3plus_fnem": movers_fnem,
        "max_rise_corr": None if max_rise is None else float(max_rise),
        "verdicts": {k: ("HELD" if v else "FAILED") for k, v in verdicts.items()},
        "table": table,
        "runs": runs_out,
        "note": ("ind = HELM's exact_match_indicator (last space-separated token, compared literally with the gold's "
                 "'N.'); fnem = HELM's final_number_exact_match (HELM Lite's GSM8K metric); corr = the number right "
                 "after the first 'the answer is' in the prediction (else its last number), compared by value with "
                 "the gold's answer. under = corr 1 and ind 0, by class; over = ind 1 and corr 0. lone_comma = "
                 "outputs whose HELM final number is empty (HELM issue #4337). Cells: mean of a run's trial means."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
