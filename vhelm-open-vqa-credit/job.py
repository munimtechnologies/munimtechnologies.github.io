# SPDX-License-Identifier: Apache-2.0
"""Audit 122: how VHELM credits open-ended short answers (GQA, VQAv2 base, VizWiz), run suite v2.1.2.

Lists every gqa, vqa (groups=vqa_base, no data augmentation) and viz_wiz run in HELM's public bucket
(crfm-helm-public), reads instances.json, display_predictions.json and stats.json, re-grades every first-trial record
(grade122.py) and keeps a run only if our H reproduces the quasi_prefix_exact_match mean in stats.json and our Q the
quasi_exact_match mean (both within 1e-9), our H equals the per-record quasi_prefix_exact_match stored in
display_predictions.json on at least 99% of the records that carry one, and no record is unmatched or duplicated.
Then: credit classes per family, VQA-style consensus accuracy C on VQAv2, model ranks under H, Q and C, grounding
markup per model, and the eight pre-registered verdicts. Only run names, instance ids, classes, counts and public model
names go to results.json; reference and answer texts of the hand-read examples go to the job log only.
Usage: python job.py --out-dir /out (network required). Standard library only. Apache-2.0.
Made with AI agents working in MV2's name (MV2 of Munim, Inc.).
"""
import argparse
import json
import os
import statistics
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import grade122 as g

BUCKET = "crfm-helm-public"
SUITE = "v2.1.2"
RUNS_PREFIX = "vhelm/benchmark_output/runs/%s/" % SUITE
UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
WORKERS = 4
TOL = 1e-9
MIN_REC_AGREE = Fraction(99, 100)
SPLIT = "valid"
FAMILIES = ("gqa", "vqa", "viz_wiz")
QWEN_CHAT = "qwen_qwen-vl-chat"
MAX_IDS = 3000
PRINT_PER_CLASS = 30


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


def list_runs(family):
    runs, token = [], None
    while True:
        q = {"prefix": RUNS_PREFIX + family + ":", "delimiter": "/", "maxResults": "1000"}
        if token:
            q["pageToken"] = token
        doc = _json("https://storage.googleapis.com/storage/v1/b/%s/o?%s" % (BUCKET, urllib.parse.urlencode(q)))
        for p in doc.get("prefixes") or []:
            runs.append(p[len(RUNS_PREFIX):].rstrip("/"))
        token = doc.get("nextPageToken")
        if not token:
            return sorted(runs)


def keep_run(family, run):
    if family == "vqa":
        return "groups=vqa_base" in run and "data_augmentation" not in run
    return True


def run_url(run, fname):
    return "https://storage.googleapis.com/%s/%s%s/%s" % (
        BUCKET, RUNS_PREFIX, urllib.parse.quote(run, safe=":,=@-_."), fname)


