"""MCQ answer-length GENERALIZATION census over CommonsenseQA, HellaSwag and MMLU (audit 52).

Audit 51 found the gold-answer-length shortcut ("the correct option is the longest") strong in crowd-authored
OpenBookQA but absent in exam-sourced ARC. This audit tests whether that crowd-vs-exam split generalizes, on a
fresh, disjoint set: two crowd-authored benchmarks (CommonsenseQA, HellaSwag) and one exam/textbook-sourced
benchmark (MMLU `all`). It reuses audit 51's census core (gold_length.py) verbatim and adds per-benchmark
schema adapters plus a grouped prediction.

Pre-registers a hand-traced fixture (exact-equality check), then reads each benchmark's auto-converted parquet
via the HuggingFace datasets-server parquet API (no fragile hard-coded paths). Reports predictions, each a
finding either way.

Usage: python job.py --out-dir /out   (network required to fetch the parquet listings and files)
Apache-2.0.
"""

import argparse
import io
import json
import os
import urllib.request

import pyarrow.parquet as pq

import gold_length as gl
import cases

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"

SCHEMA_COLS = {
    "choices_key": ["choices", "answerKey"],
    "endings_label": ["endings", "label"],
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
    if schema == "endings_label":
        endings = list(cols["endings"])
        labels = [str(i) for i in range(len(endings))]
        lab = cols["label"]
        key = str(lab).strip() if lab is not None else ""
        return labels, endings, key
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


def grouped_predictions(rep):
    """Pre-registered predictions, each a finding either way. Decided before any real number was seen."""
    benches = list(rep)
    p1 = all(rep[b]["n_bad_key"] == 0 and rep[b]["n_degenerate"] == 0 for b in benches)

    def uniq(b):
        return rep[b]["char"]["unique_longest_rate"]

    def chance(b):
        return rep[b]["chance_accuracy"]

    crowd_above = {b: uniq(b) > chance(b) for b in cases.CROWD_BENCHMARKS}
    exam_atmost = {b: uniq(b) <= chance(b) for b in cases.EXAM_BENCHMARKS}
    p2 = all(crowd_above.values()) and all(exam_atmost.values())
    p3 = {b: rep[b]["char"]["longest_accuracy"] > chance(b) for b in cases.CROWD_BENCHMARKS}

    return {
        "P1_clean_parse_every_benchmark": bool(p1),
        "P2_crowd_shortcut_and_no_exam_shortcut": bool(p2),
        "P2_detail": {
            "crowd_gold_unique_longest_above_chance": {k: bool(v) for k, v in crowd_above.items()},
            "exam_gold_unique_longest_at_or_below_chance": {k: bool(v) for k, v in exam_atmost.items()},
        },
        "P3_crowd_pick_longest_beats_chance": {k: bool(v) for k, v in p3.items()},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Pre-registered synthetic fixture: exact-equality check before any real data is read.
    fixture_census = gl.run_census(cases.FIXTURE_ROWS)
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

    census = gl.run_census(all_rows)
    report = gl.to_report(census)
    preds = grouped_predictions(report)

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
        c = e["char"]
        print("[diag] %-14s n=%6d chance=%.4f gold_uniq_longest=%.4f (%d) longest_acc=%.4f "
              "mean_gold=%.2f mean_distr=%.2f delta=%+.2f hist=%s"
              % (bench, e["n_valid"], e["chance_accuracy"], c["unique_longest_rate"],
                 c["unique_longest_count"], c["longest_accuracy"], c["mean_gold_len"],
                 c["mean_distractor_len"], c["mean_gold_len"] - c["mean_distractor_len"],
                 e["option_count_hist"]))
    print("[prediction] P1_clean_parse_every_benchmark = %s"
          % ("HELD" if preds["P1_clean_parse_every_benchmark"] else "FAILED"))
    print("[prediction] P2_crowd_shortcut_and_no_exam_shortcut = %s  detail=%s"
          % ("HELD" if preds["P2_crowd_shortcut_and_no_exam_shortcut"] else "FAILED", preds["P2_detail"]))
    print("[prediction] P3_crowd_pick_longest_beats_chance = %s" % preds["P3_crowd_pick_longest_beats_chance"])

    out = {
        "dataset": ("CommonsenseQA (tau/commonsense_qa, train+validation; test has no gold), HellaSwag "
                    "(Rowan/hellaswag, train+validation; test has no gold) and MMLU (cais/mmlu config 'all', "
                    "test+validation+dev; auxiliary_train excluded as a mix of other datasets), read from the "
                    "HuggingFace auto-converted parquet via the datasets-server parquet API. For each "
                    "multiple-choice question this audit measures, per benchmark, how the length of the gold "
                    "option compares with its distractors -- by characters (after stripping) and by whitespace "
                    "tokens -- reporting how often the gold is the unique longest / unique shortest option, the "
                    "accuracy of a tie-aware 'pick the longest' heuristic versus the random-choice baseline, and "
                    "the mean gold vs distractor length. It tests whether audit 51's crowd-authored-vs-"
                    "exam-sourced length-shortcut split generalizes. Measures a construction property of the "
                    "benchmark, not model output."),
        "crowd_benchmarks": cases.CROWD_BENCHMARKS,
        "exam_benchmarks": cases.EXAM_BENCHMARKS,
        "rows_as_expected": rows_as_expected,
        "split_counts_check": counts_check,
        "synthetic_corpus": {"target_met": target_met, "n_fixture_rows": len(cases.FIXTURE_ROWS)},
        "by_benchmark": report,
        "predictions": preds,
        "note": ("P1 (structural, finding either way): every benchmark parses with 0 bad_key and 0 degenerate "
                 "questions over its gold-bearing splits. P2 (directional headline, finding either way): audit "
                 "51's split generalizes -- the gold is the UNIQUE longest option more often than the "
                 "random-choice baseline in BOTH crowd-authored benchmarks (CommonsenseQA, HellaSwag) AND at or "
                 "below chance in exam-sourced MMLU. P3 (exploitability, finding either way): in each "
                 "crowd-authored benchmark a tie-aware 'pick the longest' heuristic beats the random-choice "
                 "baseline. 'longest_accuracy' is the expected accuracy of a heuristic that always picks the "
                 "longest option and splits ties uniformly. Lengths are characters after str.strip(); a token "
                 "view is reported alongside. Measures AGREEMENT with a length heuristic, not correctness of "
                 "any model."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
