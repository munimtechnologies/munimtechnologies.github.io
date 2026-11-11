"""Audit 103: what does HELM Classic's WikiFact "EM" column measure for each model?

Downloads every wikifact k=5 run of HELM Classic release v0.4.0 (scenario_state.json for all five completions and
their log probabilities, display_predictions.json for the stored per-record score and the shown prediction,
stats.json for the run mean), re-scores every test record with HELM's metric (transcribed; must reproduce every
stored score) and with three other estimators (first completion, mean over completions, any completion), classes
every run by how its API answered (ranked / zero_logprob / collapsed), rebuilds each adapter's published "EM" cell,
re-ranks and writes the eight pre-registered verdicts. Only run names, instance ids, trials, classes, counts and
public model names go to results.json; references and completions go to the job log only, for the hand-read.
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import cases103 as C
import grade103 as g

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
    return json.loads(_get(url))


def run_url(suite, run, fname):
    return "%s/runs/%s/%s/%s" % (C.HELM_BASE, suite, urllib.parse.quote(run, safe=":,=@-_."), fname)


def fixture_ok():
    s = g.summarize_run(C.FIX_STATE, C.FIX_PREDS, C.KEYS_PER_RUN)
    tau_ok = True
    for (xs, ys), want in C.FIX_TAU:
        got = g.kendall_tau_b(xs, ys)
        tau_ok = tau_ok and ((got is None) if want is None else (got is not None and abs(got - want) < 1e-12))
    return {
        "qem": all(g.quasi_exact_match(a, b) == w for (a, b), w in C.FIX_QEM),
        "record": all(g.score_record(gs, cs) == w for (gs, cs), w in C.FIX_RECORD),
        "parsing": (all(g.completions_of(rs) == w for rs, w in C.FIX_COMPLETIONS)
                    and g.golds_of_instance(C.FIX_GOLDS[0]) == C.FIX_GOLDS[1]),
        "run": (all(s[k] == w for k, w in C.FIX_RUN.items())
                and all(g.run_mean(s["trials"], k) == w for k, w in C.FIX_MEANS.items())
                and g.run_class(s["rec"], s["counts"]["kept"]) == C.FIX_RUN_CLASS_OF_FIXTURE),
        "classes": (all(g.run_class(r, k) == w for (r, k), w in C.FIX_RUN_CLASS)
                    and all(g.adapter_class(c) == w for c, w in C.FIX_ADAPTER_CLASS)),
        "names": (all(g.is_wikifact_k5(r) == w for r, w in C.FIX_NAMES["k5"])
                  and all(g.subject_of(r) == w for r, w in C.FIX_NAMES["subject"])
                  and all(g.adapter_of(r) == w for r, w in C.FIX_NAMES["adapter"])
                  and all(g.model_part(r) == w for r, w in C.FIX_NAMES["model"])
                  and g.select_runs(C.FIX_SUITES) == C.FIX_SELECT),
        "aggregates": (g.build_cells(C.FIX_CELL_RUNS, C.FIX_CELL_LISTED) == C.FIX_CELLS
                       and g.ranks_high(C.FIX_RANKS[0]) == C.FIX_RANKS[1] and tau_ok
                       and g.match_cells(C.FIX_MATCH[0], C.FIX_MATCH[1], C.TOL_CELL) == C.FIX_MATCH[2]
                       and g.group_values(C.FIX_GROUP, C.COLUMN) == C.FIX_GROUP_VALUES
                       and g.group_values(C.FIX_GROUP_NO_COLUMN, C.COLUMN) is None
                       and all(g.median(xs) == w for xs, w in C.FIX_MEDIAN)),
        "verdicts": (all(g.verdicts(C.FIX_VERDICT_ON).values())
                     and not any(g.verdicts(C.FIX_VERDICT_PAST).values())),
    }


def hand_read_record(state, key):
    """Texts of one record for the job log (never written to results.json)."""
    for rs in (state or {}).get("request_states") or []:
        inst = (rs or {}).get("instance") or {}
        if inst.get("perturbation") is None and inst.get("split") == "test" and \
                (inst.get("id"), rs.get("train_trial_index", 0)) == key:
            comps = g.completions_of(rs)
            if not comps:
                return None
            top = sorted(range(len(comps)), key=lambda i: -comps[i][1])[0]
            return {"golds": g.golds_of_instance(inst), "first": comps[0][0].strip(), "first_lp": comps[0][1],
                    "top": comps[top][0].strip(), "top_lp": comps[top][1], "top_index": top,
                    "texts": [t.strip() for t, _ in comps]}
    return None


def load_run(item):
    run, suite = item
    rec = {"run": run, "suite": suite, "adapter": g.adapter_of(run), "subject": g.subject_of(run)}
    try:
        state = _json(run_url(suite, run, "scenario_state.json"))
        preds = _json(run_url(suite, run, "display_predictions.json"))
        stats = _json(run_url(suite, run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    try:
        s = g.summarize_run(state, preds, C.KEYS_PER_RUN)
        k = g.pick(s["disagree_keys"], run)
        ni = g.stat_entry(stats, "num_instances")
        rec.update({"summary": s, "read": None if k is None else (k, hand_read_record(state, k)),
                    "stat": g.stat_entry(stats, "quasi_exact_match"),
                    "num_instances_sum": None if ni is None else ni.get("sum")})
    except Exception as e:  # noqa: BLE001 - unexpected file shape: recorded as a failed run, never patched
        rec["error"] = "parse: " + str(e)[:280]
    del state, preds, stats
    return run, rec


def frac(a, b):
    return None if not b else float(Fraction(a) / b)


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

    run_suites = _json("%s/releases/%s/runs_to_run_suites.json" % (C.HELM_BASE, C.HELM_RELEASE))
    chosen = g.select_runs(run_suites)
    listed = {}
    for run in chosen:
        listed.setdefault(g.adapter_of(run), []).append(run)
    print("[release] %s wikifact k=5 runs listed=%d adapters=%d suites=%s" % (
        C.HELM_RELEASE, len(chosen), len(listed), sorted(set(chosen.values()))), flush=True)
    try:
        published = g.group_values(_json("%s/releases/%s/groups/%s.json" % (C.HELM_BASE, C.HELM_RELEASE, C.GROUP)),
                                   C.COLUMN) or []
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
        hm = g.run_mean(s["trials"], "h")
        reasons = []
        if s["stat_missing"] or s["stat_mismatch"]:
            reasons.append("record_stats")
        nis = r["num_instances_sum"]
        if nis is None or s["counts"]["kept"] != int(round(nis)) or s["counts"]["no_result"]:
            reasons.append("instances")
        st = r["stat"]
        if st is None or st.get("mean") is None or hm is None or abs(float(hm) - st["mean"]) > C.TOL_RUN:
            reasons.append("run_mean")
        cls = g.run_class(s["rec"], s["counts"]["kept"])
        runs_out[run] = {"status": "included" if not reasons else "excluded", "reasons": reasons,
                         "suite": r["suite"], "class": cls, "counts": s["counts"], "trials": len(s["trials"]),
                         "rec": s["rec"], "stat_missing": s["stat_missing"], "stat_mismatch": s["stat_mismatch"],
                         "stored_eq_first": s["stored_eq_first"], "shown_mismatch": s["shown_mismatch"],
                         "shown_missing": s["shown_missing"],
                         "means": {k: (None if g.run_mean(s["trials"], k) is None
                                       else float(g.run_mean(s["trials"], k))) for k in g.EST},
                         "disagree_keys": [[k[0], k[1]] for k in s["disagree_keys"]]}
        if not reasons:
            inc[run] = dict(r, cls=cls)
    print("[runs] listed=%d included=%d" % (len(chosen), len(inc)), flush=True)
    for run in sorted(chosen):
        if runs_out[run]["status"] != "included":
            o = runs_out[run]
            print("[excluded] %s %s mismatch=%s eq_first=%s" % (run, o.get("reasons") or o.get("error"),
                                                               o.get("stat_mismatch"), o.get("stored_eq_first")))

    # ----- Pooled totals by run class -----
    tot = {}
    for r in inc.values():
        t = tot.setdefault(r["cls"], {"runs": 0, "records": 0, "h": 0, "f": 0, "m": Fraction(0), "k": 0,
                                      "rec": {k: 0 for k in g.REC_KEYS}, "shown_mismatch": 0})
        s = r["summary"]
        t["runs"] += 1
        for v in s["trials"].values():
            t["records"] += v["n"]
            for k in g.EST:
                t[k] += v[k]
        for k in g.REC_KEYS:
            t["rec"][k] += s["rec"][k]
        t["shown_mismatch"] += s["shown_mismatch"]
    for c, t in sorted(tot.items()):
        t["shares"] = {k: frac(t[k], t["records"]) for k in g.EST}
        t["bonus_h_minus_m"] = frac(t["h"] - t["m"], t["records"])
        t["display_disagree_share"] = frac(t["rec"]["display_disagree"], t["records"])
        print("[totals] %s %s" % (c, {k: (float(v) if isinstance(v, Fraction) else v) for k, v in t.items()}),
              flush=True)

    # ----- Cells, classes, matching, ranks -----
    cells = g.build_cells({run: {"adapter": r["adapter"], "trials": r["summary"]["trials"]}
                           for run, r in inc.items()}, listed)
    acls = {ad: g.adapter_class([inc[n]["cls"] for n in listed[ad]]) for ad in cells}
    hv = {ad: v["h"] for ad, v in cells.items()}
    mv = {ad: v["m"] for ad, v in cells.items()}
    matched = g.match_cells({ad: float(v) for ad, v in hv.items()}, published, C.TOL_CELL)
    rh, rm = g.ranks_high(hv), g.ranks_high(mv)
    rf, rk = g.ranks_high({a: v["f"] for a, v in cells.items()}), g.ranks_high({a: v["k"] for a, v in cells.items()})
    order = sorted(cells)
    tau = g.kendall_tau_b([hv[a] for a in order], [mv[a] for a in order])
    tau_hk = g.kendall_tau_b([hv[a] for a in order], [cells[a]["k"] for a in order])
    movers = sorted(a for a in order if abs(rh[a] - rm[a]) >= C.PLACES)
    bonus = {a: hv[a] - mv[a] for a in order}
    ranked = [a for a in order if acls[a] == "ranked"]
    unranked = [a for a in order if acls[a] in ("zero_logprob", "collapsed")]
    rb = g.median([float(bonus[a]) for a in ranked])
    ub = g.median([float(bonus[a]) for a in unranked])
    rise_or_stay = sum(1 for a in unranked if rm[a] <= rh[a])
    table = [{"adapter": a, "model": g.model_part(a), "class": acls[a], "runs": cells[a]["runs"],
              "published_em": float(hv[a]), "first": float(cells[a]["f"]), "mean_of_completions": float(mv[a]),
              "any_of_completions": float(cells[a]["k"]), "bonus_h_minus_m": float(bonus[a]),
              "rank_published": rh[a], "rank_mean": rm[a], "rank_first": rf[a], "rank_any": rk[a]}
             for a in sorted(order, key=lambda k: (rh[k], k))]
    n_cls = {c: sum(1 for a in order if acls[a] == c) for c in sorted(set(acls.values()), key=str)}
    print("[cells] %d cells, matched %d of %d published; classes %s" % (len(order), matched, len(published), n_cls))
    print("[ranks] tau_b(H,M)=%s tau_b(H,K)=%s movers(>=%d)=%d median bonus ranked=%s unranked=%s "
          "unranked rise_or_stay=%d of %d" % (tau, tau_hk, C.PLACES, len(movers), rb, ub, rise_or_stay,
                                              len(unranked)), flush=True)
    for row in table:
        print("[cell] %s" % row)

    tr = tot.get("ranked") or {"records": 0, "h": 0, "m": Fraction(0), "rec": {"display_disagree": 0}}
    stats = {"fixtures": all(fx.values()), "runs_listed": len(chosen), "runs_included": len(inc),
             "cells": len(order), "matched": matched, "unranked_adapters": len(unranked),
             "ranked_n": tr["records"], "ranked_h": tr["h"], "ranked_m": tr["m"],
             "ranked_bonus_median": rb, "unranked_bonus_median": ub, "movers": len(movers), "tau": tau,
             "ranked_disagree": tr["rec"]["display_disagree"], "unranked_rise_or_stay": rise_or_stay}
    verdicts = g.verdicts(stats)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, "HELD" if v else "FAILED"))

    # ----- Hand-read lines (stdout only): up to N per run class, one per run, spread by a hash -----
    shown = {}
    for run in sorted(inc, key=lambda x: (g.stable_hash(x), x)):
        rd = inc[run].get("read")
        if not rd or not rd[1]:
            continue
        c = inc[run]["cls"]
        n = shown.get(c, 0)
        if n >= C.PRINT_PER_CLASS:
            continue
        shown[c] = n + 1
        (iid, trial), t = rd
        print("[read %s %d] run=%s id=%s trial=%s golds=%r first=%r (lp %.3f) top=%r (index %d, lp %.3f) texts=%r" % (
            c, n + 1, run, iid, trial, t["golds"], t["first"], t["first_lp"], t["top"], t["top_index"], t["top_lp"],
            t["texts"]))

    def enc(o):
        if isinstance(o, Fraction):
            return float(o)
        if isinstance(o, tuple):
            return list(o)
        raise TypeError(type(o))

    out = {
        "audit": 103,
        "slug": "helm-wikifact-best-of-five",
        "dataset": ("Per-instance outputs of HELM Classic release %s (Stanford CRFM): every wikifact k=5 run listed "
                    "in runs_to_run_suites.json, test split, all trials, all five completions. Only run names, "
                    "instance ids, trials, classes, counts and public model names are published." % C.HELM_RELEASE),
        "fixture": fx,
        "group_error": group_err,
        "published_cells": len(published),
        "runs_listed": len(chosen),
        "runs_included": len(inc),
        "totals_by_run_class": tot,
        "cells": len(order),
        "matched": matched,
        "adapter_classes": n_cls,
        "tau_b_published_vs_mean": tau,
        "tau_b_published_vs_any": tau_hk,
        "movers_3plus": movers,
        "median_bonus_ranked": rb,
        "median_bonus_unranked": ub,
        "unranked_rise_or_stay": rise_or_stay,
        "table": table,
        "verdicts": {k: ("HELD" if v else "FAILED") for k, v in verdicts.items()},
        "runs": runs_out,
        "note": ("H = HELM's EM (quasi_exact_match of the completion with the highest log probability, stable sort; "
                 "gated against every stored record score). F = the first completion (what HELM's prediction page "
                 "shows). M = mean over the returned completions (single-sample accuracy). K = any completion "
                 "(quasi_exact_match@5). Run class: zero_logprob if >= 90%% of records have every logprob 0, else "
                 "collapsed if >= 90%% have one distinct text, else ranked. Cells: mean over the adapter's runs of "
                 "each run's mean of trial means, only when every listed run is included. disagree_keys: up to %d "
                 "[instance id, trial] per run where F != H." % C.KEYS_PER_RUN),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True, default=enc)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
