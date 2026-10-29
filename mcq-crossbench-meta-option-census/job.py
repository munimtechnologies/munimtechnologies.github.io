"""CROSS-BENCHMARK meta-option census (audit 57): is MMLU's "all of the above" artifact MMLU-specific?

Audit 56 showed MMLU's last-option ("the answer is D") tilt is mostly an "all of the above"/meta-option artifact:
meta options are 4.86% of MMLU questions, sit last 92.5% of the time, and are the gold 59.6% of the time.
Audit 53 showed ARC-Easy, ARC-Challenge and CommonsenseQA are positionally uniform (no tilt).

This audit ports audit 56's exact meta-option classifier and gold-position census to FOUR other benchmarks --
ARC-Easy, ARC-Challenge, CommonsenseQA and HellaSwag -- to test whether the meta-option mechanism is a general
exam-authoring convention or specific to MMLU, and (newly) to measure HellaSwag's gold-position distribution,
which audit 53 did not cover. Options that are free-text sentence completions (HellaSwag) or short noun phrases
(CommonsenseQA) are predicted to carry essentially no meta options; ARC is grade-school science-exam material
like MMLU, so whether it carries them is the open question (the headline).

It reuses position_census.py, meta_option.py and both of their hand-traced fixtures verbatim, adds a per-schema
row-shaping layer (loaders.py, tested in test_loaders.py), and pre-registers five predictions, each a finding
either way, decided before any real number was seen.

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
import meta_option as mo
import loaders
import cases

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"
N_EXAMPLES = 4


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


def read_columns(url, cols):
    table = pq.read_table(io.BytesIO(_get(url)), columns=cols)
    return {c: table.column(c).to_pylist() for c in cols}


def load_dataset(spec):
    """Read one benchmark, returning (rows, split_counts). Each row is (dataset_name, labels, texts, answer_key)."""
    name = spec["name"]
    schema = spec["schema"]
    rows = []
    counts = {}
    for split, url in parquet_files(spec["hf"], spec["config"], set(spec["splits"])):
        if schema == "choices_struct":
            data = read_columns(url, ["choices", "answerKey"])
            n = len(data["choices"])
            for ch, ak in zip(data["choices"], data["answerKey"]):
                labels, texts, key = loaders.shape_choices_struct(ch, ak)
                rows.append((name, labels, texts, key))
        elif schema == "endings":
            data = read_columns(url, ["endings", "label"])
            n = len(data["endings"])
            for ends, lab in zip(data["endings"], data["label"]):
                labels, texts, key = loaders.shape_endings(ends, lab)
                rows.append((name, labels, texts, key))
        else:
            raise RuntimeError("unknown schema %r for %s" % (schema, name))
        counts[split] = counts.get(split, 0) + n  # accumulate in case a split spans multiple parquet shards
    return rows, counts


def meta_rate_of(meta_rep):
    """(total_valid, n_meta_questions, meta_rate): share of valid questions classed in any non-plain category."""
    total_valid = sum(meta_rep[c]["n"] for c in meta_rep)
    plain_n = meta_rep.get("plain", {}).get("n", 0)
    n_meta = total_valid - plain_n
    return total_valid, n_meta, (n_meta / total_valid if total_valid else None)


def aota_nota_last(meta_rep):
    """(n_questions_with_an_aota_or_nota_option, n_of_them_with_it_last) pooled over the aota and nota categories."""
    n_q = sum(meta_rep[c]["n_with_meta_option"] for c in ("aota", "nota") if c in meta_rep)
    n_last = sum(meta_rep[c]["n_meta_last"] for c in ("aota", "nota") if c in meta_rep)
    return n_q, n_last


def summarise(name, display, rows):
    """Build the full per-dataset summary from its (name, labels, texts, key) rows."""
    pooled = pc.to_report(pc.run_census(rows))[name]
    cats = [mo.classify_question(t) for (_n, _l, t, _k) in rows]
    cat_rep = pc.to_report(pc.run_census([(c, l, t, k) for c, (_n, l, t, k) in zip(cats, rows)]))
    split_rep = pc.to_report(pc.run_census([("plain" if c == "plain" else "any_meta", l, t, k)
                                            for c, (_n, l, t, k) in zip(cats, rows)]))
    meta_rep = mo.meta_report(mo.run_meta_census(rows))
    total_valid, n_meta, rate = meta_rate_of(meta_rep)
    examples = []
    for c, (_n, _l, t, k) in zip(cats, rows):
        if c != "plain" and len(examples) < N_EXAMPLES:
            examples.append({"category": c, "choices": t, "answer_index_or_label": k})
    return {
        "display": display,
        "n_valid": pooled["n_valid"],
        "n_bad_key": pooled["n_bad_key"],
        "n_degenerate": pooled["n_degenerate"],
        "total_valid_meta": total_valid,
        "n_meta_questions": n_meta,
        "meta_option_rate": rate,
        "category_counts": {c: meta_rep[c]["n"] for c in meta_rep},
        "option_count_hist": pooled["option_count_hist"],
        "gold_position_pooled": pooled,
        "by_category_gold_position": cat_rep,
        "plain_vs_any_meta_gold_position": split_rep,
        "meta_option_placement_and_gold": meta_rep,
        "examples": examples,
    }


def predictions(summ, arc_pooled_rate, p5_n, p5_last):
    """Pre-registered predictions, each a finding either way. Decided before any real number was seen."""
    # P1 (structural): every dataset parses clean on its gold-bearing splits -- 0 degenerate and 0 bad_key
    # (confirms the goldless test splits were correctly excluded and the shaping is sound).
    clean = all(summ[n]["n_degenerate"] == 0 and summ[n]["n_bad_key"] == 0 for n in summ)

    # P2 (completions carry no meta options): HellaSwag's meta-option rate is below NO_META_THRESHOLD.
    p2 = summ["hellaswag"]["meta_option_rate"] is not None and \
        summ["hellaswag"]["meta_option_rate"] < cases.NO_META_THRESHOLD

    # P3 (crowd short-answer carries no meta options): CommonsenseQA's meta-option rate is below the threshold.
    p3 = summ["commonsense_qa"]["meta_option_rate"] is not None and \
        summ["commonsense_qa"]["meta_option_rate"] < cases.NO_META_THRESHOLD

    # P4 (HEADLINE): ARC (Easy + Challenge pooled) carries meta options at an exam-like rate, above ARC_META_THRESHOLD.
    p4 = arc_pooled_rate is not None and arc_pooled_rate > cases.ARC_META_THRESHOLD

    # P5 (placement): pooling the four benchmarks, an "all/none of the above" option sits LAST in >=90% of the
    # questions carrying one -- vacuous if fewer than P5_MIN_N such questions exist.
    vacuous = p5_n < cases.P5_MIN_N
    p5 = (not vacuous) and (p5_last / p5_n) >= cases.LAST_RATE_THRESHOLD

    return {
        "P1_all_datasets_clean_parse": bool(clean),
        "P1_detail": {n: {"n_valid": summ[n]["n_valid"], "n_bad_key": summ[n]["n_bad_key"],
                          "n_degenerate": summ[n]["n_degenerate"]} for n in summ},
        "P2_hellaswag_essentially_no_meta": bool(p2),
        "P2_detail": {"meta_option_rate": summ["hellaswag"]["meta_option_rate"],
                      "n_meta_questions": summ["hellaswag"]["n_meta_questions"],
                      "threshold": cases.NO_META_THRESHOLD},
        "P3_commonsenseqa_essentially_no_meta": bool(p3),
        "P3_detail": {"meta_option_rate": summ["commonsense_qa"]["meta_option_rate"],
                      "n_meta_questions": summ["commonsense_qa"]["n_meta_questions"],
                      "threshold": cases.NO_META_THRESHOLD},
        "P4_arc_carries_meta_options": bool(p4),
        "P4_detail": {"arc_pooled_meta_option_rate": arc_pooled_rate, "threshold": cases.ARC_META_THRESHOLD,
                      "mmlu_reference_rate": cases.MMLU_REFERENCE["meta_option_rate"]},
        "P5_meta_options_sit_last_ge_90pct": bool(p5),
        "P5_detail": {"n_questions": p5_n, "n_last": p5_last,
                      "last_rate": (p5_last / p5_n) if p5_n else None, "vacuous": bool(vacuous),
                      "min_n": cases.P5_MIN_N, "threshold": cases.LAST_RATE_THRESHOLD},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Pre-registered synthetic fixtures: exact-equality checks before any real data is read.
    pos_ok = (pc.run_census(cases.FIXTURE_ROWS) == cases.TARGET)
    meta_ok = (mo.run_meta_census(cases.META_FIXTURE_ROWS) == cases.META_TARGET)
    print("[fixture] position run_census == TARGET : %s ; run_meta_census == META_TARGET : %s" % (pos_ok, meta_ok))
    if not (pos_ok and meta_ok):
        raise SystemExit("fixture mismatch -- aborting before real data")

    # 2) Real data: load and summarise each benchmark.
    summ = {}
    split_report = {}
    all_rows = {}
    for spec in cases.DATASETS:
        name = spec["name"]
        rows, counts = load_dataset(spec)
        all_rows[name] = rows
        expected = cases.EXPECTED_SPLIT_COUNTS.get(name, {})
        split_report[name] = {"observed": counts, "expected": expected, "match": counts == expected,
                              "expected_total_valid": cases.EXPECTED_TOTAL_VALID.get(name)}
        summ[name] = summarise(name, spec["display"], rows)
        s = summ[name]
        print("[load] %-14s rows=%6d valid=%6d bad_key=%d degen=%d  meta=%d (%.4f)  cats=%s  k_hist=%s"
              % (name, len(rows), s["n_valid"], s["n_bad_key"], s["n_degenerate"], s["n_meta_questions"],
                 s["meta_option_rate"] if s["meta_option_rate"] is not None else -1.0, s["category_counts"],
                 s["option_count_hist"]))

    # 3) ARC pooled (Easy + Challenge) meta-option rate -> the headline P4.
    arc_rows = all_rows["arc_easy"] + all_rows["arc_challenge"]
    arc_meta = mo.meta_report(mo.run_meta_census([("arc", l, t, k) for (_n, l, t, k) in arc_rows]))
    arc_total, arc_nmeta, arc_rate = meta_rate_of(arc_meta)
    print("[arc-pooled] total_valid=%d meta=%d rate=%.4f cats=%s"
          % (arc_total, arc_nmeta, arc_rate if arc_rate is not None else -1.0,
             {c: arc_meta[c]["n"] for c in arc_meta}))

    # 4) Pool aota/nota placement across all four benchmarks -> P5.
    p5_n = 0
    p5_last = 0
    for name in summ:
        nq, nl = aota_nota_last(summ[name]["meta_option_placement_and_gold"])
        p5_n += nq
        p5_last += nl
    print("[placement-pooled] aota/nota questions=%d  sit-last=%d  rate=%s"
          % (p5_n, p5_last, (p5_last / p5_n) if p5_n else None))

    preds = predictions(summ, arc_rate, p5_n, p5_last)

    # Report each dataset's pooled gold-position modal stats (reproduces audit 53; HellaSwag is new).
    for name in summ:
        m = summ[name]["gold_position_pooled"].get("modal")
        if m:
            print("[position] %-14s n=%6d k=%d pos_rates=%s best=%d chi2=%.2f rej0.001=%s"
                  % (name, m["n"], m["df"] + 1, {q: round(r, 4) for q, r in m["pos_rates"].items()},
                     m["best_position"], m["chi_square_stat"], m["uniform_rejected_0.001"]))

    for name in ("P1_all_datasets_clean_parse", "P2_hellaswag_essentially_no_meta",
                 "P3_commonsenseqa_essentially_no_meta", "P4_arc_carries_meta_options",
                 "P5_meta_options_sit_last_ge_90pct"):
        print("[prediction] %s = %s" % (name, "HELD" if preds[name] else "FAILED"))

    out = {
        "datasets": ("ARC-Easy and ARC-Challenge (allenai/ai2_arc; train+validation+test), CommonsenseQA "
                     "(tau/commonsense_qa; train+validation, goldless test excluded) and HellaSwag "
                     "(Rowan/hellaswag; train+validation, goldless test excluded), read from the HuggingFace "
                     "auto-converted parquet via the datasets-server parquet API. Every question is classified "
                     "into ONE meta-option category (roman > aota > nota > letterref > plain; see meta_option.py) "
                     "and its gold position is recorded (position_census.py). This is a construction property of "
                     "each benchmark, not any model's behaviour. MMLU numbers are cited from audit 56, not "
                     "recomputed here."),
        "alpha": pc.ALPHA,
        "max_meta_tokens": mo.MAX_META_TOKENS,
        "thresholds": {"no_meta": cases.NO_META_THRESHOLD, "arc_meta": cases.ARC_META_THRESHOLD,
                       "last_rate": cases.LAST_RATE_THRESHOLD, "p5_min_n": cases.P5_MIN_N},
        "synthetic_corpus": {"position_target_met": pos_ok, "meta_target_met": meta_ok,
                             "n_position_fixture_rows": len(cases.FIXTURE_ROWS),
                             "n_meta_fixture_rows": len(cases.META_FIXTURE_ROWS)},
        "split_counts_check": split_report,
        "mmlu_reference_audit56": cases.MMLU_REFERENCE,
        "by_dataset": summ,
        "arc_pooled_meta": {"total_valid": arc_total, "n_meta_questions": arc_nmeta, "meta_option_rate": arc_rate,
                            "category_counts": {c: arc_meta[c]["n"] for c in arc_meta},
                            "placement_and_gold": arc_meta},
        "pooled_aota_nota_placement": {"n_questions": p5_n, "n_last": p5_last,
                                       "last_rate": (p5_last / p5_n) if p5_n else None},
        "predictions": preds,
        "note": ("P1 (structural): all four datasets parse clean (0 degenerate, 0 bad_key) on their gold-bearing "
                 "splits. P2/P3: HellaSwag (sentence completions) and CommonsenseQA (short noun phrases) carry "
                 "essentially no meta options (rate < 0.5%). P4 (headline): ARC carries meta options at an "
                 "exam-like rate (> 1%), like MMLU -- or, if it fails, the meta-option mechanism is MMLU-"
                 "specific. P5: where they occur, 'all/none of the above' options sit last in >=90% of questions. "
                 "Each is a finding either way. The classifier is regex-based and conservative; per-dataset "
                 "examples are listed so a reader can audit it. Measures construction, not any model."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
