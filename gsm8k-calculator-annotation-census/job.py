# SPDX-License-Identifier: Apache-2.0
# Part of MV2's eval-reliability audits (Munim, Inc.). Made with AI.
"""Census GSM8K's own <<expr=result>> calculator annotations.

For every released GSM8K row (train + test) this:
  1. classifies each inline <<expr=result>> annotation as match / rounded /
     mismatch / unparseable (annotation arithmetic self-consistency), and
  2. checks whether the solution's final '#### answer' equals its LAST
     annotation's stated result (final-answer consistency).

It writes results.json (totals, per-split, and real examples) and copies its
own source into the out dir so the published audit is self-contained.
"""

import argparse
import glob
import json
import os
import shutil
from collections import Counter
from fractions import Fraction

from calc_eval import (
    classify_annotation,
    find_annotations,
    parse_number,
    safe_eval,
    solution_consistency,
)
from cases import ANNOTATION_CASES, SOLUTION_CASES, TARGET

SOURCE_FILES = ["calc_eval.py", "cases.py", "test_calc_eval.py", "job.py"]
MAX_EXAMPLES = 50


def _split_of(path):
    name = os.path.basename(path).lower()
    if "train" in name:
        return "train"
    if "test" in name:
        return "test"
    return name.replace(".jsonl", "")


def _fraction_str(expr):
    try:
        v = safe_eval(expr)
    except Exception:
        return None
    return str(v)


def _float_str(expr):
    try:
        v = safe_eval(expr)
    except Exception:
        return None
    return repr(float(v))


def _synthetic_corpus():
    """Re-run the pre-registered fixtures so the output records them."""
    counts = Counter(classify_annotation(e, r) for e, r, _ in ANNOTATION_CASES)
    per_case = [
        {"expr": e, "result": r, "expected": lbl, "got": classify_annotation(e, r)}
        for e, r, lbl in ANNOTATION_CASES
    ]
    sols = [
        {
            "answer": a,
            "expected_has_annotation": h,
            "expected_final_matches_last": m,
            "got": solution_consistency(a),
        }
        for a, h, m in SOLUTION_CASES
    ]
    return {
        "target": TARGET,
        "counts": dict(counts),
        "target_met": all(counts[k] == TARGET[k] for k in TARGET),
        "annotation_cases": per_case,
        "solution_cases": sols,
    }


def census(data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "*.jsonl")))
    annot_by_split = {}          # split -> Counter of labels
    rows_by_split = {}           # split -> row count
    annot_total = Counter()
    mismatch_examples = []
    unparseable_examples = []
    # final-answer consistency
    final_checked = 0            # rows with >=1 annotation AND a #### answer
    final_mismatch = 0
    final_examples = []
    rows_with_annotation = 0

    for path in files:
        split = _split_of(path)
        split_counter = annot_by_split.setdefault(split, Counter())
        rows_by_split.setdefault(split, 0)
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                answer = row.get("answer", "")
                question = row.get("question", "")
                rows_by_split[split] += 1

                annots = find_annotations(answer)
                if annots:
                    rows_with_annotation += 1
                for expr, result in annots:
                    label = classify_annotation(expr, result)
                    split_counter[label] += 1
                    annot_total[label] += 1
                    if label == "mismatch" and len(mismatch_examples) < MAX_EXAMPLES:
                        mismatch_examples.append({
                            "split": split,
                            "expr": expr,
                            "stated": result,
                            "computed_fraction": _fraction_str(expr),
                            "computed_float": _float_str(expr),
                            "question": question[:200],
                        })
                    elif label in ("unparseable_expr", "unparseable_result") and len(unparseable_examples) < MAX_EXAMPLES:
                        unparseable_examples.append({
                            "split": split, "label": label,
                            "expr": expr, "stated": result,
                        })

                sol = solution_consistency(answer)
                if sol["has_annotation"] and sol.get("has_final") and sol["final_matches_last"] is not None:
                    final_checked += 1
                    if not sol["final_matches_last"]:
                        final_mismatch += 1
                        if len(final_examples) < MAX_EXAMPLES:
                            last_expr, last_result = annots[-1]
                            final_examples.append({
                                "split": split,
                                "last_annotation_expr": last_expr,
                                "last_annotation_result": last_result,
                                "question": question[:200],
                            })

    return {
        "files": [os.path.basename(p) for p in files],
        "rows_by_split": rows_by_split,
        "rows_total": sum(rows_by_split.values()),
        "rows_with_annotation": rows_with_annotation,
        "annotation_counts_total": dict(annot_total),
        "annotation_counts_by_split": {s: dict(c) for s, c in annot_by_split.items()},
        "final_answer_consistency": {
            "checked": final_checked,
            "mismatch": final_mismatch,
        },
        "mismatch_examples": mismatch_examples,
        "unparseable_examples": unparseable_examples,
        "final_mismatch_examples": final_examples,
    }


def copy_sources(out_dir):
    here = os.path.dirname(os.path.abspath(__file__))
    for name in SOURCE_FILES:
        src = os.path.join(here, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(out_dir, name))
    placeholder = os.path.join(out_dir, "README.md")
    with open(placeholder, "w", encoding="utf-8") as fh:
        fh.write("# gsm8k-calculator-annotation-census (placeholder)\n\n"
                 "The published README is authored at ship time from results.json.\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    result = {
        "name": "gsm8k-calculator-annotation-census",
        "dataset": "openai/grade-school-math (GSM8K), raw train.jsonl + test.jsonl",
        "method": {
            "annotation": "each <<expr=result>> classified by exact-rational arithmetic: "
                          "match / rounded (equals result at the shown decimal places) / "
                          "mismatch / unparseable_expr / unparseable_result",
            "final_answer": "the solution's '#### answer' compared to its LAST annotation's result",
            "rounding": "non-terminating annotations counted as 'rounded', NOT as errors",
        },
        "synthetic_corpus": _synthetic_corpus(),
        "census": census(args.data_dir),
    }

    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)

    copy_sources(args.out_dir)
    print("rows_total:", result["census"]["rows_total"])
    print("annotation_counts_total:", result["census"]["annotation_counts_total"])
    print("final_answer_consistency:", result["census"]["final_answer_consistency"])


if __name__ == "__main__":
    main()
