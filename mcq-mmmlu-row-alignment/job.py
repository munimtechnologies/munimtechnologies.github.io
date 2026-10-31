"""MMMLU ROW-ALIGNMENT check (audit 73): are OpenAI's MMMLU rows on MMLU's positions, and did Global-MMLU copy them?

Audits 71/72 (mcq-global-mmlu-key-drift, mcq-global-mmlu-row-alignment) traced all of Global-MMLU's Chinese and
Korean answer-key differences from English to misplaced rows in high_school_world_history. Global-MMLU (arXiv
2412.03304) took ten languages, Chinese and Korean among them, from OpenAI's MMMLU (openai/MMMLU, MIT), and MMMLU
discussion 13 (October 2024, no counts) noted that MMMLU's ZH_CN and KO_KR questions in that subject are in a
different order from MMLU's. A hand read on 2026-10-31 (rows 5852-5859 in both, plus ZH_CN 5968-5973 and 6083-6088)
showed the same three-place shift as Global-MMLU at the start, with Chinese rows 1-3 holding MMLU positions 158, 200
and 226.

This job counts, without translating, in every MMMLU language and subject: which rows hold another MMLU question
(matched by the digit runs of 3+ digits in question and options; see align.py), whether their keys follow the content,
and whether Global-MMLU's ten MMMLU-derived languages are MMMLU row for row. Seven predictions were written down (below
and in cases73.py) before any audit-73 number was seen; P7 tests a shape suggested by the hand read. Only aggregates
are written out: no question or option text.

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

import cases73 as c
import mmmlu as mm

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
        if f["split"] == c.SPLIT:
            urls.setdefault(f["config"], []).append(f["url"])
    for k in urls:
        urls[k].sort()
    return urls


def load(urls, columns):
    """Records in file order (shards in sorted order) with only the listed columns."""
    recs, shards = [], []
    for url in urls:
        raw = _get(url)
        shards.append({"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        t = pq.read_table(io.BytesIO(raw))
        cols = {k: t.column(k).to_pylist() for k in columns if k in t.column_names}
        n = t.num_rows
        del t
        recs.extend({k: cols[k][i] for k in cols} for i in range(n))
    return recs, shards


def fixture_summary():
    en = mm.english_rows(c.FIXTURE_EN_RECORDS)
    xx, tally = mm.mmmlu_rows(en, c.FIXTURE_MM_RECORDS)
    by_subject = {}
    for r in en:
        by_subject.setdefault(r["subject"], []).append(r)
    total, cells, mis, flagged, fmap = mm.compare_language(by_subject, xx, c.FIXTURE_FLAG_MIN, c.FIXTURE_FOCUS)
    gm = [mm.gm_row(r) for r in c.FIXTURE_GM_RECORDS]
    return {"en_ids": [r["sample_id"] for r in en], "en_keys": [r["key"] for r in en], "en_fps": [r["fp"] for r in en],
            "mm_keys": [r["key"] for r in xx], "mm_tally": tally, "total": total, "cells": cells,
            "misaligned": sorted(mis), "flagged": flagged, "focus_mapping": fmap,
            "inherit": mm.inherit_compare(gm, {r["sample_id"]: r for r in xx}, mis)}


def _share(a, b):
    return (a / b) if b else None


def predictions(en_struct, configs, gm):
    fs = c.FOCUS_SUBJECT
    # P1 (structural): MMLU has 14,042 rows with the subject at 5852..6088; all 14 MMMLU configs have 14,042 rows and
    # their own Subject equals MMLU's subject at the same position on >= 99% of rows.
    p1 = (en_struct["n"] == c.EXPECTED_N_ROWS and en_struct["focus_start"] == c.FOCUS_START
          and en_struct["focus_n"] == c.FOCUS_N and sorted(configs) == sorted(c.MMMLU_CONFIGS)
          and all(configs[k]["tally"]["n"] == c.EXPECTED_N_ROWS for k in configs)
          and all(configs[k]["tally"]["subject_agree"] >= c.P1_MIN_SUBJECT_AGREE * configs[k]["tally"]["n"]
                  for k in configs))
    focus = {k: configs.get(k, {}).get("cells", {}).get(fs) for k in c.FOCUS}
    # P2 (HEADLINE, source): in MMMLU ZH_CN and in KO_KR, at least 25% of the subject's 237 rows are matched to a
    # different MMLU question.
    p2_counts = {k: (f["misaligned"] if f else 0) for k, f in focus.items()}
    p2 = all(p2_counts[k] >= c.P2_MIN_MISALIGNED_SHARE * c.FOCUS_N for k in c.FOCUS)
    # P3 (keys follow content inside MMMLU): pooled, misaligned rows carry their content's MMLU key on >= 95%.
    m3 = sum(f["misaligned"] for f in focus.values() if f)
    k3 = sum(f["mis_key_equals_content"] for f in focus.values() if f)
    p3_vac = m3 < c.P3_MIN_N
    p3 = (not p3_vac) and k3 >= c.P3_MIN_CONTENT_KEY * m3
    # P4 (inheritance): Global-MMLU zh+ko rows of the subject on MMMLU-misaligned positions have the same fingerprint
    # and key as the MMMLU row at that position on >= 95%.
    m4 = sum(gm[L]["focus"]["on_misaligned"] for L in c.FOCUS_GMMLU if L in gm)
    k4 = sum(gm[L]["focus"]["on_misaligned_fp_key_equal"] for L in c.FOCUS_GMMLU if L in gm)
    p4_vac = m4 < c.P4_MIN_N
    p4 = (not p4_vac) and k4 >= c.P4_MIN_INHERITED * m4
    # P5 (confinement): the only MMMLU (config, subject) cells with >= 5 misaligned rows are ZH_CN and KO_KR in the
    # subject.
    flagged = sorted("%s|%s" % (k, s) for k in configs for s in configs[k]["flagged"])
    p5 = flagged == sorted("%s|%s" % (k, fs) for k in c.FOCUS)
    # P6 (copied verbatim): in each of the ten MMMLU-derived Global-MMLU languages, >= 95% of rows are identical
    # (normalised text and key) to the MMMLU row at the same position.
    p6_shares = {L: _share(gm[L]["all"]["identical"], gm[L]["all"]["n"] - gm[L]["all"]["not_in_mmmlu"])
                 for L in sorted(gm)}
    p6 = (len(p6_shares) == len(c.GMMLU_FROM_MMMLU)
          and all(v is not None and v >= c.P6_MIN_IDENTICAL for v in p6_shares.values()))
    # P7 (shape, from the hand read): in each of ZH_CN and KO_KR, >= 90% of misaligned rows have offset -1, -2 or -3.
    p7_shares = {}
    for k, f in focus.items():
        if f and f["misaligned"]:
            p7_shares[k] = sum(f["offsets"].get(o, 0) for o in c.SMALL_OFFSETS) / f["misaligned"]
        else:
            p7_shares[k] = None
    p7 = all(v is not None and v >= c.P7_MIN_SMALL_OFFSET for v in p7_shares.values())
    return {
        "P1_structural": bool(p1),
        "P2_mmmlu_focus_misaligned": bool(p2), "P2_counts": p2_counts,
        "P3_mmmlu_keys_follow_content": bool(p3), "P3_vacuous": bool(p3_vac), "P3_misaligned": m3,
        "P3_key_equals_content": k3,
        "P4_global_mmlu_inherits": bool(p4), "P4_vacuous": bool(p4_vac), "P4_on_misaligned": m4, "P4_fp_key_equal": k4,
        "P5_confined_to_zh_ko_world_history": bool(p5), "P5_flagged_cells": flagged,
        "P6_global_mmlu_copies_mmmlu": bool(p6), "P6_identical_shares": p6_shares,
        "P7_small_offsets": bool(p7), "P7_shares": p7_shares,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Hand-traced fixture: exact equality before any real data is read.
    fx = fixture_summary()
    fx_ok = fx == c.FIXTURE_TARGET
    print("[fixture] == FIXTURE_TARGET : %s" % fx_ok)
    if not fx_ok:
        for k in c.FIXTURE_TARGET:
            if fx.get(k) != c.FIXTURE_TARGET[k]:
                print("[fixture-diff] %s got %r want %r" % (k, fx.get(k), c.FIXTURE_TARGET[k]))
        raise SystemExit("fixture mismatch -- aborting before real data")

    fs = c.FOCUS_SUBJECT
    # 2) MMLU English (cais/mmlu 'all' test) in file order.
    en_recs, en_shards = load(split_urls(c.MMLU_DATASET)[c.MMLU_CONFIG], c.MMLU_COLUMNS)
    en_rows = mm.english_rows(en_recs)
    del en_recs
    en_by_subject, en_by_id = {}, {}
    for r in en_rows:
        en_by_subject.setdefault(r["subject"], []).append(r)
        en_by_id[r["sample_id"]] = r
    focus_pos = [i for i, r in enumerate(en_rows) if r["subject"] == fs]
    en_struct = {"n": len(en_rows), "subjects": len(en_by_subject), "focus_start": focus_pos[0] if focus_pos else None,
                 "focus_n": len(focus_pos), "with_fingerprint": sum(1 for r in en_rows if r["fp"]),
                 "focus_with_fingerprint": sum(1 for i in focus_pos if en_rows[i]["fp"])}
    print("[en] %s" % en_struct)

    # 3) Every MMMLU config against MMLU, by position.
    mm_urls = split_urls(c.MMMLU_DATASET)
    keep_cfgs = set(c.GMMLU_FROM_MMMLU.values())
    configs, shards, keep, keep_mis, focus_maps = {}, {"mmlu_all": en_shards}, {}, {}, {}
    for k in c.MMMLU_CONFIGS:
        if k not in mm_urls:
            print("[mmmlu] %s missing from the parquet listing" % k)
            continue
        recs, shards[k] = load(mm_urls[k], c.MMMLU_COLUMNS)
        rows, tally = mm.mmmlu_rows(en_rows, recs)
        del recs
        total, cells, mis, flagged, fmap = mm.compare_language(en_by_subject, rows, c.FLAG_MIN_MISALIGNED, fs)
        fp_both = total.get("same_id_fp_both", 0)
        configs[k] = {"tally": tally, "total": total, "cells": cells, "flagged": flagged,
                      "fp_agreement_pooled": _share(total.get("same_id_fp_agree", 0), fp_both),
                      "key_agreement_by_position": _share(len(rows) - total.get("key_differs_same_id", 0), len(rows))}
        if k in c.FOCUS:
            focus_maps[k] = fmap
        if k in keep_cfgs:
            keep[k] = {r["sample_id"]: {"digest": r["digest"], "fp": r["fp"], "key": r["key"]} for r in rows}
            keep_mis[k] = mis
        print("[mmmlu] %s n=%d subj_agree=%d malformed=%d key_differs=%d mapped=%d misaligned=%d fp_agree=%s "
              "flagged=%s" % (k, tally["n"], tally["subject_agree"], tally["subject_malformed"],
                              total.get("key_differs_same_id", 0), total.get("mapped", 0), total.get("misaligned", 0),
                              configs[k]["fp_agreement_pooled"], flagged))
        for subj, rep in sorted(cells.items()):
            print("[cell] %s|%s %s" % (k, subj, {a: b for a, b in rep.items() if b}))
        del rows

    # Hand-read check (descriptive): which MMLU positions do focus positions 1-3 hold?
    handread = {k: {str(i): focus_maps.get(k, {}).get("%s/test/%d" % (fs, i)) for i in (1, 2, 3)} for k in c.FOCUS}
    print("[handread] %s" % handread)
    zh_ko = None
    if all(k in focus_maps for k in c.FOCUS):
        a, b = focus_maps[c.FOCUS[0]], focus_maps[c.FOCUS[1]]
        both = sorted(set(a) & set(b))
        zh_ko = {"both_mapped": len(both), "same_content": sum(1 for s in both if a[s] == b[s]),
                 "both_misaligned": sum(1 for s in both if a[s] != s and b[s] != s),
                 "both_misaligned_same_content": sum(1 for s in both if a[s] != s and b[s] != s and a[s] == b[s])}
    print("[zh-ko %s] %s" % (fs, zh_ko))

    # 4) Global-MMLU's ten MMMLU-derived languages against MMMLU, by sample_id.
    gm_urls = split_urls(c.GMMLU_DATASET)
    gm = {}
    for L in sorted(c.GMMLU_FROM_MMMLU):
        k = c.GMMLU_FROM_MMMLU[L]
        if L not in gm_urls or k not in keep:
            print("[gmmlu] %s skipped (in listing: %s, MMMLU kept: %s)" % (L, L in gm_urls, k in keep))
            continue
        recs, shards["gmmlu_" + L] = load(gm_urls[L], c.GMMLU_COLUMNS)
        rows = [mm.gm_row(r) for r in recs]
        del recs
        focus_rows = [r for r in rows if r["sample_id"].startswith(fs + "/")]
        gm[L] = {"mmmlu_config": k, "all": mm.inherit_compare(rows, keep[k], keep_mis[k]),
                 "focus": mm.inherit_compare(focus_rows, keep[k], keep_mis[k]),
                 "key_differs_vs_mmlu_en": sum(1 for r in rows if r["sample_id"] in en_by_id
                                               and r["key"] != en_by_id[r["sample_id"]]["key"]),
                 "focus_key_differs_vs_mmlu_en": sum(1 for r in focus_rows if r["sample_id"] in en_by_id
                                                     and r["key"] != en_by_id[r["sample_id"]]["key"]),
                 "ids_not_in_mmlu": sum(1 for r in rows if r["sample_id"] not in en_by_id)}
        print("[gmmlu] %s<-%s %s" % (L, k, gm[L]))
        del rows, focus_rows

    preds = predictions(en_struct, configs, gm)
    for name, v in preds.items():
        if name.startswith("P") and isinstance(v, bool) and not name.endswith("_vacuous"):
            print("[prediction] %s = %s" % (name, "HELD" if v else "FAILED"))
    print("[prediction] details P2=%s P3=%s/%s vac=%s P4=%s/%s vac=%s P5=%s P6=%s P7=%s"
          % (preds["P2_counts"], preds["P3_key_equals_content"], preds["P3_misaligned"], preds["P3_vacuous"],
             preds["P4_fp_key_equal"], preds["P4_on_misaligned"], preds["P4_vacuous"], preds["P5_flagged_cells"],
             preds["P6_identical_shares"], preds["P7_shares"]))

    out = {
        "audit": 73,
        "slug": "mcq-mmmlu-row-alignment",
        "dataset": ("MMMLU (openai/MMMLU, MIT; 14 language configs, split test), MMLU (cais/mmlu, config all, split "
                    "test, MIT) and Global-MMLU (CohereLabs/Global-MMLU, Apache-2.0; its ten MMMLU-derived languages), "
                    "read from the HuggingFace auto-converted parquet via the datasets-server parquet API. MMMLU rows "
                    "take MMLU's positional ids 'subject/test/k'; rows are matched to MMLU only by digit runs (3+ "
                    "digits) in question and options, order-preserving within a fingerprint. Only aggregates are "
                    "written: no question or option text."),
        "fixture_target_met": fx_ok,
        "english": en_struct,
        "mmmlu": configs,
        "focus_handread_check": handread,
        "zh_ko_focus_content_agreement": zh_ko,
        "global_mmlu_vs_mmmlu": gm,
        "audit71_focus_key_diffs": c.AUDIT71_FOCUS_KEY_DIFFS,
        "parquet_shards": shards,
        "predictions": preds,
        "note": ("P1 structural (MMLU 14,042 rows, subject at 5852..6088; 14 MMMLU configs x 14,042; own Subject = "
                 "MMLU's at the same position on >= 99%). P2 HEADLINE: >= 25% of the 237 rows misaligned in each of "
                 "MMMLU ZH_CN and KO_KR high_school_world_history. P3 misaligned MMMLU rows there carry their "
                 "content's key on >= 95%. P4 Global-MMLU zh+ko rows on those positions have MMMLU's fingerprint and "
                 "key on >= 95%. P5 the only MMMLU cells with >= 5 misaligned rows are those two. P6 each of the ten "
                 "MMMLU-derived Global-MMLU languages is >= 95% identical to MMMLU by position. P7 >= 90% of "
                 "misaligned rows in each of the two have offset -1, -2 or -3 (shape suggested by a hand read)."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
