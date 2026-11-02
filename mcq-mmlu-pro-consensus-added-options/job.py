"""Do MMLU-Pro's model-consensus flags point at options MMLU-Pro added? (audit 78)

Re-runs audit 77's panel and flag on TIGER-AI-Lab's published per-question predictions (gated to reproduce audit 77's
panel and flag counts), joins every MMLU test row to MMLU-Pro with audit 75's pool rule, labels each option of a
mapped MMLU-derived question ORIGINAL (one of MMLU's four choices) or ADDED, and counts, for flagged questions, whether
the consensus option is original or added, against the panel's non-key picks on unflagged questions.

Gates before any prediction is scored: all four hand-traced fixtures match; the HF parse reproduces audit 63's row and
family counts; the Redux join reproduces audit 75. Writes results.json (aggregates) and added_candidates.json (flagged
MMLU-derived questions whose consensus option was added by MMLU-Pro: id, source, category, letters, vote counts, Redux
status; no question, option or model text). Usage: python job.py --out-dir /out   (network required). Apache-2.0.
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

import added78 as am
import cases78 as C

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
                         "answer": int(a) if a is not None else None, "label": am.label_of(et), "correct": ca})
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
        if str(rec["answer"]).strip().upper() != am.LETTERS[q["answer_index"]]:
            return "answer_differ"
    return "ok"


def fixture_ok():
    panel = am.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
    flags, _t = am.panel_flags(panel, C.FIX_PREDS, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
    labels, amb, mk, counts = am.redux_labels(C.FIX_REDUX, C.FIX_MMLU, C.FIX_PRO)
    t = C.FIX_REDUX_TARGET
    mapping, mcounts = am.map_mmlu_to_pro(C.FIX_MAP_MMLU, C.FIX_MAP_PRO)
    o1 = am.origins(C.FIX_MAP_PRO[0]["options"], mapping.get(1, ()))
    verdicts = am.predictions78(C.FIX_G, C.FIX_FLAGS, C.FIX_TALLIES, C.FIX_KEYS, C.FIX_ORIGIN, C.FIX_CATEGORY,
                                C.THRESHOLDS)
    return {"panel_flags": panel == C.FIX_TARGET["panel"] and flags == C.FIX_TARGET["flags"],
            "redux_join": (labels == t["labels"] and amb == t["ambiguous_ids"] and mk == t["miskey_ids"]
                           and counts == t["counts"]),
            "map_origins": (mapping == C.FIX_MAP_TARGET["mapping"] and mcounts == C.FIX_MAP_TARGET["counts"]
                            and o1 == C.FIX_MAP_TARGET["origins_1"]),
            "verdicts": verdicts == C.FIX_VERDICTS}


def letter(i):
    return None if i is None else am.LETTERS[i]


def share(a, n):
    return float(Fraction(a, n)) if n else None


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
    category = {q: r["category"] for q, r in hf_by_id.items()}

    mmlu, mmlu_shards = read_spec(C.MMLU)
    redux, redux_shards = read_redux()
    labels, amb_ids, miskey_ids, rcounts = am.redux_labels(redux, mmlu, raw_pro)
    redux_ok = (rcounts["redux_mmlu"]["joined"] == C.EXPECTED_REDUX["joined"]
                and rcounts["pro_join"]["in_pro"] == C.EXPECTED_REDUX["in_pro"]
                and rcounts["pro_join"]["ambiguous_pro"] == C.EXPECTED_REDUX["ambiguous_pro"]
                and len(miskey_ids) == C.N_MISKEY_IDS)
    print("[redux] %s miskey_ids=%d ok=%s" % (rcounts, len(miskey_ids), redux_ok))
    if not redux_ok:
        raise SystemExit("Redux join does not reproduce audit 75 -- aborting")

    # MMLU -> MMLU-Pro map and option origins (MMLU-derived questions only)
    mapping, mcounts = am.map_mmlu_to_pro(mmlu, raw_pro)
    origin_by_q, mapped_ori, intact_n = {}, 0, 0
    for q, choices in mapping.items():
        if q not in hf_by_id or fam_of[q] != "ori_mmlu":
            continue
        mapped_ori += 1
        orig, intact = am.origins(hf_by_id[q]["options"], choices)
        if intact:
            intact_n += 1
            origin_by_q[q] = orig
    map_ok = mapped_ori >= C.MIN_MAPPED and mapped_ori and Fraction(intact_n, mapped_ori) >= C.MIN_INTACT_SHARE
    print("[map] mmlu_rows=%s mapped_ori_mmlu=%d intact=%d ok=%s" % (mcounts, mapped_ori, intact_n, bool(map_ok)))

    # Archives (as audit 77)
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
            i = am.pred_index(p, len(r["options"]))
            correct += 1 if (i is not None and i == r["answer_index"]) else 0
        preds[model] = joined
        acc[model] = (correct, len(joined))
        archives[model]["accuracy"] = correct / len(joined)

    panel = am.select_panel(acc, C.PANEL_SIZE)
    print("[panel] %s" % panel)
    questions = {q: (len(r["options"]), r["answer_index"]) for q, r in hf_by_id.items()}
    keys = {q: kk[1] for q, kk in questions.items()}
    flags, tallies = am.panel_flags(panel, preds, questions, C.MIN_AGREE)
    g = am.groups(questions.keys(), fam_of, labels, amb_ids)
    flagged77 = {name: am.n_flagged(g[name], flags) for name in C.EXPECTED_77_FLAGGED}
    repro_ok = panel == C.EXPECTED_PANEL and flagged77 == C.EXPECTED_77_FLAGGED
    print("[repro77] panel_match=%s flagged=%s ok=%s" % (panel == C.EXPECTED_PANEL, flagged77, repro_ok))

    verdicts = am.predictions78(g, flags, tallies, keys, origin_by_q, category, C.THRESHOLDS)
    p1 = bool(all(fx.values()) and struct_ok and redux_ok and map_ok and repro_ok
              and len(preds) >= C.MIN_INCLUDED_ARCHIVES)
    verdicts["P1_structural"] = p1
    verdicts["P1_counts"] = [mapped_ori, intact_n, len(preds), sum(flagged77.values())]
    for name in sorted(v for v in verdicts if not v.endswith("_counts")):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    print("[prediction] counts %s" % {k: v for k, v in sorted(verdicts.items()) if k.endswith("_counts")})

    # Exploratory
    by_group = {}
    for name in ("miskey", "ok", "other_error", "unsure_or_conflict", "unreviewed_ori_mmlu", "ambiguous_ori_mmlu",
                 "ori_mmlu"):
        ids = g[name]
        o, a = am.consensus_origin(flags, origin_by_q, ids)
        wo, wa = am.wrong_pick_origin(tallies, keys, flags, origin_by_q, ids)
        by_group[name] = {"n": len(ids), "intact": sum(1 for q in ids if q in origin_by_q),
                          "flagged_intact": o + a, "consensus_original": o, "consensus_added": a,
                          "added_share": share(a, o + a), "unflagged_wrong_picks_original": wo,
                          "unflagged_wrong_picks_added": wa, "unflagged_wrong_pick_added_share": share(wa, wo + wa)}
        print("[group] %s %s" % (name, by_group[name]))
    nonkey = added_nonkey = 0
    for q, orig in origin_by_q.items():
        for i, o in enumerate(orig):
            if i != keys[q]:
                nonkey += 1
                added_nonkey += 1 if o == am.ADDED else 0
    print("[options] intact questions=%d non-key options=%d added=%d" % (len(origin_by_q), nonkey, added_nonkey))
    by_category = {}
    for q in g["ori_mmlu"]:
        if not flags[q][0] or q not in origin_by_q:
            continue
        c = by_category.setdefault(category[q], {"original": 0, "added": 0})
        c["added" if origin_by_q[q][flags[q][1]] == am.ADDED else "original"] += 1
    curve = []
    for m in range(4, 11):
        fl = {q: am.flag_question(tallies[q][0], keys[q], m)[:2] for q in tallies}
        row = {"min_agree": m}
        for name in ("miskey", "ok", "unreviewed_ori_mmlu"):
            row[name] = list(am.consensus_origin(fl, origin_by_q, g[name]))
        curve.append(row)
        print("[curve] %s" % row)

    def status_of(q):
        lab = labels.get(q)
        if lab is not None:
            return lab
        return "ambiguous" if q in amb_ids else "not_reviewed"

    def row_for(q):
        r = hf_by_id[q]
        pc, pn = tallies[q]
        ci = flags[q][1]
        return {"question_id": q, "src": r["src"], "category": r["category"], "k": len(r["options"]),
                "key": letter(keys[q]), "consensus": letter(ci), "flagged": bool(flags[q][0]),
                "panel_consensus": pc[ci] if ci is not None else None, "panel_key": pc[keys[q]], "panel_none": pn,
                "consensus_origin": (origin_by_q[q][ci] if (q in origin_by_q and ci is not None) else None),
                "n_added_options": (sum(1 for o in origin_by_q[q] if o == am.ADDED) if q in origin_by_q else None),
                "redux": status_of(q)}

    candidates = [row_for(q) for q in g["ori_mmlu"]
                  if flags[q][0] and q in origin_by_q and origin_by_q[q][flags[q][1]] == am.ADDED]
    external = [row_for(q) for q in C.EXTERNAL_IDS if q in hf_by_id]
    for e in external:
        print("[external] %s" % e)

    out = {
        "audit": 78,
        "slug": "mcq-mmlu-pro-consensus-added-options",
        "dataset": ("MMLU-Pro (TIGER-Lab/MMLU-Pro 'default' test), MMLU (cais/mmlu 'all' test) and MMLU-Redux 2.0 "
                    "via the HF datasets-server parquet API; per-question predictions from "
                    "github.com/TIGER-AI-Lab/MMLU-Pro eval_results (sha256 recorded). Only ids, letters and counts."),
        "fixture": fx,
        "structural": {"n": len(rows), "family_n": fam_n, "shards": pro_shards},
        "redux_join": {"counts": rcounts, "n_miskey_ids": len(miskey_ids), "mmlu_shards": mmlu_shards,
                       "redux_shards": redux_shards},
        "map": {"mmlu_rows": mcounts, "mapped_ori_mmlu": mapped_ori, "intact": intact_n,
                "intact_nonkey_options": nonkey, "intact_added_nonkey_options": added_nonkey},
        "archives": archives,
        "panel": panel,
        "reproduce_77": {"panel_match": panel == C.EXPECTED_PANEL, "flagged": flagged77, "ok": repro_ok},
        "by_group": by_group,
        "by_category_flagged_ori_mmlu": dict(sorted(by_category.items())),
        "curve_exploratory": curve,
        "external_exploratory": external,
        "n_added_candidates": len(candidates),
        "predictions": verdicts,
        "note": ("ORIGINAL = the option's normalised text is one of MMLU's four choices; ADDED = it is not. Only "
                 "intact questions (all four MMLU choices among MMLU-Pro's options) are classified. P1 structural "
                 "(fixtures, MMLU-Pro 12,032 rows, Redux join reproduces audit 75, >= 6,000 MMLU-derived questions "
                 "mapped and >= 85% of them intact, audit 77's panel and flag counts reproduced). P2 control: >= 80% "
                 "of flagged Redux-miskeyed consensus options are original. P3: >= 50% of flagged Redux-OK consensus "
                 "options are added. P4 HEADLINE: the added share among flagged Redux-OK consensus options exceeds the "
                 "added share among the panel's non-key picks on unflagged MMLU-derived questions. P5: the added "
                 "share among flagged law questions exceeds that among flagged questions in other categories."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "added_candidates.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 78, "note": ("Model-flagged, NOT expert-checked: MMLU-derived MMLU-Pro questions where "
                   "at least 6 of the 10 panel models agree on one non-key option that MMLU-Pro added (not one of "
                   "MMLU's four). Each may hold a second defensible answer, a shared model mistake, or a wrong key."),
                   "candidates": candidates}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and added_candidates.json (%d candidates)" % len(candidates))


if __name__ == "__main__":
    main()
