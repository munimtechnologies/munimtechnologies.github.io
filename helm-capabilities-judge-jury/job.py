"""Audit 106: who judges HELM Capabilities' WildBench and Omni-MATH columns, and does it matter?

Downloads every wildbench: and omni_math: run listed in HELM Capabilities release v1.15.0 (display_predictions.json for
the per-record jury annotations, falling back to scenario_state.json if they carry none; stats.json for the published
run mean), reproduces every run mean and published cell from the judges' values, records which judges rated each run,
measures each judge's offset from the other judges and its own-family offset (self-preference), re-scores every cell
with the GPT judge alone and with the jury common to all runs, and writes the eight pre-registered verdicts.
Only run names, public model names, judge names and numbers go to results.json; no model or judge text is read out.
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import gzip
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import cases106 as C
import grade106 as g

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}


def _get(url, tries=4):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=600) as r:
                body = r.read()
            if body[:2] == b"\x1f\x8b":
                body = gzip.decompress(body)
            return body
        except Exception as e:  # noqa: BLE001 - retry transient network errors
            last = e
    raise RuntimeError("GET failed after %d tries: %s (%s)" % (tries, url, last))


def run_url(suite, run, fname):
    return "%s/runs/%s/%s/%s" % (C.HELM_BASE, suite, urllib.parse.quote(run, safe=":,=@-_."), fname)


def _close(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


def fixture_ok():
    wb = g.summarize_run(json.loads(json.dumps(C.FIX_WB_PREDS)), C.WB)
    om = g.summarize_run(json.loads(json.dumps(C.FIX_OM_PREDS)), C.OM)
    n, cov = g.judge_coverage(wb["records"])
    tau_ok = True
    for (xs, ys), want in C.FIX_TAU:
        got = g.kendall_tau_b(xs, ys)
        tau_ok = tau_ok and ((got is None) if want is None else _close(got, want, 1e-12))
    sp_ok = all(_close(g.self_preference(C.FIX_SP_ROWS, j)[0], d, 1e-12)
                and g.self_preference(C.FIX_SP_ROWS, j)[1:3] == (a, b) for j, (d, a, b) in C.FIX_SP.items())
    return {
        "parse": all(g.parse_annotation(json.loads(json.dumps(a)), g.SCENARIOS[s]) == w
                     for (a, s), w in C.FIX_PARSE),
        "wildbench_run": (wb["counts"] == C.FIX_WB_COUNTS and (wb["stored_n"], wb["mismatch"]) == C.FIX_WB_STORED
                          and [r["h"] for r in wb["records"]] == C.FIX_WB_H
                          and g.run_mean(wb["records"], lambda r: r["h"]) == C.FIX_WB_MEAN
                          and (n, cov) == C.FIX_WB_COVERAGE
                          and all(g.present_judges(n, cov, sh) == w for sh, w in C.FIX_WB_PRESENT.items())
                          and g.judge_offsets(wb["records"], ["claude", "gpt", "llama"]) == C.FIX_WB_OFFSETS
                          and all(g.run_mean(wb["records"], lambda r, nm=nm: g.jury_score(r, nm)) == m
                                  and sum(1 for r in wb["records"] if g.jury_fallback(r, nm)) == f
                                  for nm, (m, f) in C.FIX_WB_JURY.items())),
        "omni_run": (om["counts"] == C.FIX_OM_COUNTS and (om["stored_n"], om["mismatch"]) == C.FIX_OM_STORED
                     and _close(g.run_mean(om["records"], lambda r: r["h"]), C.FIX_OM_MEAN, 1e-12)
                     and g.judge_offsets(om["records"], ["claude", "gpt", "llama"]) == C.FIX_OM_OFFSETS),
        "state": g.predictions_from_state(json.loads(json.dumps(C.FIX_STATE))) == C.FIX_STATE_PREDS,
        "families": (all(g.judge_family(a) == w for a, w in C.FIX_JUDGE_FAMILY)
                     and all(g.model_part(a) == w for a, w in C.FIX_MODEL)
                     and all(g.model_family(a) == w for a, w in C.FIX_MODEL_FAMILY)
                     and all(g.composition_check(s, n_, c, C.LAST_SUITE, C.FULL_SHARE) == w
                             for (s, n_, c), w in C.FIX_COMPOSITION) and sp_ok),
        "names": ({k: g.select_runs(C.FIX_SUITES, sc["prefix"]) for k, sc in g.SCENARIOS.items()} == C.FIX_SELECT
                  and all(g.stat_entry(C.FIX_STATS, nm, sp) == w for (nm, sp), w in C.FIX_STAT_ENTRY)),
        "aggregates": (g.group_values(C.FIX_GROUP, C.WB["column"]) == C.FIX_GROUP_VALUES
                       and g.ranks_high(C.FIX_RANKS[0]) == C.FIX_RANKS[1] and tau_ok
                       and g.match_cells(C.FIX_MATCH[0], C.FIX_MATCH[1], C.TOL_CELL) == C.FIX_MATCH[2]),
        "verdicts": (all(g.verdicts(C.FIX_VERDICT_ON).values())
                     and not any(g.verdicts(C.FIX_VERDICT_PAST).values())),
    }


def load_run(item):
    (scen_name, run), suite = item
    scen = g.SCENARIOS[scen_name]
    rec = {"scenario": scen_name, "run": run, "suite": suite, "model": g.model_part(run), "source": "display"}
    try:
        stats = json.loads(_get(run_url(suite, run, "stats.json")))
        preds = json.loads(_get(run_url(suite, run, "display_predictions.json")))
        s = g.summarize_run(preds, scen)
        del preds
        if s["counts"]["kept"] == 0:
            state = json.loads(_get(run_url(suite, run, "scenario_state.json")))
            s = g.summarize_run(g.predictions_from_state(state), scen)
            del state
            rec["source"] = "scenario_state"
        rec.update({"summary": s, "stat": g.stat_entry(stats, scen["stat"], C.SPLIT),
                    "cell_stat": g.stat_entry(stats, scen["cell_stat"], C.SPLIT)})
    except Exception as e:  # noqa: BLE001 - recorded as a failed run, never patched
        rec["error"] = str(e)[:300]
    print("[loaded] %s %s %s" % (scen_name, run, rec.get("error", rec["source"])), flush=True)
    return (scen_name, run), rec


def cell_of(scen_name, mean):
    return g.rescale_wb(mean) if scen_name == "wildbench" else mean


def analyse(scen_name, chosen, loaded, published):
    scen = g.SCENARIOS[scen_name]
    runs_out, inc = {}, {}
    for run in sorted(chosen):
        r = loaded[(scen_name, run)]
        if "error" in r:
            runs_out[run] = {"model": r["model"], "suite": r["suite"], "status": "download_failed",
                             "error": r["error"]}
            continue
        s = r["summary"]
        recs = s["records"]
        kept = s["counts"]["kept"]
        mean = g.run_mean(recs, lambda x: x["h"])
        pub = None if r["stat"] is None else r["stat"].get("mean")
        n, cov = g.judge_coverage(recs)
        reasons = []
        if not kept:
            reasons.append("no_records")
        if s["counts"]["unscored"] > C.UNSCORED_SHARE * kept:
            reasons.append("unscored")
        if s["stored_n"] and s["mismatch"] > C.STORED_MISMATCH * s["stored_n"]:
            reasons.append("record_mismatch")
        if not _close(mean, pub, C.TOL_RUN):
            reasons.append("mean_mismatch")
        present = g.present_judges(n, cov, C.PRESENT_SHARE)
        offs = g.judge_offsets(recs, present) if len(present) == 3 else None
        o = {"model": r["model"], "suite": r["suite"], "family": g.model_family(r["model"]), "source": r["source"],
             "counts": s["counts"], "stored_n": s["stored_n"], "mismatch": s["mismatch"], "published": pub,
             "repro": mean, "cell": cell_of(scen_name, mean),
             "published_cell_stat": None if r["cell_stat"] is None else r["cell_stat"].get("mean"),
             "non_empty": n, "coverage": cov, "present": present,
             "composition_ok": g.composition_check(r["suite"], n, cov, C.LAST_SUITE, C.FULL_SHARE),
             "offsets": offs, "status": "included" if not reasons else "excluded", "reasons": reasons}
        runs_out[run] = o
        if not reasons:
            inc[run] = dict(o, records=recs)
    print("[runs] %s listed=%d included=%d" % (scen_name, len(chosen), len(inc)), flush=True)
    for run in sorted(chosen):
        o = runs_out[run]
        if o["status"] != "included":
            print("[excluded] %s %s %s" % (scen_name, run, {k: o.get(k) for k in (
                "status", "reasons", "error", "counts", "stored_n", "mismatch", "published", "repro")}), flush=True)

    # ----- Jury composition -----
    comp_runs = sorted(inc)
    comp_ok = bool(comp_runs) and all(inc[r]["composition_ok"] for r in comp_runs) and any(
        inc[r]["suite"] == C.LAST_SUITE for r in comp_runs)
    by_suite = {}
    for r in comp_runs:
        key = (inc[r]["suite"], tuple(inc[r]["present"]))
        by_suite[key] = by_suite.get(key, 0) + 1
    for (suite, present), k in sorted(by_suite.items()):
        print("[jury] %s suite=%s judges=%s runs=%d" % (scen_name, suite, list(present), k), flush=True)
    for r in comp_runs:
        if not inc[r]["composition_ok"]:
            print("[jury-off] %s %s suite=%s n=%d coverage=%s" % (
                scen_name, r, inc[r]["suite"], inc[r]["non_empty"], inc[r]["coverage"]), flush=True)

    # ----- Offsets, leniency, agreement, self-preference (three-judge runs) -----
    three = [r for r in comp_runs if inc[r]["offsets"] and inc[r]["offsets"]["n"] >= C.MIN_FULL]
    judges = sorted({j for r in three for j in inc[r]["offsets"]["offset"]})
    pooled_sum, pooled_n, agree_num, agree_den = {}, {}, 0.0, 0
    for r in three:
        of = inc[r]["offsets"]
        for j, m in of["mean"].items():
            pooled_sum[j] = pooled_sum.get(j, 0.0) + m * of["n"]
            pooled_n[j] = pooled_n.get(j, 0) + of["n"]
        agree_num += of["agree"] * of["n"]
        agree_den += of["n"]
    pooled_mean = {j: pooled_sum[j] / pooled_n[j] for j in pooled_sum if pooled_n[j]}
    spread = (max(pooled_mean.values()) - min(pooled_mean.values())) if len(pooled_mean) >= 2 else None
    agree = agree_num / agree_den if agree_den else None
    rows = [(inc[r]["family"], inc[r]["offsets"]["offset"]) for r in three]
    sp, sp_detail = {}, {}
    for j in judges:
        diff, n_own, n_other, own, other = g.self_preference(rows, j)
        p = g.perm_p(own, other, C.PERM_ITERS, C.PERM_SEED) if diff is not None else None
        sp[j] = diff
        sp_detail[j] = {"family": g.judge_family(j), "diff": diff, "n_own": n_own, "n_other": n_other, "perm_p": p,
                        "own_mean": (sum(own) / len(own)) if own else None,
                        "other_mean": (sum(other) / len(other)) if other else None}
    print("[judges] %s three_judge_runs=%d pooled_mean=%s spread=%s agree_all=%s" % (
        scen_name, len(three), pooled_mean, spread, agree), flush=True)
    for j in judges:
        print("[sp] %s %s %s" % (scen_name, j, sp_detail[j]), flush=True)
    for r in three:
        print("[offset] %s %s family=%s n=%d offset=%s" % (
            scen_name, inc[r]["model"], inc[r]["family"], inc[r]["offsets"]["n"], inc[r]["offsets"]["offset"]))

    # ----- Cells under three juries -----
    by_model = {}
    for run in comp_runs:
        by_model.setdefault(inc[run]["model"], []).append(run)
    cells = {m: rs[0] for m, rs in by_model.items() if len(rs) == 1}
    order = sorted(cells)
    all_judges = sorted({j for r in comp_runs for j in inc[r]["coverage"]})
    gpt_jury = [j for j in all_judges if g.judge_family(j) == "openai"]
    common = None
    for r in comp_runs:
        common = set(inc[r]["present"]) if common is None else common & set(inc[r]["present"])
    common = sorted(common or [])
    pv = {m: inc[cells[m]]["cell"] for m in order}
    juries = {"gpt_only": gpt_jury, "common": common}
    alt, fallback = {}, {}
    for name, jury in juries.items():
        alt[name] = {m: cell_of(scen_name, g.run_mean(inc[cells[m]]["records"],
                                                      lambda x, jj=jury: g.jury_score(x, jj))) for m in order}
        fallback[name] = sum(1 for m in order for x in inc[cells[m]]["records"] if g.jury_fallback(x, jury))
    matched = g.match_cells(pv, published, C.TOL_CELL)
    rp = g.ranks_high(pv)
    ranks = {name: g.ranks_high(alt[name]) for name in juries}
    tau = {name: g.kendall_tau_b([pv[m] for m in order], [alt[name][m] for m in order]) for name in juries}
    movers = {name: sorted(m for m in order if abs(rp[m] - ranks[name][m]) >= C.PLACES) for name in juries}
    v115 = sorted(m for m in order if inc[cells[m]]["suite"] == C.LAST_SUITE)
    v115_movers = sorted(m for m in v115 if abs(rp[m] - ranks["common"][m]) >= C.PLACES_V115)
    table = [{"model": m, "run": cells[m], "suite": inc[cells[m]]["suite"], "judges": inc[cells[m]]["present"],
              "published": pv[m], "gpt_only": alt["gpt_only"][m], "common": alt["common"][m],
              "rank_published": rp[m], "rank_gpt_only": ranks["gpt_only"][m], "rank_common": ranks["common"][m]}
             for m in sorted(order, key=lambda k: (rp[k], k))]
    print("[cells] %s %d cells, matched %d of %d published; gpt_jury=%s common=%s fallback=%s" % (
        scen_name, len(order), matched, len(published), gpt_jury, common, fallback), flush=True)
    print("[ranks] %s tau=%s movers=%s v115=%s v115_movers_common=%s" % (
        scen_name, tau, {k: len(v) for k, v in movers.items()}, v115, v115_movers), flush=True)
    for row in table:
        print("[cell] %s %s" % (scen_name, row))

    for r in runs_out.values():
        r.pop("records", None)
    return {
        "listed": len(chosen), "included": len(inc), "published_cells": len(published), "cells": len(order),
        "matched": matched, "composition_ok": comp_ok,
        "jury_by_suite": [{"suite": s, "judges": list(p), "runs": k} for (s, p), k in sorted(by_suite.items())],
        "three_judge_runs": len(three), "judges": judges, "pooled_judge_mean": pooled_mean,
        "lenience_spread": spread, "agree_all_three": agree, "self_preference": sp_detail,
        "gpt_jury": gpt_jury, "common_jury": common, "fallback_records": fallback, "tau_b": tau,
        "movers_3plus": movers, "v115_models": v115, "v115_movers_common_2plus": v115_movers,
        "table": table, "runs": runs_out, "_sp": sp,
    }


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
    chosen, published, group_err = {}, {}, {}
    for name, scen in g.SCENARIOS.items():
        chosen[name] = g.select_runs(run_suites, scen["prefix"])
        try:
            published[name] = g.group_values(json.loads(_get("%s/releases/%s/groups/%s.json" % (
                C.HELM_BASE, C.HELM_RELEASE, name))), scen["column"]) or []
            group_err[name] = None
        except Exception as e:  # noqa: BLE001
            published[name], group_err[name] = [], str(e)[:200]
        print("[release] %s %s runs=%d suites=%s published_cells=%d group_error=%s" % (
            C.HELM_RELEASE, name, len(chosen[name]), sorted(set(chosen[name].values())), len(published[name]),
            group_err[name]), flush=True)

    items = sorted(((name, run), suite) for name in chosen for run, suite in chosen[name].items())
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(load_run, items))

    res = {name: analyse(name, chosen[name], loaded, published[name]) for name in g.SCENARIOS}
    wb, om = res["wildbench"], res["omni_math"]
    st = {"fixtures": all(fx.values()),
          "listed": {k: res[k]["listed"] for k in res}, "included": {k: res[k]["included"] for k in res},
          "cells": {k: res[k]["cells"] for k in res}, "matched": {k: res[k]["matched"] for k in res},
          "composition_ok": wb["composition_ok"] and om["composition_ok"],
          "sp_wb": wb.pop("_sp"), "lenience_spread_wb": wb["lenience_spread"],
          "agree_omni": om["agree_all_three"], "sp_omni": om.pop("_sp"),
          "tau_gpt_wb": wb["tau_b"]["gpt_only"], "movers_gpt_wb": len(wb["movers_3plus"]["gpt_only"]),
          "v115_movers_common_wb": len(wb["v115_movers_common_2plus"])}
    verdicts = g.verdicts(st)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, "HELD" if v else "FAILED"))

    out = {
        "audit": 106,
        "slug": "helm-capabilities-judge-jury",
        "dataset": ("Per-instance judge annotations of HELM Capabilities release %s (Stanford CRFM): every wildbench "
                    "and omni_math run listed in runs_to_run_suites.json (display_predictions.json, or "
                    "scenario_state.json when the display file has no annotations; stats.json). Only run names, "
                    "public model names, judge names and numbers are published." % C.HELM_RELEASE),
        "fixture": fx,
        "group_error": group_err,
        "stats_for_verdicts": st,
        "verdicts": {k: ("HELD" if v else "FAILED") for k, v in verdicts.items()},
        "wildbench": wb,
        "omni_math": om,
        "note": ("HELM score per record = mean of every non-None judge value (empty-output key included); run value "
                 "= mean over records; WildBench cell = (score - 1) / 9. offset = a judge's value minus the mean of "
                 "the other two judges, averaged over records all three rated; self-preference = mean offset on "
                 "runs of the judge's own family (openai / anthropic / meta model prefix) minus the mean offset on "
                 "all other three-judge runs; perm_p one-sided over run labels (%d shuffles, seed %d). gpt_only = "
                 "the GPT judge alone; common = judges that rated at least half of every included run; a record "
                 "none of a jury rated keeps HELM's score (fallback_records)." % (C.PERM_ITERS, C.PERM_SEED)),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
