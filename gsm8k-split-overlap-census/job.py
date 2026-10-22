# job.py -- run the GSM8K split-overlap census on the real data in /data, write
# results.json to /out, and copy the source files (+ a placeholder README) alongside.
#
# Data: openai/grade-school-math raw grade_school_math/data/{train,test}.jsonl,
# downloaded by the compete lane via data_urls into /data (data_key gsm8k-official).
#
# Authored by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.

import argparse
import glob
import json
import os
import shutil

from split_overlap import analyze, public_summary
from cases import TRAIN, TEST, TARGET

SOURCE_FILES = ["split_overlap.py", "cases.py", "test_split_overlap.py", "job.py"]

PLACEHOLDER_README = (
    "# gsm8k-split-overlap-census\n\n"
    "Placeholder. The published README is authored at ship time; see the "
    "eval-reliability-audits catalogue.\n"
)


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def pick(files, token):
    for p in files:
        if token in os.path.basename(p).lower():
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    files = sorted(glob.glob(os.path.join(args.data_dir, "**", "*.jsonl"), recursive=True))
    train_path = pick(files, "train")
    test_path = pick(files, "test")
    if not train_path or not test_path:
        raise SystemExit("could not find train/test jsonl in %s; saw %r" % (args.data_dir, files))

    train_rows = load_jsonl(train_path)
    test_rows = load_jsonl(test_path)

    result = analyze(train_rows, test_rows)

    # Pre-registered fixture self-check (mirrors the unittest).
    fixture_public = public_summary(analyze(TRAIN, TEST))
    target_met = fixture_public == TARGET

    out = {
        "dataset": "GSM8K (openai/grade-school-math)",
        "train_file": os.path.basename(train_path),
        "test_file": os.path.basename(test_path),
        "train_rows_raw": len(train_rows),
        "test_rows_raw": len(test_rows),
        "normalizer": "whitespace-collapsed then lowercased question text (only near-dup rule)",
        "final_answer_rule": "text after the last '####', stripped, commas and leading '$' removed",
        "result": result,
        "synthetic_corpus": {
            "target_met": target_met,
            "public": fixture_public,
            "target": TARGET,
        },
        "generated_by": "AI agents working in MV2's name (Munim, Inc.)",
    }

    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    here = os.path.dirname(os.path.abspath(__file__))
    for name in SOURCE_FILES:
        src = os.path.join(here, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(args.out_dir, name))
    with open(os.path.join(args.out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(PLACEHOLDER_README)

    print("train_rows_raw=%d test_rows_raw=%d" % (len(train_rows), len(test_rows)))
    print("exact_overlap_pairs=%d (conflicts=%d)" % (
        result["exact_overlap_pairs"], result["exact_overlap_answer_conflicts"]))
    print("norm_overlap_pairs=%d (conflicts=%d)" % (
        result["norm_overlap_pairs"], result["norm_overlap_answer_conflicts"]))
    print("target_met=%s" % target_met)


if __name__ == "__main__":
    main()
