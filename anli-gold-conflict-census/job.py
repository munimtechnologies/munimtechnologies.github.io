# job.py -- run the ANLI gold-conflict census on the real data in /data, write
# results.json to /out, and copy the source files (+ a placeholder README) alongside.
#
# Data: ANLI v1.0 (facebookresearch/anli), https://dl.fbaipublicfiles.com/anli/anli_v1.0.zip
# downloaded by the compete lane via data_urls into /data (data_key anli-official).
# Structure after extraction: anli_v1.0/R{1,2,3}/{train,dev,test}.jsonl.
#
# IMPORTANT (v2 fix): the RAW ANLI v1.0 jsonl names the premise field "context", NOT
# "premise" (the HuggingFace loader renames context -> premise). v1 of this job read
# with premise_key="premise" and so judged every real row invalid (rows_valid=0 on all
# 9 files). This version detects the real premise key per data (prefer "context", fall
# back to "premise") and prints diagnostics so a silent zero cannot recur unnoticed.
#
# Authored by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.

import argparse
import glob
import json
import os
import shutil
import zipfile

from nli_consistency import analyze, public_summary
from cases import ROWS, PREMISE_KEY, HYPOTHESIS_KEY, LABEL_KEY, TARGET

SOURCE_FILES = ["nli_consistency.py", "cases.py", "test_nli_consistency.py", "job.py"]

PLACEHOLDER_README = (
    "# anli-gold-conflict-census\n\n"
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


def ensure_extracted(data_dir):
    """If no jsonl files are present, extract any zip found in data_dir."""
    if glob.glob(os.path.join(data_dir, "**", "*.jsonl"), recursive=True):
        return
    for zpath in glob.glob(os.path.join(data_dir, "**", "*.zip"), recursive=True):
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(data_dir)


def detect_premise_key(rows):
    """Return the premise field name actually present in the data.

    Raw ANLI v1.0 uses "context"; some processed mirrors rename it to "premise".
    Prefer "context" (the raw release), fall back to "premise", default "context".
    """
    for row in rows:
        if isinstance(row, dict):
            if "context" in row:
                return "context"
            if "premise" in row:
                return "premise"
    return "context"


def classify(path):
    import re
    low = path.replace("\\", "/").lower()
    m = re.search(r"/(r[123])/", low)
    rnd = m.group(1).upper() if m else "R?"
    split = os.path.splitext(os.path.basename(path))[0].lower()
    return "%s/%s" % (rnd, split)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    ensure_extracted(args.data_dir)
    files = sorted(glob.glob(os.path.join(args.data_dir, "**", "*.jsonl"), recursive=True))
    if not files:
        raise SystemExit("no jsonl files found under %s" % args.data_dir)

    # Load everything first so we can detect the real premise key from the data.
    loaded = {classify(path): load_jsonl(path) for path in files}
    all_rows = []
    for rows in loaded.values():
        all_rows.extend(rows)

    real_premise_key = detect_premise_key(all_rows)
    sample_keys = sorted(all_rows[0].keys()) if all_rows else []

    per_file = {}
    for name, rows in loaded.items():
        per_file[name] = analyze(rows, real_premise_key, HYPOTHESIS_KEY, LABEL_KEY)

    combined = analyze(all_rows, real_premise_key, HYPOTHESIS_KEY, LABEL_KEY)

    # Guard: the real data must parse to non-zero valid rows, else the schema moved.
    if combined["rows_valid"] == 0:
        raise SystemExit(
            "0 valid rows across all files; premise_key=%r, first-row keys=%r"
            % (real_premise_key, sample_keys)
        )

    fixture_public = public_summary(analyze(ROWS, PREMISE_KEY, HYPOTHESIS_KEY, LABEL_KEY))
    target_met = fixture_public == TARGET

    out = {
        "dataset": "ANLI v1.0 (facebookresearch/anli, Nie et al. 2020)",
        "files": sorted(per_file.keys()),
        "premise_key_in_data": real_premise_key,
        "normalizer": "whitespace-collapsed then lowercased premise and hypothesis (only near-dup rule)",
        "conflict_rule": "a distinct (premise, hypothesis) pair carrying >1 gold label among {e,n,c}",
        "per_file": per_file,
        "combined_all_rounds_and_splits": combined,
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

    print("files=%s" % sorted(per_file.keys()))
    print("premise_key_in_data=%s first_row_keys=%s" % (real_premise_key, sample_keys))
    print("combined rows_valid=%d distinct_exact=%d distinct_norm=%d" % (
        combined["rows_valid"], combined["distinct_exact_pairs"], combined["distinct_norm_pairs"]))
    print("combined exact_conflict_pairs=%d norm_conflict_pairs=%d" % (
        combined["exact_conflict_pairs"], combined["norm_conflict_pairs"]))
    print("target_met=%s" % target_met)


if __name__ == "__main__":
    main()
