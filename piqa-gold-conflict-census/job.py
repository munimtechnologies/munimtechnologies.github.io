"""Run the PIQA gold-conflict census on the official train and validation splits.

Downloads PIQA's four files (train.jsonl, train-labels.lst, valid.jsonl, valid-labels.lst)
from the author's own GitHub Pages repo, zips each jsonl with its line-aligned label file
(FATAL if the two lengths differ), asserts the hand-traced fixture BEFORE touching real
data, prints real-data diagnostics, guards against empty reads, checks observed row counts
against the published totals, records pre-registered predictions, and writes results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import json
import os
import sys
import urllib.request

import cases
from piqa_gold_conflict import census, public_summary

# PIQA's canonical distribution is an AI2 zip (physicaliqa-train-dev.zip) plus the author's
# site. We read the author's own GitHub Pages repo, where the four files sit uncompressed:
# identical schema (goal/sol1/sol2 + a 0/1 label per line) and the canonical first valid
# example ("How do I ready a guinea pig cage for it's new occupants?", label 0). The
# row-count check below (16113 train / 1838 valid) and the per-split jsonl/lst length match
# guard against tampering or misalignment.
BASE = "https://raw.githubusercontent.com/ybisk/ybisk.github.io/master/piqa/data"
SOURCE_FILES = {
    "train": {"jsonl": BASE + "/train.jsonl", "labels": BASE + "/train-labels.lst"},
    "valid": {"jsonl": BASE + "/valid.jsonl", "labels": BASE + "/valid-labels.lst"},
}
EXPECTED_ROWS = {"train": 16113, "valid": 1838}


def fetch(url, dest):
    req = urllib.request.Request(
        url, headers={"User-Agent": "mv2-eval-reliability-audits/1.0 (+Munim, Inc.)"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = resp.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def cached_fetch(url, dest):
    if not os.path.exists(dest) or os.path.getsize(dest) == 0:
        nbytes = fetch(url, dest)
        print("[fetch] %s -> %s (%d bytes)" % (url, dest, nbytes))
    else:
        print("[cache] reusing %s (%d bytes)" % (dest, os.path.getsize(dest)))


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_labels(path):
    labels = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line != "":
                labels.append(line)
    return labels


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
        print("  %-26s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Fetch + zip each split's inputs with its line-aligned labels.
    splits = {}
    observed_rows = {}
    for name, urls in SOURCE_FILES.items():
        jpath = os.path.join(args.data_dir, "piqa_%s.jsonl" % name)
        lpath = os.path.join(args.data_dir, "piqa_%s_labels.lst" % name)
        cached_fetch(urls["jsonl"], jpath)
        cached_fetch(urls["labels"], lpath)
        inputs = load_jsonl(jpath)
        labels = load_labels(lpath)
        print("[diag] %s: inputs=%d labels=%d" % (name, len(inputs), len(labels)))
        if len(inputs) == 0 or len(labels) == 0:
            print("FATAL: %s read 0 rows" % name, file=sys.stderr)
            sys.exit(3)
        if len(inputs) != len(labels):
            print("FATAL: %s inputs/labels length mismatch (%d != %d)"
                  % (name, len(inputs), len(labels)), file=sys.stderr)
            sys.exit(4)
        rows = []
        for inp, lab in zip(inputs, labels):
            row = dict(inp)
            row["label"] = lab
            rows.append(row)
        splits[name] = rows
        observed_rows[name] = len(rows)
        print("[diag] %s first-row keys: %s" % (name, sorted(rows[0].keys())))

    rows_as_expected = all(observed_rows[k] == EXPECTED_ROWS[k] for k in EXPECTED_ROWS)
    print("[diag] observed_rows=%r expected=%r as_expected=%s"
          % (observed_rows, EXPECTED_ROWS, rows_as_expected))

    # 3. Census per split and combined.
    per_split = {name: census(rows) for name, rows in splits.items()}
    combined = census(splits["train"] + splits["valid"])
    for name in ("train", "valid"):
        print("[census:%s] %s" % (name, public_summary(per_split[name])))
    print("[census:combined] %s" % public_summary(combined))

    # 4. Pre-registered predictions (held/failed reported honestly).
    predictions = {
        "P1_combined_triple_conflicts_le_20": combined["triple_conflict_groups"] <= 20,
        "P2_valid_triple_conflicts_eq_0": per_split["valid"]["triple_conflict_groups"] == 0,
        "P3_combined_goal_duplicate_groups_ge_1": combined["goal_duplicate_groups"] >= 1,
        "P4_combined_triple_duplicate_groups_ge_1": combined["triple_duplicate_groups"] >= 1,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    results = {
        "dataset": "PIQA (Bisk et al., AAAI 2020), Academic Free License v3.0",
        "source_files": {name: urls for name, urls in SOURCE_FILES.items()},
        "expected_rows": EXPECTED_ROWS,
        "observed_rows": observed_rows,
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "per_split": per_split,
        "combined": combined,
        "predictions": predictions,
        "note": "Only (goal, sol1, sol2) triple conflicts are defects; goal reuse across "
                "different solution pairs is legitimate because PIQA reuses goals by design. "
                "The unlabelled test split (tests.jsonl) is excluded.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
