"""Run the SNLI annotator-agreement / gold-derivation census on the official release.

The runner downloads snli_1.0.zip (job.json data_urls) to the data dir. This script asserts the
hand-traced fixture BEFORE touching real data, reads the three raw jsonl splits straight from the zip
(the unfiltered 10,000-row dev/test, not a de-"-"-ed copy), verifies for every split that gold_label is
the strict majority of annotator_labels and that every "-" row lacks a majority, reproduces the residual
no-consensus counts, records pre-registered predictions, and writes results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from snli_agreement import agreement_stats, flatten, parse_row

SPLITS = ("train", "dev", "test")


def _find_member(zf, split):
    """Return the zip member name for snli_1.0_<split>.jsonl, tolerating the top-level folder."""
    want = "snli_1.0_%s.jsonl" % split
    for name in zf.namelist():
        if name.endswith(want) and not name.endswith("/"):
            return name
    return None


def read_split(zip_path, split):
    """Stream one SNLI jsonl split from the zip into parsed {gold, annotators} records."""
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

    # 2. Locate the SNLI zip.
    zips = sorted(glob.glob(os.path.join(args.data_dir, "*.zip")))
    print("[diag] zip files in data dir:", zips)
    if not zips:
        print("FATAL: no snli zip found in data dir", file=sys.stderr)
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
        print("[census] %-5s n_total=%d (expect %d, ok=%s) labeled=%d no_consensus=%d "
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
    predictions = {
        "P1_gold_is_strict_majority_everywhere": (total_mismatch == 0) and (total_labeled_no_majority == 0),
        "P2_no_consensus_rows_have_no_majority": total_consensus_anomaly == 0,
        "P3_no_consensus_counts_match_published": no_consensus_counts == cases.EXPECTED_NO_CONSENSUS,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))
    print("[diag] no_consensus_counts =", no_consensus_counts,
          "expected =", cases.EXPECTED_NO_CONSENSUS)

    out = {
        "dataset": "SNLI 1.0 (Bowman, Angeli, Potts and Manning, 2015), CC BY-SA 4.0 -- the raw "
                   "train/dev/test jsonl splits read straight from snli_1.0.zip, each row carrying an "
                   "annotator_labels list and a single gold_label",
        "raw_split_total_expected": cases.RAW_SPLIT_TOTAL,
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "per_split": per_split,
        "totals": {
            "n_gold_mismatch_majority": total_mismatch,
            "n_labeled_without_majority": total_labeled_no_majority,
            "n_no_consensus_with_majority": total_consensus_anomaly,
            "no_consensus_counts": no_consensus_counts,
            "no_consensus_expected": cases.EXPECTED_NO_CONSENSUS,
        },
        "predictions": predictions,
        "note": "For each SNLI row the gold is gold_label and the annotators are annotator_labels (one "
                "author label in train; five in the validated dev/test). strict majority = a label held by "
                "more than half the annotators. A labeled row (gold in entailment/neutral/contradiction) "
                "is checked for gold == strict majority and for having a majority at all; a '-' row is "
                "checked for having no majority. n_gold_mismatch_majority, n_labeled_without_majority and "
                "n_no_consensus_with_majority should all be 0 if the documented derivation and filter "
                "rules hold. no_consensus counts are reproduced against the published post-filter sizes "
                "(549,367 / 9,842 / 9,824 => 785 / 158 / 176). n_multi counts rows with >= 2 annotators "
                "and n_unanimous_multi those whose annotators all agree.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
