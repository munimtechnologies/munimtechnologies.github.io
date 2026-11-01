"""Global-MMLU ROW-ALIGNMENT check (audit 72): do translated rows hold the English question with the same sample_id?

Audit 71 (mcq-global-mmlu-key-drift) found that all 176 Chinese and 116 Korean answer-letter differences from English
in Global-MMLU (Singh et al. 2024, arXiv 2412.03304; Apache-2.0) sit in one subject, high_school_world_history. A
read of its first 12 rows in zh, ko and en (datasets-server rows API) suggested why: in zh and ko, test/1-3 hold three
other questions and later rows hold English's question three places earlier, each with that question's own key,
while cultural_sensitivity_label stays with the sample_id. This job counts that across every language, subject and
row, without translating: rows are matched by the digit runs in their question and options (see align.py).

Seven predictions were written down (below and in cases.py) before any audit-72 number was seen; P3-P5 test the
hypothesis that the 12-row read suggested. Only aggregates are written out: no question or option text.

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
import cases

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
            "knowledge": str(rec.get("required_knowledge")), "options": tuple(al.norm(o) for o in options)}


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


def fixture_summary():
    rep, mapping = al.compare_subject(cases.FIXTURE_EN, cases.FIXTURE_XX)
    return {"report": rep, "mapping": mapping,
            "agreement": al.content_agreement(mapping, cases.FIXTURE_MAP_B),
            "lite": al.lite_compare(cases.FIXTURE_LITE_ROWS, cases.FIXTURE_LITE_FULL, cases.FIXTURE_LITE_EN,
                                    cases.FIXTURE_LITE_MISALIGNED)}


def _share(a, b):
    return (a / b) if b else None


def _sum_into(total, rep):
    for k in ("n", "no_fingerprint", "count_differs", "mapped", "aligned", "misaligned") + al.COUNTERS:
        total[k] = total.get(k, 0) + rep[k]


def compare_language(en_by_subject, en_by_id, rows):
    """One translation against English, subject by subject (subject taken from the English row)."""
    tally = {"n_rows": len(rows), "missing_in_reference": 0, "duplicate_ids": 0}
    seen, by_subject = set(), {}
    for r in rows:
        s = r["sample_id"]
        if s in seen:
            tally["duplicate_ids"] += 1
            continue
        seen.add(s)
        e = en_by_id.get(s)
        if e is None:
            tally["missing_in_reference"] += 1
            continue
        by_subject.setdefault(e["subject"], []).append(r)
    total, cells, mappings, fp_cells = {}, {}, {}, []
    for subj in sorted(by_subject):
        rep, mapping = al.compare_subject(en_by_subject[subj], by_subject[subj])
        _sum_into(total, rep)
        mappings[subj] = mapping
        if rep["same_id_fp_both"] >= cases.FP_MIN_BOTH:
            fp_cells.append((rep["same_id_fp_agree"] / rep["same_id_fp_both"], subj, rep["same_id_fp_both"]))
        if rep["misaligned"] or rep["key_differs_same_id"]:
            cells[subj] = rep
    fp_cells.sort()
    tally["fp_agreement_pooled"] = _share(total.get("same_id_fp_agree", 0), total.get("same_id_fp_both", 0))
    tally["fp_agreement_lowest_cells"] = [{"subject": s, "agreement": a, "pairs": n} for a, s, n in fp_cells[:3]]
    return tally, total, cells, mappings


def predictions(langs, focus_reports, flagged, lite):
    others = [L for L in langs if L != cases.REFERENCE_LANGUAGE]
    # P1 (structural): 42 configs x 14,042 rows, ids unique and all in English, and the same-id key differences equal
    # audits 70/71 per language.
    p1 = (len(langs) == cases.EXPECTED_N_CONFIGS
          and all(langs[L]["tally"]["n_rows"] == cases.EXPECTED_N_ROWS for L in others)
          and all(langs[L]["tally"]["missing_in_reference"] == 0 for L in others)
          and all(langs[L]["tally"]["duplicate_ids"] == 0 for L in others)
          and all(langs[L]["total"].get("key_differs_same_id", 0) == cases.AUDIT70_KEY_MISMATCH.get(L, 0)
                  for L in others))
    # P2 (coverage): at least 60% of zh and of ko high_school_world_history rows are matched by fingerprint.
    shares = {L: _share(focus_reports[L]["mapped"], focus_reports[L]["n"]) if L in focus_reports else None
              for L in cases.FOCUS}
    p2 = all(v is not None and v >= cases.P2_MIN_MAPPED_SHARE for v in shares.values())
    pooled = {}
    for L in cases.FOCUS:
        if L in focus_reports:
            _sum_into(pooled, focus_reports[L])
    # P3 (HEADLINE, mechanism): of the matched zh+ko key differences in that subject, at least 90% are rows holding
    # another English question (vacuous below 20).
    m3 = pooled.get("key_differs_misaligned", 0) + pooled.get("key_differs_aligned", 0)
    p3_vac = m3 < cases.P3_MIN_N
    p3 = (not p3_vac) and pooled["key_differs_misaligned"] >= cases.P3_MIN_MISALIGNED_SHARE * m3
    # P4 (keys follow content): misaligned rows carry the key of the English question they hold on >= 95%.
    m4 = pooled.get("misaligned", 0)
    p4_vac = m4 < cases.P4_MIN_N
    p4 = (not p4_vac) and pooled["mis_key_equals_content"] >= cases.P4_MIN_CONTENT_KEY * m4
    # P5 (labels follow the id): where the two English labels differ, the translation carries its sample_id's label
    # on >= 95% (vacuous below 3).
    m5 = pooled.get("mis_label_differs", 0)
    p5_vac = m5 < cases.P5_MIN_N
    p5 = (not p5_vac) and pooled["mis_label_follows_id"] >= cases.P5_MIN_FOLLOWS_ID * m5
    # P6 (confinement): the only (language, subject) cells with >= 5 misaligned rows are zh and ko
    # high_school_world_history.
    p6 = sorted(flagged) == sorted("%s|%s" % (L, cases.FOCUS_SUBJECT) for L in cases.FOCUS)
    # P7 (Lite inherits): >= 99% of Global-MMLU-Lite zh and ko test rows are identical (options and key) to the
    # full-set row with the same sample_id.
    p7_shares = {}
    for L in cases.FOCUS:
        c = lite.get(L)
        p7_shares[L] = _share(c["identical_to_full"], c["n"] - c["not_in_full"]) if c else None
    p7 = all(v is not None and v >= cases.P7_MIN_IDENTICAL for v in p7_shares.values())
    return {
        "P1_structural": bool(p1),
        "P2_fingerprint_coverage": bool(p2), "P2_mapped_shares": shares,
        "P3_key_differences_are_misaligned_rows": bool(p3), "P3_vacuous": bool(p3_vac), "P3_matched": m3,
        "P4_keys_follow_content": bool(p4), "P4_vacuous": bool(p4_vac), "P4_misaligned": m4,
        "P5_labels_follow_sample_id": bool(p5), "P5_vacuous": bool(p5_vac), "P5_label_differs": m5,
        "P6_confined_to_zh_ko_world_history": bool(p6), "P6_flagged_cells": sorted(flagged),
        "P7_lite_inherits_full_rows": bool(p7), "P7_identical_shares": p7_shares,
        "pooled_zh_ko_world_history": pooled,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Hand-traced fixture: exact equality before any real data is read.
    fx = fixture_summary()
    fx_ok = fx == cases.FIXTURE_TARGET
    print("[fixture] == FIXTURE_TARGET : %s" % fx_ok)
    if not fx_ok:
        for k in cases.FIXTURE_TARGET:
            if fx.get(k) != cases.FIXTURE_TARGET[k]:
                print("[fixture-diff] %s got %r want %r" % (k, fx.get(k), cases.FIXTURE_TARGET[k]))
        raise SystemExit("fixture mismatch -- aborting before real data")

    # 2) Global-MMLU-Lite test rows (small).
    lite_urls = split_urls(cases.LITE_DATASET)
    lite_rows, lite_shards = {}, {}
    for L in sorted(lite_urls):
        lite_rows[L], lite_shards[L] = load(lite_urls[L])
    print("[lite] configs=%d rows=%s" % (len(lite_rows), {L: len(v) for L, v in sorted(lite_rows.items())}))

    # 3) Global-MMLU English.
    urls = split_urls(cases.GMMLU_DATASET)
    order = [cases.REFERENCE_LANGUAGE] + sorted(L for L in urls if L != cases.REFERENCE_LANGUAGE)
    print("[configs] %d: %s" % (len(urls), ",".join(order)))
    en_rows, en_shards = load(urls[cases.REFERENCE_LANGUAGE])
    en_by_id = {r["sample_id"]: r for r in en_rows}
    en_by_subject = {}
    for r in en_rows:
        en_by_subject.setdefault(r["subject"], []).append(r)
    en_focus = en_by_subject.get(cases.FOCUS_SUBJECT, [])
    en_fp = {"rows": len(en_rows), "with_fingerprint": sum(1 for r in en_rows if r["fp"]),
             "focus_subject_rows": len(en_focus), "focus_subject_with_fingerprint": sum(1 for r in en_focus if r["fp"])}
    print("[en] %s" % en_fp)

    langs = {cases.REFERENCE_LANGUAGE: {"tally": {"n_rows": len(en_rows), "reference": True}}}
    shards = {cases.REFERENCE_LANGUAGE: en_shards}
    lite = {}
    if cases.REFERENCE_LANGUAGE in lite_rows:
        lite[cases.REFERENCE_LANGUAGE] = al.lite_compare(lite_rows[cases.REFERENCE_LANGUAGE], en_by_id, en_by_id,
                                                         set())
    focus_reports, focus_maps, flagged = {}, {}, []

    # 4) Every translation against English.
    for L in order[1:]:
        rows, shards[L] = load(urls[L])
        tally, total, cells, mappings = compare_language(en_by_subject, en_by_id, rows)
        misaligned_ids = set()
        for subj, mp in mappings.items():
            misaligned_ids.update(s for s, m in mp.items() if s != m)
            if cells.get(subj, {}).get("misaligned", 0) >= cases.FLAG_MIN_MISALIGNED:
                flagged.append("%s|%s" % (L, subj))
        if cases.FOCUS_SUBJECT in cells:
            focus_reports[L] = cells[cases.FOCUS_SUBJECT]
        if L in cases.FOCUS:
            focus_maps[L] = mappings.get(cases.FOCUS_SUBJECT, {})
        if L in lite_rows:
            ids = {r["sample_id"] for r in lite_rows[L]}
            full_by_id = {r["sample_id"]: r for r in rows if r["sample_id"] in ids}
            lite[L] = al.lite_compare(lite_rows[L], full_by_id, en_by_id, misaligned_ids)
        langs[L] = {"tally": tally, "total": total, "cells": cells}
        print("[lang] %-3s n=%d missing=%d dup=%d key_differs=%d (audit 70: %d) mapped=%d misaligned=%d "
              "fp_agree=%s lowest=%s lite=%s"
              % (L, tally["n_rows"], tally["missing_in_reference"], tally["duplicate_ids"],
                 total.get("key_differs_same_id", 0), cases.AUDIT70_KEY_MISMATCH.get(L, 0), total.get("mapped", 0),
                 total.get("misaligned", 0), tally["fp_agreement_pooled"], tally["fp_agreement_lowest_cells"][:1],
                 lite.get(L)))
        for subj, rep in sorted(cells.items()):
            print("[cell] %s|%s %s" % (L, subj, {k: v for k, v in rep.items() if v}))
        del rows

    zh_ko = (al.content_agreement(focus_maps[cases.FOCUS[0]], focus_maps[cases.FOCUS[1]])
             if all(L in focus_maps for L in cases.FOCUS) else None)
    print("[zh-ko %s] %s" % (cases.FOCUS_SUBJECT, zh_ko))
    for L in sorted(lite):
        print("[lite-compare] %s %s" % (L, lite[L]))

    preds = predictions(langs, focus_reports, flagged, lite)
    for k, v in preds.items():
        if k.startswith("P") and isinstance(v, bool) and not k.endswith("_vacuous"):
            print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))
    print("[prediction] details P2=%s P3 matched=%s vac=%s P4 misaligned=%s vac=%s P5 differs=%s vac=%s P6=%s P7=%s"
          % (preds["P2_mapped_shares"], preds["P3_matched"], preds["P3_vacuous"], preds["P4_misaligned"],
             preds["P4_vacuous"], preds["P5_label_differs"], preds["P5_vacuous"], preds["P6_flagged_cells"],
             preds["P7_identical_shares"]))
    print("[pooled zh+ko %s] %s" % (cases.FOCUS_SUBJECT, preds["pooled_zh_ko_world_history"]))

    out = {
        "audit": 72,
        "slug": "mcq-global-mmlu-row-alignment",
        "dataset": ("Global-MMLU (CohereLabs/Global-MMLU, Apache-2.0; Singh et al. 2024, arXiv 2412.03304) and "
                    "Global-MMLU-Lite (CohereLabs/Global-MMLU-Lite, Apache-2.0), every language config, split test, "
                    "read from the HuggingFace auto-converted parquet via the datasets-server parquet API. Rows are "
                    "matched to English only by the digit runs (3+ digits) in question and options, order-preserving "
                    "within a fingerprint. Only aggregates are written: no question or option text."),
        "fixture_target_met": fx_ok,
        "english_fingerprints": en_fp,
        "languages": langs,
        "flagged_cells": sorted(flagged),
        "zh_ko_focus_content_agreement": zh_ko,
        "lite": lite,
        "parquet_shards": shards,
        "lite_parquet_shards": lite_shards,
        "predictions": preds,
        "note": ("P1 structural (42 x 14,042; unique ids; same-id key differences = audits 70/71). P2 >= 60% of zh and "
                 "ko high_school_world_history rows matched. P3 HEADLINE: >= 90% of matched zh+ko key differences "
                 "there are misaligned rows. P4 misaligned rows carry their content's English key on >= 95%. P5 "
                 "where the two English labels differ, the translation carries its sample_id's label on >= 95%. P6 "
                 "the only cells with >= 5 misaligned rows are zh and ko high_school_world_history. P7 >= 99% of "
                 "Lite zh and ko rows identical to the full-set row with the same id. P3-P5 test a hypothesis "
                 "suggested by reading 12 rows per language before this job was written."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
