"""Audit 104: is HELM Classic's BoolQ "ECE (10-bin)" computed from the probability of the answer that was scored?

Downloads every canonical BoolQ run of HELM Classic release v0.4.0 (scenario_state.json for the top completion, its
stored log probability and its token list; stats.json for the published ece_10_bin and exact_match), reproduces each
run's published ECE from the stored log probabilities (HELM's max_prob), then recomputes it with each record's
confidence cut at the stop sequence (the answer-only probability), classes every run (overrun / clean), rebuilds the
"ECE (10-bin)" cells, re-ranks and writes the eight pre-registered verdicts. Only run names, instance ids, trials,
classes, counts and public model names go to results.json; completions and tokens go to the job log only.
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import copy
import json
import math
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import cases104 as C
import grade104 as g

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}


def _get(url, tries=4):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=600) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry transient network errors
            last = e
    raise RuntimeError("GET failed after %d tries: %s (%s)" % (tries, url, last))


def run_url(suite, run, fname):
    return "%s/runs/%s/%s/%s" % (C.HELM_BASE, suite, urllib.parse.quote(run, safe=":,=@-_."), fname)


def _close(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


def fixture_ok():
    s = g.summarize_run(copy.deepcopy(C.FIX_STATE))
    tau_ok = True
    for (xs, ys), want in C.FIX_TAU:
        got = g.kendall_tau_b(xs, ys)
        tau_ok = tau_ok and ((got is None) if want is None else _close(got, want, 1e-12))
    ece_ok = all((g.ece_em(p, y, nb) is None) if w is None else _close(g.ece_em(p, y, nb), w, 1e-12)
                 for (p, y, nb), w in C.FIX_ECE)
    return {
        "tokens": (all(g.token_bytes(t) == w for t, w in C.FIX_BYTES)
                   and all(g.decode_tokens(ts) == w for ts, w in C.FIX_DECODE)
                   and all(g.keep_count(ts, st) == w for (ts, st), w in C.FIX_KEEP)
                   and all(g.exact_match(a, b) == w for (a, b), w in C.FIX_EM)),
        "records": (all(g.score_record(gs, c, st) == w for (gs, c, st), w in C.FIX_RECORD)
                    and all(g.top_completion(r) == w for r, w in C.FIX_TOP)),
        "run": (all(s[k] == w for k, w in C.FIX_RUN.items())
                and all(_close(g.run_ece(s["trials"], k, C.NUM_BINS), w, 1e-12) for k, w in C.FIX_RUN_ECE.items())
                and _close(g.run_em(s["trials"]), C.FIX_RUN_EM, 1e-12)
                and g.run_class(s["rec"]["overrun"], s["counts"]["kept"]) == C.FIX_RUN_CLASS_OF_FIXTURE
                and all(g.run_class(o, n) == w for (o, n), w in C.FIX_RUN_CLASS)),
        "ece": all(g.equal_mass_bins(p, nb) == w for (p, nb), w in C.FIX_BINS) and ece_ok,
        "names": (all(g.is_boolq_canonical(r) == w for r, w in C.FIX_NAMES["canonical"])
                  and all(g.adapter_of(r) == w for r, w in C.FIX_NAMES["adapter"])
                  and all(g.model_part(r) == w for r, w in C.FIX_NAMES["model"])
                  and g.select_runs(C.FIX_SUITES) == C.FIX_SELECT
                  and all(g.stat_entry(C.FIX_STATS, n, sp) == w for (n, sp), w in C.FIX_STAT_ENTRY)
                  and all(g.slim_hook(copy.deepcopy(d)) == w for d, w in C.FIX_SLIM)),
        "aggregates": (g.ranks_low(C.FIX_RANKS[0]) == C.FIX_RANKS[1] and tau_ok
                       and g.match_cells(C.FIX_MATCH[0], C.FIX_MATCH[1], C.TOL_CELL) == C.FIX_MATCH[2]
                       and g.group_values(C.FIX_GROUP, C.COLUMN) == C.FIX_GROUP_VALUES
                       and g.group_values(C.FIX_GROUP_NO_COLUMN, C.COLUMN) is None
                       and all(g.median(xs) == w for xs, w in C.FIX_MEDIAN)),
        "verdicts": (all(g.verdicts(C.FIX_VERDICT_ON).values())
                     and not any(g.verdicts(C.FIX_VERDICT_PAST).values())),
    }


def load_run(item):
    run, suite = item
    rec = {"run": run, "suite": suite, "adapter": g.adapter_of(run)}
    try:
        state = json.loads(_get(run_url(suite, run, "scenario_state.json")), object_hook=g.slim_hook)
        stats = json.loads(_get(run_url(suite, run, "stats.json")))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    try:
        s = g.summarize_run(state)
        split = max(s["splits"], key=lambda k: s["splits"][k]) if s["splits"] else None
        rec.update({"summary": s, "split": split,
                    "ece_stat": g.stat_entry(stats, "ece_10_bin", split),
                    "em_stat": g.stat_entry(stats, "exact_match", split)})
    except Exception as e:  # noqa: BLE001 - unexpected file shape: recorded as a failed run, never patched
        rec["error"] = "parse: " + str(e)[:280]
    del state, stats
    print("[loaded] %s" % run, flush=True)
    return run, rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    fx = fixture_ok()
    print("[fixture] %s" % fx, flush=True)
    if not all(fx.values()):
        raise SystemExit("fixture mismatch -- aborting before real data")

    run_suites = json.loads(_get("%s/releases/%s/runs_to_run_suites.json" % (C.HELM_BASE, C.HELM_RELEASE)))
    chosen = g.select_runs(run_suites)
    print("[release] %s canonical boolq runs listed=%d suites=%s" % (
        C.HELM_RELEASE, len(chosen), sorted(set(chosen.values()))), flush=True)
    try:
        published = g.group_values(json.loads(_get("%s/releases/%s/groups/%s.json" % (
            C.HELM_BASE, C.HELM_RELEASE, C.GROUP))), C.COLUMN) or []
        group_err = None
    except Exception as e:  # noqa: BLE001
        published, group_err = [], str(e)[:200]
    print("[group] %s cells published=%d error=%s" % (C.COLUMN, len(published), group_err), flush=True)

    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(load_run, sorted(chosen.items())))

    # ----- Run gates and classes -----
    runs_out, inc = {}, {}
    for run in sorted(chosen):
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "error": r["error"]}
            continue
        s = r["summary"]
        n = s["counts"]["kept"]
        ece_p, ece_t, em = g.run_ece(s["trials"], "p", C.NUM_BINS), g.run_ece(s["trials"], "t", C.NUM_BINS), \
            g.run_em(s["trials"])
        es, ms = r["ece_stat"], r["em_stat"]
        cls = g.run_class(s["rec"]["overrun"], n)
        o = {"suite": r["suite"], "split": r["split"], "class": cls, "counts": s["counts"], "rec": s["rec"],
             "stops": s["stops"], "trials": len(s["trials"]),
             "ece_published": None if es is None else es.get("mean"), "ece_p": ece_p, "ece_t": ece_t,
             "em_published": None if ms is None else ms.get("mean"), "em": em,
             "overrun_share": (s["rec"]["overrun"] / n) if n else None,
             "mean_tokens": (s["rec"]["tokens"] / n) if n else None,
             "median_excess": g.median(s["excess"])}
        if es is None or es.get("mean") is None:
            o.update({"status": "no_ece", "reasons": ["no_ece"]})
            runs_out[run] = o
            continue
        reasons = []
        if not n:
            reasons.append("no_records")
        if not _close(ece_p, es.get("mean"), C.TOL_RUN):
            reasons.append("ece_mismatch")
        if ms is None or not _close(em, ms.get("mean"), C.TOL_RUN):
            reasons.append("em_mismatch")
        if es.get("count") != len(s["trials"]):
            reasons.append("trial_count")
        o.update({"status": "included" if not reasons else "excluded", "reasons": reasons})
        runs_out[run] = o
        if not reasons:
            inc[run] = dict(r, cls=cls, out=o)
    with_ece = [run for run in chosen if runs_out[run].get("status") in ("included", "excluded", "download_failed")]
    print("[runs] listed=%d with_ece=%d included=%d" % (len(chosen), len(with_ece), len(inc)), flush=True)
    for run in sorted(chosen):
        o = runs_out[run]
        if o["status"] != "included":
            print("[excluded] %s status=%s reasons=%s error=%s ece_pub=%s ece_p=%s em_pub=%s em=%s" % (
                run, o["status"], o.get("reasons"), o.get("error"), o.get("ece_published"), o.get("ece_p"),
                o.get("em_published"), o.get("em")))

    # ----- Pooled record totals by run class -----
    tot = {}
    for r in inc.values():
        t = tot.setdefault(r["cls"], {"runs": 0, "records": 0, "overrun": 0, "consistent": 0,
                                      "overrun_consistent": 0, "excess_le_minus_ln2": 0})
        s = r["summary"]
        t["runs"] += 1
        t["records"] += s["counts"]["kept"]
        for k in ("overrun", "consistent", "overrun_consistent"):
            t[k] += s["rec"][k]
        t["excess_le_minus_ln2"] += sum(1 for x in s["excess"] if x <= -math.log(2))
    pooled_excess = sorted(x for r in inc.values() if r["cls"] == "overrun" for x in r["summary"]["excess"])
    for c, t in sorted(tot.items()):
        print("[totals] %s %s" % (c, t), flush=True)
    print("[excess] overrun-run records=%d median=%s p10=%s p90=%s" % (
        len(pooled_excess), g.median(pooled_excess),
        pooled_excess[int(0.1 * (len(pooled_excess) - 1))] if pooled_excess else None,
        pooled_excess[int(0.9 * (len(pooled_excess) - 1))] if pooled_excess else None), flush=True)

    # ----- Cells (one run per adapter), matching, ranks -----
    cells = {}
    for run, r in inc.items():
        cells.setdefault(r["adapter"], []).append(run)
    cells = {ad: runs[0] for ad, runs in cells.items() if len(runs) == 1}
    order = sorted(cells)
    pv = {ad: inc[cells[ad]]["out"]["ece_p"] for ad in order}
    tv = {ad: inc[cells[ad]]["out"]["ece_t"] for ad in order}
    matched = g.match_cells(pv, published, C.TOL_CELL)
    rp, rt = g.ranks_low(pv), g.ranks_low(tv)
    tau = g.kendall_tau_b([pv[a] for a in order], [tv[a] for a in order])
    movers = sorted(a for a in order if abs(rp[a] - rt[a]) >= C.PLACES)
    over = [a for a in order if inc[cells[a]]["cls"] == "overrun"]
    excess_hits = sum(1 for a in over if (inc[cells[a]]["out"]["median_excess"] or 0.0) <= C.EXCESS)
    delta = {a: tv[a] - pv[a] for a in order}
    delta_hits = sum(1 for a in over if abs(delta[a]) >= C.DELTA)
    better = sum(1 for a in over if abs(delta[a]) >= C.DELTA and delta[a] < 0)
    worse = sum(1 for a in over if abs(delta[a]) >= C.DELTA and delta[a] > 0)
    table = [{"adapter": a, "model": g.model_part(a), "run": cells[a], "class": inc[cells[a]]["cls"],
              "em": inc[cells[a]]["out"]["em"], "ece_published": pv[a], "ece_answer_only": tv[a],
              "delta": delta[a], "rank_published": rp[a], "rank_answer_only": rt[a],
              "overrun_share": inc[cells[a]]["out"]["overrun_share"],
              "mean_tokens": inc[cells[a]]["out"]["mean_tokens"],
              "median_excess": inc[cells[a]]["out"]["median_excess"]}
             for a in sorted(order, key=lambda k: (rp[k], k))]
    n_cls = {c: sum(1 for a in order if inc[cells[a]]["cls"] == c) for c in ("overrun", "clean")}
    print("[cells] %d cells, matched %d of %d published; classes %s" % (len(order), matched, len(published), n_cls))
    print("[ranks] tau_b(P,T)=%s movers(>=%d)=%d overrun adapters=%d excess_hits=%d delta_hits=%d better=%d "
          "worse=%d" % (tau, C.PLACES, len(movers), len(over), excess_hits, delta_hits, better, worse), flush=True)
    for row in table:
        print("[cell] %s" % row)

    ov = tot.get("overrun") or {"records": 0, "overrun": 0, "overrun_consistent": 0}
    st = {"fixtures": all(fx.values()), "runs_with_ece": len(with_ece), "runs_included": len(inc),
          "cells": len(order), "matched": matched, "overrun_adapters": len(over), "excess_hits": excess_hits,
          "delta_hits": delta_hits, "overrun_records": ov["overrun"], "overrun_consistent": ov["overrun_consistent"],
          "movers": len(movers), "tau": tau, "better": better, "worse": worse}
    verdicts = g.verdicts(st)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, "HELD" if v else "FAILED"))

    # ----- Hand-read lines (stdout only): up to N runs per class, spread by a stable hash -----
    shown = {}
    for run in sorted(inc, key=lambda x: (g.stable_hash(x), x)):
        c = inc[run]["cls"]
        smp = inc[run]["summary"]["samples"]
        if not smp or shown.get(c, 0) >= C.PRINT_PER_CLASS:
            continue
        shown[c] = shown.get(c, 0) + 1
        x = smp[0]
        print("[read %s %d] run=%s id=%s trial=%s em=%s text=%r tokens=%r kept=%d stored_lp=%.4f P=%.4f T=%.4f" % (
            c, shown[c], run, x["key"][0], x["key"][1], x["em"], x["text"], x["tokens"], x["kept"], x["stored_lp"],
            x["p"], x["t"]))

    out = {
        "audit": 104,
        "slug": "helm-boolq-post-stop-calibration",
        "dataset": ("Per-instance outputs of HELM Classic release %s (Stanford CRFM): every canonical boolq run listed "
                    "in runs_to_run_suites.json, unperturbed eval-split records, all trials. Only run names, counts, "
                    "classes and public model names are published." % C.HELM_RELEASE),
        "fixture": fx,
        "group_error": group_err,
        "published_cells": len(published),
        "runs_listed": len(chosen),
        "runs_with_ece": len(with_ece),
        "runs_included": len(inc),
        "totals_by_run_class": tot,
        "overrun_records_median_excess": g.median(pooled_excess),
        "cells": len(order),
        "matched": matched,
        "adapter_classes": n_cls,
        "tau_b_published_vs_answer_only": tau,
        "movers_3plus": movers,
        "table": table,
        "stats_for_verdicts": st,
        "verdicts": {k: ("HELD" if v else "FAILED") for k, v in verdicts.items()},
        "runs": runs_out,
        "note": ("P = HELM's max_prob, exp(stored log probability of the top completion); ece_p = HELM's ece_10_bin "
                 "rebuilt from P and exact_match (equal-mass 10 bins per trial, mean over trials) and gated against "
                 "stats.json within %g. T = exp(sum of the log probabilities of the tokens before the first token "
                 "whose decoded text reaches a stop sequence); ece_answer_only uses T. Class overrun: at least half "
                 "the records carry tokens past the stop. excess = stored minus answer-only log probability." %
                 C.TOL_RUN),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
