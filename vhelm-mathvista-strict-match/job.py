# SPDX-License-Identifier: Apache-2.0
"""Audit 119: what does VHELM's strict exact match leave uncredited on MathVista's free-form questions?

Lists every math_vista free_form run of VHELM's run suite v2.1.2 in HELM's public bucket (crfm-helm-public), reads
each run's run_spec.json (max_tokens), instances.json (question and golds), display_predictions.json (answer, stored
exact_match, output tokens) and stats.json (run mean). Gate: every stored per-record score and the run mean are
reproduced by our transcription of HELM's exact_match. Then: gold kinds, whether any sent question carries MathVista's
'Hint:' line, a class for every uncredited answer (format-only numeric equality, MathVista-official rounding to the
gold's decimals, answers cut at the token cap, ...), a lenient free-form score per model, rank changes and the eight
pre-registered verdicts. Only run names, instance ids, classes, counts and public model names go to results.json; a
few answers go to the job log only, for the hand-read.
Usage: python job.py --out-dir /out (network required). Standard library only. Apache-2.0.
Made with AI agents working in MV2's name (MV2 of Munim, Inc.).
"""
import argparse
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import grade119 as g

BUCKET = "crfm-helm-public"
SUITE = "v2.1.2"
RUNS_PREFIX = "vhelm/benchmark_output/runs/%s/" % SUITE
RUN_PREFIX = "math_vista:"
UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
WORKERS = 3
TOL_RUN = 1e-9
PLACES = 3


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


def list_runs():
    runs, token = [], None
    while True:
        q = {"prefix": RUNS_PREFIX + RUN_PREFIX, "delimiter": "/", "maxResults": "1000"}
        if token:
            q["pageToken"] = token
        doc = _json("https://storage.googleapis.com/storage/v1/b/%s/o?%s" % (BUCKET, urllib.parse.urlencode(q)))
        for p in doc.get("prefixes") or []:
            runs.append(p[len(RUNS_PREFIX):].rstrip("/"))
        token = doc.get("nextPageToken")
        if not token:
            return sorted(runs)


def run_url(run, fname):
    return "https://storage.googleapis.com/%s/%s%s/%s" % (
        BUCKET, RUNS_PREFIX, urllib.parse.quote(run, safe=":,=@-_."), fname)


