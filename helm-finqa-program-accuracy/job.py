"""Audit 107: does HELM Finance's FinQA "Program Accuracy" score right programs 0 for how they are written?

Downloads every fin_qa run of HELM Finance release v1.0.0, re-scores every test record with HELM's FinQAMetric
(program_accuracy and execution_accuracy; transcribed here, calling FinQA's evaluate.py functions as vendored by HELM
at a pinned commit, downloaded at run time), which must reproduce every stored per-record score and run mean, then
re-scores with argument-normalised program accuracy (ANPA: hyphenated table operations renamed, 'none' added to
one-argument table operations, numeric arguments compared by value), classes every up-flip, rebuilds the published
cells, re-ranks and writes the eight pre-registered verdicts. Only run names, instance ids, trials, classes, counts
and public model names go to results.json; programs and outputs go to the job log only, for the hand-read.
Usage: python job.py --out-dir /out (network required). Apache-2.0 (FinQAMetric's two scoring functions are
transcribed from stanford-crfm/helm, Apache-2.0; FinQA's evaluate.py, MIT, is downloaded, not redistributed).
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
import tempfile
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import grade107 as g

HELM_BASE = "https://storage.googleapis.com/crfm-helm-public/finance/benchmark_output"
RELEASE = "v1.0.0"
PREFIX = "fin_qa:"
GROUP = "fin_qa"
HELPER_URL = ("https://raw.githubusercontent.com/stanford-crfm/helm/ca72bdbecf593ed909ce154699ce11e7dd907f5d/"
              "src/helm/benchmark/metrics/fin_qa_metrics_helper.py")
UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
WORKERS = 2
TOL_RUN = 1e-9
TOL_CELL = 1e-6
PLACES = 3
EA_GAP = Fraction(1, 20)
PRINT_PER_CLASS = 8

# Hand-traced checks of the downloaded helper + our wrappers, run before any HELM data is read.
# (gold program, exe_ans, table json, prediction, expected subset)
HELPER_FIX = [
    ("subtract(5829, 5735), divide(#0, 5735)", "0.01639", "[]",
     "subtract(5829, 5735), divide(#0, 5735)", {"pa": 1, "ea": 1, "anpa": 1, "anea": 1, "cls": None}),
    ("subtract(5829, 5735), divide(#0, 5735)", "0.01639", "[]",
     "subtract(5829, 5735), divide(#0, 5735.0)", {"pa": 0, "ea": 1, "anpa": 1, "anea": 1, "cls": "number_form"}),
    ("divide(9413, 20.01), multiply(#0, const_100)", "47041.47926", "[]",
     "divide(9413, 20.01), multiply(#0, 100)", {"pa": 0, "anpa": 1, "cls": "const"}),
    ("table_max(net revenue, none)", "30.0", '[["net revenue", "$ 10", "$ 30"]]',
     "table-max(net revenue, none)", {"pa": 0, "ea": 0, "anpa": 1, "anea": 1, "cls": "table_name", "hyphen": True}),
    ("table_max(net revenue, none)", "30.0", '[["net revenue", "$ 10", "$ 30"]]',
     "table_max(net revenue)", {"pa": 0, "ea": 0, "anpa": 1, "anea": 1, "cls": "table_none", "onearg": True}),
    ("subtract(5829, 5735), divide(#0, 5735)", "0.01639", "[]",
     "subtract(5735, 5829), divide(#0, 5735)", {"pa": 0, "anpa": 0, "cls": None}),
]


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


def load_helper():
    raw = _get(HELPER_URL)
    sha = hashlib.sha256(raw).hexdigest()
    d = tempfile.mkdtemp(prefix="finqa-helper-")
    path = os.path.join(d, "fin_qa_metrics_helper.py")
    with open(path, "wb") as fh:
        fh.write(raw)
    spec = importlib.util.spec_from_file_location("fin_qa_metrics_helper", path)
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    h.print = lambda *a, **k: None  # silence its "structure error" prints (module global shadows the builtin)
    return h, sha


def make_grader(h):
    cache = {}

    def prog_acc(gold_toks, pred_toks):
        """HELM's _get_program_accuracy (equal_program(gold, pred)); (grade, error)."""
        try:
            return (1 if h.equal_program(list(gold_toks), list(pred_toks)) else 0), False
        except Exception:  # noqa: BLE001 - HELM would have crashed; counted, scored 0
            return 0, True

    def exec_acc(ref_exec, pred_toks, table):
        """HELM's _get_execution_accuracy, transcribed."""
        invalid_flag, generated = h.eval_program(list(pred_toks), table)
        if invalid_flag:
            return 0
        if ref_exec == "yes" or ref_exec == "no":
            return 1 if ref_exec == generated else 0
        if not isinstance(generated, float):
            return 0
        return 1 if math.isclose(float(ref_exec), generated) else 0

    def grade(gold_prog, exe, table_text, iid, pred_text):
        key = (iid, gold_prog, pred_text)
        if iid is not None and key in cache:
            return cache[key]
        pred = (pred_text or "").strip()
        table = json.loads(table_text)
        p_raw = h.program_tokenization(pred)
        pa, e1 = prog_acc(h.program_tokenization(gold_prog), p_raw)
        ea = exec_acc(exe, p_raw, table)
        g_n = g.norm_tokens(h.program_tokenization(g.norm_text(gold_prog)), "all")
        p_n = g.norm_tokens(h.program_tokenization(g.norm_text(pred)), "all")
        anpa, e2 = prog_acc(g_n, p_n)
        anea = exec_acc(exe, g.norm_tokens(h.program_tokenization(g.norm_text(pred)), "all", None), table)
        cls = None
        if anpa == 1 and pa == 0:
            flips = {}
            for c, (hy, no, mode) in g.SINGLE_FIXES:
                gt = g.norm_tokens(h.program_tokenization(g.norm_text(gold_prog, hy, no)), mode)
                pt = g.norm_tokens(h.program_tokenization(g.norm_text(pred, hy, no)), mode)
                flips[c] = prog_acc(gt, pt)[0] == 1
            cls = g.up_class(flips)
        out = {"pa": pa, "ea": ea, "anpa": anpa, "anea": anea, "cls": cls,
               "hyphen": bool(g.HYPHEN_RE.search(pred)),
               "onearg": bool(g.ONEARG_RE.search(g.norm_text(pred, True, False))),
               "invalid": h.eval_program(list(p_raw), table)[0] == 1, "err": e1 or e2}
        if iid is not None:
            cache[key] = out
        return out

    return grade


