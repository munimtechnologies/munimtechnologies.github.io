"""Run the SNLI x MultiNLI cross-overlap census on the official corpora.

The two zips (SNLI 1.0 and MultiNLI 1.0) are downloaded to the data dir by the runner
(job.json data_urls). This script asserts the hand-traced fixture BEFORE touching real data,
streams each corpus straight from its zip, checks observed labelled row counts per split
against the published totals, runs the cross-corpus overlap census, records pre-registered
predictions, and writes results.json.

v2: the SNLI zip is served from the NYU Faculty Digital Archive mirror
(archive.nyu.edu/bitstream/2451/41728/2/snli_1.0.zip) because nlp.stanford.edu was
unreachable ("No route to host") from the sandbox in the v1 run. iter_rows now de-duplicates
by member basename, so if more than one copy of a corpus zip ends up in the data dir the
counts are read exactly once and never doubled.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from cross_nli_overlap import cross_census, build_index, _bit, public_summary

# Published labelled (gold != '-') row counts for the canonical releases. SNLI has a labelled
# test split; MultiNLI's public labelled eval splits are dev_matched and dev_mismatched.
EXPECTED = {
    "snli": {"train": 549367, "dev": 9842, "test": 9824},
    "multinli": {"train": 392702, "dev_matched": 9815, "dev_mismatched": 9832},
}


def dataset_of(member):
    """Return 'multinli', 'snli', or None for a zip member path."""
    name = member.lower()
    if not name.endswith(".jsonl") or name.startswith("__macosx"):
        return None
    if "multinli" in name:
        return "multinli"
    if "snli" in name:
        return "snli"
    return None


def split_of(dataset, member):
    """Return the split name for a member, or None if unrecognized."""
    name = os.path.basename(member).lower()
    if dataset == "snli":
        for s in ("train", "dev", "test"):
            if s in name:
                return s
    else:
        if "mismatched" in name:
            return "dev_mismatched"
        if "matched" in name:
            return "dev_matched"
        if "train" in name:
            return "train"
    return None


def iter_rows(zip_paths, dataset):
    """Yield (premise, hypothesis, gold, split) for every row of one dataset, streaming.

    If the same logical file appears in more than one zip in the data dir (e.g. two mirrors of
    SNLI both downloaded), each member basename is read only once so the counts are never
    doubled. This is a safety net; normally exactly one zip per corpus is present.
    """
    seen = set()
    for zp in zip_paths:
        with zipfile.ZipFile(zp) as z:
            for m in z.namelist():
                if dataset_of(m) != dataset:
                    continue
                base = os.path.basename(m).lower()
                if base in seen:
                    continue
                seen.add(base)
                split = split_of(dataset, m)
                with z.open(m) as f:
                    for raw in f:
                        raw = raw.strip()
                        if not raw:
                            continue
                        row = json.loads(raw)
                        yield (row.get("sentence1", ""), row.get("sentence2", ""),
                               row.get("gold_label", ""), split)


def count_splits(zip_paths, dataset):
    """Count raw and labelled rows per split for one dataset (streaming, no retention)."""
    raw = {}
    valid = {}
    first = None
    for p, h, g, split in iter_rows(zip_paths, dataset):
        if first is None:
            first = (p, h, g, split)
        raw[split] = raw.get(split, 0) + 1
        if _bit(g) != 0:
            valid[split] = valid.get(split, 0) + 1
    return raw, valid, first


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix = cases.flatten(cross_census(cases.FIXTURE_SNLI, cases.FIXTURE_MULTINLI))
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET)
    print("[fixture] target_met =", target_met)
    for k in cases.TARGET:
        print("  %-34s observed=%r target=%r" % (k, fix[k], cases.TARGET[k]))
    if not target_met:
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Locate the zips.
    zip_paths = sorted(glob.glob(os.path.join(args.data_dir, "*.zip")))
    print("[diag] zips in data dir:", zip_paths)
    if not zip_paths:
        print("FATAL: no zip found in data dir", file=sys.stderr)
        sys.exit(3)

    # 3. Count rows per split and check against published totals.
    observed_valid = {}
    observed_raw = {}
    for ds in ("snli", "multinli"):
        raw, valid, first = count_splits(zip_paths, ds)
        observed_raw[ds] = raw
        observed_valid[ds] = valid
        total_valid = sum(valid.values())
        print("[diag] %s raw-per-split=%r" % (ds, raw))
        print("[diag] %s labelled-per-split=%r total_labelled=%d" % (ds, valid, total_valid))
        print("[diag] %s first row: premise=%r hypothesis=%r gold=%r split=%r"
              % (ds, (first or ("", "", "", ""))[0][:80],
                 (first or ("", "", "", ""))[1][:80],
                 (first or ("", "", "", ""))[2], (first or ("", "", "", ""))[3]))
        if total_valid == 0:
            print("FATAL: %s read 0 labelled rows" % ds, file=sys.stderr)
            sys.exit(4)

    rows_as_expected = all(
        observed_valid.get(ds, {}).get(split) == n
        for ds, splits in EXPECTED.items()
        for split, n in splits.items()
    )
    print("[diag] rows_as_expected =", rows_as_expected)

    # 4. Cross-corpus overlap census (streamed fresh from the zips).
    result = cross_census(
        ((p, h, g) for p, h, g, _ in iter_rows(zip_paths, "snli")),
        ((p, h, g) for p, h, g, _ in iter_rows(zip_paths, "multinli")),
    )
    print("[census]", public_summary(result))

    # 5. Pre-registered predictions (held/failed reported honestly).
    predictions = {
        "P1_exact_overlap_pairs_le_50": result["exact_overlap_pairs"] <= 50,
        "P2_exact_overlap_conflicting_eq_0": result["exact_overlap_conflicting_label"] == 0,
        "P3_norm_additional_le_100": result["norm_additional_over_exact"] <= 100,
        "P4_exact_overlap_pairs_ge_1": result["exact_overlap_pairs"] >= 1,
    }
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    out = {
        "datasets": {
            "snli": "SNLI 1.0 (Bowman et al., EMNLP 2015), CC BY-SA 4.0",
            "multinli": "MultiNLI 1.0 (Williams et al., NAACL 2018), multiple (see corpus)",
        },
        "expected_labelled_rows": EXPECTED,
        "observed_raw_rows": observed_raw,
        "observed_labelled_rows": observed_valid,
        "rows_as_expected": rows_as_expected,
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "result": result,
        "predictions": predictions,
        "note": "The pair key is (premise=sentence1, hypothesis=sentence2); the gold is the "
                "3-way NLI label. Rows with gold_label '-' are excluded. A shared pair is "
                "'conflicting' when the union of the two corpora's labels for it has more "
                "than one distinct label. SNLI train/dev/test and MultiNLI train/dev_matched/"
                "dev_mismatched are included; MultiNLI has no public labelled test split.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
