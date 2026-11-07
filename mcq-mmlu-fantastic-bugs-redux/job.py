"""Two expert panels and one model panel on the same MMLU questions (audit 88)

Rebuilds audit 80 (HELM MMLU release v1.13.0, 78 included models, audit 77's consensus flag on the 10 most accurate,
MMLU-Redux 2.0 labels) and checks that it reproduces. Then reads the 189 expert-reviewed MMLU rows and 16 GSM8K rows
that Fantastic Bugs (Truong et al., arXiv 2511.16842; stair-lab/fantastic-bugs, MIT) published, places each MMLU row
in the HELM universe by question and options, and compares three opinions on the same questions: Fantastic Bugs'
review (valid / answer key / other problem), MMLU-Redux 2.0's label, and the top-10 consensus flag. The GSM8K rows are
joined to GSM8K's test set, GSM8K-Platinum's status and audit 86's published candidates.

Gates: the hand-traced fixtures must match before any download; audit 80 must reproduce; the Redux join must place
at least 4,000 rows; at least 100 Fantastic Bugs MMLU rows must be placed (P1 needs 170). Writes results.json and
rows.json (split names, row numbers, HELM ids and positions, letters, our three categories, labels and counts only;
no question, option, review or model text). Usage: python job.py --out-dir /out (network required). Apache-2.0.
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

import base88 as qm
import cases88 as C
import fb88 as fb

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


def read_redux():
    rows, shards = [], []
    listing = _json(PARQUET_API % C.REDUX_DATASET)["parquet_files"]
    files = sorted((f["config"], f["url"]) for f in listing if f["split"] == C.REDUX_SPLIT)
    for config, url in files:
        raw = _get(url)
        shards.append({"config": config, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        t = pq.read_table(io.BytesIO(raw))
        cols = {c: (t.column(c).to_pylist() if c in t.column_names else [None] * t.num_rows)
                for c in ("question", "choices", "answer", "error_type")}
        for q, ch, a, et in zip(cols["question"], cols["choices"], cols["answer"], cols["error_type"]):
            rows.append({"subject": config, "question": q, "choices": list(ch or []),
                         "answer": int(a) if a is not None else None, "label": qm.label_of(et)})
    return rows, shards


def fixture_ok():
    place_out = fb.place(C.FIX_PLACE_ROWS, C.FIX_QIDS)
    return {
        "categories": all(fb.fb_category(s, r) == w for s, r, w in C.FIX_CAT),
        "mojibake": all(fb.demojibake(s) == w for s, w in C.FIX_MOJI),
        "answer_keys": all(fb.parse_answer_key(s) == w for s, w in C.FIX_AK),
        "place": place_out == (C.FIX_PLACE, C.FIX_PLACE_COUNTS),
        "redux_group": all(fb.redux_group(a) == w for a, w in C.FIX_RGROUP),
        "first_per_qid": fb.first_per_qid(C.FIX_UNITS) == C.FIX_UNITS_KEPT,
        "kappa": all(fb.kappa(p) == w for p, w in C.FIX_KAPPA),
        "verdicts": all(fb.predictions88(*a, C.THRESHOLDS) == w for a, w in C.FIX_V_CASES),
    }


# ----- HELM: audit 80, rebuilt (copied from audit 87's job.py) -----

def build_helm():
    release_url = "%s/releases/%s/runs_to_run_suites.json" % (C.HELM_BASE, C.HELM_RELEASE)
    raw_release = _get(release_url)
    run_suites = json.loads(raw_release.decode("utf-8"))
    chosen, dups = qm.select_runs(run_suites)
    models = sorted({m for m, _s in chosen})
    subjects = sorted({s for _m, s in chosen})
    print("[helm runs] entries=%d chosen=%d dups=%d models=%d subjects=%d"
          % (len(run_suites), len(chosen), dups, len(models), len(subjects)))

    inst_src = {}
    for (m, s), (run, suite) in sorted(chosen.items()):
        inst_src.setdefault((suite, s), run)

    def fetch_inst(key):
        suite, s = key
        try:
            return key, qm.parse_instances(_json(run_url(C.HELM_BASE, suite, inst_src[key], "instances.json"))), None
        except Exception as e:  # noqa: BLE001 - recorded, never patched
            return key, None, str(e)[:200]

    instances, inst_fail = {}, []
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        for key, parsed, err in ex.map(fetch_inst, sorted(inst_src)):
            if parsed is None:
                inst_fail.append({"suite": key[0], "subject": key[1], "error": err})
            else:
                instances[key] = parsed
    base_suite = {}
    for suite, s in instances:
        if s not in base_suite or qm.suite_version(suite) < qm.suite_version(base_suite[s]):
            base_suite[s] = suite
    qids, info, ucounts = qm.build_universe({s: instances[(base_suite[s], s)] for s in base_suite})
    n_q = len(info)
    gold_of = [r[3] for r in info]
    print("[helm universe] files=%d failed=%d questions=%d %s" % (len(instances), len(inst_fail), n_q, ucounts))

    def fetch_pred(item):
        (m, s), (run, suite) = item
        inst = instances.get((suite, s))
        if inst is None:
            return m, s, None, {"error": "no instances for suite"}
        try:
            data = _json(run_url(C.HELM_BASE, suite, run, "display_predictions.json"))
        except Exception as e:  # noqa: BLE001
            return m, s, None, {"error": str(e)[:200]}
        out, c = qm.map_predictions(data, inst, s, qids)
        return m, s, out, c

    preds, stats = {m: {} for m in models}, {m: {} for m in models}
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        for m, s, out, c in ex.map(fetch_pred, sorted(chosen.items())):
            stats[m][s] = c
            if out is not None:
                preds[m].update(out)

    acc = {}
    for m in models:
        ss = stats[m]
        tot = {k: sum(v.get(k, 0) for v in ss.values() if "error" not in v)
               for k in ("valid", "from_mapped", "invalid", "consistent", "inconsistent", "em_correct")}
        n_subj = sum(1 for v in ss.values() if "error" not in v)
        covered = len(preds[m])
        correct = sum(1 for q, i in preds[m].items() if i is not None and i == gold_of[q])
        mapped_items = tot["valid"] + tot["from_mapped"] + tot["invalid"]
        checked = tot["consistent"] + tot["inconsistent"]
        cons = Fraction(tot["consistent"], checked) if checked else Fraction(1)
        em_gap = abs(Fraction(correct - tot["em_correct"], mapped_items)) if mapped_items else Fraction(1)
        if (n_subj == C.N_SUBJECTS and n_q and Fraction(covered, n_q) >= C.MIN_COVERAGE
                and cons >= C.MIN_CONSISTENT and em_gap <= C.MAX_EM_GAP):
            acc[m] = (correct, covered)
    print("[helm inclusion] included=%d of %d" % (len(acc), len(models)))
    return {"qids": qids, "info": info, "n_q": n_q, "gold_of": gold_of, "preds": preds, "acc": acc,
            "release_sha256": hashlib.sha256(raw_release).hexdigest(), "inst_fail": inst_fail,
            "universe_counts": ucounts, "n_models": len(models)}


def pr(t):
    return [t[0], t[1], float(Fraction(t[0], t[1])) if t[1] else None]


def tally(units, field):
    out = {}
    for u in units:
        out[u[field]] = out.get(u[field], 0) + 1
    return dict(sorted(out.items()))


def crosstab(units, a, b):
    out = {}
    for u in units:
        k = "%s|%s" % (u[a], u[b])
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


# ----- GSM8K part -----

def gsm_part(fb_gsm):
    gsm_rows, gsm_shards = read_parquet(C.GSM8K["hf"], C.GSM8K["config"], C.GSM8K["split"], C.GSM8K["cols"])
    plat_rows, plat_shards = read_parquet(C.PLATINUM["hf"], C.PLATINUM["config"], C.PLATINUM["split"],
                                          C.PLATINUM["cols"])
    labels, _plat_answer, lcounts = qm.platinum_labels(gsm_rows, plat_rows)
    gsm_index, _dup = qm.text_index([q for q, _a in gsm_rows])
    print("[gsm] rows=%d platinum=%s" % (len(gsm_rows), lcounts))

    raw86 = _get(C.AUDIT86_CANDIDATES)
    cands = json.loads(raw86.decode("utf-8"))["candidates"]
    by_pos = {c["gsm_test_position"]: c for c in cands}
    kept_flags = sorted(c["gsm_test_position"] for c in cands if c.get("s1_flag") and c.get("platinum") in C.KEPT)

    run_suites = _json("%s/releases/%s/runs_to_run_suites.json" % (C.HELM_LITE_BASE, C.HELM_LITE_RELEASE))
    runs, _dropped = qm.select_gsm_runs(run_suites)
    model = sorted(runs)[0]
    run, suite = runs[model]
    inst = _json(run_url(C.HELM_LITE_BASE, suite, run, "instances.json"))
    helm_pos = set()
    for it in inst or []:
        if isinstance(it, dict) and it.get("split") == "test":
            p = gsm_index.get(qm.norm_q((it.get("input") or {}).get("text")))
            if p is not None:
                helm_pos.add(p)
    print("[gsm] audit-86 candidates=%d kept S1 flags=%s helm universe (%s)=%d"
          % (len(cands), kept_flags, model, len(helm_pos)))

    out_rows, placed = [], 0
    for r in fb_gsm:
        q = r["question"] or ""
        p = gsm_index.get(qm.norm_q(q))
        how = "exact"
        if p is None:
            p = gsm_index.get(qm.norm_q(fb.demojibake(qm.norm_q(q))))
            how = "repaired" if p is not None else "none"
        fb_key = qm.get_final_number(r["key_text"] or "")
        row = {"fb_split": "gsm", "fb_row": r["row"], "fb_category": r["category"], "placed_by": how,
               "gsm_test_position": p}
        if p is not None:
            placed += 1
            c = by_pos.get(p)
            row.update({"platinum": labels.get(p), "in_helm_lite_universe": p in helm_pos,
                        "fb_key_equals_gsm8k": fb_key == qm.gsm_final(gsm_rows[p][1]),
                        "s1_flag_audit86": bool(c and c.get("s1_flag")),
                        "s1_top_non_key_votes": c.get("s1_top_non_key_votes") if c else None,
                        "s1_key_votes": c.get("s1_key_votes") if c else None})
        out_rows.append(row)
    fb_pos = {r["gsm_test_position"] for r in out_rows if r["gsm_test_position"] is not None}
    overlap = [p for p in kept_flags if p in fb_pos]
    summary = {"gsm8k_shards": gsm_shards, "platinum_shards": plat_shards, "platinum": lcounts,
               "audit86_candidates_sha256": hashlib.sha256(raw86).hexdigest(), "audit86_candidates": len(cands),
               "audit86_kept_s1_flags": kept_flags, "helm_lite_universe_model": model,
               "helm_lite_universe_size": len(helm_pos), "fb_rows": len(fb_gsm), "fb_placed": placed,
               "fb_platinum": dict(sorted(tally([r for r in out_rows if r["gsm_test_position"] is not None],
                                                "platinum").items())),
               "fb_s1_flagged": sum(1 for r in out_rows if r.get("s1_flag_audit86")),
               "fb_s1_flagged_by_category": crosstab([r for r in out_rows if r["gsm_test_position"] is not None],
                                                     "fb_category", "s1_flag_audit86"),
               "overlap_kept_flags": overlap}
    return out_rows, summary, (len(overlap), len(kept_flags))


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
    fb_rows, fb_shards, fb_counts = [], [], {}
    for split in list(fb.MMLU_SPLITS) + [fb.GSM_SPLIT]:
        rows, shards = read_parquet(C.FB_DATASET, C.FB_CONFIG, split, C.FB_COLS)
        fb_shards += shards
        fb_counts[split] = len(rows)
        for i, (q, ak, rv) in enumerate(rows):
            rec = {"split": split, "row": i, "question": q, "category": fb.fb_category(split, rv)}
            if split == fb.GSM_SPLIT:
                try:
                    lst = json.loads(ak)
                    rec["key_text"] = ((lst[0] if lst else {}).get("output") or {}).get("text")
                except (ValueError, TypeError, AttributeError, IndexError):
                    rec["key_text"] = None
            else:
                rec["options"], rec["fb_key"] = fb.parse_answer_key(ak)
            fb_rows.append(rec)
    fb_counts_ok = fb_counts == C.FB_EXPECTED_ROWS
    print("[fantastic bugs] rows=%s expected=%s" % (fb_counts, fb_counts_ok))
    fb_mmlu = [r for r in fb_rows if r["split"] in fb.MMLU_SPLITS]
    fb_gsm = [r for r in fb_rows if r["split"] == fb.GSM_SPLIT]

    # ----- HELM and Redux; audit 80's gate -----
    H = build_helm()
    qids, info, n_q, gold_of, acc, preds = H["qids"], H["info"], H["n_q"], H["gold_of"], H["acc"], H["preds"]
    h_questions = {q: (info[q][2], info[q][3]) for q in range(n_q)}
    redux, redux_shards = read_redux()
    labels, rcounts, key_agree = qm.redux_join(redux, qids, gold_of)
    print("[redux] rows=%d %s key_agree=%d" % (len(redux), rcounts, key_agree))
    if rcounts["joined"] < C.ABORT_REDUX_JOINED:
        raise SystemExit("Redux join placed only %d rows -- aborting" % rcounts["joined"])
    g = qm.groups(n_q, labels)
    panel = qm.select_panel(acc, C.PANEL_SIZE)
    f1, t1 = qm.panel_flags(panel, preds, h_questions, C.MIN_AGREE)
    flagged80 = {name: qm.n_flagged(g[name], f1) for name in C.EXPECTED_80["flagged"]}
    prec80 = qm.flag_precision(f1, g)
    repro80 = (n_q == C.EXPECTED_80["universe"] and len(acc) == C.EXPECTED_80["included"]
               and panel == C.EXPECTED_80["panel"] and flagged80 == C.EXPECTED_80["flagged"]
               and prec80 == C.EXPECTED_80["precision"])
    key_counts, nokey = qm.key_pickers(preds, sorted(acc), h_questions)
    print("[audit 80] reproduced=%s flagged=%s precision=%s" % (repro80, flagged80, prec80))

    # ----- Place the Fantastic Bugs MMLU rows -----
    placements, pcounts = fb.place([(r["question"], r["options"] or []) for r in fb_mmlu], qids)
    units = []
    for r, (q, how) in zip(fb_mmlu, placements):
        u = {"fb_split": r["split"], "fb_row": r["row"], "fb_category": r["category"], "placed_by": how, "qid": q}
        if q is not None:
            subj, iid, k, gold, pos = info[q]
            counts, none = t1[q]
            flagged, ci = f1[q]
            cov, pick = key_counts[q]
            u.update({"helm_subject": subj, "helm_instance_id": iid, "helm_test_position": pos,
                      "helm_key": qm.LETTERS[gold],
                      "fb_key": None if r["fb_key"] is None else qm.LETTERS[r["fb_key"]],
                      "fb_key_equals_helm": r["fb_key"] == gold, "redux": fb.redux_group(labels.get(q)),
                      "redux_label": labels.get(q), "s1_flag": bool(flagged),
                      "consensus_letter": None if ci is None else qm.LETTERS[ci], "top10_votes": list(counts),
                      "top10_no_answer": none, "margin": qm.margin(counts, gold), "no_key": q in nokey,
                      "n_models": cov, "n_models_picking_key": pick})
        units.append(u)
    kept, twice = fb.first_per_qid(units)
    n_placed = len(kept) + twice
    key_eq = sum(1 for u in kept if u["fb_key_equals_helm"])
    print("[placement] %s placed=%d distinct=%d twice=%d fb_key_equals_helm=%d"
          % (pcounts, n_placed, len(kept), twice, key_eq))
    if n_placed < C.FB_ABORT_PLACED:
        with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
            json.dump({"audit": 88, "aborted": True, "fixture": fx, "fb_counts": fb_counts, "placement": pcounts,
                       "reproduced_80": repro80}, fh, indent=1, ensure_ascii=True)
        raise SystemExit("only %d Fantastic Bugs rows placed -- aborting (diagnostics in results.json)" % n_placed)

    # ----- Prediction inputs -----
    def is_cat(c):
        return lambda u: u["fb_category"] == c

    judged = [u for u in kept if u["redux"] in fb.JUDGED]
    err = lambda u: u["redux"] in ("miskey", "other_error")  # noqa: E731
    mis = lambda u: u["redux"] == "miskey"  # noqa: E731
    flag = lambda u: u["s1_flag"]  # noqa: E731
    key_err = fb.count(judged, is_cat("key"), err)
    key_mis = fb.count(judged, is_cat("key"), mis)
    other_mis = fb.count(judged, is_cat("other"), mis)
    valid_err = fb.count(judged, is_cat("valid"), err)
    flag_key = fb.count(kept, is_cat("key"), flag)
    flag_valid = fb.count(kept, is_cat("valid"), flag)

    gsm_rows_out, gsm_summary, gsm_overlap = gsm_part(fb_gsm)

    verdicts = fb.predictions88(key_err, key_mis, other_mis, valid_err, flag_key, flag_valid, gsm_overlap,
                                C.THRESHOLDS)
    p1_parts = {"fixtures": all(fx.values()), "fb_row_counts": fb_counts_ok, "reproduce_80": repro80,
                "placed_at_least_170": n_placed >= C.FB_MIN_PLACED,
                "fb_key_equals_helm_95pct": bool(kept) and Fraction(key_eq, len(kept)) >= C.MIN_FB_KEY_AGREE}
    verdicts["P1_structural"] = all(p1_parts.values())
    print("[P1] %s" % p1_parts)
    for name in sorted(k for k, v in verdicts.items() if isinstance(v, bool)):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    numbers = {"P2_key_redux_error": pr(key_err), "P3_key_redux_miskey": pr(key_mis),
               "P3_other_redux_miskey": pr(other_mis), "P4_valid_redux_error": pr(valid_err),
               "P5_P6_flag_key": pr(flag_key), "P5_flag_valid": pr(flag_valid), "P7_gsm_overlap": list(gsm_overlap),
               "undecidable": verdicts["undecidable"]}
    print("[numbers] %s" % numbers)

    # ----- Exploratory -----
    pairs = [(u["fb_category"] != "valid", err(u)) for u in judged]
    pairs_both = [(u["fb_category"] != "valid", err(u)) for u in judged if u["fb_split"] in fb.BOTH_KINDS]
    k_all, k_both = fb.kappa(pairs), fb.kappa(pairs_both)
    both = [u for u in kept if u["fb_split"] in fb.BOTH_KINDS]
    a_margin = qm.auc([u["margin"] for u in both if u["fb_category"] != "valid"],
                      [u["margin"] for u in both if u["fb_category"] == "valid"])
    disputes = [u for u in kept if u["fb_category"] == "valid" and u["s1_flag"]]
    other_flag = fb.count(kept, is_cat("other"), flag)
    flag_err_judged = fb.count(judged, flag, err)
    noflag_err_judged = fb.count(judged, lambda u: not u["s1_flag"], err)
    by_split = {}
    for s in fb.MMLU_SPLITS:
        su = [u for u in kept if u["fb_split"] == s]
        by_split[s] = {"placed_distinct": len(su), "categories": tally(su, "fb_category"),
                       "redux": tally(su, "redux"), "category_x_redux": crosstab(su, "fb_category", "redux"),
                       "category_x_s1_flag": crosstab(su, "fb_category", "s1_flag"),
                       "no_key": sum(1 for u in su if u["no_key"])}
    print("[exploratory] kappa_all=%s kappa_both=%s auc_margin_both=%s disputes=%d other_flag=%s"
          % (k_all, k_both, a_margin, len(disputes), other_flag))

    out = {
        "audit": 88,
        "slug": "mcq-mmlu-fantastic-bugs-redux",
        "dataset": ("Fantastic Bugs (stair-lab/fantastic-bugs, MIT; viewer splits only), HELM MMLU release %s and "
                    "HELM Lite release %s (Stanford CRFM), MMLU-Redux 2.0, GSM8K test and GSM8K-Platinum via the HF "
                    "datasets-server parquet API, and audit 86's published candidates.json. Only split names, row "
                    "numbers, ids, positions, letters, categories, labels and counts." % (C.HELM_RELEASE,
                                                                                       C.HELM_LITE_RELEASE)),
        "fixture": fx,
        "fb_shards": fb_shards,
        "fb_counts": fb_counts,
        "helm": {"release_sha256": H["release_sha256"], "universe": n_q, "universe_counts": H["universe_counts"],
                 "instances_failed": H["inst_fail"], "models": H["n_models"], "included": len(acc), "panel": panel,
                 "flagged": flagged80, "precision": list(prec80)},
        "redux": {"rows": len(redux), "join": rcounts, "key_agree": key_agree, "shards": redux_shards,
                  "groups": {k: len(v) for k, v in g.items()}},
        "placement": {"methods": pcounts, "placed_rows": n_placed, "distinct_questions": len(kept),
                      "placed_twice": twice, "fb_key_equals_helm": key_eq},
        "p1_parts": p1_parts,
        "predictions": verdicts,
        "prediction_numbers": numbers,
        "overall": {"categories": tally(kept, "fb_category"), "redux": tally(kept, "redux"),
                    "category_x_redux": crosstab(kept, "fb_category", "redux"),
                    "category_x_s1_flag": crosstab(kept, "fb_category", "s1_flag"),
                    "judged_category_x_redux": crosstab(judged, "fb_category", "redux")},
        "by_split": by_split,
        "gsm": gsm_summary,
        "exploratory": {"kappa_invalid_vs_redux_error_all_judged": None if k_all is None else float(k_all),
                        "kappa_n_all": len(pairs),
                        "kappa_clinical_and_pro_medicine": None if k_both is None else float(k_both),
                        "kappa_n_both": len(pairs_both),
                        "auc_margin_invalid_vs_valid_clinical_and_pro_medicine":
                            None if a_margin is None else float(a_margin),
                        "flag_other": pr(other_flag),
                        "redux_error_when_flagged": pr(flag_err_judged),
                        "redux_error_when_not_flagged": pr(noflag_err_judged),
                        "disputes_valid_but_flagged": len(disputes),
                        "disputes_redux": tally(disputes, "redux")},
        "note": ("Fantastic Bugs categories (fb88.fb_category): valid; key = the review points at the answer key; "
                 "other = any other problem. Units = distinct HELM questions (a second Fantastic Bugs row on the "
                 "same question is dropped). Redux judged = wrong_groundtruth, ok or one of the four other error "
                 "labels; error = any of the five. Flag = audit 77's rule on audit 80's top-10 panel. P2 Redux "
                 "error share among judged key rows >= 1/2; P3 Redux wrong_groundtruth share key > other; P4 Redux "
                 "error share among judged valid rows <= 1/4 (>= 10 rows); P5 flag rate key > valid; P6 flag rate "
                 "key >= 1/2; P7 at least one of audit 86's S1-flagged, Platinum-kept GSM8K questions is among "
                 "Fantastic Bugs' 16 published GSM8K issues. Groups under 5 rows (10 for P4) are undecidable."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    rows_out = [{k: v for k, v in u.items() if k != "qid"} for u in units]
    with open(os.path.join(args.out_dir, "rows.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 88,
                   "note": ("One row per published Fantastic Bugs row (split, 0-based row number in the HF viewer "
                            "split). fb_category is our reading of their review (fb88.fb_category), not their text. "
                            "Redux labels: MMLU-Redux 2.0 (CC BY 4.0). Platinum statuses: GSM8K-Platinum (CC BY-SA "
                            "4.0). A flag is not a verdict."),
                   "panel": panel, "mmlu": rows_out, "gsm": gsm_rows_out}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and rows.json")


if __name__ == "__main__":
    main()
