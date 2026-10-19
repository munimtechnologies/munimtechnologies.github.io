"""Run the MathQA annotated_formula consistency audit over the full dataset.

Reads the official MathQA.zip (train/dev/test JSON, plus operation_list.txt and
constant_list.txt) from --data-dir, evaluates every `annotated_formula` directly
(no number extraction from problem text), compares it to the labelled correct
option, and writes aggregate numbers + a per-problem catalog to --out-dir.

Standard library only.
"""

import argparse
import json
import os
import sys
import zipfile
from fractions import Fraction

import audit

SPLIT_KEYS = (("train", "train"), ("dev", "validation"), ("valid", "validation"),
              ("test", "test"))

TOLERANCES = [("t0", 0), ("t0_001", 0.001), ("t0_01", 0.01), ("t0_05", 0.05)]


def find_zip(data_dir):
    for name in os.listdir(data_dir):
        if name.lower().endswith(".zip"):
            return os.path.join(data_dir, name)
    raise SystemExit("no .zip found in %s" % data_dir)


def split_name_for(fname):
    base = os.path.basename(fname).lower()
    for key, norm in SPLIT_KEYS:
        if key in base:
            return norm
    return None


def load_splits(zip_path):
    """Yield (split_name, index, record) and return the aux text files."""
    aux = {}
    splits = {}
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename
            low = name.lower()
            if low.endswith("operation_list.txt") or low.endswith("constant_list.txt"):
                aux[os.path.basename(low)] = zf.read(name).decode("utf-8", "replace")
                continue
            if not low.endswith(".json"):
                continue
            sn = split_name_for(name)
            if sn is None:
                continue
            try:
                data = json.loads(zf.read(name).decode("utf-8", "replace"))
            except Exception:
                continue
            if isinstance(data, list) and data and isinstance(data[0], dict) \
                    and "annotated_formula" in data[0]:
                # Prefer the first file seen for a split name.
                splits.setdefault(sn, data)
    return splits, aux


def val_to_str(v):
    if isinstance(v, Fraction):
        return str(v)
    return repr(v)


def blank_counts():
    return {
        "total": 0,
        "evaluated": 0,
        "formula_unevaluable": 0,
        "formula_parse_error": 0,
        "formula_unsupported": 0,
        "option_unparseable": 0,
        "formula_exact_eval": 0,
        "mismatch": {k: 0 for k, _ in TOLERANCES},
        "pure_total": 0,
        "pure_mismatch": 0,
    }


