"""Do the BBQ tagging and scaling bugs found in HELM Classic (audit 95) also shape the BBQ bias columns of the current
HELM Safety leaderboard? (audit 97)

Reads HELM Safety release v1.17.0's run index and keeps every BBQ run (method=multiple_choice_joint). Per run it
downloads run_spec.json (method check), instances.json (HELM's tags: polarity, context condition and the correct,
target, non-target and unknown letters), display_predictions.json (each completion) and stats.json (HELM's published
bbq_accuracy, bbq_metric_ambiguous_bias and bbq_metric_unambiguous_bias). It downloads the BBQ data (11 category
files) and the BBQ authors' analysis_scripts/additional_metadata.csv from github.com/nyu-mll/BBQ, joins each HELM test
instance to its BBQ row, and re-computes every run four ways with grade97 (a transcription of HELM's BBQMetric):
  H  = HELM's own rule and tags (must reproduce the published values)
  A  = #4372: the ambiguous bias scaled by (1 - accuracy on ambiguous questions) instead of overall accuracy
  T  = #4368: target / non-target letters from target_loc instead of HELM's string matching
  AT = both fixes.
It also downloads audit 95's published affected.json (HELM Classic) to test whether Safety uses the same sample, and
counts completions that are not exactly one letter. Only run names, instance ids, BBQ keys, categories, letters,
counts and public model names are written to results.json and affected.json; question, answer and model text is
printed to the job log only, for the hand-read.
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import cases97 as C
import grade97 as g

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
    m = g.build_inst_map(C.FIX_INSTANCES)
    trials, counts = g.trial_records(C.FIX_PREDS, m)
    tagfn = lambda i: m[i]["tags"]  # noqa: E731
    idx = g.index_rows(C.FIX_BBQ_ROWS)
    corr = []
    for tags, loc, want in C.FIX_CORRECTED:
        got = g.corrected_tags(tags, loc)
        corr.append((None if got is None else (got["target"], got["nontarget"])) == want)
    only = g.predictions97(C.FIX_V_OVERLAP_FAIL, C.THRESHOLDS)
    return {
        "names": all(g.model_of(r) == mo and g.method_of(r) == me for r, mo, me in C.FIX_NAMES),
        "records": counts == C.FIX_RECORD_COUNTS,
        "trials": all(g.score_trial(trials[k], tagfn) == C.FIX_TRIAL_COUNTS[k]
                      and g.biases(g.score_trial(trials[k], tagfn)) == C.FIX_TRIAL_BIASES[k] for k in (0, 1, 2)),
        "corrected": all(corr),
        "meta": g.parse_meta(C.FIX_META_CSV) == C.FIX_META,
        "join": all(all(g.join(inst, idx, C.FIX_META).get(k) == v for k, v in want.items())
                    for inst, want in C.FIX_JOIN_INST),
        "ranks": g.ranks_low(C.FIX_RANKS_IN) == C.FIX_RANKS_OUT,
        "non_letter": g.non_letter(trials) == C.FIX_NON_LETTER
        and g.non_letter(C.FIX_NON_LETTER_TRIALS) == C.FIX_NON_LETTER_TRIALS_OUT,
        "overlap": g.overlap_count([g.bbq_key(*k) for k in C.FIX_KEYS], C.FIX_REF_KEYS) == C.FIX_OVERLAP,
        "verdicts": all(g.predictions97(C.FIX_V_HELD, C.THRESHOLDS).values())
        and not any(g.predictions97(C.FIX_V_FAIL, C.THRESHOLDS).values())
        and sorted(k for k, v in only.items() if not v) == ["P2_same_sample_as_classic"],
    }


def load_run(item):
    run, suite = item
    rec = {"run": run, "suite": suite, "model": g.model_of(run)}
    try:
        spec = _json(run_url(suite, run, "run_spec.json"))
        rec["method"] = (spec.get("adapter_spec") or {}).get("method")
        rec["max_tokens"] = (spec.get("adapter_spec") or {}).get("max_tokens")
        raw_inst = _json(run_url(suite, run, "instances.json"))
        rec["perturbed_instances"] = sum(1 for i in raw_inst if i.get("perturbation"))
        rec["inst"] = g.build_inst_map([i for i in raw_inst if not i.get("perturbation")])
        preds = _json(run_url(suite, run, "display_predictions.json"))
        rec["perturbed_records"] = sum(1 for p in preds if p.get("perturbation"))
        rec["trials"], rec["counts"] = g.trial_records([p for p in preds if not p.get("perturbation")], rec["inst"])
        stats = _json(run_url(suite, run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    rec["published"] = {"acc": g.stat_mean(stats, "bbq_accuracy"),
                        "amb": g.stat_mean(stats, "bbq_metric_ambiguous_bias"),
                        "disamb": g.stat_mean(stats, "bbq_metric_unambiguous_bias")}
    return run, rec


def close(a, b):
    return a is not None and b is not None and abs(a - b) <= C.TOL


def sign(x):
    return (x > 0) - (x < 0)


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

    # ----- BBQ source data -----
    rows = []
    for cat in C.BBQ_CATEGORIES:
        part = g.parse_jsonl(_get("%s/data/%s.jsonl" % (C.BBQ_BASE, cat)).decode("utf-8"))
        print("[bbq] %s rows=%d" % (cat, len(part)))
        rows.extend(part)
    meta = g.parse_meta(_get(C.BBQ_META).decode("utf-8"))
    n_na = sum(1 for v in meta.values() if v is None)
    n_conf = sum(1 for v in meta.values() if v == g.CONFLICT)
    print("[meta] keys=%d na=%d conflict=%d" % (len(meta), n_na, n_conf))
    idx = g.index_rows(rows)
    del rows

    # ----- Audit 95's HELM Classic affected list -----
    try:
        classic = _json(C.CLASSIC_AFFECTED)["affected"]
        classic_keys = {g.bbq_key(a["category"], a["question_index"], a["example_id"]) for a in classic}
        classic_ids = {a["instance_id"] for a in classic}
        print("[classic] affected=%d keys=%d" % (len(classic), len(classic_keys)))
    except Exception as e:  # noqa: BLE001 - recorded; P2 then fails
        classic_keys, classic_ids = set(), set()
        print("[classic] download failed: %s" % str(e)[:300])

    # ----- HELM runs -----
    index = _json(C.RUNS_INDEX)
    if not isinstance(index, dict):
        raise SystemExit("run index is not a mapping of run name -> suite")
    listed = sorted((r, s) for r, s in index.items() if r.startswith("bbq:") and g.method_of(r) == C.METHOD)
    other_bbq = sorted(r for r in index if r.startswith("bbq:") and g.method_of(r) != C.METHOD)
    print("[index] runs=%d bbq_joint=%d bbq_other_methods=%d" % (len(index), len(listed), len(other_bbq)))
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(load_run, listed))

    # ----- Join every distinct test instance once -----
    insts, text_conflicts = {}, 0
    for run, _ in listed:
        r = loaded[run]
        for iid, inst in (r.get("inst") or {}).items():
            if inst.get("split") != "test":
                continue
            if iid in insts and (insts[iid]["text"], insts[iid]["refs"]) != (inst["text"], inst["refs"]):
                text_conflicts += 1
                continue
            insts.setdefault(iid, inst)
    joins, status_counts, by_cat = {}, {}, {}
    for iid in sorted(insts):
        j = g.join(insts[iid], idx, meta)
        if j["status"] == "matched":
            j["corrected"] = g.corrected_tags(insts[iid]["tags"], j["target_loc"])
        joins[iid] = j
        status_counts[j["status"]] = status_counts.get(j["status"], 0) + 1
    del idx

    affected, unaff_n, unaff_agree, label_bad, rxg_rows, rxg_nonempty, kept = [], 0, 0, 0, 0, 0, 0
    for iid in sorted(joins):
        j, t = joins[iid], insts[iid]["tags"]
        cat = j.get("category")
        if cat is not None:
            d = by_cat.setdefault(cat, {"joined": 0, "matched": 0, "affected": 0, "helm_target_empty": 0})
            d["joined"] += 1
            d["helm_target_empty"] += 1 if t["target"] == "" else 0
            if cat == "Race_x_gender":
                rxg_nonempty += 1 if t["target"] != "" else 0
        if j["status"] != "matched":
            continue
        by_cat[cat]["matched"] += 1
        label_bad += 0 if j["label_ok"] else 1
        if cat == "Race_x_gender":
            rxg_rows += 1
        c = j["corrected"]
        if c is None:
            kept += 1
            continue
        if cat not in g.AFFECTED:
            unaff_n += 1
            unaff_agree += 1 if c["target"] == t["target"] else 0
        if c["target"] != t["target"]:
            by_cat[cat]["affected"] += 1
            affected.append({"instance_id": iid, "category": cat, "example_id": j["example_id"],
                             "question_index": j["question_index"], "negative": t["neg"], "ambiguous": t["amb"],
                             "helm": [t["correct"], t["target"], t["nontarget"], t["unknown"]],
                             "corrected_target": c["target"], "corrected_nontarget": c["nontarget"]})
    aff_keys = [g.bbq_key(a["category"], a["question_index"], a["example_id"]) for a in affected]
    classic_overlap = g.overlap_count(aff_keys, classic_keys)
    id_overlap = sum(1 for a in affected if a["instance_id"] in classic_ids)
    n_test = len(insts)
    print("[instances] test=%d text_conflicts=%d join=%s label_mismatch=%d kept_helm_tags=%d" % (
        n_test, text_conflicts, status_counts, label_bad, kept))
    print("[unaffected categories] target agrees %d of %d" % (unaff_agree, unaff_n))
    print("[affected] %d (Race_x_gender matched=%d, HELM target non-empty in Race_x_gender=%d)" % (
        len(affected), rxg_rows, rxg_nonempty))
    print("[classic overlap] by BBQ key %d of %d distinct; by HELM instance id %d" % (
        classic_overlap, len(set(aff_keys)), id_overlap))
    print("[by category] %s" % dict(sorted(by_cat.items())))

    def tag_t(iid):
        j = joins.get(iid)
        if j and j["status"] == "matched" and j.get("corrected") is not None:
            return j["corrected"]
        return insts[iid]["tags"]

    # ----- Re-score every run -----
    runs_out, inc, non_letter_samples = {}, {}, []
    for run, _ in listed:
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "error": r["error"]}
            continue
        local = r["inst"]
        trials = {k: [(i, c) for i, c in v if i in insts or i in local] for k, v in r["trials"].items()}
        h_tag = lambda i, local=local: insts[i]["tags"] if i in insts else local[i]["tags"]  # noqa: E731
        t_tag = lambda i, local=local: tag_t(i) if i in insts else local[i]["tags"]  # noqa: E731
        _, h = g.run_scores(trials, h_tag)
        _, t = g.run_scores(trials, t_tag)
        bad, tot = g.non_letter(trials)
        pub = r["published"]
        ok = close(h["acc"], pub["acc"]) and close(h["amb_overall_acc"], pub["amb"]) and \
            close(h["disamb"], pub["disamb"])
        method_ok = r["method"] == C.METHOD
        one_trial = sorted(trials) == [0]
        row = {"status": "included" if (ok and method_ok and one_trial) else "excluded", "suite": r["suite"],
               "model": r["model"], "method": r["method"], "max_tokens": r.get("max_tokens"),
               "trials": len(trials), "counts": r["counts"], "perturbed_instances": r["perturbed_instances"],
               "perturbed_records": r["perturbed_records"], "non_letter": [bad, tot],
               "published": pub, "H": h, "T": t}
        if not method_ok:
            row["reason"] = "method_mismatch"
        elif not one_trial:
            row["reason"] = "not_one_trial"
        elif not ok:
            row["reason"] = "not_reproduced"
        runs_out[run] = row
        if bad and len([s for s in non_letter_samples if s[0] == r["model"]]) < 2 and \
                len(non_letter_samples) < C.PRINT_NON_LETTER:
            for k in sorted(trials):
                for i, comp in trials[k]:
                    if comp not in g.LETTERS and len([s for s in non_letter_samples if s[0] == r["model"]]) < 2:
                        non_letter_samples.append((r["model"], i, comp))
        if row["status"] == "included":
            row["amb_H"] = h["amb_overall_acc"]
            row["amb_A"] = h["amb_amb_acc"]
            row["amb_T"] = t["amb_overall_acc"]
            row["amb_AT"] = t["amb_amb_acc"]
            row["disamb_H"] = h["disamb"]
            row["disamb_T"] = t["disamb"]
            inc[run] = row
    n_inc = len(inc)
    inc_share = n_inc / len(listed) if listed else 0.0
    joined_share = status_counts.get("matched", 0) / n_test if n_test else 0.0
    p1_parts = {"fixtures": all(fx.values()), "runs_listed": len(listed) >= C.MIN_RUNS,
                "included": inc_share >= C.MIN_INCLUDED, "joined": joined_share >= C.MIN_JOINED,
                "labels_agree": label_bad == 0,
                "unaffected_agree": unaff_n > 0 and unaff_agree >= C.MIN_UNAFFECTED_AGREE * unaff_n}
    print("[runs] listed=%d included=%d (%.4f)" % (len(listed), n_inc, inc_share))
    for run in sorted(runs_out):
        ro = runs_out[run]
        if ro["status"] != "included":
            print("[excluded] %s %s trials=%s pub=%s H=%s" % (run, ro.get("reason") or ro.get("error"),
                                                             ro.get("trials"), ro.get("published"), ro.get("H")))
    print("[P1] %s" % p1_parts)
    if inc_share < C.ABORT_INCLUDED:
        with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
            json.dump({"audit": 97, "aborted": True, "fixture": fx, "p1_parts": p1_parts, "runs": runs_out,
                       "join": status_counts}, fh, indent=1, ensure_ascii=True)
        raise SystemExit("inclusion gate failed -- aborting (diagnostics in results.json)")

    # ----- Predictions -----
    models = {inc[r]["model"]: inc[r] for r in inc}
    vh = {k: m["amb_H"] for k, m in models.items()}
    vat = {k: m["amb_AT"] for k, m in models.items()}
    dh = {k: m["disamb_H"] for k, m in models.items()}
    dt = {k: m["disamb_T"] for k, m in models.items()}
    rh, rat = g.ranks_low(vh), g.ranks_low(vat)
    mn = C.THRESHOLDS["P7_min_abs"]
    flips = sorted(k for k in models if abs(vh[k]) >= mn and abs(vat[k]) >= mn and sign(vh[k]) != sign(vat[k]))
    p8 = sorted(k for k, m in models.items() if m["non_letter"][1] and
                m["non_letter"][0] >= C.THRESHOLDS["P8_share"] * m["non_letter"][1])
    nums = {"affected": len(affected), "rxg_rows": rxg_rows, "rxg_nonempty_target": rxg_nonempty,
            "classic_overlap": classic_overlap, "models": len(models),
            "disamb_neg": sum(1 for k in models if dh[k] < 0),
            "p4_median": g.median([abs(dt[k] - dh[k]) for k in models]),
            "p5_med_T": g.median([abs(dt[k]) for k in models]), "p5_med_H": g.median([abs(dh[k]) for k in models]),
            "p6_tau": g.kendall_tau_b(vh, vat), "p7_flips": len(flips), "p8_models": len(p8)}
    verdicts = g.predictions97(nums, C.THRESHOLDS)
    verdicts["P1_structural"] = all(p1_parts.values())
    for name in sorted(verdicts):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    print("[numbers] %s" % nums)

    # ----- Exploratory -----
    va = {k: m["amb_A"] for k, m in models.items()}
    vt = {k: m["amb_T"] for k, m in models.items()}
    rdh, rdt = g.ranks_low(dh), g.ranks_low(dt)
    expl = {"tau_amb_H_vs_A": g.kendall_tau_b(vh, va), "tau_amb_H_vs_T": g.kendall_tau_b(vh, vt),
            "tau_disamb_H_vs_T": g.kendall_tau_b(dh, dt),
            "median_amb_AT_move": g.median([abs(vat[k] - vh[k]) for k in models]),
            "amb_rank_moves_max": max((abs(rat[k] - rh[k]) for k in models), default=0),
            "disamb_rank_moves_max": max((abs(rdt[k] - rdh[k]) for k in models), default=0),
            "disamb_T_positive": sum(1 for k in models if dt[k] > 0),
            "amb_H_positive": sum(1 for k in models if vh[k] > 0),
            "amb_AT_positive": sum(1 for k in models if vat[k] > 0),
            "sign_flips_amb_H_vs_AT": flips,
            "sign_flips_disamb_H_vs_T": sorted(k for k in models if abs(dh[k]) >= mn and abs(dt[k]) >= mn
                                               and sign(dh[k]) != sign(dt[k])),
            "models_non_letter_at_least_1pct": p8,
            "classic_overlap_by_instance_id": id_overlap,
            "excluded_runs": sorted(r for r in runs_out if runs_out[r]["status"] != "included")}
    print("[exploratory] %s" % expl)
    table = sorted(({"model": k, "suite": models[k]["suite"], "rank_amb_H": rh[k], "rank_amb_AT": rat[k],
                     "rank_disamb_H": rdh[k], "rank_disamb_T": rdt[k], "amb_H": vh[k], "amb_A": va[k],
                     "amb_T": vt[k], "amb_AT": vat[k], "disamb_H": dh[k], "disamb_T": dt[k],
                     "acc": models[k]["H"]["acc"], "amb_acc": models[k]["H"]["amb_acc"],
                     "non_letter": models[k]["non_letter"]} for k in models),
                   key=lambda x: (x["rank_disamb_H"], x["model"]))
    for row in table:
        print("[model] %s" % row)

    # ----- Hand-read lines (stdout only) -----
    for k, a in enumerate(affected[:C.PRINT_AFFECTED], 1):
        inst = insts[a["instance_id"]]
        print("[affected %d] %s refs=%r text_tail=%r" % (k, a, inst["refs"], inst["text"][-160:]))
    for k, (model, iid, comp) in enumerate(non_letter_samples, 1):
        print("[non-letter %d] model=%s id=%s completion=%r" % (k, model, iid, comp[:120]))

    out = {
        "audit": 97,
        "slug": "helm-safety-bbq-bias-regrade",
        "dataset": ("Per-record outputs of HELM Safety release %s (Stanford CRFM), every BBQ run with method "
                    "multiple_choice_joint, joined to the BBQ data and analysis_scripts/additional_metadata.csv of "
                    "github.com/nyu-mll/BBQ (CC BY 4.0). Only ids, categories, letters, counts and public model names "
                    "are published." % C.RELEASE),
        "fixture": fx,
        "p1_parts": p1_parts,
        "runs_listed": len(listed),
        "bbq_runs_other_methods": len(other_bbq),
        "runs_included": n_inc,
        "test_instances": n_test,
        "text_conflicts": text_conflicts,
        "join": status_counts,
        "label_mismatch": label_bad,
        "kept_helm_tags": kept,
        "unaffected_categories_target_agree": [unaff_agree, unaff_n],
        "by_category": by_cat,
        "classic_overlap": {"by_bbq_key": classic_overlap, "distinct_affected_keys": len(set(aff_keys)),
                            "by_instance_id": id_overlap, "classic_affected": len(classic_keys)},
        "meta_keys": [len(meta), n_na, n_conf],
        "predictions": verdicts,
        "prediction_numbers": nums,
        "exploratory": expl,
        "models": table,
        "runs": runs_out,
        "note": ("H = HELM's BBQMetric with HELM's tags (reproduces the published values); A = ambiguous bias scaled by "
                 "1 - accuracy on ambiguous questions (#4372); T = target and non-target letters from the BBQ "
                 "authors' target_loc (#4368); AT = both. Ranks: 1 + number of models with a strictly lower value "
                 "(HELM marks the BBQ bias columns lower-is-better). non_letter = [completions that are not exactly "
                 "A, B or C after strip, completions HELM keeps]."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "affected.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 97, "note": "Every HELM Safety BBQ test instance whose target letter differs between "
                   "HELM's tags and the BBQ authors' target_loc: HELM instance id, BBQ category / example_id / "
                   "question_index, polarity, context condition, HELM's [correct, target, non-target, unknown] letters "
                   "and the corrected target and non-target letters; no text.", "affected": affected}, fh, indent=1,
                  ensure_ascii=True)
    print("[done] wrote results.json and affected.json (%d affected)" % len(affected))


if __name__ == "__main__":
    main()
