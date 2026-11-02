"""Does audit 77's model-consensus flag change with one archive per model line? (audit 79)

Re-runs audit 77's panel and flag on TIGER-AI-Lab's published per-question predictions (gated to reproduce audit 77's
panel and flag counts), builds a second panel of the 10 most accurate archives with at most one archive per model
line, applies the same flag, scores both panels against MMLU-Redux 2.0's expert labels (audit 75's join), and
measures how often two archives give the same wrong answer, within a model line and across lines.

Gates before any prediction is scored: all five hand-traced fixtures match; the HF parse reproduces audit 63's row
and family counts; the Redux join reproduces audit 75. Writes results.json (aggregates, per-pair rates, curve) and
robust_candidates.json (questions both panels flag with the same consensus option: id, source, category, letters,
vote counts, Redux status; no question, option or model text). Usage: python job.py --out-dir /out (network
required). Apache-2.0.
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

import distinct79 as dm
import cases79 as C

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
                         "answer": int(a) if a is not None else None, "label": dm.label_of(et), "correct": ca})
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
        if str(rec["answer"]).strip().upper() != dm.LETTERS[q["answer_index"]]:
            return "answer_differ"
    return "ok"


def fixture_ok():
    panel = dm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
    flags, _t = dm.panel_flags(panel, C.FIX_PREDS, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
    labels, amb, mk, counts = dm.redux_labels(C.FIX_REDUX, C.FIX_MMLU, C.FIX_PRO)
    t = C.FIX_REDUX_TARGET
    dpanel = dm.select_distinct_panel(C.FIX_D_ACC, C.FIX_D_SIZE, C.FIX_D_LINES)
    within, cross = dm.pair_rates(["a1", "a2", "b1"], C.FIX_W_PREDS, C.FIX_W_QUESTIONS, C.FIX_D_LINES)
    verdicts = dm.predictions79(C.FIX_G, C.FIX_FLAGS_A, C.FIX_FLAGS_D, within, cross, C.THRESHOLDS)
    return {"panel_flags": panel == C.FIX_TARGET["panel"] and flags == C.FIX_TARGET["flags"],
            "redux_join": (labels == t["labels"] and amb == t["ambiguous_ids"] and mk == t["miskey_ids"]
                           and counts == t["counts"]),
            "distinct_panel": dpanel == C.FIX_D_TARGET,
            "wrong_agreement": within == C.FIX_W_TARGET["within"] and cross == C.FIX_W_TARGET["cross"],
            "verdicts": verdicts == C.FIX_VERDICTS}


def letter(i):
    return None if i is None else dm.LETTERS[i]


def share(a, n):
    return float(Fraction(a, n)) if n else None


GROUP_NAMES = ("all", "miskey", "ok", "other_error", "unsure_or_conflict", "unreviewed_ori_mmlu", "ori_mmlu",
               "stemez", "theoremQA", "scibench")


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
    labels, amb_ids, miskey_ids, rcounts = dm.redux_labels(redux, mmlu, raw_pro)
    del mmlu, redux
    redux_ok = (rcounts["redux_mmlu"]["joined"] == C.EXPECTED_REDUX["joined"]
                and rcounts["pro_join"]["in_pro"] == C.EXPECTED_REDUX["in_pro"]
                and rcounts["pro_join"]["ambiguous_pro"] == C.EXPECTED_REDUX["ambiguous_pro"]
                and len(miskey_ids) == C.N_MISKEY_IDS)
    print("[redux] %s miskey_ids=%d ok=%s" % (rcounts, len(miskey_ids), redux_ok))
    if not redux_ok:
        raise SystemExit("Redux join does not reproduce audit 75 -- aborting")

    # Archives (as audits 77 and 78)
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
                           "line": dm.line_of(model, C.LINES),
                           "status": "included" if ok else "excluded_join"}
        if not ok:
            print("[archive] %-44s excluded" % model)
            continue
        correct = 0
        for qid, p in joined.items():
            r = hf_by_id[qid]
            i = dm.pred_index(p, len(r["options"]))
            correct += 1 if (i is not None and i == r["answer_index"]) else 0
        preds[model] = joined
        acc[model] = (correct, len(joined))
        archives[model]["accuracy"] = correct / len(joined)

    questions = {q: (len(r["options"]), r["answer_index"]) for q, r in hf_by_id.items()}
    keys = {q: kk[1] for q, kk in questions.items()}
    g = dm.groups(questions.keys(), fam_of, labels, amb_ids)

    panel_a = dm.select_panel(acc, C.PANEL_SIZE)
    flags_a, tallies_a = dm.panel_flags(panel_a, preds, questions, C.MIN_AGREE)
    flagged77 = {name: dm.n_flagged(g[name], flags_a) for name in C.EXPECTED_77_FLAGGED}
    prec_a = dm.flag_precision(flags_a, g)
    repro_ok = (panel_a == C.EXPECTED_PANEL and flagged77 == C.EXPECTED_77_FLAGGED
                and prec_a == C.EXPECTED_77_PRECISION)
    print("[repro77] panel_match=%s flagged=%s precision=%s ok=%s"
          % (panel_a == C.EXPECTED_PANEL, flagged77, prec_a, repro_ok))

    panel_d = dm.select_distinct_panel(acc, C.PANEL_SIZE, C.LINES)
    distinct_ok = panel_d == C.EXPECTED_DISTINCT_PANEL
    print("[panel_d] %s match=%s" % (panel_d, distinct_ok))
    flags_d, tallies_d = dm.panel_flags(panel_d, preds, questions, C.MIN_AGREE)

    union = sorted(set(panel_a) | set(panel_d))
    within, cross = dm.pair_rates(union, preds, questions, C.LINES)

    verdicts = dm.predictions79(g, flags_a, flags_d, within, cross, C.THRESHOLDS)
    p1 = bool(all(fx.values()) and struct_ok and redux_ok and repro_ok and distinct_ok
              and len(preds) >= C.MIN_INCLUDED_ARCHIVES)
    verdicts["P1_structural"] = p1
    verdicts["P1_counts"] = [len(preds), len(panel_d), len({dm.line_of(m, C.LINES) for m in panel_d}), len(union)]
    for name in sorted(v for v in verdicts if not v.endswith("_counts")):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    print("[prediction] counts %s" % {k: v for k, v in sorted(verdicts.items()) if k.endswith("_counts")})

    # Exploratory
    by_group = {}
    for name in GROUP_NAMES:
        ids = g[name]
        fa, fd = dm.n_flagged(ids, flags_a), dm.n_flagged(ids, flags_d)
        both = sum(1 for q in ids if flags_a[q][0] and flags_d[q][0])
        same = sum(1 for q in ids if flags_a[q][0] and flags_d[q][0] and flags_a[q][1] == flags_d[q][1])
        by_group[name] = {"n": len(ids), "flagged_77_panel": fa, "flagged_distinct": fd, "flagged_both": both,
                          "flagged_both_same_option": same, "rate_77_panel": share(fa, len(ids)),
                          "rate_distinct": share(fd, len(ids))}
        print("[group] %s %s" % (name, by_group[name]))
    prec = {}
    for label, fl in (("panel_77", flags_a), ("distinct", flags_d)):
        e, j = dm.flag_precision(fl, g)
        prec[label] = {"error_labelled": e, "judged": j, "share": share(e, j)}
    inter = {q: (flags_a[q][0] and flags_d[q][0] and flags_a[q][1] == flags_d[q][1], flags_a[q][1])
             for q in questions}
    e, j = dm.flag_precision(inter, g)
    prec["both_same_option"] = {"error_labelled": e, "judged": j, "share": share(e, j)}
    print("[precision] %s" % prec)

    curve = []
    for m in range(4, 11):
        fl = {q: dm.flag_question(tallies_d[q][0], keys[q], m)[:2] for q in tallies_d}
        e, j = dm.flag_precision(fl, g)
        row = {"min_agree": m, "flagged": dm.n_flagged(g["all"], fl), "miskey": dm.n_flagged(g["miskey"], fl),
               "ok": dm.n_flagged(g["ok"], fl), "error_labelled": e, "judged": j,
               "unreviewed_ori_mmlu": dm.n_flagged(g["unreviewed_ori_mmlu"], fl)}
        curve.append(row)
        print("[curve_distinct] %s" % row)

    pairs = []
    for kind, d in (("within", within), ("cross", cross)):
        for key in sorted(d):
            a, b = key.split("|")
            same, both, r = d[key]
            pairs.append({"pair": key, "kind": kind, "line_a": dm.line_of(a, C.LINES),
                          "line_b": dm.line_of(b, C.LINES), "same_wrong": same, "both_wrong": both,
                          "rate": float(r), "acc_a": float(dm.accuracy(*acc[a])),
                          "acc_b": float(dm.accuracy(*acc[b]))})
    for p in pairs:
        if p["kind"] == "within":
            print("[pair] %s" % p)

    def status_of(q):
        lab = labels.get(q)
        if lab is not None:
            return lab
        return "ambiguous" if q in amb_ids else "not_reviewed"

    robust = []
    for q in sorted(questions):
        if not inter[q][0]:
            continue
        r = hf_by_id[q]
        ci = flags_a[q][1]
        ca, cd = tallies_a[q][0], tallies_d[q][0]
        robust.append({"question_id": q, "src": r["src"], "category": r["category"], "k": len(r["options"]),
                       "key": letter(keys[q]), "consensus": letter(ci),
                       "votes_77_panel": [ca[ci], ca[keys[q]], tallies_a[q][1]],
                       "votes_distinct": [cd[ci], cd[keys[q]], tallies_d[q][1]],
                       "redux": status_of(q)})

    out = {
        "audit": 79,
        "slug": "mcq-mmlu-pro-consensus-distinct-panel",
        "dataset": ("MMLU-Pro (TIGER-Lab/MMLU-Pro 'default' test), MMLU (cais/mmlu 'all' test) and MMLU-Redux 2.0 "
                    "via the HF datasets-server parquet API; per-question predictions from "
                    "github.com/TIGER-AI-Lab/MMLU-Pro eval_results (sha256 recorded). Only ids, letters and counts."),
        "fixture": fx,
        "structural": {"n": len(rows), "family_n": fam_n, "shards": pro_shards},
        "redux_join": {"counts": rcounts, "n_miskey_ids": len(miskey_ids), "mmlu_shards": mmlu_shards,
                       "redux_shards": redux_shards},
        "archives": archives,
        "lines": C.LINES,
        "panel_77": panel_a,
        "panel_distinct": panel_d,
        "reproduce_77": {"panel_match": panel_a == C.EXPECTED_PANEL, "flagged": flagged77,
                         "precision": list(prec_a), "ok": repro_ok},
        "distinct_panel_match": distinct_ok,
        "by_group": by_group,
        "precision": prec,
        "curve_distinct_exploratory": curve,
        "pairs": pairs,
        "n_robust_candidates": len(robust),
        "predictions": verdicts,
        "note": ("Panel 77 = the 10 most accurate included archives (audit 77). Distinct panel = the 10 most "
                 "accurate with at most one archive per model line (cases79.LINES; every unlisted archive is its "
                 "own line). Flag: at least 6 of 10 pick one non-key option and more than pick the key. Precision = "
                 "share of flagged Redux-judged questions (wrong key, OK or another error label) that carry an "
                 "error label. Shared-wrong-answer rate = among questions where both archives give a valid non-key "
                 "answer, the share where they give the same one. P1 structural (fixtures, 12,032 rows, Redux join, "
                 "audit 77 reproduced incl. 65/359 precision, distinct panel as frozen, >= 30 archives). P2: the "
                 "distinct panel's Redux-miskey flag rate >= 5x its Redux-OK rate. P3 HEADLINE: its precision is "
                 "higher than panel 77's 65/359. P4: it flags >= 30 of the 55 Redux miskeys. P5: every within-line "
                 "pair's shared-wrong-answer rate exceeds the median cross-line pair among the union of both "
                 "panels. P6: it flags STEM-website questions at a lower rate than MMLU-derived ones."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "robust_candidates.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 79, "note": ("Model-flagged, NOT expert-checked: MMLU-Pro questions flagged by both "
                   "audit 77's panel and the one-archive-per-line panel, with the same consensus option. votes_* = "
                   "[consensus, key, no valid answer] out of 10. Each may hold a wrong key, a second defensible "
                   "answer or a shared model mistake."), "candidates": robust}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and robust_candidates.json (%d candidates)" % len(robust))


if __name__ == "__main__":
    main()
