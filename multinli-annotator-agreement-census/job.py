"""Run the MultiNLI annotator-agreement / gold-derivation census on the official release.

The runner downloads multinli_1.0.zip (job.json data_urls) to the data dir. This script asserts the
hand-traced fixture BEFORE touching real data, reads the three raw jsonl splits straight from the zip
(train + the two dev sets; the test sets ship without labels and are not in this file), verifies for
every split that gold_label is the strict majority of annotator_labels and that every "-" row lacks a
majority, measures the per-split no-consensus counts and annotator profile, checks the MultiNLI-specific
structural expectation that train is unvalidated single-label while the two dev splits are 5-way
validated, records pre-registered predictions, and writes results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from nli_agreement import agreement_stats, flatten, parse_row

SPLITS = cases.SPLITS


def _find_member(zf, split):
    """Return the zip member name for multinli_1.0_<split>.jsonl, tolerating the top-level folder."""
    want = "multinli_1.0_%s.jsonl" % split
    for name in zf.namelist():
        if name.endswith(want) and not name.endswith("/"):
            return name
    return None


def read_split(zip_path, split):
    """Stream one MultiNLI jsonl split from the zip into parsed {gold, annotators} records."""
    recs = []
    with zipfile.ZipFile(zip_path) as zf:
        member = _find_member(zf, split)
        if member is None:
            return None
        with zf.open(member) as fh:
            for raw in fh:
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                recs.append(parse_row(json.loads(line)))
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix = flatten(agreement_stats([parse_row(o) for o in cases.FIXTURE]))
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    for k in cases.TARGET:
        print("  %-30s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Locate the MultiNLI zip.
    zips = sorted(glob.glob(os.path.join(args.data_dir, "*.zip")))
    print("[diag] zip files in data dir:", zips)
    if not zips:
        print("FATAL: no multinli zip found in data dir", file=sys.stderr)
        sys.exit(3)
    zip_path = zips[0]

    # 3. Read the three raw splits and run the per-split census.
    per_split = {}
    rows_as_expected = True
    for split in SPLITS:
        recs = read_split(zip_path, split)
        if recs is None:
            print("FATAL: split %s not found in zip" % split, file=sys.stderr)
            sys.exit(4)
        stats = agreement_stats(recs)
        per_split[split] = stats
        exp_total = cases.RAW_SPLIT_TOTAL[split]
        ok = stats["n_total"] == exp_total
        rows_as_expected = rows_as_expected and ok
        print("[census] %-14s n_total=%d (expect %d, ok=%s) labeled=%d no_consensus=%d "
              "gold_mismatch=%d labeled_without_majority=%d no_consensus_with_majority=%d "
              "multi=%d unanimous_multi=%d hist=%s" % (
                  split, stats["n_total"], exp_total, ok, stats["n_labeled"], stats["n_no_consensus"],
                  stats["n_gold_mismatch_majority"], stats["n_labeled_without_majority"],
                  stats["n_no_consensus_with_majority"], stats["n_multi"], stats["n_unanimous_multi"],
                  stats["agreement_hist"]))

    # 4. Pre-registered predictions (held/failed reported honestly).
    total_mismatch = sum(per_split[s]["n_gold_mismatch_majority"] for s in SPLITS)
    total_labeled_no_majority = sum(per_split[s]["n_labeled_without_majority"] for s in SPLITS)
    total_consensus_anomaly = sum(per_split[s]["n_no_consensus_with_majority"] for s in SPLITS)
    no_consensus_counts = {s: per_split[s]["n_no_consensus"] for s in SPLITS}

    train = per_split["train"]
    dev_m = per_split["dev_matched"]
    dev_mm = per_split["dev_mismatched"]
    train_single_label = (train["agreement_hist"] == cases.TRAIN_EXPECTED_HIST
                          and train["n_no_consensus"] == 0 and train["n_multi"] == 0)
    dev_fully_multi = (dev_m["n_multi"] == dev_m["n_total"] and dev_mm["n_multi"] == dev_mm["n_total"])

    predictions = {
        "P1_gold_is_strict_majority_everywhere": (total_mismatch == 0) and (total_labeled_no_majority == 0),
        "P2_no_consensus_rows_have_no_majority": total_consensus_anomaly == 0,
        "P3_train_unvalidated_single_label_dev_fully_validated": train_single_label and dev_fully_multi,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))
    print("[diag] no_consensus_counts =", no_consensus_counts)
    print("[diag] train_single_label =", train_single_label, "dev_fully_multi =", dev_fully_multi)

    out = {
        "dataset": "MultiNLI 1.0 (Williams, Nangia and Bowman, 2018), OANC-derived, released for research "
                   "-- the raw train/dev_matched/dev_mismatched jsonl splits read straight from "
                   "multinli_1.0.zip, each row carrying an annotator_labels list and a single gold_label",
        "raw_split_total_expected": cases.RAW_SPLIT_TOTAL,
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "per_split": per_split,
        "totals": {
            "n_gold_mismatch_majority": total_mismatch,
            "n_labeled_without_majority": total_labeled_no_majority,
            "n_no_consensus_with_majority": total_consensus_anomaly,
            "no_consensus_counts": no_consensus_counts,
            "train_single_label": train_single_label,
            "dev_fully_multi": dev_fully_multi,
        },
        "predictions": predictions,
        "note": "For each MultiNLI row the gold is gold_label and the annotators are annotator_labels. "
                "strict majority = a label held by more than half the annotators. A labeled row (gold in "
                "entailment/neutral/contradiction) is checked for gold == strict majority and for having a "
                "majority at all; a '-' row is checked for having no majority. n_gold_mismatch_majority, "
                "n_labeled_without_majority and n_no_consensus_with_majority should all be 0 if the "
                "documented derivation and filter rules hold. MultiNLI validated only its dev and test "
                "sets, so train is expected to be entirely single-annotator with no '-' rows (hist "
                "{1: 392702}), unlike SNLI's train, whose file holds a validated subset. The per-split "
                "no_consensus counts are the first published row-by-row figures for this release; they "
                "are reported, not pre-bet on an exact number. n_multi counts rows with >= 2 annotators "
                "and n_unanimous_multi those whose annotators all agree.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
