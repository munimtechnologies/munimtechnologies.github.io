"""Audit 99 follow-up (post-hoc, descriptive): HELM Classic's synthetic-reasoning credits by class, with a
pattern-exact grade that also checks where the operators sit.

Downloads the same HELM Classic v0.4.0 runs as audit 99, re-grades every test record of every trial, and splits the
column's quasi-exact credits into exact, format_only, ops_misplaced and ops_blind (see grade99b.py). Gates: the hand-
traced fixtures match; every listed run passes audit 99's inclusion rules; audit 99's totals are reproduced exactly;
every model's cell matches a published EM cell. Then it rebuilds each model's cell under the pattern-exact grade,
re-ranks the column and reports two stated expectations. Only run names, instance ids, trials, classes, counts and
public model names are written to the outputs; gold and model texts go to the job log only, for the hand-read.
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import cases99b as C
import grade99 as g
import grade99b as b

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
        for (gold, pred), want in C.FIX_GRADES_B:
            r = b.grade_record_b([gold], pred)
            if (r["em"], r["qem"], r["oa"], r["px"], r["cls"]) != want:
                return False
        (golds, pred), want = C.FIX_MULTI_B
        r = b.grade_record_b(golds, pred)
        return (r["em"], r["qem"], r["oa"], r["px"], r["cls"]) == want

    s = b.summarize_run_b(C.FIX_INSTANCES_B, C.FIX_PREDS_B)
    return {
        "tokens": all(b.tokens(t) == w for t, w in C.FIX_TOKENS),
        "grades": grades_ok(),
        "run": all(s[k] == w for k, w in C.FIX_RUN_B.items()),
        "v1_totals": b.v1_totals(s["classes"], [s["trials"]]) == C.FIX_V1_TOTALS,
        "pick": all(b.pick(lst, salt) == w for (lst, salt), w in C.FIX_PICK),
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
    s = b.summarize_run_b(inst, preds)
    gold = {i.get("id"): [((r.get("output") or {}).get("text") or "") for r in i.get("references") or []
                          if "correct" in (r.get("tags") or [])]
            for i in inst if isinstance(i, dict) and i.get("split") == "test"}
    want = {}
    for cls, lst in s["keys"].items():
        k = b.pick(lst, run + "|" + cls)
        if k is not None:
            want[k] = cls
    texts = {}
    for r in preds:
        if isinstance(r, dict) and r.get("perturbation") is None:
            key = (r.get("instance_id"), r.get("train_trial_index", 0))
            if key in want and key not in texts:
                texts[key] = (want[key], " | ".join(gold.get(key[0], [])), r.get("predicted_text"))
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

    # ----- Run gates (audit 99's rules) -----
    runs_out, inc = {}, {}
    for run in sorted(chosen):
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "error": r["error"]}
            continue
        s = r["summary"]
        qm, em = g.run_mean(s["trials"], "qem"), g.run_mean(s["trials"], "em")
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
        pxm = g.run_mean(s["trials"], "px")
        runs_out[run] = {"status": "included" if not reasons else "excluded", "reasons": reasons,
                         "model": r["model"], "mode": r["mode"], "kept": s["counts"]["kept"],
                         "classes": s["classes"], "qem": None if qm is None else float(qm),
                         "px": None if pxm is None else float(pxm)}
        if not reasons:
            inc[run] = r
    print("[runs] listed=%d included=%d" % (len(chosen), len(inc)))
    for run in sorted(chosen):
        if runs_out[run]["status"] != "included":
            print("[excluded] %s %s" % (run, runs_out[run].get("reasons") or runs_out[run].get("error")))

    # ----- Totals and the reproduction gate -----
    classes = {c: 0 for c in b.CLASSES}
    by_mode = {m: {"records": 0, "qem": 0, "classes": {c: 0 for c in b.CLASSES}} for m in C.MODES}
    for run, r in inc.items():
        s = r["summary"]
        bm = by_mode.setdefault(r["mode"], {"records": 0, "qem": 0, "classes": {c: 0 for c in b.CLASSES}})
        bm["records"] += sum(v["n"] for v in s["trials"].values())
        bm["qem"] += sum(v["qem"] for v in s["trials"].values())
        for c, v in s["classes"].items():
            classes[c] += v
            bm["classes"][c] += v
    v1 = b.v1_totals(classes, [r["summary"]["trials"] for r in inc.values()])
    records = sum(v["records"] for v in by_mode.values())
    px_total = classes["exact"] + classes["format_only"]
    print("[totals] records=%d classes=%s px=%d" % (records, classes, px_total))
    print("[v1 totals] %s (audit 99: %s)" % (v1, C.V1_TOTALS))
    for m, v in sorted(by_mode.items()):
        print("[by mode] %s %s" % (m, v))

    # ----- Cells and ranks -----
    by_model = {}
    for run in chosen:
        by_model.setdefault(g.model_of(run), []).append(run)
    cells = {"qem": {}, "oa": {}, "px": {}, "em": {}}
    complete = []
    for m, runs in sorted(by_model.items()):
        if all(x in inc for x in runs) and {g.mode_of(x) for x in runs} == set(C.MODES):
            tl = [inc[x]["summary"]["trials"] for x in runs]
            for k in cells:
                cells[k][m] = g.cell(tl, k)
            complete.append(m)
    matched = g.match_cells({m: float(v) for m, v in cells["qem"].items()}, published, C.TOL_CELL)
    gates = {"fixtures": all(fx.values()), "runs_listed": len(chosen) == C.V1_RUNS,
             "runs_included": len(inc) == len(chosen), "v1_totals_reproduced": v1 == C.V1_TOTALS,
             "cells_matched": matched == C.V1_CELLS and len(complete) == C.V1_CELLS}
    print("[gates] %s (cells matched %d of %d)" % (gates, matched, len(by_model)))

    rp, rpx, roa = g.ranks_high(cells["qem"]), g.ranks_high(cells["px"]), g.ranks_high(cells["oa"])
    order = sorted(complete)
    tau_px = g.kendall_tau_b([cells["qem"][m] for m in order], [cells["px"][m] for m in order])
    tau_oa = g.kendall_tau_b([cells["qem"][m] for m in order], [cells["oa"][m] for m in order])
    tau_em = g.kendall_tau_b([cells["qem"][m] for m in order], [cells["em"][m] for m in order])
    movers_px = sorted(m for m in complete if abs(rp[m] - rpx[m]) >= C.PLACES)
    falls = {m: cells["qem"][m] - cells["px"][m] for m in complete}
    max_fall = max(falls.values()) if falls else None
    table = [{"model": m, "published": float(cells["qem"][m]), "operator_aware": float(cells["oa"][m]),
              "pattern_exact": float(cells["px"][m]), "exact": float(cells["em"][m]), "fall_px": float(falls[m]),
              "rank_published": rp[m], "rank_operator_aware": roa[m], "rank_pattern_exact": rpx[m]}
             for m in sorted(complete, key=lambda k: (rp[k], k))]
    print("[ranks] tau_b published vs px=%s oa=%s em=%s movers_px(>=%d)=%d max_fall_px=%s" % (
        tau_px, tau_oa, tau_em, C.PLACES, len(movers_px), None if max_fall is None else float(max_fall)))
    for row in table:
        print("[cell] %s" % row)

    other_norm = classes["format_only"] + classes["ops_misplaced"]
    expect = {
        "E1_misplaced_at_least_half_of_other_norm": bool(other_norm) and Fraction(
            classes["ops_misplaced"], other_norm) >= C.EXPECT["E1_misplaced_share_of_other_norm"],
        "E2_tau_published_vs_px_at_least_0.8": tau_px is not None and tau_px >= C.EXPECT["E2_tau_published_vs_px"],
    }
    for k, v in sorted(expect.items()):
        print("[expectation] %s = %s" % (k, "MET" if v else "NOT MET"))

    # ----- Hand-read lines (stdout only): up to N per (mode, class), one per run -----
    shown = {}
    for run in sorted(inc, key=lambda x: (b.stable_hash(x), x)):  # spread the reads over models
        mode = inc[run]["mode"]
        for key, (cls, gold, pred) in sorted(inc[run]["texts"].items(), key=lambda kv: (kv[1][0], str(kv[0][0]))):
            n = shown.get((mode, cls), 0)
            if n >= C.PRINT_PER_MODE_CLASS:
                continue
            shown[(mode, cls)] = n + 1
            print("[read %s %s %d] run=%s id=%s trial=%s gold=%r pred=%r" % (
                mode, cls, n + 1, run, key[0], key[1], gold, (pred or "")[:120]))

    positions = [{"run": run, "instance_id": i, "trial": t, "class": cls}
                 for run in sorted(inc) for cls in ("format_only", "ops_misplaced")
                 for i, t in inc[run]["summary"]["keys"][cls]]
    out = {
        "audit": "99-followup-positions",
        "kind": "post-hoc, descriptive (not pre-registered)",
        "dataset": ("Per-instance outputs of HELM Classic release %s (Stanford CRFM): every synthetic_reasoning run "
                    "listed in runs_to_run_suites.json, test split, all trials." % C.HELM_RELEASE),
        "fixture": fx,
        "gates": gates,
        "group_error": group_err,
        "runs_listed": len(chosen),
        "runs_included": len(inc),
        "cells_matched": [matched, len(by_model)],
        "records": records,
        "classes": classes,
        "pattern_exact_credits": px_total,
        "v1_totals": v1,
        "by_mode": by_mode,
        "tau_b": {"published_vs_pattern_exact": tau_px, "published_vs_operator_aware": tau_oa,
                  "published_vs_exact": tau_em},
        "movers_3plus_pattern_exact": movers_px,
        "max_fall_pattern_exact": None if max_fall is None else float(max_fall),
        "expectations": expect,
        "table": table,
        "runs": runs_out,
        "note": ("Classes of HELM's quasi-exact credits: exact (exact_match 1); format_only (same tokens: case, "
                 "spacing, other punctuation, articles); ops_misplaced (the gold's operators in the gold's order but "
                 "in other places); ops_blind (audit 99's operator-blind credits). pattern_exact = exact + "
                 "format_only. Cells: mean of a model's trial-level means over the three modes."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "positions.json"), "w", encoding="utf-8") as fh:
        json.dump({"note": "Every format_only and ops_misplaced credit by run, instance id and trial; no text.",
                   "records": positions}, fh, ensure_ascii=True)
    print("[done] wrote results.json and positions.json (%d records)" % len(positions))


if __name__ == "__main__":
    main()
