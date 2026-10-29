"""MMLU-Pro per-CATEGORY gold-answer-LENGTH census (audit 61).

Does MMLU-Pro's deliberate 10-option expansion ERASE the pick-longest answer-length shortcut the way audit 59
showed it erases MMLU's gold-POSITION / meta-option artifact? Audit 60 established MMLU's pooled char pick-longest
accuracy at 0.2805 (chance 0.250, a +3.05-point lift). This audit censuses gold-vs-distractor length per MMLU-Pro
CATEGORY over the `default` test split, reports each category's tie-aware pick-longest accuracy, variable chance
baseline, unique-longest rate and mean length gap, and compares the pooled lift with MMLU's.

It reuses the exact length-census core (gold_length.py, VERBATIM from audits 51/52/60) and the audits-52/60
hand-traced fixture (cases.py). As a hard STRUCTURAL validity gate it re-keys every MMLU-Pro row under one pooled
key and requires an EXACT reproduction of audit 59's parse (n_valid 12,032 and the option-count histogram) before
trusting the by-category split. Pre-registers four predictions, each a finding either way, decided before any real
number was seen.

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


def parquet_files(hf_dataset, config, wanted_splits):
    data = json.loads(_get(PARQUET_API % hf_dataset).decode("utf-8"))
    out = []
    for f in data["parquet_files"]:
        if f["config"] == config and f["split"] in wanted_splits:
            out.append((f["split"], f["url"]))
    return sorted(out)


def read_mmlu_pro_by_category(spec):
    """Read MMLU-Pro `default` test, returning (rows, split_counts). Row = (category, labels, texts, gold_idx_str)."""
    rows = []
    counts = {}
    cols = [spec["category_col"], spec["choices_col"], spec["answer_col"]]
    for split, url in parquet_files(spec["hf"], spec["config"], set(spec["splits"])):
        table = pq.read_table(io.BytesIO(_get(url)), columns=cols)
        for c in cols:
            if c not in table.column_names:
                raise RuntimeError("MMLU-Pro parquet missing column %r: %s" % (c, table.column_names))
        data = {c: table.column(c).to_pylist() for c in cols}
        n = len(data[cols[0]])
        counts[split] = counts.get(split, 0) + n
        for i in range(n):
            category = data[spec["category_col"]][i]
            choices = list(data[spec["choices_col"]][i])
            labels = [str(j) for j in range(len(choices))]
            key = str(data[spec["answer_col"]][i])
            rows.append((category, labels, choices, key))
    return rows, counts


def structural_gate_check(pooled):
    """Hard validity gate (P1): the pooled parse must reproduce audit 59's n_valid, modal k and option histogram.

    Same dataset and split as audit 59 -> an identical parse. If this fails, the by-category split is not trusted.
    Returns (ok, detail).
    """
    detail = {
        "n_valid": {"got": pooled["n_valid"], "expected": cases.EXPECTED_N_VALID,
                    "match": pooled["n_valid"] == cases.EXPECTED_N_VALID},
        "modal_option_count": {"got": pooled["modal_option_count"], "expected": cases.EXPECTED_MODAL_K,
                               "match": pooled["modal_option_count"] == cases.EXPECTED_MODAL_K},
        "option_count_hist": {"got": pooled["option_count_hist"], "expected": cases.EXPECTED_OPTION_HIST,
                              "match": pooled["option_count_hist"] == cases.EXPECTED_OPTION_HIST},
        "clean_parse": {"got": [pooled["n_bad_key"], pooled["n_degenerate"]], "expected": [0, 0],
                        "match": pooled["n_bad_key"] == 0 and pooled["n_degenerate"] == 0},
    }
    ok = all(d["match"] for d in detail.values())
    return ok, detail


def category_predictions(rep, pooled):
    """Pre-registered real-data predictions, each a finding either way. Decided before any real number seen."""
    cats = sorted(rep)
    n_cats = len(cats)

    gate_ok, gate_detail = structural_gate_check(pooled)
    clean = all(rep[c]["n_bad_key"] == 0 and rep[c]["n_degenerate"] == 0 for c in cats)

    def lift(c):
        return rep[c]["char"]["longest_accuracy"] - rep[c]["chance_accuracy"]

    pos_lift = [c for c in cats if lift(c) > 0.0]

    pooled_lift = pooled["char"]["longest_accuracy"] - pooled["chance_accuracy"]
    gold_longer_pooled = pooled["char"]["mean_gold_len"] > pooled["char"]["mean_distractor_len"]

    # P1 (STRUCTURAL gate + clean): pooled parse reproduces audit 59 exactly and every category parses clean.
    p1 = gate_ok and clean

    # P2 (HEADLINE, directional): MMLU-Pro's 10-way expansion WEAKENS the pick-longest length shortcut -- the
    # pooled char pick-longest LIFT over chance is smaller than MMLU's +3.05 points (audit 52/60).
    p2 = pooled_lift < cases.MMLU_POOLED_LIFT

    # P3 (directional): an authoring length bias SURVIVES in direction -- the pooled mean gold option is still
    # longer (chars) than the mean distractor, even after expansion.
    p3 = bool(gold_longer_pooled)

    # P4 (category spread): the length cue is NOT pervasive across categories after expansion -- a strict MINORITY
    # of MMLU-Pro categories individually show a positive char pick-longest lift.
    p4 = len(pos_lift) < (n_cats / 2.0) if n_cats else False

    return {
        "n_categories": n_cats,
        "pooled_char_lift": pooled_lift,
        "mmlu_pooled_char_lift": cases.MMLU_POOLED_LIFT,
        "P1_structural_gate_and_clean": bool(p1),
        "P1_detail": {"gate_ok": bool(gate_ok), "clean": bool(clean), "gate": gate_detail},
        "P2_expansion_weakens_length_shortcut": bool(p2),
        "P2_detail": {"pooled_char_lift": pooled_lift, "mmlu_pooled_char_lift": cases.MMLU_POOLED_LIFT},
        "P3_gold_still_longer_than_distractors_pooled": bool(p3),
        "P3_detail": {"pooled_mean_gold_len": pooled["char"]["mean_gold_len"],
                      "pooled_mean_distractor_len": pooled["char"]["mean_distractor_len"]},
        "P4_length_cue_not_pervasive_across_categories": bool(p4),
        "P4_detail": {"n_categories_positive_lift": len(pos_lift), "categories_positive_lift": sorted(pos_lift)},
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

    # 2) Real data: MMLU-Pro `default` test, keyed by category.
    rows, split_counts = read_mmlu_pro_by_category(cases.MMLU_PRO)
    print("[load] mmlu-pro splits %s  total_rows=%d" % (split_counts, len(rows)))

    census = gl.run_census(rows)
    report = gl.to_report(census)

    # 3) Pooled cross-check: re-key every row under "ALL" and require an EXACT reproduction of audit 59's parse.
    pooled = gl.to_report(gl.run_census([("ALL", a, b, c) for (_cat, a, b, c) in rows]))["ALL"]
    gate_ok, gate_detail = structural_gate_check(pooled)
    print("[structural-gate] reproduces audit 59 parse (n_valid + hist) : %s" % gate_ok)
    for k, d in gate_detail.items():
        if not d["match"]:
            print("[structural-gate][MISMATCH] %s got=%s expected=%s" % (k, d["got"], d["expected"]))
    if not gate_ok:
        raise SystemExit("structural gate failed -- aborting (by-category numbers not trustworthy)")

    preds = category_predictions(report, pooled)

    # diagnostics (land in summary_tail): pooled headline + the three categories with the largest char pick-longest
    # lift and the three with the smallest (most negative) lift.
    def lift(c):
        return report[c]["char"]["longest_accuracy"] - report[c]["chance_accuracy"]
    cats_by_lift = sorted(report, key=lift, reverse=True)
    top = cats_by_lift[:3]
    bottom = cats_by_lift[-3:]
    pc_ = pooled["char"]
    print("[pooled] n=%d chance=%.4f pick_longest=%.4f lift=%+.4f (mmlu lift %+.4f) uniq_longest_rate=%.4f gold_len=%.3f distr_len=%.3f gap=%+.3f"
          % (pooled["n_valid"], pooled["chance_accuracy"], pc_["longest_accuracy"],
             pc_["longest_accuracy"] - pooled["chance_accuracy"], cases.MMLU_POOLED_LIFT,
             pc_["unique_longest_rate"], pc_["mean_gold_len"], pc_["mean_distractor_len"],
             pc_["mean_gold_len"] - pc_["mean_distractor_len"]))
    print("[cross] n_categories=%d  positive_lift=%d" % (preds["n_categories"],
          preds["P4_detail"]["n_categories_positive_lift"]))
    for c in top + bottom:
        ch = report[c]["char"]
        print("[cat] %-20s n=%4d chance=%.4f pick_longest=%.4f lift=%+.4f uniq_long=%.4f gap=%+.3f"
              % (c, report[c]["n_valid"], report[c]["chance_accuracy"], ch["longest_accuracy"], lift(c),
                 ch["unique_longest_rate"], ch["mean_gold_len"] - ch["mean_distractor_len"]))
    print("[prediction] P1_structural_gate_and_clean = %s"
          % ("HELD" if preds["P1_structural_gate_and_clean"] else "FAILED"))
    print("[prediction] P2_expansion_weakens_length_shortcut = %s  (pooled lift %+.4f vs mmlu %+.4f)"
          % ("HELD" if preds["P2_expansion_weakens_length_shortcut"] else "FAILED",
             preds["pooled_char_lift"], cases.MMLU_POOLED_LIFT))
    print("[prediction] P3_gold_still_longer_than_distractors_pooled = %s"
          % ("HELD" if preds["P3_gold_still_longer_than_distractors_pooled"] else "FAILED"))
    print("[prediction] P4_length_cue_not_pervasive_across_categories = %s  (%d/%d categories positive lift)"
          % ("HELD" if preds["P4_length_cue_not_pervasive_across_categories"] else "FAILED",
             preds["P4_detail"]["n_categories_positive_lift"], preds["n_categories"]))

    counts_check = {"observed": split_counts, "expected": {"test": cases.EXPECTED_N_VALID},
                    "match": split_counts == {"test": cases.EXPECTED_N_VALID}}

    out = {
        "dataset": ("MMLU-Pro (TIGER-Lab/MMLU-Pro config 'default', test split), read from the HuggingFace "
                    "auto-converted parquet via the datasets-server parquet API. For each question this audit "
                    "compares the length of the GOLD option with its distractors -- by characters (after "
                    "stripping) and by whitespace tokens -- keyed by MMLU-Pro CATEGORY. MMLU-Pro options run 3-10 "
                    "per question (modal 10), so the random-choice baseline is accumulated exactly as sum(1/k). "
                    "Per category it reports how often the gold is the unique longest / shortest option, the "
                    "accuracy of a tie-aware 'pick the longest' heuristic versus the random-choice baseline, and "
                    "the mean gold vs distractor length; it then summarises the cross-category distribution and "
                    "compares the pooled pick-longest lift with MMLU's (audit 52/60). As a hard validity gate the "
                    "pooled parse must reproduce audit 59's n_valid (12,032) and option-count histogram EXACTLY. "
                    "This is a construction property of the benchmark -- how long the correct answer was written "
                    "-- not a model's behaviour."),
        "rows_as_expected": counts_check["match"],
        "split_counts_check": counts_check,
        "synthetic_corpus": {"target_met": target_met, "n_fixture_rows": len(cases.FIXTURE_ROWS)},
        "structural_gate": {"passed": gate_ok, "detail": gate_detail},
        "pooled_mmlu_pro": pooled,
        "by_category": report,
        "predictions": preds,
        "note": ("P1 (structural gate, finding either way): every category parses with 0 bad_key / 0 degenerate "
                 "and the pooled parse reproduces audit 59 exactly (n_valid 12,032, modal 10-option, identical "
                 "option-count histogram). P2 (HEADLINE, directional, finding either way): MMLU-Pro's 10-way "
                 "expansion weakens the pick-longest length shortcut -- the pooled char pick-longest lift over "
                 "chance is smaller than MMLU's +3.05 points (audit 52/60). P3 (directional, finding either way): "
                 "an authoring length bias survives in direction -- the pooled mean gold option is still longer "
                 "(chars) than the mean distractor. P4 (spread, finding either way): the length cue is not "
                 "pervasive across categories -- a strict minority of MMLU-Pro categories individually show a "
                 "positive char pick-longest lift. 'longest_accuracy' is the expected accuracy of a heuristic that "
                 "always picks the longest option and splits ties uniformly. Lengths are characters after "
                 "str.strip(); a token view is reported alongside. Measures AGREEMENT with a length heuristic, not "
                 "correctness of any model."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
