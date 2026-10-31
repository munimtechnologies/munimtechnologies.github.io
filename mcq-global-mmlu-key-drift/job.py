"""Global-MMLU KEY-DRIFT forensics (audit 71): why do Chinese and Korean carry different answer keys from English?

Audit 70 (mcq-global-mmlu-length-census) found Global-MMLU (Singh et al. 2024, arXiv 2412.03304; Apache-2.0) gives a
different answer letter from English on 176 Chinese and 116 Korean test rows (German 5, Italian 3, Yoruba 2, Japanese
1, other languages 0), while its English rows are exactly MMLU's test set. This job, for every language:

1. classifies each key disagreement as same answer under a new letter (options reordered), a different answer with
   the options in place, a different answer with the options reordered, or unresolved (options not matchable
   without translation: matched only by identical text or identical numbers);
2. runs the same classification on every key-AGREEING row as a control (do options ever move?);
3. compares the Chinese and Korean disagreements with each other (same questions? same new key?);
4. joins English to MMLU-Redux 2.0's expert labels (edinburgh-dawg/mmlu-redux-2.0, CC BY 4.0) by subject and option
   texts, and asks whether disagreements sit on questions the experts flagged, and whether a translation's key
   equals the experts' corrected answer.

Seven predictions were written down (below) before any real number was seen. Only aggregates are written out: no
question or option text.

Usage: python job.py --out-dir /out   (network: HF datasets-server parquet API)
Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import argparse
import hashlib
import io
import json
import os
import urllib.request
from fractions import Fraction

import pyarrow.parquet as pq

import cases
import keydrift as kd

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


def parquet_files(dataset):
    return json.loads(_get(PARQUET_API % dataset).decode("utf-8"))["parquet_files"]


def fixture_summary():
    ref = kd.reference(cases.FIXTURE_EN)
    tally, mism = kd.tally_language(ref, cases.FIXTURE_XX)
    joined, st = kd.join_redux(list(ref.values()), cases.FIXTURE_REDUX)
    corr = kd.correction_agreement({s: v[0] for s, v in mism.items()}, joined)
    return {"tally": tally, "mismatches": mism, "join": st, "correction": corr}


def load_redux():
    files = sorted((f["config"], f["url"]) for f in parquet_files(cases.REDUX_DATASET)
                   if f["split"] == cases.REDUX_SPLIT)
    rows, shards = [], []
    for config, url in files:
        raw = _get(url)
        shards.append({"config": config, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        t = pq.read_table(io.BytesIO(raw))
        cols = {c: (t.column(c).to_pylist() if c in t.column_names else [None] * t.num_rows)
                for c in ("question", "choices", "answer", "error_type", "correct_answer")}
        for q, ch, a, et, ca in zip(cols["question"], cols["choices"], cols["answer"], cols["error_type"],
                                    cols["correct_answer"]):
            rows.append({"subject": config, "question": q, "options": list(ch) if ch is not None else [],
                         "key": int(a) if a is not None else None, "label": kd.normalise_label(et),
                         "correct": ca})
    return rows, shards


def to_row(rec):
    return {"sample_id": rec.get("sample_id"), "subject": rec.get("subject"), "category": rec.get("subject_category"),
            "question": rec.get("question"), "options": [rec.get(c) for c in kd.OPTION_COLS],
            "key": kd.key_index(rec.get("answer")), "label": str(rec.get("cultural_sensitivity_label")),
            "annotated": bool(rec.get("is_annotated"))}


def load_language(urls, keep_question):
    rows, shards = [], []
    for url in urls:
        raw = _get(url)
        shards.append({"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        t = pq.read_table(io.BytesIO(raw))
        cols = {c: t.column(c).to_pylist() for c in cases.GMMLU_COLUMNS if c in t.column_names}
        n = t.num_rows
        del t
        for i in range(n):
            r = to_row({c: cols[c][i] for c in cols})
            if not keep_question:
                r["question"] = None
            rows.append(r)
    return rows, shards


def _count(d, k):
    d[k] = d.get(k, 0) + 1


def _share(a, b):
    return (a / b) if b else None


def predictions(langs, mism_keys, joined, jst, base, redux_ok):
    others = [L for L in langs if L != cases.REFERENCE_LANGUAGE]
    # P1 (structural): 42 configs x 14,042 rows, every row found in English, letter disagreements identical to
    # audit 70's per-language counts, and MMLU-Redux identical to audit 69's 5,700 rows and label counts.
    p1 = (len(langs) == cases.EXPECTED_N_CONFIGS
          and all(langs[L]["tally"]["n_rows"] == cases.EXPECTED_N_ROWS for L in others)
          and all(langs[L]["tally"]["missing_in_reference"] == 0 for L in others)
          and all(langs[L]["tally"]["key_mismatch_all"] == cases.AUDIT70_KEY_MISMATCH.get(L, 0) for L in others)
          and redux_ok)
    # P2 (control): pooled over the 41 translations, at least 99% of resolvable key-AGREEING rows keep every option
    # in its English place.
    same = resolv = 0
    for L in others:
        for cell, n in langs[L]["tally"]["cells"].items():
            letter, order, _answer = cell.split("|")
            if letter == "letter_same" and order != "unresolved":
                resolv += n
                if order == "same_order":
                    same += n
    p2_share = _share(same, resolv)
    p2 = p2_share is not None and p2_share >= cases.P2_MIN_SAME_ORDER
    # P3 (HEADLINE): among resolvable zh + ko disagreements, more than half are a different answer with the options
    # in place (the key moved), not a reordering (vacuous below P3_MIN_RESOLVED).
    kinds = {}
    for L in cases.FOCUS:
        for k, n in langs[L]["tally"]["kinds"].items():
            kinds[k] = kinds.get(k, 0) + n
    resolved = sum(n for k, n in kinds.items() if k != "unresolved")
    moved = kinds.get("different_answer_same_order", 0)
    p3_vac = resolved < cases.P3_MIN_RESOLVED
    p3 = (not p3_vac) and moved * 2 > resolved
    # P4: zh and ko disagree with English on many of the SAME questions (>= 10 shared, chance about 1.5), and give
    # the same new key on at least 80% of them.
    ov = kd.overlap(mism_keys.get("zh", {}), mism_keys.get("ko", {}))
    p4 = ov["shared"] >= cases.P4_MIN_SHARED and ov["same_key"] >= cases.P4_MIN_SAME_KEY * ov["shared"]
    # P5: zh/ko disagreements that join to MMLU-Redux carry an expert error label more than twice as often as all
    # joined rows (vacuous below P5_MIN_JOINED).
    union = sorted(set(mism_keys.get("zh", {})) | set(mism_keys.get("ko", {})))
    prof = kd.redux_profile(union, joined)
    err = prof["classes"].get("error", 0)
    base_share = _share(base["classes"].get("error", 0), base["joined"])
    dis_share = _share(err, prof["joined"])
    p5_vac = prof["joined"] < cases.P5_MIN_JOINED
    p5 = (not p5_vac) and base_share is not None and dis_share is not None and dis_share > cases.P5_MIN_RATIO * base_share
    # P6: on joined miskeyed questions with a one-letter expert correction, the zh/ko disagreeing key equals the
    # correction in more than half of the (language, question) pairs (vacuous below P6_MIN_N).
    c6 = {"n": 0, "equals_correction": 0, "equals_published": 0, "other": 0}
    for L in cases.FOCUS:
        got = kd.correction_agreement(mism_keys.get(L, {}), joined)
        for k in c6:
            c6[k] += got[k]
    p6_vac = c6["n"] < cases.P6_MIN_N
    p6 = (not p6_vac) and c6["equals_correction"] * 2 > c6["n"]
    # P7 (join): at least 95% of the 5,700 MMLU-Redux rows join to Global-MMLU English.
    p7_share = _share(jst["joined"], jst["n_redux"])
    p7 = p7_share is not None and p7_share >= cases.P7_MIN_JOIN_SHARE
    return {
        "P1_structural": bool(p1),
        "P2_agreeing_rows_keep_option_order": bool(p2), "P2_share": p2_share, "P2_resolvable": resolv,
        "P3_disagreements_are_moved_keys": bool(p3), "P3_vacuous": bool(p3_vac), "P3_kinds_zh_ko": kinds,
        "P4_zh_ko_share_disagreements": bool(p4), "P4_overlap": ov,
        "P5_disagreements_enriched_for_expert_errors": bool(p5), "P5_vacuous": bool(p5_vac),
        "P5_profile_zh_ko_union": prof, "P5_error_share_disagreements": dis_share, "P5_error_share_base": base_share,
        "P6_disagreeing_key_equals_correction": bool(p6), "P6_vacuous": bool(p6_vac), "P6_counts": c6,
        "P7_redux_join": bool(p7), "P7_share": p7_share,
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

    # 2) MMLU-Redux: audit 69's rows and labels.
    redux, redux_shards = load_redux()
    redux_labels = {}
    for r in redux:
        _count(redux_labels, r["label"])
    redux_ok = len(redux) == cases.EXPECTED_REDUX_ROWS and redux_labels == cases.EXPECTED_REDUX_LABELS
    print("[redux] rows=%d labels=%s matches audit 69: %s" % (len(redux), dict(sorted(redux_labels.items())),
                                                             redux_ok))

    # 3) Global-MMLU English, then the join.
    urls = {}
    for f in parquet_files(cases.GMMLU_DATASET):
        if f["split"] == cases.GMMLU_SPLIT:
            urls.setdefault(f["config"], []).append(f["url"])
    for L in urls:
        urls[L].sort()
    order = [cases.REFERENCE_LANGUAGE] + sorted(L for L in urls if L != cases.REFERENCE_LANGUAGE)
    print("[configs] %d: %s" % (len(urls), ",".join(order)))
    en_rows, en_shards = load_language(urls[cases.REFERENCE_LANGUAGE], keep_question=True)
    ref = kd.reference(en_rows)
    print("[en] rows=%d valid=%d" % (len(en_rows), len(ref)))
    joined, jst = kd.join_redux(list(ref.values()), redux)
    print("[join-redux] %s" % jst)
    base = kd.redux_profile(sorted(joined), joined)
    print("[redux-base] %s" % base)
    miskey_ids = {s for s, x in joined.items() if x["label"] == kd.MISKEY}
    for r in ref.values():
        r["question"] = None  # question text is needed only for the join

    # 4) Every translation against English.
    langs = {cases.REFERENCE_LANGUAGE: {"tally": {"n_rows": len(en_rows), "reference": True}}}
    shards = {cases.REFERENCE_LANGUAGE: en_shards}
    mism_keys = {}
    for L in order[1:]:
        rows, sh = load_language(urls[L], keep_question=False)
        shards[L] = sh
        tally, mism = kd.tally_language(ref, rows)
        keys = {s: v[0] for s, v in mism.items()}
        mism_keys[L] = keys
        rep = {"tally": tally}
        # the translation's own key on every joined miskeyed question (not only on disagreements)
        all_keys = {r["sample_id"]: r["key"] for r in rows if r["sample_id"] in miskey_ids}
        rep["correction_all_miskeyed"] = kd.correction_agreement(all_keys, joined)
        if mism:
            by_kind_subject, by_subject, labels, annotated = {}, {}, {}, {}
            for s, (_k, kind) in sorted(mism.items()):
                e = ref[s]
                _count(by_subject, e["subject"])
                _count(by_kind_subject, "%s|%s" % (kind, e["subject"]))
                _count(labels, e["label"])
            ann_all = {}
            for r in rows:
                if r["sample_id"] in ref:
                    _count(ann_all, "annotated" if r["annotated"] else "not_annotated")
                    if r["sample_id"] in mism:
                        _count(annotated, "annotated" if r["annotated"] else "not_annotated")
            # pick-longest credit on disagreements with options in place: the translation's key vs English's key,
            # both scored on the translated options (exploratory)
            pl_xx = pl_en = Fraction(0)
            n_pl = 0
            for r in rows:
                v = mism.get(r["sample_id"])
                if v is not None and v[1] == "different_answer_same_order":
                    n_pl += 1
                    pl_xx += kd.pick_longest_credit(r["options"], r["key"])
                    pl_en += kd.pick_longest_credit(r["options"], ref[r["sample_id"]]["key"])
            rep.update({
                "by_subject": dict(sorted(by_subject.items(), key=lambda kv: (-kv[1], kv[0]))),
                "by_kind_subject": dict(sorted(by_kind_subject.items(), key=lambda kv: (-kv[1], kv[0]))),
                "cs_ca_labels": dict(sorted(labels.items())),
                "annotated_disagreements": dict(sorted(annotated.items())),
                "annotated_all_rows": dict(sorted(ann_all.items())),
                "redux_profile": kd.redux_profile(sorted(mism), joined),
                "correction_disagreements": kd.correction_agreement(keys, joined),
                "pick_longest_moved_keys": {"n": n_pl,
                                            "translated_key": float(pl_xx / n_pl) if n_pl else None,
                                            "english_key": float(pl_en / n_pl) if n_pl else None},
            })
        langs[L] = rep
        print("[lang] %-3s n=%d missing=%d invalid=%d mismatch_all=%d (audit 70: %d) kinds=%s cells=%s"
              % (L, tally["n_rows"], tally["missing_in_reference"], tally["invalid"], tally["key_mismatch_all"],
                 cases.AUDIT70_KEY_MISMATCH.get(L, 0), dict(sorted(tally["kinds"].items())),
                 dict(sorted(tally["cells"].items()))))
        if mism:
            print("[lang-detail] %-3s subjects=%s redux=%s corr=%s ann=%s/%s pl=%s"
                  % (L, dict(list(rep["by_subject"].items())[:8]), rep["redux_profile"],
                     rep["correction_disagreements"], rep["annotated_disagreements"], rep["annotated_all_rows"],
                     rep["pick_longest_moved_keys"]))
        del rows

    # 5) Pairwise overlap between the languages with any disagreement.
    with_mism = sorted(L for L in mism_keys if mism_keys[L])
    pairs = {}
    for i, a in enumerate(with_mism):
        for b in with_mism[i + 1:]:
            pairs["%s|%s" % (a, b)] = kd.overlap(mism_keys[a], mism_keys[b])
    print("[overlap] %s" % pairs)

    preds = predictions(langs, mism_keys, joined, jst, base, redux_ok)
    for k, v in preds.items():
        if k.startswith("P") and isinstance(v, bool) and not k.endswith("_vacuous"):
            print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))
    print("[prediction] details P2_share=%s P3_vacuous=%s P3_kinds=%s P4=%s P5 dis=%s base=%s vacuous=%s P6=%s "
          "vacuous=%s P7_share=%s"
          % (preds["P2_share"], preds["P3_vacuous"], preds["P3_kinds_zh_ko"], preds["P4_overlap"],
             preds["P5_error_share_disagreements"], preds["P5_error_share_base"], preds["P5_vacuous"],
             preds["P6_counts"], preds["P6_vacuous"], preds["P7_share"]))

    out = {
        "audit": 71,
        "slug": "mcq-global-mmlu-key-drift",
        "dataset": ("Global-MMLU (CohereLabs/Global-MMLU, Apache-2.0; Singh et al. 2024, arXiv 2412.03304), every "
                    "language config, split test; MMLU-Redux 2.0 (edinburgh-dawg/mmlu-redux-2.0, CC BY 4.0), 57 "
                    "configs, split test; both read from the HuggingFace auto-converted parquet via the "
                    "datasets-server parquet API. Options are matched across languages only by identical text "
                    "(NFKC, stripped) or an identical non-empty number sequence. Only aggregates are written: no "
                    "question or option text."),
        "fixture_target_met": fx_ok,
        "redux": {"rows": len(redux), "labels": dict(sorted(redux_labels.items())), "matches_audit69": redux_ok,
                  "shards": redux_shards},
        "join_redux": jst,
        "redux_base_profile": base,
        "languages": langs,
        "pairwise_overlap": pairs,
        "parquet_shards": shards,
        "predictions": preds,
        "note": ("P1 structural (42 x 14,042; disagreement counts = audit 70; Redux = audit 69). P2 control: >= 99% "
                 "of resolvable key-agreeing rows keep option order. P3 HEADLINE: > half of resolvable zh+ko "
                 "disagreements are a moved key with options in place. P4 zh and ko share >= 10 disagreements and "
                 "give the same key on >= 80% of them. P5 zh/ko disagreements joined to MMLU-Redux carry an error "
                 "label > 2x as often as all joined rows. P6 on letter-corrected Redux miskeys the zh/ko "
                 "disagreeing key equals the correction in > half. P7 >= 95% of Redux rows join. Observational: "
                 "unresolved rows (options that need translation to match) are counted, not guessed."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
