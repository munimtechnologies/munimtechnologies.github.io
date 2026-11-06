"""Does model consensus find GSM8K's flawed questions? (audit 86)

Joins Stanford CRFM's HELM Lite (release v1.13.0) per-question GSM8K outputs, about 90 models, to GSM8K's test set by
question text, labels every question with GSM8K-Platinum's cleaning status (consensus / verified / revised; GSM8K
questions Platinum dropped are 'rejected'), and scores audit 77's consensus flag (at least 6 of the 10 most accurate
models give the same non-key final number, more than give the key), the Platinum-style "any of the 10 is wrong"
filter, the 10-of-10 flag, the "no included model gives the key" flag, and disjoint weaker panels at an equal
review budget.

Gates before any prediction is scored: the hand-traced fixtures match; the Platinum join places all but at most 5
rows; HELM's questions join GSM8K and HELM's key equals GSM8K's '####' answer on at least 99%; each included model
answers at least 99% of the universe and our transcription of HELM's scorer equals HELM's recorded
final_number_exact_match on at least 99% of its predictions; at least 60 models are included.
Writes results.json and candidates.json (GSM8K test positions, labels, final numbers and vote counts only; no
question or model text). Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import hashlib
import io
import json
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import pyarrow.parquet as pq

import gsm86 as g
import cases86 as C

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"


def _get(url, tries=4):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry transient network errors
            last = e
    raise RuntimeError("GET failed after %d tries: %s (%s)" % (tries, url, last))


def _json(url):
    return json.loads(_get(url).decode("utf-8"))


def run_url(suite, run, fname):
    return "%s/runs/%s/%s/%s" % (C.HELM_BASE, suite, urllib.parse.quote(run, safe=":,=@-_."), fname)


def read_spec(spec):
    rows, shards = [], []
    listing = _json(PARQUET_API % spec["hf"])["parquet_files"]
    files = sorted(f["url"] for f in listing if f["config"] == spec["config"] and f["split"] == spec["split"])
    for url in files:
        raw = _get(url)
        shards.append({"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        t = pq.read_table(io.BytesIO(raw), columns=spec["cols"])
        data = {c: t.column(c).to_pylist() for c in spec["cols"]}
        for i in range(t.num_rows):
            rows.append(tuple(data[c][i] for c in spec["cols"]))
    return rows, shards


def fixture_ok():
    labels, ans, counts = g.platinum_labels(C.FIX_GSM_ROWS, C.FIX_PLAT_ROWS)
    view = g.panel_view(C.FIX_PANEL, C.FIX_ANSWERS, C.FIX_KEYS)
    cons, unan, anyw, score = g.flags_from_view(view, C.FIX_KEYS, 3, 2)
    nk = g.no_key_flags(view, 2)
    pos = [score[q] for q in score if C.FIX_LAB4[q] in g.ERR]
    neg = [score[q] for q in score if C.FIX_LAB4[q] in g.CLEAN]
    return {
        "scorer": (all(g.get_final_number(t) == w for t, w in C.FIX_FINAL)
                   and all(g.exact_match(a, b) == w for a, b, w in C.FIX_EM)
                   and all(g.final_number_exact_match(a, b) == w for a, b, w in C.FIX_FNEM)
                   and all(g.gsm_final(t) == w for t, w in C.FIX_GSM_FINAL)),
        "labels": labels == C.FIX_LABELS and ans == C.FIX_PLAT_ANSWER and counts == C.FIX_LABEL_COUNTS,
        "runs": g.select_runs(C.FIX_RUNS) == C.FIX_RUNS_TARGET,
        "flags": (view == C.FIX_VIEW and cons == C.FIX_CONS and unan == C.FIX_UNAN and anyw == C.FIX_ANYW
                  and score == C.FIX_SCORE and nk == C.FIX_NOKEY),
        "precision": (g.precision(cons, C.FIX_LAB4) == C.FIX_PREC["cons"]
                      and g.precision(anyw, C.FIX_LAB4) == C.FIX_PREC["anyw"]
                      and g.precision(nk, C.FIX_LAB4) == C.FIX_PREC["nokey"]
                      and g.precision(anyw, C.FIX_LAB4, kinds_all=g.REVIEWED) == C.FIX_PREC["anyw_reviewed"]
                      and g.recall(cons, C.FIX_LAB4) == C.FIX_RECALL["cons"]
                      and g.recall(nk, C.FIX_LAB4) == C.FIX_RECALL["nokey"]),
        "auc_budget": (g.auc(pos, neg) == C.FIX_AUC
                       and g.budget_precision(score, C.FIX_LAB4, C.FIX_BUDGET[0]) == C.FIX_BUDGET[1]
                       and g.ranked_models(C.FIX_ACC) == C.FIX_RANKED),
        "verdicts": all(g.predictions86(*a, C.THRESHOLDS) == w for a, w in C.FIX_V_CASES),
    }


def load_run(item, gsm_index):
    """One model's run -> (model, record). record: answers {gsm position: final number}, em {pos: 0/1}, keys {pos:
    HELM key}, and counts for the gates."""
    model, (run, suite) = item
    rec = {"run": run, "suite": suite}
    try:
        inst = _json(run_url(suite, run, "instances.json"))
        preds = _json(run_url(suite, run, "display_predictions.json"))
    except Exception as e:  # noqa: BLE001 - recorded, never patched
        rec["error"] = str(e)[:300]
        return model, rec
    id_map, keys, n_inst, joined = {}, {}, 0, 0
    for it in inst or []:
        if not isinstance(it, dict) or it.get("split") != "test":
            continue
        n_inst += 1
        refs = it.get("references") or []
        correct = [r for r in refs if "correct" in (r.get("tags") or [])]
        if len(correct) != 1:
            continue
        pos = gsm_index.get(g.norm_q((it.get("input") or {}).get("text")))
        if pos is None:
            continue
        joined += 1
        id_map[it.get("id")] = pos
        keys[pos] = g.get_final_number((correct[0].get("output") or {}).get("text"))
    answers, em = {}, {}
    c = {"n_pred": 0, "other_trial": 0, "unmapped": 0, "consistent": 0, "inconsistent": 0, "no_stat": 0}
    for p in preds or []:
        if not isinstance(p, dict):
            continue
        c["n_pred"] += 1
        if p.get("train_trial_index", 0) != 0:
            c["other_trial"] += 1
            continue
        pos = id_map.get(p.get("instance_id"))
        if pos is None or pos in answers:
            c["unmapped"] += 1
            continue
        a = g.get_final_number(p.get("predicted_text"))
        e = g.exact_match(keys[pos], a)
        answers[pos] = a
        em[pos] = e
        stat = (p.get("stats") or {}).get("final_number_exact_match")
        if stat is None:
            c["no_stat"] += 1
        elif int(round(float(stat))) == e:
            c["consistent"] += 1
        else:
            c["inconsistent"] += 1
    rec.update({"n_instances": n_inst, "joined": joined, "answers": answers, "em": em, "keys": keys, "counts": c})
    return model, rec


def share(a, n):
    return float(Fraction(a, n)) if n else None


def pr(t):
    return [t[0], t[1], share(t[0], t[1])]


def by_label(flags, labels):
    out = {}
    for q, f in flags.items():
        if f:
            lab = labels.get(q, "none")
            out[lab] = out.get(lab, 0) + 1
    return dict(sorted(out.items()))


def panel_stats(panel, answers, keys, labels, budget):
    view = g.panel_view(panel, answers, keys)
    cons, unan, anyw, score = g.flags_from_view(view, keys, len(panel), C.MIN_AGREE if len(panel) == C.PANEL_SIZE
                                                else C.TOP20_MIN_AGREE)
    err = [score[q] for q in keys if labels.get(q) in g.ERR]
    clean = [score[q] for q in keys if labels.get(q) in g.CLEAN]
    a = g.auc(err, clean)
    st = {"view": view, "cons": cons, "unan": unan, "anyw": anyw, "score": score, "auc": a}
    if budget is not None:
        st["budget"] = g.budget_precision(score, labels, budget)
    return st


def panel_json(st, labels, acc, panel):
    out = {"models": [{"model": m, "accuracy": share(*acc[m])} for m in panel],
           "mean_accuracy": sum(share(*acc[m]) for m in panel) / len(panel),
           "consensus": {"flags": sum(st["cons"].values()), "precision": pr(g.precision(st["cons"], labels)),
                         "precision_reviewed": pr(g.precision(st["cons"], labels, kinds_all=g.REVIEWED)),
                         "recall": pr(g.recall(st["cons"], labels)), "by_label": by_label(st["cons"], labels)},
           "unanimous": {"flags": sum(st["unan"].values()), "precision": pr(g.precision(st["unan"], labels)),
                         "recall": pr(g.recall(st["unan"], labels)), "by_label": by_label(st["unan"], labels)},
           "any_wrong": {"flags": sum(st["anyw"].values()), "precision": pr(g.precision(st["anyw"], labels)),
                         "precision_reviewed": pr(g.precision(st["anyw"], labels, kinds_all=g.REVIEWED)),
                         "recall": pr(g.recall(st["anyw"], labels)), "by_label": by_label(st["anyw"], labels)},
           "auc_error_vs_clean": None if st["auc"] is None else float(st["auc"])}
    if "budget" in st:
        e, j = st["budget"]
        out["budget"] = {"error_labelled": str(e), "labelled": str(j), "precision": float(e / j) if j else None}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    fx = fixture_ok()
    print("[fixture] %s" % fx)
    if not all(fx.values()):
        raise SystemExit("fixture mismatch -- aborting before real data")

    gsm_rows, gsm_shards = read_spec(C.GSM8K)
    plat_rows, plat_shards = read_spec(C.PLATINUM)
    labels, plat_answer, lcounts = g.platinum_labels([(q, a) for q, a in gsm_rows], plat_rows)
    print("[platinum] %s" % lcounts)
    if len(gsm_rows) != C.EXPECTED["gsm_rows"] or lcounts["unmatched"] + lcounts["to_duplicate"] > \
            C.ABORT_MAX_PLAT_UNMATCHED:
        raise SystemExit("GSM8K / Platinum join gate failed -- aborting")
    plat_ok = (lcounts["plat_rows"] == C.EXPECTED["plat_rows"] and lcounts["labels"] == C.EXPECTED["labels"])
    gsm_index, _dup = g.text_index([q for q, _a in gsm_rows])
    gsm_key = {i: g.gsm_final(a) for i, (_q, a) in enumerate(gsm_rows)}

    run_suites = _json("%s/releases/%s/runs_to_run_suites.json" % (C.HELM_BASE, C.HELM_RELEASE))
    chosen, dropped = g.select_runs(run_suites, C.HELM_PREFIX)
    print("[helm] runs=%d (dropped %d duplicate runs)" % (len(chosen), dropped))
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        loaded = dict(ex.map(lambda it: load_run(it, gsm_index), sorted(chosen.items())))

    # ----- Universe: GSM8K positions in at least half of the loaded runs -----
    seen = {}
    ok_runs = [m for m, r in loaded.items() if "error" not in r]
    for m in ok_runs:
        for pos in loaded[m]["keys"]:
            seen[pos] = seen.get(pos, 0) + 1
    universe = sorted(p for p, n in seen.items() if 2 * n >= len(ok_runs))
    helm_key, key_conflict = {}, 0
    for pos in universe:
        ks = {loaded[m]["keys"][pos] for m in ok_runs if pos in loaded[m]["keys"]}
        if len(ks) != 1:
            key_conflict += 1
            continue
        helm_key[pos] = ks.pop()
    agree = [p for p in helm_key if helm_key[p] == gsm_key[p]]
    key_agree = Fraction(len(agree), len(universe)) if universe else Fraction(0)
    keys = {p: helm_key[p] for p in sorted(agree) if labels.get(p) in g.ERR + g.CLEAN}
    ucounts = {"universe": len(universe), "key_conflict_across_runs": key_conflict, "key_agree": len(agree),
               "key_disagree": len(helm_key) - len(agree), "scored": len(keys),
               "labels": dict(sorted({lab: sum(1 for p in keys if labels[p] == lab)
                                      for lab in g.ERR + g.CLEAN}.items()))}
    print("[universe] %s key_agree=%.4f" % (ucounts, float(key_agree)))
    universe_ok = C.UNIVERSE_RANGE[0] <= len(universe) <= C.UNIVERSE_RANGE[1] and key_agree >= C.MIN_KEY_AGREE

    # ----- Model inclusion -----
    models_out, answers, acc = {}, {}, {}
    for m in sorted(loaded):
        r = loaded[m]
        if "error" in r:
            models_out[m] = {"run": r["run"], "suite": r["suite"], "status": "download_failed", "error": r["error"]}
            continue
        c = r["counts"]
        join = Fraction(r["joined"], r["n_instances"]) if r["n_instances"] else Fraction(0)
        cov = Fraction(sum(1 for p in keys if p in r["answers"]), len(keys)) if keys else Fraction(0)
        checked = c["consistent"] + c["inconsistent"]
        cons_share = Fraction(c["consistent"], checked) if checked else Fraction(0)
        ok = join >= C.MIN_INSTANCE_JOIN and cov >= C.MIN_COVERAGE and cons_share >= C.MIN_CONSISTENT
        correct = sum(r["em"][p] for p in keys if p in r["em"])
        n = sum(1 for p in keys if p in r["em"])
        models_out[m] = {"run": r["run"], "suite": r["suite"], "instances": r["n_instances"], "joined": r["joined"],
                         "coverage": float(cov), "scorer_consistent": float(cons_share), "counts": c,
                         "accuracy": share(correct, n), "status": "included" if ok else "excluded"}
        if ok:
            answers[m] = {p: a for p, a in r["answers"].items() if p in keys}
            acc[m] = (correct, n)
    del loaded
    print("[models] included=%d of %d" % (len(acc), len(models_out)))
    if not universe_ok or len(acc) < C.MIN_INCLUDED:
        with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
            json.dump({"audit": 86, "aborted": True, "fixture": fx, "platinum": lcounts, "universe": ucounts,
                       "key_agree": float(key_agree), "models": models_out}, fh, indent=1, ensure_ascii=True)
        raise SystemExit("universe or inclusion gate failed -- aborting (diagnostics in results.json)")

    ranked = g.ranked_models(acc)
    strata = [ranked[i * C.PANEL_SIZE:(i + 1) * C.PANEL_SIZE] for i in range(C.N_STRATA)]
    s1 = panel_stats(strata[0], answers, keys, labels, None)
    K = sum(s1["cons"].values())
    st = [panel_stats(p, answers, keys, labels, K) for p in strata]
    strata_out = []
    for i, p in enumerate(strata):
        row = {"stratum": "S%d" % (i + 1), "ranks": [i * C.PANEL_SIZE + 1, (i + 1) * C.PANEL_SIZE]}
        row.update(panel_json(st[i], labels, acc, p))
        strata_out.append(row)
        print("[stratum] %s" % {k: v for k, v in row.items() if k != "models"})
    st20 = panel_stats(ranked[:C.TOP20_SIZE], answers, keys, labels, K)
    top20_out = panel_json(st20, labels, acc, ranked[:C.TOP20_SIZE])
    print("[top20] %s" % {k: v for k, v in top20_out.items() if k != "models"})

    # ----- No-key flag over every included model -----
    view_all = g.panel_view(ranked, answers, keys)
    nk = g.no_key_flags(view_all, C.NK_MIN_COV)
    nk_prec = g.precision(nk, labels)
    nk_rec = g.recall(nk, labels)
    print("[no_key] flagged=%d precision=%s recall=%s" % (sum(nk.values()), nk_prec, nk_rec))

    s = st[0]
    cons_p = g.precision(s["cons"], labels)
    anyw_p = g.precision(s["anyw"], labels)
    rec = g.recall(s["cons"], labels)
    verdicts = g.predictions86(cons_p, anyw_p, s["auc"], rec, nk_prec, nk_prec[1], st[0]["budget"],
                               st[C.N_STRATA - 1]["budget"], C.THRESHOLDS)
    p1_parts = {"fixtures": all(fx.values()), "platinum_counts": plat_ok, "universe": universe_ok,
                "models": len(acc) >= C.MIN_INCLUDED}
    verdicts["P1_structural"] = all(p1_parts.values())
    print("[P1] %s" % p1_parts)
    for name in sorted(verdicts):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    numbers = {"P2_consensus_precision": pr(cons_p), "P3_any_wrong_precision": pr(anyw_p),
               "P4_auc": None if s["auc"] is None else float(s["auc"]), "P5_recall": pr(rec),
               "P6_no_key_precision": pr(nk_prec),
               "P7_budget_precision_S1_S5": [strata_out[0]["budget"]["precision"],
                                             strata_out[C.N_STRATA - 1]["budget"]["precision"]]}
    print("[numbers] %s" % numbers)

    # ----- Exploratory -----
    base = (sum(1 for p in keys if labels[p] in g.ERR), len(keys))
    key_share = {p: -Fraction(view_all[p][1], view_all[p][3]) if view_all[p][3] else Fraction(0) for p in keys}
    ks_auc = g.auc([key_share[p] for p in keys if labels[p] in g.ERR],
                   [key_share[p] for p in keys if labels[p] in g.CLEAN])
    ks_b = g.budget_precision(key_share, labels, K)
    revised = [p for p in keys if labels[p] == "revised"]
    rev_out = []
    for p in revised:
        counts = s["view"][p][0]
        ci, n = g.consensus(counts, keys[p])
        rev_out.append({"gsm_test_position": p, "s1_flag": bool(s["cons"][p]), "s1_top_non_key_votes": n,
                        "s1_top_non_key_equals_platinum": ci is not None and ci == plat_answer.get(p),
                        "s1_key_votes": s["view"][p][1]})
    print("[revised] %s" % rev_out)

    cands = []
    for p in keys:
        if not (s["cons"][p] or nk[p] or labels[p] in g.ERR):
            continue
        counts, kv, none, cov = s["view"][p]
        ci, n = g.consensus(counts, keys[p])
        acounts, akv, anone, acov = view_all[p]
        aci, an = g.consensus(acounts, keys[p])
        cands.append({"gsm_test_position": p, "platinum": labels[p], "key": keys[p],
                      "platinum_answer": plat_answer.get(p) if labels[p] == "revised" else None,
                      "s1_flag": bool(s["cons"][p]), "s1_top_non_key": ci, "s1_top_non_key_votes": n,
                      "s1_key_votes": kv, "s1_no_answer": none, "no_key_flag": bool(nk[p]),
                      "all_models": acov, "all_key_votes": akv, "all_top_non_key": aci, "all_top_non_key_votes": an})

    out = {
        "audit": 86,
        "slug": "gsm8k-helm-consensus-platinum",
        "dataset": ("GSM8K test (openai/gsm8k 'main') and GSM8K-Platinum (madrylab/gsm8k-platinum 'main' test) via the "
                    "HF datasets-server parquet API; per-question outputs from HELM Lite release %s (Stanford CRFM). "
                    "Only GSM8K test positions, labels, final numbers, counts and public model names and accuracies."
                    % C.HELM_RELEASE),
        "fixture": fx,
        "gsm8k_shards": gsm_shards,
        "platinum_shards": plat_shards,
        "platinum": lcounts,
        "universe": ucounts,
        "key_agree": float(key_agree),
        "models": models_out,
        "n_included": len(acc),
        "budget_K": K,
        "base": pr(base),
        "p1_parts": p1_parts,
        "predictions": verdicts,
        "prediction_numbers": numbers,
        "strata": strata_out,
        "top20_exploratory": top20_out,
        "no_key": {"min_cov": C.NK_MIN_COV, "flags": sum(nk.values()), "precision": pr(nk_prec),
                   "precision_reviewed": pr(g.precision(nk, labels, kinds_all=g.REVIEWED)), "recall": pr(nk_rec),
                   "by_label": by_label(nk, labels)},
        "key_share_all_models_exploratory": {"auc_error_vs_clean": None if ks_auc is None else float(ks_auc),
                                             "budget": {"error_labelled": str(ks_b[0]), "labelled": str(ks_b[1]),
                                                        "precision": float(ks_b[0] / ks_b[1]) if ks_b[1] else None}},
        "revised_exploratory": rev_out,
        "n_candidates": len(cands),
        "note": ("Labels: GSM8K-Platinum cleaning_status; GSM8K test questions absent from Platinum are 'rejected'. "
                 "Error = rejected or revised; clean = verified or consensus. Precision = error-labelled share of "
                 "flagged labelled questions; precision_reviewed counts only questions Platinum reviewed (rejected, "
                 "revised, verified). Answers are HELM's final numbers (HELM's own get_final_number); a model with "
                 "no number gives no answer. Consensus flag: at least 6 of 10 give one non-key answer, more than "
                 "give the key. Any-wrong: fewer than 10 of 10 give the key. No-key: at least 2 included models "
                 "answer and none gives the key. Equal budget: the K = S1-consensus-flag-count highest-margin "
                 "questions, ties shared. P2 S1 consensus precision >= 1/2; P3 consensus more precise than any-wrong; "
                 "P4 S1 margin AUC >= 3/4; P5 consensus recall >= 1/4; P6 no-key precision >= consensus precision "
                 "with >= 10 labelled no-key questions; P7 equal-budget precision S1 > S5."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "candidates.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 86, "note": ("Model-flagged or Platinum-error questions in HELM Lite's GSM8K universe, by "
                   "0-based GSM8K test position. Platinum statuses are from GSM8K-Platinum (CC BY-SA 4.0). "
                   "s1_* = the 10 most accurate HELM models; all_* = every included model. A flag is not a "
                   "verdict."), "candidates": cands}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and candidates.json (%d candidates)" % len(cands))


if __name__ == "__main__":
    main()
