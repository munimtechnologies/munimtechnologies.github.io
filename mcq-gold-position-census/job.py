"""MCQ gold-answer-POSITION census over OpenBookQA, ARC-Easy, ARC-Challenge, CommonsenseQA and MMLU (audit 53).

Audit 51 showed OpenBookQA's gold is reliably the LONGEST option while exam-sourced ARC is not. This audit asks
the sibling, construction-side question: where in the released option list is the gold placed? For each
benchmark it censuses the 0-based gold position, tests it against a uniform distribution with a Pearson
chi-square goodness-of-fit, and reports the accuracy of a constant "always pick position p" heuristic versus
the random-choice baseline -- the position analogue of audit 51's "pick the longest" baseline.

It reuses the parquet loaders from audit 52 (choices_key / choices_answer adapters) and the exact-count census
core (position_census.py). Pre-registers a hand-traced fixture (exact-equality check) and three predictions,
each a finding either way.

Usage: python job.py --out-dir /out   (network required to fetch the parquet listings and files)
Apache-2.0.
"""

import argparse
import io
import json
import os
import urllib.request

import pyarrow.parquet as pq

import position_census as pc
import cases

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"

SCHEMA_COLS = {
    "choices_key": ["choices", "answerKey"],
    "choices_answer": ["choices", "answer"],
}


def _get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry transient network errors
            last = e
    raise RuntimeError("GET failed after %d tries: %s (%s)" % (tries, url, last))


def parquet_files(hf_dataset, config, wanted_splits):
    data = json.loads(_get(PARQUET_API % hf_dataset).decode("utf-8"))
    out = []
    for f in data["parquet_files"]:
        if f["config"] == config and f["split"] in wanted_splits:
            out.append((f["split"], f["url"]))
    return sorted(out)


def _extract_choices(ch):
    """Return (labels, texts) whether choices is a dict-of-arrays or a list-of-structs."""
    if isinstance(ch, dict):
        return list(ch["label"]), list(ch["text"])
    labels = [o["label"] for o in ch]
    texts = [o["text"] for o in ch]
    return labels, texts


def normalize(schema, cols):
    """Adapt one raw parquet row (a dict of the schema's columns) to (labels, texts, answer_key)."""
    if schema == "choices_key":
        labels, texts = _extract_choices(cols["choices"])
        ak = cols["answerKey"]
        key = ak.strip() if isinstance(ak, str) else ak
        return labels, texts, key
    if schema == "choices_answer":
        choices = list(cols["choices"])
        labels = [str(i) for i in range(len(choices))]
        return labels, choices, str(cols["answer"])
    raise ValueError("unknown schema %r" % schema)


def read_benchmark(spec):
    rows = []
    counts = {}
    colnames = SCHEMA_COLS[spec["schema"]]
    for split, url in parquet_files(spec["hf"], spec["config"], set(spec["splits"])):
        table = pq.read_table(io.BytesIO(_get(url)), columns=colnames)
        data = {c: table.column(c).to_pylist() for c in colnames}
        n = len(data[colnames[0]])
        counts[split] = n
        for i in range(n):
            labels, texts, key = normalize(spec["schema"], {c: data[c][i] for c in colnames})
            rows.append((spec["benchmark"], labels, texts, key))
    return rows, counts


