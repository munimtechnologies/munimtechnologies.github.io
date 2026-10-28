"""OpenBookQA per-SPLIT gold-answer-POSITION census (audit 55).

Audit 53 found OpenBookQA's gold position (pooled over all of `main`) is skewed toward the FIRST option
(position 0 / "A", 27.6%, rejecting uniformity at alpha=0.001). That pooled number mixes the large train split
with the two 500-question evaluation splits. People report OpenBookQA *test* accuracy, so this audit asks
whether the pos-0/A skew is a property of the reported TEST split or a train-only construction artifact that is
not detectable in the small evaluation splits.

It censuses the 0-based gold position per SPLIT (train / validation / test), tests each split against uniform
with a Pearson chi-square goodness-of-fit, and reproduces audit 53's pooled OpenBookQA numbers as a cross-check.
It reuses the census core (position_census.py) and the hand-traced fixture (cases.py) from audits 53/54
verbatim. Pre-registers three predictions, each a finding either way, decided before any real number was seen.

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


def _extract_choices(choices):
    """Return (labels, texts) from an OpenBookQA `choices` value, handling the two parquet shapes.

    dict-of-arrays: {"text": [...], "label": [...]}  (the usual struct-column shape)
    list-of-structs: [{"text": ..., "label": ...}, ...]
    """
    if isinstance(choices, dict):
        labels = [str(x) for x in list(choices["label"])]
        texts = [x for x in list(choices["text"])]
        return labels, texts
    if isinstance(choices, (list, tuple)):
        labels = [str(c["label"]) for c in choices]
        texts = [c["text"] for c in choices]
        return labels, texts
    raise RuntimeError("unrecognised choices shape: %r" % type(choices))


def read_obqa_by_split(spec):
    """Read OpenBookQA `main`, returning (rows, split_counts). Each row is (split, labels, texts, gold_letter)."""
    rows = []
    counts = {}
    cols = [spec["choices_col"], spec["answer_col"]]
    for split, url in parquet_files(spec["hf"], spec["config"], set(spec["splits"])):
        table = pq.read_table(io.BytesIO(_get(url)), columns=cols)
        if spec["choices_col"] not in table.column_names or spec["answer_col"] not in table.column_names:
            raise RuntimeError("OpenBookQA parquet is missing an expected column: %s" % table.column_names)
        data = {c: table.column(c).to_pylist() for c in cols}
        n = len(data[spec["answer_col"]])
        counts[split] = counts.get(split, 0) + n  # accumulate in case a split spans multiple parquet shards
        for i in range(n):
            labels, texts = _extract_choices(data[spec["choices_col"]][i])
            key = str(data[spec["answer_col"]][i]).strip()
            rows.append((split, labels, texts, key))
    return rows, counts


def split_predictions(rep, pooled_modal, total_valid):
    """Pre-registered real-data predictions, each a finding either way. Decided before any real number seen."""
    splits = sorted(rep)

    # P1 (structural): every split parses clean (0 bad_key, 0 degenerate), is modal 4-option with coverage
    # >= 0.95, the per-split valid counts partition OpenBookQA-main exactly (sum == audit 53's 5,957), AND the
    # pooled re-key reproduces audit 53's OpenBookQA skew (best position is the FIRST option and uniform is
    # rejected at 0.001).
    clean = all(rep[s]["n_bad_key"] == 0 and rep[s]["n_degenerate"] == 0 for s in splits)
    all_k4 = all(rep[s]["modal_option_count"] == 4 for s in splits)
    cover_ok = all((rep[s]["modal_coverage"] is not None and rep[s]["modal_coverage"] >= 0.95) for s in splits)
    sum_valid = sum(rep[s]["n_valid"] for s in splits)
    partition_ok = (sum_valid == total_valid)
    pooled_repro = (pooled_modal["best_position"] == 0 and pooled_modal["uniform_rejected_0.001"] is True)
    p1 = clean and all_k4 and cover_ok and partition_ok and pooled_repro

    test = rep.get("test", {}).get("modal")
    # P2 (HEADLINE): the pos-0/A skew is present in the reported TEST split -- the test gold sits at the first
    # option more often than chance (rate > 0.25) AND the first option is the single most common gold position.
    p2 = bool(test and test["pos_rates"]["0"] > 0.25 and test["best_position"] == 0)

    # P3 (consistency): the skew DIRECTION is consistent -- the first option (pos 0) is the single most common
    # gold position in EVERY split (none flips to a different modal position).
    p3 = all(rep[s].get("modal") and rep[s]["modal"]["best_position"] == 0 for s in splits) if splits else False

    return {
        "n_splits": len(splits),
        "P1_clean_partition_and_pooled_reproduces_audit53": bool(p1),
        "P1_detail": {"clean": bool(clean), "all_modal_k_is_4": bool(all_k4), "coverage_ge_0.95": bool(cover_ok),
                      "sum_valid": sum_valid, "expected_total_valid": total_valid, "partition_ok": bool(partition_ok),
                      "pooled_best_position": pooled_modal["best_position"],
                      "pooled_uniform_rejected_0.001": pooled_modal["uniform_rejected_0.001"]},
        "P2_pos0_skew_present_in_test_split": bool(p2),
        "P2_detail": ({"test_n": test["n"], "test_pos0_rate": test["pos_rates"]["0"],
                       "test_best_position": test["best_position"],
                       "test_uniform_rejected_0.001": test["uniform_rejected_0.001"],
                       "test_chi_square_stat": test["chi_square_stat"]} if test else {"test": "absent"}),
        "P3_pos0_is_modal_in_every_split": bool(p3),
        "P3_detail": {s: rep[s]["modal"]["best_position"] for s in splits if rep[s].get("modal")},
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

    # 2) Real data: OpenBookQA `main`, keyed by split.
    rows, split_counts = read_obqa_by_split(cases.OBQA)
    print("[load] obqa splits %s  total_rows=%d" % (split_counts, len(rows)))

    census = pc.run_census(rows)
    report = pc.to_report(census)

    # Pooled cross-check: re-key every row under "ALL" and confirm it reproduces audit 53's OpenBookQA numbers.
    pooled = pc.to_report(pc.run_census([("ALL", a, b, c) for (_s, a, b, c) in rows]))["ALL"]
    preds = split_predictions(report, pooled["modal"], cases.EXPECTED_TOTAL_VALID)

    counts_check = {"observed": split_counts, "expected": cases.EXPECTED_SPLIT_COUNTS,
                    "match": split_counts == cases.EXPECTED_SPLIT_COUNTS}

    pm = pooled["modal"]
    print("[pooled] n=%d pos_rates=%s best_pos=%d best_acc=%.4f chi2=%.1f df=%d rej0.001=%s"
          % (pm["n"], {p: round(r, 4) for p, r in pm["pos_rates"].items()}, pm["best_position"],
             pm["best_position_accuracy"], pm["chi_square_stat"], pm["df"], pm["uniform_rejected_0.001"]))
    for s in sorted(report):
        m = report[s].get("modal")
        if m:
            print("[split] %-11s n=%4d rates=%s chi2=%.1f df=%d rej=%s best_pos=%d"
                  % (s, m["n"], {p: round(r, 3) for p, r in m["pos_rates"].items()}, m["chi_square_stat"],
                     m["df"], m["uniform_rejected_0.001"], m["best_position"]))
    print("[prediction] P1_clean_partition_and_pooled_reproduces_audit53 = %s"
          % ("HELD" if preds["P1_clean_partition_and_pooled_reproduces_audit53"] else "FAILED"))
    print("[prediction] P2_pos0_skew_present_in_test_split = %s  detail=%s"
          % ("HELD" if preds["P2_pos0_skew_present_in_test_split"] else "FAILED", preds["P2_detail"]))
    print("[prediction] P3_pos0_is_modal_in_every_split = %s  detail=%s"
          % ("HELD" if preds["P3_pos0_is_modal_in_every_split"] else "FAILED", preds["P3_detail"]))

    out = {
        "dataset": ("OpenBookQA (allenai/openbookqa config 'main', train+validation+test), read from the "
                    "HuggingFace auto-converted parquet via the datasets-server parquet API. For each question "
                    "this audit records the 0-based INDEX of the gold option within the released option list, "
                    "keyed by SPLIT. Per split it reports the gold-position distribution, a Pearson chi-square "
                    "goodness-of-fit against a uniform distribution, and a best-constant-position baseline; it "
                    "then reproduces audit 53's pooled OpenBookQA-main numbers as a cross-check. Note the two "
                    "evaluation splits hold only 500 questions each, so a non-rejection there is low power, not "
                    "proof of uniformity -- the raw chi-square and df are reported per split so a reader can "
                    "recompute an exact p-value. This is a construction property of the benchmark -- where the "
                    "correct answer was placed -- not a model's position / selection bias."),
        "rows_as_expected": counts_check["match"],
        "split_counts_check": counts_check,
        "synthetic_corpus": {"target_met": target_met, "n_fixture_rows": len(cases.FIXTURE_ROWS)},
        "alpha": pc.ALPHA,
        "pooled_openbookqa_main": pooled,
        "by_split": report,
        "predictions": preds,
        "note": ("P1 (structural, finding either way): every split parses with 0 bad_key and 0 degenerate, is "
                 "modal 4-option with coverage >=95%, the per-split valid counts partition OpenBookQA-main "
                 "exactly (sum == audit 53's 5,957), and the pooled re-key reproduces audit 53's skew (first "
                 "option is the modal gold position and uniform is rejected at 0.001). P2 (directional headline, "
                 "finding either way): the pos-0/A skew is present in the reported TEST split -- its gold sits "
                 "at the first option more often than chance and the first option is its modal gold position. "
                 "P3 (consistency, finding either way): the first option is the modal gold position in every "
                 "split (the skew direction does not flip across splits). Measures construction, not any model."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
