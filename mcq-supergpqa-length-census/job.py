"""SuperGPQA answer-length shortcut census (audit 64).

SuperGPQA (m-a-p/SuperGPQA, NeurIPS 2025 Datasets and Benchmarks) wrote its distractors with LLM help under a
"confusing options in similar lengths" requirement and reports mean answer length 12.86 tokens against 12.64 for
options overall. A similar mean does not settle whether "pick the longest option" beats chance: audit 62 found
MMLU-Pro's added distractors shorter on average while its pick-longest shortcut doubled. This audit runs the exact
audit-51 length census on SuperGPQA, keyed by discipline, field, difficulty, calculation flag and option count,
plus a gold-position test on the 10-option questions and a letter/answer-text consistency count.

Gates before any prediction is scored: the hand-traced fixtures must match exactly, and the same pipeline must
reproduce audit 61's pooled MMLU-Pro numbers exactly. Nine predictions were pre-registered before any real number
was seen.

Usage: python job.py --out-dir /out   (network required to fetch the parquet listings and files)
Apache-2.0.
"""

import argparse
import io
import json
import os
import urllib.request

import pyarrow.parquet as pq

import cases
import gold_length as gl
import supergpqa as sg

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


def parquet_files(hf_dataset, config, wanted_splits):
    data = json.loads(_get(PARQUET_API % hf_dataset).decode("utf-8"))
    out = []
    for f in data["parquet_files"]:
        if f["config"] == config and f["split"] in wanted_splits:
            out.append((f["split"], f["url"]))
    return sorted(out)


def read_columns(spec):
    """Read the spec's columns from every wanted split. Returns (list of row dicts, split_counts)."""
    rows = []
    counts = {}
    cols = spec["cols"]
    for split, url in parquet_files(spec["hf"], spec["config"], set(spec["splits"])):
        table = pq.read_table(io.BytesIO(_get(url)), columns=cols)
        for c in cols:
            if c not in table.column_names:
                raise RuntimeError("%s parquet missing column %r: %s" % (spec["hf"], c, table.column_names))
        data = {c: table.column(c).to_pylist() for c in cols}
        n = len(data[cols[0]])
        counts[split] = counts.get(split, 0) + n
        for i in range(n):
            rows.append({c: data[c][i] for c in cols})
    return rows, counts


def report(rows, key_fn):
    return gl.to_report(gl.run_census(sg.census_rows(rows, key_fn)))


