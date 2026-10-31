"""Global-MMLU LENGTH census (audit 70): culturally sensitive vs agnostic questions, and 42 languages.

Global-MMLU (Singh et al. 2024, arXiv 2412.03304; Apache-2.0) translates MMLU's 14,042 test questions into 42
languages and labels 2,850 of them Culturally Sensitive (CS, 792) or Culturally Agnostic (CA, 2,058). Its paper
reports no answer-length analysis. Audits 52/60 found MMLU's "pick the longest option" floor (0.2805 vs 0.25)
concentrated in law/clinical/social subjects. This job measures, on the released rows:

1. whether the English rows are MMLU's test rows (joined by sample_id to cais/mmlu), and MMLU `all` reproducing
   audit 60's pooled numbers;
2. the length floor on CS vs CA questions (raw and stratified by subject) and per subject category;
3. per language: the floor, its ratio to the English lift, the CS - CA difference on the English CS/CA split,
   answer-key and label agreement with English, and how often English's unique longest option stays the unique
   longest after translation.

Nine predictions were written down (below) before any real number was seen. Only aggregates are written out: no
question or option text.

Usage: python job.py --out-dir /out   (network: HF datasets-server parquet API and the mcq-length-floor release)
Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import argparse
import hashlib
import importlib.util
import io
import json
import os
import urllib.request

import pyarrow.parquet as pq

import cases
import gmmlu_length as gl

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


def _clean(d):
    """A report without its exact Fraction (not JSON)."""
    return {k: v for k, v in d.items() if k != "exact"}


def fixture_summary():
    en = [gl.to_row(r) for r in cases.FIXTURE_EN]
    xx = [gl.to_row(r) for r in cases.FIXTURE_XX]
    c = gl.census(en)
    out = {"en_n_rows": c["n_rows"], "en_n_invalid": c["n_invalid"], "en_labels": c["labels"]}
    for s in ("ALL", "label=CS", "label=CA", "label=unlabelled", "cat=STEM", "cat=Humanities", "label=CA|cat=STEM"):
        out["en_" + s] = gl.exact(c["accs"][s])
    out["en_diff_exact"] = gl.diff_report(c["accs"]["label=CS"], c["accs"]["label=CA"])["exact"]
    st = gl.stratified_diff(c["strata"])
    out["en_stratified_exact"] = st["exact"]
    out["en_stratified_n_used"] = st["n_strata_used"]
    ref = gl.build_reference(en)
    out["xx_compare"] = gl.compare_to_reference(ref, xx)
    cx = gl.census(gl.relabel(xx, ref))
    out["xx_ALL"] = gl.exact(cx["accs"]["ALL"])
    out["xx_diff_exact"] = gl.diff_report(cx["accs"]["label=CS"], cx["accs"]["label=CA"])["exact"]
    out["mmlu_join"] = gl.compare_to_mmlu(en, cases.FIXTURE_MMLU)
    return out


def parquet_files(dataset):
    return json.loads(_get(PARQUET_API % dataset).decode("utf-8"))["parquet_files"]


def load_mmlu():
    """cais/mmlu `all` rows per split (subject, options, key) in file order, and shard sha256s."""
    files = sorted((f["split"], f["url"]) for f in parquet_files(cases.MMLU_DATASET)
                   if f["config"] == cases.MMLU_CONFIG and f["split"] in cases.MMLU_SPLITS)
    by_split, shards = {}, []
    for split, url in files:
        raw = _get(url)
        shards.append({"split": split, "url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        cols = pq.read_table(io.BytesIO(raw), columns=["subject", "choices", "answer"]).to_pydict()
        for s, ch, a in zip(cols["subject"], cols["choices"], cols["answer"]):
            by_split.setdefault(split, []).append({"subject": s, "options": list(ch) if ch is not None else None,
                                                   "key": int(a) if a is not None else None})
    return by_split, shards


def load_language(url):
    """Rows of one Global-MMLU config, the raw label histogram, missing columns and the shard sha256."""
    raw = _get(url)
    t = pq.read_table(io.BytesIO(raw))
    missing = [c for c in cases.GMMLU_COLUMNS if c not in t.column_names]
    cols = {c: t.column(c).to_pylist() for c in cases.GMMLU_COLUMNS if c in t.column_names}
    n = t.num_rows
    del t
    raw_labels = {}
    rows = []
    for i in range(n):
        rec = {c: cols[c][i] for c in cols}
        lab = rec.get("cultural_sensitivity_label")
        raw_labels[str(lab)] = raw_labels.get(str(lab), 0) + 1
        rows.append(gl.to_row(rec))
    return rows, raw_labels, missing, {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def tool_check(rows, out_dir, mine):
    """Re-run the English ALL slice with the published mcq-length-floor 0.1.0 and compare with this module."""
    try:
        raw = _get(cases.TOOL_URL)
    except RuntimeError as e:
        return {"status": "unavailable", "error": str(e)}
    path = os.path.join(out_dir, "_tool_mcq_length_floor.py")
    with open(path, "wb") as fh:
        fh.write(raw)
    spec = importlib.util.spec_from_file_location("mcq_length_floor_v010", path)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    recs = [{"options": r["options"], "answer": r["key"]} for r in rows if gl.is_valid(r["options"], r["key"])]
    reports, skipped = tool.census(recs, options_col="options", answer_col="answer")
    os.remove(path)
    t = reports.get("ALL", {})
    keys = ("n", "chance", "pick_longest", "pick_shortest", "lift")
    agree = all(t.get(k) == mine.get(k) for k in keys) and not skipped
    return {"status": "agree" if agree else "MISMATCH", "tool_version": getattr(tool, "__version__", None),
            "tool_sha256": hashlib.sha256(raw).hexdigest(), "tool_all": {k: t.get(k) for k in keys},
            "tool_skipped": skipped}


def _z(x):
    return "%.2f" % x if x is not None else "-"


def predictions(langs, en, mmlu_floor, join):
    """Pre-registered, each a finding either way; decided before any real number was seen."""
    others = [L for L in langs if L != cases.REFERENCE_LANGUAGE]
    # P1 (structural): 42 configs, 14,042 test rows each; English has 792 CS and 2,058 CA and 0 invalid rows.
    p1 = (len(langs) == cases.EXPECTED_N_CONFIGS and all(langs[L]["n_rows"] == cases.EXPECTED_N_ROWS for L in langs)
          and en["labels"].get("CS") == cases.EXPECTED_CS and en["labels"].get("CA") == cases.EXPECTED_CA
          and en["n_invalid"] == 0)
    # P2 (reproduction): MMLU `all` (test + validation + dev) gives n 15,858 and pick-longest 0.2805 (4 dp).
    p2 = (mmlu_floor.get("n") == cases.MMLU_REFERENCE["n"]
          and round(mmlu_floor.get("pick_longest", -1), 4) == cases.MMLU_REFERENCE["pick_longest_4dp"])
    # P3: at least 99% of English rows are identical to MMLU test (all four options and the key), joined by id.
    p3_share = join["all_equal"] / join["n_rows"] if join["n_rows"] else 0.0
    p3 = p3_share >= cases.P3_MIN_JOIN_SHARE
    # P4 (HEADLINE): in English, CS questions carry a larger pick-longest lift than CA questions (direction only).
    d = en["cs_minus_ca"]["diff"]
    p4 = d is not None and d > 0
    # P5: stratifying by subject shrinks the CS - CA difference (|stratified| < |raw|): subject mix explains part.
    s = en["cs_minus_ca_by_subject"]["estimate"]
    p5 = d is not None and s is not None and abs(s) < abs(d)
    # P6: every non-English language keeps 0.80 to 1.25 of the English lift.
    lo, hi = cases.P6_RATIO_RANGE
    ratios = [langs[L]["lift_ratio_to_en"] for L in others]
    p6 = bool(ratios) and all(r is not None and lo <= r <= hi for r in ratios)
    # P7: in every language pick-longest beats chance with z > 3.29.
    p7 = all(langs[L]["ALL"].get("z") is not None and langs[L]["ALL"]["z"] > cases.Z_CRIT_0001 for L in langs)
    # P8: every language has English's answer key for every row (0 key mismatches, 0 ids missing either way).
    p8 = all(langs[L]["compare_to_en"]["key_mismatch"] == 0 and langs[L]["compare_to_en"]["missing_in_reference"] == 0
             and langs[L]["compare_to_en"]["reference_ids_absent"] == 0 for L in others)
    # P9: the CS - CA difference has the English sign in at least 38 of the 41 other languages.
    same = sum(1 for L in others if d is not None and langs[L]["cs_minus_ca"]["diff"] is not None
               and (langs[L]["cs_minus_ca"]["diff"] > 0) == (d > 0))
    p9 = d is not None and same >= cases.P9_MIN_SAME_SIGN
    return {
        "P1_structural": bool(p1),
        "P2_mmlu_all_reproduces_audit60": bool(p2),
        "P3_english_rows_are_mmlu_test": bool(p3),
        "P3_share_identical": p3_share,
        "P4_cs_lift_above_ca": bool(p4),
        "P5_subject_stratification_shrinks_gap": bool(p5),
        "P6_every_language_keeps_0.80_to_1.25": bool(p6),
        "P6_ratio_min": min(r for r in ratios if r is not None) if any(r is not None for r in ratios) else None,
        "P6_ratio_max": max(r for r in ratios if r is not None) if any(r is not None for r in ratios) else None,
        "P7_every_language_floor_above_chance": bool(p7),
        "P8_keys_identical_to_english": bool(p8),
        "P9_cs_ca_sign_kept": bool(p9),
        "P9_same_sign_count": same,
    }


def language_report(c, cmp_):
    floors = {s: gl.floor_report(a) for s, a in sorted(c["accs"].items())}
    return {
        "n_rows": c["n_rows"],
        "n_invalid": c["n_invalid"],
        "labels": dict(sorted(c["labels"].items())),
        "ALL": floors.get("ALL", {"n": 0}),
        "label=CS": floors.get("label=CS", {"n": 0}),
        "label=CA": floors.get("label=CA", {"n": 0}),
        "cs_minus_ca": _clean(gl.diff_report(c["accs"].get("label=CS", gl.new_acc()),
                                             c["accs"].get("label=CA", gl.new_acc()))),
        "cs_minus_ca_by_subject": _clean(gl.stratified_diff(c["strata"])),
        "compare_to_en": cmp_,
        "floors": floors,
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

    # 2) MMLU: audit 60's pooled numbers, and the test split for the English join.
    mmlu, mmlu_shards = load_mmlu()
    acc = gl.new_acc()
    mmlu_invalid = 0
    for split in cases.MMLU_SPLITS:
        for r in mmlu.get(split, []):
            if gl.is_valid(r["options"], r["key"]):
                gl.add(acc, r["options"], r["key"])
            else:
                mmlu_invalid += 1
    mmlu_floor = gl.floor_report(acc)
    print("[mmlu-all] splits=%s n=%d invalid=%d longest=%.4f chance=%.4f (audit 60: n 15858, longest 0.2805)"
          % ({s: len(v) for s, v in mmlu.items()}, mmlu_floor["n"], mmlu_invalid, mmlu_floor["pick_longest"],
             mmlu_floor["chance"]))

    # 3) Global-MMLU, English first, then every other language against it.
    files = sorted((f["config"], f["url"]) for f in parquet_files(cases.GMMLU_DATASET)
                   if f["split"] == cases.GMMLU_SPLIT)
    urls = {}
    for config, url in files:
        urls.setdefault(config, []).append(url)
    order = [cases.REFERENCE_LANGUAGE] + sorted(L for L in urls if L != cases.REFERENCE_LANGUAGE)
    print("[configs] %d: %s ; shards per config max %d" % (len(urls), ",".join(order),
                                                             max(len(v) for v in urls.values())))

    langs, shards, raw_label_hist, missing_cols = {}, {}, {}, {}
    ref = join = en_tool = None
    en_lift = None
    for L in order:
        rows, sh, raw_labels, missing = [], [], {}, []
        for url in urls[L]:
            r_, rl_, m_, s_ = load_language(url)
            rows.extend(r_)
            sh.append(s_)
            for k, v in rl_.items():
                raw_labels[k] = raw_labels.get(k, 0) + v
            missing.extend(m_)
        shards[L] = sh
        raw_label_hist[L] = dict(sorted(raw_labels.items()))
        if missing:
            missing_cols[L] = sorted(set(missing))
        if L == cases.REFERENCE_LANGUAGE:
            ref = gl.build_reference(rows)
            join = gl.compare_to_mmlu(rows, mmlu.get("test", []))
            print("[join-mmlu] %s" % join)
            cmp_ = {"reference": True}
            c = gl.census(rows)
            rep = language_report(c, cmp_)
            en_lift = rep["ALL"]["lift"]
            en_tool = tool_check(rows, args.out_dir, rep["ALL"])
            print("[tool] %s %s" % (en_tool["status"], en_tool.get("tool_all")))
            if en_tool["status"] == "MISMATCH":
                raise SystemExit("mcq-length-floor 0.1.0 disagrees with this module on English ALL -- aborting")
        else:
            cmp_ = gl.compare_to_reference(ref, rows)
            c = gl.census(gl.relabel(rows, ref))
            rep = language_report(c, cmp_)
        lift = rep["ALL"].get("lift")
        rep["lift_ratio_to_en"] = (lift / en_lift) if (lift is not None and en_lift) else None
        if L != cases.REFERENCE_LANGUAGE:
            rep["same_unique_longest_share"] = ((cmp_["same_unique_longest"] / cmp_["ref_unique_longest"])
                                                if cmp_["ref_unique_longest"] else None)
            del rep["floors"]
        langs[L] = rep
        a, cs_, ca_, dd = rep["ALL"], rep["label=CS"], rep["label=CA"], rep["cs_minus_ca"]
        print("[lang] %-3s n=%5d invalid=%d longest=%.4f shortest=%.4f lift=%+.4f z=%s ratio=%s | CS %.4f (n %d) "
              "CA %.4f (n %d) diff=%s z=%s | strat=%s | keys!=en %s labels!=en %s same-unique-longest %s"
              % (L, rep["n_rows"], rep["n_invalid"], a.get("pick_longest", float("nan")),
                 a.get("pick_shortest", float("nan")), a.get("lift", float("nan")), _z(a.get("z")),
                 "%.3f" % rep["lift_ratio_to_en"] if rep["lift_ratio_to_en"] is not None else "-",
                 cs_.get("pick_longest", float("nan")), cs_["n"], ca_.get("pick_longest", float("nan")), ca_["n"],
                 "%+.4f" % dd["diff"] if dd["diff"] is not None else "-", _z(dd["z"]),
                 "%+.4f" % rep["cs_minus_ca_by_subject"]["estimate"]
                 if rep["cs_minus_ca_by_subject"]["estimate"] is not None else "-",
                 cmp_.get("key_mismatch", 0), cmp_.get("label_mismatch", 0),
                 "%.4f" % rep["same_unique_longest_share"] if rep.get("same_unique_longest_share") is not None
                 else "-"))

    en = langs[cases.REFERENCE_LANGUAGE]
    for s, r in en["floors"].items():
        if s.startswith(("cat=", "label=")):
            print("[en-floor] %-40s n=%5d longest=%.4f shortest=%.4f lift=%+.4f z=%s"
                  % (s, r["n"], r["pick_longest"], r["pick_shortest"], r["lift"], _z(r["z"])))
    print("[en-raw-labels] %s" % raw_label_hist.get(cases.REFERENCE_LANGUAGE))

    preds = predictions(langs, en, mmlu_floor, join)
    for k, v in preds.items():
        if isinstance(v, bool):
            print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))
    print("[prediction] P3_share=%.5f P6 range=[%s, %s] P9 same-sign=%d"
          % (preds["P3_share_identical"], preds["P6_ratio_min"], preds["P6_ratio_max"], preds["P9_same_sign_count"]))

    out = {
        "audit": 70,
        "slug": "mcq-global-mmlu-length-census",
        "dataset": ("Global-MMLU (CohereLabs/Global-MMLU, Apache-2.0; Singh et al. 2024, arXiv 2412.03304), every "
                    "language config, split test; MMLU (cais/mmlu, MIT) config all, splits test/validation/dev; both "
                    "read from the HuggingFace auto-converted parquet via the datasets-server parquet API. Lengths "
                    "are characters after stripping (as mcq-length-floor 0.1.0). CS/CA labels are English's for "
                    "every language. Only aggregates are written: no question or option text."),
        "fixture_target_met": fx_ok,
        "mmlu_all": {"floor": mmlu_floor, "invalid": mmlu_invalid, "rows_by_split": {s: len(v) for s, v in
                                                                                    mmlu.items()},
                     "reference": cases.MMLU_REFERENCE, "shards": mmlu_shards},
        "english_vs_mmlu_test": join,
        "tool_check": en_tool,
        "languages": langs,
        "raw_label_histograms": raw_label_hist,
        "missing_columns": missing_cols,
        "parquet_shards": shards,
        "predictions": preds,
        "note": ("P1 structural (42 configs x 14,042 rows; English 792 CS, 2,058 CA, 0 invalid). P2 MMLU all "
                 "reproduces audit 60 (n 15,858, pick-longest 0.2805). P3 >= 99% of English rows identical to MMLU "
                 "test in options and key. P4 HEADLINE English CS lift > CA lift (direction only). P5 subject "
                 "stratification shrinks |CS - CA|. P6 every language keeps 0.80-1.25 of the English lift. P7 every "
                 "language z > 3.29. P8 every language has English's keys and ids. P9 CS - CA keeps English's sign in "
                 ">= 38 of 41 languages. CS n = 792 gives roughly a 2-point standard error on the CS - CA gap, so "
                 "P4 is direction only. Observational: a length cue is a property of how options were written, "
                 "translated and keyed."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