def predictions(rep):
    """Pre-registered real-data predictions, each a finding either way. Decided before any real number seen."""
    benches = sorted(rep)

    # P1 (structural): every benchmark parses clean (0 bad_key, 0 degenerate) and has a single dominant option
    # count that covers at least 95% of its valid rows, so "gold position" is well defined.
    clean = all(rep[b]["n_bad_key"] == 0 and rep[b]["n_degenerate"] == 0 for b in benches)
    coverage = {b: rep[b]["modal_coverage"] for b in benches}
    p1 = clean and all((c is not None and c >= 0.95) for c in coverage.values())

    # P2 (HEADLINE): the exam/textbook-sourced MMLU shows a construction-side gold-position skew -- its
    # whole-'all' gold-position distribution is rejected as uniform at alpha=0.001 -- while crowd-authored
    # OpenBookQA, which already leaks via answer LENGTH (audit 51), does NOT additionally leak via position
    # (its gold-position distribution is NOT rejected at 0.001). A dissociation: OBQA's artifact is
    # length-specific, not positional.
    mmlu_rej = rep["mmlu"]["modal"]["uniform_rejected_0.001"]
    obqa_rej = rep["openbookqa"]["modal"]["uniform_rejected_0.001"]
    p2 = (mmlu_rej is True) and (obqa_rej is False)

    # P3 (exploitability): among all five benchmarks, MMLU has the strictly largest "best constant position
    # minus chance" gap -- a constant-position guess is the most exploitable in MMLU.
    gaps = {b: rep[b]["modal"]["best_minus_chance"] for b in benches}
    others = [b for b in benches if b != "mmlu"]
    p3 = all(gaps["mmlu"] > gaps[b] for b in others)

    return {
        "P1_clean_parse_and_well_defined_position": bool(p1),
        "P1_detail": {"clean": bool(clean), "modal_coverage": coverage},
        "P2_mmlu_skewed_openbookqa_uniform": bool(p2),
        "P2_detail": {"mmlu_uniform_rejected_0.001": mmlu_rej, "openbookqa_uniform_rejected_0.001": obqa_rej,
                      "all_uniform_rejected_0.001": {b: rep[b]["modal"]["uniform_rejected_0.001"] for b in benches}},
        "P3_mmlu_largest_best_position_gap": bool(p3),
        "P3_detail": {"best_minus_chance": gaps},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Pre-registered synthetic fixture: exact-equality check before any real data is read.
    fixture_census = pc.run_census(cases.FIXTURE_ROWS)
    target_met = (fixture_census == cases.TARGET)
    print("[fixture] run_census == TARGET : %s" % target_met)
    if not target_met:
        raise SystemExit("fixture mismatch -- aborting before real data")

    # 2) Real data.
    all_rows = []
    split_counts = {}
    for spec in cases.SPECS:
        rows, counts = read_benchmark(spec)
        all_rows.extend(rows)
        split_counts[spec["benchmark"]] = counts
        print("[load] %-14s %s" % (spec["benchmark"], counts))

    census = pc.run_census(all_rows)
    report = pc.to_report(census)
    preds = predictions(report)

    # sanity: do observed split sizes match the documented ones?
    rows_as_expected = True
    counts_check = {}
    for bench, exp in cases.EXPECTED_SPLIT_COUNTS.items():
        obs = split_counts.get(bench, {})
        ok = (obs == exp)
        rows_as_expected = rows_as_expected and ok
        counts_check[bench] = {"observed": obs, "expected": exp, "match": ok}

    # diagnostics (land in summary_tail)
    for bench in sorted(report):
        e = report[bench]
        m = e.get("modal")
        if m is None:
            print("[diag] %-14s no valid rows" % bench)
            continue
        print("[diag] %-14s n=%6d k=%d cover=%.3f chance=%.4f best_pos=%d best_acc=%.4f (gap=%+.4f) "
              "chi2=%.1f df=%d rej0.001=%s rates=%s"
              % (bench, m["n"], e["modal_option_count"], e["modal_coverage"], m["chance_accuracy"],
                 m["best_position"], m["best_position_accuracy"], m["best_minus_chance"],
                 m["chi_square_stat"], m["df"], m["uniform_rejected_0.001"],
                 {p: round(r, 4) for p, r in m["pos_rates"].items()}))
    print("[prediction] P1_clean_parse_and_well_defined_position = %s"
          % ("HELD" if preds["P1_clean_parse_and_well_defined_position"] else "FAILED"))
    print("[prediction] P2_mmlu_skewed_openbookqa_uniform = %s  detail=%s"
          % ("HELD" if preds["P2_mmlu_skewed_openbookqa_uniform"] else "FAILED", preds["P2_detail"]))
    print("[prediction] P3_mmlu_largest_best_position_gap = %s  gaps=%s"
          % ("HELD" if preds["P3_mmlu_largest_best_position_gap"] else "FAILED", preds["P3_detail"]["best_minus_chance"]))

    out = {
        "dataset": ("OpenBookQA (allenai/openbookqa config 'main', train+validation+test), ARC-Easy and "
                    "ARC-Challenge (allenai/ai2_arc, train+validation+test), CommonsenseQA (tau/commonsense_qa "
                    "config 'default', train+validation; test has no gold) and MMLU (cais/mmlu config 'all', "
                    "test+validation+dev; auxiliary_train excluded as a mix of other datasets), read from the "
                    "HuggingFace auto-converted parquet via the datasets-server parquet API. For each "
                    "multiple-choice question this audit records the 0-based INDEX of the gold option within "
                    "the released option list, bucketed by option count, and for each benchmark's modal option "
                    "count reports the gold-position distribution, a Pearson chi-square goodness-of-fit against "
                    "a uniform distribution, and the accuracy of a constant 'always pick position p' heuristic "
                    "versus the random-choice baseline. This is a construction property of the benchmark -- "
                    "where the correct answer was placed -- not a model's position / selection bias."),
        "crowd_benchmarks": cases.CROWD_BENCHMARKS,
        "exam_benchmarks": cases.EXAM_BENCHMARKS,
        "rows_as_expected": rows_as_expected,
        "split_counts_check": counts_check,
        "synthetic_corpus": {"target_met": target_met, "n_fixture_rows": len(cases.FIXTURE_ROWS)},
        "alpha": pc.ALPHA,
        "by_benchmark": report,
        "predictions": preds,
        "note": ("P1 (structural, finding either way): every benchmark parses with 0 bad_key and 0 degenerate "
                 "and has a single dominant option count covering >=95% of valid rows, so gold position is "
                 "well defined. P2 (directional headline, finding either way): exam-sourced MMLU's whole-'all' "
                 "gold-position distribution is rejected as uniform at alpha=0.001 while crowd-authored "
                 "OpenBookQA -- which leaks via answer LENGTH (audit 51) -- is NOT, a length-vs-position "
                 "dissociation. P3 (exploitability, finding either way): among the five benchmarks MMLU has the "
                 "largest 'best constant position minus chance' gap. The chi-square statistic and df are "
                 "reported so an exact p-value can be recomputed; 'best_position_accuracy' is the accuracy of "
                 "always guessing the single most frequent gold position. Measures construction, not any model."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