def fmt(key, e):
    if not e["n_valid"]:
        return "%-44s n=0" % key
    c = e["char"]
    return ("%-44s n=%5d chance=%.4f pick_longest=%.4f lift=%+.4f uniq_long=%.4f uniq_short=%.4f gold/dist=%.1f/%.1f"
            % (key, e["n_valid"], e["chance_accuracy"], c["longest_accuracy"], sg.lift(e),
               c["unique_longest_rate"], c["unique_shortest_rate"], c["mean_gold_len"],
               c["mean_distractor_len"] or 0.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Hand-traced fixtures must match exactly before any real data is read.
    core_ok = gl.run_census(cases.FIXTURE_ROWS) == cases.TARGET
    disc_ok = sg.digest(gl.run_census(sg.census_rows(cases.SG_ROWS, lambda r: r["discipline"]))) \
        == cases.SG_TARGET_DISCIPLINE
    calc_ok = sg.digest(gl.run_census(sg.census_rows(cases.SG_ROWS, lambda r: sg.calc_key(r["is_calculation"])))) \
        == cases.SG_TARGET_CALC
    diff_ok = sg.digest(gl.run_census(sg.census_rows(cases.SG_ROWS, lambda r: r["difficulty"]))) \
        == cases.SG_TARGET_DIFFICULTY
    qual_ok = sg.quality(cases.SG_ROWS) == (cases.SG_QUALITY_TARGET, cases.SG_QUALITY_EXAMPLES)
    chi_ok = sg.position_chi2(cases.CHI_INDICES, cases.CHI_K) == cases.CHI_TARGET
    print("[fixture] core=%s discipline=%s calc=%s difficulty=%s quality=%s chi2=%s"
          % (core_ok, disc_ok, calc_ok, diff_ok, qual_ok, chi_ok))
    if not (core_ok and disc_ok and calc_ok and diff_ok and qual_ok and chi_ok):
        raise SystemExit("fixture mismatch -- aborting before real data")

    # 2) Structural gate: the same pipeline must reproduce audit 61's pooled MMLU-Pro census.
    pro_rows, pro_counts = read_columns(cases.MMLU_PRO)
    print("[load] mmlu-pro %s" % pro_counts)
    pooled_pro = gl.to_report(gl.run_census(sg.mmlu_pro_rows(pro_rows, lambda r: "ALL")))["ALL"]
    gate_ok, gate_detail = sg.structural_gate(pooled_pro, cases.EXPECTED_MMLU_PRO)
    print("[structural-gate] reproduces audit 61 : %s" % gate_ok)
    for k, d in gate_detail.items():
        if not d["match"]:
            print("[structural-gate][MISMATCH] %s got=%s expected=%s" % (k, d["got"], d["expected"]))
    if not gate_ok:
        raise SystemExit("structural gate failed -- aborting")

    # 3) SuperGPQA.
    rows, counts = read_columns(cases.SUPERGPQA)
    n_rows = sum(counts.values())
    print("[load] supergpqa %s (paper: %d)" % (counts, cases.PAPER_ROW_COUNT))

    pooled = report(rows, lambda r: "ALL")["ALL"]
    by_discipline = report(rows, lambda r: r["discipline"] or "")
    by_field = report(rows, lambda r: (r["discipline"] or "") + "|" + (r["field"] or ""))
    by_difficulty = report(rows, lambda r: r["difficulty"] or "")
    by_calc = report(rows, lambda r: sg.calc_key(r["is_calculation"]))
    by_diff_calc = report(rows, lambda r: (r["difficulty"] or "") + "|" + sg.calc_key(r["is_calculation"]))
    by_option_count = report(rows, lambda r: "%02d" % len(r["options"] or []))

    qual, qual_ex = sg.quality(rows)
    pos = sg.position_chi2(sg.ten_option_positions(rows), 10)
    pos_out = {"n": pos["n"], "counts": pos["counts"], "chi2": float(pos["chi2"])}

    preds = sg.predictions(pooled, by_calc, by_difficulty, by_discipline, qual, pos_out)

    print("[pooled] " + fmt("ALL", pooled))
    print("[mmlu-pro] " + fmt("ALL", pooled_pro))
    for name, rep in (("difficulty", by_difficulty), ("calc", by_calc), ("diff|calc", by_diff_calc),
                      ("options", by_option_count), ("discipline", by_discipline)):
        for k in sorted(rep):
            print("[%s] %s" % (name, fmt(k, rep[k])))
    print("[quality] %s" % qual)
    print("[position] n=%d chi2=%.3f counts=%s" % (pos_out["n"], pos_out["chi2"], pos_out["counts"]))
    for name in sorted(p for p in preds if not p.endswith("_detail")):
        print("[prediction] %s = %s" % (name, "HELD" if preds[name] else "FAILED"))

    out = {
        "dataset": ("SuperGPQA (m-a-p/SuperGPQA config 'default', split 'train', the full released set) read from "
                    "the HuggingFace auto-converted parquet via the datasets-server parquet API. Gold position = "
                    "answer_letter (A = first option); the answer text is only used for the consistency count. "
                    "Lengths are characters after str.strip() (whitespace tokens alongside). This is a "
                    "construction property of the benchmark, not a model's behaviour."),
        "split_counts": counts,
        "paper_row_count": cases.PAPER_ROW_COUNT,
        "row_count_matches_paper": n_rows == cases.PAPER_ROW_COUNT,
        "fixtures": {"core": core_ok, "discipline": disc_ok, "calc": calc_ok, "difficulty": diff_ok,
                     "quality": qual_ok, "chi2": chi_ok},
        "structural_gate": {"passed": gate_ok, "detail": gate_detail},
        "mmlu_pro_pooled": pooled_pro,
        "pooled": pooled,
        "by_difficulty": by_difficulty,
        "by_calculation": by_calc,
        "by_difficulty_calculation": by_diff_calc,
        "by_option_count": by_option_count,
        "by_discipline": by_discipline,
        "by_field": by_field,
        "quality": qual,
        "quality_examples": qual_ex,
        "position_10_options": pos_out,
        "predictions": preds,
        "note": ("P1: pooled pick-longest under 1.5x chance. P2: pooled pick-longest lift at least +1 point. P3: "
                 "text questions' lift exceeds calculation questions'. P4: easy lift exceeds hard lift. P5: mean "
                 "gold length exceeds mean distractor length (characters). P6: gold unique-longest more often than "
                 "unique-shortest. P7: gold positions of 10-option questions uniform (chi-square df 9 below "
                 "27.877). P8: pick-longest beats chance in a strict majority of disciplines with n >= 100. P9: "
                 "answer text equals the lettered option everywhere. Each is a finding either way. Measures "
                 "agreement with a length heuristic, not correctness of any model."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
