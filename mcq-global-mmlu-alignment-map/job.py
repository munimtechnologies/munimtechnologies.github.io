"""Global-MMLU ALIGNMENT MAP (audit 74): are audit 72's extra flagged cells matcher artifacts, and which world-history
rows in Chinese and Korean hold which English question?

Audit 72 matched every translated Global-MMLU row to English by a digit fingerprint and found 180 Chinese and 113
Korean rows of high_school_world_history holding another English question, with that question's key. Its P6 failed:
eight more cells were flagged (Japanese moral_scenarios; professional_law in ig it ja ny sn so tr), but there every
"misaligned" row carries its own position's key, which points to the matcher (huge shared-fingerprint groups), not
to the data. This job (1) reruns audit 72's matcher as a gate, (2) reruns it with fingerprint groups of more than
CAP rows left unmatched, (3) fills unmatched zh/ko world-history rows from their neighbours' offsets and checks that
rule by leave-one-out and by the answer keys, and (4) writes a per-position map (ids, keys, labels; no text).

Predictions P1-P7 are in cases74.py and were written before any audit-74 number existed.

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

import align as al
import amap
import cases
import cases74 as c74
import gate

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


def split_urls(dataset):
    urls = {}
    for f in json.loads(_get(PARQUET_API % dataset).decode("utf-8"))["parquet_files"]:
        if f["split"] == cases.SPLIT:
            urls.setdefault(f["config"], []).append(f["url"])
    for L in urls:
        urls[L].sort()
    return urls


def to_row(rec):
    options = [rec.get(c) for c in al.OPTION_COLS]
    return {"sample_id": rec.get("sample_id"), "subject": rec.get("subject"),
            "fp": al.fingerprint(rec.get("question"), options), "key": al.key_index(rec.get("answer")),
            "label": str(rec.get("cultural_sensitivity_label")), "annotated": bool(rec.get("is_annotated")),
            "knowledge": str(rec.get("required_knowledge"))}


def load(urls):
    rows, shards = [], []
    for url in urls:
        raw = _get(url)
        shards.append({"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        t = pq.read_table(io.BytesIO(raw))
        cols = {c: t.column(c).to_pylist() for c in cases.COLUMNS if c in t.column_names}
        n = t.num_rows
        del t
        for i in range(n):
            rows.append(to_row({c: cols[c][i] for c in cols}))
    return rows, shards


def _share(a, b):
    return (a / b) if b else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Hand-traced fixtures (audit 72's and audit 74's): exact equality before any real data is read.
    ok, diffs = gate.check()
    print("[fixture] audit 72 + audit 74 fixtures match: %s" % ok)
    if not ok:
        for d in diffs:
            print("[fixture-diff] audit %s %s got %r want %r" % d)
        raise SystemExit("fixture mismatch -- aborting before real data")

    # 2) Global-MMLU-Lite zh / ko ids.
    lite_urls = split_urls(cases.LITE_DATASET)
    lite_ids, lite_shards = {}, {}
    for L in cases.FOCUS:
        if L in lite_urls:
            rows, lite_shards[L] = load(lite_urls[L])
            lite_ids[L] = set(r["sample_id"] for r in rows)
    print("[lite] %s" % {L: len(v) for L, v in sorted(lite_ids.items())})

    # 3) English.
    urls = split_urls(cases.GMMLU_DATASET)
    order = [cases.REFERENCE_LANGUAGE] + sorted(L for L in urls if L != cases.REFERENCE_LANGUAGE)
    en_rows, en_shards = load(urls[cases.REFERENCE_LANGUAGE])
    en_by_id = {r["sample_id"]: r for r in en_rows}
    en_by_subject = {}
    for r in en_rows:
        en_by_subject.setdefault(r["subject"], []).append(r)
    en_focus = en_by_subject.get(cases.FOCUS_SUBJECT, [])
    focus_positions_ok = sorted(al.index_of(r["sample_id"]) for r in en_focus) == list(range(c74.FOCUS_N))
    print("[en] rows=%d configs=%d focus_rows=%d focus_positions_0_to_236=%s"
          % (len(en_rows), len(urls), len(en_focus), focus_positions_ok))

    shards = {cases.REFERENCE_LANGUAGE: en_shards}
    n_rows, key_diffs = {}, {}
    orig_flagged, capped_flagged = [], []
    cells = {}
    focus = {}

    # 4) Every translation.
    for L in order[1:]:
        rows, shards[L] = load(urls[L])
        n_rows[L] = len(rows)
        by_subject = {}
        for r in rows:
            e = en_by_id.get(r["sample_id"])
            if e is not None:
                by_subject.setdefault(e["subject"], []).append(r)
        kd = 0
        for subj in sorted(by_subject):
            xx = by_subject[subj]
            rep, mapping = al.compare_subject(en_by_subject[subj], xx)
            kd += rep["key_differs_same_id"]
            cmap, cst = amap.capped_align(en_by_subject[subj], xx, c74.CAP)
            ckeys = amap.key_report(en_by_id, xx, cmap)
            cell = "%s|%s" % (L, subj)
            if rep["misaligned"] >= cases.FLAG_MIN_MISALIGNED:
                orig_flagged.append(cell)
            if cst["misaligned"] >= cases.FLAG_MIN_MISALIGNED:
                capped_flagged.append(cell)
            if rep["misaligned"] or cst["misaligned"]:
                cells[cell] = {
                    "original": {"misaligned": rep["misaligned"], "mis_key_equals_content": rep["mis_key_equals_content"],
                                 "mis_key_equals_id": rep["mis_key_equals_id"],
                                 "same_id_fp_both": rep["same_id_fp_both"], "same_id_fp_agree": rep["same_id_fp_agree"]},
                    "capped": dict(cst, **{k: v for k, v in ckeys.items() if k != "misaligned"}),
                }
                print("[cell] %s %s" % (cell, cells[cell]))
            if L in cases.FOCUS and subj == cases.FOCUS_SUBJECT:
                offsets = amap.offsets_from(mapping)
                targets = [al.index_of(r["sample_id"]) for r in xx if r["sample_id"] not in mapping]
                inferred = amap.infer(c74.FOCUS_N, offsets, targets)
                loo = amap.leave_one_out(c74.FOCUS_N, offsets)
                records = amap.build_map(en_focus, xx, mapping, inferred)
                summ = amap.summarize(records)
                lite_other = sorted(
                    (r["sample_id"] for r in records
                     if r["sample_id"] in lite_ids.get(L, set())
                     and r["holds_position"] is not None and r["holds_position"] != r["position"]),
                    key=al.index_of)
                focus[L] = {"original_misaligned": rep["misaligned"], "unmatched": len(targets),
                            "inferred": len(inferred), "loo": loo, "summary": summ,
                            "capped": cells.get(cell, {}).get("capped"),
                            "lite_rows_in_subject": sum(1 for r in records if r["sample_id"] in lite_ids.get(L, set())),
                            "lite_ids_holding_other": lite_other, "records": records}
                print("[focus] %s orig_misaligned=%d unmatched=%d inferred=%d loo=%s summary=%s lite_other=%s"
                      % (L, rep["misaligned"], len(targets), len(inferred), loo, summ, lite_other))
        key_diffs[L] = kd
        print("[lang] %-3s n=%d key_differs=%d (audit 70: %d)" % (L, len(rows), kd, cases.AUDIT70_KEY_MISMATCH.get(L, 0)))
        del rows, by_subject

    # 5) Predictions.
    others = order[1:]
    p1 = (len(urls) == cases.EXPECTED_N_CONFIGS and focus_positions_ok
          and all(n_rows[L] == cases.EXPECTED_N_ROWS for L in others)
          and all(key_diffs[L] == cases.AUDIT70_KEY_MISMATCH.get(L, 0) for L in others)
          and all(L in focus for L in cases.FOCUS)
          and all(focus[L]["original_misaligned"] == c74.AUDIT72_FOCUS_MISALIGNED[L] for L in cases.FOCUS if L in focus)
          and sorted(orig_flagged) == sorted(c74.AUDIT72_FLAGGED))
    want_cells = sorted("%s|%s" % (L, cases.FOCUS_SUBJECT) for L in cases.FOCUS)
    p2 = sorted(capped_flagged) == want_cells

    cap_mis = {L: ((focus.get(L) or {}).get("capped") or {}).get("misaligned", 0) for L in cases.FOCUS}
    p3 = all(cap_mis[L] >= c74.P3_MIN_KEEP * c74.AUDIT72_FOCUS_MISALIGNED[L] for L in cases.FOCUS)

    m4 = sum(cap_mis.values())
    k4 = sum(((focus.get(L) or {}).get("capped") or {}).get("mis_key_equals_content", 0) for L in cases.FOCUS)
    p4_vac = m4 < c74.P4_MIN_N
    p4 = (not p4_vac) and k4 >= c74.P4_MIN_CONTENT_KEY * m4

    unmatched = sum(focus[L]["unmatched"] for L in focus)
    filled = sum(focus[L]["inferred"] for L in focus)
    p5 = unmatched > 0 and filled >= c74.P5_MIN_FILL * unmatched

    made = sum(focus[L]["loo"]["made"] for L in focus)
    agree = sum(focus[L]["loo"]["agree"] for L in focus)
    p6_vac = made < c74.P6_MIN_MADE
    p6 = (not p6_vac) and agree >= c74.P6_MIN_AGREE * made

    n7 = sum(focus[L]["summary"]["holds_other_neighbours"] for L in focus)
    k7 = sum(focus[L]["summary"]["neighbours_other_key_fits_held"] for L in focus)
    p7_vac = n7 < c74.P7_MIN_N
    p7 = (not p7_vac) and k7 >= c74.P7_MIN_KEY * n7

    preds = {
        "P1_structural_reproduces_audit72": bool(p1),
        "P2_capped_only_zh_ko_world_history": bool(p2), "P2_capped_flagged": sorted(capped_flagged),
        "P3_capped_keeps_focus": bool(p3), "P3_capped_misaligned": cap_mis,
        "P4_capped_keys_follow_content": bool(p4), "P4_vacuous": bool(p4_vac), "P4_counts": [k4, m4],
        "P5_inference_fills_half": bool(p5), "P5_counts": [filled, unmatched],
        "P6_loo_agrees": bool(p6), "P6_vacuous": bool(p6_vac), "P6_counts": [agree, made],
        "P7_inferred_keys_follow_content": bool(p7), "P7_vacuous": bool(p7_vac), "P7_counts": [k7, n7],
    }
    for k, v in preds.items():
        if k.startswith("P") and isinstance(v, bool) and not k.endswith("_vacuous"):
            print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))
    print("[prediction] details P2=%s P3=%s P4=%s vac=%s P5=%s P6=%s vac=%s P7=%s vac=%s"
          % (preds["P2_capped_flagged"], cap_mis, preds["P4_counts"], p4_vac, preds["P5_counts"],
             preds["P6_counts"], p6_vac, preds["P7_counts"], p7_vac))

    amap_out = {L: focus[L]["records"] for L in focus}
    focus_out = {L: {k: v for k, v in focus[L].items() if k != "records"} for L in focus}
    out = {
        "audit": 74,
        "slug": "mcq-global-mmlu-alignment-map",
        "dataset": ("Global-MMLU (CohereLabs/Global-MMLU, Apache-2.0; Singh et al. 2024, arXiv 2412.03304), every "
                    "language config, split test, and the zh / ko configs of Global-MMLU-Lite (Apache-2.0), read "
                    "from the HuggingFace auto-converted parquet via the datasets-server parquet API. Rows are "
                    "matched to English only by digit runs (3+ digits) in question and options. Only aggregates and "
                    "sample_id positions are written: no question or option text."),
        "cap": c74.CAP,
        "fixtures_met": ok,
        "n_rows": n_rows,
        "key_differs_same_id": key_diffs,
        "original_flagged": sorted(orig_flagged),
        "capped_flagged": sorted(capped_flagged),
        "cells": cells,
        "focus": focus_out,
        "parquet_shards": shards,
        "lite_parquet_shards": lite_shards,
        "predictions": preds,
        "note": ("P1 reproduces audit 72 (42 x 14,042; key differences = audit 70; zh 180 / ko 113 misaligned; the "
                 "same 10 flagged cells). P2 with groups > CAP rows unmatched, only zh and ko world history keep >= 5 "
                 "misaligned rows. P3 capped keeps >= 90% of 180 / 113. P4 capped misaligned zh+ko rows carry the "
                 "held key >= 95%. P5 neighbour inference fills >= 50% of unmatched zh+ko rows. P6 leave-one-out "
                 "agrees >= 90% (>= 50 made). P7 inferred rows holding another question carry its key >= 90% "
                 "(>= 20)."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "alignment_map.json"), "w", encoding="utf-8") as fh:
        json.dump({"subject": cases.FOCUS_SUBJECT, "languages": amap_out,
                   "fields": "position = the row's sample_id index; holds_position = index of the English question "
                             "the row holds (null = unresolved); how = fingerprint | neighbours | unresolved"},
                  fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and alignment_map.json")


if __name__ == "__main__":
    main()
