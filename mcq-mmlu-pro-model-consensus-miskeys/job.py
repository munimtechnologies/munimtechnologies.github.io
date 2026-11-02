"""Model-consensus miskey flags for all of MMLU-Pro, validated against MMLU-Redux 2.0's experts (audit 77).

Reads every per-question prediction archive audit 66 listed from TIGER-AI-Lab's MMLU-Pro eval_results, joins each
record to the HF test row by question_id with identical stripped options and answer (audits 65/66/76 rule), picks
the PANEL_SIZE most accurate included models, and flags each of the 12,032 questions where at least MIN_AGREE panel
models pick the same non-key option and more of them pick it than the key. The flag is validated on the MMLU-Pro
questions MMLU-Redux 2.0's experts labelled (audit 75's join, re-run here and gated to reproduce its counts and its
55 miskey ids) and applied to the rest.

Gates before any prediction is scored: both hand-traced fixtures match; the HF parse reproduces audit 63's row and
family counts; the Redux join reproduces audit 75. Writes results.json (aggregates) and candidates.json (every flagged
question: id, source, category, key and consensus letters, vote counts, Redux status; no question, option or model
text). Usage: python job.py --out-dir /out   (network required). Apache-2.0.
"""

import argparse
import hashlib
import io
import json
import os
import urllib.parse
import urllib.request
import zipfile

import pyarrow.parquet as pq

import cases77 as C
import consensus77 as cm

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
    """Rows (dicts of spec cols) from the spec's config and splits, plus shard sha256s."""
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
    """MMLU-Redux 2.0, all 57 configs (as audit 75)."""
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
                         "answer": int(a) if a is not None else None, "label": cm.label_of(et), "correct": ca})
    return rows, shards


def family(src):
    s = src or ""
    return s.split("-", 1)[0] if s else "unknown"


