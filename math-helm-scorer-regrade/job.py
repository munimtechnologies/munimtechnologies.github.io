"""How often does HELM Lite's MATH scorer grade an answer wrongly, in both directions? (audit 91)

Downloads every math: run of HELM Lite release v1.13.0 (instances.json and display_predictions.json; one run per model
and subject, 7 subjects, level 1, chain of thought), re-grades every first-trial prediction with H (HELM's
is_equiv_chain_of_thought, transcribed) and A (the corrected grade, grade91.py), and reports the flips by class, per-
model macro accuracies and ranks under H and A, the references HELM cannot extract an answer from, and the
pre-registered verdicts. Prints a seeded sample of flips with the end of each output for the hand-read check (P8,
graded next run); only ids, classes, routes, counts and public model names are written to results.json and
flips.json.

Gates before any verdict: the hand-traced fixtures match; a run is included when it scores at least 95% of its test
instances, every scored item carries HELM's recorded score and our H equals it on at least 99% of them; a model is
included when all 7 subject runs are included; at least 80 models; H equals HELM on at least 99.9% overall; the
reference answer of a (subject, instance id) is the same in every included run for at least 99% of them.
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import json
import os
import random
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import grade91 as g
import cases91 as C

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
    grades = all((lambda r: (r["h"], r["a"], r["route"], g.flip_class(r)) == (h, a, route, cls))(g.grade(gd, pr))
                 for gd, pr, h, a, route, cls in C.FIX_GRADE)
    tau = all((g.kendall_tau_b(x, y) is None) if w is None else abs(g.kendall_tau_b(x, y) - w) < 1e-12
              for x, y, w in C.FIX_TAU)
    return {
        "grades": grades,
        "values": all(g.value(s) == w for s, w in C.FIX_VALUE),
        "unboxed": all(g.unboxed_candidate(p) == w for p, w in C.FIX_UNBOXED),
        "runs": g.select_runs(C.FIX_RUNS, C.HELM_PREFIX) == C.FIX_RUNS_TARGET,
        "ranks": g.min_ranks(C.FIX_ACC) == C.FIX_RANKS and tau,
        "verdicts": all(g.predictions91(*a, C.THRESHOLDS) == w for a, w in C.FIX_V_CASES),
    }


def load_run(item):
    """One (model, subject) run -> (key, record) with counts, H and A totals, flips (with the output text kept in
    memory only for the printed sample), the reference answer per instance id, and gate counts."""
    (model, subject), (run, suite) = item
    rec = {"run": run, "suite": suite}
    try:
        inst = _json(run_url(suite, run, "instances.json"))
        preds = _json(run_url(suite, run, "display_predictions.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return (model, subject), rec
    gold = {}
    for it in inst or []:
        if not isinstance(it, dict) or it.get("split") != "test":
            continue
        refs = it.get("references") or []
        correct = [r for r in refs if "correct" in (r.get("tags") or [])]
        if len(correct) == 1:
            gold[it.get("id")] = (correct[0].get("output") or {}).get("text") or ""
    c = {"n_gold": len(gold), "n_pred": 0, "other_trial": 0, "no_gold": 0, "duplicate": 0, "scored": 0,
         "consistent": 0, "inconsistent": 0, "no_stat": 0}
    tot = {"h": 0, "a": 0, "h_both_none": 0, "pred_unboxed": 0, "gold_none": 0}
    routes, flips, answers, seen = {}, [], {}, set()
    for p in preds or []:
        if not isinstance(p, dict):
            continue
        c["n_pred"] += 1
        if p.get("train_trial_index", 0) != 0:
            c["other_trial"] += 1
            continue
        iid = p.get("instance_id")
        if iid not in gold:
            c["no_gold"] += 1
            continue
        if iid in seen:
            c["duplicate"] += 1
            continue
        seen.add(iid)
        text = p.get("predicted_text") or ""
        r = g.grade(gold[iid], text)
        c["scored"] += 1
        answers[iid] = g.get_answer(gold[iid])
        stat = (p.get("stats") or {}).get(C.STAT)
        if stat is None:
            c["no_stat"] += 1
        elif int(round(float(stat))) == r["h"]:
            c["consistent"] += 1
        else:
            c["inconsistent"] += 1
        tot["h"] += r["h"]
        tot["a"] += r["a"]
        tot["h_both_none"] += 1 if (r["both_none"] and r["h"] == 1) else 0
        tot["pred_unboxed"] += 1 if r["helm_pred_answer"] is None else 0
        tot["gold_none"] += 1 if r["gold_src"] != "boxed" else 0
        routes[r["route"]] = routes.get(r["route"], 0) + 1
        cls = g.flip_class(r)
        if cls is not None:
            flips.append({"model": model, "subject": subject, "instance_id": iid,
                          "direction": "up" if r["a"] else "down", "class": cls, "route": r["route"],
                          "_gold": r["gold_answer"], "_helm_pred": r["helm_pred_answer"], "_cand": r["candidate"],
                          "_text": text})
    rec.update({"counts": c, "totals": tot, "routes": routes, "flips": flips, "answers": answers})
    return (model, subject), rec


def share(a, n):
    return float(Fraction(a, n)) if n else None


def show(f):
    """One flip for the hand-read sample (stdout only; never written to the published files)."""
    t = f["_text"]
    return ("model=%s subject=%s id=%s class=%s route=%s gold=%r helm_pred=%r candidate=%r\n    tail=%r"
            % (f["model"], f["subject"], f["instance_id"], f["class"], f["route"], f["_gold"], f["_helm_pred"],
               f["_cand"], t[-300:]))


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
    chosen, dropped = g.select_runs(run_suites, C.HELM_PREFIX)
    models_all = sorted({m for m, _ in chosen})
    subjects_seen = sorted({s for _, s in chosen})
    print("[helm] runs=%d models=%d subjects=%s (dropped %d duplicate runs)"
          % (len(chosen), len(models_all), subjects_seen, dropped))
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(load_run, sorted(chosen.items())))

    # ----- Inclusion and gates -----
    run_ok, runs_out = {}, {}
    for k in sorted(loaded):
        r = loaded[k]
        name = "%s|%s" % k
        if "error" in r:
            runs_out[name] = {"run": r["run"], "suite": r["suite"], "status": "download_failed", "error": r["error"]}
            run_ok[k] = False
            continue
        c = r["counts"]
        checked = c["consistent"] + c["inconsistent"]
        cons = Fraction(c["consistent"], checked) if checked else Fraction(0)
        ok = (c["n_gold"] > 0 and Fraction(c["scored"], c["n_gold"]) >= C.MIN_RUN_SCORED and c["no_stat"] == 0
              and cons >= C.MIN_RUN_CONSISTENT)
        run_ok[k] = ok
        runs_out[name] = {"run": r["run"], "suite": r["suite"], "counts": c, "scorer_consistent": float(cons),
                          "status": "included" if ok else "excluded"}
    inc = [m for m in models_all if all(run_ok.get((m, s), False) for s in C.SUBJECTS)]
    inc_keys = [(m, s) for m in inc for s in C.SUBJECTS]
    all_cons = sum(loaded[k]["counts"]["consistent"] for k in inc_keys)
    all_checked = all_cons + sum(loaded[k]["counts"]["inconsistent"] for k in inc_keys)
    overall_cons = Fraction(all_cons, all_checked) if all_checked else Fraction(0)
    ans_seen, ans_conflict = {}, set()
    for k in inc_keys:
        for iid, a in loaded[k]["answers"].items():
            q = (k[1], iid)
            if q in ans_seen and ans_seen[q] != a:
                ans_conflict.add(q)
            ans_seen.setdefault(q, a)
    gold_agree = Fraction(len(ans_seen) - len(ans_conflict), len(ans_seen)) if ans_seen else Fraction(0)
    gold_none = sorted("%s|%s" % q for q, a in ans_seen.items() if a is None)
    p1_parts = {"fixtures": all(fx.values()), "models": len(inc) >= C.MIN_MODELS,
                "consistent": overall_cons >= C.MIN_ALL_CONSISTENT, "gold_agree": gold_agree >= C.MIN_GOLD_AGREE}
    print("[models] included=%d of %d; overall scorer consistency %d/%d; questions %d; reference conflicts %d; "
          "references without an extractable answer %d" % (len(inc), len(models_all), all_cons, all_checked,
                                                             len(ans_seen), len(ans_conflict), len(gold_none)))
    print("[P1] %s" % p1_parts)
    if not (p1_parts["models"] and p1_parts["consistent"]):
        with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
            json.dump({"audit": 91, "aborted": True, "fixture": fx, "p1_parts": p1_parts, "runs": runs_out},
                      fh, indent=1, ensure_ascii=True)
        raise SystemExit("inclusion or consistency gate failed -- aborting (diagnostics in results.json)")

    # ----- Totals and flips -----
    T = {k: sum(loaded[x]["totals"][k] for x in inc_keys) for k in loaded[inc_keys[0]]["totals"]}
    n_all = sum(loaded[x]["counts"]["scored"] for x in inc_keys)
    routes = {}
    for x in inc_keys:
        for rt, v in loaded[x]["routes"].items():
            routes[rt] = routes.get(rt, 0) + v
    flips = [f for x in inc_keys for f in loaded[x]["flips"]]
    up = [f for f in flips if f["direction"] == "up"]
    down = [f for f in flips if f["direction"] == "down"]
    net = T["a"] - T["h"]
    classes, by_subject = {}, {}
    for f in flips:
        classes.setdefault(f["direction"], {}).setdefault(f["class"], 0)
        classes[f["direction"]][f["class"]] += 1
        d = by_subject.setdefault(f["subject"], {"up": 0, "down": 0})
        d[f["direction"]] += 1
    print("[totals] predictions=%d H=%d A=%d net(A-H)=%d up=%d down=%d H_both_none=%d pred_unboxed=%d routes=%s"
          % (n_all, T["h"], T["a"], net, len(up), len(down), T["h_both_none"], T["pred_unboxed"], routes))
    print("[classes] %s" % classes)
    print("[by subject] %s" % by_subject)
    print("[references without an extractable answer] %s" % gold_none)

    # ----- Per-model macro accuracy (mean of the 7 subject accuracies) and ranks -----
    acc_h, acc_a, rows = {}, {}, []
    for m in inc:
        sh = [Fraction(loaded[(m, s)]["totals"]["h"], loaded[(m, s)]["counts"]["scored"]) for s in C.SUBJECTS]
        sa = [Fraction(loaded[(m, s)]["totals"]["a"], loaded[(m, s)]["counts"]["scored"]) for s in C.SUBJECTS]
        acc_h[m], acc_a[m] = sum(sh) / len(sh), sum(sa) / len(sa)
    rk_h, rk_a = g.min_ranks(acc_h), g.min_ranks(acc_a)
    moved = 0
    for m in inc:
        mv = rk_h[m] - rk_a[m]
        if abs(mv) >= C.THRESHOLDS["P6_min_move"]:
            moved += 1
        mf = [f for f in up + down if f["model"] == m]
        n_m = sum(loaded[(m, s)]["counts"]["scored"] for s in C.SUBJECTS)
        unb = sum(loaded[(m, s)]["totals"]["pred_unboxed"] for s in C.SUBJECTS)
        rows.append({"model": m, "n": n_m, "H": float(acc_h[m]), "A": float(acc_a[m]),
                     "gain_A_minus_H": float(acc_a[m] - acc_h[m]), "rank_H": rk_h[m], "rank_A": rk_a[m],
                     "rank_move_up": mv, "up_flips": sum(1 for f in mf if f["direction"] == "up"),
                     "down_flips": sum(1 for f in mf if f["direction"] == "down"),
                     "unboxed_share": share(unb, n_m)})
    rows.sort(key=lambda r: (r["rank_A"], r["model"]))

    unboxed_up = classes.get("up", {}).get("unboxed", 0)
    value_up = classes.get("up", {}).get("value_format", 0)
    verdicts = g.predictions91(net, n_all, unboxed_up, value_up, len(gold_none), moved, len(up), len(down),
                               C.THRESHOLDS)
    verdicts["P1_structural"] = all(p1_parts.values())
    for name in sorted(verdicts):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    numbers = {"P2_net_and_predictions": [net, n_all, share(net, n_all)], "P3_unboxed_up": unboxed_up,
               "P4_value_format_up": value_up, "P5_references_without_answer": len(gold_none),
               "P6_models_moving_3": moved, "P7_up_down": [len(up), len(down)]}
    print("[numbers] %s" % numbers)

    # ----- Exploratory -----
    order = sorted(inc)
    tau = g.kendall_tau_b([acc_h[m] for m in order], [acc_a[m] for m in order])
    top_h = sorted(m for m in inc if rk_h[m] <= 10)
    top_a = sorted(m for m in inc if rk_a[m] <= 10)
    biggest = sorted(rows, key=lambda r: (-r["gain_A_minus_H"], r["model"]))[:10]
    per_model_up = sorted((sum(1 for f in up if f["model"] == m) for m in inc), reverse=True)
    expl = {"kendall_tau_b_H_vs_A": tau, "top10_H": top_h, "top10_A": top_a,
            "top10_entered": sorted(set(top_a) - set(top_h)), "top10_left": sorted(set(top_h) - set(top_a)),
            "micro_accuracy_H": share(T["h"], n_all), "micro_accuracy_A": share(T["a"], n_all),
            "macro_mean_H": float(sum(acc_h.values()) / len(acc_h)),
            "macro_mean_A": float(sum(acc_a.values()) / len(acc_a)),
            "pred_unboxed_share": share(T["pred_unboxed"], n_all),
            "up_flips_top10_models_share": share(sum(per_model_up[:10]), len(up)),
            "largest_gains": [{k: r[k] for k in ("model", "H", "A", "rank_H", "rank_A", "unboxed_share")}
                              for r in biggest]}
    print("[exploratory] %s" % expl)

    # ----- The hand-read sample (P8) -----
    rng = random.Random(C.SAMPLE_SEED)
    key = lambda f: (f["model"], f["subject"], str(f["instance_id"]))  # noqa: E731
    s_up = rng.sample(sorted(up, key=key), min(C.SAMPLE_UP, len(up)))
    s_down = rng.sample(sorted(down, key=key), min(C.SAMPLE_DOWN, len(down)))
    for i, f in enumerate(s_up, 1):
        print("[sample-up %d] %s" % (i, show(f)))
    for i, f in enumerate(s_down, 1):
        print("[sample-down %d] %s" % (i, show(f)))

    pub = [{k: v for k, v in f.items() if not k.startswith("_")} for f in sorted(flips, key=key)]
    out = {
        "audit": 91,
        "slug": "math-helm-scorer-regrade",
        "dataset": ("Per-question MATH outputs of HELM Lite release %s (Stanford CRFM), every math: run (7 subjects, "
                    "level 1, chain of thought), first trial. Only subjects, instance ids, classes, routes, grades, "
                    "counts and public model names are published." % C.HELM_RELEASE),
        "fixture": fx,
        "p1_parts": p1_parts,
        "n_models_included": len(inc),
        "n_predictions": n_all,
        "n_questions": len(ans_seen),
        "scorer_consistency": [all_cons, all_checked],
        "reference_conflicts": len(ans_conflict),
        "references_without_answer": gold_none,
        "totals": T,
        "routes": routes,
        "classes": classes,
        "by_subject": by_subject,
        "predictions": verdicts,
        "prediction_numbers": numbers,
        "exploratory": expl,
        "per_model": rows,
        "runs": runs_out,
        "sample_up": [key(f) for f in s_up],
        "sample_down": [key(f) for f in s_down],
        "note": ("H = HELM's is_equiv_chain_of_thought as transcribed (gated against HELM's recorded score); A = the "
                 "corrected grade (grade91.py). Up-flip: H 0, A 1; down-flip: H 1, A 0. Macro accuracy = mean of the "
                 "7 subject accuracies; rank = 1 + models strictly more accurate. P2 net A - H >= 0.5% of "
                 "predictions; P3 >= 100 unboxed up-flips; P4 >= 20 value_format up-flips; P5 >= 1 reference with "
                 "no answer HELM can extract; P6 >= 5 models move >= 3 places; P7 5 x down-flips <= up-flips; P8 "
                 "(read next run) >= 27 of 30 sampled up-flips are genuine."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "flips.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 91, "note": ("Every prediction whose corrected grade (A) differs from HELM's grade (H), "
                   "by public model name, subject and HELM instance id; no question, answer or model text."),
                   "flips": pub}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and flips.json (%d flips)" % len(pub))


if __name__ == "__main__":
    main()
