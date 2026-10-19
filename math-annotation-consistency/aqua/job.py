"""Run the AQuA-RAT rationale inline-arithmetic self-consistency audit over the
full dataset (train + dev + test) and write a summary, a reldiff histogram, and
a labelled catalogue of genuine arithmetic errors.

Data: google-deepmind/AQuA train.json / dev.json / test.json (JSON-lines; fields
question, options, rationale, correct), downloaded by the compete runner into
/data. Standard library only.

v4: the extractor in audit.py now drops four classes of extraction artifact that
hand review found in v3's catalogue (ratio fragments, stripped radicals,
'x'-as-times splits) and sets precedence-ambiguous linearizations aside as
`ambiguous` rather than flagging them as errors. The driver is unchanged except
that it now also tallies the `ambiguous` set-aside bucket. Streaming (v2) and the
magnitude guards (v3) are retained.
"""

from __future__ import annotations

import argparse
import glob
import json
import os

import audit


def load_records(data_dir):
    """Yield (split, index, record) for each AQuA record, streaming line by line."""
    wanted = ["train.json", "dev.json", "test.json"]
    files = []
    for name in wanted:
        p = os.path.join(data_dir, name)
        if os.path.exists(p):
            files.append((name[:-5], p))
    if not files:  # fall back to any *.json present
        for p in sorted(glob.glob(os.path.join(data_dir, "*.json"))):
            files.append((os.path.basename(p)[:-5], p))
    for split, path in files:
        with open(path, "r", encoding="utf-8") as fh:
            first = ""
            while True:
                ch = fh.read(1)
                if ch == "":
                    break
                if not ch.isspace():
                    first = ch
                    break
            fh.seek(0)
            if first == "[":
                data = json.load(fh)
                if isinstance(data, list):
                    for i, rec in enumerate(data):
                        yield split, i, rec
                continue
            i = 0
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                yield split, i, rec
                i += 1


def bucket(reldiff):
    if reldiff == 0.0:
        return "exact"
    if reldiff <= 0.001:
        return "le_0p1pct"
    if reldiff <= 0.01:
        return "le_1pct"
    if reldiff <= 0.05:
        return "le_5pct"
    return "gt_5pct"


def _blank():
    return {"records": 0, "records_with_steps": 0, "records_all_exact": 0,
            "audited_steps": 0, "exact_steps": 0,
            "percent_setaside": 0, "ambiguous_setaside": 0,
            "unevaluable_setaside": 0, "buckets": {}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    per_split = {}
    overall = _blank()
    genuine_path = os.path.join(args.out_dir, "genuine_errors.jsonl")
    gf = open(genuine_path, "w", encoding="utf-8")
    n_genuine = 0

    for split, idx, rec in load_records(args.data_dir):
        rationale = rec.get("rationale", "") or ""
        ps = per_split.setdefault(split, _blank())
        ps["records"] += 1
        overall["records"] += 1

        steps = audit.audit_rationale(rationale)
        for key, st in (("percent_setaside", "percent"),
                        ("ambiguous_setaside", "ambiguous"),
                        ("unevaluable_setaside", "unevaluable")):
            c = sum(1 for s in steps if s["status"] == st)
            ps[key] += c
            overall[key] += c

        ok = [s for s in steps if s["status"] == "ok"]
        if not ok:
            continue
        ps["records_with_steps"] += 1
        overall["records_with_steps"] += 1
        all_exact = True
        for s in ok:
            ps["audited_steps"] += 1
            overall["audited_steps"] += 1
            if s["exact"]:
                ps["exact_steps"] += 1
                overall["exact_steps"] += 1
            else:
                all_exact = False
            b = bucket(s["reldiff"])
            ps["buckets"][b] = ps["buckets"].get(b, 0) + 1
            overall["buckets"][b] = overall["buckets"].get(b, 0) + 1
            if s["reldiff"] > 0.05:
                n_genuine += 1
                gf.write(json.dumps({
                    "split": split, "index": idx,
                    "left": s["left"], "right": s["right"],
                    "left_value": s["leftval"], "right_value": s["rightval"],
                    "reldiff": s["reldiff"],
                    "correct": rec.get("correct", ""),
                    "rationale": rationale[:1500],
                }) + "\n")
        if all_exact:
            ps["records_all_exact"] += 1
            overall["records_all_exact"] += 1

    gf.close()

    def rate(num, den):
        return (num / den) if den else None

    overall["exact_step_rate"] = rate(overall["exact_steps"], overall["audited_steps"])
    overall["genuine_error_steps_gt_5pct"] = n_genuine
    overall["genuine_error_rate_gt_5pct"] = rate(n_genuine, overall["audited_steps"])
    for ps in per_split.values():
        ps["exact_step_rate"] = rate(ps["exact_steps"], ps["audited_steps"])

    summary = {
        "dataset": "google-deepmind/AQuA (AQuA-RAT, Ling et al. 2017)",
        "version": "v4 (false-positive-hardened extractor)",
        "question": ("Within a single written equation LHS=RHS in an AQuA-RAT "
                     "rationale, does the compound left side's exact arithmetic "
                     "equal the plain number on the right?"),
        "method": ("Conservative extraction, v4: ratio/radical/x-times boundary "
                   "artifacts dropped; precedence-ambiguous linearizations set "
                   "aside; percent steps set aside; exact Fraction arithmetic; "
                   "audited only when the right side is a bare number and the left "
                   "applies >=1 operation."),
        "overall": overall,
        "per_split": per_split,
    }
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    with open(os.path.join(args.out_dir, "reldiff_histogram.json"), "w", encoding="utf-8") as fh:
        json.dump({"overall": overall["buckets"],
                   "per_split": {k: v["buckets"] for k, v in per_split.items()}},
                  fh, indent=2)
    print("records:", overall["records"],
          "records_with_steps:", overall["records_with_steps"],
          "audited_steps:", overall["audited_steps"])
    print("exact_step_rate:", overall["exact_step_rate"])
    print("genuine_error_steps_gt_5pct:", n_genuine,
          "rate:", overall["genuine_error_rate_gt_5pct"])
    print("ambiguous_setaside:", overall["ambiguous_setaside"],
          "percent_setaside:", overall["percent_setaside"],
          "unevaluable_setaside:", overall["unevaluable_setaside"])
    print("buckets:", overall["buckets"])


if __name__ == "__main__":
    main()
