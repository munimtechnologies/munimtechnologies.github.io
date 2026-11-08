"""How often does HELM Lite's GSM8K scorer grade an answer wrongly, in both directions? (audit 90)

Downloads every gsm: run of HELM Lite release v1.13.0 (instances.json and display_predictions.json, about 90 models x
1,000 questions), re-grades every first-trial prediction with four graders (grade90.py: H = HELM's scorer as
transcribed, F = PR #4341's regex, N = F compared as numbers, A = the stated answer compared as a number), and reports
the flips between H and A by class, per-model accuracies and GSM8K ranks under H and A, and the pre-registered
verdicts. Prints a seeded sample of flips with the end of each model output for the hand-read check (P7, graded next
run); only numbers, ids, classes and public model names are written to results.json and flips.json.

Gates before any prediction is scored: the hand-traced fixtures match; every included run has at least 990 scored
predictions and our transcription of H equals HELM's recorded final_number_exact_match on at least 99% of them (and
99.9% overall); at least 85 runs are included; the reference answer of an instance id is the same in every run.
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

import grade90 as g
import cases90 as C

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
    grades = True
    for gold, pred, hfna, hf, ff, st, src, cls in C.FIX_GRADE:
        r = g.grade(gold, pred)
        grades = grades and ((r["h"], r["f"], r["n"], r["a"]) == hfna and r["helm_final"] == hf
                             and r["fixed_final"] == ff and (r["stated"], r["source"]) == (st, src)
                             and g.flip_class(r) == cls)
    tau = all((g.kendall_tau_b(x, y) is None) if w is None else abs(g.kendall_tau_b(x, y) - w) < 1e-12
              for x, y, w in C.FIX_TAU)
    return {
        "grades": grades,
        "numbers": all(g.to_num(s) == w for s, w in C.FIX_TO_NUM),
        "runs": g.select_runs(C.FIX_RUNS) == C.FIX_RUNS_TARGET and all(g.is_stop_none(r) == w for r, w in C.FIX_STOP),
        "ranks": g.min_ranks(C.FIX_ACC) == C.FIX_RANKS and tau,
        "verdicts": all(g.predictions90(*a, C.THRESHOLDS) == w for a, w in C.FIX_V_CASES),
    }


def load_run(item):
    """One model's run -> (model, record) with per-grader correct counts, flips (with the output text, kept in memory
    only for the printed sample), the gold final number per instance id, and gate counts."""
    model, (run, suite) = item
    rec = {"run": run, "suite": suite, "stop_none": g.is_stop_none(run)}
    try:
        inst = _json(run_url(suite, run, "instances.json"))
        preds = _json(run_url(suite, run, "display_predictions.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return model, rec
    gold = {}
    for it in inst or []:
        if not isinstance(it, dict) or it.get("split") != "test":
            continue
        refs = it.get("references") or []
        correct = [r for r in refs if "correct" in (r.get("tags") or [])]
        if len(correct) == 1:
            gold[it.get("id")] = (correct[0].get("output") or {}).get("text") or ""
    c = {"n_pred": 0, "other_trial": 0, "no_gold": 0, "duplicate": 0, "scored": 0, "consistent": 0,
         "inconsistent": 0, "no_stat": 0}
    tot = {"h": 0, "f": 0, "n": 0, "a": 0, "h0_f0_n1": 0, "f_up": 0, "f_down": 0, "phrase": 0, "boxed": 0,
           "last": 0}
    flips, keys, seen = [], {}, set()
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
        keys[iid] = r["key"]
        stat = (p.get("stats") or {}).get("final_number_exact_match")
        if stat is None:
            c["no_stat"] += 1
        elif int(round(float(stat))) == r["h"]:
            c["consistent"] += 1
        else:
            c["inconsistent"] += 1
        for k in ("h", "f", "n", "a"):
            tot[k] += r[k]
        tot[r["source"]] += 1
        if r["h"] == 0 and r["f"] == 0 and r["n"] == 1:
            tot["h0_f0_n1"] += 1
        if r["h"] == 0 and r["f"] == 1:
            tot["f_up"] += 1
        if r["h"] == 1 and r["f"] == 0:
            tot["f_down"] += 1
        cls = g.flip_class(r)
        if cls is not None:
            flips.append({"model": model, "instance_id": iid, "direction": "up" if r["a"] else "down", "class": cls,
                          "key": r["key"], "helm_final": r["helm_final"], "fixed_final": r["fixed_final"],
                          "stated": r["stated"], "source": r["source"], "_text": text})
    rec.update({"counts": c, "totals": tot, "flips": flips, "keys": keys})
    return model, rec


def share(a, n):
    return float(Fraction(a, n)) if n else None


def show(f):
    """One flip for the hand-read sample: ids, numbers, the text around the first 'answer is' and the last 220
    characters of the output (stdout only; never written to the published files)."""
    t = f["_text"]
    i = t.lower().find("answer is")
    ctx = t[max(0, i - 120): i + 60] if i >= 0 else ""
    return ("model=%s id=%s class=%s key=%s helm_final=%r fixed_final=%r stated=%r source=%s\n    ctx=%r\n    tail=%r"
            % (f["model"], f["instance_id"], f["class"], f["key"], f["helm_final"], f["fixed_final"], f["stated"],
               f["source"], ctx, t[-220:]))


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
    print("[helm] runs=%d (dropped %d duplicate runs)" % (len(chosen), dropped))
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(load_run, sorted(chosen.items())))

    # ----- Inclusion and gates -----
    models_out, inc = {}, []
    all_cons = all_checked = 0
    for m in sorted(loaded):
        r = loaded[m]
        if "error" in r:
            models_out[m] = {"run": r["run"], "suite": r["suite"], "status": "download_failed", "error": r["error"]}
            continue
        c = r["counts"]
        checked = c["consistent"] + c["inconsistent"]
        cons = Fraction(c["consistent"], checked) if checked else Fraction(0)
        ok = c["scored"] >= C.MIN_PREDICTIONS and checked == c["scored"] and cons >= C.MIN_RUN_CONSISTENT
        models_out[m] = {"run": r["run"], "suite": r["suite"], "stop_none": r["stop_none"], "counts": c,
                         "scorer_consistent": float(cons), "status": "included" if ok else "excluded"}
        if ok:
            inc.append(m)
            all_cons += c["consistent"]
            all_checked += checked
    gold_seen, gold_conflicts = {}, 0
    for m in inc:
        for iid, k in loaded[m]["keys"].items():
            if iid in gold_seen and gold_seen[iid] != k:
                gold_conflicts += 1
            gold_seen.setdefault(iid, k)
    overall_cons = Fraction(all_cons, all_checked) if all_checked else Fraction(0)
    p1_parts = {"fixtures": all(fx.values()), "runs": len(chosen) == C.EXPECTED_RUNS,
                "included": len(inc) >= C.MIN_INCLUDED, "consistent": overall_cons >= C.MIN_ALL_CONSISTENT,
                "gold_conflicts": gold_conflicts == 0}
    print("[models] included=%d of %d; overall scorer consistency %d/%d; gold conflicts %d; questions %d"
          % (len(inc), len(models_out), all_cons, all_checked, gold_conflicts, len(gold_seen)))
    print("[P1] %s" % p1_parts)
    if not (p1_parts["included"] and p1_parts["consistent"]):
        with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
            json.dump({"audit": 90, "aborted": True, "fixture": fx, "p1_parts": p1_parts, "models": models_out},
                      fh, indent=1, ensure_ascii=True)
        raise SystemExit("inclusion or consistency gate failed -- aborting (diagnostics in results.json)")

    # ----- Totals, flips, replication -----
    T = {k: sum(loaded[m]["totals"][k] for m in inc) for k in loaded[inc[0]]["totals"]}
    n_all = sum(loaded[m]["counts"]["scored"] for m in inc)
    flips = [f for m in inc for f in loaded[m]["flips"]]
    up = [f for f in flips if f["direction"] == "up"]
    down = [f for f in flips if f["direction"] == "down"]
    net = T["a"] - T["h"]
    replication = {"F_up": T["f_up"], "F_down": T["f_down"], "reported_4337": C.REPLICATION_4337,
                   "matches": T["f_up"] == C.REPLICATION_4337["up"] and T["f_down"] == C.REPLICATION_4337["down"]}
    print("[replication #4337] %s" % replication)
    print("[totals] predictions=%d H=%d F=%d N=%d A=%d net(A-H)=%d up=%d down=%d H0F0N1=%d sources=%s"
          % (n_all, T["h"], T["f"], T["n"], T["a"], net, len(up), len(down), T["h0_f0_n1"],
             {k: T[k] for k in ("phrase", "boxed", "last")}))
    classes = {}
    for f in flips:
        grp = "stop_none" if loaded[f["model"]]["stop_none"] else "other"
        d = classes.setdefault(f["direction"], {}).setdefault(f["class"], {"stop_none": 0, "other": 0, "all": 0})
        d[grp] += 1
        d["all"] += 1
    print("[classes] %s" % classes)

    # ----- Per-model accuracy and ranks -----
    acc_h, acc_a, rows = {}, {}, []
    for m in inc:
        t, n = loaded[m]["totals"], loaded[m]["counts"]["scored"]
        acc_h[m], acc_a[m] = Fraction(t["h"], n), Fraction(t["a"], n)
    rk_h, rk_a = g.min_ranks(acc_h), g.min_ranks(acc_a)
    gains = {"stop_none": [Fraction(0), 0], "other": [Fraction(0), 0]}
    moved = 0
    for m in inc:
        t, n = loaded[m]["totals"], loaded[m]["counts"]["scored"]
        grp = "stop_none" if loaded[m]["stop_none"] else "other"
        gains[grp][0] += acc_a[m] - acc_h[m]
        gains[grp][1] += 1
        mv = rk_h[m] - rk_a[m]
        if abs(mv) >= C.THRESHOLDS["P5_min_move"]:
            moved += 1
        ups = sum(1 for f in loaded[m]["flips"] if f["direction"] == "up")
        rows.append({"model": m, "stop_none": loaded[m]["stop_none"], "n": n, "H": share(t["h"], n),
                     "F": share(t["f"], n), "N": share(t["n"], n), "A": share(t["a"], n),
                     "gain_A_minus_H": float(acc_a[m] - acc_h[m]), "rank_H": rk_h[m], "rank_A": rk_a[m],
                     "rank_move_up": mv, "up_flips": ups, "down_flips": len(loaded[m]["flips"]) - ups,
                     "phrase_share": share(t["phrase"], n), "boxed_share": share(t["boxed"], n)})
        models_out[m]["accuracy_H"] = share(t["h"], n)
    rows.sort(key=lambda r: (r["rank_A"], r["model"]))

    verdicts = g.predictions90(net, T["h0_f0_n1"], tuple(gains["stop_none"]), tuple(gains["other"]), moved,
                               len(up), len(down), C.THRESHOLDS)
    verdicts["P1_structural"] = all(p1_parts.values())
    for name in sorted(verdicts):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    mean_gain = {k: (float(v[0] / v[1]) if v[1] else None, v[1]) for k, v in gains.items()}
    numbers = {"P2_net": net, "P3_H0_F0_N1": T["h0_f0_n1"], "P4_mean_gain_stop_none_other": mean_gain,
               "P5_models_moving_5": moved, "P6_up_down": [len(up), len(down)]}
    print("[numbers] %s" % numbers)

    # ----- Exploratory -----
    order = sorted(inc)
    tau = g.kendall_tau_b([acc_h[m] for m in order], [acc_a[m] for m in order])
    top_h = sorted(m for m in inc if rk_h[m] <= 10)
    top_a = sorted(m for m in inc if rk_a[m] <= 10)
    biggest = sorted(rows, key=lambda r: (-r["gain_A_minus_H"], r["model"]))[:10]
    expl = {"kendall_tau_b_H_vs_A": tau, "top10_H": top_h, "top10_A": top_a,
            "top10_entered": sorted(set(top_a) - set(top_h)), "top10_left": sorted(set(top_h) - set(top_a)),
            "mean_accuracy_H": share(T["h"], n_all), "mean_accuracy_A": share(T["a"], n_all),
            "mean_accuracy_F": share(T["f"], n_all), "mean_accuracy_N": share(T["n"], n_all),
            "largest_gains": [{k: r[k] for k in ("model", "stop_none", "H", "A", "rank_H", "rank_A")} for r in biggest],
            "phrase_share_all": share(T["phrase"], n_all)}
    print("[exploratory] %s" % expl)

    # ----- The hand-read sample (P7) -----
    rng = random.Random(C.SAMPLE_SEED)
    key = lambda f: (f["model"], str(f["instance_id"]))  # noqa: E731
    s_up = rng.sample(sorted(up, key=key), min(C.SAMPLE_UP, len(up)))
    s_down = rng.sample(sorted(down, key=key), min(C.SAMPLE_DOWN, len(down)))
    for i, f in enumerate(s_up, 1):
        print("[sample-up %d] %s" % (i, show(f)))
    for i, f in enumerate(s_down, 1):
        print("[sample-down %d] %s" % (i, show(f)))

    pub = [{k: v for k, v in f.items() if k != "_text"} for f in sorted(flips, key=key)]
    out = {
        "audit": 90,
        "slug": "gsm8k-helm-scorer-regrade",
        "dataset": ("Per-question GSM8K outputs of HELM Lite release %s (Stanford CRFM), every gsm: run, first trial. "
                    "Only instance ids, final numbers, grades, counts and public model names are published." %
                    C.HELM_RELEASE),
        "fixture": fx,
        "p1_parts": p1_parts,
        "n_included": len(inc),
        "n_predictions": n_all,
        "n_questions": len(gold_seen),
        "scorer_consistency": [all_cons, all_checked],
        "totals": T,
        "replication_4337": replication,
        "classes": classes,
        "predictions": verdicts,
        "prediction_numbers": numbers,
        "exploratory": expl,
        "per_model": rows,
        "models": models_out,
        "sample_up": [key(f) for f in s_up],
        "sample_down": [key(f) for f in s_down],
        "note": ("H = HELM's final_number_exact_match as transcribed (gated against HELM's recorded score); F = PR "
                 "#4341's regex, string comparison; N = F's last number vs the key as numbers; A = the number after "
                 "the first 'answer is' (any case), else the last \\boxed{} number, else F's last number, vs the key "
                 "as numbers. Up-flip: H 0, A 1; down-flip: H 1, A 0. Ranks: 1 + models strictly more accurate. "
                 "P2 net A - H >= 900; P3 H 0, F 0, N 1 on >= 100; P4 mean gain of stop=none runs > other runs (>= 5 "
                 "each); P5 >= 5 models move >= 5 ranks; P6 5 x down-flips <= up-flips; P7 (read next run) >= 27 of "
                 "30 sampled up-flips are genuine rescues."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "flips.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 90, "note": ("Every prediction where the stated-answer grade (A) differs from HELM's grade "
                   "(H), by public model name and HELM instance id; numbers only, no question or model text."),
                   "flips": pub}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and flips.json (%d flips)" % len(pub))


if __name__ == "__main__":
    main()
