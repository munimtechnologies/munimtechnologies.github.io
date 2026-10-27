"""MMLU per-SUBJECT gold-answer-POSITION census (audit 54).

Audit 53 found MMLU's whole-'all' gold position is skewed toward the LAST option (position 3, 26.7%, rejecting
uniformity at alpha=0.001). This audit asks whether that pooled "answer tends to be last" tilt is a pervasive
authoring convention spread across MMLU's ~57 subjects or an aggregate of a few strongly skewed subjects. It
censuses the 0-based gold position per subject, tests each subject against uniform with a Pearson chi-square
goodness-of-fit, and summarises the cross-subject distribution of tilts.

It reuses the exact-count census core (position_census.py) and the hand-traced fixture (cases.py) from audit
53, and reproduces audit 53's MMLU-all totals as a pooled cross-check. Pre-registers three predictions, each a
finding either way, decided before any real number was seen.

Usage: python job.py --out-dir /out   (network required to fetch the parquet listings and files)
Apache-2.0.
"""

import argparse
import io
import json
import os
import urllib.request

import pyarrow.parquet as pq

import position_census as pc
import cases

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"


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


def parquet_files(hf_dataset, config, wanted_splits):
    data = json.loads(_get(PARQUET_API % hf_dataset).decode("utf-8"))
    out = []
    for f in data["parquet_files"]:
        if f["config"] == config and f["split"] in wanted_splits:
            out.append((f["split"], f["url"]))
    return sorted(out)


def read_mmlu_by_subject(spec):
    """Read MMLU `all`, returning (rows, split_counts). Each row is (subject, labels, texts, gold_index_str)."""
    rows = []
    counts = {}
    cols = [spec["subject_col"], spec["choices_col"], spec["answer_col"]]
    for split, url in parquet_files(spec["hf"], spec["config"], set(spec["splits"])):
        table = pq.read_table(io.BytesIO(_get(url)), columns=cols)
        if spec["subject_col"] not in table.column_names:
            raise RuntimeError("MMLU parquet is missing a 'subject' column: %s" % table.column_names)
        data = {c: table.column(c).to_pylist() for c in cols}
        n = len(data[cols[0]])
        counts[split] = n
        for i in range(n):
            subject = data[spec["subject_col"]][i]
            choices = list(data[spec["choices_col"]][i])
            labels = [str(j) for j in range(len(choices))]
            key = str(data[spec["answer_col"]][i])
            rows.append((subject, labels, choices, key))
    return rows, counts