def load_run(item):
    run, family = item
    rec = {"run": run, "family": family, "model": g.run_field(run, "model")}
    try:
        inst = _json(run_url(run, "instances.json"))
        preds = _json(run_url(run, "display_predictions.json"))
        stats = _json(run_url(run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return rec
    imap, perturbed = g.instance_map(inst, SPLIT)
    c, s, ex = g.summarize_run(preds, imap, consensus=(family == "vqa"))
    c["perturbed_instances"] = perturbed
    c["n_instances"] = len(imap)
    reasons = []
    stored_h, stored_q = g.stat_mean(stats, SPLIT, g.STAT), g.stat_mean(stats, SPLIT, g.QSTAT)
    ours_h = float(Fraction(s["h"], s["n"])) if s["n"] else None
    ours_q = float(Fraction(s["q"], s["n"])) if s["n"] else None
    if stored_h is None or ours_h is None or abs(ours_h - stored_h) > TOL:
        reasons.append("mean H")
    if stored_q is None or ours_q is None or abs(ours_q - stored_q) > TOL:
        reasons.append("mean Q")
    if c["rec_checked"] and Fraction(c["rec_agree"], c["rec_checked"]) < MIN_REC_AGREE:
        reasons.append("records H")
    if c["scored"] == 0 or c["duplicate"] or c["no_instance"]:
        reasons.append("records")
    rec.update({"counts": c, "sub": s, "examples": ex, "means": {"H": [ours_h, stored_h], "Q": [ours_q, stored_q]},
                "reasons": reasons})
    # Hand-read material for the log only (texts are never written to results.json).
    texts = {}
    want = {iid for iid, _cls, _m in ex[:PRINT_PER_CLASS * 2]}
    for p in preds or []:
        iid = p.get("instance_id") if isinstance(p, dict) else None
        if iid in want and p.get("train_trial_index", 0) == 0 and iid not in texts:
            texts[iid] = ((p.get("predicted_text") or "")[:70], [r[:40] for r in sorted(set(imap.get(iid) or []))][:6])
    rec["texts"] = texts
    md = [p.get("predicted_text") for p in preds or [] if isinstance(p, dict) and g.has_markup(p.get("predicted_text"))]
    rec["markup_sample"] = [(t or "")[:70] for t in md[:3]]
    return rec


def f(x):
    return None if x is None else float(x)


def rank_compare(per, a, b):
    """per {model: {score name: Fraction}} -> tau-b, movers (3+ places) and leaders between scores a and b."""
    ms = sorted(per)
    ra = g.min_ranks({m: per[m][a] for m in ms})
    rb = g.min_ranks({m: per[m][b] for m in ms})
    movers = sorted(m for m in ms if abs(ra[m] - rb[m]) >= 3)
    tau = g.kendall_tau_b([per[m][a] for m in ms], [per[m][b] for m in ms]) if len(ms) > 1 else None
    return {"tau_b": tau, "movers_3plus": movers, "max_move": max((abs(ra[m] - rb[m]) for m in ms), default=0),
            "leader_" + a: min(ms, key=lambda m: (ra[m], m)) if ms else None,
            "leader_" + b: min(ms, key=lambda m: (rb[m], m)) if ms else None,
            "ranks": {m: [ra[m], rb[m]] for m in ms}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    items, listed = [], {}
    for fam in FAMILIES:
        runs = [r for r in list_runs(fam) if keep_run(fam, r)]
        listed[fam] = len(runs)
        items.extend((r, fam) for r in runs)
        print("[suite] %s %s runs listed=%d" % (SUITE, fam, len(runs)))

    runs_out, inc = {}, {}
    fam_inc = {fam: 0 for fam in FAMILIES}
    read = {fam: {"mid_word": [], "empty_ref": [], "minority": []} for fam in FAMILIES}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for rec in ex.map(load_run, items):
            run, fam = rec["run"], rec["family"]
            if "error" in rec:
                runs_out[run] = {"status": "download_failed", "error": rec["error"]}
                print("[excluded] %s download_failed %s" % (run, rec["error"][:120]))
                continue
            c, s = rec["counts"], rec["sub"]
            status = "included" if not rec["reasons"] else "excluded"
            sj = dict(s, c_sum=f(s["c_sum"]))
            runs_out[run] = {"status": status, "model": rec["model"], "family": fam, "means": rec["means"],
                             "counts": c, "sub": sj}
            if status != "included":
                runs_out[run]["reasons"] = rec["reasons"]
                print("[excluded] %s %s %s %s" % (run, rec["reasons"], json.dumps(rec["means"]), json.dumps(c)))
                continue
            fam_inc[fam] += 1
            inc[run] = rec
            for iid, cls, m in rec["examples"]:
                key = cls if cls in ("mid_word", "empty_ref") else "minority"
                if len(read[fam][key]) < PRINT_PER_CLASS and iid in rec["texts"]:
                    read[fam][key].append((rec["model"], iid, m) + rec["texts"][iid])
            if s["markup"]:
                print("[markup] %s %s %d of %d records (credited %d) e.g. %r" % (
                    fam, rec["model"], s["markup"], s["n"], s["markup_h"], rec["markup_sample"][:2]))

    for fam in FAMILIES:
        print("[included] %s %d of %d" % (fam, fam_inc[fam], listed[fam]))

    # ----- Pooled classes per family -----
    pooled = {}
    for fam in FAMILIES:
        d = {"runs": 0, "n": 0, "h": 0, "q": 0, "cls": {k: 0 for k in g.CLASSES}, "minority": 0, "zero_match": 0,
             "m_hist": {"0": 0, "1": 0, "2": 0, "3": 0, "4+": 0}, "markup": 0, "rec_agree": 0, "rec_checked": 0}
        for rec in inc.values():
            if rec["family"] != fam:
                continue
            s, c = rec["sub"], rec["counts"]
            d["runs"] += 1
            for k in ("n", "h", "q", "minority", "zero_match", "markup"):
                d[k] += s[k]
            for k in g.CLASSES:
                d["cls"][k] += s["cls"][k]
            for k in d["m_hist"]:
                d["m_hist"][k] += s["m_hist"][k]
            d["rec_agree"] += c["rec_agree"]
            d["rec_checked"] += c["rec_checked"]
        pooled[fam] = d
        print("[pooled] %s %s" % (fam, json.dumps(d, sort_keys=True)))

    # ----- Per model scores and ranks per family -----
    models, per_fam = {}, {}
    for fam in FAMILIES:
        per = {}
        for rec in inc.values():
            if rec["family"] != fam or not rec["sub"]["n"]:
                continue
            s = rec["sub"]
            n = s["n"]
            sc = {"H": Fraction(s["h"], n), "Q": Fraction(s["q"], n),
                  "H_no_mid": Fraction(s["h"] - s["cls"]["mid_word"] - s["cls"]["empty_ref"], n)}
            if fam == "vqa" and s["c_n"] == n:
                sc["C"] = s["c_sum"] / n
            elif fam == "vqa":
                print("[consensus] %s: only %d of %d records have 10 annotator answers; no C" % (
                    rec["model"], s["c_n"], n))
            per[rec["model"]] = sc
        per_fam[fam] = per
        comps = {"H_vs_Q": rank_compare(per, "H", "Q"), "H_vs_H_no_mid": rank_compare(per, "H", "H_no_mid")}
        if fam == "vqa" and per and all("C" in v for v in per.values()):
            comps["H_vs_C"] = rank_compare(per, "H", "C")
        table = []
        for rec in sorted(inc.values(), key=lambda r: (-per_fam[fam].get(r["model"], {}).get("H", -1), r["model"])):
            if rec["family"] != fam or rec["model"] not in per:
                continue
            s, sc = rec["sub"], per[rec["model"]]
            table.append({"model": rec["model"], "n": s["n"], "H": f(sc["H"]), "Q": f(sc["Q"]), "C": f(sc.get("C")),
                          "H_no_mid": f(sc["H_no_mid"]), "credits": s["h"], "cls": s["cls"],
                          "minority": s["minority"], "zero_match": s["zero_match"], "markup": s["markup"],
                          "word_prefix_share": f(Fraction(s["cls"]["word_prefix"], s["h"])) if s["h"] else None})
        models[fam] = {"comparisons": {k: {kk: vv for kk, vv in v.items()} for k, v in comps.items()},
                       "table": table}
        for k, v in comps.items():
            print("[models %s %s] n=%d tau_b=%s movers=%d max_move=%d %s" % (
                fam, k, len(per), v["tau_b"], len(v["movers_3plus"]), v["max_move"],
                {kk: vv for kk, vv in v.items() if kk.startswith("leader_")}))

    # ----- Numbers behind the verdicts -----
    vqa_diffs = [v["H"] - v["C"] for v in per_fam["vqa"].values() if "C" in v]
    gqa_word_models = sorted(r["model"] for r in inc.values() if r["family"] == "gqa" and r["sub"]["h"]
                             and Fraction(r["sub"]["cls"]["word_prefix"], r["sub"]["h"]) >= g.THRESHOLDS["P6_share"])
    qwen = {}
    for rec in inc.values():
        if rec["model"] == QWEN_CHAT:
            qwen[rec["family"]] = (rec["sub"]["markup"], rec["sub"]["n"])
    hvc = models["vqa"]["comparisons"].get("H_vs_C")
    st = {"fam_inc": {fam: (fam_inc[fam], listed[fam]) for fam in FAMILIES},
          "vqa_credits": pooled["vqa"]["h"], "vqa_minority": pooled["vqa"]["minority"],
          "vqa_zero_match": pooled["vqa"]["zero_match"],
          "vqa_median_diff": statistics.median(vqa_diffs) if vqa_diffs else None,
          "vqa_movers": len(hvc["movers_3plus"]) if hvc else 0,
          "gqa_credits": pooled["gqa"]["h"], "gqa_mid": pooled["gqa"]["cls"]["mid_word"],
          "gqa_word_models": len(gqa_word_models), "qwen_markup": qwen}
    num = {k: (f(v) if isinstance(v, Fraction) else v) for k, v in st.items()}
    num["fam_inc"] = {k: list(v) for k, v in st["fam_inc"].items()}
    num["qwen_markup"] = {k: list(v) for k, v in qwen.items()}
    num["gqa_word_prefix_models"] = gqa_word_models
    num["vqa_diff_min_max"] = [f(min(vqa_diffs)), f(max(vqa_diffs))] if vqa_diffs else None
    print("[numbers] %s" % json.dumps(num, sort_keys=True))
    vd = g.verdicts(st)
    for k in sorted(vd):
        print("[verdict] %s = %s" % (k, g.verdict_word(vd[k])))

    # ----- Hand-read material (job log only) -----
    for fam in FAMILIES:
        for key in ("mid_word", "empty_ref", "minority"):
            for i, (model, iid, m, ptxt, refs) in enumerate(read[fam][key], 1):
                print("[read %s %s %d] %s id=%s m=%d pred=%r refs=%r" % (fam, key, i, model, iid, m, ptxt, refs))

    ids = {fam: {"mid_word": [], "empty_ref": []} for fam in FAMILIES}
    for run, rec in sorted(inc.items()):
        for iid, cls, _m in rec["examples"]:
            if cls in ("mid_word", "empty_ref") and len(ids[rec["family"]][cls]) < MAX_IDS:
                ids[rec["family"]][cls].append({"model": rec["model"], "id": iid})
    out = {
        "audit": 122,
        "slug": "vhelm-open-vqa-credit",
        "dataset": ("Per-instance outputs of HELM's VHELM run suite %s (Stanford CRFM): every gqa, vqa (vqa_base) and "
                    "viz_wiz run in the public bucket. GQA by Hudson and Manning (arXiv 1902.09506), VQAv2 by Goyal et "
                    "al. (arXiv 1612.00837), VizWiz by Gurari et al. (arXiv 1802.08218). Only run names, instance ids, "
                    "classes, counts and public model names are published." % SUITE),
        "runs_listed": listed,
        "runs_included": fam_inc,
        "pooled": pooled,
        "models": models,
        "numbers": num,
        "verdicts": {k: g.verdict_word(v) for k, v in vd.items()},
        "prefix_credit_ids": ids,
        "runs": runs_out,
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"), ensure_ascii=True)  # compact: publish lane limit is 2 MB
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
