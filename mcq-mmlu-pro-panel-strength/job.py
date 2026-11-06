"""How strong must a model panel be to find MMLU-Pro's wrong keys, and do questions no archive answers with the key
hold errors? (audit 84)

Loads TIGER-AI-Lab's published per-question MMLU-Pro predictions (as audits 77-79), ranks the included archives by
accuracy and cuts them into four disjoint panels of 10 (S1 = ranks 1-10, gated to equal audit 77's panel and
reproduce its flag counts and precision). For each panel: audit 77's flag, its margin AUC (MMLU-Redux miskeys vs OK)
and its precision at an equal review budget (K = S1's flag count, ties shared). Also the ranks 1-20 panel, and the
no-key flag (no included archive picks the key) against S1's 10-of-10 flag.

Gates before any prediction is scored: all hand-traced fixtures match; the HF parse reproduces audit 63's row and
family counts; the Redux join reproduces audit 75; at least 40 archives are included. Writes results.json
(aggregates, verdicts, strata, windows, overlaps) and nokey_candidates.json (every no-key question: id, source,
category, letters, counts, Redux status; no question, option or model text). Usage: python job.py --out-dir /out
(network required). Apache-2.0.
"""

import argparse
import hashlib
import io
import json
import os
import urllib.parse
import urllib.request
import zipfile
from fractions import Fraction

import pyarrow.parquet as pq

import panel84 as pm
import cases84 as C

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


def _listing(hf):
    return json.loads(_get(PARQUET_API % hf).decode("utf-8"))["parquet_files"]


