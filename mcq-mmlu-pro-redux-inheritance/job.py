"""Audit 75: which of MMLU's expert-flagged errors did MMLU-Pro inherit, fix or drop?

Joins MMLU-Redux 2.0's expert labels (57 subjects x 100 MMLU test questions) to MMLU test and then to MMLU-Pro's
MMLU-derived questions, and counts, per label, how many made it into MMLU-Pro and whether MMLU-Pro kept MMLU's key.
Six predictions were frozen before any real number was seen (cases75.py, README). Writes results.json (aggregates)
and pro_flags.json (MMLU-Pro question_ids with their Redux label, key status, MMLU-Pro answer letter and the experts'
answer as an MMLU-Pro letter; no question or option text).

Usage: python job.py --out-dir /out   (network: HF datasets-server parquet API)
Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import argparse
import hashlib
import io
import json
import os
import urllib.request

import pyarrow.parquet as pq

import cases75 as cs
import redux_pro as rp

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"


def _get(url, tries=4):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
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
                   if f["config"] == spec["config"] and f["split"] in spec["splits"])
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
    files = sorted((f["config"], f["url"]) for f in _listing(cs.REDUX_DATASET) if f["split"] == cs.REDUX_SPLIT)
    for config, url in files:
        raw = _get(url)
        shards.append({"config": config, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        t = pq.read_table(io.BytesIO(raw))
        cols = {c: (t.column(c).to_pylist() if c in t.column_names else [None] * t.num_rows)
                for c in ("question", "choices", "answer", "error_type", "correct_answer")}
        for q, ch, a, et, ca in zip(cols["question"], cols["choices"], cols["answer"], cols["error_type"],
                                    cols["correct_answer"]):
            rows.append({"subject": config, "question": q, "choices": list(ch or []),
                         "answer": int(a) if a is not None else None, "label": rp.label_of(et), "correct": ca})
    return rows, shards


def predictions(S, n):
    """n: dict of structural counts. Each prediction is a finding either way."""
    p1 = (n["pro"] == cs.EXPECTED_PRO_N and n["pro_ori"] == cs.EXPECTED_PRO_ORI and n["mmlu"] == cs.EXPECTED_MMLU_TEST
          and n["redux"] == cs.EXPECTED_REDUX_N and n["subjects"] == cs.EXPECTED_REDUX_SUBJECTS
          and n["labels"] == cs.EXPECTED_LABELS
          and S["redux_mmlu"]["joined"] >= cs.P1_MIN_JOIN * n["redux"])
    in_pro = S["pro_join"]["in_pro"] + S["pro_join"]["ambiguous_pro"]
    p2 = n["redux"] > 0 and in_pro >= cs.P2_MIN_IN_PRO * n["redux"]
    m = S["miskey"]
    den3 = m["kept"] + m["moved"] + m["new"]
    p3_vac = den3 < cs.P3_MIN_N
    p3 = (not p3_vac) and m["kept"] >= cs.P3_MIN_KEPT * den3
    pooled, h = S["inclusion"]["pooled"], S["inclusion"]["by_subject_cmh"]
    p4 = (pooled["risk_ratio"] is not None and pooled["risk_ratio"] > 1
          and h["mh_odds_ratio"] is not None and h["mh_odds_ratio"] > 1)
    c = m["corrections"]["primary"]
    p5_vac = c["resolved_kept"] < cs.P5_MIN_N
    p5 = (not p5_vac) and c["kept_present"] >= cs.P5_MIN_PRESENT * c["resolved_kept"]
    moved = sum(S["moved_labels"].values())
    flagged = moved - S["moved_labels"].get(rp.OK, 0)
    p6_vac = moved < cs.P6_MIN_N
    p6 = (not p6_vac) and flagged >= cs.P6_MIN_FLAGGED * moved
    return {"P1_structural": bool(p1),
            "P2_at_least_30pct_in_mmlu_pro": bool(p2), "P2_counts": [in_pro, n["redux"]],
            "P3_mmlu_pro_keeps_disputed_keys": bool(p3), "P3_vacuous": bool(p3_vac), "P3_counts": [m["kept"], den3],
            "P4_flagged_included_more_than_ok": bool(p4),
            "P5_expert_answer_still_an_option": bool(p5), "P5_vacuous": bool(p5_vac),
            "P5_counts": [c["kept_present"], c["resolved_kept"]],
            "P6_moved_keys_mostly_flagged": bool(p6), "P6_vacuous": bool(p6_vac), "P6_counts": [flagged, moved]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Hand-traced fixture: exact equality before any real data is read.
    fS, fflags = rp.analyse(cs.FIXTURE_REDUX, cs.FIXTURE_MMLU, cs.FIXTURE_PRO)
    got = rp.fixture_summary(fS, fflags)
    ok = got == cs.FIXTURE_TARGET
    print("[fixture] == FIXTURE_TARGET : %s" % ok)
    if not ok:
        for k in cs.FIXTURE_TARGET:
            if got.get(k) != cs.FIXTURE_TARGET[k]:
                print("[fixture-diff] %s got %r want %r" % (k, got.get(k), cs.FIXTURE_TARGET[k]))
        raise SystemExit("fixture mismatch -- aborting before real data")

    # 2) Real data.
    pro, pro_shards = read_spec(cs.PRO)
    mmlu, mmlu_shards = read_spec(cs.MMLU)
    redux, redux_shards = read_redux()
    labels = {}
    for r in redux:
        labels[r["label"]] = labels.get(r["label"], 0) + 1
    n = {"pro": len(pro), "pro_ori": sum(1 for r in pro if rp.pro_subject(r["src"]) is not None),
         "mmlu": len(mmlu), "redux": len(redux), "subjects": len(set(r["subject"] for r in redux)),
         "labels": dict(sorted(labels.items()))}
    print("[load] %s" % n)

    # 3) Analysis.
    S, flags = rp.analyse(redux, mmlu, pro)
    print("[redux->mmlu] %s ; redux answer == mmlu key on %d" % (S["redux_mmlu"], S["redux_answer_equals_mmlu_key"]))
    print("[mmlu->pro] %s" % S["pro_join"])
    for lab, v in sorted(S["by_label"].items()):
        print("[label] %-26s %s" % (lab, v))
    print("[moved] %s ; [new] %s" % (S["moved_labels"], S["new_labels"]))
    print("[miskey] %s" % S["miskey"])
    p, h = S["inclusion"]["pooled"], S["inclusion"]["by_subject_cmh"]
    print("[inclusion] table=%s rate_flagged=%s rate_ok=%s RR=%s chi2=%s | CMH=%s O-E=%s MH-OR=%s informative=%d"
          % (p["table"], p["rate_1"], p["rate_2"], p["risk_ratio"], p["chi_square_stat"], h["cmh_stat"],
             h["sum_observed_minus_expected"], h["mh_odds_ratio"], h["n_informative_strata"]))
    inherited_by_category = {}
    for f in flags:
        if f["label"] == rp.MISKEY and f["key_status"] == "kept":
            inherited_by_category[f["category"]] = inherited_by_category.get(f["category"], 0) + 1
    print("[inherited-miskeys-by-category] %s" % dict(sorted(inherited_by_category.items(), key=lambda kv: -kv[1])))

    preds = predictions(S, n)
    for k, v in preds.items():
        if not k.endswith(("_counts", "_vacuous")):
            print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))
    print("[prediction] details P2=%s P3=%s vac=%s P5=%s vac=%s P6=%s vac=%s"
          % (preds["P2_counts"], preds["P3_counts"], preds["P3_vacuous"], preds["P5_counts"], preds["P5_vacuous"],
             preds["P6_counts"], preds["P6_vacuous"]))

    out = {
        "audit": 75,
        "slug": "mcq-mmlu-pro-redux-inheritance",
        "datasets": ("MMLU-Redux 2.0 (edinburgh-dawg/mmlu-redux-2.0, CC BY 4.0; 57 configs, test), MMLU (cais/mmlu "
                     "'all', test; MIT) and MMLU-Pro (TIGER-Lab/MMLU-Pro 'default', test; MIT), read from the "
                     "HuggingFace auto-converted parquet via the datasets-server parquet API. Only ids, labels and "
                     "counts are written: no question, option or suggested-answer text."),
        "fixture_target_met": ok,
        "structural": n,
        "summary": S,
        "inherited_miskeys_by_category": inherited_by_category,
        "predictions": preds,
        "shards": {"mmlu_pro": pro_shards, "mmlu": mmlu_shards, "mmlu_redux": redux_shards},
        "note": ("P1 structural (MMLU-Pro 12,032 / 6,810 ori_mmlu; MMLU test 14,042; Redux 5,700 rows, 57 subjects, "
                 "labels = audit 58/69; >= 99% of Redux rows join MMLU test). P2 >= 30% of Redux rows are in "
                 "MMLU-Pro. P3 HEADLINE: MMLU-Pro keeps MMLU's key on >= 75% of Redux-miskeyed questions it contains "
                 "(vacuous below 10). P4 flagged questions are in MMLU-Pro more often than expert-OK ones (pooled RR "
                 "> 1 and Mantel-Haenszel OR > 1 by subject). P5 on inherited miskeys, the experts' answer (letters or "
                 "exact text) is still an MMLU-Pro option on >= 80% (vacuous below 10). P6 where MMLU-Pro moved the "
                 "key to another MMLU option, Redux had flagged the question on >= 50% (vacuous below 5)."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "pro_flags.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 75, "fields": ["question_id", "category", "src", "label", "key_status", "pro_answer",
                                           "expert_answer", "expert_answer_digits_0_based",
                                           "expert_answer_digits_1_based", "correction_format"],
                   "rows": flags}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and pro_flags.json")


if __name__ == "__main__":
    main()
