"""MMLU-Redux META-OPTION x ANNOTATION-ERROR census (audit 58): are "all of the above" questions more often wrong?

Audit 56 showed MMLU's last-option ("the answer is D") tilt is mostly an "all of the above"/meta-option artifact:
meta options are 4.86% of MMLU questions, sit last 92.5% of the time, and are the gold 59.6% of the time. MMLU-
Redux 2.0 (Gema et al. 2024, arXiv 2406.04127; CC BY 4.0) has expert error labels for 100 questions from each of
MMLU's 57 subjects. Its paper reports error rates by subject and by error type, but not by option type.

This audit classifies every MMLU-Redux question with audit 56's exact meta-option classifier and cross-tabulates
the categories against the expert error labels: pooled, and stratified by subject (Cochran-Mantel-Haenszel),
because meta options cluster in a few subjects and error rates vary strongly by subject. It pre-registers four
predictions, each a finding either way, decided before any real number was seen.

Usage: python job.py --out-dir /out   (network required to fetch the parquet listing and files)
Apache-2.0.
"""

import argparse
import io
import json
import os
import urllib.request

import pyarrow.parquet as pq

import position_census as pc
import meta_option as mo
import error_census as ec
import cases

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"
N_EXAMPLES = 8


def _get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry transient network errors
            last = e
    raise RuntimeError("GET failed after %d tries: %s (%s)" % (tries, url, last))


def parquet_files(hf_dataset, split):
    """Sorted (config, url) pairs for every parquet shard of the given split."""
    data = json.loads(_get(PARQUET_API % hf_dataset).decode("utf-8"))
    return sorted((f["config"], f["url"]) for f in data["parquet_files"] if f["split"] == split)


def read_columns(url, cols):
    table = pq.read_table(io.BytesIO(_get(url)), columns=cols)
    return {c: table.column(c).to_pylist() for c in cols}


def load_redux():
    """Rows (subject, labels, texts, answer_key, error_type) and per-subject row counts."""
    rows = []
    counts = {}
    for config, url in parquet_files(cases.HF_DATASET, cases.SPLIT):
        data = read_columns(url, ["choices", "answer", "error_type"])
        n = len(data["choices"])
        for ch, ans, et in zip(data["choices"], data["answer"], data["error_type"]):
            labels, texts, key = ec.shape_mmlu(ch, ans)
            rows.append((config, labels, texts, key, et))
        counts[config] = counts.get(config, 0) + n  # accumulate in case a subject spans multiple shards
    return rows, counts


def meta_gold_split(rows):
    """For aota/nota/letterref questions: error labels split by whether a meta option is the keyed gold."""
    out = {}
    for _s, labels, texts, key, et in rows:
        if pc.question_validity(labels, texts, key) != "valid":
            continue
        cat = mo.classify_question(texts)
        if cat not in ("aota", "nota", "letterref"):
            continue
        idxs = mo.meta_indices(texts, cat)
        grp = "%s|%s" % (cat, "meta_is_gold" if labels.index(key) in idxs else "meta_not_gold")
        lab = ec.normalise_label(et)
        c = out.setdefault(grp, {})
        c[lab] = c.get(lab, 0) + 1
    return {g: ec.summarise_counts(out[g]) for g in sorted(out)}


def position_by_error(rows):
    """Gold-position census keyed by error class, and by (meta group, error class)."""
    by_class = []
    by_group_class = []
    for _s, labels, texts, key, et in rows:
        cls = ec.error_class(ec.normalise_label(et))
        by_class.append((cls, labels, texts, key))
        if pc.question_validity(labels, texts, key) == "valid":
            grp = "plain" if mo.classify_question(texts) == "plain" else "any_meta"
            by_group_class.append(("%s|%s" % (grp, cls), labels, texts, key))
    return pc.to_report(pc.run_census(by_class)), pc.to_report(pc.run_census(by_group_class))


