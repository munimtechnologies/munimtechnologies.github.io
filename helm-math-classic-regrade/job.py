"""Audit 102: how often do HELM Classic's two MATH columns grade an answer wrongly?

Downloads every math run of HELM Classic release v0.4.0 that belongs to the "MATH" (no chain of thought, official
examples) or "MATH (chain-of-thoughts)" column, re-grades every test record of every trial with HELM's metric
(transcribed; must reproduce every stored score) and with the corrected grade, classes every disagreement, rebuilds
each adapter's published cell (mean of its 7 subject runs), re-ranks both columns and writes the eight pre-registered
verdicts. Only run names, instance ids, trials, classes, counts and public model names go to results.json; gold
answers and prediction tails go to the job log only, for the hand-read.
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import cases102 as C
import grade102 as g

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
    def same(r, want):
        return (r["h"], r["a"], r["cls"]) == want

    reg = g.summarize_run("reg", C.FIX_REG_INSTANCES, C.FIX_REG_PREDS, C.CAP["reg"])
    cot = g.summarize_run("cot", C.FIX_COT_INSTANCES, C.FIX_COT_PREDS, C.CAP["cot"])
    names = (all(g.run_mode(r) == w for r, w in C.FIX_NAMES["mode"])
             and all(g.subject_of(r) == w for r, w in C.FIX_NAMES["subject"])
             and all(g.adapter_of(r) == w for r, w in C.FIX_NAMES["adapter"])
             and all(g.model_part(r) == w for r, w in C.FIX_NAMES["model"])
             and g.select_runs(C.FIX_SUITES) == C.FIX_SELECT)
    tau_ok = True
    for (xs, ys), want in C.FIX_TAU:
        got = g.kendall_tau_b(xs, ys)
        tau_ok = tau_ok and ((got is None) if want is None else (got is not None and abs(got - want) < 1e-12))
    return {
        "reg": all(same(g.grade_reg(gd, p), w) for (gd, p), w in C.FIX_REG),
        "cot": all(same(g.grade_one("cot", gd, p), w) for (gd, p), w in C.FIX_COT),
        "record": all(g.grade_record(m, gs, p) == w for (m, gs, p), w in C.FIX_RECORD),
        "names": names,
        "reg_run": (all(reg[k] == w for k, w in C.FIX_REG_RUN.items())
                    and all(g.run_mean(reg["trials"], k) == w for k, w in C.FIX_REG_MEANS.items())),
        "cot_run": (all(cot[k] == w for k, w in C.FIX_COT_RUN.items())
                    and all(g.run_mean(cot["trials"], k) == w for k, w in C.FIX_COT_MEANS.items())),
        "cells": g.build_cells(C.FIX_CELL_RUNS, C.FIX_CELL_SUBJECTS) == C.FIX_CELLS,
        "aggregates": (g.ranks_high(C.FIX_RANKS[0]) == C.FIX_RANKS[1] and tau_ok
                       and g.match_cells(C.FIX_MATCH[0], C.FIX_MATCH[1], C.TOL_CELL) == C.FIX_MATCH[2]
                       and g.group_values(C.FIX_GROUP) == C.FIX_GROUP_VALUES),
        "verdicts": (all(g.verdicts(C.FIX_VERDICT_ON).values())
                     and not any(g.verdicts(C.FIX_VERDICT_PAST).values())),
    }


def load_run(item):
    run, (mode, suite) = item
    rec = {"run": run, "suite": suite, "mode": mode, "adapter": g.adapter_of(run), "subject": g.subject_of(run)}
    try:
        inst = _json(run_url(suite, run, "instances.json"))
        preds = _json(run_url(suite, run, "display_predictions.json"))
        stats = _json(run_url(suite, run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    s = g.summarize_run(mode, inst, preds, C.CAP[mode])
    gold = g.golds_of(inst)
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
                golds = gold.get(key[0], [])
                ga = " | ".join(str(x if mode == "reg" else g.get_answer(x)) for x in golds)
                pred = (r.get("predicted_text") or "").strip()
                cands = " | ".join(str(g.grade_one(mode, x, pred).get("candidate")) for x in golds)
                texts[key] = (want[key], ga, cands, pred)
    ni = g.stat_entry(stats, "num_instances")
    rec.update({"summary": s, "texts": texts, "stat": g.stat_entry(stats, g.STAT[mode]),
                "num_instances_sum": None if ni is None else ni.get("sum")})
    del inst, preds, stats
    return run, rec


def frac(a, b):
    return None if not b else float(Fraction(a, b))


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
    chosen = g.select_runs(run_suites)
    n_mode = {m: sum(1 for v in chosen.values() if v[0] == m) for m in g.MODES}
    print("[release] %s runs listed=%d by mode=%s" % (C.HELM_RELEASE, len(chosen), n_mode))
    published, group_err = {}, {}
    for m in g.MODES:
        try:
            published[m] = g.group_values(_json("%s/releases/%s/groups/%s.json" % (
                C.HELM_BASE, C.HELM_RELEASE, C.GROUPS[m]))) or []
            group_err[m] = None
        except Exception as e:  # noqa: BLE001
            published[m], group_err[m] = [], str(e)[:200]
        print("[group] %s Equivalent cells published=%d error=%s" % (m, len(published[m]), group_err[m]))

    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(load_run, sorted(chosen.items())))

    # ----- Run gates -----
    runs_out, inc = {}, {}
    for run in sorted(chosen):
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "mode": r["mode"], "error": r["error"]}
            continue
        s = r["summary"]
        hm = g.run_mean(s["trials"], "h")
        reasons = []
        if s["stat_missing"] or s["stat_mismatch"]:
            reasons.append("record_stats")
        nis = r["num_instances_sum"]
        if nis is None or s["counts"]["kept"] != int(round(nis)):
            reasons.append("instances")
        st = r["stat"]
        if st is None or st.get("mean") is None or hm is None or abs(float(hm) - st["mean"]) > C.TOL_RUN:
            reasons.append("run_mean")
        if r["subject"] not in C.SUBJECTS:
            reasons.append("subject")
        flips = [[k[0], k[1], cls] for cls, lst in sorted(s["keys"].items()) for k in lst][:C.FLIPS_PER_RUN]
        runs_out[run] = {"status": "included" if not reasons else "excluded", "reasons": reasons, "mode": r["mode"],
                         "kept": s["counts"]["kept"], "trials": len(s["trials"]), "stat_missing": s["stat_missing"],
                         "stat_mismatch": s["stat_mismatch"], "h": sum(v["h"] for v in s["trials"].values()),
                         "a": sum(v["a"] for v in s["trials"].values()), "up": s["up"], "down": s["down"],
                         "cap_records": s["cap_records"], "cap_up": s["cap_up"], "flips": flips}
        if not reasons:
            inc[run] = r
    n_inc = {m: sum(1 for r in inc.values() if r["mode"] == m) for m in g.MODES}
    print("[runs] listed=%d included=%d by mode=%s" % (len(chosen), len(inc), n_inc))
    for run in sorted(chosen):
        if runs_out[run]["status"] != "included":
            print("[excluded] %s %s" % (run, runs_out[run].get("reasons") or runs_out[run].get("error")))

    # ----- Pooled totals per column -----
    tot = {}
    for m in g.MODES:
        t = {"records": 0, "h": 0, "a": 0, "cap_records": 0, "cap_up": 0,
             "up": {c: 0 for c in g.UP[m]}, "down": {c: 0 for c in g.DOWN[m]}}
        for r in inc.values():
            if r["mode"] != m:
                continue
            s = r["summary"]
            for v in s["trials"].values():
                t["records"] += v["n"]
                t["h"] += v["h"]
                t["a"] += v["a"]
            for c, v in s["up"].items():
                t["up"][c] += v
            for c, v in s["down"].items():
                t["down"][c] += v
            t["cap_records"] += s["cap_records"]
            t["cap_up"] += s["cap_up"]
        t["n_up"] = sum(t["up"].values())
        t["n_down"] = sum(t["down"].values())
        t["net"] = t["a"] - t["h"]
        t["net_share"] = frac(t["net"], t["records"])
        t["up_share"] = frac(t["n_up"], t["records"])
        tot[m] = t
        print("[totals] %s %s" % (m, t))

    # ----- Cells (one per adapter: mean of its 7 subject runs), matching, ranks -----
    cells_all = g.build_cells({run: {"mode": r["mode"], "adapter": r["adapter"], "subject": r["subject"],
                                     "trials": r["summary"]["trials"]} for run, r in inc.items()}, C.SUBJECTS)
    col = {}
    for m in g.MODES:
        cells = {ad: v for (mm, ad), v in cells_all.items() if mm == m}
        hv = {ad: v["h"] for ad, v in cells.items()}
        av = {ad: v["a"] for ad, v in cells.items()}
        matched = g.match_cells({ad: float(v) for ad, v in hv.items()}, published[m], C.TOL_CELL)
        rp, ra = g.ranks_high(hv), g.ranks_high(av)
        order = sorted(cells)
        tau = g.kendall_tau_b([hv[a] for a in order], [av[a] for a in order])
        movers = sorted(a for a in order if abs(rp[a] - ra[a]) >= C.PLACES)
        rises = {a: av[a] - hv[a] for a in order}
        table = [{"adapter": a, "model": g.model_part(a), "published": float(hv[a]), "corrected": float(av[a]),
                  "rise": float(rises[a]), "rank_published": rp[a], "rank_corrected": ra[a]}
                 for a in sorted(order, key=lambda k: (rp[k], k))]
        col[m] = {"cells": len(order), "matched": matched, "published_cells": len(published[m]), "tau_b": tau,
                  "movers_3plus": movers, "max_rise": max(rises.values()) if rises else None,
                  "hash_rises": sorted(a for a in order if "stop=hash" in a and rises[a] > 0),
                  "table": table, "_h": hv, "_a": av}
        print("[cells] %s matched %d of %d (published %d)" % (m, matched, len(order), len(published[m])))
        print("[ranks] %s tau_b=%s movers(>=%d)=%d max_rise=%s hash_rises=%s" % (
            m, tau, C.PLACES, len(movers), None if not rises else float(max(rises.values())),
            col[m]["hash_rises"]))
        for row in table:
            print("[cell %s] %s" % (m, row))

    # ----- Cross-column (descriptive): does chain of thought beat the regular prompt, before and after? -----
    reg_by = {g.model_part(a): a for a in col["reg"]["_h"]}
    cot_by = {g.model_part(a): a for a in col["cot"]["_h"]}
    both = sorted(set(reg_by) & set(cot_by))
    cross = {"models": len(both), "cot_wins_published": 0, "cot_wins_corrected": 0, "sign_changes": []}
    for mp in both:
        gh = col["cot"]["_h"][cot_by[mp]] - col["reg"]["_h"][reg_by[mp]]
        ga = col["cot"]["_a"][cot_by[mp]] - col["reg"]["_a"][reg_by[mp]]
        cross["cot_wins_published"] += 1 if gh > 0 else 0
        cross["cot_wins_corrected"] += 1 if ga > 0 else 0
        if (gh > 0) != (ga > 0) or (gh < 0) != (ga < 0):
            cross["sign_changes"].append({"model": mp, "gap_published": float(gh), "gap_corrected": float(ga)})
    print("[cross] %s" % cross)

    stats = {"fixtures": all(fx.values()), "runs_listed": len(chosen), "runs_included": len(inc),
             "cells_reg": col["reg"]["cells"], "cells_cot": col["cot"]["cells"],
             "matched_reg": col["reg"]["matched"], "matched_cot": col["cot"]["matched"],
             "cot_n": tot["cot"]["records"], "cot_net": tot["cot"]["net"], "cot_up_classes": tot["cot"]["up"],
             "cot_movers": len(col["cot"]["movers_3plus"]), "cot_tau": col["cot"]["tau_b"],
             "reg_n": tot["reg"]["records"], "reg_up": tot["reg"]["n_up"], "reg_net": tot["reg"]["net"],
             "hash_rise": bool(col["reg"]["hash_rises"])}
    verdicts = g.verdicts(stats)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, "HELD" if v else "FAILED"))

    # ----- Hand-read lines (stdout only): up to N per mode and class, at most one per run, spread by a hash -----
    shown = {}
    for run in sorted(inc, key=lambda x: (g.stable_hash(x), x)):
        m = inc[run]["mode"]
        for key, (cls, ga, cand, pred) in sorted(inc[run]["texts"].items(), key=lambda kv: (kv[1][0], str(kv[0]))):
            n = shown.get((m, cls), 0)
            if n >= C.PRINT_PER_CLASS:
                continue
            shown[(m, cls)] = n + 1
            print("[read %s %s %d] run=%s id=%s trial=%s gold_answer=%r candidate=%r pred_tail=%r" % (
                m, cls, n + 1, run, key[0], key[1], ga, cand, pred[-200:]))

    out = {
        "audit": 102,
        "slug": "helm-math-classic-regrade",
        "dataset": ("Per-instance outputs of HELM Classic release %s (Stanford CRFM): every math run of the 'MATH' "
                    "(math_regular) and 'MATH (chain-of-thoughts)' (math_chain_of_thought) columns listed in "
                    "runs_to_run_suites.json, test split, all trials. Only run names, instance ids, trials, classes, "
                    "counts and public model names are published." % C.HELM_RELEASE),
        "fixture": fx,
        "group_error": group_err,
        "runs_listed": len(chosen),
        "runs_listed_by_mode": n_mode,
        "runs_included": len(inc),
        "runs_included_by_mode": n_inc,
        "totals": tot,
        "columns": {m: {k: v for k, v in col[m].items() if not k.startswith("_")} for m in g.MODES},
        "cross_column": cross,
        "verdicts": {k: ("HELD" if v else "FAILED") for k, v in verdicts.items()},
        "runs": runs_out,
        "note": ("reg = the 'MATH' column (math_equiv on a short answer); cot = 'MATH (chain-of-thoughts)' "
                 "(math_equiv_chain_of_thought). h = HELM's metric, transcribed and gated against every stored "
                 "record score; a = the corrected grade (cot: audit 91's grade; reg: the answer up to its first "
                 "unescaped '$', credited when HELM's is_equiv holds or both sides are the same rational number). "
                 "Cells: mean over the 7 subject runs of each run's mean of trial means. flips per run are "
                 "[instance id, trial, class], at most %d per run." % C.FLIPS_PER_RUN),
    }

    def enc(o):
        if isinstance(o, Fraction):
            return float(o)
        raise TypeError(type(o))

    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True, default=enc)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