def cross_subject_predictions(rep, total_valid):
    """Pre-registered real-data predictions, each a finding either way. Decided before any real number seen."""
    subjects = sorted(rep)
    n_subjects = len(subjects)

    # P1 (structural): every subject parses clean (0 bad_key, 0 degenerate), is modal 4-option with coverage
    # >= 0.95, and the per-subject valid counts partition MMLU-all exactly (sum == audit 53's 15,858).
    clean = all(rep[s]["n_bad_key"] == 0 and rep[s]["n_degenerate"] == 0 for s in subjects)
    all_k4 = all(rep[s]["modal_option_count"] == 4 for s in subjects)
    cover_ok = all((rep[s]["modal_coverage"] is not None and rep[s]["modal_coverage"] >= 0.95) for s in subjects)
    sum_valid = sum(rep[s]["n_valid"] for s in subjects)
    partition_ok = (sum_valid == total_valid)
    p1 = clean and all_k4 and cover_ok and partition_ok

    # Subjects summarised at a 4-option modal bucket (all of MMLU, if P1 holds) carry a pos-3 rate.
    k4 = [s for s in subjects if rep[s]["modal_option_count"] == 4]
    pos3_over_chance = [s for s in k4 if rep[s]["modal"]["pos_rates"]["3"] > 0.25]
    best_is_last = [s for s in k4 if rep[s]["modal"]["best_position"] == 3]
    rejecting = [s for s in subjects if rep[s].get("modal") and rep[s]["modal"]["uniform_rejected_0.001"]]

    # P2 (HEADLINE): the "answer tends to be last" tilt is pervasive -- in a strict MAJORITY of subjects the
    # gold sits at the last option (pos 3) more often than chance (rate > 0.25).
    p2 = len(pos3_over_chance) > (len(k4) / 2.0) if k4 else False

    # P3 (concentration): the pooled skew is DIFFUSE, not driven by a few subjects -- fewer than a quarter of
    # subjects individually reject uniformity at alpha=0.001.
    p3 = len(rejecting) < (n_subjects / 4.0) if n_subjects else False

    return {
        "n_subjects": n_subjects,
        "P1_clean_well_defined_and_complete_partition": bool(p1),
        "P1_detail": {"clean": bool(clean), "all_modal_k_is_4": bool(all_k4), "coverage_ge_0.95": bool(cover_ok),
                      "sum_valid": sum_valid, "expected_total_valid": total_valid, "partition_ok": bool(partition_ok)},
        "P2_last_position_tilt_pervasive": bool(p2),
        "P2_detail": {"n_subjects_k4": len(k4), "n_pos3_rate_over_chance": len(pos3_over_chance),
                      "n_best_position_is_last": len(best_is_last)},
        "P3_skew_is_diffuse_not_concentrated": bool(p3),
        "P3_detail": {"n_subjects_rejecting_uniform_0.001": len(rejecting),
                      "subjects_rejecting_uniform_0.001": sorted(rejecting)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Pre-registered synthetic fixture: exact-equality check before any real data is read.
    fixture_census = pc.run_census(cases.FIXTURE_ROWS)
    target_met = (fixture_census == cases.TARGET)
    print("[fixture] run_census == TARGET : %s" % target_met)
    if not target_met:
        raise SystemExit("fixture mismatch -- aborting before real data")

    # 2) Real data: MMLU `all`, keyed by subject.
    rows, split_counts = read_mmlu_by_subject(cases.MMLU)
    print("[load] mmlu splits %s  total_rows=%d" % (split_counts, len(rows)))

    census = pc.run_census(rows)
    report = pc.to_report(census)
    preds = cross_subject_predictions(report, cases.EXPECTED_TOTAL_VALID)

    # Pooled cross-check: re-key every row under "ALL" and confirm it reproduces audit 53's MMLU-all numbers.
    pooled = pc.to_report(pc.run_census([("ALL", a, b, c) for (_s, a, b, c) in rows]))["ALL"]

    # sanity: observed split sizes vs the documented ones
    counts_check = {"observed": split_counts, "expected": cases.EXPECTED_SPLIT_COUNTS,
                    "match": split_counts == cases.EXPECTED_SPLIT_COUNTS}

    # diagnostics (land in summary_tail): headline counts + the three most-skewed subjects by chi-square
    k4 = [s for s in report if report[s]["modal_option_count"] == 4]
    top = sorted(k4, key=lambda s: report[s]["modal"]["chi_square_stat"], reverse=True)[:3]
    pm = pooled["modal"]
    print("[pooled] n=%d pos_rates=%s best_pos=%d best_acc=%.4f chi2=%.1f df=%d rej0.001=%s"
          % (pm["n"], {p: round(r, 4) for p, r in pm["pos_rates"].items()}, pm["best_position"],
             pm["best_position_accuracy"], pm["chi_square_stat"], pm["df"], pm["uniform_rejected_0.001"]))
    print("[cross] n_subjects=%d  pos3_over_chance=%d/%d  best_is_last=%d/%d  reject_uniform_0.001=%d"
          % (preds["n_subjects"], preds["P2_detail"]["n_pos3_rate_over_chance"], preds["P2_detail"]["n_subjects_k4"],
             preds["P2_detail"]["n_best_position_is_last"], preds["P2_detail"]["n_subjects_k4"],
             preds["P3_detail"]["n_subjects_rejecting_uniform_0.001"]))
    for s in top:
        m = report[s]["modal"]
        print("[top] %-34s n=%4d rates=%s chi2=%.1f rej=%s best_pos=%d"
              % (s, m["n"], {p: round(r, 3) for p, r in m["pos_rates"].items()}, m["chi_square_stat"],
                 m["uniform_rejected_0.001"], m["best_position"]))
    print("[prediction] P1_clean_well_defined_and_complete_partition = %s"
          % ("HELD" if preds["P1_clean_well_defined_and_complete_partition"] else "FAILED"))
    print("[prediction] P2_last_position_tilt_pervasive = %s  detail=%s"
          % ("HELD" if preds["P2_last_position_tilt_pervasive"] else "FAILED", preds["P2_detail"]))
    print("[prediction] P3_skew_is_diffuse_not_concentrated = %s  detail=%s"
          % ("HELD" if preds["P3_skew_is_diffuse_not_concentrated"] else "FAILED", preds["P3_detail"]))

    out = {
        "dataset": ("MMLU (cais/mmlu config 'all', test+validation+dev; auxiliary_train excluded as a mix of "
                    "other datasets), read from the HuggingFace auto-converted parquet via the datasets-server "
                    "parquet API. For each question this audit records the 0-based INDEX of the gold option "
                    "within the released option list, keyed by MMLU SUBJECT. Per subject it reports the "
                    "gold-position distribution, a Pearson chi-square goodness-of-fit against a uniform "
                    "distribution, and a best-constant-position baseline; it then summarises the cross-subject "
                    "distribution of tilts and reproduces audit 53's pooled MMLU-all numbers as a cross-check. "
                    "This is a construction property of the benchmark -- where the correct answer was placed -- "
                    "not a model's position / selection bias."),
        "rows_as_expected": counts_check["match"],
        "split_counts_check": counts_check,
        "synthetic_corpus": {"target_met": target_met, "n_fixture_rows": len(cases.FIXTURE_ROWS)},
        "alpha": pc.ALPHA,
        "pooled_mmlu_all": pooled,
        "by_subject": report,
        "predictions": preds,
        "note": ("P1 (structural, finding either way): every subject parses with 0 bad_key and 0 degenerate, is "
                 "modal 4-option with coverage >=95%, and the per-subject valid counts partition MMLU-all "
                 "exactly (sum == audit 53's 15,858). P2 (directional headline, finding either way): the "
                 "'answer tends to be last' tilt is pervasive -- in a strict majority of subjects the gold sits "
                 "at the last option (position 3) more often than chance (rate > 0.25). P3 (concentration, "
                 "finding either way): the pooled skew is diffuse, not concentrated -- fewer than a quarter of "
                 "subjects individually reject uniformity at alpha=0.001. The chi-square statistic and df are "
                 "reported per subject so an exact p-value can be recomputed. Measures construction, not any "
                 "model."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
