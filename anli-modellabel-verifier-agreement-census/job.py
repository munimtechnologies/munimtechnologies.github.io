"""Run the ANLI per-(gold class, model_label) verifier-agreement census on the official release.

Reads the main ANLI examples from anli_v1.0.zip into a uid -> {split, gold, model_label} index, parses
the separately released verifier_labels_R1-3.jsonl, joins them by uid, and tallies -- per (gold class,
model_label bucket) -- the verifier unanimity and the writer-gold-vs-verifier-majority outcome. Also
reports the per-gold-class aggregate (which must reproduce audit 45) as a built-in cross-check. The
hand-traced fixture is asserted BEFORE any real file is touched.

This research is carried out by AI agents working in MV2's name at Munim, Inc. Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import cases
from modellabel_census import (
    LETTERS, MLABELS, aggregate_over_mlabels, census_by_gold_modellabel, flatten_gm,
    get_model_label, parse_verifier_row,
)

SPLITS = cases.SPLITS
ROUNDS = ("R1", "R2", "R3")


def read_verifier(path):
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if line:
                rows.append(parse_verifier_row(json.loads(line)))
    return rows


def _member_round_split(name):
    if not name.endswith(".jsonl") or name.endswith("/"):
        return None, None
    parts = name.split("/")
    rnd = next((p for p in parts if p in ROUNDS), None)
    stem = parts[-1][:-len(".jsonl")]
    split = stem if stem in SPLITS else None
    return rnd, split


def read_main(zip_path):
    index = {}
    totals = {}
    ml_present = {}
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            rnd, split = _member_round_split(name)
            if rnd is None or split is None:
                continue
            n = 0
            with_ml = 0
            with zf.open(name) as fh:
                for raw in fh:
                    line = raw.decode("utf-8").strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    ml = get_model_label(obj)
                    index[obj.get("uid")] = {"split": split, "round": rnd,
                                             "gold": obj.get("label"), "model_label": ml}
                    n += 1
                    if ml is not None and str(ml).strip():
                        with_ml += 1
            totals["%s/%s" % (rnd, split)] = n
            ml_present["%s/%s" % (rnd, split)] = with_ml
    return index, totals, ml_present


def _rates_cell(c):
    n = c["n"]
    return {
        "n": n,
        "unanimous": c["unanimous"],
        "unanimous_rate": (c["unanimous"] / n) if n else None,
        "match": c["match"],
        "match_rate": (c["match"] / n) if n else None,
        "differ": c["differ"],
        "no_majority": c["no_majority"],
        "no_majority_rate": (c["no_majority"] / n) if n else None,
        "k2": c["k2"], "k3": c["k3"], "k_other": c["k_other"], "k2_split": c["k2_split"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. Assert the hand-traced fixture BEFORE touching real data.
    fix_stats = census_by_gold_modellabel([parse_verifier_row(o) for o in cases.FIXTURE_VERIFIER_RAW],
                                           cases.build_gold_index(cases.FIXTURE_MAIN_RAW))
    fix = flatten_gm(fix_stats["per_gold_mlabel"], fix_stats["totals"])
    target_met = all(fix[k] == cases.TARGET[k] for k in cases.TARGET) and set(fix) == set(cases.TARGET)
    print("[fixture] target_met =", target_met)
    if not target_met:
        for k in sorted(set(fix) | set(cases.TARGET)):
            o, t = fix.get(k), cases.TARGET.get(k)
            if o != t:
                print("  MISMATCH %-16s observed=%r target=%r" % (k, o, t))
        print("FATAL: fixture does not match hand-traced target", file=sys.stderr)
        sys.exit(2)

    # 2. Locate the two inputs in the (reused) data volume.
    verifier_files = sorted(glob.glob(os.path.join(args.data_dir, "*verifier*.jsonl")))
    zips = sorted(glob.glob(os.path.join(args.data_dir, "*.zip")))
    print("[diag] verifier files:", verifier_files)
    print("[diag] zip files:", zips)
    if not verifier_files:
        print("FATAL: no verifier jsonl found in data dir", file=sys.stderr)
        sys.exit(3)
    if not zips:
        print("FATAL: no anli zip found in data dir", file=sys.stderr)
        sys.exit(4)

    # 3. Read both sides and run the per-(gold, model_label) census.
    verifier_rows = read_verifier(verifier_files[0])
    gold_index, main_totals, ml_present = read_main(zips[0])
    print("[diag] verifier lines =", len(verifier_rows), " main examples =", len(gold_index))
    print("[diag] main rows with a non-empty model_label, by file =", ml_present)
    stats = census_by_gold_modellabel(verifier_rows, gold_index)
    t = stats["totals"]
    print("[diag] totals =", t)

    pgm = stats["per_gold_mlabel"]
    per_gold_mlabel = {g: {m: _rates_cell(pgm[g][m]) for m in MLABELS} for g in LETTERS}
    per_gold = {g: _rates_cell(c) for g, c in aggregate_over_mlabels(pgm).items()}

    # 4. Pre-registered predictions (held/failed reported honestly).
    # P1 (structural): among joined rows with a recognised model_label, model_label != gold on >95%
    # (confirms, at the data level, that the retained examples really did fool the adversary model).
    denom = t["n_model_label_recognised"]
    fooled_rate = (t["n_model_fooled"] / denom) if denom else None
    p1 = fooled_rate is not None and fooled_rate > cases.MIN_FOOLED_RATE

    # P2 (directional, a finding either way): in at least one gold class the verifier unanimous rate
    # spans more than MIN_SPREAD across the recognised model_label buckets present (>=1 example each) --
    # i.e. WHICH wrong label the model chose predicts how decisively the verifiers agree.
    class_mlabel_spread = {}
    for g in LETTERS:
        urs = {m: per_gold_mlabel[g][m]["unanimous_rate"] for m in ("e", "n", "c")
               if per_gold_mlabel[g][m]["n"] > 0 and per_gold_mlabel[g][m]["unanimous_rate"] is not None}
        class_mlabel_spread[g] = (max(urs.values()) - min(urs.values())) if len(urs) >= 2 else None
    p2 = any(s is not None and s > cases.MIN_SPREAD for s in class_mlabel_spread.values())

    # P3 (structural): the writer gold == strict verifier majority on >95% in every (gold, mlabel) cell
    # with at least MIN_CELL_N examples (the per-cell slice of audit 39/45's near-ceiling match rate).
    big_cells = [(g, m) for g in LETTERS for m in MLABELS
                 if per_gold_mlabel[g][m]["n"] >= cases.MIN_CELL_N]
    p3 = all(per_gold_mlabel[g][m]["match_rate"] is not None
             and per_gold_mlabel[g][m]["match_rate"] > cases.MIN_MATCH_RATE for g, m in big_cells) \
        and len(big_cells) > 0

    predictions = {
        "P1_model_fooled_rate_above_min": p1,
        "P2_unanimity_varies_by_model_label_in_some_class": p2,
        "P3_match_rate_above_min_every_big_cell": p3,
    }
    print("[diag] model_fooled_rate =", None if fooled_rate is None else round(fooled_rate, 4))
    print("[diag] per-class unanimity spread across model_label buckets =",
          {g: (None if s is None else round(s, 4)) for g, s in class_mlabel_spread.items()})
    for g in LETTERS:
        row = {m: (None if per_gold_mlabel[g][m]["n"] == 0
                   else round(per_gold_mlabel[g][m]["unanimous_rate"], 4)) for m in MLABELS}
        ns = {m: per_gold_mlabel[g][m]["n"] for m in MLABELS}
        print("[diag] gold=%s unanimous_rate by model_label =" % g, row, " n =", ns)
    print("[diag] big cells (n >= %d) =" % cases.MIN_CELL_N, big_cells)
    for k, v in predictions.items():
        print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))

    out = {
        "dataset": "ANLI v1.0 (Nie, Williams, Dinan, Bansal, Weston and Kiela, 2020), R1/R2/R3, joined to "
                   "the separately released verifier_labels_R1-3.jsonl by uid. This audit cross-tabulates "
                   "the writer's gold label with the adversary model's predicted label (model_label): per "
                   "(gold class, model_label bucket) it tallies verifier unanimity and the "
                   "writer-gold-vs-verifier-majority outcome, to test whether WHICH wrong label the "
                   "model-in-the-loop predicted predicts how decisively ANLI's verifiers then endorse the "
                   "writer's gold, and to confirm at the data level that the retained examples fooled the "
                   "model (model_label != gold). Reuses audits 39/45/46 label/majority primitives verbatim; "
                   "per_gold_aggregate reproduces audit 45's per-class table.",
        "rows_as_expected": (t["n_orphan"] == 0 and t["n_gold_unexpected"] == 0),
        "synthetic_corpus": {"target_met": target_met, "observed": fix, "target": cases.TARGET},
        "main_totals_by_round_split": main_totals,
        "main_model_label_present_by_file": ml_present,
        "totals": t,
        "model_fooled_rate": fooled_rate,
        "per_gold_mlabel": per_gold_mlabel,
        "per_gold_aggregate": per_gold,
        "per_class_unanimity_spread_across_model_labels": class_mlabel_spread,
        "big_cells_tested_for_P3": big_cells,
        "examples_differ": stats["examples_differ"],
        "predictions": predictions,
        "note": "Verifier unanimity = all verifier labels identical (under ANLI's protocol a 3rd verifier "
                "is added only when the first 2 disagree, so this equals 'the first two agreed'). "
                "model_label is the label ANLI's model-in-the-loop predicted for the example; the 'x' "
                "bucket holds rows whose model_label is missing or unrecognised. match/differ/no_majority "
                "partition each (gold, model_label) cell by whether the writer's gold equals / differs from "
                "/ lacks a strict verifier majority. P1 (structural) bets model_label != gold on >95% of "
                "rows with a recognised model_label (the adversarial-filter construction, a finding either "
                "way). P2 (directional) bets the verifier unanimous rate spans >0.03 across model_label "
                "buckets in at least one gold class. P3 (structural) bets the gold==verifier-majority rate "
                "exceeds 0.95 in every (gold, model_label) cell with >=100 examples. per_gold_aggregate "
                "reproduces audit 45's per-class table. This audit measures AGREEMENT, not label "
                "correctness.",
    }
    out_path = os.path.join(args.out_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    print("[done] wrote", out_path)


if __name__ == "__main__":
    main()
