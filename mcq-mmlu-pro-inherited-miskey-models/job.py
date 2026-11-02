"""Do published models pick the experts' answer on MMLU-Pro's inherited MMLU miskeys? (audit 76)

Reads every per-question prediction archive TIGER-AI-Lab publishes for MMLU-Pro (the 48 audit 66 listed), joins
each record to the HF test row by question_id with identical stripped options and answer (audits 65/66 rule), and on
the 46 target questions from audit 75 counts picks of the published KEY, the EXPERTS' answer, another option and
no valid answer. Control: each model's accuracy on MMLU-derived questions other than the 55 Redux miskeys.

Gates before any prediction is scored: the hand-traced fixture matches; the HF parse reproduces audit 63's row and
family counts; the frozen target list has 46 rows (24 primary) and 55 miskey ids. Only ids, letters and counts are
written. Usage: python job.py --out-dir /out   (network required). Apache-2.0.
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

import cases76 as C
import inherit_models as im

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


def read_columns(spec):
    data = json.loads(_get(PARQUET_API % spec["hf"]).decode("utf-8"))
    files = sorted((f["split"], f["url"]) for f in data["parquet_files"]
                   if f["config"] == spec["config"] and f["split"] in set(spec["splits"]))
    rows, shards = [], []
    for split, url in files:
        blob = _get(url)
        shards.append({"split": split, "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob)})
        table = pq.read_table(io.BytesIO(blob), columns=spec["cols"])
        cols = {c: table.column(c).to_pylist() for c in spec["cols"]}
        for i in range(len(cols[spec["cols"][0]])):
            rows.append({c: cols[c][i] for c in spec["cols"]})
    return rows, shards


def family(src):
    s = src or ""
    return s.split("-", 1)[0] if s else "unknown"


def records_from_zip(blob):
    """Prediction records from every .json member (same reader as audits 65/66)."""
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
    """'ok' | 'no_id' | 'options_differ' | 'answer_differ' (as audits 65/66)."""
    q = hf_by_id.get(_qid(rec.get("question_id")))
    if q is None:
        return "no_id"
    if _norm_options(rec.get("options")) != _norm_options(q["options"]):
        return "options_differ"
    if "answer_index" in rec and rec["answer_index"] is not None:
        if _qid(rec["answer_index"]) != q["answer_index"]:
            return "answer_differ"
    elif "answer" in rec and rec["answer"] is not None:
        if str(rec["answer"]).strip().upper() != im.LETTERS[q["answer_index"]]:
            return "answer_differ"
    return "ok"


def fixture_ok():
    models, per_q = {}, {}
    for m, q, pred in C.FIX_PREDS:
        k, key_i, exp_i, basis = C.FIX_QUESTIONS[q]
        cls = im.classify(pred, key_i, exp_i, k)
        rec = models.setdefault(m, {"all": im.new_tally(), "primary": im.new_tally()})
        im.add_tally(rec["all"], cls, k)
        if basis == "primary":
            im.add_tally(rec["primary"], cls, k)
        im.add_tally(per_q.setdefault(q, im.new_tally()), cls, k)
    for m in models:
        models[m]["control_accuracy"] = C.FIX_CONTROL_ACCURACY[m]
    verdicts, _p, _pp = im.predictions(models, per_q, C.FIX_MIN_TARGETS, C.THRESHOLDS)
    ok_models = {m: models[m]["all"] for m in models} == C.FIX_TARGET["models"]
    ok_q = per_q == C.FIX_TARGET["per_question"]
    ok_v = verdicts == C.FIX_TARGET["verdicts"]
    return {"models": ok_models, "per_question": ok_q, "verdicts": ok_v}


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
    frozen = {"targets": len(C.TARGETS), "primary": sum(1 for t in C.TARGETS if t[4] == "primary"),
              "miskey_ids": len(C.MISKEY_IDS),
              "targets_unique": len(set(t[0] for t in C.TARGETS)),
              "targets_in_miskeys": all(t[0] in C.MISKEY_IDS for t in C.TARGETS)}
    frozen_ok = (frozen["targets"] == C.N_TARGETS == frozen["targets_unique"] and frozen["primary"] == C.N_PRIMARY
                 and frozen["miskey_ids"] == C.N_MISKEY_IDS and frozen["targets_in_miskeys"])
    print("[frozen] %s ok=%s" % (frozen, frozen_ok))
    if not frozen_ok:
        raise SystemExit("frozen target list inconsistent -- aborting")

    raw, shards = read_columns(C.MMLU_PRO)
    rows = [r for r in raw if r["options"] and len(r["options"]) >= 2 and r["answer_index"] is not None
            and 0 <= r["answer_index"] < len(r["options"])]
    fam_n = {}
    for r in rows:
        fam_n[family(r["src"])] = fam_n.get(family(r["src"]), 0) + 1
    struct_ok = len(rows) == C.EXPECTED["n_valid"] and fam_n == C.EXPECTED["family_n"]
    print("[structural] n=%d families=%s ok=%s" % (len(rows), fam_n, struct_ok))
    if not struct_ok:
        raise SystemExit("structural gate failed -- aborting")
    hf_by_id = {int(r["question_id"]): r for r in rows}

    # Targets still keyed as in audit 75
    targets, target_check = {}, []
    for qid, src, key, exp, basis in C.TARGETS:
        r = hf_by_id.get(qid)
        k = len(r["options"]) if r else 0
        key_i, exp_i = im.LETTERS.index(key), im.LETTERS.index(exp)
        status = "ok"
        if r is None:
            status = "missing"
        elif r["src"] != src:
            status = "src_changed"
        elif r["answer_index"] != key_i:
            status = "key_changed"
        elif exp_i >= k or exp_i == key_i:
            status = "expert_out_of_range"
        target_check.append({"question_id": qid, "status": status})
        if status == "ok":
            targets[qid] = (k, key_i, exp_i, basis, src)
    n_keyed = len(targets)
    print("[targets] still keyed as audit 75: %d of %d" % (n_keyed, len(C.TARGETS)))
    control_ids = set(q for q, r in hf_by_id.items() if family(r["src"]) == "ori_mmlu" and q not in C.MISKEY_IDS)
    print("[control] MMLU-derived questions outside the 55 miskeys: %d" % len(control_ids))

    archives, models = {}, {}
    per_q = {q: im.new_tally() for q in targets}
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
        status, seen, joined = {}, set(), {}
        for rec in recs:
            s = join_status(rec, hf_by_id)
            status[s] = status.get(s, 0) + 1
            if s != "ok":
                continue
            qid = int(rec["question_id"])
            if qid in seen:
                continue
            seen.add(qid)
            joined[qid] = rec.get("pred")
        n_rec = len(recs)
        del recs
        join_share = status.get("ok", 0) / n_rec if n_rec else 0.0
        coverage = len(seen) / len(hf_by_id)
        ok = join_share >= C.MIN_JOIN_SHARE and coverage >= C.MIN_JOIN_SHARE
        info = {"archive": zname, "sha256": sha, "members": len(member_log), "n_records": n_rec,
                "join_status": status, "join_share": join_share, "coverage": coverage,
                "status": "included" if ok else "excluded_join"}
        archives[model] = info
        if not ok:
            print("[archive] %-44s excluded: join_share=%.4f coverage=%.4f" % (model, join_share, coverage))
            continue
        rec_m = {"all": im.new_tally(), "primary": im.new_tally(), "control": im.new_ctrl(), "n_joined": len(seen)}
        for qid, (k, key_i, exp_i, basis, _src) in targets.items():
            if qid not in joined:
                continue
            cls = im.classify(joined[qid], key_i, exp_i, k)
            im.add_tally(rec_m["all"], cls, k)
            if basis == "primary":
                im.add_tally(rec_m["primary"], cls, k)
            im.add_tally(per_q[qid], cls, k)
        for qid in control_ids:
            if qid in joined:
                r = hf_by_id[qid]
                im.add_ctrl(rec_m["control"], joined[qid], r["answer_index"], len(r["options"]))
        rec_m["control_accuracy"] = im.ctrl_accuracy(rec_m["control"])
        models[model] = rec_m
        t = rec_m["all"]
        print("[model] %-40s targets n=%2d key=%2d expert=%2d other=%2d none=%2d | control acc=%.4f (n=%d)"
              % (model, t["n"], t["key"], t["expert"], t["other"], t["none"],
                 rec_m["control_accuracy"] or 0.0, rec_m["control"]["n"]))

    verdicts, pooled, pooled_primary = im.predictions(models, per_q, C.MIN_TARGETS_PER_MODEL, C.THRESHOLDS)
    p1 = (all(fx.values()) and frozen_ok and struct_ok and n_keyed >= C.MIN_TARGETS_STILL_KEYED
          and len(models) >= C.MIN_INCLUDED_ARCHIVES)
    verdicts = dict(verdicts)
    verdicts["P1_structural"] = p1
    verdicts["P1_counts"] = [n_keyed, len(C.TARGETS), len(models), len(C.ARCHIVES)]
    for name in sorted(v for v in verdicts if not v.endswith("_counts")):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    print("[prediction] counts %s" % {k: v for k, v in sorted(verdicts.items()) if k.endswith("_counts")})
    print("[pooled] %s" % im.tally_report(pooled))
    print("[pooled-primary] %s" % im.tally_report(pooled_primary))

    # Exploratory: what each included model's MMLU-Pro score would gain if the 46 keys followed the experts
    impact = {}
    for m, r in sorted(models.items()):
        n_all = r["n_joined"]
        impact[m] = {"expert_minus_key": r["all"]["expert"] - r["all"]["key"],
                     "points_on_joined_questions": 100.0 * (r["all"]["expert"] - r["all"]["key"]) / n_all
                     if n_all else None}

    out = {
        "audit": 76,
        "slug": "mcq-mmlu-pro-inherited-miskey-models",
        "dataset": ("MMLU-Pro (TIGER-Lab/MMLU-Pro 'default' test, HF parquet) joined by question_id to every "
                    "per-question prediction archive in github.com/TIGER-AI-Lab/MMLU-Pro eval_results that audit 66 "
                    "listed (raw, main branch; sha256 recorded). Targets frozen from audit 75's pro_flags.json. A "
                    "missing or malformed pred counts as NONE. Only ids, letters and counts are written."),
        "fixture": fx, "frozen": frozen, "structural": {"n": len(rows), "family_n": fam_n, "shards": shards},
        "targets_check": target_check, "control_n": len(control_ids),
        "archives": archives,
        "models": {m: {"targets": im.tally_report(r["all"]), "targets_primary": im.tally_report(r["primary"]),
                       "control": {"n": r["control"]["n"], "accuracy": r["control_accuracy"]},
                       "n_joined": r["n_joined"]} for m, r in sorted(models.items())},
        "pooled": im.tally_report(pooled), "pooled_primary": im.tally_report(pooled_primary),
        "per_question": [dict(question_id=q, src=targets[q][4], basis=targets[q][3],
                              key_letter=im.LETTERS[targets[q][1]], expert_letter=im.LETTERS[targets[q][2]],
                              **im.tally_report(per_q[q])) for q in sorted(targets)],
        "score_impact_exploratory": impact,
        "predictions": verdicts,
        "note": ("P1 structural (fixture, frozen list 46/24/55, MMLU-Pro 12,032 rows and audit 63 families, >= 44 of 46 "
                 "targets still keyed as in audit 75, >= 30 archives included). P2 HEADLINE: pooled over included "
                 "models, the experts' answer is picked more often than the published key on the 46 targets. P3: in "
                 ">= 75% of models with >= 40 joined targets, expert picks > key picks. P4: pooled expert picks >= 3x "
                 "an average other distractor (sum of 1/(k-2) per OTHER pick). P5: every such model's key-pick rate "
                 "on the targets is below its accuracy on the control. P6: on >= 60% of target questions, pooled "
                 "expert picks > key picks. P7: P2 on the 24 primary (letter/text) targets alone."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
