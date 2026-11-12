"""Audit 109: does HELM Finance's BANKING77 scorer miss correct answers given as the label's list number?

Reads every banking77 run of HELM Finance release v1.0.0: the numbered label list in run_spec.json's instructions, the
gold label of each test instance (instances.json), each stored answer and its stored quasi_exact_match
(display_predictions.json) and the run means (stats.json). Gate: every stored per-record score is reproduced with
HELM's own normalize_text and every run mean matches. Then every answer HELM scored 0 is put in a class (a bare list
number for the gold label, a number plus the gold label, the gold label up to spacing, ...), the column is re-scored
with the three misread classes counted as correct, and ranks and the eight pre-registered verdicts follow. Only run
names, instance ids, classes, counts and public model names go to results.json; answers go to the job log only, for the
hand-read. Usage: python job.py --out-dir /out (network required). Standard library only. Apache-2.0.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import grade109 as g

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/finance/benchmark_output"
RELEASE = "v1.0.0"
PREFIX = "banking77:"
GROUP = "banking77"
UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
WORKERS = 2
TOL_RUN = 1e-9
TOL_CELL = 1e-6
PLACES = 3
PRINT_N = 8


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
        spec = _json(run_url(run, "run_spec.json"))
        inst = _json(run_url(run, "instances.json"))
        preds = _json(run_url(run, "display_predictions.json"))
        stats = _json(run_url(run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    rec["labels"] = g.parse_labels(((spec or {}).get("adapter_spec") or {}).get("instructions"))
    rec["gold"] = {i.get("id"): g.gold_of(i) for i in inst if isinstance(i, dict) and i.get("split") == "test"}
    rec["summary"] = g.summarize_run(preds, rec["gold"], rec["labels"] or {})
    rec["stat"] = g.stat_entry(stats, g.MAIN)
    ni = g.stat_entry(stats, "num_instances")
    rec["num_instances_sum"] = None if ni is None else ni.get("sum")
    del spec, inst, preds, stats
    return run, rec


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
    gold = ref["gold"] if ref else {}
    test_ids = sorted(gold)
    ref_labels = ref["labels"] if ref else None
    golds = sorted({v for v in gold.values() if v is not None})
    cover = g.labels_cover_gold(ref_labels, golds) if ref_labels else False
    unlisted = sorted(x for x in golds if ref_labels and not g.labels_cover_gold(ref_labels, [x]))
    print("[test] ids=%d distinct_gold=%d gold_missing=%d labels_listed=%s labels_cover_gold=%s unlisted=%d" % (
        len(test_ids), len(golds), sum(1 for v in gold.values() if v is None),
        None if ref_labels is None else len(ref_labels), cover, len(unlisted)))

    runs_out, inc, lists_ok = {}, {}, True
    for run in chosen:
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "error": r["error"]}
            continue
        s = r["summary"]
        reasons = []
        if r["labels"] is None or len(r["labels"]) != g.N_LABELS or r["labels"] != ref_labels:
            reasons.append("label_list")
            lists_ok = False
        if sorted(r["gold"]) != test_ids or r["gold"] != gold:
            reasons.append("test_ids")
        if s["stored_missing"] or s["recompute_mismatch"]:
            reasons.append("stored")
        nis = r["num_instances_sum"]
        if nis is None or s["counts"]["kept"] != int(round(nis)):
            reasons.append("instances")
        st, m = r["stat"], g.run_mean(s["trials"], "published")
        if st is None or st.get("mean") is None or m is None or abs(float(m) - st["mean"]) > TOL_RUN:
            reasons.append("mean")
        cc = g.class_counts(s["classes"])
        runs_out[run] = {"status": "included" if not reasons else "excluded", "reasons": reasons,
                         "model": r["model"], "counts": s["counts"], "stored_missing": s["stored_missing"],
                         "recompute_mismatch": s["recompute_mismatch"], "classes": cc}
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
    pooled_mis = sum(pooled[c] for c in g.MISREAD)
    print("[pooled] n=%d misread=%d classes=%s" % (pooled_n, pooled_mis, pooled))

    pub, len_, gain, mis2 = {}, {}, {}, 0
    for m in order:
        s = inc[m]["summary"]
        pub[m] = g.run_mean(s["trials"], "published")
        len_[m] = g.run_mean(s["trials"], "lenient")
        gain[m] = len_[m] - pub[m]
        n = sum(inc[m]["cc"].values())
        mis = sum(inc[m]["cc"][c] for c in g.MISREAD)
        if n and mis * 50 >= n:
            mis2 += 1
    matched = g.match_cells({m: float(v) for m, v in pub.items()}, published, TOL_CELL)
    rp, rl = g.ranks_high(pub), g.ranks_high(len_)
    tau = g.kendall_tau_b([pub[m] for m in order], [len_[m] for m in order]) if order else None
    movers = sorted(m for m in order if abs(rp[m] - rl[m]) >= PLACES)
    leaders = [m for m in order if rp[m] == 1]
    leader_ok = bool(leaders) and all(rl[m] == 1 for m in leaders)
    max_gain = max(gain.values()) if gain else None
    table = []
    for m in sorted(order, key=lambda k: (rp[k], k)):
        cc = inc[m]["cc"]
        table.append({"run": m, "model": inc[m]["model"], "published": float(pub[m]), "lenient": float(len_[m]),
                      "gain": float(gain[m]), "misread": sum(cc[c] for c in g.MISREAD), "classes": cc,
                      "rank_published": rp[m], "rank_lenient": rl[m]})
    print("[cells] matched %d of %d (published %d)" % (matched, len(order), len(published)))
    print("[ranks] tau_b published vs lenient=%s movers(>=%d)=%d leaders=%s leader_ok=%s runs_misread_2pct=%d "
          "max_gain=%s" % (tau, PLACES, len(movers), leaders, leader_ok, mis2,
                           None if max_gain is None else float(max_gain)))
    for row in table:
        print("[cell] %s" % row)

    stats = {"test_ids": len(test_ids), "runs_listed": len(chosen), "runs_included": len(inc), "lists_ok": lists_ok,
             "cells_matched": matched, "labels_cover_gold": cover, "runs_misread_2pct": mis2,
             "pooled_n": pooled_n, "pooled_misread": pooled_mis, "max_gain": max_gain, "tau": tau,
             "movers": len(movers), "leader_ok": leader_ok}
    verdicts = g.verdicts(stats)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, g.verdict_word(v)))

    # Hand-read material (job log only): up to PRINT_N answers per zero-scored class, spread over runs.
    for cls in ("number_gold", "number_other", "numbered_gold", "spacing_gold", "contains_gold", "empty", "other"):
        shown = 0
        for m in sorted(order, key=lambda x: (g.stable_hash(x + cls), x)):
            if shown >= PRINT_N:
                break
            ids = [i for i, c in inc[m]["summary"]["classes"].items() if c == cls]
            if not ids:
                continue
            i = min(ids, key=lambda x: (g.stable_hash(m + x), x))
            shown += 1
            print("[read %s %d] run=%s id=%s gold=%r pred=%r" % (
                cls, shown, m, i, gold.get(i), inc[m]["summary"]["texts"].get(i)))

    def f(x):
        return None if x is None else float(x)

    out = {
        "audit": 109,
        "slug": "helm-banking77-numbered-labels",
        "dataset": ("Per-instance outputs of HELM Finance release %s (Stanford CRFM): every banking77 run listed in "
                    "runs_to_run_suites.json, test split (BANKING77, PolyAI, CC BY 4.0). Only run names, instance ids, "
                    "classes, counts and public model names are published." % RELEASE),
        "test_ids": len(test_ids),
        "distinct_gold_labels": len(golds),
        "labels_listed": None if ref_labels is None else len(ref_labels),
        "labels_cover_gold": cover,
        "unlisted_gold_labels": unlisted,
        "group_error": group_err,
        "runs_listed": len(chosen),
        "runs_included": len(inc),
        "label_lists_identical": lists_ok,
        "cells_matched": [matched, len(order)],
        "published_cells": len(published),
        "pooled_classes": pooled,
        "pooled_n": pooled_n,
        "pooled_misread": pooled_mis,
        "runs_misread_2pct": mis2,
        "max_gain": f(max_gain),
        "tau_b_published_vs_lenient": tau,
        "movers_3plus": movers,
        "leaders": leaders,
        "verdicts": {k: g.verdict_word(v) for k, v in verdicts.items()},
        "table": table,
        "ids_by_class": {m: {c: sorted(i for i, x in inc[m]["summary"]["classes"].items() if x == c)
                             for c in g.MISREAD} for m in order},
        "runs": runs_out,
        "note": ("HELM's banking77 prompt lists the 77 labels as a numbered list; its main metric quasi_exact_match "
                 "compares the answer with the label text after normalize_text, which deletes '_' and so joins a label "
                 "into one word. Misread classes (scored 0 by HELM, counted correct in 'lenient'): number_gold (a bare "
                 "list number whose label is gold), numbered_gold (a number and a label text, both gold), spacing_gold "
                 "(the gold label up to spacing and punctuation). contains_gold is reported but never credited."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
