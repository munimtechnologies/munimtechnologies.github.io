"""How many GPT-4o judge ratings does AHELM drop silently from its published means? (audit 98, HELM issue #4345)

Reads the three run-group pages of AHELM suite v1.0.0 whose main metric is gpt4_audio_critique (HELM's
schema_audio.yaml), takes every run they list, downloads each run's run_spec.json, stats.json and
display_predictions.json, and compares the number of judge ratings HELM averaged (stats.json count) with the number
it requested (num_instances x num_respondents). Each missing rating is an instance whose judge reply HELM could not
parse (or got no reply for); HELM leaves it out of the mean. The job re-values each dropped rating at 1 (the lowest
rating), recomputes every run mean and every headline cell, re-ranks each group table (higher is better) and reports
the pre-registered verdicts. Only run names, instance ids, output classes, counts and public model names are written
to results.json and unjudged.json; model output text is printed to the job log only, for the hand-read.

Gates before any verdict: the hand-traced fixtures match; all 3 group pages load; at least 50 runs; at least 95% of
listed runs download, have num_respondents 1, list every instance once, and reproduce HELM's count and mean
(within 1e-6); at least 90% of headline cells are rebuilt from their runs (pooled or mean of means, within 1e-6).
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import cases98 as C
import grade98 as g

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
    s = g.summarize_run(C.FIX_RECORDS)
    t = C.FIX_RUN_TARGET
    return {
        "models": all(g.model_of(r) == m for r, m in C.FIX_MODEL),
        "classes": all(g.output_class(x) == w for x, w in C.FIX_CLASS),
        "run_summary": all(s[k] == t[k] for k in t),
        "stats": all(g.stat_entry(C.FIX_STATS, n) == w for n, w in C.FIX_STAT_TARGET.items()),
        "respondents": all(g.num_respondents(sp) == w for sp, w in C.FIX_SPECS),
        "corrected": all(g.corrected_mean(*a) == w for a, w in C.FIX_CORRECTED),
        "cells": (g.judge_cells(C.FIX_GROUP) == C.FIX_GROUP_CELLS and g.judge_cells(C.FIX_GROUP_NO_COL) is None),
        "rules": all(g.cell_rule(v, rs, 1e-9) == w for (v, rs), w in C.FIX_RULES),
        "cell_values": all(g.cell_value(rl, rs) == w for (rl, rs), w in C.FIX_CELL_VALUES),
        "ranks": g.ranks_high(C.FIX_RANKS_IN) == C.FIX_RANKS_OUT,
        "topk": g.top_k_sum(C.FIX_TOPK[0], C.FIX_TOPK[1]) == C.FIX_TOPK[2],
        "verdicts": all(g.predictions98(*a, C.THRESHOLDS) == w for a, w in C.FIX_V_CASES),
    }


def load_run(run):
    rec = {"run": run, "model": g.model_of(run)}
    try:
        spec = _json(run_url(run, "run_spec.json"))
        stats = _json(run_url(run, "stats.json"))
        preds = _json(run_url(run, "display_predictions.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    s = g.summarize_run(preds)
    want = {iid for iid, _ in s["unjudged"]} | {iid for iid, _ in s["rating_text"]}
    texts = {}
    for r in preds or []:
        if (isinstance(r, dict) and r.get("train_trial_index", 0) == 0 and r.get("perturbation") is None
                and r.get("instance_id") in want and r.get("instance_id") not in texts):
            texts[r.get("instance_id")] = r.get("predicted_text")
    ni = g.stat_entry(stats, "num_instances")
    rec.update({"summary": s, "texts": texts, "respondents": g.num_respondents(spec),
                "judge": g.stat_entry(stats, g.JUDGE_METRIC),
                "num_instances": None if ni is None else ni.get("mean")})
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

    group_runs, group_cells, group_err = {}, {}, {}
    for grp in C.GROUPS:
        try:
            doc = _json("%s/runs/%s/groups/%s.json" % (C.HELM_BASE, C.SUITE, grp))
        except Exception as e:  # noqa: BLE001
            group_err[grp] = str(e)[:200]
            continue
        cells = g.judge_cells(doc)
        group_cells[grp] = cells or []
        names = set()
        for _, _, rn in cells or []:
            names.update(rn)
        group_runs[grp] = sorted(names)
        print("[group] %s cells=%s runs=%d" % (grp, None if cells is None else len(cells), len(names)))
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
        s, j, ni, nr = r["summary"], r["judge"], r["num_instances"], r["respondents"]
        ours = s["sum"] / s["judged"] if s["judged"] else None
        reasons = []
        if j is None or j.get("count") is None:
            reasons.append("no_judge_stat")
        if nr != 1:
            reasons.append("respondents_%s" % nr)
        if ni is None or s["counts"]["kept"] != int(round(ni)):
            reasons.append("instances")
        if j is not None and j.get("count") is not None and s["judged"] != int(j["count"]):
            reasons.append("count")
        if j is not None and j.get("mean") is not None and (ours is None or abs(ours - j["mean"]) > C.TOL_RUN):
            reasons.append("mean")
        dropped = None if (j is None or j.get("count") is None or ni is None) else int(round(ni)) - int(j["count"])
        row = {"status": "included" if not reasons else "excluded", "reasons": reasons, "model": r["model"],
               "respondents": nr, "num_instances": ni, "counts": s["counts"], "classes": s["classes"],
               "judged": s["judged"], "hist": s["hist"], "published": j, "ours_mean": ours, "dropped": dropped,
               "unjudged_classes": s["unjudged_classes"], "rating_text": len(s["rating_text"]),
               "corrected_mean": (None if dropped is None or j is None or j.get("sum") is None
                                  else g.corrected_mean(j["sum"], int(j["count"]), dropped))}
        runs_out[run] = row
        if not reasons:
            inc[run] = row
    n_inc = len(inc)
    inc_share = Fraction(n_inc, len(all_runs)) if all_runs else Fraction(0)
    print("[runs] listed=%d included=%d (%.4f)" % (len(all_runs), n_inc, float(inc_share)))
    for run in all_runs:
        if runs_out[run]["status"] != "included":
            print("[excluded] %s %s" % (run, runs_out[run].get("reasons") or runs_out[run].get("error")))

    # ----- Headline cells -----
    cells_out, cell_ok, cell_n = {}, 0, 0
    for grp, cells in group_cells.items():
        rows = []
        for label, value, names in cells:
            cell_n += 1
            have = [loaded[n] for n in names if n in loaded and "error" not in loaded[n] and loaded[n]["judge"]
                    and loaded[n]["judge"].get("count")]
            pairs = [(int(x["judge"]["count"]), x["judge"]["sum"]) for x in have]
            rule = g.cell_rule(value, pairs, C.TOL_CELL) if len(have) == len(names) else None
            cell_ok += 1 if rule else 0
            complete = rule is not None and all(n in inc for n in names)
            pub = cor = None
            if complete:
                trip = [(inc[n]["published"]["count"], inc[n]["published"]["sum"], inc[n]["dropped"]) for n in names]
                pub = g.cell_value(rule, [(c, s, 0) for c, s, _ in trip])
                cor = g.cell_value(rule, trip)
            rows.append({"model": label, "published": value, "rule": rule, "complete": complete, "runs": names,
                         "ours_published": pub, "corrected": cor,
                         "fall": None if cor is None else pub - cor,
                         "dropped": sum(inc[n]["dropped"] for n in names if n in inc),
                         "requested": sum(int(round(inc[n]["num_instances"])) for n in names if n in inc)})
        cells_out[grp] = rows
    cell_share = Fraction(cell_ok, cell_n) if cell_n else Fraction(0)
    groups_with_cells = sum(1 for v in group_cells.values() if v)
    p1_parts = {"fixtures": all(fx.values()), "groups": groups_with_cells >= C.MIN_GROUPS_LOADED,
                "runs": len(all_runs) >= C.MIN_RUNS, "runs_included": inc_share >= C.MIN_RUNS_REPRODUCED,
                "cells_rebuilt": cell_share >= C.MIN_CELLS_REPRODUCED}
    print("[cells] rebuilt %d/%d" % (cell_ok, cell_n))
    print("[P1] %s" % p1_parts)
    if groups_with_cells == 0 or inc_share < C.ABORT_RUNS_REPRODUCED:
        with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
            json.dump({"audit": 98, "aborted": True, "fixture": fx, "p1_parts": p1_parts, "group_errors": group_err,
                       "runs": runs_out}, fh, indent=1, ensure_ascii=True)
        raise SystemExit("group or reproduction gate failed -- aborting (diagnostics in results.json)")

    # ----- Census over included runs -----
    requested = sum(int(round(r["num_instances"])) for r in inc.values())
    dropped = sum(r["dropped"] for r in inc.values())
    per_model, by_group = {}, {}
    for r in inc.values():
        per_model[r["model"]] = per_model.get(r["model"], 0) + r["dropped"]
    for grp, names in group_runs.items():
        rs = [inc[n] for n in names if n in inc]
        by_group[grp] = {"runs_listed": len(names), "runs_included": len(rs),
                         "requested": sum(int(round(r["num_instances"])) for r in rs),
                         "dropped": sum(r["dropped"] for r in rs)}
    unj = {c: 0 for c in g.OUTPUT_CLASSES}
    hist = {k: 0 for k in g.HIST_KEYS}
    rating_text_n, rating_text_hist = 0, {k: 0 for k in g.HIST_KEYS + ("unjudged",)}
    for n, r in inc.items():
        for c, v in r["unjudged_classes"].items():
            unj[c] += v
        for k, v in r["hist"].items():
            hist[k] += v
        for iid, v in loaded[n]["summary"]["rating_text"]:
            rating_text_n += 1
            key = "unjudged" if v is None else (str(int(v)) if v == int(v) and 1 <= v <= 5 else "other")
            rating_text_hist[key] += 1
    unjudged_total = sum(unj.values())
    over = sorted(n for n, r in inc.items() if r["dropped"] < 0)
    top3 = g.top_k_sum(per_model, 3)
    totals = {"runs": n_inc, "requested": requested, "dropped": dropped,
              "dropped_share": float(Fraction(dropped, requested)) if requested else None,
              "unjudged_in_predictions": unjudged_total, "unjudged_classes": unj, "rating_hist": hist,
              "runs_with_drops": sum(1 for r in inc.values() if r["dropped"] > 0), "runs_over_requested": over,
              "top3_models_dropped": top3, "rating_text_outputs": rating_text_n,
              "rating_text_hist": rating_text_hist}
    print("[totals] %s" % totals)
    print("[by group] %s" % by_group)
    print("[by model] %s" % {k: per_model[k] for k in sorted(per_model)})

    # ----- Ranks in each group table (complete cells only) -----
    ranks, max_fall, changed_total = {}, None, 0
    for grp, rows in cells_out.items():
        comp = [r for r in rows if r["complete"]]
        rp = g.ranks_high({r["model"]: r["ours_published"] for r in comp})
        rc = g.ranks_high({r["model"]: r["corrected"] for r in comp})
        changed = sorted(m for m in rp if rp[m] != rc[m])
        for r in comp:
            r["rank_published"], r["rank_corrected"] = rp[r["model"]], rc[r["model"]]
            max_fall = r["fall"] if max_fall is None or r["fall"] > max_fall else max_fall
        changed_total += len(changed)
        ranks[grp] = {"complete_cells": len(comp), "cells": len(rows), "models_rank_changed": changed,
                      "max_fall": max((r["fall"] for r in comp), default=None)}
    print("[ranks] %s" % ranks)

    verdicts = g.predictions98(dropped, requested, top3, max_fall, changed_total, unj["empty"], unjudged_total,
                               C.THRESHOLDS)
    verdicts["P1_structural"] = all(p1_parts.values())
    for name in sorted(verdicts):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    numbers = {"P2_dropped": dropped, "P3_dropped_of_requested": [dropped, requested],
               "P4_top3_of_dropped": [top3, dropped], "P5_max_cell_fall": max_fall,
               "P6_models_rank_changed": changed_total, "P7_empty_of_unjudged": [unj["empty"], unjudged_total]}
    print("[numbers] %s" % numbers)

    # ----- Log lines for the hand-read (stdout only) -----
    unjudged_pub, k = [], 0
    for n in sorted(inc):
        for iid, cls in loaded[n]["summary"]["unjudged"]:
            unjudged_pub.append({"run": n, "instance_id": iid, "output_class": cls})
            k += 1
            if k <= C.PRINT_UNJUDGED:
                print("[unjudged %d] run=%s id=%s class=%s text=%r" % (k, n, iid, cls,
                                                                       (loaded[n]["texts"].get(iid) or "")[:160]))
    rating_pub, k = [], 0
    for n in sorted(inc):
        for iid, v in loaded[n]["summary"]["rating_text"]:
            rating_pub.append({"run": n, "instance_id": iid, "published_rating": v})
            k += 1
            if k <= C.PRINT_RATING_TEXT:
                print("[rating-text %d] run=%s id=%s rating=%s text=%r" % (k, n, iid, v,
                                                                           (loaded[n]["texts"].get(iid) or "")[:160]))

    out = {
        "audit": 98,
        "slug": "ahelm-judge-dropped-ratings",
        "dataset": ("Per-instance outputs and stats of AHELM (HELM audio) suite %s, Stanford CRFM: every run listed in "
                    "the GPT-4o Judge Critique column of the run-group pages %s, first trial. Only run names, instance "
                    "ids, output classes, counts and public model names are published." % (C.SUITE, ", ".join(C.GROUPS))),
        "fixture": fx,
        "p1_parts": p1_parts,
        "group_errors": group_err,
        "runs_listed": len(all_runs),
        "runs_included": [n_inc, len(all_runs)],
        "cells_rebuilt": [cell_ok, cell_n],
        "totals": totals,
        "by_group": by_group,
        "by_model": per_model,
        "ranks": ranks,
        "predictions": verdicts,
        "prediction_numbers": numbers,
        "cells": cells_out,
        "runs": runs_out,
        "note": ("requested = num_instances x num_respondents (1 everywhere included); dropped = requested - the "
                 "count of HELM's gpt4_audio_critique stat, i.e. ratings HELM left out of the mean because the judge "
                 "reply had no 'Rating: 1-5' (Stat.add skips None) or no reply came back. corrected = each dropped "
                 "rating counted as 1, the lowest rating. A headline cell is rebuilt by the rule that reproduces it "
                 "(pooled first, then mean of run means). Ranks: higher is better, 1 + number of models strictly "
                 "higher. rating_text = model outputs that already contain a string HELM's judge regex would read "
                 "(HELM issue #4344); exploratory."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "unjudged.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 98, "note": ("Every first-trial AHELM instance in the included runs whose published "
                   "stats carry no gpt4_audio_critique value (the dropped ratings), and every model output that "
                   "already contains a 'Rating: 1-5' string, by run name and instance id; no text."),
                   "unjudged": unjudged_pub, "rating_text": rating_pub}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and unjudged.json (%d unjudged, %d rating_text)" % (len(unjudged_pub),
                                                                                         len(rating_pub)))


if __name__ == "__main__":
    main()
