"""Audit 124: HELM Classic's IMDB, CivilComments and RAFT "ECE (10-bin)" columns, re-computed with the probability of
the answer that was scored.

Downloads every canonical imdb / civil_comments / raft run of HELM Classic release v0.4.0 (scenario_state.json for
the top completion, its stored log probability and its token list; stats.json for the stored ece_10_bin and
exact_match per split), reproduces each run's stored ECE per split from HELM's max_prob, recomputes it with each
record's confidence cut at the stop sequence, pools the runs of each adapter into its published cell (9
CivilComments demographics, 11 RAFT subsets), checks the cells against the group pages, re-ranks and writes the
eight pre-registered verdicts. Only run names, counts, classes, numbers and public model names go to results.json;
completions and tokens go to the job log only.
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import array
import copy
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import cases124 as C
import grade124 as g

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research)"}


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


def _split_ok(got, want):
    if sorted(got) != sorted(want):
        return False
    return all(_close(got[k][0], want[k][0], 1e-12) and got[k][1] == want[k][1] for k in want)


def fixture_ok():
    s = g.summarize_run(copy.deepcopy(C.FIX_STATE))
    tau_ok = True
    for (xs, ys), want in C.FIX_TAU:
        got = g.kendall_tau_b(xs, ys)
        tau_ok = tau_ok and ((got is None) if want is None else _close(got, want, 1e-12))
    ece_ok = all((g.ece_em(p, y, nb) is None) if w is None else _close(g.ece_em(p, y, nb), w, 1e-12)
                 for (p, y, nb), w in C.FIX_ECE)
    pooled_ok = all((g.pooled_value(pr) is None) if w is None else _close(g.pooled_value(pr), w, 1e-12)
                    for pr, w in C.FIX_POOLED)
    return {
        "tokens": (all(g.token_bytes(t) == w for t, w in C.FIX_BYTES)
                   and all(g.decode_tokens(ts) == w for ts, w in C.FIX_DECODE)
                   and all(g.keep_count(ts, st) == w for (ts, st), w in C.FIX_KEEP)
                   and all(g.exact_match(a, b) == w for (a, b), w in C.FIX_EM)),
        "records": (all(g.score_record(gs, c, st) == w for (gs, c, st), w in C.FIX_RECORD)
                    and all(g.top_completion(r) == w for r, w in C.FIX_TOP)),
        "run": (all(s[k] == w for k, w in C.FIX_RUN.items())
                and all(_split_ok(g.split_values(s["trials"], k, C.NUM_BINS), w)
                        for k, w in C.FIX_SPLIT_VALUES.items())
                and all(_close(g.mean_conf(s["trials"], k), w, 1e-12) for k, w in C.FIX_MEAN_CONF.items())
                and g.run_class(s["rec"]["overrun"], s["counts"]["kept"]) == C.FIX_RUN_CLASS_OF_FIXTURE
                and all(g.run_class(o, n) == w for (o, n), w in C.FIX_RUN_CLASS) and pooled_ok),
        "ece": all(g.equal_mass_bins(p, nb) == w for (p, nb), w in C.FIX_BINS) and ece_ok,
        "names": (all(g.is_canonical(r) == w for r, w in C.FIX_NAMES["canonical"])
                  and all(g.scenario_of(r) == w for r, w in C.FIX_NAMES["scenario"])
                  and all(g.adapter_of(r) == w for r, w in C.FIX_NAMES["adapter"])
                  and all(g.model_part(r) == w for r, w in C.FIX_NAMES["model"])
                  and all(g.is_flagged(a) == w for a, w in C.FIX_NAMES["flagged"])
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
    """Download and score one run; keep only the per-split values, counts and the overrun excesses."""
    run, suite = item
    rec = {"run": run, "suite": suite, "scenario": g.scenario_of(run), "adapter": g.adapter_of(run)}
    try:
        state = json.loads(_get(run_url(suite, run, "scenario_state.json")), object_hook=g.slim_hook)
        stats = json.loads(_get(run_url(suite, run, "stats.json")))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    try:
        s = g.summarize_run(state)
        tr = s["trials"]
        sv = {k: g.split_values(tr, k, C.NUM_BINS) for k in ("p", "t", "em")}
        rec.update({
            "sv": sv, "counts": s["counts"], "rec": s["rec"], "splits": s["splits"], "stops": s["stops"],
            "excess": array.array("d", s["excess"]), "samples": s["samples"],
            "conf_p_sum": sum(x for v in tr.values() for x in v["p"]),
            "conf_t_sum": sum(x for v in tr.values() for x in v["t"]),
            "ece_stat": {sp: g.stat_entry(stats, "ece_10_bin", sp) for sp in sv["p"]},
            "em_stat": {sp: g.stat_entry(stats, "exact_match", sp) for sp in sv["p"]},
        })
    except Exception as e:  # noqa: BLE001 - unexpected file shape: recorded as a failed run, never patched
        rec["error"] = "parse: " + str(e)[:280]
    del state, stats
    print("[loaded] %s" % run, flush=True)
    return run, rec


def gate(r):
    """Status and reasons of one loaded run: download_failed, no_ece, included or excluded."""
    if "error" in r:
        return "download_failed", [r["error"]]
    es = r["ece_stat"]
    if not r["counts"]["kept"]:
        return ("no_ece", ["no_records"]) if not any(es.values()) else ("excluded", ["no_records"])
    if not any(v is not None and v.get("mean") is not None for v in es.values()):
        return "no_ece", ["no_ece"]
    reasons = []
    for sp, (v, n) in sorted(r["sv"]["p"].items()):
        st = es.get(sp)
        if st is None or st.get("mean") is None:
            reasons.append("ece_missing:%s" % sp)
            continue
        if not _close(v, st.get("mean"), C.TOL_RUN):
            reasons.append("ece_mismatch:%s" % sp)
        if st.get("count") != n:
            reasons.append("trial_count:%s" % sp)
        ms = r["em_stat"].get(sp)
        em = r["sv"]["em"].get(sp)
        if ms is None or em is None or not _close(em[0], ms.get("mean"), C.TOL_RUN):
            reasons.append("em_mismatch:%s" % sp)
    return ("included" if not reasons else "excluded"), reasons


def pairs(runs, key):
    return [vn for r in runs for _, vn in sorted(r["sv"][key].items())]


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
    published, group_err = {}, {}
    for sc in g.SCENARIOS:
        n_sc = sum(1 for r in chosen if g.scenario_of(r) == sc)
        try:
            published[sc] = g.group_values(json.loads(_get("%s/releases/%s/groups/%s.json" % (
                C.HELM_BASE, C.HELM_RELEASE, C.GROUPS[sc]))), C.COLUMN) or []
            group_err[sc] = None
        except Exception as e:  # noqa: BLE001
            published[sc], group_err[sc] = [], str(e)[:200]
        print("[release] %s: canonical runs listed=%d, published %s cells=%d, error=%s" % (
            sc, n_sc, C.COLUMN, len(published[sc]), group_err[sc]), flush=True)

    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(load_run, sorted(chosen.items())))

    # ----- Run gates -----
    runs_out = {}
    for run in sorted(chosen):
        r = loaded[run]
        status, reasons = gate(r)
        r["status"] = status
        o = {"status": status, "reasons": reasons, "suite": r["suite"]}
        if "error" not in r:
            o.update({"kept": r["counts"]["kept"], "overrun": r["rec"]["overrun"], "splits": r["splits"],
                      "ece_published": {sp: (None if st is None else st.get("mean")) for sp, st in
                                        r["ece_stat"].items()},
                      "ece_p": {sp: vn[0] for sp, vn in r["sv"]["p"].items()},
                      "ece_t": {sp: vn[0] for sp, vn in r["sv"]["t"].items()}})
        runs_out[run] = o
        if status in ("excluded", "download_failed"):
            print("[excluded] %s %s %s" % (run, status, reasons), flush=True)

    # ----- Cells per scenario -----
    by, tables, cells_out, flag = {}, {}, {}, {"records": 0, "consistent": 0}
    for sc in g.SCENARIOS:
        sc_runs = [run for run in chosen if g.scenario_of(run) == sc]
        with_ece = [run for run in sc_runs if loaded[run]["status"] in ("included", "excluded", "download_failed")]
        included = [run for run in sc_runs if loaded[run]["status"] == "included"]
        groups = {}
        for run in sc_runs:
            groups.setdefault(loaded[run]["adapter"], []).append(run)
        cells, skipped = {}, {}
        for ad, runs in sorted(groups.items()):
            st = [loaded[x]["status"] for x in runs]
            if any(s in ("excluded", "download_failed") for s in st):
                skipped[ad] = "incomplete"
                continue
            inc = [loaded[x] for x in runs if loaded[x]["status"] == "included"]
            if not inc:
                skipped[ad] = "no_ece"
                continue
            kept = sum(x["counts"]["kept"] for x in inc)
            ov = sum(x["rec"]["overrun"] for x in inc)
            cells[ad] = {
                "runs": len(runs), "runs_with_ece": len(inc),
                "p": g.pooled_value(pairs(inc, "p")), "t": g.pooled_value(pairs(inc, "t")),
                "em": g.pooled_value(pairs(inc, "em")),
                "class": g.run_class(ov, kept), "records": kept, "overrun_records": ov,
                "overrun_consistent": sum(x["rec"]["overrun_consistent"] for x in inc),
                "mean_tokens": sum(x["rec"]["tokens"] for x in inc) / kept if kept else None,
                "mean_conf_p": sum(x["conf_p_sum"] for x in inc) / kept if kept else None,
                "mean_conf_t": sum(x["conf_t_sum"] for x in inc) / kept if kept else None,
                "median_excess": g.median([v for x in inc for v in x["excess"]]),
                "flagged": g.is_flagged(ad),
            }
        order = sorted(cells)
        pv = {a: cells[a]["p"] for a in order}
        tv = {a: cells[a]["t"] for a in order}
        matched = g.match_cells(pv, published[sc], C.TOL_CELL)
        rp, rt = g.ranks_low(pv), g.ranks_low(tv)
        tau = g.kendall_tau_b([pv[a] for a in order], [tv[a] for a in order])
        movers = sorted(a for a in order if abs(rp[a] - rt[a]) >= C.PLACES)
        over = [a for a in order if cells[a]["class"] == "overrun"]
        delta = {a: tv[a] - pv[a] for a in order}
        pooled_excess = sorted(v for a in over for r in groups[a] if loaded[r]["status"] == "included"
                               for v in loaded[r]["excess"])
        for a in over:
            if not cells[a]["flagged"]:
                flag["records"] += cells[a]["overrun_records"]
                flag["consistent"] += cells[a]["overrun_consistent"]
        by[sc] = {
            "runs_listed": len(sc_runs), "runs_with_ece": len(with_ece), "runs_included": len(included),
            "cells": len(order), "skipped_cells": skipped, "published": len(published[sc]), "matched": matched,
            "overrun": len(over), "clean": len(order) - len(over),
            "delta_hits": sum(1 for a in over if abs(delta[a]) >= C.DELTA),
            "better": sum(1 for a in over if delta[a] <= -C.DELTA),
            "worse": sum(1 for a in over if delta[a] >= C.DELTA),
            "better10": sum(1 for a in over if delta[a] <= -0.10),
            "median_excess": g.median(pooled_excess),
            "excess_p10": pooled_excess[int(0.1 * (len(pooled_excess) - 1))] if pooled_excess else None,
            "excess_p90": pooled_excess[int(0.9 * (len(pooled_excess) - 1))] if pooled_excess else None,
            "overrun_records": len(pooled_excess),
            "tau": tau, "movers": len(movers),
        }
        tables[sc] = [dict({"adapter": a, "model": g.model_part(a), "ece_published": pv[a], "ece_answer_only": tv[a],
                            "delta": delta[a], "rank_published": rp[a], "rank_answer_only": rt[a]},
                           **{k: v for k, v in cells[a].items() if k not in ("p", "t")})
                      for a in sorted(order, key=lambda k: (rp[k], k))]
        cells_out[sc] = movers
        print("[scenario] %s %s" % (sc, {k: v for k, v in by[sc].items() if k != "skipped_cells"}), flush=True)
        print("[skipped] %s %s" % (sc, skipped), flush=True)
        for row in tables[sc]:
            print("[cell] %s %s" % (sc, row))

    st = {"fixtures": all(fx.values()), "flag_records": flag["records"], "flag_consistent": flag["consistent"],
          "by": by}
    verdicts = g.verdicts(st)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, "HELD" if v else "FAILED"))

    # ----- Hand-read lines (stdout only): overrun records from up to N runs per scenario, by a stable hash -----
    shown = {}
    for run in sorted((r for r in chosen if loaded[r]["status"] == "included"), key=lambda x: (g.stable_hash(x), x)):
        sc = loaded[run]["scenario"]
        smp = loaded[run]["samples"]
        if not smp or shown.get(sc, 0) >= C.PRINT_PER_SCENARIO:
            continue
        shown[sc] = shown.get(sc, 0) + 1
        x = smp[0]
        print("[read %s %d] run=%s key=%s em=%s text=%r tokens=%r kept=%d stored_lp=%.4f P=%.4f T=%.4f" % (
            sc, shown[sc], run, x["key"], x["em"], x["text"], x["tokens"], x["kept"], x["stored_lp"], x["p"], x["t"]))

    out = {
        "audit": 124,
        "slug": "helm-classic-post-stop-calibration",
        "dataset": ("Per-instance outputs of HELM Classic release %s (Stanford CRFM): every canonical imdb, "
                    "civil_comments and raft run listed in runs_to_run_suites.json, unperturbed eval-split records, "
                    "all trials. Only run names, counts, classes, numbers and public model names are published."
                    % C.HELM_RELEASE),
        "fixture": fx,
        "group_error": group_err,
        "stats_for_verdicts": st,
        "verdicts": {k: ("HELD" if v else "FAILED") for k, v in verdicts.items()},
        "movers_3plus": cells_out,
        "tables": tables,
        "runs": runs_out,
        "note": ("P = HELM's max_prob, exp(stored log probability of the top completion); ece_p = HELM's ece_10_bin "
                 "rebuilt from P and exact_match per (split, trial), mean over a split's trials, gated against "
                 "stats.json within %g. T = exp(sum of the log probabilities of the tokens before the first token "
                 "whose decoded text reaches a stop sequence); ece_answer_only uses T. A cell pools the adapter's "
                 "included runs and splits as HELM merges stats (sum of mean x count over sum of counts). Class "
                 "overrun: at least half the cell's records carry tokens past the stop. excess = stored minus "
                 "answer-only log probability. flagged = model families whose kept tokens did not decode to the "
                 "scored text in audit 104 (T5 11B, UL2, Llama 2 7B, YaLM)." % C.TOL_RUN),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"), ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
