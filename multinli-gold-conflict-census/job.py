# SPDX-License-Identifier: Apache-2.0
# Part of MV2's eval-reliability audits (Munim, Inc.). Made with AI.
"""Run the NLI gold-label conflict census over released MultiNLI splits.

Reads the official MultiNLI 1.0 zip (downloaded to the data dir), and for each
of its jsonl members (train, dev_matched, dev_mismatched) counts
(premise, hypothesis) pairs that carry conflicting gold labels, both exactly and
under normalization. MultiNLI withholds test labels, so there is no test split
to census. Writes results.json and copies its own source into the out dir.
"""

import argparse
import glob
import io
import json
import os
import shutil
import zipfile

from cases import FIXTURE_ROWS, TARGET
from nli_consistency import analyze, normalize

SOURCE_FILES = ["nli_consistency.py", "cases.py", "test_nli_consistency.py", "job.py"]
MAX_EXAMPLES = 50


def _rows_from_member(zf, member):
    """Yield (premise, hypothesis, gold_label) from one jsonl zip member."""
    with zf.open(member) as raw:
        for line in io.TextIOWrapper(raw, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            yield (row.get("sentence1", ""), row.get("sentence2", ""), row.get("gold_label", ""))


def _split_of(member):
    name = member.rsplit("/", 1)[-1].lower()
    # Order matters: 'mismatched' contains 'matched' as a substring.
    if "dev_mismatched" in name or "mismatched" in name:
        return "dev_mismatched"
    if "dev_matched" in name or "matched" in name:
        return "dev_matched"
    if "train" in name:
        return "train"
    return name.replace(".jsonl", "")


def _examples_exact(conflicts):
    out = []
    for (p, h), labels in list(conflicts.items())[:MAX_EXAMPLES]:
        out.append({"premise": p[:200], "hypothesis": h[:200], "gold_labels": labels})
    return out


def _examples_norm(conflicts):
    out = []
    for (p, h), labels in list(conflicts.items())[:MAX_EXAMPLES]:
        out.append({"premise_norm": p[:200], "hypothesis_norm": h[:200], "gold_labels": labels})
    return out


def _synthetic_corpus():
    got = analyze(FIXTURE_ROWS)
    public = {k: v for k, v in got.items() if not k.startswith("_")}
    return {"target": TARGET, "counts": public,
            "target_met": all(public[k] == TARGET[k] for k in TARGET)}


def census(data_dir):
    zips = sorted(glob.glob(os.path.join(data_dir, "*.zip")))
    if not zips:
        raise SystemExit("no MultiNLI zip found in data dir: " + data_dir)
    by_split = {}
    with zipfile.ZipFile(zips[0]) as zf:
        members = [m for m in zf.namelist()
                   if m.endswith(".jsonl") and not m.startswith("__MACOSX")]
        for member in sorted(members):
            split = _split_of(member)
            stats = analyze(_rows_from_member(zf, member))
            by_split[split] = {
                "member": member,
                "rows_valid": stats["rows_valid"],
                "distinct_exact_pairs": stats["distinct_exact_pairs"],
                "exact_conflict_pairs": stats["exact_conflict_pairs"],
                "duplicate_exact_pairs": stats["duplicate_exact_pairs"],
                "distinct_norm_pairs": stats["distinct_norm_pairs"],
                "norm_conflict_pairs": stats["norm_conflict_pairs"],
                "exact_conflict_examples": _examples_exact(stats["_exact_conflicts"]),
                "norm_conflict_examples": _examples_norm(stats["_norm_conflicts"]),
            }
    return {"zip": os.path.basename(zips[0]), "by_split": by_split}


def copy_sources(out_dir):
    here = os.path.dirname(os.path.abspath(__file__))
    for name in SOURCE_FILES:
        src = os.path.join(here, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(out_dir, name))
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("# multinli-gold-conflict-census (placeholder)\n\n"
                 "The published README is authored at ship time from results.json.\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    result = {
        "name": "multinli-gold-conflict-census",
        "dataset": "MultiNLI 1.0 (Williams et al. 2018), official zip, train/dev_matched/dev_mismatched",
        "method": {
            "question": "does one (premise, hypothesis) pair carry two gold labels?",
            "exact": "exact string pair",
            "normalized": "lowercased, whitespace-collapsed, trailing period dropped",
            "excluded": "rows with gold_label '-' (no annotator majority)",
            "note": "MultiNLI reuses a premise across labels by design; that is NOT counted. "
                    "Only a repeated (premise, hypothesis) PAIR with differing labels counts. "
                    "Test labels are withheld upstream, so there is no test split.",
        },
        "synthetic_corpus": _synthetic_corpus(),
        "census": census(args.data_dir),
    }

    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)

    copy_sources(args.out_dir)
    for split, s in result["census"]["by_split"].items():
        print(split, "exact_conflicts:", s["exact_conflict_pairs"],
              "norm_conflicts:", s["norm_conflict_pairs"], "rows_valid:", s["rows_valid"])


if __name__ == "__main__":
    main()
