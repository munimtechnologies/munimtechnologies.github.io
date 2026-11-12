"""Audit 112: how much do MedHELM's MEDEC gold-id parsing and strict answer reading change the published numbers?

Reads every medec run of MedHELM release v4.0.0: the reference of each test instance (instances.json), each stored
answer with its stored medec_error_flag_accuracy and medec_error_sentence_accuracy (display_predictions.json) and the
run means (stats.json). Gate: every stored per-record value is reproduced by our transcription of HELM's MedecMetric
and both run means match. Then each run is re-scored with the gold sentence id read as the scenario writes it, with
HELM-invalid answers counted as no answer, and with a lenient reading of 'CORRECT.'-style and '**7**'-style answers;
ranks and the eight pre-registered verdicts follow. Only run names, instance ids, classes, counts and public model
names go to results.json; answers and references go to the job log only, for the hand-read.
Usage: python job.py --out-dir /out (network required). Standard library only. Apache-2.0.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import grade112 as g

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/medhelm/benchmark_output"
RELEASE = "v4.0.0"
PREFIX = "medec:"
GROUP = "medec"
UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
WORKERS = 2
TOL_RUN = 1e-9
TOL_CELL = 1e-6
PLACES = 3
PRINT_N = 8
NEAR = Fraction(3, 100)


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
    return "%s/runs/%s/%s/%s" % (HELM_BASE, RELEASE, urllib.parse.quote(run, safe=":,=@-_."), fname)


def load_run(run):
    rec = {"run": run, "model": g.model_of(run)}
    try:
        inst = _json(run_url(run, "instances.json"))
        preds = _json(run_url(run, "display_predictions.json"))
        stats = _json(run_url(run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    rec["refs"] = {i.get("id"): g.gold_of(i) for i in inst if isinstance(i, dict) and i.get("split") == "test"}
    rec["summary"] = g.summarize_run(preds, rec["refs"])
    rec["stat_flag"] = g.stat_entry(stats, g.FLAG)
    rec["stat_sent"] = g.stat_entry(stats, g.SENT)
    ni = g.stat_entry(stats, "num_instances")
    rec["num_instances_sum"] = None if ni is None else ni.get("sum")
    del inst, preds, stats
    return run, rec


def _mean_ok(stat, ours):
    return (stat is not None and stat.get("mean") is not None and ours is not None
            and abs(float(ours) - stat["mean"]) <= TOL_RUN)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    run_suites = _json("%s/releases/%s/runs_to_run_suites.json" % (HELM_BASE, RELEASE))
    chosen = sorted(g.select_runs(run_suites, PREFIX))
    print("[release] %s runs listed=%d" % (RELEASE, len(chosen)))
    try:
        published = g.group_values(_json("%s/releases/%s/groups/%s.json" % (HELM_BASE, RELEASE, GROUP))) or []
        group_err = None
    except Exception as e:  # noqa: BLE001
        published, group_err = [], str(e)[:200]
    print("[group] %s cells published=%d error=%s" % (g.CELL_HEADER, len(published), group_err))

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        loaded = dict(ex.map(load_run, chosen))

    ref = next((loaded[r] for r in chosen if "error" not in loaded[r]), None)
    refs = ref["refs"] if ref else {}
    test_ids = sorted(refs)
    gold_fixed = {i: g.gold_fixed_id(t) for i, t in refs.items()}
    n_error = sum(1 for v in gold_fixed.values() if v[0] == 1)
    n_error_noid = sum(1 for v in gold_fixed.values() if v[0] == 1 and v[1] < 0)
    n_helm_id = sum(1 for t in refs.values() if g.gold_flag_id(t)[0] == 1 and g.gold_flag_id(t)[1] >= 0)
    print("[test] ids=%d error_notes=%d error_notes_without_leading_id=%d error_notes_HELM_reads_an_id=%d "
          "refs_missing=%d" % (len(test_ids), n_error, n_error_noid, n_helm_id,
                               sum(1 for v in refs.values() if v is None)))
    base_err = Fraction(n_error, len(test_ids)) if test_ids else None

    runs_out, inc = {}, {}
    for run in chosen:
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "error": r["error"]}
            continue
        s = r["summary"]
        reasons = []
        if sorted(r["refs"]) != test_ids or r["refs"] != refs:
            reasons.append("test_ids")
        if s["stored_missing"] or s["flag_mismatch"] or s["sent_mismatch"]:
            reasons.append("stored")
        nis = r["num_instances_sum"]
        if nis is None or s["counts"]["kept"] != int(round(nis)):
            reasons.append("instances")
        if not _mean_ok(r["stat_flag"], g.run_mean(s["trials"], "pub_flag")):
            reasons.append("mean_flag")
        if not _mean_ok(r["stat_sent"], g.run_mean(s["trials"], "pub_sent")):
            reasons.append("mean_sent")
        cc = g.class_counts(s["classes"])
        runs_out[run] = {"status": "included" if not reasons else "excluded", "reasons": reasons,
                         "model": r["model"], "counts": s["counts"], "stored_missing": s["stored_missing"],
                         "flag_mismatch": s["flag_mismatch"], "sent_mismatch": s["sent_mismatch"], "classes": cc}
        if not reasons:
            inc[run] = r
            r["cc"] = cc
    print("[runs] listed=%d included=%d" % (len(chosen), len(inc)))
    for run in chosen:
        if runs_out[run]["status"] != "included":
            print("[excluded] %s %s" % (run, runs_out[run].get("reasons") or runs_out[run].get("error")))

    order = sorted(inc)
    pooled = {c: sum(inc[m]["cc"].get(c, 0) for m in order) for c in g.CLASSES}
    pooled_n = sum(pooled.values())
    pooled_inv = sum(pooled[c] for c in g.INVALID)
    print("[pooled] n=%d invalid=%d classes=%s" % (pooled_n, pooled_inv, pooled))

    cell = {k: {} for k in g.VARIANTS}
    for m in order:
        for k in g.VARIANTS:
            cell[k][m] = g.run_mean(inc[m]["summary"]["trials"], k)
    check_bug = all(inc[m]["summary"]["err_sent_credit"] == 0
                    and Fraction(inc[m]["summary"]["tn"], inc[m]["summary"]["counts"]["kept"]) == cell["pub_sent"][m]
                    for m in order) if order else None
    sent_rise10 = sum(1 for m in order if cell["fixed_sent"][m] - cell["pub_sent"][m] >= Fraction(1, 10))
    max_fixed_sent = max(cell["fixed_sent"].values()) if order else None
    runs_inv20 = sum(1 for m in order if sum(inc[m]["cc"][c] for c in g.INVALID) * 5 >= sum(inc[m]["cc"].values()))
    drops = {m: cell["pub_flag"][m] - cell["noinv_flag"][m] for m in order}
    max_drop = max(drops.values()) if drops else None
    matched = g.match_cells({m: float(v) for m, v in cell["pub_flag"].items()}, published, TOL_CELL)
    rp, rl = g.ranks_high(cell["pub_flag"]), g.ranks_high(cell["len_flag"])
    rs = g.ranks_high(cell["fixed_sent"])
    tau = g.kendall_tau_b([cell["pub_flag"][m] for m in order], [cell["len_flag"][m] for m in order]) if order else None
    tau_s = (g.kendall_tau_b([cell["pub_flag"][m] for m in order], [cell["fixed_sent"][m] for m in order])
             if order else None)
    movers = sorted(m for m in order if abs(rp[m] - rl[m]) >= PLACES)
    leaders = [m for m in order if rp[m] == 1]
    leader_ok = bool(leaders) and all(rl[m] == 1 for m in leaders)
    near_base = sorted(m for m in order if base_err is not None and abs(cell["pub_flag"][m] - base_err) <= NEAR)
    table = []
    for m in sorted(order, key=lambda k: (rp[k], k)):
        s = inc[m]["summary"]
        table.append(dict({"run": m, "model": inc[m]["model"]},
                          **{k: float(cell[k][m]) for k in g.VARIANTS},
                          **{"rank_published_flag": rp[m], "rank_lenient_flag": rl[m],
                             "rank_fixed_sentence": rs[m], "classes": inc[m]["cc"],
                             "invalid": sum(inc[m]["cc"][c] for c in g.INVALID),
                             "invalid_flag_credit": s["invalid_flag_credit"], "tn": s["tn"],
                             "error_notes": s["error_notes"], "err_sent_credit": s["err_sent_credit"]}))
    print("[cells] matched %d of %d (published %d)" % (matched, len(order), len(published)))
    print("[check] sentence bug (no error note credited; stored sentence = tn/n in every run) = %s" % check_bug)
    print("[baseline] always-error=%s near(<=0.03)=%d" % (None if base_err is None else float(base_err),
                                                           len(near_base)))
    print("[ranks] tau_b flag published vs lenient=%s; published flag vs fixed sentence=%s; movers(>=%d)=%d "
          "leaders=%s leader_ok=%s sent_rise10=%d max_fixed_sent=%s runs_invalid20=%d max_noinv_drop=%s" % (
              tau, tau_s, PLACES, len(movers), leaders, leader_ok, sent_rise10,
              None if max_fixed_sent is None else float(max_fixed_sent), runs_inv20,
              None if max_drop is None else float(max_drop)))
    for row in table:
        print("[cell] %s" % row)

    stats = {"test_ids": len(test_ids), "runs_listed": len(chosen), "runs_included": len(inc),
             "cells_matched": matched, "sent_rise10": sent_rise10, "max_fixed_sent": max_fixed_sent,
             "pooled_n": pooled_n, "pooled_invalid": pooled_inv, "runs_invalid20": runs_inv20,
             "max_noinv_drop": max_drop, "movers_len": len(movers), "leader_ok_len": leader_ok}
    verdicts = g.verdicts(stats)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, g.verdict_word(v)))

    # Hand-read material (job log only): up to PRINT_N answers per class HELM marks invalid, one per run.
    for cls in g.INVALID:
        shown = 0
        for m in sorted(order, key=lambda x: (g.stable_hash(x + cls), x)):
            if shown >= PRINT_N:
                break
            s = inc[m]["summary"]
            ids = [i for i, c in s["classes"].items() if c == cls]
            if not ids:
                continue
            i = min(ids, key=lambda x: (g.stable_hash(m + x), x))
            shown += 1
            print("[read %s %d] run=%s id=%s gold=%s pred=%r" % (cls, shown, m, i, s["golds"].get(i),
                                                                 s["texts"].get(i)))
    # Gold-id parse check (job log only): four references with an error, start of the text and our id.
    for i in sorted((i for i, v in gold_fixed.items() if v[0] == 1), key=lambda x: (g.stable_hash(x), x))[:4]:
        print("[read gold] id=%s fixed=%s helm=%s ref_start=%r" % (i, gold_fixed[i], g.gold_flag_id(refs[i]),
                                                                    (refs[i] or "")[:40]))

    def f(x):
        return None if x is None else float(x)

    out = {
        "audit": 112,
        "slug": "helm-medec-scorer",
        "dataset": ("Per-instance outputs of MedHELM release %s (Stanford CRFM): every medec run listed in "
                    "runs_to_run_suites.json, test split (MEDEC-MS, Ben Abacha et al.). Only run names, instance ids, "
                    "classes, counts and public model names are published." % RELEASE),
        "test_ids": len(test_ids),
        "error_notes": n_error,
        "error_notes_without_leading_id": n_error_noid,
        "error_notes_helm_reads_an_id": n_helm_id,
        "always_error_baseline": f(base_err),
        "runs_near_baseline": near_base,
        "group_error": group_err,
        "runs_listed": len(chosen),
        "runs_included": len(inc),
        "cells_matched": [matched, len(order)],
        "published_cells": len(published),
        "check_sentence_bug": check_bug,
        "pooled_classes": pooled,
        "pooled_n": pooled_n,
        "pooled_invalid": pooled_inv,
        "sent_rise10": sent_rise10,
        "max_fixed_sent": f(max_fixed_sent),
        "runs_invalid20": runs_inv20,
        "max_noinv_drop": f(max_drop),
        "tau_b_flag_published_vs_lenient": tau,
        "tau_b_published_flag_vs_fixed_sentence": tau_s,
        "movers_3plus": movers,
        "leaders": leaders,
        "verdicts": {k: g.verdict_word(v) for k, v in verdicts.items()},
        "table": table,
        "ids_by_class": {m: {c: sorted(i for i, x in inc[m]["summary"]["classes"].items() if x == c)
                             for c in g.INVALID} for m in order},
        "runs": runs_out,
        "note": ("pub_flag / pub_sent: HELM's stored per-record stats. fixed_sent: HELM's answer reading with the gold "
                 "sentence id read as the leading number of the reference. noinv_*: as fixed, but an answer HELM marks "
                 "invalid (neither exactly 'CORRECT' nor starting with a digit) counts as no answer. len_*: as fixed, "
                 "with correct_variant read as 'CORRECT', id_variant read as its id, empty/other as no answer."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