def helper_fixture_ok(grade):
    ok = []
    for gold, exe, table, pred, want in HELPER_FIX:
        r = grade(gold, exe, table, None, pred)
        ok.append(all(r.get(k) == v for k, v in want.items()))
    return ok


def load_run(args):
    run, grade = args
    rec = {"run": run, "model": g.model_of(run)}
    try:
        inst = _json(run_url(run, "instances.json"))
        preds = _json(run_url(run, "display_predictions.json"))
        pis = _json(run_url(run, "per_instance_stats.json"))
        stats = _json(run_url(run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    s = g.summarize_run(inst, preds, pis, grade)
    gold = {i.get("id"): i for i in inst if isinstance(i, dict) and i.get("split") == "test"}
    want = {}
    for cls in g.KEY_CLASSES:
        k = g.pick(s["keys"][cls], run + "|" + cls)
        if k is not None:
            want[k] = cls
    texts = {}
    for r in preds:
        if isinstance(r, dict) and r.get("perturbation") is None:
            key = (r.get("instance_id"), r.get("train_trial_index", 0))
            if key in want and key not in texts:
                refs = gold[key[0]].get("references") or []
                texts[key] = (want[key], refs[0]["output"]["text"], refs[1]["output"]["text"], r.get("predicted_text"))
    ni = g.stat_entry(stats, "num_instances")
    rec.update({"summary": s, "texts": texts, "pa_stat": g.stat_entry(stats, "program_accuracy"),
                "ea_stat": g.stat_entry(stats, "execution_accuracy"),
                "num_instances_sum": None if ni is None else ni.get("sum")})
    del inst, preds, pis, stats
    return run, rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    h, sha = load_helper()
    grade = make_grader(h)
    fx = helper_fixture_ok(grade)
    print("[helper] sha256=%s fixtures=%s" % (sha, fx))
    if not all(fx):
        raise SystemExit("helper fixture mismatch -- aborting before real data")

    run_suites = _json("%s/releases/%s/runs_to_run_suites.json" % (HELM_BASE, RELEASE))
    chosen = sorted(g.select_runs(run_suites, PREFIX))
    print("[release] %s runs listed=%d" % (RELEASE, len(chosen)))
    try:
        published = g.group_values(_json("%s/releases/%s/groups/%s.json" % (HELM_BASE, RELEASE, GROUP))) or []
        group_err = None
    except Exception as e:  # noqa: BLE001
        published, group_err = [], str(e)[:200]
    print("[group] Program Accuracy cells published=%d error=%s" % (len(published), group_err))

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        loaded = dict(ex.map(load_run, [(r, grade) for r in chosen]))

    runs_out, inc = {}, {}
    for run in chosen:
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "error": r["error"]}
            continue
        s = r["summary"]
        pm, em = g.run_mean(s["trials"], "pa"), g.run_mean(s["trials"], "ea")
        reasons = []
        if s["pa_missing"] or s["pa_mismatch"]:
            reasons.append("pa_records")
        nis = r["num_instances_sum"]
        if nis is None or s["counts"]["kept"] != int(round(nis)):
            reasons.append("instances")
        st = r["pa_stat"]
        if st is None or st.get("mean") is None or pm is None or abs(float(pm) - st["mean"]) > TOL_RUN:
            reasons.append("pa_mean")
        # Execution accuracy is not the published column: its own gate decides only whether a run counts for P8.
        est = r["ea_stat"]
        ea_ok = (not s["ea_missing"] and not s["ea_mismatch"] and est is not None and est.get("mean") is not None
                 and em is not None and abs(float(em) - est["mean"]) <= TOL_RUN)
        r["ea_ok"] = ea_ok
        runs_out[run] = {"status": "included" if not reasons else "excluded", "reasons": reasons, "ea_ok": ea_ok,
                         "model": r["model"], "counts": s["counts"], "classes": s["classes"],
                         **{k: s[k] for k in ("up", "down", "exec_only", "anea_up", "anea_down", "hyphen", "onearg",
                                              "invalid", "errors", "pa_missing", "pa_mismatch", "ea_missing",
                                              "ea_mismatch")},
                         "pa": None if pm is None else float(pm), "ea": None if em is None else float(em),
                         "anpa": float(g.run_mean(s["trials"], "anpa") or 0),
                         "anea": float(g.run_mean(s["trials"], "anea") or 0)}
        if not reasons:
            inc[run] = r
    print("[runs] listed=%d included=%d" % (len(chosen), len(inc)))
    for run in chosen:
        if runs_out[run]["status"] != "included":
            print("[excluded] %s %s" % (run, runs_out[run].get("reasons") or runs_out[run].get("error")))

    tot = {"records": 0, "pa": 0, "ea": 0, "anpa": 0, "anea": 0}
    pooled = {k: 0 for k in ("up", "down", "exec_only", "anea_up", "anea_down", "hyphen", "onearg", "invalid",
                             "errors")}
    classes = {c: 0 for c in g.UP_CLASSES}
    for r in inc.values():
        s = r["summary"]
        for v in s["trials"].values():
            tot["records"] += v["n"]
            for k in ("pa", "ea", "anpa", "anea"):
                tot[k] += v[k]
        for k in pooled:
            pooled[k] += s[k]
        for c, v in s["classes"].items():
            classes[c] += v
    print("[totals] %s %s classes=%s" % (tot, pooled, classes))

    order = sorted(inc)
    cells = {k: {m: g.run_mean(inc[m]["summary"]["trials"], k) for m in order} for k in ("pa", "ea", "anpa", "anea")}
    matched = g.match_cells({m: float(v) for m, v in cells["pa"].items()}, published, TOL_CELL)
    rp, ra = g.ranks_high(cells["pa"]), g.ranks_high(cells["anpa"])
    tau = g.kendall_tau_b([cells["pa"][m] for m in order], [cells["anpa"][m] for m in order])
    tau_ea = g.kendall_tau_b([cells["pa"][m] for m in order], [cells["ea"][m] for m in order])
    movers = sorted(m for m in order if abs(rp[m] - ra[m]) >= PLACES)
    rises = {m: cells["anpa"][m] - cells["pa"][m] for m in order}
    max_rise = max(rises.values()) if rises else None
    leaders = [m for m in order if rp[m] == 1]
    leader_ok = bool(leaders) and all(ra[m] == 1 for m in leaders)
    ea_gap_runs = sum(1 for m in order if inc[m]["ea_ok"] and cells["ea"][m] - cells["pa"][m] >= EA_GAP)
    print("[ea-gate] runs passing the execution-accuracy gate: %d of %d" % (
        sum(1 for m in order if inc[m]["ea_ok"]), len(order)))
    table = [{"run": m, "model": inc[m]["model"], "published_pa": float(cells["pa"][m]),
              "anpa": float(cells["anpa"][m]), "ea": float(cells["ea"][m]), "anea": float(cells["anea"][m]),
              "rise": float(rises[m]), "rank_published": rp[m], "rank_anpa": ra[m]}
             for m in sorted(order, key=lambda k: (rp[k], k))]
    print("[cells] matched %d of %d (published %d)" % (matched, len(order), len(published)))
    print("[ranks] tau_b pa vs anpa=%s pa vs ea=%s movers(>=%d)=%d max_rise=%s leaders=%s leader_ok=%s "
          "ea_gap_runs=%d" % (tau, tau_ea, PLACES, len(movers), None if max_rise is None else float(max_rise),
                              leaders, leader_ok, ea_gap_runs))
    for row in table:
        print("[cell] %s" % row)

    stats = {"fixtures": all(fx), "runs_listed": len(chosen), "runs_included": len(inc), "cells_matched": matched,
             "records": tot["records"], "up": pooled["up"], "up_classes": classes, "hyphen": pooled["hyphen"],
             "max_rise": max_rise, "tau": tau, "leader_ok": leader_ok, "ea_gap_runs": ea_gap_runs}
    verdicts = g.verdicts(stats)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, "HELD" if v else "FAILED"))

    shown = {}
    for run in sorted(inc, key=lambda x: (g.stable_hash(x), x)):
        for key, (cls, gp, exe, pred) in sorted(inc[run]["texts"].items(), key=lambda kv: (kv[1][0], str(kv[0]))):
            n = shown.get(cls, 0)
            if n >= PRINT_PER_CLASS:
                continue
            shown[cls] = n + 1
            print("[read %s %d] run=%s id=%s trial=%s gold=%r exe=%r pred=%r" % (
                cls, n + 1, run, key[0], key[1], gp, exe, (pred or "")[:300]))

    def frac(a, b):
        return None if not b else float(Fraction(a, b))

    out = {
        "audit": 107,
        "slug": "helm-finqa-program-accuracy",
        "dataset": ("Per-instance outputs of HELM Finance release %s (Stanford CRFM): every fin_qa run listed in "
                    "runs_to_run_suites.json, test split. Only run names, instance ids, trials, classes, counts and "
                    "public model names are published." % RELEASE),
        "helper": {"url": HELPER_URL, "sha256": sha, "fixtures": fx},
        "group_error": group_err,
        "runs_listed": len(chosen),
        "runs_included": len(inc),
        "cells_matched": [matched, len(order)],
        "published_cells": len(published),
        "totals": dict(tot, **pooled, up_share_of_records=frac(pooled["up"], tot["records"]),
                       up_share_of_pa=frac(pooled["up"], tot["pa"])),
        "up_classes": classes,
        "tau_b": {"pa_vs_anpa": tau, "pa_vs_ea": tau_ea},
        "movers_3plus": movers,
        "max_rise": None if max_rise is None else float(max_rise),
        "leaders": leaders,
        "ea_gap_runs": ea_gap_runs,
        "verdicts": {k: ("HELD" if v else "FAILED") for k, v in verdicts.items()},
        "table": table,
        "runs": runs_out,
        "note": ("pa = HELM's program_accuracy (the published column); ea = HELM's execution_accuracy (archived, not "
                 "shown on the leaderboard); anpa = argument-normalised program accuracy (hyphenated table operations "
                 "renamed, ', none' added to one-argument table operations, numeric arguments compared by value: "
                 "const_100 = 100, 5,829 = 5829, 14.1% = 0.141); anea = execution accuracy with the same table fixes. "
                 "up = anpa 1 and pa 0, classed by the first single fix that alone gives credit (table_name, "
                 "table_none, const, number_form) else combined; exec_only = ea 1 and anpa 0."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
