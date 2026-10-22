"""Run the CommonsenseQA gold-conflict census on the official train and dev splits.

Downloads CommonsenseQA's two labelled random-split files from the authors' canonical S3
bucket, asserts the hand-traced fixture BEFORE touching real data, prints real-data
diagnostics, guards against empty reads, checks observed row counts against the published
totals (9,741 train / 1,221 dev), records pre-registered predictions, and writes
results.json.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import json
import os
import sys
import urllib.request

import cases
from commonsenseqa_gold_conflict import census, public_summary

# CommonsenseQA's canonical public release (Talmor et al., NAACL 2019) is served from the
# authors' S3 bucket as one JSONL per split with the answerKey inline. The test split
# (test_rand_split_no_answers.jsonl) ships without gold answers and is excluded. The
# row-count check below (9,741 train / 1,221 dev) and the schema/first-row diagnostics guard
# against a wrong mirror or tampering.
BASE = "https://s3.amazonaws.com/commensenseqa"
SOURCE_FILES = {
    "train": BASE + "/train_rand_split.jsonl",
    "dev": BASE + "/dev_rand_split.jsonl",
}
EXPECTED_ROWS = {"train": 9741, "dev": 1221}


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

    # 2. Fetch each split.
    splits = {}
    observed_rows = {}
    for name, url in SOURCE_FILES.items():
        path = os.path.join(args.data_dir, "commonsenseqa_%s.jsonl" % name)
        cached_fetch(url, path)
        rows = load_jsonl(path)
        print("[diag] %s: rows=%d" % (name, len(rows)))
        if len(rows) == 0:
            print("FATAL: %s read 0 rows" % name, file=sys.stderr)
            sys.exit(3)
        splits[name] = rows
        observed_rows[name] = len(rows)
        q0 = rows[0].get("question", {})
        print("[diag] %s first-row keys: %s" % (name, sorted(rows[0].keys())))
        print("[diag] %s first stem: %r answerKey=%r n_choices=%d"
              % (name, q0.get("stem"), rows[0].get("answerKey"),
                 len(q0.get("choices", []))))

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
        "P1_combined_item_conflicts_le_20": combined["item_conflict_groups"] <= 20,
        "P2_dev_item_conflicts_eq_0": per_split["dev"]["item_conflict_groups"] == 0,
        "P3_combined_item_duplicate_groups_ge_1": combined["item_duplicate_groups"] >= 1,
        "P4_combined_stem_duplicate_groups_ge_1": combined["stem_duplicate_groups"] >= 1,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    results = {
        "dataset": "CommonsenseQA (Talmor et al., NAACL 2019), MIT License",
        "source_files": SOURCE_FILES,
        "expected_rows": EXPECTED_ROWS,
        "observed_rows": observed_rows,
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "per_split": per_split,
        "combined": combined,
        "predictions": predictions,
        "note": "The item key is (stem, sorted option-text set); the gold compared is the "
                "answer TEXT, so option reshuffles are not conflicts. Same stem with a "
                "different option set is legitimate reuse (context). The unlabelled test "
                "split (test_rand_split_no_answers.jsonl) is excluded.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
