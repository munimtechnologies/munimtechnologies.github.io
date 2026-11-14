# SPDX-License-Identifier: Apache-2.0
"""Audit 120: how much of VHELM's letter-answer credit comes from the gold "A" normalising to nothing?

Lists every exams_v, mm_star and blink run of VHELM's run suite v2.1.2 in HELM's public bucket (crfm-helm-public),
reads each run's instances.json (golds), display_predictions.json (answer, stored quasi_prefix_exact_match) and
stats.json (run mean). Gate: every stored per-record score and the run mean are reproduced by our transcription of
HELM's quasi_prefix_exact_match. Then: a class for every credited record (genuine / free credit on a gold that
normalises to "" / a prefix word such as "Both" for B), a letter grade that keeps articles, per-family model means and
rank changes, the EXAMS-V Cyrillic-gold and empty-run checks, and the eight pre-registered verdicts. Only run names,
instance ids, classes, counts and public model names go to results.json; a few answers go to the job log only.
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

import grade120 as g

BUCKET = "crfm-helm-public"
SUITE = "v2.1.2"
RUNS_PREFIX = "vhelm/benchmark_output/runs/%s/" % SUITE
UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
WORKERS = 4
TOL_RUN = 1e-9
PLACES = 3
DROP = Fraction(5, 100)


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


def run_url(run, fname):
    return "https://storage.googleapis.com/%s/%s%s/%s" % (
        BUCKET, RUNS_PREFIX, urllib.parse.quote(run, safe=":,=@-_."), fname)


def load_run(run):
    fam = g.family_of(run)
    split = g.FAMILIES[fam]
    rec = {"run": run, "family": fam, "model": g.run_field(run, "model"), "language": g.run_field(run, "language")}
    try:
        inst = _json(run_url(run, "instances.json"))
        imap = g.instance_map(inst)
        rec["n_instances_main"] = sum(1 for v in imap.values() if v["split"] == split)
        if rec["n_instances_main"] == 0:
            rec["empty"] = True
            return run, rec
        preds = _json(run_url(run, "display_predictions.json"))
        stats = _json(run_url(run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return run, rec
    rec["summary"] = g.summarize_run(preds, imap, split)
    st = g.stat_entry(stats, g.STAT, split)
    rec["stat_mean"] = None if st is None else st.get("mean")
    ni = g.stat_entry(stats, "num_instances", split)
    rec["num_instances_sum"] = None if ni is None else ni.get("sum")
    return run, rec


def f(x):
    return None if x is None else float(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    listed = {}
    for fam in g.FAMILIES:
        listed[fam] = list_runs(fam)
        print("[suite] %s %s runs listed=%d" % (SUITE, fam, len(listed[fam])))
    allruns = [r for fam in g.FAMILIES for r in listed[fam]]
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        loaded = dict(ex.map(load_run, allruns))

    runs_out, inc = {}, {}
    empty_by_lang = {}
    fam_stats = {fam: {"runs_listed": len(listed[fam]), "runs_empty": 0, "runs_nonempty": 0, "runs_included": 0,
                       "kept": 0, "credits": 0, "letter": 0, "article_gold": 0, "beyond_four": 0,
                       "article_gold_nonempty_uncredited": 0,
                       "classes": {c: 0 for c in g.CLASSES}} for fam in g.FAMILIES}
    for run in allruns:
        r = loaded[run]
        fs = fam_stats[r["family"]]
        if "error" in r:
            runs_out[run] = {"status": "download_failed", "error": r["error"]}
            fs["runs_nonempty"] += 1
            continue
        if r.get("empty"):
            runs_out[run] = {"status": "empty", "model": r["model"], "language": r["language"]}
            fs["runs_empty"] += 1
            key = "%s/%s" % (r["family"], r["language"])
            empty_by_lang[key] = empty_by_lang.get(key, 0) + 1
            continue
        fs["runs_nonempty"] += 1
        s = r["summary"]
        c = s["counts"]
        reasons = []
        if c["stored_missing"] or c["mismatch"]:
            reasons.append("stored")
        nis = r["num_instances_sum"]
        if nis is None or c["kept"] != int(round(nis)) or c["kept"] != r["n_instances_main"]:
            reasons.append("instances")
        mean = Fraction(c["credit"], c["kept"]) if c["kept"] else None
        sm = r["stat_mean"]
        if sm is None or mean is None or abs(float(mean) - sm) > TOL_RUN:
            reasons.append("mean")
        runs_out[run] = {"status": "included" if not reasons else "excluded", "reasons": reasons,
                         "family": r["family"], "model": r["model"], "language": r["language"],
                         "counts": c, "classes": s["classes"]}
        if s["cyr"]["n"]:
            runs_out[run]["cyr"] = s["cyr"]
        if reasons:
            continue
        inc[run] = r
        fs["runs_included"] += 1
        fs["kept"] += c["kept"]
        fs["credits"] += c["credit"]
        fs["letter"] += c["letter"]
        fs["article_gold"] += c["article_gold"]
        fs["beyond_four"] += c["beyond_four"]
        fs["article_gold_nonempty_uncredited"] += c["article_gold_nonempty_uncredited"]
        for k in g.CLASSES:
            fs["classes"][k] += s["classes"][k]
    for run in allruns:
        if runs_out[run]["status"] in ("excluded", "download_failed"):
            print("[excluded] %s %s" % (run, runs_out[run].get("reasons") or runs_out[run].get("error")))
    for fam in g.FAMILIES:
        print("[family] %s %s" % (fam, json.dumps(fam_stats[fam], sort_keys=True)))
    print("[check C1] records with a gold normalising to '' and a non-empty answer stored as 0: %d" % sum(
        fam_stats[fam]["article_gold_nonempty_uncredited"] for fam in g.FAMILIES))
    print("[check C2] runs with no main-split instances, by family/language: %s" % json.dumps(empty_by_lang,
                                                                                             sort_keys=True))

    # EXAMS-V Cyrillic golds, by language.
    cyr_lang = {}
    for run, r in inc.items():
        if r["family"] != "exams_v":
            continue
        cy = r["summary"]["cyr"]
        if cy["n"] == 0:
            continue
        d = cyr_lang.setdefault(r["language"], g.new_cyr())
        for k in d:
            d[k] += cy[k]
    print("[check C3] Cyrillic-gold records by language: %s" % json.dumps(cyr_lang, sort_keys=True))
    bg = cyr_lang.get("Bulgarian", g.new_cyr())

    # Per family, per model: mean of run means (published vs letter grade).
    taus, drops, fam_models = [], set(), {}
    for fam in g.FAMILIES:
        per = {}
        for run, r in inc.items():
            if r["family"] != fam:
                continue
            c = r["summary"]["counts"]
            per.setdefault(r["model"], []).append((Fraction(c["credit"], c["kept"]), Fraction(c["letter"], c["kept"])))
        if not per:
            fam_models[fam] = {"models": 0}
            continue
        full = max(len(v) for v in per.values())
        complete = sorted(m for m, v in per.items() if len(v) == full)
        pub = {m: sum(x[0] for x in per[m]) / len(per[m]) for m in complete}
        let = {m: sum(x[1] for x in per[m]) / len(per[m]) for m in complete}
        rp, rl = g.ranks_high(pub), g.ranks_high(let)
        tau = g.kendall_tau_b([pub[m] for m in complete], [let[m] for m in complete]) if len(complete) > 1 else None
        taus.append(tau)
        movers = sorted(m for m in complete if abs(rp[m] - rl[m]) >= PLACES)
        table = []
        for m in sorted(complete, key=lambda x: (-pub[x], x)):
            drop = pub[m] - let[m]
            if drop >= DROP:
                drops.add(m)
            row = {"model": m, "runs": len(per[m]), "published": f(pub[m]), "letter_grade": f(let[m]),
                   "drop": f(drop), "rank_published": rp[m], "rank_letter": rl[m]}
            table.append(row)
            print("[model %s] %s" % (fam, json.dumps(row, sort_keys=True)))
        leader_p = min(complete, key=lambda x: (rp[x], x))
        leader_l = min(complete, key=lambda x: (rl[x], x))
        fam_models[fam] = {"models": len(complete), "runs_per_model": full, "tau_b": tau, "movers_3plus": movers,
                           "leader_published": leader_p, "leader_letter": leader_l,
                           "max_drop": f(max(pub[m] - let[m] for m in complete)), "table": table}
        print("[models %s] complete=%d tau_b=%s movers=%d max_drop=%s leader %s -> %s" % (
            fam, len(complete), tau, len(movers), fam_models[fam]["max_drop"], leader_p, leader_l))

    credits = sum(fam_stats[fam]["credits"] for fam in g.FAMILIES)
    st = {"families": fam_stats, "credits": credits,
          "free_article_gold": sum(fam_stats[fam]["classes"]["free_article_gold"] for fam in g.FAMILIES),
          "prefix_word": sum(fam_stats[fam]["classes"]["prefix_word"] for fam in g.FAMILIES),
          "models_drop_005": len(drops), "taus": taus,
          "bg_latin_letter": bg["latin_letter"], "bg_cyr_letter": bg["cyr_letter"], "bg_pos_right": bg["pos_right"]}
    print("[pooled] credits=%d free_article_gold=%d prefix_word=%d models_drop_005=%d" % (
        credits, st["free_article_gold"], st["prefix_word"], len(drops)))
    verdicts = g.verdicts(st)
    for k, v in sorted(verdicts.items()):
        print("[verdict] %s = %s" % (k, g.verdict_word(v)))

    # Hand-read material (job log only): up to 8 examples per class, one per run.
    for key in ("free_article_gold", "prefix_word", "letter_only"):
        shown = 0
        for run in sorted(inc, key=lambda x: (g.stable_hash(x + key), x)):
            ex = inc[run]["summary"]["examples"][key]
            if not ex or shown >= 8:
                continue
            shown += 1
            print("[read %s %d] run=%s id=%s gold=%r pred=%r" % (key, shown, run, ex[0][0], ex[0][1], ex[0][2]))

    out = {
        "audit": 120,
        "slug": "vhelm-letter-article-gold",
        "dataset": ("Per-instance outputs of HELM's VHELM run suite %s (Stanford CRFM): every exams_v, mm_star and "
                    "blink run in the public bucket. EXAMS-V by Das et al. (arXiv 2403.10378), MM-Star by Chen et "
                    "al. (arXiv 2403.20330), BLINK by Fu et al. (arXiv 2404.12390). Only run names, instance ids, "
                    "classes, counts and public model names are published." % SUITE),
        "families": fam_stats,
        "empty_runs_by_language": empty_by_lang,
        "cyrillic_by_language": cyr_lang,
        "pooled_credits": credits,
        "pooled_free_article_gold": st["free_article_gold"],
        "pooled_prefix_word": st["prefix_word"],
        "models_drop_005": sorted(drops),
        "models": fam_models,
        "verdicts": {k: g.verdict_word(v) for k, v in verdicts.items()},
        "runs": runs_out,
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"), ensure_ascii=True)  # compact: publish lane limit is 2 MB
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
