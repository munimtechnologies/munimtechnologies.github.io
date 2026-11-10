"""Audit 100: does HELM Classic's Dyck column credit closing sequences whose only right bracket is the last one?

Downloads every dyck_language run of HELM Classic release v0.4.0, re-grades every test record of every trial with
HELM's exact_match_indicator (transcribed; must reproduce every stored score), a strict grade (the whole closing
sequence, whitespace ignored) and a lenient grade (the prediction's brackets equal the gold sequence; other text
forgiven), classes every indicator credit that is not strict, rebuilds each run's published cell, re-ranks the column
under the lenient grade and writes the seven pre-registered verdicts. Only run names, instance ids, trials, classes,
counts and public model names go to results.json; gold and prediction texts go to the job log only, for the hand-read.
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import cases100 as C
import grade100 as g

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}


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
            if (r["ind"], r["strict"], r["lenient"], r["cls"]) != want:
                return False
        return True

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
                texts[key] = (want[key], " | ".join(gold.get(key[0], [])), r.get("predicted_text"))
    ni = g.stat_entry(stats, "num_instances")
    rec.update({"summary": s, "texts": texts, "ind_stat": g.stat_entry(stats, g.STAT),
                "num_instances_sum": None if ni is None else ni.get("sum")})
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
                         "classes": s["classes"], "under": s["under"], "cap_records": s["cap_records"],
                         "cap_wrong": s["cap_wrong"]}
        if not reasons:
            inc[run] = r
    print("[runs] listed=%d included=%d" % (len(chosen), len(inc)))
    for run in sorted(chosen):
        if runs_out[run]["status"] != "included":
            print("[excluded] %s %s" % (run, runs_out[run].get("reasons") or runs_out[run].get("error")))

    # ----- Pooled totals over included runs -----
    tot = {"records": 0, "ind": 0, "strict": 0, "lenient": 0}
    classes = {c: 0 for c in g.CLASSES}
    by_depth = {}
    under = cap_records = cap_wrong = 0
    for r in inc.values():
        s = r["summary"]
        for v in s["trials"].values():
            tot["records"] += v["n"]
            for k in ("ind", "strict", "lenient"):
                tot[k] += v[k]
        for c, v in s["classes"].items():
            classes[c] += v
        for d, v in s["by_depth"].items():
            bd = by_depth.setdefault(d, {"records": 0, "ind": 0, "strict": 0, "lenient": 0, "wrong": 0})
            for k in bd:
                bd[k] += v[k]
        under += s["under"]
        cap_records += s["cap_records"]
        cap_wrong += s["cap_wrong"]
    wrong = sum(classes[c] for c in g.WRONG_CLASSES)
    print("[totals] %s classes=%s wrong=%d under=%d cap_records=%d cap_wrong=%d" % (
        tot, classes, wrong, under, cap_records, cap_wrong))
    for d in sorted(by_depth):
        print("[by depth] %s %s" % (d, by_depth[d]))

    # ----- Cells (one per run, as HELM's 'Model/adapter' rows) and ranks -----
    cells = {"ind": {}, "strict": {}, "lenient": {}}
    for run, r in inc.items():
        for k in cells:
            cells[k][run] = g.run_mean(r["summary"]["trials"], k)
    matched = g.match_cells({m: float(v) for m, v in cells["ind"].items()}, published, C.TOL_CELL)
    rp, rl, rs = g.ranks_high(cells["ind"]), g.ranks_high(cells["lenient"]), g.ranks_high(cells["strict"])
    order = sorted(inc)
    tau = g.kendall_tau_b([cells["ind"][m] for m in order], [cells["lenient"][m] for m in order])
    tau_strict = g.kendall_tau_b([cells["ind"][m] for m in order], [cells["strict"][m] for m in order])
    movers = sorted(m for m in order if abs(rp[m] - rl[m]) >= C.PLACES)
    falls = {m: cells["ind"][m] - cells["lenient"][m] for m in order}
    max_fall = max(falls.values()) if falls else None
    table = [{"run": m, "model": inc[m]["model"], "published": float(cells["ind"][m]),
              "lenient": float(cells["lenient"][m]), "strict": float(cells["strict"][m]),
              "fall_lenient": float(falls[m]), "rank_published": rp[m], "rank_lenient": rl[m], "rank_strict": rs[m]}
             for m in sorted(order, key=lambda k: (rp[k], k))]
    print("[cells] matched %d of %d (published %d)" % (matched, len(order), len(published)))
    print("[ranks] tau_b published vs lenient=%s strict=%s movers(>=%d)=%d max_fall=%s" % (
        tau, tau_strict, C.PLACES, len(movers), None if max_fall is None else float(max_fall)))
    for row in table:
        print("[cell] %s" % row)

    stats = {"fixtures": all(fx.values()), "runs_listed": len(chosen), "runs_included": len(inc),
             "cells_matched": matched, "ind_credits": tot["ind"], "wrong": wrong, "by_depth": by_depth,
             "max_fall": max_fall, "movers": len(movers), "tau": tau, "missing_leading": classes["missing_leading"]}
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
            print("[read %s %d] run=%s id=%s trial=%s gold=%r pred=%r" % (cls, n + 1, run, key[0], key[1], gold,
                                                                         (pred or "")[:80]))

    def frac(a, b):
        return None if not b else float(Fraction(a, b))

    out = {
        "audit": 100,
        "slug": "helm-dyck-last-token",
        "dataset": ("Per-instance outputs of HELM Classic release %s (Stanford CRFM): every dyck_language run listed in "
                    "runs_to_run_suites.json, test split, all trials. Only run names, instance ids, trials, classes, "
                    "counts and public model names are published." % C.HELM_RELEASE),
        "fixture": fx,
        "group_error": group_err,
        "runs_listed": len(chosen),
        "runs_included": len(inc),
        "cells_matched": [matched, len(order)],
        "published_cells": len(published),
        "totals": dict(tot, wrong=wrong, under=under, cap_records=cap_records, cap_wrong=cap_wrong,
                       wrong_share_of_ind=frac(wrong, tot["ind"]), format_only=classes["format_only"]),
        "classes": classes,
        "by_depth": {str(d): dict(v, wrong_share_of_ind=frac(v["wrong"], v["ind"])) for d, v in sorted(by_depth.items())},
        "tau_b": {"published_vs_lenient": tau, "published_vs_strict": tau_strict},
        "movers_3plus_lenient": movers,
        "max_fall_lenient": None if max_fall is None else float(max_fall),
        "verdicts": {k: ("HELD" if v else "FAILED") for k, v in verdicts.items()},
        "table": table,
        "runs": runs_out,
        "note": ("ind = HELM's exact_match_indicator (last space-separated token only); strict = whole closing "
                 "sequence, whitespace ignored; lenient = the prediction's bracket characters equal the gold sequence. "
                 "wrong = indicator credits that are not lenient (classes missing_leading, extra_leading, "
                 "wrong_same_length, other). under = lenient answers HELM scored 0. Cells: mean of a run's trial "
                 "means."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
