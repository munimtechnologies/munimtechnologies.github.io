# SPDX-License-Identifier: Apache-2.0
"""Audit 118: how much of VHELM's published Unicorn scores can be earned without the image?

Lists every unicorn run of VHELM's run suite v2.1.2 in HELM's public bucket (crfm-helm-public), reads each run's
instances.json (question and gold), display_predictions.json (answer and stored quasi_prefix_exact_match) and stats.json
(run mean). Gate: every stored per-record score and the run mean are reproduced by our transcription of HELM's metric.
Then: question classes and gold tallies, the text-only baseline (presence -> Yes, unicorn -> 0, counting -> the best
constant count; Sketchy-VQA -> the best constant answer), each model's accuracy per class, prefix-only credits,
non-answers, rank changes and the eight pre-registered verdicts. Only run names, instance ids, classes, counts and public
model names go to results.json; a few answers go to the job log only, for the hand-read.
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

import grade118 as g

BUCKET = "crfm-helm-public"
SUITE = "v2.1.2"
RUNS_PREFIX = "vhelm/benchmark_output/runs/%s/" % SUITE
RUN_PREFIX = "unicorn:"
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
    subj = g.subject_of(run)
    rec = {"run": run, "model": g.model_of(run), "subject": subj}
    try:
        inst = _json(run_url(run, "instances.json"))
        preds = _json(run_url(run, "display_predictions.json"))
        stats = _json(run_url(run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    rec["imap"] = g.instance_map(subj, inst)
    rec["summary"] = g.summarize_run(preds, rec["imap"])
    rec["stat"] = g.stat_entry(stats, g.STAT)
    ni = g.stat_entry(stats, "num_instances")
    rec["num_instances_sum"] = None if ni is None else ni.get("sum")
    del inst, preds, stats
    return run, rec


def f(x):
    return None if x is None else float(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    chosen = list_runs()
    print("[suite] %s unicorn runs listed=%d" % (SUITE, len(chosen)))
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        loaded = dict(ex.map(load_run, chosen))

    # Reference instance maps per subject (the first run without a download error).
    ref = {}
    for run in chosen:
        r = loaded[run]
        if "error" not in r and r["subject"] not in ref:
            ref[r["subject"]] = r["imap"]
    imo, ims = ref.get("OODCV-VQA", {}), ref.get("Sketchy-VQA", {})

    def tally(imap):
        out = {}
        for c, gold in imap.values():
            out.setdefault(c, {})
            out[c][str(gold)] = out[c].get(str(gold), 0) + 1
        return out

    gold_tally = {"OODCV-VQA": tally(imo), "Sketchy-VQA": tally(ims)}
    best_count = g.best_constant([gd for c, gd in imo.values() if c == "count"])
    best_sketch = g.best_constant([gd for c, gd in ims.values() if c == "sketch"])
    blind_o = g.blind_score(imo, best_count, None)
    blind_s = g.blind_score(ims, None, best_sketch)
    c1 = (bool(imo) and all(gd == "Yes" for c, gd in imo.values() if c == "presence")
          and all(gd == "0" for c, gd in imo.values() if c == "unicorn"))
    textonly = sum(1 for c, _ in imo.values() if c in ("presence", "unicorn"))
    print("[ids] OODCV-VQA=%d Sketchy-VQA=%d" % (len(imo), len(ims)))
    print("[golds] %s" % json.dumps(gold_tally, sort_keys=True))
    print("[check C1] every presence gold is Yes and every unicorn gold is 0 = %s; presence+unicorn=%d of %d" % (
        c1, textonly, len(imo)))
    print("[check C2] text-only score OODCV-VQA=%s (best count %r); Sketchy-VQA best constant %r scores %s" % (
        f(blind_o), best_count, best_sketch, f(blind_s)))

    runs_out, inc = {}, {}
    for run in chosen:
        r = loaded[run]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "error": r["error"]}
            continue
        s = r["summary"]
        c = s["counts"]
        reasons = []
        if r["imap"] != ref.get(r["subject"]):
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
                         "model": r["model"], "subject": r["subject"], "counts": c}
        if not reasons:
            r["mean"] = mean
            inc[run] = r
    print("[runs] listed=%d included=%d" % (len(chosen), len(inc)))
    for run in chosen:
        if runs_out[run]["status"] != "included":
            print("[excluded] %s %s" % (run, runs_out[run].get("reasons") or runs_out[run].get("error")))

    oo = sorted(m for m in inc if inc[m]["subject"] == "OODCV-VQA")
    ss = sorted(m for m in inc if inc[m]["subject"] == "Sketchy-VQA")

    def pooled(cls):
        n = sum(inc[m]["summary"]["by_class"][cls]["n"] for m in oo)
        k = sum(inc[m]["summary"]["by_class"][cls]["credit"] for m in oo)
        return Fraction(k, n) if n else None

    pp, pu, pc = pooled("presence"), pooled("unicorn"), pooled("count")
    below_o = sorted(m for m in oo if blind_o is not None and inc[m]["mean"] < blind_o)
    below_s = sorted(m for m in ss if blind_s is not None and inc[m]["mean"] < blind_s)
    pub = {m: inc[m]["mean"] for m in oo}
    cnt = {m: g.acc(inc[m]["summary"]["by_class"]["count"]) or Fraction(0) for m in oo}
    rp, rc = g.ranks_high(pub), g.ranks_high(cnt)
    tau = g.kendall_tau_b([pub[m] for m in oo], [cnt[m] for m in oo]) if oo else None
    movers = sorted(m for m in oo if abs(rp[m] - rc[m]) >= PLACES)
    leaders = [m for m in oo if rp[m] == 1]
    leader_changes = (not any(rc[m] == 1 for m in leaders)) if leaders else None
    allinc = oo + ss
    p_credits = sum(inc[m]["summary"]["counts"]["credit"] for m in allinc)
    p_prefix = sum(inc[m]["summary"]["counts"]["prefix_only"] for m in allinc)
    nonans = sorted(m for m in allinc if (inc[m]["summary"]["kinds"]["other"] + inc[m]["summary"]["kinds"]["empty"])
                    * 20 >= inc[m]["summary"]["counts"]["kept"])

    def one_answer(m):
        a, n = inc[m]["summary"]["answers"], inc[m]["summary"]["counts"]["kept"]
        return max(a.get("yes", 0), a.get("no", 0)) * 5 >= n * 4

    sk80 = sorted(m for m in ss if one_answer(m))
    print("[pooled OODCV] presence=%s unicorn=%s count=%s" % (f(pp), f(pu), f(pc)))
    print("[below text-only] OODCV=%d of %d; Sketchy=%d of %d" % (len(below_o), len(oo), len(below_s), len(ss)))
    print("[ranks] OODCV published vs count-question accuracy: tau_b=%s movers(>=%d)=%d leaders=%s "
          "leader_changes=%s" % (tau, PLACES, len(movers), leaders, leader_changes))
    print("[prefix] prefix-only credits=%d of %d credits; runs with >=5%% non-answers=%d; Sketchy runs with one "
          "answer >=80%%=%d" % (p_prefix, p_credits, len(nonans), len(sk80)))

    table = []
    for m in sorted(allinc, key=lambda k: (inc[k]["subject"], -inc[k]["mean"], k)):
        s = inc[m]["summary"]
        row = {"run": m, "model": inc[m]["model"], "subject": inc[m]["subject"], "published": f(inc[m]["mean"]),
               "n": s["counts"]["kept"], "prefix_only": s["counts"]["prefix_only"], "kinds": s["kinds"],
               "yes": s["answers"].get("yes", 0), "no": s["answers"].get("no", 0),
               "by_class": {c: {"n": b["n"], "credit": b["credit"], "exact": b["exact"]}
                            for c, b in s["by_class"].items() if b["n"]}}
        if inc[m]["subject"] == "OODCV-VQA":
            tc = sum(s["by_class"][c]["credit"] for c in ("presence", "unicorn"))
            row.update({"count_accuracy": f(cnt[m]), "rank_published": rp[m], "rank_count": rc[m],
                        "credits_text_answerable": tc, "credits": s["counts"]["credit"]})
        table.append(row)
        print("[cell] %s" % json.dumps(row, sort_keys=True))

    stats = {"runs_listed": len(chosen), "runs_included": len(inc), "ids_oodcv": len(imo), "ids_sketchy": len(ims),
             "below_blind_oodcv": len(below_o) if blind_o is not None else None,
             "pooled_presence": pp, "pooled_unicorn": pu, "pooled_count": pc,
             "pooled_credits": p_credits, "pooled_prefix_only": p_prefix,
             "movers_count": len(movers) if oo else None, "runs_nonanswer5": len(nonans),
             "sketchy_one_answer80": len(sk80) if ss else None, "leader_changes": leader_changes}
    verdicts = g.verdicts(stats)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, g.verdict_word(v)))

    # Hand-read material (job log only): up to 8 prefix-only credits and 8 non-answers, one per run.
    for key in ("prefix_only", "other"):
        shown = 0
        for m in sorted(allinc, key=lambda x: (g.stable_hash(x + key), x)):
            ex = inc[m]["summary"]["examples"][key]
            if not ex or shown >= 8:
                continue
            shown += 1
            print("[read %s %d] run=%s id=%s gold=%r pred=%r" % (key, shown, m, ex[0][0], ex[0][1], ex[0][2]))

    out = {
        "audit": 118,
        "slug": "vhelm-unicorn-blind-answers",
        "dataset": ("Per-instance outputs of HELM's VHELM run suite %s (Stanford CRFM), every unicorn run in the "
                    "public bucket; Unicorn benchmark by Tu et al. (arXiv 2311.16101). Only run names, instance ids, "
                    "classes, counts and public model names are published." % SUITE),
        "ids": {"OODCV-VQA": len(imo), "Sketchy-VQA": len(ims)},
        "gold_tally": gold_tally,
        "check_c1": c1,
        "text_answerable_oodcv": textonly,
        "best_count": best_count,
        "best_sketch": best_sketch,
        "text_only_oodcv": f(blind_o),
        "text_only_sketchy": f(blind_s),
        "runs_listed": len(chosen),
        "runs_included": len(inc),
        "pooled_oodcv": {"presence": f(pp), "unicorn": f(pu), "count": f(pc)},
        "below_text_only_oodcv": below_o,
        "below_text_only_sketchy": below_s,
        "tau_b_published_vs_count": tau,
        "movers_3plus": movers,
        "leaders": leaders,
        "leader_changes": leader_changes,
        "pooled_credits": p_credits,
        "pooled_prefix_only": p_prefix,
        "runs_nonanswer5": nonans,
        "sketchy_one_answer80": sk80,
        "verdicts": {k: g.verdict_word(v) for k, v in verdicts.items()},
        "table": table,
        "runs": runs_out,
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