def flagged_meta_examples(rows):
    ex = []
    for subj, labels, texts, key, et in rows:
        if len(ex) >= N_EXAMPLES:
            break
        if pc.question_validity(labels, texts, key) != "valid":
            continue
        cat = mo.classify_question(texts)
        lab = ec.normalise_label(et)
        if cat != "plain" and ec.error_class(lab) == "error":
            ex.append({"subject": subj, "category": cat, "choices": texts, "answer_index": int(key),
                       "error_type": lab})
    return ex


def predictions(rep, pos_by_class):
    """Pre-registered predictions, each a finding either way. Decided before any real number was seen."""
    # P1 (structural): 57 subjects and 5,700 rows load, every question is valid, and every error label is one of
    # the seven documented values.
    p1 = (rep["n_subjects"] == cases.EXPECTED_N_SUBJECTS and rep["n_rows"] == cases.EXPECTED_N_ROWS
          and rep["n_invalid"] == 0 and not rep["undocumented_labels"])

    # P2 (HEADLINE): within subject, meta-option questions are flagged as erroneous more often than plain ones:
    # CMH chi-square (df 1) > 3.841 (alpha 0.05) AND a positive association (observed - expected > 0).
    c = rep["meta_vs_plain_error_by_subject_cmh"]
    p2 = c["cmh_stat"] is not None and c["cmh_stat"] > ec.CHI2_CRIT_1DF_005 and c["sum_observed_minus_expected"] > 0

    # P3: "all of the above" questions carry more ANSWER-SET errors (no correct answer / multiple correct answers)
    # than plain questions, pooled (direction only; vacuous if fewer than P3_MIN_N judged aota questions).
    aota = rep["by_category"].get("aota", ec.summarise_counts({}))
    plain = rep["by_group"]["plain"]
    p3_vac = aota["n_judged"] < cases.P3_MIN_N
    p3 = ((not p3_vac) and plain["answer_set_error_rate"] is not None
          and aota["answer_set_error_rate"] > plain["answer_set_error_rate"])

    # P4: the last-option tilt is not an error artifact: among questions judged OK (k = 4), the last position is
    # the single most common gold position.
    m = pos_by_class.get("ok", {}).get("modal")
    p4 = m is not None and m["df"] == 3 and m["best_position"] == 3

    return {
        "P1_clean_load_and_documented_labels": bool(p1),
        "P1_detail": {"n_subjects": rep["n_subjects"], "n_rows": rep["n_rows"], "n_invalid": rep["n_invalid"],
                      "undocumented_labels": rep["undocumented_labels"]},
        "P2_meta_flagged_more_within_subject": bool(p2),
        "P2_detail": c,
        "P3_aota_more_answer_set_errors": bool(p3),
        "P3_detail": {"aota_judged": aota["n_judged"], "aota_rate": aota["answer_set_error_rate"],
                      "plain_rate": plain["answer_set_error_rate"], "vacuous": bool(p3_vac),
                      "min_n": cases.P3_MIN_N},
        "P4_ok_subset_last_is_modal": bool(p4),
        "P4_detail": m,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Pre-registered synthetic fixtures: exact-equality checks before any real data is read.
    pos_ok = (pc.run_census(cases.FIXTURE_ROWS) == cases.TARGET)
    meta_ok = (mo.run_meta_census(cases.META_FIXTURE_ROWS) == cases.META_TARGET)
    err_ok = (ec.run_error_census(cases.ERROR_FIXTURE_ROWS) == cases.ERROR_TARGET)
    print("[fixture] position == TARGET : %s ; meta == META_TARGET : %s ; error == ERROR_TARGET : %s"
          % (pos_ok, meta_ok, err_ok))
    if not (pos_ok and meta_ok and err_ok):
        raise SystemExit("fixture mismatch -- aborting before real data")

    # 2) Real data.
    rows, counts = load_redux()
    print("[load] subjects=%d rows=%d" % (len(counts), len(rows)))
    rep = ec.error_report(ec.run_error_census(rows))
    for g in ("plain", "any_meta", "all"):
        s = rep["by_group"][g]
        print("[group] %-8s n=%5d judged=%5d error=%4d rate=%s answer_set_rate=%s unsure=%d unknown=%d"
              % (g, s["n"], s["n_judged"], s["n_error"], s["error_rate"], s["answer_set_error_rate"],
                 s["n_unsure"], s["n_unknown"]))
    for cat, s in sorted(rep["by_category"].items()):
        print("[category] %-9s n=%5d judged=%5d error_rate=%s answer_set_rate=%s labels=%s"
              % (cat, s["n"], s["n_judged"], s["error_rate"], s["answer_set_error_rate"], s["label_counts"]))
    print("[pooled-2x2] %s" % rep["meta_vs_plain_error_pooled"])
    print("[cmh-error] %s" % rep["meta_vs_plain_error_by_subject_cmh"])
    print("[cmh-answer-set] %s" % rep["meta_vs_plain_answer_set_by_subject_cmh"])
    print("[undocumented-labels] %s" % rep["undocumented_labels"])

    mg = meta_gold_split(rows)
    for g, s in mg.items():
        print("[meta-gold] %-28s n=%4d judged=%4d error_rate=%s" % (g, s["n"], s["n_judged"], s["error_rate"]))

    pos_by_class, pos_by_group_class = position_by_error(rows)
    for key, r in sorted(pos_by_class.items()):
        m = r.get("modal")
        if m:
            print("[position] %-8s n=%5d pos_rates=%s best=%d chi2=%.2f"
                  % (key, m["n"], {q: round(x, 4) for q, x in m["pos_rates"].items()}, m["best_position"],
                     m["chi_square_stat"]))

    preds = predictions(rep, pos_by_class)
    for name in ("P1_clean_load_and_documented_labels", "P2_meta_flagged_more_within_subject",
                 "P3_aota_more_answer_set_errors", "P4_ok_subset_last_is_modal"):
        print("[prediction] %s = %s" % (name, "HELD" if preds[name] else "FAILED"))

    out = {
        "dataset": ("MMLU-Redux 2.0 (edinburgh-dawg/mmlu-redux-2.0, CC BY 4.0; Gema et al. 2024, arXiv 2406.04127): "
                    "100 expert-re-annotated questions from each of MMLU's 57 subjects, read from the HuggingFace "
                    "auto-converted parquet via the datasets-server parquet API. Every question is classified into "
                    "ONE meta-option category (roman > aota > nota > letterref > plain; meta_option.py, unchanged "
                    "from audit 56) and cross-tabulated against its error_type label. Error rates are over judged "
                    "questions (ok + five error types); 'expert' (annotators unsure) is counted but excluded from "
                    "rates. This measures the benchmark's construction and annotation, not any model."),
        "synthetic_corpus": {"position_target_met": pos_ok, "meta_target_met": meta_ok, "error_target_met": err_ok},
        "subject_row_counts": counts,
        "mmlu_reference_audit56": cases.MMLU_REFERENCE,
        "report": rep,
        "meta_gold_split": mg,
        "gold_position_by_error_class": pos_by_class,
        "gold_position_by_group_and_error_class": pos_by_group_class,
        "flagged_meta_examples": flagged_meta_examples(rows),
        "predictions": preds,
        "note": ("P1 (structural): 57 subjects / 5,700 rows, all valid, all labels documented. P2 (headline): within "
                 "subject, meta-option questions are flagged as erroneous more often than plain ones (CMH > 3.841, "
                 "positive direction). P3: 'all of the above' questions carry more answer-set errors (no correct / "
                 "multiple correct) than plain ones, pooled (direction only; vacuous below 30 judged). P4: among "
                 "questions judged OK, the last position is the modal gold position. Each is a finding either way. "
                 "The classifier is regex-based and conservative; flagged examples are listed for audit."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