def classify_formula_error(msg):
    if "unsupported" in msg:
        return "formula_unsupported"
    return "formula_parse_error"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    zip_path = find_zip(args.data_dir)
    splits, aux = load_splits(zip_path)
    if not splits:
        raise SystemExit("no usable splits parsed from %s" % zip_path)

    op_freq = {}
    const_freq = {}
    per_split = {}
    pure_mismatch_examples = []
    catalog_path = os.path.join(args.out_dir, "catalog.jsonl")

    with open(catalog_path, "w", encoding="utf-8") as cat:
        for sn in sorted(splits):
            records = splits[sn]
            c = blank_counts()
            for i, rec in enumerate(records):
                c["total"] += 1
                formula = (rec.get("annotated_formula") or "").strip()
                options = rec.get("options") or ""
                correct = (rec.get("correct") or "").strip().lower()

                # Vocabulary (best effort; parse errors still counted below).
                try:
                    node = audit.parse(formula)
                    audit.collect_names(node, op_freq, const_freq)
                    pure = audit.is_pure_exact_arithmetic(node)
                except audit.EvalError:
                    node = None
                    pure = False

                row = {"s": sn, "i": i, "c": correct}

                # Option value.
                opt_val = None
                opt_exact = False
                try:
                    opts = audit.parse_options(options)
                    if correct not in opts:
                        raise audit.EvalError("correct letter %r not in options" % correct)
                    opt_val, opt_exact = audit.parse_option_value(opts[correct])
                except audit.EvalError:
                    opt_val = None

                # Formula value.
                f_val = None
                f_exact = False
                f_err = None
                if node is not None:
                    try:
                        f_val, f_exact = audit.evaluate(node)
                    except audit.EvalError as e:
                        f_err = str(e)
                else:
                    f_err = "parse error"

                if f_val is None:
                    c["formula_unevaluable"] += 1
                    c[classify_formula_error(f_err or "")] += 1
                    row["st"] = "formula_unevaluable"
                    cat.write(json.dumps(row) + "\n")
                    continue
                if opt_val is None:
                    c["option_unparseable"] += 1
                    row["st"] = "option_unparseable"
                    row["fr"] = val_to_str(f_val)
                    cat.write(json.dumps(row) + "\n")
                    continue

                c["evaluated"] += 1
                if f_exact:
                    c["formula_exact_eval"] += 1

                row["st"] = "evaluated"
                row["fr"] = val_to_str(f_val)
                row["ov"] = val_to_str(opt_val)
                row["ex"] = bool(f_exact and opt_exact)

                # Mismatch at each tolerance.
                for key, tol in TOLERANCES:
                    if tol == 0 and f_exact and opt_exact:
                        match = (Fraction(f_val) == Fraction(opt_val))
                    else:
                        match = audit.rel_match(f_val, opt_val, tol)
                    if not match:
                        c["mismatch"][key] += 1
                    row["m_" + key] = bool(match)

                # Headline: pure exact-arithmetic subset.
                if pure and f_exact and opt_exact:
                    c["pure_total"] += 1
                    exact_match = (Fraction(f_val) == Fraction(opt_val))
                    if not exact_match:
                        c["pure_mismatch"] += 1
                        if len(pure_mismatch_examples) < 1000:
                            pure_mismatch_examples.append({
                                "split": sn, "index": i, "correct": correct,
                                "annotated_formula": formula,
                                "formula_result": val_to_str(f_val),
                                "option_value": val_to_str(opt_val),
                                "options": options,
                            })
                cat.write(json.dumps(row) + "\n")
            per_split[sn] = c

    # Aggregate across splits.
    agg = blank_counts()
    for sn, c in per_split.items():
        for k in ("total", "evaluated", "formula_unevaluable", "formula_parse_error",
                  "formula_unsupported", "option_unparseable", "formula_exact_eval",
                  "pure_total", "pure_mismatch"):
            agg[k] += c[k]
        for key, _ in TOLERANCES:
            agg["mismatch"][key] += c["mismatch"][key]

    def rate(num, den):
        return round(num / den, 6) if den else None

    def rates_block(c):
        return {
            "evaluated_mismatch_rate": {
                k: rate(c["mismatch"][k], c["evaluated"]) for k, _ in TOLERANCES
            },
            "pure_exact_mismatch_rate": rate(c["pure_mismatch"], c["pure_total"]),
        }

    summary = {
        "dataset": "allenai/math_qa (MathQA.zip, math-qa.github.io)",
        "method": ("Evaluate annotated_formula directly (literal numbers, no "
                   "problem-text number extraction); compare to the labelled "
                   "correct option. Exact rational arithmetic via fractions; "
                   "values whose exact magnitude exceeds %d bits are reported "
                   "unevaluable rather than built." % audit.MAX_VALUE_BITS),
        "max_value_bits": audit.MAX_VALUE_BITS,
        "supported_ops": sorted(audit.SUPPORTED_OPS),
        "exact_arithmetic_ops": sorted(audit.EXACT_ARITHMETIC_OPS),
        "tolerances": {k: tol for k, tol in TOLERANCES},
        "per_split": {sn: {**per_split[sn], **rates_block(per_split[sn])}
                      for sn in per_split},
        "overall": {**agg, **rates_block(agg)},
        "op_frequency": dict(sorted(op_freq.items(), key=lambda kv: -kv[1])),
        "const_frequency": dict(sorted(const_freq.items(), key=lambda kv: -kv[1])),
        "aux_files_present": sorted(aux.keys()),
        "operation_list_head": (aux.get("operation_list.txt", "")[:2000]),
        "constant_list_head": (aux.get("constant_list.txt", "")[:2000]),
        "pure_mismatch_example_count": len(pure_mismatch_examples),
    }

    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(args.out_dir, "mismatches_pure.json"), "w", encoding="utf-8") as f:
        json.dump(pure_mismatch_examples, f, indent=2)

    # Compact human-readable echo to stdout.
    print(json.dumps({
        "per_split_totals": {sn: per_split[sn]["total"] for sn in per_split},
        "overall": {
            "total": agg["total"],
            "evaluated": agg["evaluated"],
            "formula_unevaluable": agg["formula_unevaluable"],
            "option_unparseable": agg["option_unparseable"],
            "pure_total": agg["pure_total"],
            "pure_mismatch": agg["pure_mismatch"],
            "pure_exact_mismatch_rate": rate(agg["pure_mismatch"], agg["pure_total"]),
            "evaluated_mismatch_rate": {
                k: rate(agg["mismatch"][k], agg["evaluated"]) for k, _ in TOLERANCES
            },
        },
    }, indent=2))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
