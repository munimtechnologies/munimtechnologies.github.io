"""Do real models' MMLU-Pro answers follow the answer-length cue? (audit 65)

Audits 61-63 showed that a question-free "pick the longest option" heuristic scores 18.38% on MMLU-Pro (chance
11.09%) and about 67% on its STEM-website biology and psychology questions. That is a property of the options.
This audit reads the per-question predictions TIGER-AI-Lab publishes for MMLU-Pro (eval_results/*.zip in
github.com/TIGER-AI-Lab/MMLU-Pro), joins each record to the HF test row by question_id with identical stripped
options and answer, and measures per model:

- error pull: share of wrong answers that land on a longest distractor, against the exact tie-aware rate a
  uniformly random wrong choice would give (ratio > 1 = errors drawn toward long options);
- accuracy when the gold is the unique longest option versus otherwise, pooled, by source family and on the
  STEM-website biology+psychology subset, compared with the pick-longest heuristic there.

Gates before any prediction is scored: hand-traced fixtures match exactly, and the HF parse reproduces audit 63
(n, family counts, stemez-Biology / stemez-Psychology pick-longest) exactly. Five predictions were pre-registered
before any archive was opened.

Usage: python job.py --out-dir /out   (network required)
Apache-2.0.
"""

import argparse
import hashlib
import io
import json
import os
import urllib.request
import zipfile
from fractions import Fraction

import pyarrow.parquet as pq

import cases
import model_length as ml

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"


def _get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry transient network errors
            last = e
    raise RuntimeError("GET failed after %d tries: %s (%s)" % (tries, url, last))


def parquet_files(hf_dataset, config, wanted_splits):
    data = json.loads(_get(PARQUET_API % hf_dataset).decode("utf-8"))
    out = []
    for f in data["parquet_files"]:
        if f["config"] == config and f["split"] in wanted_splits:
            out.append((f["split"], f["url"]))
    return sorted(out)


def read_columns(spec):
    rows = []
    cols = spec["cols"]
    for split, url in parquet_files(spec["hf"], spec["config"], set(spec["splits"])):
        table = pq.read_table(io.BytesIO(_get(url)), columns=cols)
        data = {c: table.column(c).to_pylist() for c in cols}
        for i in range(len(data[cols[0]])):
            rows.append({c: data[c][i] for c in cols})
    return rows


def fixtures_ok():
    acc = ml.new_acc()
    for options, gold, pred in cases.ADD_ROWS:
        ml.add(acc, options, gold, pred)
    ok_add = acc == cases.ADD_TARGET
    ok_credit = all(ml.pick_longest_credit(o, g) == w for o, g, w in cases.CREDIT_CASES)
    ok_join = all(ml.join_status(r, cases.JOIN_HF) == w for r, w in cases.JOIN_CASES)
    ok_keys = all(ml.keys_for(r) == w for r, w in cases.KEY_CASES)
    return {"add": ok_add, "credit": ok_credit, "join": ok_join, "keys": ok_keys}


def structural_gate(rows):
    fam_n = {}
    src_credit = {}
    for r in rows:
        f = ml.family(r["src"])
        fam_n[f] = fam_n.get(f, 0) + 1
        if r["src"] in cases.EXPECTED["src_pick_longest"]:
            n, c = src_credit.get(r["src"], (0, Fraction(0)))
            src_credit[r["src"]] = (n + 1, c + ml.pick_longest_credit(r["options"], r["answer_index"]))
    detail = {"n_valid": {"got": len(rows), "expected": cases.EXPECTED["n_valid"],
                          "match": len(rows) == cases.EXPECTED["n_valid"]},
              "family_n": {"got": fam_n, "expected": cases.EXPECTED["family_n"],
                           "match": fam_n == cases.EXPECTED["family_n"]}}
    for src, (n_exp, acc_exp) in sorted(cases.EXPECTED["src_pick_longest"].items()):
        n, c = src_credit.get(src, (0, Fraction(0)))
        got = float(c / n) if n else None
        detail["src:" + src] = {"got": [n, got], "expected": [n_exp, acc_exp],
                                "match": n == n_exp and got is not None and abs(got - acc_exp) < 1e-12}
    return all(d["match"] for d in detail.values()), detail


def heuristic_biopsy(rows):
    n, c = 0, Fraction(0)
    for r in rows:
        if r["src"] in ml.BIOPSY_STEMEZ:
            n += 1
            c += ml.pick_longest_credit(r["options"], r["answer_index"])
    return n, float(c / n) if n else None


def records_from_zip(blob):
    """Yield prediction records from every .json member; returns (records, member_log)."""
    recs = []
    log = []
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


