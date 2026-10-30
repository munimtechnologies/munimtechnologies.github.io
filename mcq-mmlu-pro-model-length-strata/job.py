"""MMLU-Pro's answer-length pull, within source and over every published prediction archive (audit 66).

Audit 65 read 17 of the per-question prediction archives TIGER-AI-Lab publishes for MMLU-Pro and found every
included model's wrong answers lean toward the longest distractor, most on the STEM-website biology and psychology
questions. This job reads every archive listed in eval_results (48 on 2026-10-30), joins each record to the HF test
row by question_id with identical stripped options and answer (same rule as audit 65), and adds per model:

- the mean normalised length rank of wrong picks among the distractors (0.5 = no lean);
- a within-src Mantel-Haenszel accuracy difference, gold unique-longest vs not, so the STEM-website gap of audit 65
  is no longer confounded by which subjects have long gold answers.

Gates before any prediction is scored: hand-traced fixtures match; the HF parse reproduces audit 63 exactly; and
every audit-65 model whose archive is byte-identical reproduces audit 65's n and pooled error pull exactly. Seven
predictions were pre-registered before any new archive was opened.

Usage: python job.py --out-dir /out   (network required)
Apache-2.0.
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

import cases
import model_length as ml
import strata as st

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
    ok_rank = all(st.length_rank(o, g, p) == w for o, g, p, w in cases.RANK_CASES)
    acc = st.new_strata_acc()
    for src, options, gold, pred in cases.STRATA_ROWS:
        st.add_strata(acc, src, options, gold, pred)
    ok_add = acc == cases.STRATA_TARGET
    ok_mh = st.mh_risk_difference(cases.MH_CELLS) == cases.MH_TARGET
    rep = st.report_strata(acc)
    ok_rep = (set(rep) == set(cases.STRATA_REPORT)
              and all(abs(rep[k] - v) < 1e-12 for k, v in cases.STRATA_REPORT.items()))
    return {"rank": ok_rank, "add_strata": ok_add, "mh": ok_mh, "report": ok_rep}


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
    """Prediction records from every .json member; returns (records, member_log). Same reader as audit 65."""
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
    saccs = {}
    n_dup = 0
    for rec in recs:
        s = ml.join_status(rec, hf_by_id)
        status[s] = status.get(s, 0) + 1
        if s != "ok":
            continue
        qid = int(rec["question_id"])
        if qid in seen:
            n_dup += 1
            continue
        seen.add(qid)
        row = hf_by_id[qid]
        for k in ml.keys_for(row):
            ml.add(accs.setdefault(k, ml.new_acc()), row["options"], row["answer_index"], rec.get("pred"))
            st.add_strata(saccs.setdefault(k, st.new_strata_acc()), row["src"], row["options"],
                          row["answer_index"], rec.get("pred"))
    reports = {}
    for k in sorted(accs):
        merged = ml.report(accs[k])
        merged.update(st.report_strata(saccs[k]))
        reports[k] = merged
    n_rec = len(recs)
    join_share = status.get("ok", 0) / n_rec if n_rec else 0.0
    coverage = len(seen) / len(hf_by_id) if hf_by_id else 0.0
    return {"n_records": n_rec, "join_status": status, "duplicates_skipped": n_dup,
            "join_share": join_share, "coverage": coverage}, reports


def audit65_gate(archives, included):
    """Byte-identical audit-65 archives must reproduce its n and pooled error pull exactly."""
    detail = {}
    for model, (sha, n_exp, ratio_exp) in sorted(cases.AUDIT65.items()):
        a = archives.get(model)
        if not a or a.get("sha256") is None:
            detail[model] = {"status": "not_downloaded"}
            continue
        if a["sha256"] != sha:
            detail[model] = {"status": "archive_changed", "sha256": a["sha256"]}
            continue
        r = included.get(model, {}).get("ALL")
        ok = (r is not None and r["n"] == n_exp and r["error_pull_ratio"] is not None
              and abs(r["error_pull_ratio"] - ratio_exp) < 1e-12)
        detail[model] = {"status": "match" if ok else "MISMATCH",
                         "got": [r["n"], r["error_pull_ratio"]] if r else None, "expected": [n_exp, ratio_exp]}
    checked = [d for d in detail.values() if d["status"] in ("match", "MISMATCH")]
    passed = bool(checked) and all(d["status"] == "match" for d in checked)
    return passed, detail


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
    if not gate_ok:
        for k, d in gate_detail.items():
            if not d["match"]:
                print("[structural-gate][MISMATCH] %s got=%s expected=%s" % (k, d["got"], d["expected"]))
        raise SystemExit("structural gate failed -- aborting")
    hf_by_id = {int(r["question_id"]): r for r in rows}
    n_bp, heur_bp = heuristic_biopsy(rows)
    print("[heuristic] stemez biology+psychology n=%d pick_longest=%.4f" % (n_bp, heur_bp))

    archives = {}
    included = {}
    for zname in cases.ARCHIVES:
        model = cases.model_name(zname)
        try:
            blob = _get(cases.EVAL_RESULTS_URL % urllib.parse.quote(zname))
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
        info, reports = analyse_model(recs, hf_by_id)
        del recs
        ok = info["join_share"] >= cases.MIN_JOIN_SHARE and info["coverage"] >= cases.MIN_JOIN_SHARE
        info.update({"archive": zname, "sha256": sha, "members": len(member_log),
                     "members_without_records": [m for m in member_log if m["status"] != "ok"][:20],
                     "status": "included" if ok else "excluded_join"})
        archives[model] = info
        if ok:
            included[model] = reports
            a = reports["ALL"]
            s = reports.get("sub:stemez-biopsy", {})
            print("[model] %-40s n=%5d acc=%.4f pull=%.3f rank=%.4f | stemez mh=%s ori mh=%s | biopsy acc=%.4f rank=%s"
                  % (model, a["n"], a["accuracy"], a["error_pull_ratio"] or 0.0, a["length_rank_mean"] or 0.0,
                     reports.get("fam:stemez", {}).get("mh_rd_gold_ul"),
                     reports.get("fam:ori_mmlu", {}).get("mh_rd_gold_ul"),
                     s.get("accuracy") or 0.0, s.get("length_rank_mean")))
        else:
            print("[archive] %-44s excluded: join_share=%.4f coverage=%.4f status=%s"
                  % (model, info["join_share"], info["coverage"], info["join_status"]))

    g65_ok, g65_detail = audit65_gate(archives, included)
    print("[audit65-gate] byte-identical archives reproduce audit 65 : %s" % g65_ok)
    for m, d in g65_detail.items():
        if d["status"] != "match":
            print("[audit65-gate] %-40s %s" % (m, d["status"]))
    if not g65_ok:
        raise SystemExit("audit-65 gate failed -- aborting")

    new_models = [m for m in included if m not in cases.AUDIT65_ATTEMPTED]
    preds = st.predictions(included, heur_bp, new_models) if included else {}
    for name in sorted(p for p in preds if not p.endswith("_detail")):
        print("[prediction] %s = %s" % (name, "HELD" if preds[name] else "FAILED"))
    print("[models] included %d of %d archives (%d not in audit 65)"
          % (len(included), len(cases.ARCHIVES), len(new_models)))

    out = {
        "dataset": ("MMLU-Pro (TIGER-Lab/MMLU-Pro 'default' test, HF parquet) joined by question_id to every "
                    "per-question prediction archive listed in github.com/TIGER-AI-Lab/MMLU-Pro eval_results on "
                    "2026-10-30 (raw, main branch; each archive's sha256 recorded). A record joins only if its "
                    "stripped options and answer equal the HF row. A missing or malformed pred counts as not "
                    "correct (the upstream scorer substitutes a random guess instead). Lengths are characters "
                    "after str.strip()."),
        "fixtures": fx,
        "structural_gate": {"passed": gate_ok, "detail": gate_detail},
        "audit65_gate": {"passed": g65_ok, "detail": g65_detail},
        "heuristic_stemez_biopsy": {"n": n_bp, "pick_longest": heur_bp},
        "archives": archives,
        "new_models": sorted(new_models),
        "models": included,
        "predictions": preds,
        "note": ("length_rank_mean: mean normalised mid-rank (0 shortest .. 1 longest, ties averaged) of a wrong "
                 "pick's length among that question's distractors; 0.5 = no lean. mh_rd_gold_ul: Mantel-Haenszel "
                 "risk difference over src strata, accuracy with the gold the unique longest option minus "
                 "accuracy otherwise. error_pull_ratio as in audit 65. Observational: a pull toward long options "
                 "can reflect plausibility, not length itself."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