def load_run(run):
    rec = {"run": run, "model": g.run_field(run, "model"), "grade": g.run_field(run, "grade")}
    try:
        spec = _json(run_url(run, "run_spec.json"))
        inst = _json(run_url(run, "instances.json"))
        preds = _json(run_url(run, "display_predictions.json"))
        stats = _json(run_url(run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    rec["max_tokens"] = (spec.get("adapter_spec") or {}).get("max_tokens")
    rec["imap"] = g.instance_map(inst)
    rec["summary"] = g.summarize_run(preds, rec["imap"], rec["max_tokens"])
    rec["stat"] = g.stat_entry(stats, g.STAT)
    ni = g.stat_entry(stats, "num_instances")
    rec["num_instances_sum"] = None if ni is None else ni.get("sum")
    del spec, inst, preds, stats
    return run, rec


def f(x):
    return None if x is None else float(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    listed = list_runs()
    chosen = [r for r in listed if g.run_field(r, "question_type") == "free_form"]
    print("[suite] %s math_vista runs listed=%d free_form=%d" % (SUITE, len(listed), len(chosen)))
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        loaded = dict(ex.map(load_run, chosen))

    ref = {}
    for run in chosen:
        r = loaded[run]
        if "error" not in r and r["grade"] not in ref:
            ref[r["grade"]] = r["imap"]
    kinds = {}
    hints = 0
    for gr, im in sorted(ref.items()):
        for k, _, h in im.values():
            kinds.setdefault(gr, {}).setdefault(k, 0)
            kinds[gr][k] += 1
            hints += 1 if h else 0
    total_ids = sum(len(im) for im in ref.values())
    print("[check C1] free-form ids per grade %s; total=%d; gold kinds %s" % (
        {k: len(v) for k, v in sorted(ref.items())}, total_ids, json.dumps(kinds, sort_keys=True)))
    print("[check C2] sent questions containing 'Hint:' = %d of %d" % (hints, total_ids))

    runs_out, inc = {}, {}
    for run in chosen:
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "error": r["error"]}
            continue
        s = r["summary"]
        c = s["counts"]
        reasons = []
        if r["imap"] != ref.get(r["grade"]):
            reasons.append("test_ids")
        if c["stored_missing"] or c["mismatch"]:
            reasons.append("stored")
        nis = r["num_instances_sum"]
        if nis is None or c["kept"] != int(round(nis)):
            reasons.append("instances")
        mean = Fraction(c["credit"], c["kept"]) if c["kept"] else None
        st = r["stat"]
        if st is None or st.get("mean") is None or mean is None or abs(float(mean) - st["mean"]) > TOL_RUN:
            reasons.append("mean")
        runs_out[run] = {"status": "included" if not reasons else "excluded", "reasons": reasons,
                         "model": r["model"], "grade": r["grade"], "max_tokens": r["max_tokens"],
                         "counts": c, "classes": s["classes"], "cap_by_class": s["cap_by_class"],
                         "tags": s["tags"], "by_kind": s["by_kind"], "float_single": s["float_single"],
                         "lenient": s["lenient"]}
        if not reasons:
            inc[run] = r
    print("[runs] free_form=%d included=%d" % (len(chosen), len(inc)))
    for run in chosen:
        if runs_out[run]["status"] != "included":
            print("[excluded] %s %s" % (run, runs_out[run].get("reasons") or runs_out[run].get("error")))

    # Pooled census over included runs.
    pooled = {c: 0 for c in g.CLASSES}
    cap_cls = {c: 0 for c in g.CLASSES}
    tags = {t: 0 for t in g.TAGS}
    by_kind = {k: {"n": 0, "credit": 0, "lenient": 0} for k in ("integer", "float", "list", "other")}
    fs_n = fs_o = recs = caps = 0
    for run, r in inc.items():
        s = r["summary"]
        recs += s["counts"]["kept"]
        caps += s["counts"]["cap"]
        fs_n += s["float_single"]["n"]
        fs_o += s["float_single"]["other_decimals"]
        for c in g.CLASSES:
            pooled[c] += s["classes"][c]
            cap_cls[c] += s["cap_by_class"][c]
        for t in g.TAGS:
            tags[t] += s["tags"][t]
        for k in by_kind:
            for x in ("n", "credit", "lenient"):
                by_kind[k][x] += s["by_kind"][k][x]
    print("[pooled] records=%d classes=%s" % (recs, json.dumps(pooled, sort_keys=True)))
    print("[pooled] cap hits=%d by class=%s" % (caps, json.dumps(cap_cls, sort_keys=True)))
    print("[pooled] format tags=%s" % json.dumps(tags, sort_keys=True))
    print("[pooled] by gold kind=%s" % json.dumps(by_kind, sort_keys=True))
    print("[pooled] float golds with a single-number answer=%d; other number of decimals=%d" % (fs_n, fs_o))

    # Per model (only models with all four grades included).
    models = {}
    for run, r in inc.items():
        models.setdefault(r["model"], []).append(r)
    complete = sorted(m for m, rs in models.items() if sorted(x["grade"] for x in rs) == sorted(g.GRADES))
    em, len_acc, cap_share, table = {}, {}, {}, []
    for m in complete:
        rs = models[m]
        n = sum(x["summary"]["counts"]["kept"] for x in rs)
        k = sum(x["summary"]["counts"]["credit"] for x in rs)
        le = sum(x["summary"]["lenient"] for x in rs)
        cp = sum(x["summary"]["counts"]["cap"] for x in rs)
        em[m] = Fraction(k, n) if n else Fraction(0)
        len_acc[m] = Fraction(le, n) if n else Fraction(0)
        cap_share[m] = Fraction(cp, n) if n else Fraction(0)
    re_, rl = g.ranks_high(em), g.ranks_high(len_acc)
    tau = g.kendall_tau_b([em[m] for m in complete], [len_acc[m] for m in complete]) if len(complete) > 1 else None
    gains = {m: len_acc[m] - em[m] for m in complete}
    max_gain = max(gains.values()) if gains else None
    movers = sorted(m for m in complete if abs(re_[m] - rl[m]) >= PLACES)
    cap2 = sorted(m for m in complete if cap_share[m] >= Fraction(2, 100))
    for m in sorted(complete, key=lambda x: (-em[x], x)):
        cls = {c: sum(x["summary"]["classes"][c] for x in models[m]) for c in g.CLASSES}
        row = {"model": m, "n": sum(x["summary"]["counts"]["kept"] for x in models[m]),
               "exact_match": f(em[m]), "lenient": f(len_acc[m]), "gain": f(gains[m]),
               "rank_exact": re_[m], "rank_lenient": rl[m], "cap_share": f(cap_share[m]),
               "max_tokens": sorted({x["max_tokens"] for x in models[m]}, key=str), "classes": cls}
        table.append(row)
        print("[model] %s" % json.dumps(row, sort_keys=True))
    print("[models] complete=%d tau_b(exact vs lenient)=%s movers(>=%d)=%d max_gain=%s cap>=2%%=%d" % (
        len(complete), tau, PLACES, len(movers), f(max_gain), len(cap2)))

    stats = {"runs_listed": len(chosen), "runs_included": len(inc), "models_complete": len(complete),
             "pooled_records": recs, "pooled_num_equal": pooled["num_equal"],
             "pooled_rounds_to_gold": pooled["rounds_to_gold"], "float_single_n": fs_n, "float_single_other": fs_o,
             "models_cap2": len(cap2), "tau_b": tau, "max_gain": max_gain}
    verdicts = g.verdicts(stats)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, g.verdict_word(v)))

    # Hand-read material (job log only): up to 8 examples per class, one per run.
    for key in ("num_equal", "rounds_to_gold", "last_number_equal", "int_trunc_official"):
        shown = 0
        for run in sorted(inc, key=lambda x: (g.stable_hash(x + key), x)):
            ex = inc[run]["summary"]["examples"][key]
            if not ex or shown >= 8:
                continue
            shown += 1
            print("[read %s %d] run=%s id=%s gold=%r pred=%r" % (key, shown, run, ex[0][0], ex[0][1], ex[0][2]))

    out = {
        "audit": 119,
        "slug": "vhelm-mathvista-strict-match",
        "dataset": ("Per-instance outputs of HELM's VHELM run suite %s (Stanford CRFM), every math_vista free_form "
                    "run in the public bucket; MathVista testmini by Lu et al. (arXiv 2310.02255). Only run names, "
                    "instance ids, classes, counts and public model names are published." % SUITE),
        "ids_per_grade": {k: len(v) for k, v in sorted(ref.items())},
        "gold_kinds": kinds,
        "questions_with_hint": hints,
        "runs_listed_free_form": len(chosen),
        "runs_included": len(inc),
        "pooled_records": recs,
        "pooled_classes": pooled,
        "pooled_cap_hits": caps,
        "pooled_cap_by_class": cap_cls,
        "pooled_tags": tags,
        "pooled_by_gold_kind": by_kind,
        "float_single_number": {"n": fs_n, "other_decimals": fs_o},
        "models_complete": len(complete),
        "tau_b_exact_vs_lenient": tau,
        "movers_3plus": movers,
        "max_gain": f(max_gain),
        "models_cap_2pct": cap2,
        "verdicts": {k: g.verdict_word(v) for k, v in verdicts.items()},
        "table": table,
        "runs": runs_out,
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
