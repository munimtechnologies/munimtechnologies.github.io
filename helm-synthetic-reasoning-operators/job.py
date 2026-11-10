"""Does HELM Classic's "Synthetic reasoning (abstract symbols)" column credit answers with the wrong operators?
(audit 99)

Reads HELM Classic release v0.4.0 (runs_to_run_suites.json), takes every synthetic_reasoning run it lists (3 modes x
the models), downloads each run's instances.json, display_predictions.json and stats.json, re-grades every test record
of every trial with a transcription of HELM's quasi_exact_match (the column's main metric) and exact_match, and with an
operator-aware grade (quasi-exact AND the same sequence of + - * = characters). It then rebuilds each model's
published cell (the mean of its 9 trial-level means), checks it against the group page, recomputes the cell with the
operator-aware grade, re-ranks the column and reports the pre-registered verdicts.

Gates before any verdict: the hand-traced fixtures match; at least 200 runs listed; at least 90% of runs included
(downloaded; every test record's stored quasi_exact_match reproduced; the number of kept records equals HELM's
num_instances sum; our quasi-exact and exact run means equal stats.json's within 1e-6); at least 90% of models' cells
match a published EM cell within 1e-9. Only run names, instance ids, trials, classes, counts and public model names
are written to the outputs; gold and model texts are printed to the job log only, for the hand-read.
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import cases99 as C
import grade99 as g

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
    s = g.summarize_run(C.FIX_INSTANCES, C.FIX_PREDS)

    def grades_ok():
        for (gold, pred), want in C.FIX_GRADES:
            r = g.grade_record([gold], pred)
            if (r["em"], r["qem"], r["oa"], r["cls"]) != want:
                return False
        (golds, pred), want = C.FIX_MULTI
        r = g.grade_record(golds, pred)
        return (r["em"], r["qem"], r["oa"], r["cls"]) == want

    tau_ok = True
    for (xs, ys), want in C.FIX_TAU:
        got = g.kendall_tau_b(xs, ys)
        tau_ok = tau_ok and ((got is None) if want is None else (got is not None and abs(got - want) < 1e-12))
    return {
        "normalize": all(g.normalize_text(t) == w for t, w in C.FIX_NORMALIZE),
        "grades": grades_ok(),
        "model_mode": all(g.model_of(r) == m and g.mode_of(r) == d for r, m, d in C.FIX_MODEL_MODE),
        "select": g.select_runs(C.FIX_SUITES, C.PREFIX) == C.FIX_SUITES_OUT,
        "run_summary": all(s[k] == w for k, w in C.FIX_RUN_TARGET.items()),
        "run_means": all(g.run_mean(s["trials"], k) == w for k, w in C.FIX_RUN_MEANS.items()),
        "cell": g.cell(C.FIX_CELL[0], "qem") == C.FIX_CELL[1],
        "stats": all(g.stat_entry(C.FIX_STATS, n) == w for n, w in C.FIX_STAT_TARGET.items()),
        "ranks": g.ranks_high(C.FIX_RANKS_IN) == C.FIX_RANKS_OUT,
        "tau": tau_ok,
        "group": (g.group_em_values(C.FIX_GROUP) == C.FIX_GROUP_VALUES
                  and g.group_em_values(C.FIX_GROUP_NO_COL) is None),
        "match": g.match_cells(*C.FIX_MATCH[0]) == C.FIX_MATCH[1],
        "verdicts": all(g.predictions99(*a, C.THRESHOLDS) == w for a, w in C.FIX_V_CASES),
    }


def load_run(item):
    run, suite = item
    rec = {"run": run, "suite": suite, "model": g.model_of(run), "mode": g.mode_of(run)}
    try:
        inst = _json(run_url(suite, run, "instances.json"))
        preds = _json(run_url(suite, run, "display_predictions.json"))
        stats = _json(run_url(suite, run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    s = g.summarize_run(inst, preds)
    # keep a few texts for the hand-read (log only)
    gold = {i.get("id"): [((r.get("output") or {}).get("text") or "") for r in i.get("references") or []
                          if "correct" in (r.get("tags") or [])]
            for i in inst if isinstance(i, dict) and i.get("split") == "test"}
    want = {(iid, t) for iid, t, _ in s["blind"][:3]} | set(s["other_norm"][:1])
    texts = {}
    for r in preds:
        if isinstance(r, dict) and r.get("perturbation") is None:
            key = (r.get("instance_id"), r.get("train_trial_index", 0))
            if key in want and key not in texts:
                texts[key] = (" | ".join(gold.get(key[0], [])), r.get("predicted_text"))
    ni = g.stat_entry(stats, "num_instances")
    rec.update({"summary": s, "texts": texts, "qem_stat": g.stat_entry(stats, g.STAT_QEM),
                "em_stat": g.stat_entry(stats, g.STAT_EM),
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
    print("[release] %s runs listed=%d suites=%s" % (C.HELM_RELEASE, len(chosen), sorted(set(chosen.values()))))
    try:
        group_doc = _json("%s/releases/%s/groups/%s.json" % (C.HELM_BASE, C.HELM_RELEASE, C.GROUP))
        published = g.group_em_values(group_doc) or []
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
        qm, em = g.run_mean(s["trials"], "qem"), g.run_mean(s["trials"], "em")
        oam = g.run_mean(s["trials"], "oa")
        reasons = []
        if s["stat_missing"] or s["stat_mismatch"]:
            reasons.append("record_stats")
        nis = r["num_instances_sum"]
        if nis is None or s["counts"]["kept"] != int(round(nis)):
            reasons.append("instances")
        qs, es = r["qem_stat"], r["em_stat"]
        if qs is None or qs.get("mean") is None or qm is None or abs(float(qm) - qs["mean"]) > C.TOL_RUN:
            reasons.append("qem_mean")
        if es is None or es.get("mean") is None or em is None or abs(float(em) - es["mean"]) > C.TOL_RUN:
            reasons.append("em_mean")
        row = {"status": "included" if not reasons else "excluded", "reasons": reasons, "model": r["model"],
               "mode": r["mode"], "suite": r["suite"], "counts": s["counts"],
               "trials": {str(k): v for k, v in sorted(s["trials"].items())},
               "stat_missing": s["stat_missing"], "stat_mismatch": s["stat_mismatch"],
               "published_qem": None if qs is None else qs.get("mean"),
               "published_em": None if es is None else es.get("mean"),
               "qem": None if qm is None else float(qm), "em": None if em is None else float(em),
               "oa": None if oam is None else float(oam),
               "blind": len(s["blind"]), "blind_classes": s["classes"], "other_norm": len(s["other_norm"]),
               "qem_not_em": s["qem_not_em"]}
        runs_out[run] = row
        if not reasons:
            inc[run] = r
    n_inc = len(inc)
    inc_share = Fraction(n_inc, len(chosen)) if chosen else Fraction(0)
    print("[runs] listed=%d included=%d (%.4f)" % (len(chosen), n_inc, float(inc_share)))
    for run in sorted(chosen):
        if runs_out[run]["status"] != "included":
            print("[excluded] %s %s" % (run, runs_out[run].get("reasons") or runs_out[run].get("error")))

    # ----- Model cells -----
    by_model = {}
    for run in chosen:
        by_model.setdefault(g.model_of(run), []).append(run)
    cells_pub, cells_oa, cells_em, complete = {}, {}, {}, []
    for m, runs in sorted(by_model.items()):
        if all(x in inc for x in runs) and {g.mode_of(x) for x in runs} == set(C.MODES):
            tl = [inc[x]["summary"]["trials"] for x in runs]
            cells_pub[m], cells_oa[m], cells_em[m] = g.cell(tl, "qem"), g.cell(tl, "oa"), g.cell(tl, "em")
            complete.append(m)
    matched = g.match_cells({m: float(v) for m, v in cells_pub.items()}, published, C.TOL_CELL)
    cell_share = Fraction(matched, len(by_model)) if by_model else Fraction(0)
    print("[cells] models=%d complete=%d matched_to_published=%d" % (len(by_model), len(complete), matched))
    p1_parts = {"fixtures": all(fx.values()), "runs": len(chosen) >= C.MIN_RUNS,
                "runs_included": inc_share >= C.MIN_RUNS_INCLUDED, "cells_matched": cell_share >= C.MIN_CELLS_MATCHED}
    print("[P1] %s" % p1_parts)
    if inc_share < C.ABORT_RUNS_INCLUDED:
        with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
            json.dump({"audit": 99, "aborted": True, "fixture": fx, "p1_parts": p1_parts, "group_error": group_err,
                       "runs": runs_out}, fh, indent=1, ensure_ascii=True)
        raise SystemExit("reproduction gate failed -- aborting (diagnostics in results.json)")

    # ----- Census over included runs -----
    tot = {"records": 0, "em": 0, "qem": 0, "oa": 0, "blind": 0, "other_norm": 0, "qem_not_em": 0}
    classes = {c: 0 for c in g.BLIND_CLASSES}
    by_mode = {m: {"runs": 0, "records": 0, "qem": 0, "blind": 0, "em": 0, "oa": 0} for m in C.MODES}
    for run, r in inc.items():
        s = r["summary"]
        rec = sum(v["n"] for v in s["trials"].values())
        q = sum(v["qem"] for v in s["trials"].values())
        e = sum(v["em"] for v in s["trials"].values())
        o = sum(v["oa"] for v in s["trials"].values())
        tot["records"] += rec
        tot["qem"] += q
        tot["em"] += e
        tot["oa"] += o
        tot["blind"] += len(s["blind"])
        tot["other_norm"] += len(s["other_norm"])
        tot["qem_not_em"] += s["qem_not_em"]
        for c, v in s["classes"].items():
            classes[c] += v
        bm = by_mode.setdefault(r["mode"], {"runs": 0, "records": 0, "qem": 0, "blind": 0, "em": 0, "oa": 0})
        bm["runs"] += 1
        bm["records"] += rec
        bm["qem"] += q
        bm["em"] += e
        bm["oa"] += o
        bm["blind"] += len(s["blind"])
    tot["blind_share_of_qem"] = float(Fraction(tot["blind"], tot["qem"])) if tot["qem"] else None
    tot["blind_classes"] = classes
    for bm in by_mode.values():
        bm["blind_share_of_qem"] = float(Fraction(bm["blind"], bm["qem"])) if bm["qem"] else None
    print("[totals] %s" % tot)
    print("[by mode] %s" % by_mode)

    # ----- Ranks over complete models -----
    rp, ro = g.ranks_high(cells_pub), g.ranks_high(cells_oa)
    falls = {m: cells_pub[m] - cells_oa[m] for m in complete}
    max_fall = max(falls.values()) if falls else None
    movers = sorted(m for m in complete if abs(rp[m] - ro[m]) >= C.THRESHOLDS["P5_places"])
    order = sorted(complete)
    tau = g.kendall_tau_b([cells_pub[m] for m in order], [cells_oa[m] for m in order]) if len(order) > 1 else None
    table = [{"model": m, "published": float(cells_pub[m]), "operator_aware": float(cells_oa[m]),
              "exact": float(cells_em[m]), "fall": float(falls[m]), "rank_published": rp[m], "rank_operator_aware": ro[m]}
             for m in sorted(complete, key=lambda k: (rp[k], k))]
    print("[ranks] complete=%d movers(>=%d places)=%d tau_b=%s max_fall=%s" % (
        len(complete), C.THRESHOLDS["P5_places"], len(movers), tau, None if max_fall is None else float(max_fall)))
    for row in table:
        print("[cell] %s" % row)

    mode_shares = {m: (v["blind"], v["qem"]) for m, v in by_mode.items()}
    verdicts = g.predictions99(tot["blind"], tot["qem"], mode_shares, max_fall, len(movers), tau, tot["qem_not_em"],
                               C.THRESHOLDS)
    verdicts["P1_structural"] = all(p1_parts.values())
    for name in sorted(verdicts):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    numbers = {"P2_blind_of_qem_credits": [tot["blind"], tot["qem"]],
               "P3_mode_shares": {m: list(v) for m, v in mode_shares.items()},
               "P4_max_cell_fall": None if max_fall is None else float(max_fall),
               "P5_models_moving_3plus": len(movers), "P6_tau_b": tau,
               "P7_blind_of_qem_not_em": [tot["blind"], tot["qem_not_em"]]}
    print("[numbers] %s" % numbers)

    # ----- Hand-read lines (stdout only) -----
    k = 0
    for run in sorted(inc):
        for key, (gold, pred) in sorted(inc[run]["texts"].items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
            if key in set(inc[run]["summary"]["other_norm"]):
                continue
            k += 1
            if k <= C.PRINT_BLIND:
                cls = next(c for i, t, c in inc[run]["summary"]["blind"] if (i, t) == key)
                print("[blind %d] run=%s id=%s trial=%s class=%s gold=%r pred=%r" % (k, run, key[0], key[1], cls,
                                                                                     gold, (pred or "")[:120]))
    k = 0
    for run in sorted(inc):
        for key in inc[run]["summary"]["other_norm"][:1]:
            k += 1
            if k <= C.PRINT_OTHER and key in inc[run]["texts"]:
                gold, pred = inc[run]["texts"][key]
                print("[other-norm %d] run=%s id=%s trial=%s gold=%r pred=%r" % (k, run, key[0], key[1], gold,
                                                                                 (pred or "")[:120]))

    flips = [{"run": run, "instance_id": i, "trial": t, "class": c}
             for run in sorted(inc) for i, t, c in inc[run]["summary"]["blind"]]
    out = {
        "audit": 99,
        "slug": "helm-synthetic-reasoning-operators",
        "dataset": ("Per-instance outputs of HELM Classic release %s (Stanford CRFM): every synthetic_reasoning run "
                    "listed in runs_to_run_suites.json, test split, all trials. Only run names, instance ids, trials, "
                    "classes, counts and public model names are published." % C.HELM_RELEASE),
        "fixture": fx,
        "p1_parts": p1_parts,
        "group_error": group_err,
        "runs_listed": len(chosen),
        "runs_included": [n_inc, len(chosen)],
        "models": len(by_model),
        "models_complete": len(complete),
        "cells_matched": [matched, len(by_model)],
        "published_cells": len(published),
        "totals": tot,
        "by_mode": by_mode,
        "table": table,
        "movers_3plus": movers,
        "tau_b": tau,
        "predictions": verdicts,
        "prediction_numbers": numbers,
        "runs": runs_out,
        "note": ("qem = HELM's quasi_exact_match (the column's main metric, shown as EM); em = HELM's exact_match; "
                 "oa = operator-aware: quasi-exact AND the same sequence of + - * = characters as the gold. blind = "
                 "quasi-exact credits that are not operator-aware (classes: ops_missing, ops_reordered, ops_other). "
                 "A cell is the mean of a model's trial-level means over the three modes. Ranks: higher is better, "
                 "1 + number of models strictly higher."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "flips.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 99, "note": "Every quasi-exact credit that is not operator-aware, by run, instance id, "
                   "trial and class; no text.", "flips": flips}, fh, ensure_ascii=True)
    print("[done] wrote results.json and flips.json (%d blind credits)" % len(flips))


if __name__ == "__main__":
    main()
