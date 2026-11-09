"""How much do HELM's MedCalc-Bench scoring gaps change MedHELM's published scores? (audit 96)

Downloads every medcalc_bench run of MedHELM release v4.0.0 (instances.json and display_predictions.json), re-grades
every first-trial prediction with H (HELM's MedCalcBenchMetric, transcribed), R (H plus HELM issue #4351's range
check for lab and dosage) and C (R plus a duration-format rule and a same-value rule), and reports totals by category,
up-flips by class, outputs that are not a plain number, per-model accuracies and ranks, and the pre-registered
verdicts. Prints a hand-read sample of up-flips (output and reference text) to stdout only; results.json and
flips.json hold only model names, instance ids, categories, classes and counts.

Gates before any verdict: the hand-traced fixtures match; a run is included when at most 1% of its first-trial
predictions lack an instance with a reference, it scores at least 95% of the median run's count, every scored
prediction carries HELM's medcalc_bench_accuracy and our H equals it on at least 99%; at least 12 included models;
H equals HELM on at least 99.9% of all included predictions.
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import hashlib
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import cases96 as C
import grade96 as g

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
CATS = ("lab", "physical", "risk", "severity", "date", "diagnosis", "dosage")
CLASSES = ("range_lab", "range_dosage", "duration_format", "same_value")


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
    def grade_ok(row):
        pred, ref, extra, cat, h, r, c, cls = row
        return g.grade(pred, ref, extra, cat) == {"h": h, "r": r, "c": c, "cls": cls}

    tau = all((g.kendall_tau_b(x, y) is None) if w is None else abs(g.kendall_tau_b(x, y) - w) < 1e-12
              for x, y, w in C.FIX_TAU)
    return {
        "helm": all(g.helm_score(p, r, e, c) == w for p, r, e, c, w in C.FIX_HELM),
        "grades": all(grade_ok(row) for row in C.FIX_GRADE),
        "rounded_only": all(g.rounded_only(p, r) == w for p, r, w in C.FIX_ROUND),
        "durations": all(g.duration_days(p) == w for p, w in C.FIX_DAYS),
        "runs": g.select_runs(C.FIX_RUNS, C.PREFIX) == C.FIX_RUNS_TARGET,
        "ranks": g.min_ranks(C.FIX_ACC) == C.FIX_RANKS and tau,
        "verdicts": all(g.predictions96(*a, C.THRESHOLDS) == w for a, w in C.FIX_V_CASES),
    }


def _zero():
    return {"n": 0, "H": 0, "R": 0, "C": 0, "not_number": 0, "rounded_only": 0}


def load_run(item):
    """One model's run -> (model, record) with gate counts, per-category totals, up-flips and sample texts."""
    (model, _s), (run, suite) = item
    rec = {"run": run, "suite": suite}
    try:
        inst = _json(run_url(suite, run, "instances.json"))
        preds = _json(run_url(suite, run, "display_predictions.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return model, rec
    gold = {}
    for it in inst or []:
        if not isinstance(it, dict) or it.get("split") == "train":
            continue
        refs = it.get("references") or []
        extra = it.get("extra_data") or {}
        if refs and "category" in extra:
            gold[str(it.get("id"))] = ((refs[0].get("output") or {}).get("text") or "", extra)
    c = {"n_pred": 0, "other_trial": 0, "trial0": 0, "no_gold": 0, "duplicate": 0, "scored": 0, "consistent": 0,
         "inconsistent": 0, "no_stat": 0}
    cats, flips, texts, seen, inconsistent_ids = {}, [], {}, set(), []
    for p in preds or []:
        if not isinstance(p, dict):
            continue
        c["n_pred"] += 1
        if p.get("train_trial_index", 0) != 0:
            c["other_trial"] += 1
            continue
        c["trial0"] += 1
        iid = str(p.get("instance_id"))
        if iid not in gold:
            c["no_gold"] += 1
            continue
        if iid in seen:
            c["duplicate"] += 1
            continue
        seen.add(iid)
        ref, extra = gold[iid]
        cat = extra.get("category")
        text = p.get("predicted_text")
        r = g.grade(text, ref, extra, cat)
        c["scored"] += 1
        stat = (p.get("stats") or {}).get(C.METRIC)
        if stat is None:
            c["no_stat"] += 1
        elif int(round(float(stat))) == r["h"]:
            c["consistent"] += 1
        else:
            c["inconsistent"] += 1
            if len(inconsistent_ids) < 20:
                inconsistent_ids.append(iid)
        d = cats.setdefault(cat, _zero())
        d["n"] += 1
        d["H"] += r["h"]
        d["R"] += r["r"]
        d["C"] += r["c"]
        if cat in g.RANGE_CATEGORIES and g.plain_number(text) is None:
            d["not_number"] += 1
        if cat in g.EXACT_CATEGORIES and r["h"] == 0 and g.rounded_only(text, ref):
            d["rounded_only"] += 1
        if r["cls"] is not None:
            flips.append({"model": model, "instance_id": iid, "category": cat, "class": r["cls"]})
            texts[iid] = {"pred": (text or "")[:100], "ref": ref[:60],
                          "lo": str(extra.get("lower_limit"))[:40], "hi": str(extra.get("upper_limit"))[:40]}
    rec.update({"counts": c, "categories": cats, "flips": flips, "_texts": texts,
                "inconsistent_ids": inconsistent_ids})
    return model, rec


def frac(a, n):
    return Fraction(a, n) if n else Fraction(0)


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
    sel, dropped = g.select_runs(run_suites, C.PREFIX)
    print("[helm] medcalc_bench runs=%d models=%d (dropped %d duplicate runs)"
          % (len(sel), len({m for m, _ in sel}), dropped))
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(load_run, sorted(sel.items())))

    # ----- Inclusion and gates -----
    counts = sorted(r["counts"]["scored"] for r in loaded.values() if "error" not in r)
    med = counts[len(counts) // 2] if counts else 0
    inc, runs_out = [], {}
    for m in sorted(loaded):
        r = loaded[m]
        if "error" in r:
            runs_out[m] = {"run": r["run"], "suite": r["suite"], "status": "download_failed", "error": r["error"]}
            continue
        c = r["counts"]
        checked = c["consistent"] + c["inconsistent"]
        cons = frac(c["consistent"], checked)
        ok = (c["scored"] > 0 and c["no_gold"] <= C.MAX_RUN_NO_GOLD * c["trial0"]
              and c["scored"] >= C.MIN_RUN_SCORED_VS_MEDIAN * med and c["no_stat"] == 0
              and cons >= C.MIN_RUN_CONSISTENT)
        runs_out[m] = {"run": r["run"], "suite": r["suite"], "counts": c, "scorer_consistent": float(cons),
                       "inconsistent_ids": r["inconsistent_ids"], "status": "included" if ok else "excluded"}
        if ok:
            inc.append(m)
    all_cons = sum(loaded[m]["counts"]["consistent"] for m in inc)
    all_checked = all_cons + sum(loaded[m]["counts"]["inconsistent"] for m in inc)
    overall = frac(all_cons, all_checked)
    p1_parts = {"fixtures": all(fx.values()), "models": len(inc) >= C.MIN_MODELS,
                "consistent": all_checked > 0 and overall >= C.MIN_ALL_CONSISTENT}
    print("[models] included %d of %d; overall scorer consistency %d/%d" % (len(inc), len(loaded), all_cons,
                                                                              all_checked))
    print("[P1] %s" % p1_parts)
    if not (p1_parts["models"] and p1_parts["consistent"]):
        with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
            json.dump({"audit": 96, "aborted": True, "fixture": fx, "p1_parts": p1_parts, "runs": runs_out},
                      fh, indent=1, ensure_ascii=True)
        raise SystemExit("inclusion or consistency gate failed -- aborting (diagnostics in results.json)")

    # ----- Totals by category and up-flips by class -----
    by_cat = {}
    for m in inc:
        for cat, d in loaded[m]["categories"].items():
            t = by_cat.setdefault(cat, _zero())
            for k in t:
                t[k] += d[k]
    flips = [f for m in inc for f in loaded[m]["flips"]]
    by_class = {k: sum(1 for f in flips if f["class"] == k) for k in CLASSES}
    n_all = sum(t["n"] for t in by_cat.values())
    tot = {k: sum(t[k] for t in by_cat.values()) for k in ("H", "R", "C")}
    print("[categories] %s" % {k: by_cat[k] for k in sorted(by_cat)})
    print("[totals] predictions=%d H=%d R=%d C=%d up-flips by class %s" % (n_all, tot["H"], tot["R"], tot["C"],
                                                                         by_class))

    # ----- Per-model accuracy (mean over instances, as HELM's medcalc_bench_accuracy) and ranks -----
    acc = {"H": {}, "R": {}, "C": {}}
    rows = []
    for m in inc:
        cats = loaded[m]["categories"]
        n = sum(d["n"] for d in cats.values())
        for k in acc:
            acc[k][m] = frac(sum(d[k] for d in cats.values()), n)
        n_range = sum(cats[x]["n"] for x in g.RANGE_CATEGORIES if x in cats)
        nn = sum(cats[x]["not_number"] for x in g.RANGE_CATEGORIES if x in cats)
        rows.append({"model": m, "n": n, "H": float(acc["H"][m]), "R": float(acc["R"][m]), "C": float(acc["C"][m]),
                     "gain_R": float(acc["R"][m] - acc["H"][m]), "gain_C": float(acc["C"][m] - acc["H"][m]),
                     "range_outputs": n_range, "range_not_number": nn,
                     "range_not_number_share": float(frac(nn, n_range)),
                     "by_category": {k: {"n": cats[k]["n"], "H": cats[k]["H"], "R": cats[k]["R"], "C": cats[k]["C"]}
                                     for k in sorted(cats)},
                     "up_flips": {k: sum(1 for f in loaded[m]["flips"] if f["class"] == k) for k in CLASSES}})
    rk = {k: g.min_ranks(acc[k]) for k in acc}
    for row in rows:
        row["rank_H"], row["rank_R"], row["rank_C"] = rk["H"][row["model"]], rk["R"][row["model"]], rk["C"][row["model"]]
    rows.sort(key=lambda r: (r["rank_H"], r["model"]))
    order = sorted(inc)
    tau_hc = g.kendall_tau_b([acc["H"][m] for m in order], [acc["C"][m] for m in order])
    tau_hr = g.kendall_tau_b([acc["H"][m] for m in order], [acc["R"][m] for m in order])
    changed = sum(1 for m in inc if rk["H"][m] != rk["C"][m])
    print("[ranks] tau_b(H,R)=%s tau_b(H,C)=%s models whose rank changes H->C: %d" % (tau_hr, tau_hc, changed))
    for row in rows:
        print("[model] %s H=%.3f R=%.3f C=%.3f rank %d->%d not_number=%d/%d"
              % (row["model"], row["H"], row["R"], row["C"], row["rank_H"], row["rank_C"], row["range_not_number"],
                 row["range_outputs"]))

    # ----- Verdicts -----
    h_lab_dosage = sum(by_cat.get(x, _zero())["H"] for x in ("lab", "dosage"))
    gains_r = [acc["R"][m] - acc["H"][m] for m in order]
    n_exact = sum(by_cat.get(x, _zero())["n"] for x in g.EXACT_CATEGORIES)
    n_fmt = sum(1 for row in rows if row["range_outputs"]
                and Fraction(row["range_not_number"], row["range_outputs"]) >= C.THRESHOLDS["P7_share"])
    verdicts = g.predictions96(h_lab_dosage, gains_r, by_class["duration_format"], by_class["same_value"], n_exact,
                               changed, n_fmt, C.THRESHOLDS)
    verdicts["P1_structural"] = all(p1_parts.values())
    for name in sorted(verdicts):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    mean_gain = sum(gains_r) / len(gains_r)
    numbers = {"P2_lab_dosage_H_credits": h_lab_dosage,
               "P3_mean_and_min_gain_R": [float(mean_gain), float(min(gains_r))],
               "P4_duration_format_upflips": by_class["duration_format"],
               "P5_same_value_upflips_and_exact_predictions": [by_class["same_value"], n_exact],
               "P6_models_rank_changed": changed, "P7_models_range_not_number_10pct": n_fmt}
    print("[numbers] %s" % numbers)

    # ----- Hand-read sample: up to SAMPLE_PER_CLASS up-flips per class, chosen by a hash (stdout only) -----
    sample = []
    for k in CLASSES:
        fk = sorted((f for f in flips if f["class"] == k),
                    key=lambda f: hashlib.sha1(("%s|%s" % (f["model"], f["instance_id"])).encode()).hexdigest())
        sample.extend(fk[:C.SAMPLE_PER_CLASS])
    for n, f in enumerate(sample, 1):
        print("[sample %d] class=%s model=%s id=%s category=%s texts=%r"
              % (n, f["class"], f["model"], f["instance_id"], f["category"],
                 loaded[f["model"]]["_texts"][f["instance_id"]]))

    out = {
        "audit": 96,
        "slug": "medcalc-helm-scorer-regrade",
        "dataset": ("Per-instance outputs of MedHELM release %s (Stanford CRFM): every medcalc_bench run, first trial. "
                    "Only model names, instance ids, categories, classes and counts are published." % C.HELM_RELEASE),
        "fixture": fx,
        "p1_parts": p1_parts,
        "n_models_included": len(inc),
        "scorer_consistency": [all_cons, all_checked],
        "categories": {k: by_cat[k] for k in sorted(by_cat)},
        "totals": {"predictions": n_all, "H": tot["H"], "R": tot["R"], "C": tot["C"], "up_flips_by_class": by_class},
        "ranks": {"kendall_tau_b_H_vs_R": tau_hr, "kendall_tau_b_H_vs_C": tau_hc, "models_rank_changed_H_to_C": changed},
        "predictions": verdicts,
        "prediction_numbers": numbers,
        "per_model": rows,
        "sample_ids": [{"model": f["model"], "instance_id": f["instance_id"], "class": f["class"]} for f in sample],
        "runs": runs_out,
        "note": ("H = HELM's MedCalcBenchMetric (transcribed), gated against HELM's recorded medcalc_bench_accuracy; "
                 "R = H plus a range check for lab and dosage (#4351); C = R plus whole-string (weeks, days) tuples in "
                 "other forms within the limits and numbers equal in value to a numeric risk/severity/diagnosis "
                 "reference. rounded_only (exploratory, not in C) counts risk/severity/diagnosis outputs that equal an "
                 "integer reference only after rounding. P2 H credits no lab or dosage prediction; P3 mean R - H gain "
                 ">= 5 points and every model >= 2; P4 120-175 duration_format up-flips; P5 same_value up-flips < 1% "
                 "of risk/severity/diagnosis predictions; P6 >= 3 models change rank H -> C; P7 >= 3 models have >= "
                 "10% of lab/dosage/physical outputs that are not a plain number."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "flips.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 96, "note": ("Every prediction the corrected grade C credits and HELM's score H does not, "
                                         "by model, HELM instance id, category and class; no text."),
                   "flips": sorted(flips, key=lambda f: (f["model"], f["class"], f["instance_id"]))},
                  fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and flips.json (%d up-flips)" % len(flips))


if __name__ == "__main__":
    main()