def analyse_model(recs, hf_by_id):
    status = {}
    seen = set()
    accs = {}
    n_dup = 0
    for rec in recs:
        st = ml.join_status(rec, hf_by_id)
        status[st] = status.get(st, 0) + 1
        if st != "ok":
            continue
        qid = int(rec["question_id"])
        if qid in seen:
            n_dup += 1
            continue
        seen.add(qid)
        row = hf_by_id[qid]
        for k in ml.keys_for(row):
            ml.add(accs.setdefault(k, ml.new_acc()), row["options"], row["answer_index"], rec.get("pred"))
    reports = {k: ml.report(v) for k, v in sorted(accs.items())}
    n_rec = len(recs)
    join_share = status.get("ok", 0) / n_rec if n_rec else 0.0
    coverage = len(seen) / len(hf_by_id) if hf_by_id else 0.0
    return {"n_records": n_rec, "join_status": status, "duplicates_skipped": n_dup,
            "join_share": join_share, "coverage": coverage}, reports


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    fx = fixtures_ok()
    print("[fixture] %s" % fx)
    if not all(fx.values()):
        raise SystemExit("fixture mismatch -- aborting before real data")

    rows = [r for r in read_columns(cases.MMLU_PRO) if r["options"] and len(r["options"]) >= 2
            and r["answer_index"] is not None and 0 <= r["answer_index"] < len(r["options"])]
    gate_ok, gate_detail = structural_gate(rows)
    print("[structural-gate] reproduces audit 63 : %s" % gate_ok)
    for k, d in gate_detail.items():
        if not d["match"]:
            print("[structural-gate][MISMATCH] %s got=%s expected=%s" % (k, d["got"], d["expected"]))
    if not gate_ok:
        raise SystemExit("structural gate failed -- aborting")
    hf_by_id = {int(r["question_id"]): r for r in rows}
    n_bp, heur_bp = heuristic_biopsy(rows)
    print("[heuristic] stemez biology+psychology n=%d pick_longest=%.4f" % (n_bp, heur_bp))

    archives = {}
    included = {}
    for zname in cases.MODEL_ZIPS:
        model = zname[len("model_outputs_"):].rsplit(".zip", 1)[0]
        try:
            blob = _get(cases.EVAL_RESULTS_URL % zname)
        except RuntimeError as e:
            archives[model] = {"archive": zname, "status": "download_failed", "error": str(e)[:300]}
            print("[archive] %-40s download failed" % model)
            continue
        sha = hashlib.sha256(blob).hexdigest()
        try:
            recs, member_log = records_from_zip(blob)
        except zipfile.BadZipFile:
            archives[model] = {"archive": zname, "sha256": sha, "bytes": len(blob), "status": "bad_zip"}
            print("[archive] %-40s bad zip" % model)
            continue
        del blob
        info, reports = analyse_model(recs, hf_by_id)
        ok = info["join_share"] >= cases.MIN_JOIN_SHARE and info["coverage"] >= cases.MIN_JOIN_SHARE
        info.update({"archive": zname, "sha256": sha, "members": len(member_log),
                     "members_without_records": [m for m in member_log if m["status"] != "ok"][:20],
                     "status": "included" if ok else "excluded_join"})
        archives[model] = info
        if ok:
            included[model] = reports
            a = reports["ALL"]
            s = reports.get("sub:stemez-biopsy", {})
            print("[model] %-36s n=%5d acc=%.4f pull=%.3f | stemez=%.3f ori=%.3f | biopsy acc=%.4f ul=%.4f not=%.4f"
                  % (model, a["n"], a["accuracy"], a["error_pull_ratio"] or 0.0,
                     reports.get("fam:stemez", {}).get("error_pull_ratio") or 0.0,
                     reports.get("fam:ori_mmlu", {}).get("error_pull_ratio") or 0.0,
                     s.get("accuracy") or 0.0, s.get("accuracy_gold_unique_longest") or 0.0,
                     s.get("accuracy_gold_not_unique_longest") or 0.0))
        else:
            print("[archive] %-40s excluded: join_share=%.4f coverage=%.4f status=%s"
                  % (model, info["join_share"], info["coverage"], info["join_status"]))

    preds = ml.predictions(included, heur_bp) if included else {}
    for name in sorted(p for p in preds if not p.endswith("_detail")):
        print("[prediction] %s = %s" % (name, "HELD" if preds[name] else "FAILED"))
    print("[models] included %d of %d" % (len(included), len(cases.MODEL_ZIPS)))

    out = {
        "dataset": ("MMLU-Pro (TIGER-Lab/MMLU-Pro 'default' test, HF parquet) joined by question_id to the "
                    "per-question model predictions in github.com/TIGER-AI-Lab/MMLU-Pro eval_results (raw, main "
                    "branch; each archive's sha256 recorded). A record joins only if its stripped options and "
                    "answer equal the HF row. A missing or malformed pred counts as not correct (the upstream "
                    "scorer substitutes a random guess instead). Lengths are characters after str.strip()."),
        "fixtures": fx,
        "structural_gate": {"passed": gate_ok, "detail": gate_detail},
        "heuristic_stemez_biopsy": {"n": n_bp, "pick_longest": heur_bp},
        "archives": archives,
        "models": included,
        "predictions": preds,
        "note": ("error_pull_ratio = (wrong answers on a longest distractor) / (expected count if each wrong "
                 "answer were a uniformly random distractor). P1: ratio > 1 in a strict majority of included "
                 "models. P2: ratio larger on stemez than on ori_mmlu in a strict majority. P3: on src "
                 "stemez-Biology + stemez-Psychology every model is more accurate when the gold is the unique "
                 "longest (both groups >= 20). P4: models below the median accuracy have a larger mean pooled "
                 "ratio. P5: at least a quarter of models score below the pick-longest heuristic on that subset. "
                 "Observational: a pull toward long options can reflect plausibility, not length itself."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
