# SPDX-License-Identifier: Apache-2.0
"""Audit 121: HELM's option-text scoring (issue #4358) on VHELM's published multiple-choice scores.

Lists every a_okvqa, mmmu (multiple-choice) and seed_bench run of VHELM's run suite v2.1.2 in HELM's public bucket
(crfm-helm-public), reads instances.json, display_predictions.json and stats.json, re-grades every first-trial record
with H (letter -> option text -> quasi_prefix_exact_match, transcribed) and I (option identity), and keeps a run only
if our H reproduces every quasi_prefix_exact_match mean in stats.json that applies (original records; each perturbed
variant; and the per-instance worst case that VHELM's leaderboard shows for augmented runs) and our letter -> option
text equals HELM's stored mapped_output on at least 99% of records. Then: the question census (gold normalising to
'', identical, quasi_only and prefix_only collisions) per variant, published over-credits, per-group model means and
ranks under H and I, unmapped outputs, and the eight pre-registered verdicts. Only run names, instance ids, letters,
classes, counts and public model names go to results.json; colliding option texts go to the job log only.
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

import grade121 as g

BUCKET = "crfm-helm-public"
SUITE = "v2.1.2"
RUNS_PREFIX = "vhelm/benchmark_output/runs/%s/" % SUITE
UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
WORKERS = 6
TOL = 1e-9
MIN_RUN_MAP = Fraction(99, 100)
# family -> (main split, required substring in the run name or None)
FAMILIES = {"a_okvqa": ("valid", None), "mmmu": ("valid", "question_type=multiple-choice"),
            "seed_bench": ("test", None)}
TRANSLATED_GROUPS = ("a_okvqa_chinese", "a_okvqa_hindi", "a_okvqa_spanish", "a_okvqa_swahili")
MAX_PUBLISHED_QUESTIONS = 2000
PRINT_PER_CLASS = 25


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


def load_run(item):
    run, family = item
    split = FAMILIES[family][0]
    rec = {"run": run, "family": family, "group": g.group_of(run, family), "model": g.run_field(run, "model"),
           "subject": g.run_field(run, "subject") or "-"}
    try:
        inst = _json(run_url(run, "instances.json"))
        preds = _json(run_url(run, "display_predictions.json"))
        stats = _json(run_url(run, "stats.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return rec
    imap = g.instance_map(inst, split)
    rec["n_instances"] = len(imap)
    s = g.summarize_run(preds, imap)
    rec["summary"] = s
    perts = [v["pert"] for v in imap.values() if v["pert"]]
    wn = g.worst_name(perts)
    checks = {"orig": (g.stat_mean(stats, split), s["subsets"].get("", g.new_sub()))}
    for var, sub in s["subsets"].items():
        if var == "":
            continue
        name = var.split(":", 1)[0]
        checks["pert:" + var] = (g.stat_mean(stats, split, name, "perturbed"), sub)
    if wn is not None:
        checks["worst:" + wn] = (g.stat_mean(stats, split, wn, "worst"), s["worst"])
    reasons, means = [], {}
    for k, (stored, sub) in checks.items():
        ours = Fraction(sub["h"], sub["n"]) if sub and sub["n"] else None
        means[k] = [None if ours is None else float(ours), stored]
        if stored is None or ours is None or abs(float(ours) - stored) > TOL:
            reasons.append("mean " + k)
    c = s["counts"]
    if c["scored"] == 0 or c["no_gold"] or c["duplicate"] or c["no_instance"]:
        reasons.append("records")
    if c["map_checked"] == 0 or Fraction(c["map_agree"], c["map_checked"]) < MIN_RUN_MAP:
        reasons.append("mapped_output")
    rec["worst_name"] = wn
    rec["means"] = means
    rec["reasons"] = reasons
    return rec


def f(x):
    return None if x is None else float(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    items = []
    listed = {}
    for fam, (_split, must) in FAMILIES.items():
        runs = [r for r in list_runs(fam) if must is None or must in r]
        listed[fam] = len(runs)
        items.extend((r, fam) for r in runs)
        print("[suite] %s %s runs listed=%d" % (SUITE, fam, len(runs)))

    runs_out, inc = {}, {}
    census = {}            # (family, subject, variant, qhash) -> question info
    variant_groups = {}    # (family, variant) -> set of groups whose runs carry it
    fam_inc = {fam: 0 for fam in FAMILIES}
    examples = []
    map_agree = map_checked = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for rec in ex.map(load_run, items):
            run = rec["run"]
            if "error" in rec:
                runs_out[run] = {"status": "download_failed", "error": rec["error"]}
                print("[excluded] %s download_failed %s" % (run, rec["error"][:120]))
                continue
            s = rec.pop("summary")
            c = s["counts"]
            status = "included" if not rec["reasons"] else "excluded"
            runs_out[run] = {"s": status, "m": rec["means"]}
            if status != "included":
                runs_out[run].update({"reasons": rec["reasons"], "counts": c})
                print("[excluded] %s %s %s %s" % (run, rec["reasons"], json.dumps(rec["means"]), json.dumps(c)))
                continue
            fam_inc[rec["family"]] += 1
            map_agree += c["map_agree"]
            map_checked += c["map_checked"]
            pub = g.published(s)
            inc[run] = {"family": rec["family"], "group": rec["group"], "model": rec["model"],
                        "subject": rec["subject"], "pub": {"n": pub["n"], "h": pub["h"], "i": pub["i"],
                                                           "under": pub["under"], "over": dict(pub["over"])},
                        "orig": s["subsets"].get("", g.new_sub()), "flips": s["flips"]}
            for (var, qh), q in s["questions"].items():
                label = var if var == "" else "%s@%s" % (var, rec["group"])
                census.setdefault((rec["family"], rec["subject"], label, qh), q)
                variant_groups.setdefault((rec["family"], label), set()).add(rec["group"])
            for e in s["examples"]:
                if len(examples) < 40:
                    examples.append((run,) + e)

    for fam in FAMILIES:
        print("[included] %s %d of %d" % (fam, fam_inc[fam], listed[fam]))
    print("[mapped_output] agreement %d / %d" % (map_agree, map_checked))

    # ----- Question census by (family, variant) -----
    cen = {}
    for (fam, subj, var, qh), q in census.items():
        d = cen.setdefault("%s|%s" % (fam, var), {"questions": 0, "gold_empty": 0, "identical": 0, "quasi_only": 0,
                                                  "prefix_only": 0, "any": 0})
        d["questions"] += 1
        d["gold_empty"] += 1 if q["col"]["gold_empty"] else 0
        for k in ("identical", "quasi_only", "prefix_only"):
            d[k] += 1 if q["col"][k] else 0
        d["any"] += 1 if (q["col"]["identical"] or q["col"]["quasi_only"] or q["col"]["prefix_only"]) else 0
    for k in sorted(cen):
        groups = sorted(variant_groups.get(tuple(k.split("|", 1)), []))
        print("[census] %s %s groups=%s" % (k, json.dumps(cen[k], sort_keys=True), groups))

    def variants_for(groups):
        return sorted({var for (fam, var), gs in variant_groups.items()
                       if fam == "a_okvqa" and var != "" and any(x in gs for x in groups)})

    tr_vars = variants_for(TRANSLATED_GROUPS)
    zh_vars, es_vars = variants_for(("a_okvqa_chinese",)), variants_for(("a_okvqa_spanish",))
    print("[variants] translated=%s chinese=%s spanish=%s" % (tr_vars, zh_vars, es_vars))

    def csum(vars_, key):
        return sum(cen.get("a_okvqa|%s" % v, {}).get(key, 0) for v in vars_)

    # ----- Published over-credits, by group -----
    groups = {}
    for run, r in inc.items():
        d = groups.setdefault(r["group"], {"runs": 0, "n": 0, "credits": 0, "identity": 0, "under": 0,
                                           "over": {k: 0 for k in g.OVER_CLASSES}, "unmapped_orig": 0, "n_orig": 0})
        d["runs"] += 1
        d["n"] += r["pub"]["n"]
        d["credits"] += r["pub"]["h"]
        d["identity"] += r["pub"]["i"]
        d["under"] += r["pub"]["under"]
        for k in g.OVER_CLASSES:
            d["over"][k] += r["pub"]["over"][k]
        d["unmapped_orig"] += r["orig"]["unmapped"]
        d["n_orig"] += r["orig"]["n"]
    for k in sorted(groups):
        print("[group] %s %s" % (k, json.dumps(groups[k], sort_keys=True)))
    pub_credits = sum(d["credits"] for d in groups.values())
    pub_over = sum(sum(d["over"].values()) for d in groups.values())
    print("[pooled] published credits=%d over-credits=%d (%s)" % (
        pub_credits, pub_over, None if not pub_credits else float(Fraction(pub_over, pub_credits))))

    # ----- Per group: model means (mean of run means), ranks under H and I -----
    models, movers_total = {}, 0
    for grp in sorted(groups):
        per = {}
        for run, r in inc.items():
            if r["group"] != grp or r["pub"]["n"] == 0:
                continue
            per.setdefault(r["model"], []).append((Fraction(r["pub"]["h"], r["pub"]["n"]),
                                                   Fraction(r["pub"]["i"], r["pub"]["n"])))
        if not per:
            continue
        full = max(len(v) for v in per.values())
        complete = sorted(m for m, v in per.items() if len(v) == full)
        acc_h = {m: sum(x[0] for x in per[m]) / len(per[m]) for m in complete}
        acc_i = {m: sum(x[1] for x in per[m]) / len(per[m]) for m in complete}
        rh, ri = g.min_ranks(acc_h), g.min_ranks(acc_i)
        movers = sorted(m for m in complete if abs(rh[m] - ri[m]) >= g.THRESHOLDS["P6_places"])
        movers_total += len(movers)
        tau = g.kendall_tau_b([acc_h[m] for m in complete], [acc_i[m] for m in complete]) if len(complete) > 1 else None
        lead_h = min(complete, key=lambda m: (rh[m], m))
        lead_i = min(complete, key=lambda m: (ri[m], m))
        table = [{"model": m, "runs": len(per[m]), "published": f(acc_h[m]), "identity": f(acc_i[m]),
                  "diff": f(acc_h[m] - acc_i[m]), "rank_published": rh[m], "rank_identity": ri[m]}
                 for m in sorted(complete, key=lambda x: (rh[x], x))]
        models[grp] = {"models": len(complete), "runs_per_model": full, "tau_b": tau, "movers_3plus": movers,
                       "leader_published": lead_h, "leader_identity": lead_i,
                       "max_diff": f(max(acc_h[m] - acc_i[m] for m in complete)), "table": table}
        print("[models %s] n=%d tau_b=%s movers=%d max_diff=%s leader %s -> %s" % (
            grp, len(complete), tau, len(movers), models[grp]["max_diff"], lead_h, lead_i))

    # ----- Unmapped outputs on A-OKVQA base (original records) -----
    unm = {}
    for run, r in inc.items():
        if r["group"] == "a_okvqa_base" and r["orig"]["n"]:
            unm[r["model"]] = [r["orig"]["unmapped"], r["orig"]["n"]]
    models_unm = sorted(m for m, (u, n) in unm.items() if Fraction(u, n) >= g.THRESHOLDS["P8_share"])
    print("[unmapped a_okvqa_base] models >= 1%%: %d %s" % (len(models_unm), json.dumps(
        {m: unm[m] for m in models_unm}, sort_keys=True)))

    st = {"family_included": {fam: (fam_inc[fam], listed[fam]) for fam in FAMILIES},
          "mmmu_gold_empty": cen.get("mmmu|", {}).get("gold_empty", 0),
          "tr_any": csum(tr_vars, "any"), "tr_q": csum(tr_vars, "questions"),
          "en_any": cen.get("a_okvqa|", {}).get("any", 0), "en_q": cen.get("a_okvqa|", {}).get("questions", 0),
          "tr_identical": csum(tr_vars, "identical"), "pub_over": pub_over, "pub_credits": pub_credits,
          "movers": movers_total, "zh_prefix": csum(zh_vars, "prefix_only"), "es_prefix": csum(es_vars, "prefix_only"),
          "models_unmapped_base": len(models_unm)}
    print("[numbers] %s" % json.dumps({k: (list(v) if isinstance(v, tuple) else v) for k, v in st.items()
                                       if k != "family_included"}, sort_keys=True))
    print("[numbers] family_included %s" % json.dumps({k: list(v) for k, v in st["family_included"].items()}))
    vd = g.verdicts(st)
    for k in sorted(vd):
        print("[verdict] %s = %s" % (k, g.verdict_word(vd[k])))

    # ----- Hand-read material (job log only): colliding questions with their option texts -----
    for cls in ("gold_empty", "identical", "quasi_only", "prefix_only"):
        shown = 0
        for (fam, subj, var, qh), q in sorted(census.items(), key=lambda t: (t[0][0], t[0][2], t[0][1], str(t[1]["iid"]))):
            hit = q["col"]["gold_empty"] if cls == "gold_empty" else bool(q["col"][cls])
            if not hit or shown >= PRINT_PER_CLASS:
                continue
            shown += 1
            print("[read %s %d] %s/%s/%s id=%s gold=%s col=%s texts=%r" % (
                cls, shown, fam, subj, var or "original", q["iid"], q["gold_letter"], json.dumps(q["col"]), q["texts"]))
    for e in examples[:20]:
        print("[read record] run=%s id=%s variant=%s letter=%s gold=%s class=%s" % e)

    coll = [{"family": fam, "subject": subj, "variant": var or "original", "instance_id": q["iid"],
             "gold_letter": q["gold_letter"], "collides": q["col"]}
            for (fam, subj, var, qh), q in sorted(census.items(), key=lambda t: (t[0][0], t[0][2], t[0][1],
                                                                                 str(t[1]["iid"])))
            if q["col"]["gold_empty"] or q["col"]["identical"] or q["col"]["quasi_only"] or q["col"]["prefix_only"]]
    flips = [dict(fl, run=run) for run, r in sorted(inc.items()) for fl in r["flips"]]
    out = {
        "audit": 121,
        "slug": "vhelm-mcq-option-collisions",
        "dataset": ("Per-instance outputs of HELM's VHELM run suite %s (Stanford CRFM): every a_okvqa, mmmu "
                    "(multiple-choice) and seed_bench run in the public bucket. A-OKVQA by Schwenk et al. (arXiv "
                    "2206.01718), MMMU by Yue et al. (arXiv 2311.16502), SEED-Bench by Li et al. (arXiv 2307.16125). "
                    "Only run names, instance ids, letters, classes, counts and public model names are published."
                    % SUITE),
        "runs_listed": listed,
        "runs_included": fam_inc,
        "mapped_output_agreement": [map_agree, map_checked],
        "census": cen,
        "variants": {"translated": tr_vars, "chinese": zh_vars, "spanish": es_vars},
        "groups": groups,
        "pooled": {"published_credits": pub_credits, "published_over": pub_over},
        "models": models,
        "unmapped_a_okvqa_base": unm,
        "numbers": {k: (list(v) if isinstance(v, tuple) else v) for k, v in st.items() if k != "family_included"},
        "verdicts": {k: g.verdict_word(v) for k, v in vd.items()},
        "collision_questions_total": len(coll),
        "collision_questions": coll[:MAX_PUBLISHED_QUESTIONS],
        "published_overcredits_total": len(flips),
        "published_overcredits": flips[:MAX_PUBLISHED_QUESTIONS],
        "runs": runs_out,
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"), ensure_ascii=True)  # compact: publish lane limit is 2 MB
    print("[done] wrote results.json (%d collision questions, %d published over-credits)" % (len(coll), len(flips)))


if __name__ == "__main__":
    main()