def read_spec(spec):
    rows, shards = [], []
    files = sorted((f["split"], f["url"]) for f in _listing(spec["hf"])
                   if f["config"] == spec["config"] and f["split"] in set(spec["splits"]))
    for split, url in files:
        raw = _get(url)
        shards.append({"split": split, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        t = pq.read_table(io.BytesIO(raw), columns=spec["cols"])
        data = {c: t.column(c).to_pylist() for c in spec["cols"]}
        for i in range(t.num_rows):
            rows.append({c: data[c][i] for c in spec["cols"]})
    return rows, shards


def read_redux():
    rows, shards = [], []
    files = sorted((f["config"], f["url"]) for f in _listing(C.REDUX_DATASET) if f["split"] == C.REDUX_SPLIT)
    for config, url in files:
        raw = _get(url)
        shards.append({"config": config, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        t = pq.read_table(io.BytesIO(raw))
        cols = {c: (t.column(c).to_pylist() if c in t.column_names else [None] * t.num_rows)
                for c in ("question", "choices", "answer", "error_type", "correct_answer")}
        for q, ch, a, et, ca in zip(cols["question"], cols["choices"], cols["answer"], cols["error_type"],
                                    cols["correct_answer"]):
            rows.append({"subject": config, "question": q, "choices": list(ch or []),
                         "answer": int(a) if a is not None else None, "label": pm.label_of(et), "correct": ca})
    return rows, shards


def family(src):
    s = src or ""
    return s.split("-", 1)[0] if s else "unknown"


def records_from_zip(blob):
    recs, log = [], []
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for info in z.infolist():
            name = info.filename
            if info.is_dir() or "__MACOSX" in name or not name.lower().endswith(".json"):
                continue
            try:
                data = json.loads(z.read(info).decode("utf-8"))
            except Exception as e:  # noqa: BLE001 - report unreadable members, never patch them
                log.append({"member": name, "status": "unreadable: %s" % type(e).__name__})
                continue
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list):
                        items.extend(v)
            got = [d for d in items if isinstance(d, dict) and "pred" in d and "question_id" in d]
            log.append({"member": name, "status": "ok" if got else "no_prediction_records", "records": len(got)})
            recs.extend(got)
    return recs, log


def _qid(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def _norm_options(opts):
    return [str(o).strip() for o in (opts or [])]


def join_status(rec, hf_by_id):
    q = hf_by_id.get(_qid(rec.get("question_id")))
    if q is None:
        return "no_id"
    if _norm_options(rec.get("options")) != _norm_options(q["options"]):
        return "options_differ"
    if "answer_index" in rec and rec["answer_index"] is not None:
        if _qid(rec["answer_index"]) != q["answer_index"]:
            return "answer_differ"
    elif "answer" in rec and rec["answer"] is not None:
        if str(rec["answer"]).strip().upper() != pm.LETTERS[q["answer_index"]]:
            return "answer_differ"
    return "ok"


def fixture_ok():
    panel = pm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
    flags, _t = pm.panel_flags(panel, C.FIX_PREDS, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
    labels, amb, mk, counts = pm.redux_labels(C.FIX_REDUX, C.FIX_MMLU, C.FIX_PRO)
    t = C.FIX_REDUX_TARGET
    kc = pm.key_counts(C.FIX_K_MODELS, C.FIX_K_PREDS, C.FIX_K_QUESTIONS)
    return {"panel_flags": panel == C.FIX_TARGET["panel"] and flags == C.FIX_TARGET["flags"],
            "redux_join": (labels == t["labels"] and amb == t["ambiguous_ids"] and mk == t["miskey_ids"]
                           and counts == t["counts"]),
            "margin_auc": (all(pm.margin(c, k) == w for (c, k), w in C.FIX_MARGIN)
                           and all(pm.auc(p, n) == w for (p, n), w in C.FIX_AUC)),
            "strata": pm.strata(C.FIX_S_ACC, 2, 3) == C.FIX_S_TARGET,
            "budget": all(pm.budget_counts(C.FIX_B_SCORE, C.FIX_B_SETS, b) == w for b, w in C.FIX_B_CASES),
            "stratum_stats": pm.stratum_stats(C.FIX_P_FLAGS, C.FIX_P_SCORE, C.FIX_P_G, C.FIX_P_BUDGET)
                             == C.FIX_P_TARGET,
            "no_key": (kc == C.FIX_K_COUNTS and pm.nk_flags(kc, C.NK_MIN_COV) == C.FIX_K_NK
                       and pm.key_share(kc) == C.FIX_K_SHARE),
            "verdicts": pm.predictions84(C.FIX_V_ST, C.FIX_V_TOP20, C.FIX_V_BASE[0], C.FIX_V_BASE[1], C.FIX_V_NK,
                                         C.FIX_V_UNAN, C.THRESHOLDS) == C.FIX_VERDICTS}


def letter(i):
    return None if i is None else pm.LETTERS[i]


def share(a, n):
    return float(Fraction(a, n)) if n else None


def mean_acc(models, acc):
    return float(sum(pm.accuracy(*acc[m]) for m in models) / len(models)) if models else None


def load_archives(hf_by_id):
    archives, preds, acc = {}, {}, {}
    for zname in C.ARCHIVES:
        model = C.model_name(zname)
        try:
            blob = _get(C.EVAL_RESULTS_URL % urllib.parse.quote(zname))
        except RuntimeError as e:
            archives[model] = {"archive": zname, "status": "download_failed", "error": str(e)[:300]}
            print("[archive] %-44s download failed" % model)
            continue
        sha = hashlib.sha256(blob).hexdigest()
        try:
            recs, member_log = records_from_zip(blob)
        except zipfile.BadZipFile:
            archives[model] = {"archive": zname, "sha256": sha, "bytes": len(blob), "status": "bad_zip"}
            print("[archive] %-44s bad zip" % model)
            continue
        del blob
        status, joined = {}, {}
        for rec in recs:
            s = join_status(rec, hf_by_id)
            status[s] = status.get(s, 0) + 1
            if s != "ok":
                continue
            qid = int(rec["question_id"])
            if qid not in joined:
                joined[qid] = rec.get("pred")
        n_rec = len(recs)
        del recs
        join_share = status.get("ok", 0) / n_rec if n_rec else 0.0
        coverage = len(joined) / len(hf_by_id)
        ok = join_share >= C.MIN_JOIN_SHARE and coverage >= C.MIN_JOIN_SHARE
        archives[model] = {"archive": zname, "sha256": sha, "members": len(member_log), "n_records": n_rec,
                           "join_status": status, "join_share": join_share, "coverage": coverage,
                           "status": "included" if ok else "excluded_join"}
        if not ok:
            print("[archive] %-44s excluded" % model)
            continue
        correct = 0
        for qid, p in joined.items():
            r = hf_by_id[qid]
            i = pm.pred_index(p, len(r["options"]))
            correct += 1 if (i is not None and i == r["answer_index"]) else 0
        preds[model] = joined
        acc[model] = (correct, len(joined))
        archives[model]["accuracy"] = correct / len(joined)
    return archives, preds, acc


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

    raw_pro, pro_shards = read_spec(C.MMLU_PRO)
    rows = [r for r in raw_pro if r["options"] and len(r["options"]) >= 2 and r["answer_index"] is not None
            and 0 <= r["answer_index"] < len(r["options"])]
    fam_n = {}
    for r in rows:
        fam_n[family(r["src"])] = fam_n.get(family(r["src"]), 0) + 1
    struct_ok = len(rows) == C.EXPECTED["n_valid"] and fam_n == C.EXPECTED["family_n"]
    print("[structural] n=%d families=%s ok=%s" % (len(rows), fam_n, struct_ok))
    if not struct_ok:
        raise SystemExit("structural gate failed -- aborting")
    hf_by_id = {int(r["question_id"]): r for r in rows}
    fam_of = {q: family(r["src"]) for q, r in hf_by_id.items()}

    mmlu, mmlu_shards = read_spec(C.MMLU)
    redux, redux_shards = read_redux()
    labels, amb_ids, miskey_ids, rcounts = pm.redux_labels(redux, mmlu, raw_pro)
    del mmlu, redux
    redux_ok = (rcounts["redux_mmlu"]["joined"] == C.EXPECTED_REDUX["joined"]
                and rcounts["pro_join"]["in_pro"] == C.EXPECTED_REDUX["in_pro"]
                and rcounts["pro_join"]["ambiguous_pro"] == C.EXPECTED_REDUX["ambiguous_pro"]
                and len(miskey_ids) == C.N_MISKEY_IDS)
    print("[redux] %s miskey_ids=%d ok=%s" % (rcounts, len(miskey_ids), redux_ok))
    if not redux_ok:
        raise SystemExit("Redux join does not reproduce audit 75 -- aborting")

    archives, preds, acc = load_archives(hf_by_id)
    print("[archives] included=%d of %d" % (len(acc), len(C.ARCHIVES)))
    if len(acc) < C.MIN_INCLUDED_ARCHIVES:
        raise SystemExit("only %d archives included -- aborting" % len(acc))

    questions = {q: (len(r["options"]), r["answer_index"]) for q, r in hf_by_id.items()}
    g = pm.groups(questions.keys(), fam_of, labels, amb_ids)
    ranked = pm.select_panel(acc, len(acc))
    panels = pm.strata(acc, C.PANEL_SIZE, C.N_STRATA)

    # ----- S1 = audit 77's panel (gate) -----
    flags_by, tallies_by, score_by = [], [], []
    for panel in panels:
        f, t = pm.panel_flags(panel, preds, questions, C.MIN_AGREE)
        flags_by.append(f)
        tallies_by.append(t)
        score_by.append(pm.margins(t, questions))
    flagged77 = {name: pm.n_flagged(g[name], flags_by[0]) for name in C.EXPECTED_77_FLAGGED}
    prec77 = pm.flag_precision(flags_by[0], g)
    repro_ok = (panels[0] == C.EXPECTED_PANEL and flagged77 == C.EXPECTED_77_FLAGGED
                and prec77 == C.EXPECTED_77_PRECISION)
    print("[repro77] panel_match=%s flagged=%s precision=%s ok=%s"
          % (panels[0] == C.EXPECTED_PANEL, flagged77, prec77, repro_ok))
    K = pm.n_flagged(g["all"], flags_by[0])

    err_ids = g["miskey"] + g["other_error"]
    base_err, base_judged = len(err_ids), len(err_ids) + len(g["ok"])
    print("[base] miskey=%d other_error=%d ok=%d -> %d of %d judged carry an error label"
          % (len(g["miskey"]), len(g["other_error"]), len(g["ok"]), base_err, base_judged))

    st = [pm.stratum_stats(flags_by[i], score_by[i], g, K) for i in range(C.N_STRATA)]
    strata_out = []
    for i, panel in enumerate(panels):
        row = {"stratum": "S%d" % (i + 1), "ranks": [i * C.PANEL_SIZE + 1, (i + 1) * C.PANEL_SIZE],
               "mean_accuracy": mean_acc(panel, acc),
               "models": [{"model": m, "accuracy": float(pm.accuracy(*acc[m]))} for m in panel],
               "flags_by_family": {f: pm.n_flagged(g[f], flags_by[i]) for f in pm.FAMILIES},
               "unreviewed_ori_mmlu_flags": pm.n_flagged(g["unreviewed_ori_mmlu"], flags_by[i])}
        row.update(pm.stats_json(st[i]))
        strata_out.append(row)
        print("[stratum] %s" % {k: v for k, v in row.items() if k != "models"})

    top_panel = ranked[:C.TOP20_SIZE]
    f20, t20 = pm.panel_flags(top_panel, preds, questions, C.TOP20_MIN_AGREE)
    s20 = pm.margins(t20, questions)
    st20 = pm.stratum_stats(f20, s20, g, K)
    top20_out = {"ranks": [1, C.TOP20_SIZE], "min_agree": C.TOP20_MIN_AGREE, "mean_accuracy": mean_acc(top_panel, acc)}
    top20_out.update(pm.stats_json(st20))
    print("[top20] %s" % top20_out)

    # ----- The no-key flag and S1 at 10 of 10 -----
    models = sorted(acc)
    kc = pm.key_counts(models, preds, questions)
    nk = pm.nk_flags(kc, C.NK_MIN_COV)
    nk_prec = pm.flag_precision(nk, g)
    unan = {q: pm.flag_question(tallies_by[0][q][0], questions[q][1], C.UNANIMOUS)[:2] for q in questions}
    unan_prec = pm.flag_precision(unan, g)
    print("[no_key] flagged=%d precision=%s; S1 10-of-10 flagged=%d precision=%s"
          % (pm.n_flagged(g["all"], nk), nk_prec, pm.n_flagged(g["all"], unan), unan_prec))

    verdicts = pm.predictions84(st, st20, base_err, base_judged, nk_prec, unan_prec, C.THRESHOLDS)
    p1_parts = {"fixtures": all(fx.values()), "structural": struct_ok, "redux": redux_ok, "reproduce_77": repro_ok,
                "archives": len(acc) >= C.MIN_INCLUDED_ARCHIVES}
    verdicts["P1_structural"] = all(p1_parts.values())
    verdicts["P1_counts"] = [len(rows), len(acc), K]
    print("[P1] %s" % p1_parts)
    for name in sorted(v for v in verdicts if not (v.endswith("_counts") or v.endswith("_auc")
                                                   or v.endswith("_precision"))):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    print("[prediction] numbers %s" % {k: v for k, v in sorted(verdicts.items())
                                       if k.endswith("_counts") or k.endswith("_auc") or k.endswith("_precision")})

    # ----- Exploratory -----
    windows = []
    for s in C.WINDOW_STARTS:
        panel = ranked[s:s + C.PANEL_SIZE]
        if len(panel) < C.PANEL_SIZE:
            continue
        f, t = pm.panel_flags(panel, preds, questions, C.MIN_AGREE)
        stw = pm.stratum_stats(f, pm.margins(t, questions), g, K)
        b = pm._bprec(stw)
        windows.append({"ranks": [s + 1, s + C.PANEL_SIZE], "mean_accuracy": mean_acc(panel, acc),
                        "flags": stw["flags"], "auc_miskey_vs_ok": None if stw["auc"] is None else float(stw["auc"]),
                        "budget_precision": None if b is None else float(b)})
    print("[windows] %s" % windows)

    overlap = []
    s1_set = {q for q in questions if flags_by[0][q][0]}
    s1_mis = {q for q in g["miskey"] if flags_by[0][q][0]}
    for i in range(1, C.N_STRATA):
        fs = {q for q in questions if flags_by[i][q][0]}
        ms = {q for q in g["miskey"] if flags_by[i][q][0]}
        overlap.append({"stratum": "S%d" % (i + 1), "flags": len(fs), "shared_with_S1": len(fs & s1_set),
                        "shared_miskeys": len(ms & s1_mis), "S1_miskeys_missed": len(s1_mis - ms),
                        "new_miskeys": len(ms - s1_mis)})
    print("[overlap] %s" % overlap)

    auc_any = []
    for i in range(C.N_STRATA):
        a = pm.auc([score_by[i][q] for q in err_ids], [score_by[i][q] for q in g["ok"]])
        auc_any.append({"stratum": "S%d" % (i + 1), "auc_any_error_vs_ok": None if a is None else float(a)})
    print("[auc any error] %s" % auc_any)

    ks = pm.key_share(kc)
    ks_auc = pm.auc([ks[q] for q in g["miskey"]], [ks[q] for q in g["ok"]])
    ks_err, ks_judged, ks_mis = pm.budget_counts(ks, [set(err_ids), set(err_ids) | set(g["ok"]),
                                                      set(g["miskey"])], K)
    key_share_out = {"auc_miskey_vs_ok": None if ks_auc is None else float(ks_auc),
                     "budget": {"error_labelled": str(ks_err), "judged": str(ks_judged), "miskeys": str(ks_mis),
                                "precision": float(ks_err / ks_judged) if ks_judged else None}}
    print("[key_share all archives] %s" % key_share_out)

    nk_by_group = {name: pm.n_flagged(g[name], nk) for name in
                   ("all", "miskey", "ok", "other_error", "unsure_or_conflict", "unreviewed_ori_mmlu",
                    "ambiguous_ori_mmlu") + pm.FAMILIES}
    unan_by_group = {name: pm.n_flagged(g[name], unan) for name in nk_by_group}
    nk_and_unan = {q: (nk[q][0] and unan[q][0], None) for q in questions}
    print("[no_key by group] %s" % nk_by_group)
    print("[S1 10-of-10 by group] %s" % unan_by_group)

    def status_of(q):
        lab = labels.get(q)
        if lab is not None:
            return lab
        if fam_of[q] != "ori_mmlu":
            return "not_mmlu_derived"
        return "ambiguous" if q in amb_ids else "not_reviewed"

    cands = []
    for q in sorted(questions):
        if not nk[q][0]:
            continue
        r = hf_by_id[q]
        k, key_i = questions[q]
        all_counts, all_none = pm.votes([preds[m].get(q) for m in models if q in preds[m]], k)
        top_i, top_n = pm.consensus(all_counts, key_i)
        cands.append({"question_id": q, "src": r["src"], "category": r["category"], "k": k, "key": letter(key_i),
                      "n_archives": kc[q][0], "all_archives_top_option": letter(top_i),
                      "all_archives_top_votes": top_n, "all_archives_no_answer": all_none,
                      "s1_votes": tallies_by[0][q][0], "s1_flag": bool(flags_by[0][q][0]),
                      "redux": status_of(q)})

    out = {
        "audit": 84,
        "slug": "mcq-mmlu-pro-panel-strength",
        "dataset": ("MMLU-Pro (TIGER-Lab/MMLU-Pro 'default' test), MMLU (cais/mmlu 'all' test) and MMLU-Redux 2.0 "
                    "via the HF datasets-server parquet API; per-question predictions from "
                    "github.com/TIGER-AI-Lab/MMLU-Pro eval_results (sha256 recorded). Only ids, letters, counts and "
                    "public model names and accuracies."),
        "fixture": fx,
        "structural": {"n": len(rows), "family_n": fam_n, "shards": pro_shards},
        "redux_join": {"counts": rcounts, "n_miskey_ids": len(miskey_ids), "mmlu_shards": mmlu_shards,
                       "redux_shards": redux_shards},
        "archives": archives,
        "reproduce_77": {"panel_match": panels[0] == C.EXPECTED_PANEL, "flagged": flagged77,
                         "precision": list(prec77), "ok": repro_ok},
        "base": {"miskey": len(g["miskey"]), "other_error": len(g["other_error"]), "ok": len(g["ok"]),
                 "base_error_labelled": base_err, "base_judged": base_judged},
        "budget_K": K,
        "p1_parts": p1_parts,
        "predictions": verdicts,
        "strata": strata_out,
        "top20": top20_out,
        "no_key": {"min_cov": C.NK_MIN_COV, "by_group": nk_by_group, "precision": list(nk_prec),
                   "both_no_key_and_s1_unanimous": list(pm.flag_precision(nk_and_unan, g)),
                   "n_both": pm.n_flagged(g["all"], nk_and_unan)},
        "s1_unanimous": {"min_agree": C.UNANIMOUS, "by_group": unan_by_group, "precision": list(unan_prec)},
        "windows_exploratory": windows,
        "overlap_with_S1_exploratory": overlap,
        "auc_any_error_exploratory": auc_any,
        "key_share_all_archives_exploratory": key_share_out,
        "n_nokey_candidates": len(cands),
        "note": ("Strata: included archives ranked by accuracy (ties by name), S1..S4 = ranks 1-10 ... 31-40. Flag: "
                 "at least 6 of 10 pick one non-key option and more than pick the key (audit 77). Margin = top "
                 "non-key votes minus key votes. Equal budget: the K = S1-flag-count highest-margin questions over "
                 "all 12,032, ties at the cut shared evenly (expected counts). Precision = share of Redux-judged "
                 "questions (wrong key, OK or another error label) with an error label. No-key: at least 2 included "
                 "archives cover the question and none picks the key. P1 structural; P2 S4 flags more than S1; P3 "
                 "HEADLINE equal-budget precision S1 > S2 > S4; P4 margin AUC S1 > S4; P5 S4 equal-budget precision "
                 ">= 2x base rate; P6 ranks 1-20 not more precise than S1 at the same budget; P7 no-key precision "
                 "above S1's 10-of-10 precision, with at least 10 judged no-key questions."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "nokey_candidates.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 84, "note": ("Model-flagged, NOT expert-checked: MMLU-Pro questions that none of the "
                   "included TIGER-AI-Lab archives answers with the published key. all_archives_top_option = the "
                   "non-key option most archives pick (None if tied); s1_votes = votes of the 10 most accurate "
                   "archives per option. Each may hold a wrong key, a second defensible answer or a question every "
                   "model gets wrong."), "candidates": cands}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and nokey_candidates.json (%d candidates)" % len(cands))


if __name__ == "__main__":
    main()
