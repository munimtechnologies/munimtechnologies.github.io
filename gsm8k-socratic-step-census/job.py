# job.py -- run the GSM8K main-vs-socratic step and annotation census on the official data.
#
# Reads the four official JSONL files (main + socratic, train + test), pairs rows by exact
# question text, and censuses whether the socratic steps (sub-question prefix removed) and
# calculator annotations match the main ones. Prints real-data diagnostics and RAISES if
# no valid rows are read (guards against a silent read-of-nothing).
#
# Authored by AI agents working in MV2's name (Munim, Inc.). Apache-2.0.

import argparse
import json
import os
import shutil
import sys
import urllib.request

import cases
from gsm8k_socratic_steps import census, public_summary

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
    "gsm8k_socratic_steps.py",
    "calc_eval.py",
    "cases.py",
    "test_gsm8k_socratic_steps.py",
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


def predictions_check(combined):
    pairs = combined["pairs"]
    lines = combined["socratic_lines_in_pairs"]
    ann_share = combined["annotations_identical"] / pairs if pairs else 0.0
    sep_share = combined["socratic_lines_with_separator"] / lines if lines else 0.0
    p = cases.PREDICTIONS
    return {
        "P1_pairs": {"predicted": p["P1_pairs"], "observed": pairs,
                     "held": pairs == p["P1_pairs"]},
        "P2_annotation_identical_share": {
            "predicted_min": p["P2_min_annotation_identical_share"],
            "observed": round(ann_share, 6),
            "held": ann_share >= p["P2_min_annotation_identical_share"]},
        "P3_socratic_mismatch": {
            "predicted": p["P3_socratic_mismatch"],
            "observed": combined["socratic_annotation_classes"]["mismatch"],
            "held": combined["socratic_annotation_classes"]["mismatch"]
            == p["P3_socratic_mismatch"]},
        "P4_separator_share": {
            "predicted_min": p["P4_min_separator_share"],
            "observed": round(sep_share, 6),
            "held": sep_share >= p["P4_min_separator_share"]},
    }


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
        print(f"{name}: pairs={res['pairs']} only_main={res['only_in_main']} "
              f"only_socratic={res['only_in_socratic']} "
              f"soc_lines={res['socratic_lines_in_pairs']} "
              f"with_sep={res['socratic_lines_with_separator']} "
              f"step_count_equal={res['step_count_equal']} "
              f"steps_identical={res['steps_identical']} "
              f"ann_identical={res['annotations_identical']} "
              f"ann_differ={res['annotations_differ']} "
              f"main_ann={res['main_annotation_classes']} "
              f"soc_ann={res['socratic_annotation_classes']}", flush=True)

    # 4) Guard against a silent read-of-nothing.
    if combined["pairs"] == 0 or combined["main_annotations_total"] == 0:
        raise SystemExit("ABORT: real-data pairs or annotations are 0 -- data not read correctly")

    audit19_ok = combined["main_annotation_classes"] == cases.AUDIT19_MAIN_CLASSES
    print(f"audit19 cross-check ok={audit19_ok}", flush=True)
    preds = predictions_check(combined)
    print(f"predictions={json.dumps({k: v['held'] for k, v in preds.items()})}", flush=True)

    results = {
        "dataset": "GSM8K (openai/grade-school-math, Cobbe et al. 2021)",
        "files": {k: v for k, v in FILES.items()},
        "match_rule": "rows paired by EXACT question text",
        "step_rule": "lines before the last '####', stripped; each socratic line loses the "
                     "text up to and including its first ' ** '; steps identical iff the "
                     "two line lists are equal",
        "annotation_rule": "every <<expr=result>> in the whole answer, in order "
                           "(calc_eval.find_annotations); identical iff sequences equal",
        "per_split": per_split,
        "combined_train_and_test": combined,
        "audit19_crosscheck": {"expected_main_classes": cases.AUDIT19_MAIN_CLASSES,
                               "ok": audit19_ok},
        "predictions": preds,
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
