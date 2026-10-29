"""MMLU-Pro META-OPTION + POSITION census (audit 59): did the 4->10 option expansion remove MMLU's artifacts?

Audit 56 found two construction artifacts in 4-option MMLU: the gold leans toward the LAST option (pooled 26.7%),
and "all/none of the above"-type options sit last in >=90% of the questions carrying one and are the gold above
chance. MMLU-Pro (Wang et al., 2024) rebuilt the same material with up to TEN options -- mostly GPT-4-generated
distractors, then human-curated -- as a harder, hoped-to-be-more-robust benchmark. This audit applies the SAME
instrument (position_census.py and meta_option.py, verbatim; only the chi-square table is extended to df 12 for
10-option questions) to MMLU-Pro and asks whether those artifacts survived.

It records, per MMLU-Pro CATEGORY and pooled, where the gold sits among up to ten positions (chi-square vs
uniform); runs the meta-option census (where "all/none of the above"-type cues sit and how often they are gold);
measures the k-independent rate at which the gold is the FIRST or LAST option against a uniform baseline; and
slices by provenance (`src`) to confirm even inherited 4-option MMLU questions were expanded. Five predictions
are pre-registered, each a finding either way, against two hand-traced fixtures checked before any real data.

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


def read_dataset(spec):
    """Read MMLU-Pro, returning (rows, split_counts). Each row is (category, labels, texts, gold_index_str, src)."""
    rows = []
    counts = {}
    cols = [spec["subject_col"], spec["choices_col"], spec["answer_col"], spec["src_col"]]
    for split, url in parquet_files(spec["hf"], spec["config"], set(spec["splits"])):
        table = pq.read_table(io.BytesIO(_get(url)), columns=cols)
        for c in cols:
            if c not in table.column_names:
                raise RuntimeError("MMLU-Pro parquet is missing column %r: %s" % (c, table.column_names))
        data = {c: table.column(c).to_pylist() for c in cols}
        n = len(data[cols[0]])
        counts[split] = counts.get(split, 0) + n  # accumulate in case a split spans multiple parquet shards
        for i in range(n):
            category = data[spec["subject_col"]][i]
            choices = list(data[spec["choices_col"]][i])
            labels = [str(j) for j in range(len(choices))]
            key = str(data[spec["answer_col"]][i])
            src = data[spec["src_col"]][i]
            rows.append((category, labels, choices, key, src))
    return rows, counts


def k_independent_position(rows):
    """FIRST/LAST gold rates across ALL valid questions regardless of option count k, vs a uniform baseline.

    rows: iterable of 5-tuples (category, labels, texts, answer_key, src). For each valid question the chance of
    the gold being last (or first) under uniform placement is 1/k, so the expected rate is the mean of 1/k.
    """
    n = n_last = n_first = 0
    exp_last = 0.0
    for (_cat, labels, texts, key, _src) in rows:
        if pc.question_validity(labels, texts, key) != "valid":
            continue
        k = len(labels)
        gold = labels.index(key)
        n += 1
        exp_last += 1.0 / k
        if gold == k - 1:
            n_last += 1
        if gold == 0:
            n_first += 1
    return {
        "n": n,
        "n_gold_last": n_last,
        "gold_last_rate": (n_last / n) if n else None,
        "n_gold_first": n_first,
        "gold_first_rate": (n_first / n) if n else None,
        "expected_last_or_first_rate_uniform": (exp_last / n) if n else None,
    }


def predictions(pooled, meta_rep, srcgroup_rep, total_valid):
    """Pre-registered real-data predictions, each a finding either way. Decided before any real number seen."""
    modal = pooled.get("modal") or {}
    modal_k = pooled.get("modal_option_count")

    # P1 (structural): clean parse (0 bad_key, 0 degenerate), the modal option count is 10, and more than one
    # option count occurs (MMLU-Pro's documented variable-length option lists are present).
    clean = (pooled["n_bad_key"] == 0 and pooled["n_degenerate"] == 0)
    hist = pooled["option_count_hist"]
    p1 = clean and (modal_k == 10) and (len(hist) > 1)

    # P2 (HEADLINE "all of the above"): meta-option questions (aota + nota + letterref + roman) are RARE in
    # MMLU-Pro -- their combined share of valid questions is < 2%. The GPT-4 10-option expansion did not carry
    # over MMLU's "all/none of the above"-style cues. Finding either way.
    meta_n = sum(meta_rep[c]["n"] for c in ("aota", "nota", "letterref", "roman") if c in meta_rep)
    meta_share = (meta_n / total_valid) if total_valid else None
    p2 = meta_share is not None and meta_share < 0.02

    # P3 (HEADLINE position): among the modal (10-option) questions the gold position is NOT uniform -- it rejects
    # a uniform placement at alpha = 0.001 (df 9, critical 27.877). I.e. MMLU-Pro is not positionally balanced
    # despite its redesign. Finding either way.
    p3 = bool(modal) and modal.get("uniform_rejected_0.001") is True

    # P4 (direction): the modal gold position among 10-option questions is NOT the last (index 9) -- MMLU's
    # "the answer tends to be last" tilt does NOT transfer to MMLU-Pro. Finding either way.
    p4 = bool(modal) and modal_k is not None and modal.get("best_position") != (modal_k - 1)

    # P5 (expansion check): among questions inherited from the original 4-option MMLU (src starts "ori_mmlu"),
    # the modal option count is 10 -- confirming even inherited questions were expanded well past four options.
    ori = srcgroup_rep.get("ori_mmlu") or {}
    p5 = ori.get("modal_option_count") == 10

    return {
        "P1_clean_modal10_variable_k": bool(p1),
        "P1_detail": {"clean": bool(clean), "n_bad_key": pooled["n_bad_key"], "n_degenerate": pooled["n_degenerate"],
                      "modal_option_count": modal_k, "n_distinct_option_counts": len(hist),
                      "option_count_hist": hist},
        "P2_meta_options_rare_under_2pct": bool(p2),
        "P2_detail": {"n_meta_questions": meta_n, "total_valid": total_valid, "meta_share": meta_share,
                      "by_category": {c: meta_rep[c]["n"] for c in ("aota", "nota", "letterref", "roman")
                                      if c in meta_rep}},
        "P3_10opt_position_rejects_uniform_0.001": bool(p3),
        "P3_detail": ({"n": modal["n"], "chi_square_stat": modal["chi_square_stat"], "df": modal["df"],
                       "critical_0.001": modal["chi_square_critical_0.001"],
                       "uniform_rejected_0.001": modal["uniform_rejected_0.001"]} if modal else {"modal": "absent"}),
        "P4_last_is_not_modal_gold_position": bool(p4),
        "P4_detail": ({"modal_option_count": modal_k, "best_position": modal["best_position"],
                       "last_position": (modal_k - 1) if modal_k is not None else None,
                       "pos_rates": modal["pos_rates"], "best_position_accuracy": modal["best_position_accuracy"],
                       "chance_accuracy": modal["chance_accuracy"]} if modal else {"modal": "absent"}),
        "P5_inherited_mmlu_expanded_to_10": bool(p5),
        "P5_detail": {"n_valid": ori.get("n_valid"), "modal_option_count": ori.get("modal_option_count"),
                      "option_count_hist": ori.get("option_count_hist")},
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

    # 2) Real data: MMLU-Pro test split, each question classified into one meta-option category.
    rows, split_counts = read_dataset(cases.MMLU_PRO)
    print("[load] mmlu-pro splits %s  total_rows=%d" % (split_counts, len(rows)))
    cats = [mo.classify_question(texts) for (_c, _l, texts, _k, _s) in rows]

    # Pooled gold position (summarised at the modal option count, k=10) -- the position headline.
    pooled = pc.to_report(pc.run_census([("ALL", l, t, k) for (_c, l, t, k, _s) in rows]))["ALL"]
    # Gold position per MMLU-Pro category.
    by_category = pc.to_report(pc.run_census([(c, l, t, k) for (c, l, t, k, _s) in rows]))
    # Gold position split into plain (no meta option) vs any_meta.
    split_rep = pc.to_report(pc.run_census([("plain" if mc == "plain" else "any_meta", l, t, k)
                                            for mc, (_c, l, t, k, _s) in zip(cats, rows)]))
    # Gold position by provenance group (inherited original MMLU vs everything else).
    srcgroup_rep = pc.to_report(pc.run_census(
        [("ori_mmlu" if str(s).startswith(cases.ORI_MMLU_PREFIX) else "other", l, t, k)
         for (_c, l, t, k, s) in rows]))
    # Meta-option placement + gold census (key ignored by run_meta_census).
    meta_rep = mo.meta_report(mo.run_meta_census([(c, l, t, k) for (c, l, t, k, _s) in rows]))
    # k-independent first/last gold rates vs uniform.
    kindep = k_independent_position(rows)

    total_valid = pooled["n_valid"]
    preds = predictions(pooled, meta_rep, srcgroup_rep, total_valid)

    counts_check = {"observed": split_counts, "expected_documented": cases.EXPECTED_SPLIT_COUNTS,
                    "match": split_counts == cases.EXPECTED_SPLIT_COUNTS}

    # A few verbatim examples per meta category so a reader can audit the classifier on MMLU-Pro.
    examples = {}
    for mc, (_c, _l, t, k, s) in zip(cats, rows):
        if mc == "plain":
            continue
        lst = examples.setdefault(mc, [])
        if len(lst) < N_EXAMPLES:
            lst.append({"src": s, "choices": t, "answer_index": int(k)})

    # ----- console summary -----
    pm = pooled.get("modal") or {}
    print("[pooled] n=%d modal_k=%s pos_rates=%s best_pos=%s chi2=%.2f df=%s rej0.001=%s"
          % (pooled["n_valid"], pooled["modal_option_count"],
             {q: round(r, 4) for q, r in pm.get("pos_rates", {}).items()}, pm.get("best_position"),
             pm.get("chi_square_stat", float("nan")), pm.get("df"), pm.get("uniform_rejected_0.001")))
    print("[option_count_hist] %s" % pooled["option_count_hist"])
    print("[kindep] gold_first=%s gold_last=%s expected(uniform)=%s"
          % (kindep["gold_first_rate"], kindep["gold_last_rate"], kindep["expected_last_or_first_rate_uniform"]))
    for c in mo.CATEGORIES:
        if c in meta_rep:
            r = meta_rep[c]
            print("[meta] %-9s n=%5d with_meta=%s first_pos=%s last_rate=%s gold_rate=%s chance=%s"
                  % (c, r["n"], r["n_with_meta_option"], r["meta_first_pos_counts"], r["meta_last_rate"],
                     r["meta_gold_rate"], r["meta_gold_chance_rate"]))
    for key in ("plain", "any_meta"):
        m = split_rep.get(key, {}).get("modal")
        if m:
            print("[split] %-8s n=%5d best=%d chi2=%.2f df=%d rej=%s"
                  % (key, m["n"], m["best_position"], m["chi_square_stat"], m["df"], m["uniform_rejected_0.001"]))
    for key in ("ori_mmlu", "other"):
        g = srcgroup_rep.get(key)
        if g:
            print("[src] %-9s n_valid=%d modal_k=%s hist=%s" % (key, g["n_valid"], g["modal_option_count"],
                                                                g["option_count_hist"]))
    for name in ("P1_clean_modal10_variable_k", "P2_meta_options_rare_under_2pct",
                 "P3_10opt_position_rejects_uniform_0.001", "P4_last_is_not_modal_gold_position",
                 "P5_inherited_mmlu_expanded_to_10"):
        print("[prediction] %s = %s" % (name, "HELD" if preds[name] else "FAILED"))

    out = {
        "dataset": ("MMLU-Pro (TIGER-Lab/MMLU-Pro config 'default', test split), read from the HuggingFace "
                    "auto-converted parquet via the datasets-server parquet API. For each question this audit "
                    "records the 0-based INDEX of the gold option (answer_index) within the released option list "
                    "(options), and classifies the question into ONE meta-option category (roman > aota > nota > "
                    "letterref > plain; meta_option.py, applied verbatim from audit 56). It reports the gold-"
                    "position distribution pooled and per MMLU-Pro category (chi-square vs uniform, summarised at "
                    "the modal option count k=10, df 9); where meta options sit and how often they are the gold "
                    "vs a uniform-placement baseline; the k-independent first/last gold rates; and a split by "
                    "provenance (src). This is a construction property of the benchmark -- where the correct "
                    "answer was placed -- not any model's position / selection behaviour. The letterref predicate "
                    "recognises only references to option letters A-D, so for MMLU-Pro's A-J lists it is a "
                    "conservative lower bound (documented, not silently changed, to keep the instrument identical "
                    "to audit 56)."),
        "rows_as_expected": counts_check["match"],
        "split_counts_check": counts_check,
        "synthetic_corpus": {"position_target_met": pos_ok, "meta_target_met": meta_ok,
                             "n_position_fixture_rows": len(cases.FIXTURE_ROWS),
                             "n_meta_fixture_rows": len(cases.META_FIXTURE_ROWS)},
        "alpha": pc.ALPHA,
        "max_meta_tokens": mo.MAX_META_TOKENS,
        "pooled_gold_position": pooled,
        "by_category_gold_position": by_category,
        "plain_vs_any_meta_gold_position": split_rep,
        "by_provenance_gold_position": srcgroup_rep,
        "meta_option_placement_and_gold": meta_rep,
        "k_independent_first_last": kindep,
        "examples": examples,
        "predictions": preds,
        "note": ("P1 (structural): clean parse, modal option count 10, variable option counts present. P2 "
                 "(headline): 'all/none of the above'-type meta options are rare in MMLU-Pro (<2% of valid "
                 "questions). P3 (headline): among 10-option questions the gold position rejects uniform at "
                 "alpha=0.001 (df 9). P4 (direction): the last option (index 9) is NOT the modal gold position, so "
                 "MMLU's last-tilt does not transfer. P5 (expansion): questions inherited from 4-option MMLU "
                 "(src 'ori_mmlu*') were expanded to a modal 10 options. Each is a finding either way, decided "
                 "before any real number was seen. Measures construction, not any model."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
