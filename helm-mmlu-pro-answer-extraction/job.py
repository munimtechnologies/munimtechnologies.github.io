"""Audit 105: does HELM Capabilities' MMLU-Pro column credit the answer each model actually stated?

Downloads every MMLU-Pro run listed in HELM Capabilities release v1.15.0 (display_predictions.json for the scored
text and the stored per-record chain_of_thought_correctness; instances.json for the gold letter; stats.json for the
published run mean), finds which version of HELM's extract_answer reproduces the stored scores, re-grades every output
with the last explicit answer statement, classes every record, rebuilds the "COT correct" cells, re-ranks and writes
the eight pre-registered verdicts. Only run names, public model names, instance ids, letters, classes and counts go to
results.json / flips.json; output text goes to the job log only (hand-read lines).
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import gzip
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import cases105 as C
import grade105 as g

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
    s = g.summarize_run(json.loads(json.dumps(C.FIX_PREDICTIONS)), C.FIX_GOLDS)
    v = g.choose_version(s["mismatch"])
    tau_ok = True
    for (xs, ys), want in C.FIX_TAU:
        got = g.kendall_tau_b(xs, ys)
        tau_ok = tau_ok and ((got is None) if want is None else _close(got, want, 1e-12))
    return {
        "extract": all(g.helm_extract(t, ver) == w for (t, ver), w in C.FIX_EXTRACT),
        "stated": all(g.stated_answer(t) == w for t, w in C.FIX_STATED),
        "records": (all(g.record_class(*a) == w for a, w in C.FIX_CLASS)
                    and all(g.gold_letter(r) == w for r, w in C.FIX_GOLD)
                    and g.golds_by_id(C.FIX_INSTANCES) == C.FIX_GOLDS),
        "run": (s["counts"] == C.FIX_RUN_COUNTS and s["stored_n"] == C.FIX_RUN_STORED_N
                and s["mismatch"] == C.FIX_RUN_MISMATCH and v == C.FIX_RUN_VERSION
                and g.run_mean(s["records"], lambda r: r["credit"][v]) == C.FIX_RUN_MEAN_V3
                and g.run_mean(s["records"], lambda r: r["stated_credit"]) == C.FIX_RUN_MEAN_STATED
                and g.class_counts(s["records"], "v3") == C.FIX_RUN_CLASSES_V3
                and g.class_counts(s["records"], "v4") == C.FIX_RUN_CLASSES_V4
                and g.pr_up(s["records"], "v3") == C.FIX_RUN_PR_UP_V3),
        "names": (g.select_runs(C.FIX_SUITES) == C.FIX_SELECT
                  and all(g.model_part(n) == w for n, w in C.FIX_MODEL)
                  and all(g.stat_entry(C.FIX_STATS, n, sp) == w for (n, sp), w in C.FIX_STAT_ENTRY)),
        "aggregates": (g.group_values(C.FIX_GROUP, C.COLUMN_PREFIX) == C.FIX_GROUP_VALUES
                       and g.ranks_high(C.FIX_RANKS[0]) == C.FIX_RANKS[1] and tau_ok
                       and g.match_cells(C.FIX_MATCH[0], C.FIX_MATCH[1], C.TOL_CELL) == C.FIX_MATCH[2]),
        "verdicts": (all(g.verdicts(C.FIX_VERDICT_ON).values())
                     and not any(g.verdicts(C.FIX_VERDICT_PAST).values())),
    }


def load_run(item):
    run, suite = item
    rec = {"run": run, "suite": suite, "model": g.model_part(run)}
    try:
        preds = json.loads(_get(run_url(suite, run, "display_predictions.json")))
        insts = json.loads(_get(run_url(suite, run, "instances.json")))
        stats = json.loads(_get(run_url(suite, run, "stats.json")))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    try:
        golds = g.golds_by_id(insts)
        s = g.summarize_run(preds, golds)
        rec.update({"summary": s, "n_instances": len(golds), "stat": g.stat_entry(stats, C.STAT, C.SPLIT)})
    except Exception as e:  # noqa: BLE001 - unexpected file shape: recorded as a failed run, never patched
        rec["error"] = "parse: " + str(e)[:280]
    del preds, insts, stats
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
    print("[release] %s mmlu_pro runs listed=%d suites=%s" % (
        C.HELM_RELEASE, len(chosen), sorted(set(chosen.values()))), flush=True)
    try:
        published = g.group_values(json.loads(_get("%s/releases/%s/groups/%s.json" % (
            C.HELM_BASE, C.HELM_RELEASE, C.GROUP))), C.COLUMN_PREFIX) or []
        group_err = None
    except Exception as e:  # noqa: BLE001
        published, group_err = [], str(e)[:200]
    print("[group] %s cells published=%d error=%s" % (C.COLUMN_PREFIX, len(published), group_err), flush=True)

    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(load_run, sorted(chosen.items())))

    # ----- Run gates -----
    runs_out, inc = {}, {}
    for run in sorted(chosen):
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"model": r["model"], "status": "download_failed", "error": r["error"]}
            continue
        s = r["summary"]
        kept = s["counts"]["kept"]
        v = g.choose_version(s["mismatch"])
        recs = s["records"]
        repro = g.run_mean(recs, lambda x, v=v: x["credit"][v])
        stated = g.run_mean(recs, lambda x: x["stated_credit"])
        pr = g.run_mean(recs, lambda x: x["credit"]["pr4323"])
        pub = None if r["stat"] is None else r["stat"].get("mean")
        agree = s["stored_n"] - s["mismatch"][v]
        reasons = []
        if not kept:
            reasons.append("no_records")
        if s["stored_n"] < C.STORED_SHARE * kept:
            reasons.append("stored_missing")
        if s["stored_n"] and agree < C.REPRO_SHARE * s["stored_n"]:
            reasons.append("record_mismatch")
        if not _close(repro, pub, C.TOL_RUN):
            reasons.append("mean_mismatch")
        o = {"model": r["model"], "suite": r["suite"], "counts": s["counts"], "n_instances": r["n_instances"],
             "stored_n": s["stored_n"], "mismatch": s["mismatch"], "version": v, "agree": agree,
             "published": pub, "repro": repro, "stated": stated, "pr4323": pr,
             "classes": g.class_counts(recs, v), "pr_up_down": list(g.pr_up(recs, v)),
             "helm_none": sum(1 for x in recs if x["ext"][v][0] is None),
             "stated_none": sum(1 for x in recs if x["s_letter"] is None),
             "mean_chars": (sum(x["chars"] for x in recs) / len(recs)) if recs else None,
             "status": "included" if not reasons else "excluded", "reasons": reasons}
        runs_out[run] = o
        if not reasons:
            inc[run] = dict(r, v=v, out=o)
    print("[runs] listed=%d included=%d" % (len(chosen), len(inc)), flush=True)
    for run in sorted(chosen):
        o = runs_out[run]
        if o["status"] != "included":
            print("[excluded] %s %s" % (run, {k: o.get(k) for k in (
                "status", "reasons", "error", "version", "mismatch", "stored_n", "agree", "published", "repro")}))

    # ----- Pooled classes -----
    pooled, pr_up_tot, pr_down_tot, recs_tot = {}, 0, 0, 0
    for r in inc.values():
        for c, n in r["out"]["classes"].items():
            pooled[c] = pooled.get(c, 0) + n
        pr_up_tot += r["out"]["pr_up_down"][0]
        pr_down_tot += r["out"]["pr_up_down"][1]
        recs_tot += r["summary"]["counts"]["kept"]
    up = sum(n for c, n in pooled.items() if c.startswith("up_"))
    down = sum(n for c, n in pooled.items() if c.startswith("down_"))
    credits = sum(n for c, n in pooled.items() if c in ("both_right",) or c.startswith("down_"))
    versions = {}
    for r in inc.values():
        versions[r["v"]] = versions.get(r["v"], 0) + 1
    print("[totals] records=%d published_credits=%d up=%d down=%d classes=%s pr4323_up=%d pr4323_down=%d "
          "versions=%s" % (recs_tot, credits, up, down, dict(sorted(pooled.items())), pr_up_tot, pr_down_tot,
                           versions), flush=True)

    # ----- Cells (one run per model), matching, ranks -----
    by_model = {}
    for run, r in inc.items():
        by_model.setdefault(r["model"], []).append(run)
    cells = {m: runs[0] for m, runs in by_model.items() if len(runs) == 1}
    order = sorted(cells)
    pv = {m: inc[cells[m]]["out"]["repro"] for m in order}
    sv = {m: inc[cells[m]]["out"]["stated"] for m in order}
    matched = g.match_cells(pv, published, C.TOL_CELL)
    rp, rs = g.ranks_high(pv), g.ranks_high(sv)
    tau = g.kendall_tau_b([pv[m] for m in order], [sv[m] for m in order])
    movers = sorted(m for m in order if abs(rp[m] - rs[m]) >= C.PLACES)
    gain = {m: sv[m] - pv[m] for m in order}
    fl_gain = gain.get(g.FLASH_LITE)
    gainers_other = sorted(m for m in order if m != g.FLASH_LITE and gain[m] >= C.GAIN_OTHER - 1e-12)
    gem_other = sorted(m for m in order if m != g.FLASH_LITE and "gemini" in m and gain[m] >= C.GAIN_GEMINI - 1e-12)
    table = [{"model": m, "run": cells[m], "version": inc[cells[m]]["v"], "published": pv[m], "stated": sv[m],
              "pr4323": inc[cells[m]]["out"]["pr4323"], "gain": gain[m], "rank_published": rp[m],
              "rank_stated": rs[m], "classes": inc[cells[m]]["out"]["classes"],
              "helm_none": inc[cells[m]]["out"]["helm_none"], "stated_none": inc[cells[m]]["out"]["stated_none"]}
             for m in sorted(order, key=lambda k: (rp[k], k))]
    print("[cells] %d cells, matched %d of %d published" % (len(order), matched, len(published)))
    print("[ranks] tau_b(published,stated)=%s movers(>=%d)=%d flash_lite_gain=%s gainers_other=%d gemini_other=%s"
          % (tau, C.PLACES, len(movers), fl_gain, len(gainers_other), gem_other), flush=True)
    for row in table:
        print("[cell] %s" % row)

    st = {"fixtures": all(fx.values()), "runs_listed": len(chosen), "runs_included": len(inc), "cells": len(order),
          "matched": matched, "flash_lite_gain": fl_gain, "gainers_other": len(gainers_other), "up": up,
          "down": down, "up_boxed": pooled.get("up_boxed", 0), "up_phrase": pooled.get("up_phrase", 0),
          "up_other_letter": pooled.get("up_other_letter", 0), "pr_up": pr_up_tot, "movers": len(movers),
          "tau": tau, "gemini_other_gainers": len(gem_other)}
    verdicts = g.verdicts(st)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, "HELD" if v else "FAILED"))

    # ----- Flips (ids and classes only) and hand-read lines (stdout only) -----
    flips, cand = [], {}
    for run, r in sorted(inc.items()):
        v = r["v"]
        for x in r["summary"]["records"]:
            h_letter, h_rule, h_spur = x["ext"][v]
            c = g.record_class(h_letter, h_rule, h_spur, x["s_letter"], x["s_form"], x["gold"])
            if c.startswith("up_") or c.startswith("down_"):
                flips.append([r["model"], x["key"][0], x["key"][1], c, x["gold"], h_letter, x["s_letter"]])
                cand.setdefault(c, []).append((g.stable_hash("%s|%s|%s" % (r["model"], x["key"][0], x["key"][1])),
                                               r["model"], x, h_letter, h_rule))
    for c in sorted(cand):
        for i, (_, model, x, hl, hr) in enumerate(sorted(cand[c], key=lambda t: (t[0], t[1]))[:C.PRINT_PER_CLASS]):
            print("[read %s %d] model=%s id=%s gold=%s helm=%s(rule %s) stated=%s(%s) tail=%r" % (
                c, i + 1, model, x["key"][0], x["gold"], hl, hr, x["s_letter"], x["s_form"], x["tail"]))

    out = {
        "audit": 105,
        "slug": "helm-mmlu-pro-answer-extraction",
        "dataset": ("Per-instance outputs of HELM Capabilities release %s (Stanford CRFM): every mmlu_pro run listed in "
                    "runs_to_run_suites.json (display_predictions.json, instances.json, stats.json). Only run names, "
                    "public model names, instance ids, letters, classes and counts are published." % C.HELM_RELEASE),
        "fixture": fx,
        "group_error": group_err,
        "published_cells": len(published),
        "runs_listed": len(chosen),
        "runs_included": len(inc),
        "records": recs_tot,
        "published_credits": credits,
        "pooled_classes": pooled,
        "up": up,
        "down": down,
        "pr4323_up": pr_up_tot,
        "pr4323_down": pr_down_tot,
        "scorer_versions": versions,
        "cells": len(order),
        "matched": matched,
        "tau_b_published_vs_stated": tau,
        "movers_3plus": movers,
        "gainers_other_1pt": gainers_other,
        "gemini_other_2pt": gem_other,
        "table": table,
        "stats_for_verdicts": st,
        "verdicts": {k: ("HELD" if v else "FAILED") for k, v in verdicts.items()},
        "runs": runs_out,
        "note": ("published = HELM's chain_of_thought_correctness rebuilt with the version of extract_answer that "
                 "reproduces the stored per-record scores (gated against stats.json within %g); stated = 1 when the "
                 "last explicit answer statement ('answer is X', 'answer: X', '\\\\boxed{X}') is the gold letter; "
                 "pr4323 = HELM main with PR #4323's unescaped regex 2. Classes: up_* = published 0, stated 1 "
                 "(up_boxed / up_phrase: HELM extracted nothing; up_other_letter: HELM read a different letter); "
                 "down_* = published 1, stated 0." % C.TOL_RUN),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "flips.json"), "w", encoding="utf-8") as fh:
        json.dump({"columns": ["model", "instance_id", "trial", "class", "gold", "helm", "stated"], "rows": flips},
                  fh, separators=(",", ":"), ensure_ascii=True)
    print("[done] wrote results.json and flips.json (%d flips)" % len(flips))


if __name__ == "__main__":
    main()