def records_from_zip(blob):
    """Prediction records from every .json member (same reader as audits 65/66/76)."""
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
    """'ok' | 'no_id' | 'options_differ' | 'answer_differ' (as audits 65/66/76)."""
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
    panel = cm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
    flags, _t = cm.panel_flags(panel, C.FIX_PREDS, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
    g = cm.groups(C.FIX_QUESTIONS.keys(), C.FIX_FAMILY, C.FIX_LABELS, C.FIX_AMBIGUOUS)
    verdicts = cm.predictions(g, flags, C.FIX_TARGETS, C.THRESHOLDS)
    labels, amb, mk, counts = cm.redux_labels(C.FIX_REDUX, C.FIX_MMLU, C.FIX_PRO)
    t = C.FIX_REDUX_TARGET
    return {"panel": panel == C.FIX_TARGET["panel"], "flags": flags == C.FIX_TARGET["flags"],
            "verdicts": verdicts == C.FIX_TARGET["verdicts"],
            "redux_join": (labels == t["labels"] and amb == t["ambiguous_ids"] and mk == t["miskey_ids"]
                           and counts == t["counts"])}


def letter(i):
    return None if i is None else cm.LETTERS[i]


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

    # MMLU-Pro
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

    # MMLU-Redux labels on MMLU-Pro (audit 75's join, gated)
    mmlu, mmlu_shards = read_spec(C.MMLU)
    redux, redux_shards = read_redux()
    labels, amb_ids, miskey_ids, rcounts = cm.redux_labels(redux, mmlu, raw_pro)
    redux_ok = (rcounts["redux_mmlu"]["joined"] == C.EXPECTED_REDUX["joined"]
                and rcounts["pro_join"]["in_pro"] == C.EXPECTED_REDUX["in_pro"]
                and rcounts["pro_join"]["ambiguous_pro"] == C.EXPECTED_REDUX["ambiguous_pro"]
                and set(miskey_ids) == set(C.MISKEY_IDS))
    label_n = {}
    for lab in labels.values():
        label_n[lab] = label_n.get(lab, 0) + 1
    print("[redux] %s miskey_ids=%d (match audit 75: %s) labels=%s ok=%s"
          % (rcounts, len(miskey_ids), set(miskey_ids) == set(C.MISKEY_IDS), dict(sorted(label_n.items())),
             redux_ok))
    if not redux_ok:
        raise SystemExit("Redux join does not reproduce audit 75 -- aborting")

    # Audit 76's targets, still keyed as before
    targets, target_meta = {}, {}
    for qid, src, key, exp, basis in C.TARGETS:
        r = hf_by_id.get(qid)
        key_i, exp_i = cm.LETTERS.index(key), cm.LETTERS.index(exp)
        if r is None or r["src"] != src or r["answer_index"] != key_i or exp_i >= len(r["options"]):
            continue
        targets[qid] = exp_i
        target_meta[qid] = (basis, src)
    print("[targets] still keyed as audit 75/76: %d of %d" % (len(targets), len(C.TARGETS)))

    # Archives
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
            print("[archive] %-44s excluded: join_share=%.4f coverage=%.4f" % (model, join_share, coverage))
            continue
        correct = 0
        for qid, p in joined.items():
            r = hf_by_id[qid]
            i = cm.pred_index(p, len(r["options"]))
            correct += 1 if (i is not None and i == r["answer_index"]) else 0
        preds[model] = joined
        acc[model] = (correct, len(joined))
        archives[model]["accuracy"] = correct / len(joined)
        print("[model] %-40s joined=%d accuracy=%.4f" % (model, len(joined), correct / len(joined)))

    panel = cm.select_panel(acc, C.PANEL_SIZE)
    print("[panel] %s" % [(m, round(acc[m][0] / acc[m][1], 4)) for m in panel])
    questions = {q: (len(r["options"]), r["answer_index"]) for q, r in hf_by_id.items()}
    flags, tallies = cm.panel_flags(panel, preds, questions, C.MIN_AGREE)
    included = sorted(preds)
    _af, all_tallies = cm.panel_flags(included, preds, questions, C.MIN_AGREE)
    g = cm.groups(questions.keys(), fam_of, labels, amb_ids)
    verdicts = cm.predictions(g, flags, targets, C.THRESHOLDS)
    p1 = (all(fx.values()) and struct_ok and redux_ok and len(preds) >= C.MIN_INCLUDED_ARCHIVES
          and len(panel) == C.PANEL_SIZE)
    verdicts["P1_structural"] = p1
    verdicts["P1_counts"] = [len(preds), len(C.ARCHIVES), len(panel), len(targets)]
    for name in sorted(v for v in verdicts if not v.endswith("_counts")):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    print("[prediction] counts %s" % {k: v for k, v in sorted(verdicts.items()) if k.endswith("_counts")})

    by_group = {name: {"flagged": cm.n_flagged(ids, flags), "n": len(ids)} for name, ids in sorted(g.items())}
    print("[groups] %s" % {k: (v["flagged"], v["n"]) for k, v in by_group.items()})
    by_category = {}
    for q, r in hf_by_id.items():
        c = by_category.setdefault(r["category"], {"flagged": 0, "n": 0})
        c["n"] += 1
        c["flagged"] += 1 if flags[q][0] else 0
    keys = {q: kk[1] for q, kk in questions.items()}
    curve_rows = cm.curve(tallies, keys, g, C.CURVE_MS)
    for row in curve_rows:
        print("[curve] m=%d miskey=%s ok=%s other_error=%s unreviewed=%s all=%s"
              % (row["min_agree"], row["miskey"], row["ok"], row["other_error"], row["unreviewed_ori_mmlu"],
                 row["all"]))

    def status_of(q):
        lab = labels.get(q)
        if lab is not None:
            return lab
        if fam_of[q] == "ori_mmlu":
            return "ambiguous" if q in amb_ids else "not_reviewed"
        return "not_from_mmlu"

    def row_for(q):
        r = hf_by_id[q]
        k, key_i = questions[q]
        pc, pn = tallies[q]
        ac, an = all_tallies[q]
        ci = flags[q][1]
        return {"question_id": q, "src": r["src"], "category": r["category"], "k": k,
                "key": letter(key_i), "consensus": letter(ci), "flagged": bool(flags[q][0]),
                "panel_consensus": pc[ci] if ci is not None else None, "panel_key": pc[key_i], "panel_none": pn,
                "all_consensus": ac[ci] if ci is not None else None, "all_key": ac[key_i], "all_none": an,
                "all_models": len(included), "redux": status_of(q)}

    candidates = [row_for(q) for q in sorted(q for q in questions if flags[q][0])]
    per_target = []
    for q in sorted(targets):
        d = row_for(q)
        d.update({"expert": letter(targets[q]), "basis": target_meta[q][0],
                  "panel_expert": tallies[q][0][targets[q]], "consensus_is_expert": flags[q][1] == targets[q]})
        per_target.append(d)
    external = [row_for(q) for q in C.EXTERNAL_IDS if q in hf_by_id]

    out = {
        "audit": 77,
        "slug": "mcq-mmlu-pro-model-consensus-miskeys",
        "dataset": ("MMLU-Pro (TIGER-Lab/MMLU-Pro 'default' test), MMLU (cais/mmlu 'all' test) and MMLU-Redux 2.0 "
                    "(edinburgh-dawg/mmlu-redux-2.0, 57 configs) via the HF datasets-server parquet API; per-question "
                    "predictions from github.com/TIGER-AI-Lab/MMLU-Pro eval_results (raw, main; sha256 recorded). "
                    "Only ids, letters and counts are written."),
        "rule": {"panel_size": C.PANEL_SIZE, "min_agree": C.MIN_AGREE,
                 "thresholds": {k: str(v) for k, v in C.THRESHOLDS.items()}},
        "fixture": fx,
        "structural": {"n": len(rows), "family_n": fam_n, "shards": pro_shards},
        "redux_join": {"counts": rcounts, "miskey_ids_match_audit_75": set(miskey_ids) == set(C.MISKEY_IDS),
                       "labels_on_pro": dict(sorted(label_n.items())), "ambiguous_ids": len(amb_ids),
                       "mmlu_shards": mmlu_shards, "redux_shards": redux_shards},
        "archives": archives,
        "panel": [{"model": m, "accuracy": acc[m][0] / acc[m][1], "joined": acc[m][1]} for m in panel],
        "groups": by_group,
        "by_category": dict(sorted(by_category.items())),
        "curve_exploratory": curve_rows,
        "per_target": per_target,
        "external_exploratory": external,
        "n_candidates": len(candidates),
        "predictions": verdicts,
        "note": ("FLAG: >= %d of the %d most accurate included models pick the same non-key option, and more of them "
                 "pick it than the key. P1 structural (fixtures, MMLU-Pro 12,032 rows and audit 63 families, Redux join "
                 "reproduces audit 75: 5,690 joined, 2,758 single and 71 ambiguous MMLU-Pro matches, the same 55 "
                 "miskey ids; >= 30 archives included; panel of 10). P2 HEADLINE: flag rate on Redux-miskeyed >= 5x "
                 "that on Redux-OK questions. P3: >= 40%% of audit 76's 46 targets flagged and the consensus is the "
                 "experts' answer on >= 80%% of those. P4: >= 20%% of flagged Redux-judged questions carry a Redux "
                 "error label. P5: flag rate on MMLU-derived questions Redux never reviewed > on Redux-OK. P6: flag "
                 "rate on STEM-website questions > on MMLU-derived questions." % (C.MIN_AGREE, C.PANEL_SIZE)),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "candidates.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 77, "rule": out["rule"], "note": ("Model-flagged, NOT expert-checked: each entry is an "
                   "MMLU-Pro question where the panel of published models agrees on one non-key option. 'redux' is "
                   "MMLU-Redux 2.0's expert label where it exists."), "candidates": candidates},
                  fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and candidates.json (%d candidates)" % len(candidates))


if __name__ == "__main__":
    main()
