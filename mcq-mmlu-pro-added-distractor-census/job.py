"""MMLU-Pro ADDED-vs-ORIGINAL distractor length census (audit 62).

Audit 61 found that MMLU-Pro's 10-option expansion more than doubled MMLU's pick-longest answer-length shortcut
(pooled lift +7.29 points vs MMLU's +3.05; biology 44.6% vs 11% chance). This audit locates the mechanism. It joins
every MMLU-Pro question inherited from MMLU (`src` "ori_mmlu-*") back to MMLU `all` by whitespace-normalised
question text, requires the gold text to be unchanged, labels each MMLU-Pro distractor ORIGINAL (one of MMLU's
three) or ADDED (introduced by the expansion), and compares the gold's length with each kind: mean lengths, a
pairwise gold-is-longer rate, and on intact questions pick-longest on the full list vs on the original 4 options.
It also re-runs the audit-51 length census keyed by provenance (ori_mmlu vs other).

Gates before any prediction is scored: both hand-traced fixtures must match exactly, and the pooled census must
reproduce audit 61 (n 12,032, unique-longest 1,655, pick-longest 0.18376805...) and audit 59's provenance counts
(ori_mmlu 6,810 / other 5,222). Six predictions were pre-registered before any real number was seen.

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
import provenance as pv

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


def structural_gate(pooled, by_prov):
    """Pooled census must reproduce audit 61; provenance split must reproduce audit 59. Returns (ok, detail)."""
    detail = {
        "n_valid": {"got": pooled["n_valid"], "expected": cases.EXPECTED_N_VALID,
                    "match": pooled["n_valid"] == cases.EXPECTED_N_VALID},
        "pooled_unique_longest": {"got": pooled["char"]["unique_longest_count"],
                                  "expected": cases.EXPECTED_POOLED_UNIQUE_LONGEST,
                                  "match": pooled["char"]["unique_longest_count"]
                                  == cases.EXPECTED_POOLED_UNIQUE_LONGEST},
        "pooled_longest_accuracy": {"got": pooled["char"]["longest_accuracy"],
                                    "expected": cases.EXPECTED_POOLED_LONGEST_ACCURACY,
                                    "match": abs(pooled["char"]["longest_accuracy"]
                                                 - cases.EXPECTED_POOLED_LONGEST_ACCURACY) < 1e-12},
        "provenance_counts": {"got": {k: by_prov[k]["n_valid"] for k in sorted(by_prov)},
                              "expected": cases.EXPECTED_PROVENANCE_COUNTS,
                              "match": {k: by_prov[k]["n_valid"] for k in by_prov}
                              == cases.EXPECTED_PROVENANCE_COUNTS},
        "clean_parse": {"got": [pooled["n_bad_key"], pooled["n_degenerate"]], "expected": [0, 0],
                        "match": pooled["n_bad_key"] == 0 and pooled["n_degenerate"] == 0},
    }
    return all(d["match"] for d in detail.values()), detail


def predictions(status_counts, join_rep, by_prov):
    """Pre-registered predictions, each a finding either way. Decided before any real number was seen."""
    n_ori = sum(status_counts.values())
    coverage = status_counts["matched"] / n_ori if n_ori else 0.0
    allr = join_rep.get("ALL")

    def gap(rep):
        if not rep or rep["gold_longer_vs_added"] is None or rep["gold_longer_vs_original"] is None:
            return None
        return rep["gold_longer_vs_added"] - rep["gold_longer_vs_original"]

    # P1 (join coverage): at least 90% of ori_mmlu MMLU-Pro questions join to MMLU with an unchanged gold text.
    p1 = coverage >= 0.90

    # P2 (HEADLINE): the distractors ADDED by the expansion are shorter on average than MMLU's ORIGINAL ones.
    p2 = bool(allr and allr["mean_added_len"] is not None and allr["mean_original_len"] is not None
              and allr["mean_added_len"] < allr["mean_original_len"])

    # P3 (mechanism): the gold is longer than an ADDED distractor more often than an ORIGINAL one (pairwise).
    g_all = gap(allr)
    p3 = g_all is not None and g_all > 0

    # P4 (amplification): on intact questions, pick-longest relative to chance is higher on the full MMLU-Pro list
    # than on the original 4-option subset.
    ratio_full = ratio_orig = None
    if allr and allr["n_intact"]:
        ratio_full = allr["intact_pick_longest_full"] / allr["intact_chance_full"]
        ratio_orig = allr["intact_pick_longest_original4"] / allr["intact_chance_original4"]
    p4 = ratio_full is not None and ratio_full > ratio_orig

    # P5 (localisation): in each of audit 61's two highest-lift categories, the pairwise gap is at least 0.10.
    focus = {c: gap(join_rep.get(c)) for c in cases.FOCUS_CATEGORIES}
    p5 = all(v is not None and v >= 0.10 for v in focus.values())

    # P6 (provenance): the pick-longest lift over chance is larger on ori_mmlu questions than on the rest.
    def lift(rep):
        return rep["char"]["longest_accuracy"] - rep["chance_accuracy"]
    lift_ori = lift(by_prov["ori_mmlu"])
    lift_other = lift(by_prov["other"])
    p6 = lift_ori > lift_other

    return {
        "P1_join_coverage_at_least_90pct": bool(p1),
        "P1_detail": {"status_counts": status_counts, "coverage": coverage},
        "P2_added_distractors_shorter_than_original": bool(p2),
        "P2_detail": {"mean_added_len": allr and allr["mean_added_len"],
                      "mean_original_len": allr and allr["mean_original_len"],
                      "mean_gold_len": allr and allr["mean_gold_len"]},
        "P3_gold_longer_vs_added_exceeds_vs_original": bool(p3),
        "P3_detail": {"gold_longer_vs_added": allr and allr["gold_longer_vs_added"],
                      "gold_longer_vs_original": allr and allr["gold_longer_vs_original"], "gap": g_all},
        "P4_expansion_amplifies_pick_longest_on_intact": bool(p4),
        "P4_detail": {"n_intact": allr and allr["n_intact"], "full_over_chance": ratio_full,
                      "original4_over_chance": ratio_orig},
        "P5_gap_at_least_0p10_in_biology_and_psychology": bool(p5),
        "P5_detail": focus,
        "P6_ori_mmlu_lift_exceeds_other": bool(p6),
        "P6_detail": {"lift_ori_mmlu": lift_ori, "lift_other": lift_other},
    }


def examples(pro_rows, index, category, k=3):
    """First k matched questions of a category, with option lengths, for the write-up."""
    out = []
    for r in pro_rows:
        if r["category"] != category or pv.provenance(r["src"]) != "ori_mmlu":
            continue
        st, split = pv.match_question(r["question"], r["options"], r["answer_index"], index)
        if st != "matched":
            continue
        gold, original, added = split
        out.append({
            "question_id": r["question_id"],
            "src": r["src"],
            "gold": [gold, gl.char_len(gold)],
            "original": [[t, gl.char_len(t)] for t in original],
            "added": [[t, gl.char_len(t)] for t in added],
        })
        if len(out) >= k:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Both hand-traced fixtures must match exactly before any real data is read.
    core_ok = gl.run_census(cases.FIXTURE_ROWS) == cases.TARGET
    fx_index = pv.build_index(cases.JOIN_MMLU_ROWS)
    fx_status, fx_accs = pv.run_join(cases.JOIN_PRO_ROWS, fx_index)
    join_ok = fx_status == cases.JOIN_STATUS_TARGET and fx_accs == cases.JOIN_TARGET
    print("[fixture] core == TARGET : %s ; join == JOIN_TARGET : %s" % (core_ok, join_ok))
    if not (core_ok and join_ok):
        raise SystemExit("fixture mismatch -- aborting before real data")

    # 2) Real data.
    pro_rows, pro_counts = read_columns(cases.MMLU_PRO)
    mmlu_rows, mmlu_counts = read_columns(cases.MMLU)
    print("[load] mmlu-pro %s ; mmlu %s" % (pro_counts, mmlu_counts))

    # 3) Length census keyed by provenance and pooled; structural gate vs audits 59/61.
    census_rows = []
    for r in pro_rows:
        opts = list(r["options"])
        census_rows.append((pv.provenance(r["src"]), [str(j) for j in range(len(opts))], opts,
                            str(r["answer_index"])))
    by_prov = gl.to_report(gl.run_census(census_rows))
    pooled = gl.to_report(gl.run_census([("ALL", a, b, c) for (_k, a, b, c) in census_rows]))["ALL"]
    gate_ok, gate_detail = structural_gate(pooled, by_prov)
    print("[structural-gate] reproduces audits 59/61 : %s" % gate_ok)
    for k, d in gate_detail.items():
        if not d["match"]:
            print("[structural-gate][MISMATCH] %s got=%s expected=%s" % (k, d["got"], d["expected"]))
    if not gate_ok:
        raise SystemExit("structural gate failed -- aborting")

    # 4) Join ori_mmlu questions to MMLU and split distractors by origin.
    index = pv.build_index((m["subject"], m["question"], m["choices"], m["answer"]) for m in mmlu_rows)
    join_input = [(r["category"], r["src"], r["question"], r["options"], r["answer_index"]) for r in pro_rows]
    status_counts, accs = pv.run_join(join_input, index)
    if status_counts["matched"] == 0:
        raise SystemExit("join matched 0 questions -- aborting")
    join_rep = {k: pv.summarize(v) for k, v in accs.items()}

    preds = predictions(status_counts, join_rep, by_prov)

    allr = join_rep["ALL"]
    print("[join] %s" % status_counts)
    print("[join-ALL] n=%d gold=%.2f original=%.2f (n=%d) added=%.2f (n=%d) gold>orig=%.4f gold>added=%.4f"
          % (allr["n_questions"], allr["mean_gold_len"], allr["mean_original_len"] or 0.0,
             allr["n_original_distractors"], allr["mean_added_len"] or 0.0, allr["n_added_distractors"],
             allr["gold_longer_vs_original"] or 0.0, allr["gold_longer_vs_added"] or 0.0))
    print("[intact] n=%d full=%.4f (chance %.4f) original4=%.4f (chance 0.25)"
          % (allr["n_intact"], allr["intact_pick_longest_full"] or 0.0, allr["intact_chance_full"] or 0.0,
             allr["intact_pick_longest_original4"] or 0.0))
    for c in sorted(join_rep):
        if c == "ALL":
            continue
        e = join_rep[c]
        print("[cat] %-17s n=%4d gold=%6.2f orig=%6.2f added=%6.2f gold>orig=%.3f gold>added=%.3f"
              % (c, e["n_questions"], e["mean_gold_len"], e["mean_original_len"] or 0.0,
                 e["mean_added_len"] or 0.0, e["gold_longer_vs_original"] or 0.0,
                 e["gold_longer_vs_added"] or 0.0))
    for p in ("ori_mmlu", "other"):
        e = by_prov[p]
        print("[prov] %-8s n=%5d chance=%.4f pick_longest=%.4f lift=%+.4f"
              % (p, e["n_valid"], e["chance_accuracy"], e["char"]["longest_accuracy"],
                 e["char"]["longest_accuracy"] - e["chance_accuracy"]))
    for name in ("P1_join_coverage_at_least_90pct", "P2_added_distractors_shorter_than_original",
                 "P3_gold_longer_vs_added_exceeds_vs_original", "P4_expansion_amplifies_pick_longest_on_intact",
                 "P5_gap_at_least_0p10_in_biology_and_psychology", "P6_ori_mmlu_lift_exceeds_other"):
        print("[prediction] %s = %s" % (name, "HELD" if preds[name] else "FAILED"))

    out = {
        "dataset": ("MMLU-Pro (TIGER-Lab/MMLU-Pro config 'default', test split) joined to MMLU (cais/mmlu config "
                    "'all', test+validation+dev), both read from the HuggingFace auto-converted parquet via the "
                    "datasets-server parquet API. Each MMLU-Pro question whose src starts with 'ori_mmlu' is "
                    "matched to MMLU by whitespace-normalised question text with an unchanged gold text; each "
                    "MMLU-Pro distractor is labelled ORIGINAL (its normalised text is one of MMLU's three "
                    "distractors) or ADDED (anything else). Lengths are characters after str.strip(). This is a "
                    "construction property of the benchmark, not a model's behaviour."),
        "split_counts": {"mmlu_pro": pro_counts, "mmlu": mmlu_counts},
        "fixtures": {"core_target_met": core_ok, "join_target_met": join_ok},
        "structural_gate": {"passed": gate_ok, "detail": gate_detail},
        "pooled_mmlu_pro": pooled,
        "by_provenance": by_prov,
        "join_status": status_counts,
        "join_by_category": join_rep,
        "examples": {c: examples(pro_rows, index, c) for c in cases.FOCUS_CATEGORIES},
        "predictions": preds,
        "note": ("P1: >=90% of ori_mmlu questions join with unchanged gold. P2 (headline): added distractors are "
                 "shorter on average than original ones. P3: the gold is longer than an added distractor more "
                 "often than an original one (pairwise; ties count 1/2). P4: on intact questions (all three "
                 "MMLU distractors kept) pick-longest relative to chance is higher on the full list than on the "
                 "original 4 options. P5: the P3 gap is at least 0.10 in both biology and psychology. P6: the "
                 "pick-longest lift over chance is larger on ori_mmlu questions than on the rest. Each is a finding "
                 "either way. Measures agreement with a length heuristic, not correctness of any model."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
