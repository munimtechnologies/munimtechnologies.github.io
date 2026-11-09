"""Which tie rule do HELM Classic's published log-probability multiple-choice scores use, and how often do ties
change a grade? (audit 94; HELM issue #4363)

Reads HELM Classic release v0.4.0's run index, keeps every run whose name says method=multiple_choice_separate_original
or _calibrated, and for each downloads run_spec.json (method check), instances.json (which options are correct, from
the unperturbed copy of each instance), display_predictions.json (HELM's per-record exact_match and predicted_index)
and stats.json (HELM's published exact_match and num_instances). Each record is classed by grade94.classify: `frac`
(a fractional exact_match: a tie scored by the current rule in #4363), `old_tie` (exact_match 1 although HELM's
predicted option is wrong: a tie credited in full by the v0.2.2 rule), `inconsistent`, `plain`. It re-scores every
record with F (first-argmax binary, the fix proposed in #4363 / PR #4364), recomputes each run's headline accuracy
and the rank of each model among the runs that differ only by model, and reports the pre-registered verdicts.

Gates before any verdict: the hand-traced fixtures match; at least 200 runs listed; at least 95% of them included
(method confirmed, our mean of unperturbed exact_match equals HELM's stats.json mean within 1e-6, as many first-trial
unperturbed records as HELM's num_instances); inconsistent records at most 0.1% of records. Only run names, instance
ids, option indices, classes, counts and public model names are written to results.json and ties.json; option text is
printed to the job log only, for the hand-read. Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import cases94 as C
import grade94 as g

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
    m, split = g.build_inst_map(C.FIX_INSTANCES)
    s = g.summarize_run(C.FIX_PREDS, m)
    return {
        "names": all(g.model_of(r) == mo and g.method_of(r) == me and g.group_of(r) == gr and g.scenario_of(r) == sc
                     for r, mo, me, gr, sc in C.FIX_NAMES),
        "dup": all(g.has_dup_correct(t, c) == w for (t, c), w in C.FIX_DUP_CASES),
        "inst_map": split == "valid" and sorted(m) == ["id1", "id2", "id3", "id4"] and m["id1"]["correct"] == [1],
        "run_summary": all(s[k] == v for k, v in C.FIX_RUN_TARGET.items()),
        "stats": all(g.stat_mean(C.FIX_STATS, n, sp) == w for (n, sp), w in C.FIX_STAT_CASES),
        "reproduce": all(g.reproduce(s, p, n, C.TOL) == w for (p, n), w in C.FIX_REPRO_CASES),
        "ranks": g.ranks_high(C.FIX_RANKS_IN) == C.FIX_RANKS_OUT and g.top_share(C.FIX_TOP_IN, 3) == C.FIX_TOP_OUT,
        "verdicts": all(g.predictions94(*a, C.THRESHOLDS) == w for a, w in C.FIX_V_CASES),
    }


def load_run(item):
    run, suite = item
    rec = {"run": run, "suite": suite, "model": g.model_of(run)}
    try:
        spec = _json(run_url(suite, run, "run_spec.json"))
        rec["method"] = (spec.get("adapter_spec") or {}).get("method")
        del spec
        inst_map, split = g.build_inst_map(_json(run_url(suite, run, "instances.json")))
        rec["split"] = split
        s = g.summarize_run(_json(run_url(suite, run, "display_predictions.json")), inst_map)
        stats = _json(run_url(suite, run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    rec["summary"] = s
    rec["published"] = g.stat_mean(stats, "exact_match", split)
    rec["num_instances"] = g.stat_mean(stats, "num_instances", split)
    lines = []
    for iid, pname, cls, em, dup, pi, correct in s["ties"][:C.PER_RUN_PRINT]:
        texts = inst_map.get(iid, {}).get("texts", [])
        lines.append("run=%s id=%s pert=%s class=%s em=%s pi=%s correct=%s dup=%s refs=%r" % (
            run, iid, pname, cls, em, pi, correct, dup, [t[:60] for t in texts]))
    rec["print"] = lines
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

    index = _json(C.RUNS_INDEX)
    if not isinstance(index, dict):
        raise SystemExit("run index is not a mapping of run name -> suite")
    listed = sorted((r, s) for r, s in index.items() if g.method_of(r) in g.SEPARATE)
    by_method = {}
    for r, _ in listed:
        by_method[g.method_of(r)] = by_method.get(g.method_of(r), 0) + 1
    print("[index] runs=%d separate=%d by_method=%s" % (len(index), len(listed), by_method))
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(load_run, listed))

    # ----- Gates -----
    runs_out, inc = {}, {}
    for run, _ in listed:
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "error": r["error"]}
            continue
        s = r["summary"]
        basis, ok = g.reproduce(s, r["published"], r["num_instances"], C.TOL)
        method_ok = r["method"] == g.method_of(run)
        row = {"status": "included" if (ok and method_ok) else "excluded", "suite": r["suite"], "model": r["model"],
               "method": r["method"], "split": r["split"], "counts": s["counts"], "basis": basis,
               "published": r["published"], "num_instances": r["num_instances"],
               "ours_all": s["unpert_all"]["pub"] / s["unpert_all"]["n"] if s["unpert_all"]["n"] else None,
               "ours_t0": s["unpert_t0"]["pub"] / s["unpert_t0"]["n"] if s["unpert_t0"]["n"] else None}
        if not method_ok:
            row["reason"] = "method_mismatch"
        elif not ok:
            row["reason"] = "not_reproduced"
        runs_out[run] = row
        if ok and method_ok:
            key = "unpert_all" if basis == "all" else "unpert_t0"
            u = s[key]
            row["headline_published"] = u["pub"] / u["n"]
            row["headline_F"] = u["f"] / u["n"]
            row["move"] = row["headline_F"] - row["headline_published"]
            row["ties_unperturbed"] = sum(1 for t in s["ties"] if t[1] is None)
            inc[run] = r
    n_inc = len(inc)
    inc_share = Fraction(n_inc, len(listed)) if listed else Fraction(0)

    totals = {"records": 0, "plain": 0, "old_tie": 0, "frac": 0, "inconsistent": 0, "unmatched": 0, "missing": 0}
    frac_values, by_model, by_scen, dup, ties_pub = {}, {}, {}, 0, []
    for run in sorted(inc):
        s = inc[run]["summary"]
        for k in totals:
            totals[k] += s["counts"][k]
        for k, v in s["frac_values"].items():
            frac_values[k] = frac_values.get(k, 0) + v
        nt = s["counts"]["old_tie"] + s["counts"]["frac"]
        by_model[inc[run]["model"]] = by_model.get(inc[run]["model"], 0) + nt
        d = by_scen.setdefault(g.scenario_of(run), {"runs": 0, "records": 0, "old_tie": 0, "frac": 0,
                                                    "inconsistent": 0})
        d["runs"] += 1
        for k in ("records", "old_tie", "frac", "inconsistent"):
            d[k] += s["counts"][k]
        for iid, pname, cls, em, dp, pi, correct in s["ties"]:
            dup += 1 if dp else 0
            ties_pub.append({"run": run, "instance_id": iid, "perturbation": pname, "class": cls,
                             "exact_match": em, "predicted_index": pi, "correct": correct, "duplicate_option": dp})
    ties = totals["old_tie"] + totals["frac"]
    p1_parts = {"fixtures": all(fx.values()), "runs_listed": len(listed) >= C.MIN_RUNS,
                "included": inc_share >= C.MIN_INCLUDED,
                "inconsistent_rare": totals["records"] > 0
                and Fraction(totals["inconsistent"], totals["records"]) <= C.MAX_INCONSISTENT}
    print("[runs] listed=%d included=%d (%.4f)" % (len(listed), n_inc, float(inc_share)))
    print("[P1] %s" % p1_parts)
    if inc_share < C.ABORT_INCLUDED:
        with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
            json.dump({"audit": 94, "aborted": True, "fixture": fx, "p1_parts": p1_parts, "runs": runs_out}, fh,
                      indent=1, ensure_ascii=True)
        raise SystemExit("inclusion gate failed -- aborting (diagnostics in results.json)")
    print("[totals] %s ties=%d duplicate_option=%d" % (totals, ties, dup))
    print("[frac values] %s" % dict(sorted(frac_values.items())))
    print("[by scenario] %s" % dict(sorted(by_scen.items())))
    print("[by model, ties] %s" % {k: v for k, v in sorted(by_model.items(), key=lambda kv: (-kv[1], kv[0])) if v})

    # ----- Headlines and ranks -----
    groups = {}
    for run in inc:
        groups.setdefault(g.group_of(run), []).append(run)
    ranks, changed_total = {}, 0
    for grp in sorted(groups):
        rs = groups[grp]
        if len(rs) < 2:
            continue
        pub = {inc[r]["model"]: runs_out[r]["headline_published"] for r in rs}
        cor = {inc[r]["model"]: runs_out[r]["headline_F"] for r in rs}
        rp, rc = g.ranks_high(pub), g.ranks_high(cor)
        changed = sorted(m for m in pub if rp[m] != rc[m])
        changed_total += len(changed)
        ranks[grp] = {"runs": len(rs), "models_rank_changed": changed,
                      "max_abs_move": max(abs(cor[m] - pub[m]) for m in pub)}
    moves = [(abs(runs_out[r]["move"]), r) for r in inc]
    max_move = max((m for m, _ in moves), default=None)
    biggest = [{"run": r, "published": runs_out[r]["headline_published"], "F": runs_out[r]["headline_F"],
                "ties_unperturbed": runs_out[r]["ties_unperturbed"]}
               for _, r in sorted(moves, key=lambda x: (-x[0], x[1]))[:15]]
    print("[ranks] groups=%d models_rank_changed=%d" % (len(ranks), changed_total))
    print("[biggest moves] %s" % biggest)

    topk = g.top_share(by_model, C.THRESHOLDS["P5_top_models"])
    verdicts = g.predictions94(totals["old_tie"], totals["frac"], totals["records"], topk, max_move, dup, C.THRESHOLDS)
    verdicts["P1_structural"] = all(p1_parts.values())
    for name in sorted(verdicts):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    numbers = {"P2_ties": ties, "P3_old_tie_and_frac": [totals["old_tie"], totals["frac"]],
               "P4_ties_of_records": [ties, totals["records"], share(ties, totals["records"])],
               "P5_top3_models_of_ties": [topk, ties, share(topk, ties)], "P6_max_abs_move": max_move,
               "P7_duplicate_of_ties": [dup, ties, share(dup, ties)]}
    print("[numbers] %s" % numbers)

    # ----- Log lines for the hand-read (stdout only) -----
    k = 0
    for run in sorted(inc):
        for line in inc[run]["print"]:
            k += 1
            if k > C.PRINT_TIES:
                break
            print("[tie %d] %s" % (k, line))

    out = {
        "audit": 94,
        "slug": "helm-classic-mc-ties",
        "dataset": ("Per-record outputs of HELM Classic release %s (Stanford CRFM): every run whose method is "
                    "multiple_choice_separate_original or multiple_choice_separate_calibrated. Only run names, instance "
                    "ids, option indices, classes, counts and public model names are published." % C.RELEASE),
        "fixture": fx,
        "p1_parts": p1_parts,
        "runs_listed": len(listed),
        "runs_by_method": by_method,
        "runs_included": n_inc,
        "totals": totals,
        "ties": ties,
        "duplicate_option": dup,
        "frac_values": frac_values,
        "by_scenario": by_scen,
        "by_model_ties": by_model,
        "ranks": ranks,
        "models_rank_changed": changed_total,
        "biggest_moves": biggest,
        "predictions": verdicts,
        "prediction_numbers": numbers,
        "runs": runs_out,
        "note": ("exact_match and predicted_index are HELM's recorded per-record values. frac: exact_match not 0 or "
                 "1 (current HELM tie rule); old_tie: exact_match 1 but predicted_index (first top-scoring option) "
                 "not correct (HELM v0.2.2 tie rule); F = 1 iff predicted_index is correct (first-argmax binary, the "
                 "fix proposed in HELM issue #4363 / PR #4364). Headline = mean over unperturbed records (all trials, "
                 "or the first trial when only that reproduces HELM). P2 >= 1 tie; P3 old_tie >= 1 and frac == 0; P4 "
                 "ties <= 1% of records; P5 the 3 models with most ties hold >= 50%; P6 some run's headline moves >= "
                 "0.01; P7 >= 50% of ties are in instances where a wrong option repeats a correct option's text."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "ties.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 94, "note": "Every tie record (old_tie or frac) in the included runs, by run name, "
                   "instance id and perturbation, with HELM's recorded exact_match and predicted_index and the correct "
                   "option indices; no text.", "ties": ties_pub}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and ties.json (%d ties)" % len(ties_pub))


if __name__ == "__main__":
    main()
