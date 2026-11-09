"""Does HELM issue #4358 (multiple-choice option collisions) reach HELM Lite's published scores? (audit 92)

Downloads every multiple_choice_joint run of HELM Lite release v1.13.0 for MMLU (5 subjects), MedQA and OpenBookQA
(instances.json and display_predictions.json; one run per model and subject), re-grades every first-trial
prediction with H (HELM's letter -> option text -> main metric, transcribed) and I (option identity), and reports:
the questions whose gold option collides with a wrong option under exact_match, quasi_exact_match and
quasi_prefix_exact_match; the predictions HELM over-credits (H 1, I 0) or under-credits (H 0, I 1); outputs that
map to no option; per-model accuracies and ranks under H and I; and the pre-registered verdicts. Prints the
collision questions (option texts) for the hand-read check; only benchmarks, subjects, instance ids, option letters,
classes, counts and public model names are written to results.json and flips.json.

Gates before any verdict: the hand-traced fixtures match; a run is included when at most 1% of its first-trial
predictions lack a parsable gold, it scores at least 95% of the median run of its (benchmark, subject), every scored
item carries HELM's main metric and our H equals it on at least 99%; a model is included in a benchmark when all of
that benchmark's subject runs are included; at least 80 models per benchmark; H equals HELM on at least 99.9% of all
included predictions; HELM's mapped_output equals our letter -> option text on at least 99.9% of mapped predictions.
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

import grade92 as g
import cases92 as C

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
    fn = {"exact_match": g.exact_match, "quasi_exact_match": g.quasi_exact_match,
          "quasi_prefix_exact_match": g.quasi_prefix_exact_match}

    def grade_ok(row):
        opts, gi, pred, metric, idx, h, i, cls, unm = row
        r = g.grade(opts, gi, pred, metric)
        return (r["idx"], r["h"], r["i"], r["cls"], r["unmapped"]) == (idx, h, i, cls, unm)

    runs_ok = all(g.select_runs(C.FIX_RUNS, C.BENCHES[b]["prefix"], C.BENCHES[b]["must_contain"]) == want
                  for b, want in C.FIX_RUNS_TARGET.items())
    tau = all((g.kendall_tau_b(x, y) is None) if w is None else abs(g.kendall_tau_b(x, y) - w) < 1e-12
              for x, y, w in C.FIX_TAU)
    return {
        "normalize": all(g.normalize_text(t) == w for t, w in C.FIX_NORM),
        "metrics": all(fn[m](a, b) == w for m, a, b, w in C.FIX_METRIC),
        "grades": all(grade_ok(row) for row in C.FIX_GRADE),
        "collisions": all(g.collisions(o, gi) == w and g.gold_norm_empty(o, gi) == e for o, gi, w, e in C.FIX_COLL),
        "runs": runs_ok,
        "ranks": g.min_ranks(C.FIX_ACC) == C.FIX_RANKS and tau,
        "verdicts": all(g.predictions92(*a, C.THRESHOLDS) == w for a, w in C.FIX_V_CASES),
    }


def qhash(text, opts, gold_i):
    """Content identity of a question (stem, options, gold) -- a hash, so no text is kept for every question."""
    h = hashlib.sha1()
    h.update(" ".join((text or "").split()).encode("utf-8"))
    for o in opts:
        h.update(b"\x00" + o.encode("utf-8"))
    h.update(b"\x01" + str(gold_i).encode("ascii"))
    return h.hexdigest()


def load_run(item):
    """One (bench, model, subject) run -> (key, record) with gate counts, H and I totals, flips, unmapped kinds and
    the evaluated questions' collision census (option texts kept only for colliding questions, for stdout)."""
    (bench, model, subject), (run, suite) = item
    metric = C.BENCHES[bench]["metric"]
    rec = {"run": run, "suite": suite}
    try:
        inst = _json(run_url(suite, run, "instances.json"))
        preds = _json(run_url(suite, run, "display_predictions.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return (bench, model, subject), rec
    gold = {}
    for it in inst or []:
        if not isinstance(it, dict) or it.get("split") == "train":
            continue
        refs = it.get("references") or []
        opts = [(r.get("output") or {}).get("text") or "" for r in refs]
        correct = [i for i, r in enumerate(refs) if "correct" in (r.get("tags") or [])]
        if len(correct) == 1 and opts:
            gold[it.get("id")] = (opts, correct[0], (it.get("input") or {}).get("text") or "")
    c = {"n_pred": 0, "other_trial": 0, "trial0": 0, "no_gold": 0, "duplicate": 0, "scored": 0, "consistent": 0,
         "inconsistent": 0, "no_stat": 0, "mapped_checked": 0, "mapped_agree": 0, "mapped_missing": 0}
    tot = {"h": 0, "i": 0, "unmapped": 0}
    unm, flips, questions, seen = {}, [], {}, set()
    for p in preds or []:
        if not isinstance(p, dict):
            continue
        c["n_pred"] += 1
        if p.get("train_trial_index", 0) != 0:
            c["other_trial"] += 1
            continue
        c["trial0"] += 1
        iid = p.get("instance_id")
        if iid not in gold:
            c["no_gold"] += 1
            continue
        if iid in seen:
            c["duplicate"] += 1
            continue
        seen.add(iid)
        opts, gi, text = gold[iid]
        r = g.grade(opts, gi, p.get("predicted_text"), metric)
        c["scored"] += 1
        stat = (p.get("stats") or {}).get(metric)
        if stat is None:
            c["no_stat"] += 1
        elif int(round(float(stat))) == r["h"]:
            c["consistent"] += 1
        else:
            c["inconsistent"] += 1
        if r["idx"] is not None:
            c["mapped_checked"] += 1
            mo = p.get("mapped_output")
            if mo is None:
                c["mapped_missing"] += 1
            elif mo == r["mapped"]:
                c["mapped_agree"] += 1
        tot["h"] += r["h"]
        tot["i"] += r["i"]
        if r["unmapped"] is not None:
            tot["unmapped"] += 1
            unm[r["unmapped"]] = unm.get(r["unmapped"], 0) + 1
        if r["cls"] is not None:
            flips.append({"benchmark": bench, "model": model, "subject": subject, "instance_id": iid,
                          "direction": "over" if r["h"] else "under", "class": r["cls"],
                          "letter": g.LETTERS[r["idx"]], "gold_letter": g.LETTERS[gi]})
        qh = qhash(text, opts, gi)
        if qh not in questions:
            col = g.collisions(opts, gi)
            hit = any(col.values())
            questions[qh] = {"iid": iid, "k": len(opts), "gold_letter": g.LETTERS[gi],
                             "col": {k: [g.LETTERS[j] for j in v] for k, v in col.items()},
                             "gold_norm_empty": g.gold_norm_empty(opts, gi),
                             "_texts": ({"gold": opts[gi][:120],
                                         "others": {g.LETTERS[j]: opts[j][:120] for v in col.values() for j in v}}
                                        if hit else None)}
    rec.update({"counts": c, "totals": tot, "unmapped": unm, "flips": flips, "questions": questions})
    return (bench, model, subject), rec


def share(a, n):
    return float(Fraction(a, n)) if n else None


def g_num(iid):
    """'id42' -> 42 for sorting (10**9 when not of that form)."""
    s = str(iid)
    return int(s[2:]) if s.startswith("id") and s[2:].isdigit() else 10 ** 9


def median(xs):
    s = sorted(xs)
    if not s:
        return 0
    m = len(s) // 2
    return s[m] if len(s) % 2 else Fraction(s[m - 1] + s[m], 2)


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
    chosen = {}
    for b, cfg in C.BENCHES.items():
        sel, dropped = g.select_runs(run_suites, cfg["prefix"], cfg["must_contain"])
        sel = {k: v for k, v in sel.items() if k[1] in cfg["subjects"]}
        print("[helm] %s runs=%d models=%d (dropped %d duplicate runs)"
              % (b, len(sel), len({m for m, _ in sel}), dropped))
        for (m, s), v in sel.items():
            chosen[(b, m, s)] = v
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(load_run, sorted(chosen.items())))

    # ----- Inclusion and gates -----
    med = {}
    for (b, m, s), r in loaded.items():
        if "error" not in r:
            med.setdefault((b, s), []).append(r["counts"]["scored"])
    med = {k: median(v) for k, v in med.items()}
    run_ok, runs_out = {}, {}
    for k in sorted(loaded):
        r = loaded[k]
        name = "%s|%s|%s" % k
        if "error" in r:
            runs_out[name] = {"run": r["run"], "suite": r["suite"], "status": "download_failed", "error": r["error"]}
            run_ok[k] = False
            continue
        c = r["counts"]
        checked = c["consistent"] + c["inconsistent"]
        cons = Fraction(c["consistent"], checked) if checked else Fraction(0)
        ok = (c["scored"] > 0 and c["no_gold"] <= C.MAX_RUN_NO_GOLD * c["trial0"]
              and c["scored"] >= C.MIN_RUN_SCORED_VS_MEDIAN * med[(k[0], k[2])] and c["no_stat"] == 0
              and cons >= C.MIN_RUN_CONSISTENT)
        run_ok[k] = ok
        runs_out[name] = {"run": r["run"], "suite": r["suite"], "counts": c, "scorer_consistent": float(cons),
                          "status": "included" if ok else "excluded"}
    inc = {}
    for b, cfg in C.BENCHES.items():
        models_b = sorted({m for (bb, m, _s) in loaded if bb == b})
        inc[b] = [m for m in models_b if all(run_ok.get((b, m, s), False) for s in cfg["subjects"])]
    inc_keys = [(b, m, s) for b in C.BENCHES for m in inc[b] for s in C.BENCHES[b]["subjects"]]
    all_cons = sum(loaded[k]["counts"]["consistent"] for k in inc_keys)
    all_checked = all_cons + sum(loaded[k]["counts"]["inconsistent"] for k in inc_keys)
    overall_cons = Fraction(all_cons, all_checked) if all_checked else Fraction(0)
    map_agree = sum(loaded[k]["counts"]["mapped_agree"] for k in inc_keys)
    map_checked = sum(loaded[k]["counts"]["mapped_checked"] for k in inc_keys)
    map_share = Fraction(map_agree, map_checked) if map_checked else Fraction(0)
    p1_parts = {"fixtures": all(fx.values()), "models": all(len(inc[b]) >= C.MIN_MODELS for b in C.BENCHES),
                "consistent": overall_cons >= C.MIN_ALL_CONSISTENT, "mapped_output": map_share >= C.MIN_ALL_MAPPED}
    print("[models] included %s; overall scorer consistency %d/%d; mapped_output agreement %d/%d"
          % ({b: "%d of %d" % (len(inc[b]), len({m for (bb, m, _s) in loaded if bb == b})) for b in C.BENCHES},
             all_cons, all_checked, map_agree, map_checked))
    print("[P1] %s" % p1_parts)
    if not (p1_parts["models"] and p1_parts["consistent"]):
        with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
            json.dump({"audit": 92, "aborted": True, "fixture": fx, "p1_parts": p1_parts, "runs": runs_out},
                      fh, indent=1, ensure_ascii=True)
        raise SystemExit("inclusion or consistency gate failed -- aborting (diagnostics in results.json)")

    # ----- Question census (each distinct evaluated question once, by content) -----
    census, qinfo = {}, {}
    for k in inc_keys:
        b, _m, s = k
        for qh, q in loaded[k]["questions"].items():
            qinfo.setdefault((b, s, qh), q)
    over_by_q = {}
    flips = [f for k in inc_keys for f in loaded[k]["flips"]]
    for b in C.BENCHES:
        d = {"questions": 0, "identical": 0, "quasi_only": 0, "prefix_only": 0, "any": 0, "gold_norm_empty": 0,
             "ids_reused_for_other_content": 0}
        ids = {}
        for (bb, s, qh), q in qinfo.items():
            if bb != b:
                continue
            d["questions"] += 1
            for cls in ("identical", "quasi_only", "prefix_only"):
                d[cls] += 1 if q["col"][cls] else 0
            d["any"] += 1 if any(q["col"].values()) else 0
            d["gold_norm_empty"] += 1 if q["gold_norm_empty"] else 0
            ids.setdefault((s, q["iid"]), set()).add(qh)
        d["ids_reused_for_other_content"] = sum(1 for v in ids.values() if len(v) > 1)
        census[b] = d
    print("[census] %s" % census)

    # ----- Totals, flips, unmapped -----
    totals, unmapped_kinds = {}, {}
    for b in C.BENCHES:
        keys = [k for k in inc_keys if k[0] == b]
        n = sum(loaded[k]["counts"]["scored"] for k in keys)
        h = sum(loaded[k]["totals"]["h"] for k in keys)
        i = sum(loaded[k]["totals"]["i"] for k in keys)
        u = sum(loaded[k]["totals"]["unmapped"] for k in keys)
        fb = [f for f in flips if f["benchmark"] == b]
        cls = {}
        for f in fb:
            cls["%s:%s" % (f["direction"], f["class"])] = cls.get("%s:%s" % (f["direction"], f["class"]), 0) + 1
        totals[b] = {"predictions": n, "H": h, "I": i, "H_minus_I": h - i, "unmapped": u,
                     "over": sum(1 for f in fb if f["direction"] == "over"),
                     "under": sum(1 for f in fb if f["direction"] == "under"), "flip_classes": cls}
        kinds = {}
        for k in keys:
            for kk, v in loaded[k]["unmapped"].items():
                kinds[kk] = kinds.get(kk, 0) + v
        unmapped_kinds[b] = kinds
    for f in flips:
        if f["direction"] == "over":
            q = (f["benchmark"], f["subject"], f["instance_id"])
            over_by_q[q] = over_by_q.get(q, 0) + 1
    print("[totals] %s" % totals)
    print("[unmapped kinds] %s" % unmapped_kinds)

    # ----- Per-model accuracy (MMLU: mean of the 5 subject accuracies, as HELM averages) and ranks -----
    per_model, ranks, moved = {}, {}, {}
    for b, cfg in C.BENCHES.items():
        acc_h, acc_i, rows = {}, {}, []
        for m in inc[b]:
            sh = [Fraction(loaded[(b, m, s)]["totals"]["h"], loaded[(b, m, s)]["counts"]["scored"])
                  for s in cfg["subjects"]]
            si = [Fraction(loaded[(b, m, s)]["totals"]["i"], loaded[(b, m, s)]["counts"]["scored"])
                  for s in cfg["subjects"]]
            acc_h[m], acc_i[m] = sum(sh) / len(sh), sum(si) / len(si)
        rk_h, rk_i = g.min_ranks(acc_h), g.min_ranks(acc_i)
        mv = 0
        for m in inc[b]:
            n_m = sum(loaded[(b, m, s)]["counts"]["scored"] for s in cfg["subjects"])
            u_m = sum(loaded[(b, m, s)]["totals"]["unmapped"] for s in cfg["subjects"])
            if abs(rk_h[m] - rk_i[m]) >= C.THRESHOLDS["P4_min_move"]:
                mv += 1
            rows.append({"model": m, "n": n_m, "H": float(acc_h[m]), "I": float(acc_i[m]),
                         "H_minus_I": float(acc_h[m] - acc_i[m]), "rank_H": rk_h[m], "rank_I": rk_i[m],
                         "unmapped": u_m, "unmapped_share": share(u_m, n_m),
                         "over": sum(1 for f in flips if f["benchmark"] == b and f["model"] == m
                                     and f["direction"] == "over")})
        rows.sort(key=lambda r: (r["rank_H"], r["model"]))
        per_model[b] = rows
        order = sorted(inc[b])
        ranks[b] = {"kendall_tau_b_H_vs_I": g.kendall_tau_b([acc_h[m] for m in order], [acc_i[m] for m in order]),
                    "models_moving_3": mv}
        moved[b] = mv
    print("[ranks] %s" % ranks)

    # ----- Verdicts -----
    q_quasi_medqa = census["med_qa"]["quasi_only"]
    q_prefix_all = sum(census[b]["prefix_only"] for b in C.BENCHES)
    q_quasi_all = sum(census[b]["quasi_only"] for b in C.BENCHES)
    q_ident_all = sum(census[b]["identical"] for b in C.BENCHES)
    models_unm = sum(1 for r in per_model["med_qa"] if r["n"] and Fraction(r["unmapped"], r["n"]) >= C.THRESHOLDS["P7_share"])
    verdicts = g.predictions92(q_quasi_medqa, totals["med_qa"]["over"], totals["med_qa"]["predictions"],
                               moved["med_qa"], q_prefix_all, q_quasi_all, q_ident_all, models_unm, C.THRESHOLDS)
    verdicts["P1_structural"] = all(p1_parts.values())
    for name in sorted(verdicts):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    numbers = {"P2_medqa_quasi_only_questions": q_quasi_medqa,
               "P3_medqa_over_and_predictions": [totals["med_qa"]["over"], totals["med_qa"]["predictions"],
                                                 share(totals["med_qa"]["over"], totals["med_qa"]["predictions"])],
               "P4_medqa_models_moving_3": moved["med_qa"],
               "P5_prefix_only_vs_quasi_only_questions": [q_prefix_all, q_quasi_all],
               "P6_identical_questions": q_ident_all, "P7_medqa_models_unmapped_1pct": models_unm}
    print("[numbers] %s" % numbers)

    # ----- Collision questions for the hand-read (stdout only) -----
    by_key = lambda t: (t[0][0], t[0][1], g_num(t[0][2]), str(t[0][2]))  # noqa: E731 - never compares dicts
    hits = sorted((((b, s, q["iid"]), q) for (b, s, _qh), q in qinfo.items()
                   if q["col"]["identical"] or q["col"]["quasi_only"]), key=by_key)
    for n, (key, q) in enumerate(hits[:C.PRINT_COLLISIONS], 1):
        print("[collision %d] bench=%s subject=%s id=%s gold=%s col=%s over_credited=%d texts=%r"
              % (n, key[0], key[1], key[2], q["gold_letter"], q["col"], over_by_q.get(key, 0), q["_texts"]))
    pre = sorted((((b, s, q["iid"]), q) for (b, s, _qh), q in qinfo.items()
                  if q["col"]["prefix_only"] and not (q["col"]["identical"] or q["col"]["quasi_only"])), key=by_key)
    for n, (key, q) in enumerate(pre[:C.PRINT_PREFIX], 1):
        print("[prefix %d] bench=%s subject=%s id=%s gold=%s col=%s texts=%r"
              % (n, key[0], key[1], key[2], q["gold_letter"], q["col"], q["_texts"]))

    coll_pub = [{"benchmark": key[0], "subject": key[1], "instance_id": key[2], "gold_letter": q["gold_letter"],
                 "collides": q["col"], "gold_normalises_to_empty": q["gold_norm_empty"],
                 "over_credited_predictions": over_by_q.get(key, 0)}
                for key, q in sorted((((b, s, q["iid"]), q) for (b, s, _qh), q in qinfo.items()
                                      if any(q["col"].values())), key=by_key)]
    out = {
        "audit": 92,
        "slug": "mcq-helm-option-collisions",
        "dataset": ("Per-question outputs of HELM Lite release %s (Stanford CRFM): every multiple_choice_joint run of "
                    "MMLU (5 subjects), MedQA and OpenBookQA, first trial. Only benchmarks, subjects, instance ids, "
                    "option letters, classes, counts and public model names are published." % C.HELM_RELEASE),
        "fixture": fx,
        "p1_parts": p1_parts,
        "n_models_included": {b: len(inc[b]) for b in C.BENCHES},
        "scorer_consistency": [all_cons, all_checked],
        "mapped_output_agreement": [map_agree, map_checked],
        "census": census,
        "totals": totals,
        "unmapped_kinds": unmapped_kinds,
        "ranks": ranks,
        "predictions": verdicts,
        "prediction_numbers": numbers,
        "per_model": per_model,
        "runs": runs_out,
        "note": ("H = HELM's score (answer letter -> option text -> main metric: exact_match for MMLU and OpenBookQA, "
                 "quasi_exact_match for MedQA), gated against HELM's recorded score; I = 1 when the letter names the "
                 "gold option itself. Over: H 1, I 0; under: H 0, I 1. A question collides when a wrong option's "
                 "text is string-identical to the gold's (identical), equal after HELM's normalize_text (quasi_only) "
                 "or starts with it after normalisation (prefix_only). P2 >= 1 MedQA quasi_only question; P3 MedQA "
                 "over-credits <= 0.2% of predictions; P4 no model's MedQA rank moves 3+ places; P5 >= 5 prefix_only "
                 "questions and >= 2 x quasi_only (all benchmarks); P6 >= 1 identical question; P7 >= 3 models have "
                 ">= 1% of their MedQA outputs unmapped."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "flips.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 92, "note": ("Every prediction whose HELM score (H) differs from option identity (I), and "
                   "every evaluated question whose gold option collides with a wrong option, by benchmark, subject, "
                   "HELM instance id and option letter; no question, option or model text."),
                   "flips": sorted(flips, key=lambda f: (f["benchmark"], f["model"], f["subject"],
                                                         str(f["instance_id"]))),
                   "collision_questions": coll_pub}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and flips.json (%d flips, %d collision questions)" % (len(flips), len(coll_pub)))


if __name__ == "__main__":
    main()
