"""MMLU per-SUBJECT gold-answer-LENGTH census (audit 60).

Audit 52 found MMLU's whole-'all' answer-length signal: across 15,858 questions (test+validation+dev, chance
0.250) the gold option was the UNIQUE longest 23.5% of the time and a tie-aware "pick the longest" heuristic
scored 0.2805 (a +3-point lift over chance), with the mean gold option +1.68 characters longer than the mean
distractor. Audit 52 reported this only POOLED. This audit asks whether that length cue is a pervasive authoring
tendency spread across MMLU's ~57 subjects, or an aggregate of a few subjects. It censuses gold-vs-distractor
length per SUBJECT over MMLU `all`, reports each subject's tie-aware pick-longest accuracy, chance baseline,
unique-longest rate and mean length gap, and summarises the cross-subject distribution.

It reuses the exact length-census core (gold_length.py, question_validity/_per_question/run_census VERBATIM from
audits 51/52) and the audit-52 hand-traced fixture (cases.py), and reuses audit 54's MMLU-by-subject parquet
reader. As a hard validity gate it re-keys every MMLU row under one pooled key and requires an EXACT
reproduction of audit 52's pooled MMLU numbers before trusting the by-subject split. Pre-registers four
predictions, each a finding either way, decided before any real number was seen.

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


def read_mmlu_by_subject(spec):
    """Read MMLU `all`, returning (rows, split_counts). Each row is (subject, labels, texts, gold_index_str)."""
    rows = []
    counts = {}
    cols = [spec["subject_col"], spec["choices_col"], spec["answer_col"]]
    for split, url in parquet_files(spec["hf"], spec["config"], set(spec["splits"])):
        table = pq.read_table(io.BytesIO(_get(url)), columns=cols)
        if spec["subject_col"] not in table.column_names:
            raise RuntimeError("MMLU parquet is missing a 'subject' column: %s" % table.column_names)
        data = {c: table.column(c).to_pylist() for c in cols}
        n = len(data[cols[0]])
        counts[split] = n
        for i in range(n):
            subject = data[spec["subject_col"]][i]
            choices = list(data[spec["choices_col"]][i])
            labels = [str(j) for j in range(len(choices))]
            key = str(data[spec["answer_col"]][i])
            rows.append((subject, labels, choices, key))
    return rows, counts


def pooled_reproduction_check(pooled, expected, tol=1e-9):
    """Hard validity gate: the pooled by-key split must reproduce audit 52's pooled MMLU numbers exactly.

    Counts are compared exactly; floats within a tiny tolerance (same core + same data = deterministic floats).
    Returns (ok, detail).
    """
    got = {
        "n_valid": pooled["n_valid"],
        "char_unique_longest_count": pooled["char"]["unique_longest_count"],
        "char_unique_shortest_count": pooled["char"]["unique_shortest_count"],
        "char_longest_accuracy": pooled["char"]["longest_accuracy"],
        "char_shortest_accuracy": pooled["char"]["shortest_accuracy"],
        "char_mean_gold_len": pooled["char"]["mean_gold_len"],
        "char_mean_distractor_len": pooled["char"]["mean_distractor_len"],
        "token_longest_accuracy": pooled["token"]["longest_accuracy"],
    }
    int_keys = ("n_valid", "char_unique_longest_count", "char_unique_shortest_count")
    detail = {}
    ok = True
    for k, exp in expected.items():
        g = got[k]
        if k in int_keys:
            match = (g == exp)
        else:
            match = abs(g - exp) <= tol
        detail[k] = {"got": g, "expected": exp, "match": bool(match)}
        ok = ok and match
    return ok, detail


def cross_subject_predictions(rep, total_valid):
    """Pre-registered real-data predictions, each a finding either way. Decided before any real number seen."""
    subjects = sorted(rep)
    n_subjects = len(subjects)

    # P1 (structural): every subject parses clean (0 bad_key, 0 degenerate), is modal 4-option with coverage
    # >= 0.95, and the per-subject valid counts partition MMLU-all exactly (sum == audit 52/53's 15,858).
    clean = all(rep[s]["n_bad_key"] == 0 and rep[s]["n_degenerate"] == 0 for s in subjects)
    all_k4 = all(rep[s]["modal_option_count"] == 4 for s in subjects)
    cover_ok = all((rep[s]["modal_coverage"] is not None and rep[s]["modal_coverage"] >= 0.95) for s in subjects)
    sum_valid = sum(rep[s]["n_valid"] for s in subjects)
    partition_ok = (sum_valid == total_valid)
    p1 = clean and all_k4 and cover_ok and partition_ok

    # Per-subject char length lift over that subject's chance baseline (MMLU is all 4-option -> chance ~ 0.25).
    def lift(s):
        return rep[s]["char"]["longest_accuracy"] - rep[s]["chance_accuracy"]

    pos_lift = [s for s in subjects if lift(s) > 0.0]
    gold_longer = [s for s in subjects if rep[s]["char"]["mean_gold_len"] > rep[s]["char"]["mean_distractor_len"]]
    strong_lift = [s for s in subjects if lift(s) >= 0.05]

    # P2 (HEADLINE): the char "pick the longest" shortcut is PERVASIVE -- in a strict MAJORITY of subjects the
    # tie-aware pick-longest accuracy beats that subject's chance baseline.
    p2 = len(pos_lift) > (n_subjects / 2.0) if n_subjects else False

    # P3 (directional): the mean length GAP is near-universal in direction -- in a strict majority of subjects
    # the mean gold option is longer (chars) than the mean distractor.
    p3 = len(gold_longer) > (n_subjects / 2.0) if n_subjects else False

    # P4 (concentration): the pooled +3-point lift is DIFFUSE, not concentrated -- fewer than a quarter of
    # subjects individually show a char pick-longest lift of at least +5 points.
    p4 = len(strong_lift) < (n_subjects / 4.0) if n_subjects else False

    return {
        "n_subjects": n_subjects,
        "P1_clean_well_defined_and_complete_partition": bool(p1),
        "P1_detail": {"clean": bool(clean), "all_modal_k_is_4": bool(all_k4), "coverage_ge_0.95": bool(cover_ok),
                      "sum_valid": sum_valid, "expected_total_valid": total_valid, "partition_ok": bool(partition_ok)},
        "P2_length_shortcut_pervasive": bool(p2),
        "P2_detail": {"n_subjects_pick_longest_beats_chance": len(pos_lift),
                      "subjects_pick_longest_beats_chance": sorted(pos_lift)},
        "P3_gold_longer_than_distractors_pervasive": bool(p3),
        "P3_detail": {"n_subjects_gold_mean_longer": len(gold_longer)},
        "P4_lift_is_diffuse_not_concentrated": bool(p4),
        "P4_detail": {"n_subjects_lift_ge_0.05": len(strong_lift),
                      "subjects_lift_ge_0.05": sorted(strong_lift)},
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

    # 2) Real data: MMLU `all`, keyed by subject.
    rows, split_counts = read_mmlu_by_subject(cases.MMLU)
    print("[load] mmlu splits %s  total_rows=%d" % (split_counts, len(rows)))

    census = gl.run_census(rows)
    report = gl.to_report(census)

    # 3) Pooled cross-check: re-key every row under "ALL" and require an EXACT reproduction of audit 52's pooled
    # MMLU numbers. This is a hard validity gate -- if it fails, the by-subject split is not to be trusted.
    pooled = gl.to_report(gl.run_census([("ALL", a, b, c) for (_s, a, b, c) in rows]))["ALL"]
    repro_ok, repro_detail = pooled_reproduction_check(pooled, cases.EXPECTED_POOLED_MMLU)
    print("[pooled-repro] reproduces audit 52 pooled MMLU exactly : %s" % repro_ok)
    for k, d in repro_detail.items():
        if not d["match"]:
            print("[pooled-repro][MISMATCH] %s got=%s expected=%s" % (k, d["got"], d["expected"]))
    if not repro_ok:
        raise SystemExit("pooled reproduction gate failed -- aborting (by-subject numbers not trustworthy)")

    preds = cross_subject_predictions(report, cases.EXPECTED_TOTAL_VALID)

    # sanity: observed split sizes vs the documented ones
    counts_check = {"observed": split_counts, "expected": cases.EXPECTED_SPLIT_COUNTS,
                    "match": split_counts == cases.EXPECTED_SPLIT_COUNTS}

    # diagnostics (land in summary_tail): pooled headline + the three subjects with the largest char pick-longest
    # lift and the three with the smallest (most negative) lift.
    def lift(s):
        return report[s]["char"]["longest_accuracy"] - report[s]["chance_accuracy"]
    subjects_by_lift = sorted(report, key=lift, reverse=True)
    top = subjects_by_lift[:3]
    bottom = subjects_by_lift[-3:]
    pc_ = pooled["char"]
    print("[pooled] n=%d chance=%.4f pick_longest=%.4f uniq_longest_rate=%.4f gold_len=%.3f distr_len=%.3f gap=%+.3f"
          % (pooled["n_valid"], pooled["chance_accuracy"], pc_["longest_accuracy"], pc_["unique_longest_rate"],
             pc_["mean_gold_len"], pc_["mean_distractor_len"], pc_["mean_gold_len"] - pc_["mean_distractor_len"]))
    print("[cross] n_subjects=%d  pick_longest>chance=%d  gold_mean_longer=%d  lift>=+0.05=%d"
          % (preds["n_subjects"], preds["P2_detail"]["n_subjects_pick_longest_beats_chance"],
             preds["P3_detail"]["n_subjects_gold_mean_longer"], preds["P4_detail"]["n_subjects_lift_ge_0.05"]))
    for s in top + bottom:
        c = report[s]["char"]
        print("[subj] %-34s n=%4d pick_longest=%.4f lift=%+.4f uniq_long=%.4f gap=%+.3f"
              % (s, report[s]["n_valid"], c["longest_accuracy"], lift(s), c["unique_longest_rate"],
                 c["mean_gold_len"] - c["mean_distractor_len"]))
    print("[prediction] P1_clean_well_defined_and_complete_partition = %s"
          % ("HELD" if preds["P1_clean_well_defined_and_complete_partition"] else "FAILED"))
    print("[prediction] P2_length_shortcut_pervasive = %s  (%d/%d subjects)"
          % ("HELD" if preds["P2_length_shortcut_pervasive"] else "FAILED",
             preds["P2_detail"]["n_subjects_pick_longest_beats_chance"], preds["n_subjects"]))
    print("[prediction] P3_gold_longer_than_distractors_pervasive = %s  (%d/%d subjects)"
          % ("HELD" if preds["P3_gold_longer_than_distractors_pervasive"] else "FAILED",
             preds["P3_detail"]["n_subjects_gold_mean_longer"], preds["n_subjects"]))
    print("[prediction] P4_lift_is_diffuse_not_concentrated = %s  (%d/%d subjects with lift>=+0.05)"
          % ("HELD" if preds["P4_lift_is_diffuse_not_concentrated"] else "FAILED",
             preds["P4_detail"]["n_subjects_lift_ge_0.05"], preds["n_subjects"]))

    out = {
        "dataset": ("MMLU (cais/mmlu config 'all', test+validation+dev; auxiliary_train excluded as a mix of "
                    "other datasets), read from the HuggingFace auto-converted parquet via the datasets-server "
                    "parquet API. For each question this audit compares the length of the GOLD option with its "
                    "distractors -- by characters (after stripping) and by whitespace tokens -- keyed by MMLU "
                    "SUBJECT. Per subject it reports how often the gold is the unique longest / shortest option, "
                    "the accuracy of a tie-aware 'pick the longest' heuristic versus the random-choice baseline, "
                    "and the mean gold vs distractor length; it then summarises the cross-subject distribution "
                    "and reproduces audit 52's pooled MMLU numbers EXACTLY as a hard validity gate. This is a "
                    "construction property of the benchmark -- how long the correct answer was written -- not a "
                    "model's behaviour."),
        "rows_as_expected": counts_check["match"],
        "split_counts_check": counts_check,
        "synthetic_corpus": {"target_met": target_met, "n_fixture_rows": len(cases.FIXTURE_ROWS)},
        "pooled_reproduction_gate": {"passed": repro_ok, "detail": repro_detail},
        "pooled_mmlu_all": pooled,
        "by_subject": report,
        "predictions": preds,
        "note": ("P1 (structural, finding either way): every subject parses with 0 bad_key and 0 degenerate, is "
                 "modal 4-option with coverage >=95%, and the per-subject valid counts partition MMLU-all "
                 "exactly (sum == audit 52/53's 15,858). P2 (directional headline, finding either way): the char "
                 "'pick the longest' shortcut is pervasive -- in a strict majority of subjects the tie-aware "
                 "pick-longest accuracy beats that subject's chance baseline. P3 (directional, finding either "
                 "way): the mean length gap is near-universal in direction -- in a strict majority of subjects "
                 "the mean gold option is longer (chars) than the mean distractor. P4 (concentration, finding "
                 "either way): the pooled +3-point lift is diffuse, not concentrated -- fewer than a quarter of "
                 "subjects individually show a char pick-longest lift of at least +5 points. 'longest_accuracy' "
                 "is the expected accuracy of a heuristic that always picks the longest option and splits ties "
                 "uniformly. Lengths are characters after str.strip(); a token view is reported alongside. "
                 "Measures AGREEMENT with a length heuristic, not correctness of any model."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
