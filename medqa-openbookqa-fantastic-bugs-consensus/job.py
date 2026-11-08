"""Answer-level consensus inside one reviewed sample: MedQA and OpenBookQA (audit 89)

Reads the expert-reviewed MedQA (49) and OpenBookQA (50) rows that Fantastic Bugs (Truong et al., arXiv 2511.16842;
stair-lab/fantastic-bugs, MIT) published, builds each benchmark's question universe and every model's answers from
HELM Lite release v1.13.0 (Stanford CRFM), applies audit 77's consensus flag (at least 6 of the 10 most accurate
included models pick the same non-key option, more than pick the key), places each reviewed row in the universe by
question and options, and compares the flag on items the reviewers judged valid and invalid inside one benchmark.

Gates: the hand-traced fixtures must match before any download; at least 20 rows per split must be placed or the
job aborts (P1 needs 45 and 50 included models per benchmark). Writes results.json and rows.json (split names, row
numbers, HELM ids and positions, letters, our categories, votes and counts only; no question, option, review or model
text). Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import hashlib
import io
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import pyarrow.parquet as pq

import base89 as qm
import cases89 as C
import fb89 as fb

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"


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


def run_url(base, suite, run, fname):
    return "%s/runs/%s/%s/%s" % (base, suite, urllib.parse.quote(run, safe=":,=@-_."), fname)


def read_parquet(dataset, config, split, cols):
    """All shards of one dataset split -> (rows as tuples in shard order, shard records)."""
    rows, shards = [], []
    listing = _json(PARQUET_API % dataset)["parquet_files"]
    files = sorted(f["url"] for f in listing if f["config"] == config and f["split"] == split)
    for url in files:
        raw = _get(url)
        shards.append({"split": split, "url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        t = pq.read_table(io.BytesIO(raw))
        data = {c: (t.column(c).to_pylist() if c in t.column_names else [None] * t.num_rows) for c in cols}
        for i in range(t.num_rows):
            rows.append(tuple(data[c][i] for c in cols))
    return rows, shards


def fixture_ok():
    inst = qm.parse_instances(C.FIX_INSTANCES)
    qids, info, _c = qm.build_universe({"med_qa": inst})
    mapped, _mc = qm.map_predictions(C.FIX_PREDS, inst, "med_qa", qids)
    return {
        "categories": all(fb.fb_category(s, r) == w for s, r, w in C.FIX_CAT),
        "suggested": all(fb.suggested_option(r, o) == w for r, o, w in C.FIX_SUGGEST),
        "answer_keys": all(qm.parse_answer_key(s) == w for s, w in C.FIX_AK),
        "place": qm.place(C.FIX_PLACE_ROWS, C.FIX_QIDS) == (C.FIX_PLACE, C.FIX_PLACE_COUNTS),
        "universe": info == C.FIX_UNIVERSE_INFO,
        "mapping": mapped == C.FIX_MAPPED,
        "verdicts": all(fb.predictions89(*a, C.THRESHOLDS) == w for a, w in C.FIX_V_CASES),
    }


def pr(t):
    return [t[0], t[1], float(Fraction(t[0], t[1])) if t[1] else None]


def tally(units, field):
    out = {}
    for u in units:
        out[str(u[field])] = out.get(str(u[field]), 0) + 1
    return dict(sorted(out.items()))


def crosstab(units, a, b):
    out = {}
    for u in units:
        k = "%s|%s" % (u[a], u[b])
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


# ----- One HELM Lite benchmark -----

def build_bench(bench, run_suites):
    runs, dropped = qm.select_gsm_runs(run_suites, C.BENCHES[bench]["prefix"])
    models = sorted(runs)
    inst_src = {}
    for m in models:
        run, suite = runs[m]
        inst_src.setdefault(suite, run)

    def fetch_inst(suite):
        try:
            return suite, qm.parse_instances(_json(run_url(C.HELM_LITE_BASE, suite, inst_src[suite],
                                                           "instances.json"))), None
        except Exception as e:  # noqa: BLE001 - recorded, never patched
            return suite, None, str(e)[:200]

    instances, inst_fail = {}, []
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        for suite, parsed, err in ex.map(fetch_inst, sorted(inst_src)):
            if parsed is None:
                inst_fail.append({"suite": suite, "error": err})
            else:
                instances[suite] = parsed
    if not instances:
        raise SystemExit("%s: no instances.json could be read -- aborting" % bench)
    base_suite = sorted(instances, key=qm.suite_version)[0]
    qids, info, ucounts = qm.build_universe({bench: instances[base_suite]})
    n_q = len(info)
    gold_of = [r[3] for r in info]
    print("[%s] runs=%d dropped=%d suites=%s base=%s universe=%d %s inst_fail=%d"
          % (bench, len(runs), dropped, sorted(instances), base_suite, n_q, ucounts, len(inst_fail)))

    def fetch_pred(m):
        run, suite = runs[m]
        inst = instances.get(suite)
        if inst is None:
            return m, None, {"error": "no instances for suite"}
        try:
            data = _json(run_url(C.HELM_LITE_BASE, suite, run, "display_predictions.json"))
        except Exception as e:  # noqa: BLE001
            return m, None, {"error": str(e)[:200]}
        out, c = qm.map_predictions(data, inst, bench, qids)
        return m, out, c

    preds, stats = {}, {}
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        for m, out, c in ex.map(fetch_pred, models):
            stats[m] = c
            if out is not None:
                preds[m] = out

    acc, excluded = {}, {}
    for m in models:
        c = stats[m]
        if "error" in c:
            excluded[m] = "error"
            continue
        covered = len(preds[m])
        correct = sum(1 for q, i in preds[m].items() if i is not None and i == gold_of[q])
        mapped_items = c["valid"] + c["from_mapped"] + c["invalid"]
        checked = c["consistent"] + c["inconsistent"]
        cons = Fraction(c["consistent"], checked) if checked else Fraction(1)
        em_gap = abs(Fraction(correct - c["em_correct"], mapped_items)) if mapped_items else Fraction(1)
        if not (n_q and Fraction(covered, n_q) >= C.MIN_COVERAGE):
            excluded[m] = "coverage"
        elif cons < C.MIN_CONSISTENT:
            excluded[m] = "consistency"
        elif em_gap > C.MAX_EM_GAP:
            excluded[m] = "exact_match_gap"
        else:
            acc[m] = (correct, covered)
    panel = qm.select_panel(acc, C.PANEL_SIZE)
    questions = {q: (info[q][2], info[q][3]) for q in range(n_q)}
    flags, tallies = qm.panel_flags(panel, preds, questions, C.MIN_AGREE)
    key_counts, nokey = qm.key_pickers(preds, sorted(acc), questions)
    n_flag = sum(1 for q in range(n_q) if flags[q][0])
    n_unan = sum(1 for q in range(n_q) if flags[q][0] and tallies[q][0][flags[q][1]] == C.PANEL_SIZE)
    print("[%s] included=%d of %d excluded=%s panel_acc=%s flagged=%d unanimous=%d no_key=%d"
          % (bench, len(acc), len(models), tally([{"r": r} for r in excluded.values()], "r"),
             [round(float(qm.accuracy(*acc[m])), 3) for m in panel], n_flag, n_unan, len(nokey)))
    return {"qids": qids, "info": info, "n_q": n_q, "flags": flags, "tallies": tallies, "key_counts": key_counts,
            "nokey": nokey, "panel": panel, "acc": acc,
            "summary": {"runs": len(runs), "runs_dropped_as_duplicates": dropped, "suites": sorted(instances),
                        "base_suite": base_suite, "instances_failed": inst_fail, "universe": n_q,
                        "universe_counts": ucounts, "models": len(models), "included": len(acc),
                        "excluded": dict(sorted(excluded.items())), "panel": panel,
                        "panel_accuracy": [float(qm.accuracy(*acc[m])) for m in panel],
                        "flagged_in_universe": pr((n_flag, n_q)), "unanimous_flags_in_universe": n_unan,
                        "no_key_in_universe": len(nokey)}}


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

    # ----- Fantastic Bugs rows -----
    fb_rows, fb_shards, fb_counts = {}, [], {}
    for bench in C.BENCHES:
        split = C.BENCHES[bench]["fb_split"]
        rows, shards = read_parquet(C.FB_DATASET, C.FB_CONFIG, split, C.FB_COLS)
        fb_shards += shards
        fb_counts[split] = len(rows)
        recs = []
        for i, (q, ak, rv) in enumerate(rows):
            opts, key = qm.parse_answer_key(ak)
            recs.append({"row": i, "question": q, "options": opts, "fb_key": key,
                         "category": fb.fb_category(split, rv), "suggested": fb.suggested_option(rv, opts)})
        fb_rows[bench] = recs
    fb_counts_ok = fb_counts == C.FB_EXPECTED_ROWS
    print("[fantastic bugs] rows=%s expected=%s categories=%s"
          % (fb_counts, fb_counts_ok, {b: tally(r, "category") for b, r in fb_rows.items()}))

    # ----- HELM Lite -----
    raw_release = _get("%s/releases/%s/runs_to_run_suites.json" % (C.HELM_LITE_BASE, C.HELM_LITE_RELEASE))
    run_suites = json.loads(raw_release.decode("utf-8"))
    B = {bench: build_bench(bench, run_suites) for bench in C.BENCHES}

    # ----- Place the rows and read the three signals -----
    units, kept, placement = {}, {}, {}
    for bench in C.BENCHES:
        H = B[bench]
        recs = fb_rows[bench]
        pl, pcounts = qm.place([(r["question"], r["options"] or []) for r in recs], H["qids"])
        us = []
        for r, (q, how) in zip(recs, pl):
            u = {"fb_split": C.BENCHES[bench]["fb_split"], "fb_row": r["row"], "fb_category": r["category"],
                 "placed_by": how, "qid": q,
                 "fb_suggested": None if r["suggested"] is None else qm.LETTERS[r["suggested"]]}
            if q is not None:
                _b, iid, k, gold, pos = H["info"][q]
                counts, none = H["tallies"][q]
                flagged, ci = H["flags"][q]
                cov, pick = H["key_counts"][q]
                u.update({"helm_instance_id": iid, "helm_test_position": pos, "helm_key": qm.LETTERS[gold],
                          "fb_key": None if r["fb_key"] is None else qm.LETTERS[r["fb_key"]],
                          "fb_key_equals_helm": r["fb_key"] == gold, "s1_flag": bool(flagged),
                          "consensus_letter": None if ci is None else qm.LETTERS[ci], "top10_votes": list(counts),
                          "top10_no_answer": none, "margin": qm.margin(counts, gold), "no_key": q in H["nokey"],
                          "unanimous": bool(flagged) and counts[ci] == C.PANEL_SIZE,
                          "n_models": cov, "n_models_picking_key": pick})
            us.append(u)
        k_units, twice = qm.first_per_qid(us)
        key_eq = sum(1 for u in k_units if u["fb_key_equals_helm"])
        units[bench], kept[bench] = us, k_units
        placement[bench] = {"methods": pcounts, "placed_rows": len(k_units) + twice,
                            "distinct_questions": len(k_units), "placed_twice": twice, "fb_key_equals_helm": key_eq}
        print("[placement %s] %s" % (bench, placement[bench]))
    if any(placement[b]["placed_rows"] < C.FB_ABORT_PLACED for b in C.BENCHES):
        with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
            json.dump({"audit": 89, "aborted": True, "fixture": fx, "fb_counts": fb_counts, "placement": placement,
                       "helm": {b: B[b]["summary"] for b in B}}, fh, indent=1, ensure_ascii=True)
        raise SystemExit("too few Fantastic Bugs rows placed -- aborting (diagnostics in results.json)")

    def is_cat(c):
        return lambda u: u["fb_category"] == c

    flag = lambda u: u["s1_flag"]  # noqa: E731
    med, obqa = kept["med_qa"], kept["openbookqa"]
    flag_inv = qm.count(med, is_cat("invalid"), flag)
    flag_val = qm.count(med, is_cat("valid"), flag)
    m_inv = [u["margin"] for u in med if u["fb_category"] == "invalid"]
    m_val = [u["margin"] for u in med if u["fb_category"] == "valid"]
    auc_med = (qm.auc(m_inv, m_val), len(m_inv), len(m_val))
    flag_obqa_val = qm.count(obqa, is_cat("valid"), flag)

    verdicts = fb.predictions89(flag_inv, flag_val, auc_med, flag_obqa_val, C.THRESHOLDS)
    p1_parts = {"fixtures": all(fx.values()), "fb_row_counts": fb_counts_ok}
    for b in C.BENCHES:
        p = placement[b]
        p1_parts["included_at_least_%d_%s" % (C.MIN_INCLUDED, b)] = B[b]["summary"]["included"] >= C.MIN_INCLUDED
        p1_parts["placed_at_least_%d_%s" % (C.FB_MIN_PLACED[b], b)] = p["placed_rows"] >= C.FB_MIN_PLACED[b]
        p1_parts["fb_key_equals_helm_95pct_%s" % b] = (bool(p["distinct_questions"]) and
                                                       Fraction(p["fb_key_equals_helm"], p["distinct_questions"])
                                                       >= C.MIN_FB_KEY_AGREE)
    verdicts["P1_structural"] = all(p1_parts.values())
    print("[P1] %s" % p1_parts)
    for name in sorted(k for k, v in verdicts.items() if isinstance(v, bool)):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    numbers = {"P2_P6_medqa_flag_invalid": pr(flag_inv), "P2_P4_medqa_flag_valid": pr(flag_val),
               "P3_medqa_margin_auc": [None if auc_med[0] is None else float(auc_med[0]), auc_med[1], auc_med[2]],
               "P5_openbookqa_flag_valid": pr(flag_obqa_val), "undecidable": verdicts["undecidable"]}
    print("[numbers] %s" % numbers)

    # ----- Exploratory -----
    exploratory = {}
    for b, ku in (("med_qa", med), ("openbookqa", obqa)):
        exploratory[b] = {
            "categories": tally(ku, "fb_category"),
            "category_x_s1_flag": crosstab(ku, "fb_category", "s1_flag"),
            "category_x_unanimous": crosstab(ku, "fb_category", "unanimous"),
            "category_x_no_key": crosstab(ku, "fb_category", "no_key"),
            "margin_auc_invalid_vs_valid": (lambda a: None if a is None else float(a))(
                qm.auc([u["margin"] for u in ku if u["fb_category"] == "invalid"],
                       [u["margin"] for u in ku if u["fb_category"] == "valid"])),
            "mean_top10_key_votes": {c: (lambda xs: None if not xs else float(Fraction(sum(xs), len(xs))))(
                [u["top10_votes"][qm.LETTERS.index(u["helm_key"])] for u in ku if u["fb_category"] == c])
                for c in fb.CATEGORIES},
            "flagged_invalid_with_suggestion": sum(1 for u in ku if u["s1_flag"] and u["fb_suggested"]),
            "consensus_equals_suggested": sum(1 for u in ku if u["s1_flag"] and u["fb_suggested"]
                                              and u["consensus_letter"] == u["fb_suggested"]),
        }
    print("[exploratory] %s" % json.dumps(exploratory, sort_keys=True))

    out = {
        "audit": 89,
        "slug": "medqa-openbookqa-fantastic-bugs-consensus",
        "dataset": ("Fantastic Bugs (stair-lab/fantastic-bugs, MIT; viewer splits med_qa and openbookqa only) via the "
                    "HF datasets-server parquet API, and HELM Lite release %s (Stanford CRFM) per-question outputs for "
                    "med_qa and openbookqa. Only split names, row numbers, ids, positions, letters, categories, votes "
                    "and counts." % C.HELM_LITE_RELEASE),
        "fixture": fx,
        "fb_shards": fb_shards,
        "fb_counts": fb_counts,
        "helm_release_sha256": hashlib.sha256(raw_release).hexdigest(),
        "helm": {b: B[b]["summary"] for b in B},
        "placement": placement,
        "p1_parts": p1_parts,
        "predictions": verdicts,
        "prediction_numbers": numbers,
        "exploratory": exploratory,
        "note": ("Fantastic Bugs categories (fb89.fb_category): MedQA first word valid / invalid; OpenBookQA first "
                 "word correct -> valid, incorrect -> invalid; anything else unclear (left out). Units = distinct "
                 "HELM questions. Flag = audit 77's rule on each benchmark's 10 most accurate included HELM Lite "
                 "models. P2 MedQA flag rate invalid > valid; P3 MedQA margin AUC invalid vs valid >= 3/5; P4 MedQA "
                 "flag rate on valid <= 1/4 (>= 10 rows); P5 OpenBookQA flag rate on valid <= 1/4 (>= 10 rows); P6 "
                 "MedQA flag rate on invalid >= 1/3. Groups under 5 rows (10 for P4, P5) are undecidable."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    rows_out = {b: [{k: v for k, v in u.items() if k != "qid"} for u in units[b]] for b in units}
    with open(os.path.join(args.out_dir, "rows.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 89,
                   "note": ("One row per published Fantastic Bugs row (split, 0-based row number in the HF viewer "
                            "split). fb_category is our reading of their review (fb89.fb_category), not their text; "
                            "fb_suggested is the option an OpenBookQA 'incorrect' review names, when it names one. A "
                            "flag is not a verdict."),
                   "panels": {b: B[b]["panel"] for b in B}, "rows": rows_out}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and rows.json")


if __name__ == "__main__":
    main()
