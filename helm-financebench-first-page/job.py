"""Audit 108: does HELM Finance's FinanceBench prompt leave out evidence its questions need?

Downloads FinanceBench's open-source questions (patronus-ai/financebench at the commit HELM pins), classes every
question by whether the evidence it cites is in the one page HELM puts in the prompt (evidence[0]'s full page), checks
that each HELM instance's prompt is exactly that page plus the question, then reads every financebench run of HELM
Finance release v1.0.0: the GPT-4o judge's label per answer (gate: every stored per-record score and the run mean
reproduced), label rates by evidence class, the "Correct Answer" column on complete-evidence questions only, ranks and
the eight pre-registered verdicts. Only run names, instance ids, classes, question types, counts and public model names
go to results.json; questions, evidence, answers and judge explanations go to the job log only, for the hand-read.
Usage: python job.py --out-dir /out (network required). Standard library only. Apache-2.0.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import grade108 as g

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/finance/benchmark_output"
RELEASE = "v1.0.0"
PREFIX = "financebench:"
GROUP = "financebench"
FB_URL = ("https://raw.githubusercontent.com/patronus-ai/financebench/d7beebe5e739e0b806ab4443c1b3e23f51804acf/"
          "data/financebench_open_source.jsonl")
UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
WORKERS = 2
TOL_RUN = 1e-9
TOL_CELL = 1e-6
PLACES = 3
PRINT_N = 8
METRICS_TYPE = "metrics-generated"


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


def load_fb():
    recs, dup = {}, 0
    for line in _get(FB_URL).decode("utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rid = r.get("financebench_id")
        if rid in recs:
            dup += 1
            continue
        recs[rid] = r
    return recs, dup


def load_run(run):
    rec = {"run": run, "model": g.model_of(run)}
    try:
        inst = _json(run_url(run, "instances.json"))
        preds = _json(run_url(run, "display_predictions.json"))
        stats = _json(run_url(run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    rec["test"] = {i.get("id"): ((i.get("input") or {}).get("text"))
                   for i in inst if isinstance(i, dict) and i.get("split") == "test"}
    rec["train"] = sorted(i.get("id") for i in inst if isinstance(i, dict) and i.get("split") == "train")
    rec["summary"] = g.summarize_run(preds, set(rec["test"]))
    rec["texts"] = {}
    for r in preds:
        if isinstance(r, dict) and r.get("perturbation") is None and r.get("train_trial_index", 0) == 0:
            iid = r.get("instance_id")
            if iid in rec["test"] and iid not in rec["texts"]:
                ann = (r.get("annotations") or {}).get(g.ANN) or {}
                rec["texts"][iid] = ((r.get("predicted_text") or "")[:300],
                                     str(ann.get("explanation") or ann.get("reasoning") or "")[:300])
    rec["stats"] = {lab: g.stat_entry(stats, g.STAT_NAMES[lab]) for lab in g.LABELS}
    ni = g.stat_entry(stats, "num_instances")
    rec["num_instances_sum"] = None if ni is None else ni.get("sum")
    del inst, preds, stats
    return run, rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    fb, fb_dup = load_fb()
    cls_of, info_of, own_hits, own_total = {}, {}, 0, 0
    for rid, r in fb.items():
        c, info = g.evidence_class(r.get("evidence"))
        cls_of[rid], info_of[rid] = c, info
        for e in r.get("evidence") or []:
            if isinstance(e, dict):
                own_total += 1
                own_hits += 1 if g.snippet_in_own_page(e) else 0
    own_share = Fraction(own_hits, own_total) if own_total else None
    all_classes = {c: sum(1 for v in cls_of.values() if v == c) for c in g.CLASSES}
    print("[financebench] records=%d duplicates=%d classes=%s snippets_in_own_page=%d/%d" % (
        len(fb), fb_dup, all_classes, own_hits, own_total))

    run_suites = _json("%s/releases/%s/runs_to_run_suites.json" % (HELM_BASE, RELEASE))
    chosen = sorted(g.select_runs(run_suites, PREFIX))
    print("[release] %s runs listed=%d" % (RELEASE, len(chosen)))
    try:
        published = g.group_values(_json("%s/releases/%s/groups/%s.json" % (HELM_BASE, RELEASE, GROUP))) or []
        group_err = None
    except Exception as e:  # noqa: BLE001
        published, group_err = [], str(e)[:200]
    print("[group] Correct Answer cells published=%d error=%s" % (len(published), group_err))

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        loaded = dict(ex.map(load_run, chosen))

    # Test instances: taken from the first run that downloaded; every run is checked against the same set.
    ref = next((loaded[r] for r in chosen if "error" not in loaded[r]), None)
    test_ids = sorted(ref["test"]) if ref else []
    train_ids = ref["train"] if ref else []
    found = [i for i in test_ids if i in fb]
    test_cls = {i: cls_of[i] for i in found}
    test_classes = {c: sum(1 for v in test_cls.values() if v == c) for c in g.CLASSES}
    train_classes = {c: sum(1 for i in train_ids if cls_of.get(i) == c) for c in g.CLASSES}
    qtype = {i: str(fb[i].get("question_type")) for i in found}
    qtype_by_class = {}
    for i in found:
        d = qtype_by_class.setdefault(test_cls[i], {})
        d[qtype[i]] = d.get(qtype[i], 0) + 1
    print("[test] ids=%d found_in_financebench=%d classes=%s train_ids=%d train_classes=%s" % (
        len(test_ids), len(found), test_classes, len(train_ids), train_classes))
    print("[qtype] %s" % qtype_by_class)

    runs_out, inc, prompt_ok = {}, {}, {}
    for run in chosen:
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "error": r["error"]}
            continue
        ok = sum(1 for i, t in r["test"].items() if i in fb and g.prompt_matches(t, fb[i]))
        prompt_ok[run] = Fraction(ok, len(r["test"])) if r["test"] else Fraction(0)
        s = r["summary"]
        reasons = []
        if sorted(r["test"]) != test_ids:
            reasons.append("test_ids")
        if s["label_bad"] or s["stored_missing"] or s["stored_mismatch"]:
            reasons.append("labels")
        nis = r["num_instances_sum"]
        if nis is None or s["counts"]["kept"] != int(round(nis)):
            reasons.append("instances")
        for lab in g.LABELS:
            st, m = r["stats"][lab], g.run_mean(s["trials"], lab)
            if st is None or st.get("mean") is None or m is None or abs(float(m) - st["mean"]) > TOL_RUN:
                reasons.append("mean_" + lab)
        bc = g.by_class(s["labels"], test_cls)
        r["bc"] = bc
        r["bc_metrics"] = g.by_class(s["labels"], {i: c for i, c in test_cls.items() if qtype[i] == METRICS_TYPE})
        runs_out[run] = {"status": "included" if not reasons else "excluded", "reasons": reasons,
                         "model": r["model"], "counts": s["counts"], "prompt_ok": float(prompt_ok[run]),
                         "by_class": bc}
        if not reasons:
            inc[run] = r
    print("[runs] listed=%d included=%d" % (len(chosen), len(inc)))
    for run in chosen:
        if runs_out[run]["status"] != "included":
            print("[excluded] %s %s" % (run, runs_out[run].get("reasons") or runs_out[run].get("error")))
    prompt_ok_min = min(prompt_ok.values()) if prompt_ok else None
    print("[prompt] runs checked=%d min share of test prompts equal to evidence[0] page + question=%s" % (
        len(prompt_ok), None if prompt_ok_min is None else float(prompt_ok_min)))

    order = sorted(inc)
    bcs = [inc[m]["bc"] for m in order]
    pooled = {c: g.merge(bcs, (c,)) for c in g.CLASSES}
    pm, pc = g.merge(bcs, ("missing",)), g.merge(bcs, g.COMPLETE)
    mm = g.merge([inc[m]["bc_metrics"] for m in order], ("missing",))
    mc = g.merge([inc[m]["bc_metrics"] for m in order], g.COMPLETE)
    print("[pooled] %s" % pooled)
    print("[pooled2] missing=%s complete=%s metrics_missing=%s metrics_complete=%s" % (pm, pc, mm, mc))

    cells, comp, miss, lower = {}, {}, {}, 0
    for m in order:
        s = inc[m]["summary"]
        cells[m] = g.run_mean(s["trials"], "correct_answer")
        c = g.merge([inc[m]["bc"]], g.COMPLETE)
        x = g.merge([inc[m]["bc"]], ("missing",))
        comp[m], miss[m] = g.share(c, "correct_answer"), g.share(x, "correct_answer")
        if comp[m] is not None and miss[m] is not None and miss[m] < comp[m]:
            lower += 1
    matched = g.match_cells({m: float(v) for m, v in cells.items()}, published, TOL_CELL)
    comp_ok = all(comp[m] is not None for m in order)
    rp = g.ranks_high(cells)
    rc = g.ranks_high(comp) if comp_ok else {m: None for m in order}
    tau = g.kendall_tau_b([cells[m] for m in order], [comp[m] for m in order]) if comp_ok and order else None
    movers = sorted(m for m in order if rc[m] is not None and abs(rp[m] - rc[m]) >= PLACES)
    leaders = [m for m in order if rp[m] == 1]
    leader_ok = comp_ok and bool(leaders) and all(rc[m] == 1 for m in leaders)
    table = []
    for m in sorted(order, key=lambda k: (rp[k], k)):
        c = g.merge([inc[m]["bc"]], g.COMPLETE)
        x = g.merge([inc[m]["bc"]], ("missing",))
        table.append({"run": m, "model": inc[m]["model"], "published": float(cells[m]),
                      "complete_only": None if comp[m] is None else float(comp[m]),
                      "missing_only": None if miss[m] is None else float(miss[m]),
                      "failure_complete": None if g.share(c, "failure_to_answer") is None
                      else float(g.share(c, "failure_to_answer")),
                      "failure_missing": None if g.share(x, "failure_to_answer") is None
                      else float(g.share(x, "failure_to_answer")),
                      "rank_published": rp[m], "rank_complete_only": rc[m]})
    print("[cells] matched %d of %d (published %d)" % (matched, len(order), len(published)))
    print("[ranks] tau_b published vs complete-only=%s movers(>=%d)=%d leaders=%s leader_ok=%s runs_lower=%d" % (
        tau, PLACES, len(movers), leaders, leader_ok, lower))
    for row in table:
        print("[cell] %s" % row)

    stats = {"test_ids": len(test_ids), "test_ids_found": len(found), "prompt_ok_min": prompt_ok_min,
             "own_page_share": own_share, "runs_listed": len(chosen), "runs_included": len(inc),
             "cells_matched": matched, "missing": test_classes["missing"], "pooled_missing": pm,
             "pooled_complete": pc, "runs_lower": lower, "metrics_missing": mm, "metrics_complete": mc,
             "metrics_missing_q": sum(1 for i in found if qtype[i] == METRICS_TYPE and test_cls[i] == "missing"),
             "metrics_complete_q": sum(1 for i in found if qtype[i] == METRICS_TYPE and test_cls[i] in g.COMPLETE),
             "tau": tau, "movers": len(movers), "leader_ok": leader_ok}
    verdicts = g.verdicts(stats)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, g.verdict_word(v)))

    # Hand-read material (job log only): the missing questions and their uncited pages; judge reasons.
    miss_ids = sorted((i for i in found if test_cls[i] == "missing"), key=lambda i: (g.stable_hash(i), i))
    for n, i in enumerate(miss_ids[:PRINT_N]):
        r = fb[i]
        evs = r.get("evidence") or []
        k = info_of[i]["missing"][0]
        print("[read missing %d] id=%s type=%s pages=%s q=%r given_head=%r missing_snippet=%r answer=%r" % (
            n + 1, i, qtype[i], [(g.doc_of(e), e.get("evidence_page_num")) for e in evs],
            str(r.get("question"))[:200], str(evs[0].get("evidence_text"))[:120],
            str(evs[k].get("evidence_text"))[:200], str(r.get("answer"))[:150]))
    for lab_cls, want in (("missing", "failure_to_answer"), ("complete", "failure_to_answer"),
                          ("missing", "correct_answer")):
        shown = 0
        for m in sorted(order, key=lambda x: (g.stable_hash(x + want), x)):
            if shown >= PRINT_N:
                break
            labs = inc[m]["summary"]["labels"]
            ids = [i for i in found if labs.get(i) == want
                   and ((test_cls[i] == "missing") if lab_cls == "missing" else (test_cls[i] in g.COMPLETE))]
            if not ids:
                continue
            i = min(ids, key=lambda x: (g.stable_hash(m + x), x))
            p, e = inc[m]["texts"].get(i, ("", ""))
            shown += 1
            print("[read %s %s %d] run=%s id=%s pred=%r judge=%r" % (lab_cls, want, shown, m, i, p, e))

    def f(x):
        return None if x is None else float(x)

    out = {
        "audit": 108,
        "slug": "helm-financebench-first-page",
        "dataset": ("Per-instance outputs of HELM Finance release %s (Stanford CRFM): every financebench run listed in "
                    "runs_to_run_suites.json, test split; FinanceBench's open-source questions (Patronus AI) at the "
                    "commit HELM pins. Only run names, instance ids, classes, question types, counts and public model "
                    "names are published." % RELEASE),
        "financebench_url": FB_URL,
        "financebench_records": len(fb),
        "classes_all_records": all_classes,
        "snippets_in_own_page": [own_hits, own_total],
        "test_ids": len(test_ids),
        "test_ids_found": len(found),
        "test_classes": test_classes,
        "test_ids_by_class": {c: sorted(i for i in found if test_cls[i] == c) for c in g.CLASSES},
        "question_types_by_class": qtype_by_class,
        "train_ids": train_ids,
        "train_classes": train_classes,
        "group_error": group_err,
        "runs_listed": len(chosen),
        "runs_included": len(inc),
        "prompt_ok_min": f(prompt_ok_min),
        "cells_matched": [matched, len(order)],
        "published_cells": len(published),
        "pooled_by_class": pooled,
        "pooled_missing": pm,
        "pooled_complete": pc,
        "metrics_generated_missing": mm,
        "metrics_generated_complete": mc,
        "runs_lower_on_missing": lower,
        "tau_b_published_vs_complete_only": tau,
        "movers_3plus": movers,
        "leaders": leaders,
        "verdicts": {k: g.verdict_word(v) for k, v in verdicts.items()},
        "table": table,
        "runs": runs_out,
        "note": ("HELM's prompt holds only evidence[0]'s full page. Classes per question: single (one evidence item); "
                 "covered (every other item is on the same page or its snippet is in that page); missing (some item "
                 "on another page whose snippet is not in the given page but is in its own page); unverifiable "
                 "(otherwise). Matching ignores whitespace. complete = single + covered. Labels are HELM's stored "
                 "GPT-4o judge labels; 'published' is the Correct Answer column; 'complete_only' is the same share "
                 "over complete questions only."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
