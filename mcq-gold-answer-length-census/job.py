"""MCQ gold-answer-length census over OpenBookQA, ARC-Easy and ARC-Challenge.

Pre-registers a hand-traced fixture, then reads each benchmark's auto-converted parquet (via the HuggingFace
datasets-server parquet API, so no fragile hard-coded file paths), and measures, per benchmark, how often the
gold option is the longest / shortest and whether a "pick the longest option" heuristic beats the
random-choice baseline. Reports three pre-registered predictions, each a finding either way.

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


def parquet_files(hf_dataset, config):
    data = json.loads(_get(PARQUET_API % hf_dataset).decode("utf-8"))
    out = []
    for f in data["parquet_files"]:
        if f["config"] == config:
            out.append((f["split"], f["url"]))
    return sorted(out)


def _extract_choices(ch):
    """Return (labels, texts) whether the parquet stores choices as a dict-of-arrays or a list-of-structs."""
    if isinstance(ch, dict):
        return list(ch["label"]), list(ch["text"])
    labels = [o["label"] for o in ch]
    texts = [o["text"] for o in ch]
    return labels, texts


def read_benchmark(hf_dataset, config, benchmark):
    rows = []
    counts = {}
    for split, url in parquet_files(hf_dataset, config):
        table = pq.read_table(io.BytesIO(_get(url)), columns=["choices", "answerKey"])
        choices = table.column("choices").to_pylist()
        keys = table.column("answerKey").to_pylist()
        counts[split] = len(keys)
        for ch, ak in zip(choices, keys):
            labels, texts = _extract_choices(ch)
            key = ak.strip() if isinstance(ak, str) else ak
            rows.append((benchmark, labels, texts, key))
    return rows, counts


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
    for hf_dataset, config, benchmark in cases.SPECS:
        rows, counts = read_benchmark(hf_dataset, config, benchmark)
        all_rows.extend(rows)
        split_counts[benchmark] = counts
        print("[load] %-14s %s" % (benchmark, counts))

    census = gl.run_census(all_rows)
    report = gl.to_report(census)
    preds = gl.predictions(report)

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
        print("[diag] %-14s n=%5d chance=%.4f gold_uniq_longest=%.4f (%d) longest_acc=%.4f "
              "mean_gold=%.2f mean_distr=%.2f delta=%+.2f hist=%s"
              % (bench, e["n_valid"], e["chance_accuracy"], c["unique_longest_rate"],
                 c["unique_longest_count"], c["longest_accuracy"], c["mean_gold_len"],
                 c["mean_distractor_len"], c["mean_gold_len"] - c["mean_distractor_len"],
                 e["option_count_hist"]))
    for k in ("P1_clean_parse_every_benchmark",
              "P2_gold_unique_longest_above_chance_every_benchmark",
              "P3_mean_gold_longer_than_distractors_every_benchmark"):
        print("[prediction] %s = %s" % (k, "HELD" if preds[k] else "FAILED"))

    out = {
        "dataset": ("OpenBookQA main (allenai/openbookqa), ARC-Easy and ARC-Challenge (allenai/ai2_arc), read "
                    "from the HuggingFace auto-converted parquet via the datasets-server parquet API. For each "
                    "multiple-choice question this audit measures, per benchmark, how the length of the gold "
                    "option compares with its distractors -- by characters (after stripping) and by whitespace "
                    "tokens -- reporting how often the gold is the unique longest / unique shortest option, the "
                    "accuracy of a tie-aware 'pick the longest' heuristic versus the random-choice baseline, and "
                    "the mean gold vs distractor length. It extends the answer-leakage family (audits 34-36) to "
                    "a length-shortcut lens. Measures a construction property of the benchmark, not model output."),
        "rows_as_expected": rows_as_expected,
        "split_counts_check": counts_check,
        "synthetic_corpus": {"target_met": target_met, "n_fixture_rows": len(cases.FIXTURE_ROWS)},
        "by_benchmark": report,
        "predictions": preds,
        "note": ("P1 (structural, finding either way): every benchmark parses with 0 bad_key and 0 degenerate "
                 "questions. P2 (directional headline, finding either way): in every benchmark the gold option is "
                 "the UNIQUE longest more often than the random-choice baseline (1/n_options) -- a construction-"
                 "side length shortcut. P3 (directional, finding either way): in every benchmark the mean gold "
                 "character length exceeds the mean distractor character length. 'longest_accuracy' is the "
                 "expected accuracy of a heuristic that always picks the longest option and splits ties "
                 "uniformly. Lengths are characters after str.strip(); a token view is reported alongside. "
                 "Measures AGREEMENT with a length heuristic, not correctness of any model."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
