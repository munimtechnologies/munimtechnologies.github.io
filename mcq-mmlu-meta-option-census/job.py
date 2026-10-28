"""MMLU META-OPTION census (audit 56): do "all/none of the above"-type options explain MMLU's last-option tilt?

Audits 53/54 found MMLU's gold position is tilted toward the LAST option (pooled 26.7%, chi2 42.93 df 3; the tilt
is pervasive in direction but concentrated in 8 subjects). This audit tests one concrete construction mechanism:
options that refer to the other options -- "All of the above", "None of these", "Both A and B", Roman-numeral
statement sets -- are conventionally placed last and cannot be shuffled. It classifies every MMLU question into
one meta-option category (meta_option.py), measures where the meta option sits and how often it is the gold
against a uniform-placement baseline, and re-runs the gold-position census on the PLAIN remainder (no meta
option at all) to see whether the pooled last-tilt survives.

It reuses the exact-count gold-position census core (position_census.py) and its hand-traced fixture verbatim
from audits 53/54/55, adds a new hand-traced meta-option fixture, and reproduces audit 53's pooled MMLU-all as a
cross-check. Pre-registers five predictions, each a finding either way, decided before any real number was seen.

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
import cases

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"
N_EXAMPLES = 3


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


def read_mmlu(spec):
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
        counts[split] = counts.get(split, 0) + n  # accumulate in case a split spans multiple parquet shards
        for i in range(n):
            subject = data[spec["subject_col"]][i]
            choices = list(data[spec["choices_col"]][i])
            labels = [str(j) for j in range(len(choices))]
            key = str(data[spec["answer_col"]][i])
            rows.append((subject, labels, choices, key))
    return rows, counts


def _pos3(modal):
    """(count at position 3, n) of a 4-option modal summary, or (None, None) if it is not 4-option."""
    if not modal or len(modal["pos_counts"]) != 4:
        return None, None
    return modal["pos_counts"]["3"], modal["n"]


def predictions(cat_rep, split_rep, pooled_modal, meta_rep, total_valid):
    """Pre-registered real-data predictions, each a finding either way. Decided before any real number seen."""
    # P1 (structural): every category parses clean (0 bad_key, 0 degenerate), the category valid counts
    # partition MMLU-all exactly (sum == audit 53's 15,858), and the pooled re-key reproduces audit 53 (best
    # position is the LAST option and uniform is rejected at 0.001).
    clean = all(cat_rep[c]["n_bad_key"] == 0 and cat_rep[c]["n_degenerate"] == 0 for c in cat_rep)
    sum_valid = sum(cat_rep[c]["n_valid"] for c in cat_rep)
    partition_ok = (sum_valid == total_valid)
    pooled_repro = (pooled_modal["best_position"] == 3 and pooled_modal["uniform_rejected_0.001"] is True)
    p1 = clean and partition_ok and pooled_repro

    # P2 (placement): "all/none of the above" options sit at the LAST position in at least 90% of the questions
    # that carry one (aota + nota pooled).
    n_q = sum(meta_rep[c]["n_with_meta_option"] for c in ("aota", "nota") if c in meta_rep)
    n_last = sum(meta_rep[c]["n_meta_last"] for c in ("aota", "nota") if c in meta_rep)
    p2 = bool(n_q) and (n_last / n_q) >= 0.90

    # P3 (gold cue): when an "all of the above"-type option is present, it is the gold MORE often than a
    # uniformly placed gold would make it (meta_gold_rate > meta_gold_chance_rate).
    a = meta_rep.get("aota")
    p3 = bool(a and a["n_with_meta_option"]) and a["meta_gold_rate"] > a["meta_gold_chance_rate"]

    # P4 (HEADLINE, mechanism): the last-option tilt SURVIVES in the PLAIN remainder (questions with no meta
    # option of any kind) -- position 3 is still its most common gold position AND its rate exceeds 0.25.
    plain = split_rep.get("plain", {}).get("modal")
    p4 = bool(plain) and plain["best_position"] == 3 and plain["pos_rates"]["3"] > 0.25

    # P5 (strength): the PLAIN remainder still rejects a uniform gold position at alpha = 0.001.
    p5 = bool(plain) and plain["uniform_rejected_0.001"] is True

    return {
        "P1_clean_partition_and_pooled_reproduces_audit53": bool(p1),
        "P1_detail": {"clean": bool(clean), "sum_valid": sum_valid, "expected_total_valid": total_valid,
                      "partition_ok": bool(partition_ok), "pooled_best_position": pooled_modal["best_position"],
                      "pooled_uniform_rejected_0.001": pooled_modal["uniform_rejected_0.001"]},
        "P2_aota_nota_placed_last_ge_90pct": bool(p2),
        "P2_detail": {"n_questions": n_q, "n_meta_last": n_last, "rate": (n_last / n_q) if n_q else None,
                      "vacuous": not bool(n_q)},
        "P3_aota_is_gold_above_chance": bool(p3),
        "P3_detail": ({"n": a["n_with_meta_option"], "meta_gold_rate": a["meta_gold_rate"],
                       "chance_rate": a["meta_gold_chance_rate"]} if a else {"aota": "absent"}),
        "P4_last_tilt_survives_in_plain": bool(p4),
        "P5_plain_still_rejects_uniform_0.001": bool(p5),
        "P4_P5_detail": ({"n": plain["n"], "pos_rates": plain["pos_rates"], "best_position": plain["best_position"],
                          "chi_square_stat": plain["chi_square_stat"], "df": plain["df"],
                          "uniform_rejected_0.001": plain["uniform_rejected_0.001"]} if plain else {"plain": "absent"}),
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

    # 2) Real data: MMLU `all`, each question classified into one meta-option category.
    rows, split_counts = read_mmlu(cases.MMLU)
    print("[load] mmlu splits %s  total_rows=%d" % (split_counts, len(rows)))
    cats = [mo.classify_question(texts) for (_s, _l, texts, _k) in rows]

    cat_rep = pc.to_report(pc.run_census([(c, l, t, k) for c, (_s, l, t, k) in zip(cats, rows)]))
    split_rep = pc.to_report(pc.run_census([("plain" if c == "plain" else "any_meta", l, t, k)
                                            for c, (_s, l, t, k) in zip(cats, rows)]))
    pooled = pc.to_report(pc.run_census([("ALL", l, t, k) for (_s, l, t, k) in rows]))["ALL"]
    meta_rep = mo.meta_report(mo.run_meta_census(rows))
    preds = predictions(cat_rep, split_rep, pooled["modal"], meta_rep, cases.EXPECTED_TOTAL_VALID)

    # How much of the pooled position-3 excess (count above n/4) sits outside the plain remainder.
    c3_all, n_all = _pos3(pooled.get("modal"))
    c3_plain, n_plain = _pos3(split_rep.get("plain", {}).get("modal"))
    excess = None
    if c3_all is not None and c3_plain is not None:
        ex_all = c3_all - n_all / 4.0
        ex_plain = c3_plain - n_plain / 4.0
        excess = {"pooled_pos3_excess": ex_all, "plain_pos3_excess": ex_plain,
                  "share_of_excess_outside_plain": (1.0 - ex_plain / ex_all) if ex_all else None}

    # Per subject: category counts, and the position-3 rate over all questions vs over plain questions only.
    subj_cats = {}
    for c, (s, _l, _t, _k) in zip(cats, rows):
        d = subj_cats.setdefault(s, {})
        d[c] = d.get(c, 0) + 1
    subj_all = pc.to_report(pc.run_census(rows))
    subj_plain = pc.to_report(pc.run_census([r for c, r in zip(cats, rows) if c == "plain"]))
    by_subject = {}
    for s in sorted(subj_cats):
        a = subj_all.get(s, {}).get("modal")
        p = subj_plain.get(s, {}).get("modal")
        by_subject[s] = {
            "category_counts": subj_cats[s],
            "n_all": a["n"] if a else 0,
            "pos3_rate_all": a["pos_rates"].get("3") if a else None,
            "chi2_all": a["chi_square_stat"] if a else None,
            "n_plain": p["n"] if p else 0,
            "pos_rates_plain": p["pos_rates"] if p else None,
            "chi2_plain": p["chi_square_stat"] if p else None,
            "rejects_plain_0.001": p["uniform_rejected_0.001"] if p else None,
        }

    # A few verbatim examples per category so a reader can audit the classifier.
    examples = {}
    for c, (s, _l, t, k) in zip(cats, rows):
        lst = examples.setdefault(c, [])
        if len(lst) < N_EXAMPLES and c != "plain":
            lst.append({"subject": s, "choices": t, "answer_index": int(k)})

    counts_check = {"observed": split_counts, "expected": cases.EXPECTED_SPLIT_COUNTS,
                    "match": split_counts == cases.EXPECTED_SPLIT_COUNTS}

    pm = pooled["modal"]
    print("[pooled] n=%d pos_rates=%s best_pos=%d chi2=%.2f rej0.001=%s"
          % (pm["n"], {q: round(r, 4) for q, r in pm["pos_rates"].items()}, pm["best_position"],
             pm["chi_square_stat"], pm["uniform_rejected_0.001"]))
    for c in mo.CATEGORIES:
        if c in cat_rep and cat_rep[c].get("modal"):
            m = cat_rep[c]["modal"]
            print("[cat] %-9s n=%5d gold_pos_rates=%s chi2=%.1f" % (c, cat_rep[c]["n_valid"],
                  {q: round(r, 3) for q, r in m["pos_rates"].items()}, m["chi_square_stat"]))
        if c in meta_rep:
            r = meta_rep[c]
            print("[meta] %-9s first_pos=%s last_rate=%s gold_rate=%s chance=%s incl=%s/%s"
                  % (c, r["meta_first_pos_counts"], r["meta_last_rate"], r["meta_gold_rate"],
                     r["meta_gold_chance_rate"], r["n_gold_inclusive"], r["n_inclusive_unique"]))
    for key in ("plain", "any_meta"):
        m = split_rep.get(key, {}).get("modal")
        if m:
            print("[split] %-8s n=%5d rates=%s best=%d chi2=%.2f rej=%s"
                  % (key, m["n"], {q: round(r, 4) for q, r in m["pos_rates"].items()}, m["best_position"],
                     m["chi_square_stat"], m["uniform_rejected_0.001"]))
    print("[excess] %s" % excess)
    for s in cases.AUDIT54_SIGNIFICANT:
        if s in by_subject:
            b = by_subject[s]
            print("[subj] %-36s cats=%s pos3_all=%s pos_plain=%s chi2_plain=%s"
                  % (s, b["category_counts"], b["pos3_rate_all"],
                     {q: round(r, 3) for q, r in b["pos_rates_plain"].items()} if b["pos_rates_plain"] else None,
                     b["chi2_plain"]))
    for name in ("P1_clean_partition_and_pooled_reproduces_audit53", "P2_aota_nota_placed_last_ge_90pct",
                 "P3_aota_is_gold_above_chance", "P4_last_tilt_survives_in_plain",
                 "P5_plain_still_rejects_uniform_0.001"):
        print("[prediction] %s = %s" % (name, "HELD" if preds[name] else "FAILED"))
    print("[prediction-detail] %s" % {k: v for k, v in preds.items() if k.endswith("_detail")})

    out = {
        "dataset": ("MMLU (cais/mmlu config 'all', test+validation+dev; auxiliary_train excluded), read from the "
                    "HuggingFace auto-converted parquet via the datasets-server parquet API. Every question is "
                    "classified into ONE meta-option category (roman > aota > nota > letterref > plain; see "
                    "meta_option.py). Per category it reports the gold-position distribution (chi-square vs "
                    "uniform), where the meta option sits, and how often it is the gold against a uniform-"
                    "placement baseline; it then re-runs the gold-position census on the PLAIN remainder and per "
                    "subject. This is a construction property of the benchmark, not a model's behaviour."),
        "rows_as_expected": counts_check["match"],
        "split_counts_check": counts_check,
        "synthetic_corpus": {"position_target_met": pos_ok, "meta_target_met": meta_ok,
                             "n_position_fixture_rows": len(cases.FIXTURE_ROWS),
                             "n_meta_fixture_rows": len(cases.META_FIXTURE_ROWS)},
        "alpha": pc.ALPHA,
        "max_meta_tokens": mo.MAX_META_TOKENS,
        "pooled_mmlu_all": pooled,
        "by_category_gold_position": cat_rep,
        "plain_vs_any_meta_gold_position": split_rep,
        "meta_option_placement_and_gold": meta_rep,
        "pos3_excess_decomposition": excess,
        "by_subject": by_subject,
        "examples": examples,
        "predictions": preds,
        "note": ("P1 (structural): clean parse, the categories partition MMLU-all exactly (15,858), and the pooled "
                 "re-key reproduces audit 53 (last option modal, uniform rejected). P2 (placement): all/none-of-"
                 "the-above options sit last in >=90% of the questions carrying one. P3 (gold cue): an all-of-the-"
                 "above-type option is the gold more often than uniform placement would make it. P4 (headline, "
                 "mechanism): the last-option tilt survives in the plain remainder (position 3 modal and > 0.25). "
                 "P5 (strength): the plain remainder still rejects uniform at alpha=0.001. Each is a finding "
                 "either way. The classifier is regex-based and conservative; its examples are listed so a "
                 "reader can audit it. Measures construction, not any model."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
