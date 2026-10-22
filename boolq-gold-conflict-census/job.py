"""Run the BoolQ gold-conflict census on the official train and dev splits.

Downloads BoolQ train.jsonl and dev.jsonl (if not already cached in --data-dir), asserts
the hand-traced fixture BEFORE touching real data, prints real-data diagnostics, guards
against empty reads, records pre-registered predictions, and writes results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import json
import os
import sys
import urllib.request

import cases
from boolq_gold_conflict import census, public_summary

# BoolQ's canonical files live on Google Cloud Storage (gs://boolq), but anonymous HTTPS
# to storage.googleapis.com/boolq/*.jsonl now returns 403 Forbidden. We use a verified,
# unmodified GitHub mirror: identical schema (question/title/answer/passage) and identical
# first dev example ("does ethanol take more energy make that produces", answer false).
# The row-count check below (9427 train / 3270 dev) guards against any tampering.
SOURCE_FILES = {
    "train": "https://raw.githubusercontent.com/svinkapeppa/boolq/master/train.jsonl",
    "dev": "https://raw.githubusercontent.com/svinkapeppa/boolq/master/dev.jsonl",
}
EXPECTED_ROWS = {"train": 9427, "dev": 3270}


def fetch(url, dest):
    req = urllib.request.Request(
        url, headers={"User-Agent": "mv2-eval-reliability-audits/1.0 (+Munim, Inc.)"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = resp.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.data_dir, exist_ok=True)
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix = census(cases.FIXTURE)
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    for k in cases.TARGET:
        print("  %-24s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Fetch + load splits, with diagnostics and an empty-read guard.
    splits = {}
    observed_rows = {}
    for name, url in SOURCE_FILES.items():
        dest = os.path.join(args.data_dir, "boolq_%s.jsonl" % name)
        if not os.path.exists(dest) or os.path.getsize(dest) == 0:
            nbytes = fetch(url, dest)
            print("[fetch] %s -> %s (%d bytes)" % (url, dest, nbytes))
        else:
            print("[cache] reusing %s (%d bytes)" % (dest, os.path.getsize(dest)))
        rows = load_jsonl(dest)
        splits[name] = rows
        observed_rows[name] = len(rows)
        print("[diag] %s: rows=%d" % (name, len(rows)))
        if rows:
            print("[diag] %s first-row keys: %s" % (name, sorted(rows[0].keys())))
        if len(rows) == 0:
            print("FATAL: %s read 0 rows" % name, file=sys.stderr)
            sys.exit(3)

    rows_as_expected = all(observed_rows[k] == EXPECTED_ROWS[k] for k in EXPECTED_ROWS)
    print("[diag] observed_rows=%r expected=%r as_expected=%s"
          % (observed_rows, EXPECTED_ROWS, rows_as_expected))

    # 3. Census per split and combined.
    per_split = {name: census(rows) for name, rows in splits.items()}
    combined = census(splits["train"] + splits["dev"])
    for name in ("train", "dev"):
        print("[census:%s] %s" % (name, public_summary(per_split[name])))
    print("[census:combined] %s" % public_summary(combined))

    # 4. Pre-registered predictions (held/failed reported honestly).
    predictions = {
        "P1_combined_qp_conflicts_le_20": combined["qp_conflict_groups"] <= 20,
        "P2_dev_qp_conflicts_eq_0": per_split["dev"]["qp_conflict_groups"] == 0,
        "P3_combined_question_conflicts_ge_5": combined["question_conflict_groups"] >= 5,
        "P4_combined_qp_duplicate_groups_ge_1": combined["qp_duplicate_groups"] >= 1,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    results = {
        "dataset": "BoolQ (Clark et al., NAACL 2019), CC BY-SA 3.0",
        "source_files": SOURCE_FILES,
        "expected_rows": EXPECTED_ROWS,
        "observed_rows": observed_rows,
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "per_split": per_split,
        "combined": combined,
        "predictions": predictions,
        "note": "Only (question, passage) gold conflicts are defects; question-only "
                "conflicts are legitimate because the BoolQ answer depends on the passage. "
                "test.jsonl is unlabelled and excluded.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
