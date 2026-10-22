# job.py -- run the GSM8K main-vs-socratic final-answer census on the official data.
#
# Reads the four official JSONL files (main + socratic, train + test), matches rows by
# exact question text, and censuses final-answer agreement. Prints real-data diagnostics
# and RAISES if no valid rows are read (guards against a silent read-of-nothing).
#
# Authored by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.

import argparse
import json
import os
import shutil
import sys
import urllib.request

import cases
from gsm8k_socratic_consistency import census, public_summary

RAW_BASE = ("https://raw.githubusercontent.com/openai/grade-school-math/"
            "master/grade_school_math/data/")

FILES = {
    "train": "train.jsonl",
    "test": "test.jsonl",
    "train_socratic": "train_socratic.jsonl",
    "test_socratic": "test_socratic.jsonl",
}

# Source files copied verbatim into /out so the shipped audit is self-contained.
SOURCE_FILES = [
    "gsm8k_socratic_consistency.py",
    "cases.py",
    "test_gsm8k_socratic_consistency.py",
    "job.py",
    "README.md",
]


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def ensure_file(data_dir, basename):
    """Return a local path to basename, fetching it into data_dir if not cached."""
    local = os.path.join(data_dir, basename)
    if os.path.exists(local):
        return local
    url = RAW_BASE + basename
    print(f"fetching {url}", flush=True)
    urllib.request.urlretrieve(url, local)
    return local


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()

    os.makedirs(args.data_dir, exist_ok=True)
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Pre-registered fixture must hold before touching real data.
    fixture = census(cases.MAIN_ROWS, cases.SOCRATIC_ROWS,
                     cases.QUESTION_KEY, cases.ANSWER_KEY)
    target_met = public_summary(fixture) == cases.TARGET
    print(f"synthetic target_met={target_met}", flush=True)

    # 2) Load the four official files.
    loaded = {}
    for key, basename in FILES.items():
        path = ensure_file(args.data_dir, basename)
        loaded[key] = load_jsonl(path)
        print(f"{key}: rows={len(loaded[key])} "
              f"first_row_keys={sorted(loaded[key][0].keys()) if loaded[key] else []}",
              flush=True)

    # 3) Census per split and combined.
    per_split = {
        "train": census(loaded["train"], loaded["train_socratic"]),
        "test": census(loaded["test"], loaded["test_socratic"]),
    }
    combined = census(loaded["train"] + loaded["test"],
                      loaded["train_socratic"] + loaded["test_socratic"])

    for name, res in list(per_split.items()) + [("combined", combined)]:
        print(f"{name}: main_rows={res['main_rows_valid']} "
              f"socratic_rows={res['socratic_rows_valid']} "
              f"in_both={res['questions_in_both']} "
              f"only_main={res['questions_only_in_main']} "
              f"only_socratic={res['questions_only_in_socratic']} "
              f"agree={res['final_answer_agree']} "
              f"disagree={res['final_answer_disagree']}", flush=True)

    # 4) Guard against a silent read-of-nothing.
    if combined["main_rows_valid"] == 0 or combined["socratic_rows_valid"] == 0:
        raise SystemExit("ABORT: real-data rows_valid is 0 -- data not read correctly")

    results = {
        "dataset": "GSM8K (openai/grade-school-math, Cobbe et al. 2021)",
        "files": {k: v for k, v in FILES.items()},
        "final_answer_rule": "text after the last '####', stripped, commas and a "
                             "leading '$' removed",
        "match_rule": "rows paired by EXACT question text; agreement is identical "
                      "normalized final answer",
        "per_split": per_split,
        "combined_train_and_test": combined,
        "synthetic_corpus": {
            "target_met": target_met,
            "public": public_summary(fixture),
            "target": cases.TARGET,
        },
        "generated_by": "AI agents working in MV2's name (Munim, Inc.)",
    }

    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)

    here = os.path.dirname(os.path.abspath(__file__))
    for name in SOURCE_FILES:
        src = os.path.join(here, name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(args.out_dir, name))

    if not target_met:
        print("FAIL: synthetic target not met", file=sys.stderr, flush=True)
        raise SystemExit(1)
    print("OK", flush=True)


if __name__ == "__main__":
    main()
