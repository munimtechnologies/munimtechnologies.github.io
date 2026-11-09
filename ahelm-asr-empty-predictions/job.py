"""Does HELM issue #4359 (an empty transcription gets a perfect error rate of 0) reach AHELM's published scores? (audit 93)

Reads the seven run-group pages of AHELM suite v1.0.0 whose main metric is wer_score (HELM's schema_audio.yaml), takes
every run they list, downloads each run's display_predictions.json and stats.json, and counts first-trial outputs that
are empty after strip() -- the outputs HELM's `if not pred: return 0` guard scores 0 on wer/mer/cer (and chinese_*).
It re-values those at 1.0 (jiwer's value for an empty hypothesis, the fix proposed in #4359 / PR #4361), recomputes
every run's mean and every headline WER cell (the mean of its runs' means), re-ranks the models in each group table,
and reports the pre-registered verdicts. Only run names, instance ids, metric names, classes, counts and public model
names are written to results.json and empties.json; output text of punctuation-only outputs is printed to the job log
only, for the hand-read.

Gates before any verdict: the hand-traced fixtures match; at least 6 of the 7 group pages load; at least 100 runs;
at least 99% of listed runs download and our mean of per-record main-metric values equals HELM's stats.json mean
(within 1e-6) with as many records as HELM's num_instances; at least 95% of headline WER cells equal the mean of their
runs' stats.json means. Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import cases93 as C
import grade93 as g

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


def run_url(run, fname):
    return "%s/runs/%s/%s/%s" % (C.HELM_BASE, C.SUITE, urllib.parse.quote(run, safe=":,=@-_."), fname)


def fixture_ok():
    r = g.summarize_run(C.FIX_RECORDS)
    t = C.FIX_RUN_TARGET
    run_ok = (r["counts"] == t["counts"] and r["classes"] == t["classes"] and r["metrics"] == t["metrics"]
              and [e[0] for e in r["empties"]] == t["empty_ids"] and [p[0] for p in r["punct"]] == t["punct_ids"])
    return {
        "normalize": all(g.normalize_text(x, should_remove_articles=False) == w for x, w in C.FIX_NORM),
        "classes": all(g.pred_class(x) == w for x, w in C.FIX_CLASS),
        "models": all(g.model_of(rn) == m and g.is_gemini(m) == gem for rn, m, gem in C.FIX_MODEL),
        "run_summary": run_ok,
        "stats": all(g.stat_mean(C.FIX_STATS, n) == w for n, w in C.FIX_STAT_TARGET.items()),
        "groups": (g.collect_run_names(C.FIX_GROUP) == C.FIX_GROUP_RUNS
                   and g.wer_cells(C.FIX_GROUP) == C.FIX_GROUP_CELLS),
        "ranks": g.min_ranks_low(C.FIX_RANKS_IN) == C.FIX_RANKS_OUT,
        "verdicts": all(g.predictions93(*a, C.THRESHOLDS) == w for a, w in C.FIX_V_CASES),
    }


def load_run(run):
    rec = {"run": run, "model": g.model_of(run)}
    try:
        preds = _json(run_url(run, "display_predictions.json"))
        stats = _json(run_url(run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    s = g.summarize_run(preds)
    main = next((m for m in g.MAIN_METRICS if g.stat_mean(stats, m) is not None), None)
    rec.update({"summary": s, "main": main,
                "published": {m: g.stat_mean(stats, m) for m in g.ERROR_METRICS if g.stat_mean(stats, m) is not None},
                "num_instances": g.stat_mean(stats, "num_instances"),
                "num_references": g.stat_mean(stats, "num_references")})
    return run, rec


def share(a, n):
    return float(Fraction(a, n)) if n else None


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

    # ----- Group pages -> runs and headline cells -----
    group_runs, group_cells, group_err = {}, {}, {}
    for grp in C.GROUPS:
        try:
            doc = _json("%s/runs/%s/groups/%s.json" % (C.HELM_BASE, C.SUITE, grp))
        except Exception as e:  # noqa: BLE001
            group_err[grp] = str(e)[:200]
            continue
        group_runs[grp] = sorted(g.collect_run_names(doc))
        group_cells[grp] = g.wer_cells(doc)
        print("[group] %s runs=%d wer_cells=%s" % (grp, len(group_runs[grp]),
                                                  None if group_cells[grp] is None else len(group_cells[grp])))
    if group_err:
        print("[group errors] %s" % group_err)
    all_runs = sorted({r for v in group_runs.values() for r in v})
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(load_run, all_runs))

    # ----- Run gates -----
    runs_out, inc = {}, {}
    for run in all_runs:
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "error": r["error"]}
            continue
        m = r["main"]
        met = r["summary"]["metrics"].get(m) if m else None
        ours = met["sum"] / met["n"] if met and met["n"] else None
        pub = r["published"].get(m) if m else None
        ok = (m is not None and met is not None and pub is not None and abs(ours - pub) <= C.TOL
              and r["num_instances"] is not None and met["n"] == int(round(r["num_instances"])))
        row = {"status": "included" if ok else "excluded", "model": r["model"], "main": m,
               "counts": r["summary"]["counts"], "classes": r["summary"]["classes"],
               "num_instances": r["num_instances"], "num_references": r["num_references"],
               "published_main": pub, "ours_main": ours,
               "metrics": {mm: {"n": v["n"], "n_empty": v["n_empty"], "empty_nonzero": v["empty_nonzero"],
                                "published_mean": v["sum"] / v["n"] if v["n"] else None,
                                "corrected_mean": v["corrected_sum"] / v["n"] if v["n"] else None,
                                "zeros": v["zeros"], "zero_empty": v["zero_empty"]}
                           for mm, v in sorted(r["summary"]["metrics"].items())}}
        runs_out[run] = row
        if ok:
            inc[run] = r
    n_rep = len(inc)
    rep_share = Fraction(n_rep, len(all_runs)) if all_runs else Fraction(0)

    # ----- Headline cells -----
    cells_out, cell_ok_n, cell_n = {}, 0, 0
    for grp, cells in group_cells.items():
        rows = []
        for label, value, names in cells or []:
            cell_n += 1
            wruns = [n for n in names if n in loaded and "error" not in loaded[n]
                     and loaded[n]["published"].get("wer_score") is not None]
            complete = bool(wruns) and all(n in inc and inc[n]["main"] == "wer_score" for n in wruns)
            pub_mean = g.mean(loaded[n]["published"]["wer_score"] for n in wruns) if wruns else None
            reproduced = pub_mean is not None and abs(pub_mean - value) <= C.TOL
            cell_ok_n += 1 if reproduced else 0
            corr = None
            if complete:
                ms = [inc[n]["summary"]["metrics"]["wer_score"] for n in wruns]
                corr = g.mean(v["corrected_sum"] / v["n"] for v in ms)
            rows.append({"model": label, "published": value, "ours_published": pub_mean, "reproduced": reproduced,
                         "complete": complete, "corrected": corr, "n_runs": len(wruns),
                         "runs_listed": len(names),
                         "empty": sum(inc[n]["summary"]["metrics"]["wer_score"]["n_empty"] for n in wruns
                                      if n in inc and "wer_score" in inc[n]["summary"]["metrics"]),
                         "records": sum(inc[n]["summary"]["metrics"]["wer_score"]["n"] for n in wruns
                                        if n in inc and "wer_score" in inc[n]["summary"]["metrics"])})
        cells_out[grp] = rows
    cell_share = Fraction(cell_ok_n, cell_n) if cell_n else Fraction(0)
    p1_parts = {"fixtures": all(fx.values()), "groups": len(group_runs) >= C.MIN_GROUPS_LOADED,
                "runs": len(all_runs) >= C.MIN_RUNS, "runs_reproduced": rep_share >= C.MIN_RUNS_REPRODUCED,
                "cells_reproduced": cell_share >= C.MIN_CELLS_REPRODUCED}
    print("[runs] listed=%d included=%d (%.4f); cells reproduced %d/%d" % (len(all_runs), n_rep, float(rep_share),
                                                                       cell_ok_n, cell_n))
    print("[P1] %s" % p1_parts)
    if not p1_parts["groups"] or rep_share < C.ABORT_RUNS_REPRODUCED:
        with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
            json.dump({"audit": 93, "aborted": True, "fixture": fx, "p1_parts": p1_parts, "group_errors": group_err,
                       "runs": runs_out}, fh, indent=1, ensure_ascii=True)
        raise SystemExit("group or reproduction gate failed -- aborting (diagnostics in results.json)")

    # ----- Census over included runs -----
    n_records = sum(r["summary"]["metrics"][r["main"]]["n"] for r in inc.values())
    n_empty = sum(r["summary"]["metrics"][r["main"]]["n_empty"] for r in inc.values())
    n_empty_gem = sum(r["summary"]["metrics"][r["main"]]["n_empty"] for r in inc.values() if g.is_gemini(r["model"]))
    nonzero = sum(v["empty_nonzero"] for r in inc.values() for v in r["summary"]["metrics"].values())
    zeros = sum(r["summary"]["metrics"][r["main"]]["zeros"] for r in inc.values())
    zero_empty = sum(r["summary"]["metrics"][r["main"]]["zero_empty"] for r in inc.values())
    classes = {}
    for r in inc.values():
        for k, v in r["summary"]["classes"].items():
            classes[k] = classes.get(k, 0) + v
    multi_ref = sorted(n for n, r in inc.items() if r["num_references"] is not None and r["num_references"] > 1)
    ref_missing = sum(1 for r in inc.values() if r["num_references"] is None)
    by_model, by_group = {}, {}
    for n, r in inc.items():
        d = by_model.setdefault(r["model"], {"runs": 0, "records": 0, "empty": 0, "punct_only": 0})
        mm = r["summary"]["metrics"][r["main"]]
        d["runs"] += 1
        d["records"] += mm["n"]
        d["empty"] += mm["n_empty"]
        d["punct_only"] += r["summary"]["classes"]["punct_only"]
    for grp, names in group_runs.items():
        rs = [inc[n] for n in names if n in inc]
        by_group[grp] = {"runs_listed": len(names), "runs_included": len(rs),
                         "records": sum(r["summary"]["metrics"][r["main"]]["n"] for r in rs),
                         "empty": sum(r["summary"]["metrics"][r["main"]]["n_empty"] for r in rs)}
    totals = {"runs": len(inc), "records": n_records, "empty": n_empty, "empty_share": share(n_empty, n_records),
              "empty_gemini": n_empty_gem, "empty_with_nonzero_published": nonzero, "published_zeros": zeros,
              "published_zeros_from_empty": zero_empty, "classes": classes, "runs_multi_reference": len(multi_ref),
              "runs_num_references_missing": ref_missing}
    print("[totals] %s" % totals)
    print("[by group] %s" % by_group)
    print("[by model] %s" % {k: by_model[k] for k in sorted(by_model)})

    # ----- Ranks in each group table (complete cells only) -----
    ranks, max_rise, changed_total = {}, None, 0
    for grp, rows in cells_out.items():
        comp = [r for r in rows if r["complete"]]
        pub = {r["model"]: r["ours_published"] for r in comp}
        cor = {r["model"]: r["corrected"] for r in comp}
        rp, rc = g.min_ranks_low(pub), g.min_ranks_low(cor)
        changed = sorted(m for m in pub if rp[m] != rc[m])
        for r in comp:
            r["rank_published"], r["rank_corrected"] = rp[r["model"]], rc[r["model"]]
            rise = r["corrected"] - r["ours_published"]
            r["rise"] = rise
            max_rise = rise if max_rise is None or rise > max_rise else max_rise
        changed_total += len(changed)
        ranks[grp] = {"complete_cells": len(comp), "cells": len(rows), "models_rank_changed": changed,
                      "max_rise": max((r["rise"] for r in comp), default=None)}
    print("[ranks] %s" % ranks)

    # ----- Verdicts -----
    verdicts = g.predictions93(n_empty, nonzero == 0, n_empty_gem, n_records, max_rise, changed_total,
                               len(multi_ref), C.THRESHOLDS)
    verdicts["P1_structural"] = all(p1_parts.values())
    for name in sorted(verdicts):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    numbers = {"P2_empty_and_nonzero": [n_empty, nonzero],
               "P3_empty_gemini_of_empty": [n_empty_gem, n_empty, share(n_empty_gem, n_empty)],
               "P4_empty_of_records": [n_empty, n_records, share(n_empty, n_records)],
               "P5_max_cell_rise": max_rise, "P6_models_rank_changed": changed_total,
               "P7_runs_multi_reference": len(multi_ref)}
    print("[numbers] %s" % numbers)

    # ----- Log lines for the hand-read (stdout only) -----
    empties_pub, k = [], 0
    for n in sorted(inc):
        for iid, vals in inc[n]["summary"]["empties"]:
            empties_pub.append({"run": n, "instance_id": iid, "published": vals})
            k += 1
            if k <= C.PRINT_EMPTIES:
                print("[empty %d] run=%s id=%s published=%s" % (k, n, iid, vals))
    k = 0
    punct_pub = []
    for n in sorted(inc):
        for iid, vals, text in inc[n]["summary"]["punct"]:
            punct_pub.append({"run": n, "instance_id": iid, "published": vals})
            k += 1
            if k <= C.PRINT_PUNCT:
                print("[punct %d] run=%s id=%s published=%s text=%r" % (k, n, iid, vals, (text or "")[:80]))

    out = {
        "audit": 93,
        "slug": "ahelm-asr-empty-predictions",
        "dataset": ("Per-instance outputs of AHELM (HELM audio) suite %s, Stanford CRFM: every run listed on the "
                    "run-group pages %s, first trial. Only run names, instance ids, metric names, classes, counts and "
                    "public model names are published." % (C.SUITE, ", ".join(C.GROUPS))),
        "fixture": fx,
        "p1_parts": p1_parts,
        "group_errors": group_err,
        "runs_listed": len(all_runs),
        "runs_reproduced": [n_rep, len(all_runs)],
        "cells_reproduced": [cell_ok_n, cell_n],
        "totals": totals,
        "by_group": by_group,
        "by_model": by_model,
        "ranks": ranks,
        "predictions": verdicts,
        "prediction_numbers": numbers,
        "cells": cells_out,
        "multi_reference_runs": multi_ref,
        "runs": runs_out,
        "note": ("An output is empty when its text is empty after strip(); HELM's wer/mer/cer (and chinese_*) then "
                 "return 0, the best value. Corrected = the same mean with each empty output valued 1.0 (jiwer's value "
                 "for an empty hypothesis; the fix proposed in HELM issue #4359 and PR #4361). A headline cell is the "
                 "mean of its runs' wer_score means. P2 >= 1 empty output and every one has a published 0; P3 >= 50% "
                 "of empty outputs come from Gemini models; P4 empty outputs <= 1% of records; P5 at least one "
                 "headline WER cell rises by >= 0.01; P6 at least one model changes rank in a group table; P7 no "
                 "included run has more than one reference per instance on average."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "empties.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 93, "note": ("Every first-trial AHELM output in the included runs that is empty after "
                   "strip() (scored by HELM's guard) or punctuation-only (passes the guard, normalises to nothing), "
                   "by run name and instance id, with HELM's published per-instance error rates; no text."),
                   "empty": empties_pub, "punct_only": punct_pub}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and empties.json (%d empty, %d punct_only)" % (len(empties_pub), len(punct_pub)))


if __name__ == "__main__":
    main()
