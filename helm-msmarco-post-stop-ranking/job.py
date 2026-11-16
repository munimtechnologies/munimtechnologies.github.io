"""Audit 125: HELM Classic's MS MARCO (regular track) RR@10 column, re-computed with each passage's answer-only log
probability.

Downloads every canonical msmarco track=regular run of HELM Classic release v0.4.0 (scenario_state.json for each
passage request's first completion, stored log probability, token list and reference tags; stats.json for the stored
RR@10 and RR@10 (topk=30)), reproduces each run's stored values by re-ranking every query as HELM does, re-ranks with
the log probability cut at the stop sequence, checks the cells against the group page, re-ranks the models and writes
the eight pre-registered verdicts. Only run names, counts, classes, numbers and public model names go to results.json;
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

import cases125 as C
import grade125 as g

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


def fixture_ok():
    s = g.summarize_run(copy.deepcopy(C.FIX_STATE))
    tau_ok = True
    for (xs, ys), want in C.FIX_TAU:
        got = g.kendall_tau_b(xs, ys)
        tau_ok = tau_ok and ((got is None) if want is None else _close(got, want, 1e-12))
    objs, order_want = C.FIX_ORDER
    return {
        "tokens": (all(g.token_bytes(t) == w for t, w in C.FIX_BYTES)
                   and all(g.decode_tokens(ts) == w for ts, w in C.FIX_DECODE)
                   and all(g.keep_count(ts, st) == w for (ts, st), w in C.FIX_KEEP)),
        "records": (all(g.first_completion(r) == w for r, w in C.FIX_FIRST)
                    and all(g.answer_only(c, st) == w for (c, st), w in C.FIX_ANSWER)
                    and all(g.ref_tags(r) == w for r, w in C.FIX_TAGS)),
        "ranking": (all(g.score_key(t, lp) == w for (t, lp), w in C.FIX_SCORE_KEY)
                    and [o["id"] for o in g.model_order(objs, "p")] == order_want
                    and all(g.rr_at(o, k, lim) == w for (o, k, lim), w in C.FIX_RR)
                    and all(g.first_gold_position(o) == w for o, w in C.FIX_FIRST_GOLD)
                    and all(g.gold_outside(o, k) == w for (o, k), w in C.FIX_OUTSIDE)),
        "run": (all(s[k] == w for k, w in C.FIX_RUN.items())
                and all(_close(g.trial_mean(s["trials"], k)[0], v, 1e-12) and g.trial_mean(s["trials"], k)[1] == n
                        for k, (v, n) in C.FIX_TRIAL_MEAN.items())
                and g.run_class(s["rec"]["overrun"], s["rec"]["records"]) == C.FIX_RUN_CLASS_OF_FIXTURE
                and all(g.run_class(o, n) == w for (o, n), w in C.FIX_RUN_CLASS)),
        "names": (all(g.is_selected(r) == w for r, w in C.FIX_NAMES["selected"])
                  and all(g.scenario_of(r) == w for r, w in C.FIX_NAMES["scenario"])
                  and all(g.adapter_of(r) == w for r, w in C.FIX_NAMES["adapter"])
                  and all(g.model_part(r) == w for r, w in C.FIX_NAMES["model"])
                  and g.select_runs(C.FIX_SUITES) == C.FIX_SELECT
                  and all(g.stat_entry(C.FIX_STATS, n, sp) == w for (n, sp), w in C.FIX_STAT_ENTRY)
                  and all(g.slim_hook(copy.deepcopy(d)) == w for d, w in C.FIX_SLIM)),
        "aggregates": (g.ranks_high(C.FIX_RANKS[0]) == C.FIX_RANKS[1] and tau_ok
                       and g.match_cells(C.FIX_MATCH[0], C.FIX_MATCH[1], C.TOL_CELL) == C.FIX_MATCH[2]
                       and g.group_values(C.FIX_GROUP, C.COLUMN) == C.FIX_GROUP_VALUES
                       and g.group_values(C.FIX_GROUP_NO_COLUMN, C.COLUMN) is None
                       and all(g.median(xs) == w for xs, w in C.FIX_MEDIAN)),
        "verdicts": (all(g.verdicts(C.FIX_VERDICT_ON).values())
                     and not any(g.verdicts(C.FIX_VERDICT_PAST).values())),
    }


def load_run(item):
    """Download and score one run; keep only run-level values, counts and the overrun excesses."""
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
        rec.update({
            "tm": {k: g.trial_mean(s["trials"], k) for k in g.TRIAL_KEYS},
            "counts": s["counts"], "rec": s["rec"], "grp": s["grp"], "stops": s["stops"],
            "excess": array.array("d", s["excess"]), "samples": s["samples"],
            "stat": g.stat_entry(stats, C.STAT, g.EVAL_SPLIT),
            "stat_topk": g.stat_entry(stats, C.STAT_TOPK, g.EVAL_SPLIT),
        })
    except Exception as e:  # noqa: BLE001 - unexpected file shape: recorded as a failed run, never patched
        rec["error"] = "parse: " + str(e)[:280]
    del state, stats
    print("[loaded] %s" % run, flush=True)
    return run, rec


def gate(r):
    """Status and reasons of one loaded run: download_failed, included or excluded."""
    if "error" in r:
        return "download_failed", [r["error"]]
    reasons = []
    if not r["grp"]["groups"]:
        reasons.append("no_groups")
    for key, st, name in (("p10", r["stat"], "rr10"), ("pk", r["stat_topk"], "rr10_topk")):
        v, n = r["tm"][key]
        if st is None or st.get("mean") is None:
            reasons.append("%s_missing" % name)
            continue
        if not _close(v, st.get("mean"), C.TOL_RUN):
            reasons.append("%s_mismatch" % name)
        if st.get("count") != n:
            reasons.append("%s_trial_count" % name)
    return ("included" if not reasons else "excluded"), reasons


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
    try:
        published = g.group_values(json.loads(_get("%s/releases/%s/groups/%s.json" % (
            C.HELM_BASE, C.HELM_RELEASE, C.GROUP))), C.COLUMN) or []
        group_err = None
    except Exception as e:  # noqa: BLE001
        published, group_err = [], str(e)[:200]
    print("[release] runs listed=%d, published %s cells=%d, error=%s" % (
        len(chosen), C.COLUMN, len(published), group_err), flush=True)

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
            o.update({"counts": r["counts"], "rec": r["rec"], "grp": r["grp"],
                      "rr10_published": None if r["stat"] is None else r["stat"].get("mean"),
                      "rr10_topk_published": None if r["stat_topk"] is None else r["stat_topk"].get("mean"),
                      "tm": {k: v[0] for k, v in r["tm"].items()}, "trials": r["tm"]["p10"][1]})
        runs_out[run] = o
        if status != "included":
            print("[excluded] %s %s %s" % (run, status, reasons), flush=True)

    # ----- Cells (one run per adapter) -----
    cells = {}
    for run in sorted(chosen):
        r = loaded[run]
        if r["status"] != "included":
            continue
        n = r["rec"]["records"]
        cells[r["adapter"]] = {
            "run": run, "p": r["tm"]["p10"][0], "t": r["tm"]["t10"][0],
            "pk": r["tm"]["pk"][0], "tk": r["tm"]["tk"][0],
            "class": g.run_class(r["rec"]["overrun"], n), "records": n,
            "overrun_records": r["rec"]["overrun"], "overrun_consistent": r["rec"]["overrun_consistent"],
            "lp_mismatch": r["rec"]["lp_mismatch"], "mean_tokens": r["rec"]["tokens"] / n if n else None,
            "groups": r["grp"]["groups"], "groups_rr_changed": r["grp"]["rr_changed"],
            "groups_first_gold_moved": r["grp"]["first_gold_moved"],
            "groups_gold_outside_top30": r["grp"]["gold_outside_topk"], "groups_no_gold": r["grp"]["no_gold"],
            "median_excess": g.median(list(r["excess"])),
        }
    order = sorted(cells)
    pv = {a: cells[a]["p"] for a in order}
    tv = {a: cells[a]["t"] for a in order}
    matched = g.match_cells(pv, published, C.TOL_CELL)
    rp, rt = g.ranks_high(pv), g.ranks_high(tv)
    tau = g.kendall_tau_b([pv[a] for a in order], [tv[a] for a in order])
    movers = sorted(a for a in order if abs(rp[a] - rt[a]) >= C.PLACES)
    over = [a for a in order if cells[a]["class"] == "overrun"]
    delta = {a: tv[a] - pv[a] for a in order}
    pooled_excess = sorted(v for a in over for v in loaded[cells[a]["run"]]["excess"])
    st = {
        "fixtures": all(fx.values()), "runs_listed": len(chosen),
        "runs_included": sum(1 for r in chosen if loaded[r]["status"] == "included"),
        "published": len(published), "matched": matched, "cells": len(order),
        "overrun_set": sorted(g.model_part(a) for a in over), "overrun": len(over),
        "median_excess": g.median(pooled_excess),
        "excess_p10": pooled_excess[int(0.1 * (len(pooled_excess) - 1))] if pooled_excess else None,
        "excess_p90": pooled_excess[int(0.9 * (len(pooled_excess) - 1))] if pooled_excess else None,
        "overrun_records": sum(cells[a]["overrun_records"] for a in over),
        "overrun_consistent": sum(cells[a]["overrun_consistent"] for a in over),
        "delta_hits": sum(1 for a in over if abs(delta[a]) >= C.DELTA),
        "better": sum(1 for a in over if delta[a] >= C.DELTA),
        "worse": sum(1 for a in over if delta[a] <= -C.DELTA),
        "movers": len(movers), "tau": tau,
        "groups_overrun": sum(cells[a]["groups"] for a in over),
        "groups_changed": sum(cells[a]["groups_rr_changed"] for a in over),
        "changed_in_clean_cells": sum(cells[a]["groups_rr_changed"] for a in order if a not in over),
    }
    verdicts = g.verdicts(st)
    print("[stats] %s" % st, flush=True)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, "HELD" if v else "FAILED"))
    table = [dict({"adapter": a, "model": g.model_part(a), "rr10_published": pv[a], "rr10_answer_only": tv[a],
                   "delta": delta[a], "rank_published": rp[a], "rank_answer_only": rt[a],
                   "rr10_top30_published": cells[a]["pk"], "rr10_top30_answer_only": cells[a]["tk"]},
                  **{k: v for k, v in cells[a].items() if k not in ("p", "t", "pk", "tk")})
             for a in sorted(order, key=lambda k: (rp[k], k))]
    for row in table:
        print("[cell] %s" % row)

    # ----- Hand-read lines (stdout only): overrun records from up to PRINT_RUNS runs, by a stable hash -----
    shown = 0
    for run in sorted((r for r in chosen if loaded[r]["status"] == "included"), key=lambda x: (g.stable_hash(x), x)):
        smp = loaded[run]["samples"]
        if not smp or shown >= C.PRINT_RUNS:
            continue
        shown += 1
        x = smp[0]
        print("[read %d] run=%s key=%s gold=%s text=%r tokens=%r kept=%d stored_lp=%.4f answer_lp=%.4f" % (
            shown, run, x["key"], x["gold"], x["text"], x["tokens"], x["kept"], x["stored_lp"], x["answer_lp"]))

    out = {
        "audit": 125,
        "slug": "helm-msmarco-post-stop-ranking",
        "dataset": ("Per-instance outputs of HELM Classic release %s (Stanford CRFM): every canonical msmarco "
                    "track=regular run listed in runs_to_run_suites.json, unperturbed valid-split passage requests, "
                    "all trials. Only run names, counts, classes, numbers and public model names are published."
                    % C.HELM_RELEASE),
        "fixture": fx,
        "group_error": group_err,
        "stats_for_verdicts": st,
        "verdicts": {k: ("HELD" if v else "FAILED") for k, v in verdicts.items()},
        "movers_3plus": movers,
        "table": table,
        "runs": runs_out,
        "note": ("rr10_published = HELM's RR@10 rebuilt from the stored completion log probabilities (HELM's binary "
                 "ranking: 'Yes' answers first, most probable first; 'No' answers next, least probable first; "
                 "anything else last; stable on reference order), mean over queries per trial, mean over trials, "
                 "gated against stats.json within %g together with RR@10 (topk=30). rr10_answer_only = the same "
                 "ranking with each log probability cut where the decoded tokens reach the stop sequence. Class "
                 "overrun: at least half the run's passage records carry tokens past the stop. excess = stored "
                 "minus answer-only log probability. Ranks: higher RR@10 is better." % C.TOL_RUN),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"), ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
