"""Do two independent model panels, in two harnesses, agree on which MMLU answer keys are wrong? (audit 81)

Rebuilds audit 80 (HELM MMLU release v1.13.0: 10 most accurate included models, audit 77's flag, MMLU-Redux 2.0
labels) and audit 77 (TIGER-AI-Lab's per-question MMLU-Pro archives: 10 most accurate archives, the same flag), both
gated to reproduce their published counts, joins every MMLU-derived MMLU-Pro question to its HELM MMLU question, and
compares the precision of three flags on the joined questions: HELM's panel alone, the MMLU-Pro panel alone, and
their agreement (both flag, with the same consensus answer text).

Gates: the hand-traced fixtures must match before any download; MMLU-Pro must parse to audit 63's row and family
counts; the Redux join must place at least 4,000 rows. Writes results.json (aggregates, join counts, precisions,
per-subject counts) and agree_candidates.json (every question both panels flag with the same answer: subject, HELM
instance id and position, MMLU-Pro question_id, letters, votes, Redux status and a 16-hex sha256 of the normalised
question; no question, option or model text). Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import hashlib
import io
import json
import os
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import pyarrow.parquet as pq

import cross81 as cm
import cases81 as C

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


def run_url(suite, run, fname):
    return "%s/runs/%s/%s/%s" % (C.HELM_BASE, suite, urllib.parse.quote(run, safe=":,=@-_."), fname)


def _listing(hf):
    return _json(PARQUET_API % hf)["parquet_files"]


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
                for c in ("question", "choices", "answer", "error_type")}
        for q, ch, a, et in zip(cols["question"], cols["choices"], cols["answer"], cols["error_type"]):
            rows.append({"subject": config, "question": q, "choices": list(ch or []),
                         "answer": int(a) if a is not None else None, "label": cm.label_of(et)})
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
        if str(rec["answer"]).strip().upper() != cm.LETTERS[q["answer_index"]]:
            return "answer_differ"
    return "ok"


def fixture_ok():
    idx = {m: {q: cm.pred_index(p, C.FIX_QUESTIONS[q][0]) for q, p in d.items()} for m, d in C.FIX_PREDS.items()}
    panel = cm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
    flags, _t = cm.panel_flags(panel, idx, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
    parsed = {s: cm.parse_instances(items) for s, items in C.FIX_INST.items()}
    qids, info, counts = cm.build_universe(parsed)
    t = C.FIX_UNIVERSE_TARGET
    preds_ok = all(cm.map_predictions(C.FIX_PRED[s], parsed[s], s, qids) == C.FIX_PRED_TARGET[s]
                   for s in ("virology", "anatomy"))
    rj = cm.redux_join(C.FIX_REDUX, qids, C.FIX_GOLD)
    agree = cm.agree_flags(C.FIX_A_J, C.FIX_A_PAIRS, C.FIX_A_HELM_FLAGS, C.FIX_A_PRO_FLAGS, C.FIX_J_HELM_OPTS,
                           C.FIX_A_PRO_OPTS)
    return {"panel_flags": panel == C.FIX_TARGET["panel"] and flags == C.FIX_TARGET["flags"],
            "runs": cm.select_runs(C.FIX_RUNS) == C.FIX_RUNS_TARGET,
            "universe": qids == t["qids"] and info == t["info"] and counts == t["counts"],
            "predictions": preds_ok,
            "redux_join": rj == C.FIX_REDUX_TARGET and cm.groups(3, rj[0]) == C.FIX_GROUPS_TARGET,
            "pro_helm_join": (cm.helm_options(C.FIX_J_QIDS) == C.FIX_J_HELM_OPTS
                              and cm.stem_index(C.FIX_J_QIDS) == C.FIX_J_STEMS
                              and cm.join_pro_helm(C.FIX_J_PRO, C.FIX_J_STEMS, C.FIX_J_HELM_OPTS) == C.FIX_J_TARGET),
            "agree": agree == C.FIX_A_TARGET,
            "verdicts": cm.predictions81(C.FIX_V_GJ, C.FIX_V_GJX, C.FIX_V_HELM, C.FIX_V_PRO, C.FIX_V_AGREE,
                                         C.THRESHOLDS) == C.FIX_VERDICTS}


def share(a, n):
    return float(Fraction(a, n)) if n else None


def letter(i):
    return None if i is None else cm.LETTERS[i]


def prec_dict(pair):
    e, j = pair
    return {"error_labelled": e, "judged": j, "share": share(e, j)}


# ----- HELM: audit 80, rebuilt -----

def build_helm():
    release_url = "%s/releases/%s/runs_to_run_suites.json" % (C.HELM_BASE, C.HELM_RELEASE)
    raw_release = _get(release_url)
    run_suites = json.loads(raw_release.decode("utf-8"))
    chosen, dups = cm.select_runs(run_suites)
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
            return key, cm.parse_instances(_json(run_url(suite, inst_src[key], "instances.json"))), None
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
        if s not in base_suite or cm.suite_version(suite) < cm.suite_version(base_suite[s]):
            base_suite[s] = suite
    qids, info, ucounts = cm.build_universe({s: instances[(base_suite[s], s)] for s in base_suite})
    n_q = len(info)
    gold_of = [r[3] for r in info]
    print("[helm universe] files=%d failed=%d questions=%d %s" % (len(instances), len(inst_fail), n_q, ucounts))

    def fetch_pred(item):
        (m, s), (run, suite) = item
        inst = instances.get((suite, s))
        if inst is None:
            return m, s, None, {"error": "no instances for suite"}
        try:
            data = _json(run_url(suite, run, "display_predictions.json"))
        except Exception as e:  # noqa: BLE001
            return m, s, None, {"error": str(e)[:200]}
        out, c = cm.map_predictions(data, inst, s, qids)
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


# ----- MMLU-Pro: audit 77, rebuilt -----

def build_pro():
    raw_pro, pro_shards = read_spec(C.MMLU_PRO)
    rows = [r for r in raw_pro if r["options"] and len(r["options"]) >= 2 and r["answer_index"] is not None
            and 0 <= r["answer_index"] < len(r["options"])]
    fam_n = {}
    for r in rows:
        fam_n[family(r["src"])] = fam_n.get(family(r["src"]), 0) + 1
    struct_ok = len(rows) == C.EXPECTED_PRO["n_valid"] and fam_n == C.EXPECTED_PRO["family_n"]
    print("[pro structural] n=%d families=%s ok=%s" % (len(rows), fam_n, struct_ok))
    if not struct_ok:
        raise SystemExit("MMLU-Pro structural gate failed -- aborting")
    hf_by_id = {int(r["question_id"]): r for r in rows}
    questions = {q: (len(r["options"]), r["answer_index"]) for q, r in hf_by_id.items()}

    archives, preds, acc = {}, {}, {}
    for zname in C.ARCHIVES:
        model = C.model_name(zname)
        try:
            blob = _get(C.EVAL_RESULTS_URL % urllib.parse.quote(zname))
        except RuntimeError as e:
            archives[model] = {"status": "download_failed", "error": str(e)[:300]}
            continue
        sha = hashlib.sha256(blob).hexdigest()
        try:
            recs, _log = records_from_zip(blob)
        except zipfile.BadZipFile:
            archives[model] = {"sha256": sha, "status": "bad_zip"}
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
        archives[model] = {"sha256": sha, "n_records": n_rec, "join_share": join_share, "coverage": coverage,
                           "status": "included" if ok else "excluded_join"}
        if not ok:
            continue
        idx = {q: cm.pred_index(p, questions[q][0]) for q, p in joined.items()}
        correct = sum(1 for q, i in idx.items() if i is not None and i == questions[q][1])
        preds[model] = idx
        acc[model] = (correct, len(idx))
        archives[model]["accuracy"] = correct / len(idx)
    print("[pro archives] included=%d of %d" % (len(acc), len(C.ARCHIVES)))
    return {"rows": rows, "hf_by_id": hf_by_id, "questions": questions, "fam_n": fam_n, "preds": preds, "acc": acc,
            "archives": archives, "shards": pro_shards}


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

    # ----- HELM panel and flags (audit 80) -----
    H = build_helm()
    qids, info, n_q, gold_of = H["qids"], H["info"], H["n_q"], H["gold_of"]
    subj_of = [r[0] for r in info]
    h_questions = {q: (info[q][2], info[q][3]) for q in range(n_q)}
    redux, redux_shards = read_redux()
    labels, rcounts, key_agree = cm.redux_join(redux, qids, gold_of)
    print("[redux] rows=%d %s key_agree=%d" % (len(redux), rcounts, key_agree))
    if rcounts["joined"] < C.ABORT_REDUX_JOINED:
        raise SystemExit("Redux join placed only %d rows -- aborting" % rcounts["joined"])
    g = cm.groups(n_q, labels)
    panel_h = cm.select_panel(H["acc"], C.PANEL_SIZE)
    flags_h, tallies_h = cm.panel_flags(panel_h, H["preds"], h_questions, C.MIN_AGREE)
    flagged80 = {name: cm.n_flagged(g[name], flags_h) for name in C.EXPECTED_80["flagged"]}
    prec80 = cm.flag_precision(flags_h, g)
    repro80 = (n_q == C.EXPECTED_80["universe"] and len(H["acc"]) == C.EXPECTED_80["included"]
               and panel_h == C.EXPECTED_80["panel"] and flagged80 == C.EXPECTED_80["flagged"]
               and prec80 == C.EXPECTED_80["precision"])
    print("[repro80] panel=%s flagged=%s precision=%s ok=%s" % (panel_h, flagged80, prec80, repro80))

    # ----- MMLU-Pro panel and flags (audit 77) -----
    P = build_pro()
    hf_by_id, p_questions = P["hf_by_id"], P["questions"]
    panel_p = cm.select_panel(P["acc"], C.PANEL_SIZE)
    flags_p, tallies_p = cm.panel_flags(panel_p, P["preds"], p_questions, C.MIN_AGREE)
    fam_of = {q: family(r["src"]) for q, r in hf_by_id.items()}
    flagged77 = {"all": cm.n_flagged(list(p_questions), flags_p),
                 "ori_mmlu": cm.n_flagged([q for q in p_questions if fam_of[q] == "ori_mmlu"], flags_p),
                 "stemez": cm.n_flagged([q for q in p_questions if fam_of[q] == "stemez"], flags_p)}
    repro77 = panel_p == C.EXPECTED_77["panel"] and flagged77 == C.EXPECTED_77["flagged"]
    print("[repro77] panel=%s flagged=%s ok=%s" % (panel_p, flagged77, repro77))

    # ----- Join MMLU-Pro's MMLU-derived questions to HELM -----
    helm_opts = cm.helm_options(qids)
    pairs, jcounts = cm.join_pro_helm(P["rows"], cm.stem_index(qids), helm_opts)
    pro_opts = {p: list(r["options"]) for p, r in hf_by_id.items()}
    J = sorted(q for q, p in pairs.items()
               if cm.same_key(helm_opts[q], gold_of[q], pro_opts[p], p_questions[p][1]))
    n_diff_key = len(pairs) - len(J)
    print("[join] %s same_key=%d different_key=%d" % (jcounts, len(J), n_diff_key))

    keep = set(J)
    keep_x = {q for q in J if subj_of[q] != "virology"}
    gJ, gJx = cm.restrict(g, keep), cm.restrict(g, keep_x)
    helmJ = {q: flags_h[q] for q in J}
    proJ = {q: flags_p[pairs[q]] for q in J}
    agree = cm.agree_flags(J, pairs, flags_h, flags_p, helm_opts, pro_opts)

    verdicts = cm.predictions81(gJ, gJx, helmJ, proJ, agree, C.THRESHOLDS)
    p1_parts = {
        "fixtures": all(fx.values()),
        "reproduce_80": repro80,
        "reproduce_77": repro77,
        "pairs_same_key": len(J) >= C.MIN_PAIRS_SAME_KEY,
        "same_key_share": bool(pairs) and Fraction(len(J), len(pairs)) >= C.MIN_SAME_KEY_SHARE,
    }
    verdicts["P1_structural"] = all(p1_parts.values())
    verdicts["P1_counts"] = [n_q, len(H["acc"]), len(P["acc"]), len(pairs), len(J)]
    print("[P1] %s" % p1_parts)
    for name in sorted(v for v in verdicts if not v.endswith("_counts")):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    print("[prediction] counts %s" % {k: v for k, v in sorted(verdicts.items()) if k.endswith("_counts")})

    # ----- Exploratory -----
    def outcome(q):
        """What the MMLU-Pro panel does on a question HELM's panel flags."""
        if agree[q][0]:
            return "agree"
        fp, cp = proJ[q]
        if not fp:
            return "pro_no_flag"
        if norm_in(pro_opts[pairs[q]][cp], helm_opts[q]):
            return "pro_other_mmlu_option"
        return "pro_added_option"

    def norm_in(text, opts):
        return cm.norm(text) in set(cm.norm(o) for o in opts)

    by_group = {}
    for name in ("all", "miskey", "ok", "other_error", "unsure_or_conflict", "unreviewed"):
        ids = gJ[name]
        row = {"n": len(ids), "helm": cm.n_flagged(ids, helmJ), "pro": cm.n_flagged(ids, proJ),
               "agree": cm.n_flagged(ids, agree)}
        tally = {}
        for q in ids:
            if helmJ[q][0]:
                o = outcome(q)
                tally[o] = tally.get(o, 0) + 1
        row["helm_flag_outcomes"] = tally
        by_group[name] = row
        print("[group] %s %s" % (name, row))

    h10 = {q: cm.flag_question(tallies_h[q][0], h_questions[q][1], 10)[:2] for q in J}
    p10 = {q: cm.flag_question(tallies_p[pairs[q]][0], p_questions[pairs[q]][1], 10)[:2] for q in J}
    agree10 = {q: (agree[q][0] and h10[q][0] and p10[q][0], agree[q][1]) for q in J}
    either = {q: (helmJ[q][0] or proJ[q][0], None) for q in J}
    precision = {
        "helm": prec_dict(cm.flag_precision(helmJ, gJ)),
        "pro": prec_dict(cm.flag_precision(proJ, gJ)),
        "agree": prec_dict(cm.flag_precision(agree, gJ)),
        "either": prec_dict(cm.flag_precision(either, gJ)),
        "helm_10_of_10": prec_dict(cm.flag_precision(h10, gJ)),
        "pro_10_of_10": prec_dict(cm.flag_precision(p10, gJ)),
        "agree_both_10_of_10": prec_dict(cm.flag_precision(agree10, gJ)),
        "no_virology": {"helm": prec_dict(cm.flag_precision(helmJ, gJx)),
                        "pro": prec_dict(cm.flag_precision(proJ, gJx)),
                        "agree": prec_dict(cm.flag_precision(agree, gJx))},
    }
    print("[precision] %s" % precision)
    flagged_counts = {"agree": cm.n_flagged(J, agree), "agree_both_10_of_10": cm.n_flagged(J, agree10),
                      "agree_unreviewed": cm.n_flagged(gJ["unreviewed"], agree),
                      "agree_both_10_of_10_unreviewed": cm.n_flagged(gJ["unreviewed"], agree10)}
    print("[flagged] %s" % flagged_counts)

    by_subject = {}
    for s in sorted(set(subj_of[q] for q in J)):
        ids = [q for q in J if subj_of[q] == s]
        gs = cm.restrict(gJ, set(ids))
        by_subject[s] = {"n": len(ids), "helm": cm.n_flagged(ids, helmJ), "pro": cm.n_flagged(ids, proJ),
                         "agree": cm.n_flagged(ids, agree), "agree_precision": list(cm.flag_precision(agree, gs)),
                         "helm_precision": list(cm.flag_precision(helmJ, gs)),
                         "agree_unreviewed": cm.n_flagged(gs["unreviewed"], agree)}

    qtext = [None] * n_q
    for key, q in qids.items():
        qtext[q] = key[1][0]
    candidates = []
    for q in J:
        if not agree[q][0]:
            continue
        s, iid, k, gold, pos = info[q]
        ch = agree[q][1]
        p = pairs[q]
        fp, cp = flags_p[p]
        hc, hn = tallies_h[q]
        pc, pn = tallies_p[p]
        pkey = p_questions[p][1]
        candidates.append({"subject": s, "helm_instance_id": iid, "helm_test_position": pos, "helm_key": letter(gold),
                           "helm_consensus": letter(ch), "helm_votes": [hc[ch], hc[gold], hn],
                           "mmlu_pro_question_id": p, "mmlu_pro_k": len(pro_opts[p]), "mmlu_pro_key": letter(pkey),
                           "mmlu_pro_consensus": letter(cp), "mmlu_pro_votes": [pc[cp], pc[pkey], pn],
                           "both_10_of_10": bool(agree10[q][0]),
                           "redux": labels.get(q, "not_in_redux_sample"),
                           "question_sha256_16": cm.question_hash(qtext[q])})

    out = {
        "audit": 81,
        "slug": "mcq-mmlu-cross-harness-consensus",
        "dataset": ("HELM MMLU release %s (Stanford CRFM, public GCS bucket crfm-helm-public/mmlu); MMLU-Pro "
                    "(TIGER-Lab/MMLU-Pro 'default' test) and MMLU-Redux 2.0 via the HF datasets-server parquet API; "
                    "per-question MMLU-Pro predictions from github.com/TIGER-AI-Lab/MMLU-Pro eval_results. Only ids, "
                    "letters, counts and hashes." % C.HELM_RELEASE),
        "fixture": fx,
        "helm": {"release_sha256": H["release_sha256"], "universe": n_q, "universe_counts": H["universe_counts"],
                 "instances_failed": H["inst_fail"], "models": H["n_models"], "included": len(H["acc"]),
                 "panel": [{"model": m, "accuracy": float(cm.accuracy(*H["acc"][m]))} for m in panel_h],
                 "flagged": flagged80, "precision": list(prec80), "reproduces_80": repro80},
        "redux": {"rows": len(redux), "join": rcounts, "key_agree": key_agree, "shards": redux_shards},
        "mmlu_pro": {"n": len(P["rows"]), "family_n": P["fam_n"], "shards": P["shards"], "archives": P["archives"],
                     "included": len(P["acc"]),
                     "panel": [{"model": m, "accuracy": float(cm.accuracy(*P["acc"][m]))} for m in panel_p],
                     "flagged": flagged77, "reproduces_77": repro77},
        "join": {"counts": jcounts, "same_key": len(J), "different_key": n_diff_key,
                 "same_key_no_virology": len(keep_x)},
        "p1_parts": p1_parts,
        "predictions": verdicts,
        "by_group": by_group,
        "precision": precision,
        "flagged": flagged_counts,
        "by_subject_exploratory": by_subject,
        "n_candidates": len(candidates),
        "note": ("J = MMLU-derived MMLU-Pro questions joined one-to-one to a HELM MMLU question (same subject and "
                 "normalised question text, at least 3 shared option texts) whose two keys have the same option "
                 "text. HELM flag = audit 80's; Pro flag = audit 77's; agree = both flag and their consensus options "
                 "have the same text. Precision = share of flagged Redux-judged questions (wrong key, OK or another "
                 "error label) that carry an error label. P1 structural; P2 HEADLINE agree precision > HELM's on J; "
                 "P3 agree precision > Pro's on J; P4 agree keeps >= half of HELM-flagged Redux miskeys in J; P5 "
                 "Redux-OK retention <= half of miskey retention; P6 P2 without virology."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "agree_candidates.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 81, "note": ("Model-flagged, NOT expert-checked: MMLU questions where HELM's 10 most "
                   "accurate models (at least 6 of 10) and TIGER-AI-Lab's 10 most accurate MMLU-Pro archives (at least "
                   "6 of 10) both pick the same answer text other than the key. *_votes = [consensus, key, no valid "
                   "answer] out of 10. Each may hold a wrong key, a second defensible answer or a mistake the models "
                   "share."), "candidates": candidates}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and agree_candidates.json (%d candidates)" % len(candidates))


if __name__ == "__main__":
    main()
