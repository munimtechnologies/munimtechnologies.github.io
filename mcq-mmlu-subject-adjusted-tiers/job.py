"""Tiers adjusted by subject: a better count of MMLU's remaining wrong keys? (audit 87)

Rebuilds audit 85 (HELM MMLU release v1.13.0, 78 included models, audit 77's flag on the 10 most accurate, MMLU-Redux
2.0 labels, the four tiers, the fixed 2-fold split) and checks that its published numbers reproduce. Then fits the
subject-adjusted tier model of est87.py on each half and scores it on the other half against audit 85's subject and
tier rates, builds stratified-bootstrap predictive intervals, estimates the wrong keys among the questions outside
Redux's sample and writes the queue re-ranked by the adjusted probability.

Gates: the hand-traced fixtures must match before any download; the Redux join must place at least 4,000 rows;
audits 80, 82 and 85 must be reproduced (P1). Writes results.json and review_queue_adjusted.json (ids, letters,
probabilities and counts only; no question, option or model text).
Usage: python job.py --out-dir /out (network required). Apache-2.0.
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

import base87 as qm
import cases87 as C
import est87 as em

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


def read_redux():
    rows, shards = [], []
    listing = _json(PARQUET_API % C.REDUX_DATASET)["parquet_files"]
    files = sorted((f["config"], f["url"]) for f in listing if f["split"] == C.REDUX_SPLIT)
    for config, url in files:
        raw = _get(url)
        shards.append({"config": config, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        t = pq.read_table(io.BytesIO(raw))
        cols = {c: (t.column(c).to_pylist() if c in t.column_names else [None] * t.num_rows)
                for c in ("question", "choices", "answer", "error_type")}
        for q, ch, a, et in zip(cols["question"], cols["choices"], cols["answer"], cols["error_type"]):
            rows.append({"subject": config, "question": q, "choices": list(ch or []),
                         "answer": int(a) if a is not None else None, "label": qm.label_of(et)})
    return rows, shards


def fixture_ok():
    t, s, f, tg, j = C.FIX_TIERS, C.FIX_SUBJ, C.FIX_FOLD, C.FIX_TARGET, C.FIX_JUDGED
    fac = em.subject_factors(t, s, tg, j, C.FIX_TRAIN_F0, C.FIX_RATE_F0, C.FIX_POOLED_F0, C.PRIOR)
    adj = em.cross_fold_adjusted(t, s, f, tg, j, C.PRIOR)
    base = qm.cross_fold(t, s, f, tg, j)
    b1 = em.bootstrap_total(t, s, set(), j, list(range(12)), C.PRIOR, 40, 1)
    b2 = em.bootstrap_total(C.FIX_B_TIERS, C.FIX_B_SUBJ, set(range(6)), set(range(6)), list(range(6)), C.PRIOR, 40, 1)
    b3 = em.bootstrap_total(t, s, tg, j, list(range(12)), C.PRIOR, 40, 5)
    b4 = em.bootstrap_total(t, s, tg, j, list(range(12)), C.PRIOR, 40, 5)
    adj_e, tier_e, subj_e = C.FIX_V_EST
    v = em.predictions87(C.FIX_ADJ, C.FIX_V_BASE, C.FIX_V_ADJ_ERR, C.FIX_V_BASE_ERR, C.FIX_V_BOOT, adj_e, tier_e,
                         subj_e)
    return {"rates": qm.rates(t, tg, j, C.FIX_TRAIN_F0)[:2] == (C.FIX_RATE_F0, C.FIX_POOLED_F0),
            "factors": fac == C.FIX_FACTORS_F0,
            "cross_fold_adjusted": adj == C.FIX_ADJ,
            "cross_fold_base": [(x["mae_subject"], x["mae_tier"]) for x in base] == C.FIX_BASE_MAE,
            "bootstrap": (b1[:2] == (0, 0) and b2[:2] == (6, 6) and b3 == b4 and len(b3[2]) == 40),
            "pct_bounds": all(em.pct_bounds(b) == w for b, w in C.FIX_PCT),
            "verdicts": v == C.FIX_VERDICTS}


# ----- HELM: audit 80, rebuilt (copied from audit 85's job.py) -----

def build_helm():
    release_url = "%s/releases/%s/runs_to_run_suites.json" % (C.HELM_BASE, C.HELM_RELEASE)
    raw_release = _get(release_url)
    run_suites = json.loads(raw_release.decode("utf-8"))
    chosen, dups = qm.select_runs(run_suites)
    models = sorted({m for m, _s in chosen})
    subjects = sorted({s for _m, s in chosen})
    print("[helm runs] entries=%d chosen=%d dups=%d models=%d subjects=%d"
          % (len(run_suites), len(chosen), dups, len(models), len(subjects)))

    inst_src = {}
    for (m, s), (run, suite) in sorted(chosen.items()):
        inst_src.setdefault((suite, s), run)

    def fetch_inst(key):
        suite, s = key
        try:
            return key, qm.parse_instances(_json(run_url(suite, inst_src[key], "instances.json"))), None
        except Exception as e:  # noqa: BLE001 - recorded, never patched
            return key, None, str(e)[:200]

    instances, inst_fail = {}, []
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        for key, parsed, err in ex.map(fetch_inst, sorted(inst_src)):
            if parsed is None:
                inst_fail.append({"suite": key[0], "subject": key[1], "error": err})
            else:
                instances[key] = parsed
    base_suite = {}
    for suite, s in instances:
        if s not in base_suite or qm.suite_version(suite) < qm.suite_version(base_suite[s]):
            base_suite[s] = suite
    qids, info, ucounts = qm.build_universe({s: instances[(base_suite[s], s)] for s in base_suite})
    n_q = len(info)
    gold_of = [r[3] for r in info]
    print("[helm universe] files=%d failed=%d questions=%d %s" % (len(instances), len(inst_fail), n_q, ucounts))

    def fetch_pred(item):
        (m, s), (run, suite) = item
        inst = instances.get((suite, s))
        if inst is None:
            return m, s, None, {"error": "no instances for suite"}
        try:
            data = _json(run_url(suite, run, "display_predictions.json"))
        except Exception as e:  # noqa: BLE001
            return m, s, None, {"error": str(e)[:200]}
        out, c = qm.map_predictions(data, inst, s, qids)
        return m, s, out, c

    preds, stats = {m: {} for m in models}, {m: {} for m in models}
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        for m, s, out, c in ex.map(fetch_pred, sorted(chosen.items())):
            stats[m][s] = c
            if out is not None:
                preds[m].update(out)

    acc = {}
    for m in models:
        ss = stats[m]
        tot = {k: sum(v.get(k, 0) for v in ss.values() if "error" not in v)
               for k in ("valid", "from_mapped", "invalid", "consistent", "inconsistent", "em_correct")}
        n_subj = sum(1 for v in ss.values() if "error" not in v)
        covered = len(preds[m])
        correct = sum(1 for q, i in preds[m].items() if i is not None and i == gold_of[q])
        mapped_items = tot["valid"] + tot["from_mapped"] + tot["invalid"]
        checked = tot["consistent"] + tot["inconsistent"]
        cons = Fraction(tot["consistent"], checked) if checked else Fraction(1)
        em_gap = abs(Fraction(correct - tot["em_correct"], mapped_items)) if mapped_items else Fraction(1)
        if (n_subj == C.N_SUBJECTS and n_q and Fraction(covered, n_q) >= C.MIN_COVERAGE
                and cons >= C.MIN_CONSISTENT and em_gap <= C.MAX_EM_GAP):
            acc[m] = (correct, covered)
    print("[helm inclusion] included=%d of %d" % (len(acc), len(models)))
    return {"qids": qids, "info": info, "n_q": n_q, "gold_of": gold_of, "preds": preds, "acc": acc,
            "release_sha256": hashlib.sha256(raw_release).hexdigest(), "inst_fail": inst_fail,
            "universe_counts": ucounts, "n_models": len(models)}


def by_group(ids, g):
    s = set(ids)
    return {name: sum(1 for q in g[name] if q in s) for name in g}


def r2(x):
    return round(float(x), 2)


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

    H = build_helm()
    qids, info, n_q, gold_of, acc, preds = H["qids"], H["info"], H["n_q"], H["gold_of"], H["acc"], H["preds"]
    h_questions = {q: (info[q][2], info[q][3]) for q in range(n_q)}
    redux, redux_shards = read_redux()
    labels, rcounts, key_agree = qm.redux_join(redux, qids, gold_of)
    print("[redux] rows=%d %s key_agree=%d" % (len(redux), rcounts, key_agree))
    if rcounts["joined"] < C.ABORT_REDUX_JOINED:
        raise SystemExit("Redux join placed only %d rows -- aborting" % rcounts["joined"])
    g = qm.groups(n_q, labels)
    miskey = set(g["miskey"])
    err = miskey | set(g["other_error"])
    judged = err | set(g["ok"])
    unreviewed = list(g["unreviewed"])

    # ----- Gates: audits 80, 82 and 85 -----
    panel = qm.select_panel(acc, C.PANEL_SIZE)
    f1, t1 = qm.panel_flags(panel, preds, h_questions, C.MIN_AGREE)
    flagged80 = {name: qm.n_flagged(g[name], f1) for name in C.EXPECTED_80["flagged"]}
    prec80 = qm.flag_precision(f1, g)
    repro80 = (n_q == C.EXPECTED_80["universe"] and len(acc) == C.EXPECTED_80["included"]
               and panel == C.EXPECTED_80["panel"] and flagged80 == C.EXPECTED_80["flagged"]
               and prec80 == C.EXPECTED_80["precision"])
    key_counts, nokey = qm.key_pickers(preds, sorted(acc), h_questions)
    repro82 = by_group(nokey, g) == C.EXPECTED_82_NOKEY
    tiers = qm.assign_tiers(f1, t1, nokey, C.PANEL_SIZE)
    subject_of = {q: info[q][0] for q in range(n_q)}
    fold = {q: qm.fold_of(info[q][0], info[q][1]) for q in range(n_q)}
    tier_counts = {t: sum(1 for q in range(n_q) if tiers[q] == t) for t in (1, 2, 3, 0)}
    queue = qm.queue_rows(unreviewed, tiers, f1, t1, key_counts, info)
    base_mis = qm.cross_fold(tiers, subject_of, fold, miskey, judged)
    base_err = qm.cross_fold(tiers, subject_of, fold, err, judged)
    mt85 = sum((f["mae_tier"] for f in base_mis), Fraction(0))
    ms85 = sum((f["mae_subject"] for f in base_mis), Fraction(0))
    rm, pm, dm = qm.rates(tiers, miskey, judged, judged)
    sr, sp, sd = qm.rates(subject_of, miskey, judged, judged)
    est_tier, _tv, _ = qm.estimate(tiers, rm, pm, dm, unreviewed)
    est_subj, _sv, _ = qm.estimate(subject_of, sr, sp, sd, unreviewed)
    e85 = C.EXPECTED_85
    repro85 = (tier_counts == e85["tiers"] and len(queue) == e85["queue"] and r2(mt85) == e85["mae_tier"]
               and r2(ms85) == e85["mae_subject"] and r2(est_tier) == e85["est_tier"]
               and r2(est_subj) == e85["est_subject"])
    p1_parts = {"fixtures": all(fx.values()), "reproduce_80": repro80, "reproduce_82_nokey": repro82,
                "reproduce_85": repro85}
    print("[P1] %s tiers=%s queue=%d mae85=(%.4f, %.4f) est85=(%.4f, %.4f)"
          % (p1_parts, tier_counts, len(queue), float(mt85), float(ms85), float(est_tier), float(est_subj)))

    # ----- P2, P5: the held-out test; P3: bootstrap intervals -----
    adj_mis = em.cross_fold_adjusted(tiers, subject_of, fold, miskey, judged, C.PRIOR)
    adj_err = em.cross_fold_adjusted(tiers, subject_of, fold, err, judged, C.PRIOR)
    boots = []
    for f in (0, 1):
        train = {q for q in judged if fold[q] != f}
        test = [q for q in sorted(judged) if fold[q] == f]
        lo, hi, _tot = em.bootstrap_total(tiers, subject_of, miskey, train, test, C.PRIOR, C.B, C.SEED + f)
        boots.append((lo, hi))
    print("[held-out] adjusted=%s boot=%s" % ([(f["actual"], float(f["adj_expected"]), float(f["mae_adj"]))
                                                for f in adj_mis], boots))

    # ----- The estimate outside Redux's sample (P4) -----
    rate, pooled, fac = em.fit_adjusted(tiers, subject_of, miskey, judged, judged, C.PRIOR)
    p_un = em.adjusted_predict(tiers, subject_of, rate, pooled, fac, unreviewed)
    est_adj = sum(p_un.values(), Fraction(0))
    lo_f, hi_f, tot_f = em.bootstrap_total(tiers, subject_of, miskey, judged, unreviewed, C.PRIOR, C.B, C.SEED + 2)
    erate, epooled, efac = em.fit_adjusted(tiers, subject_of, err, judged, judged, C.PRIOR)
    est_adj_err = sum(em.adjusted_predict(tiers, subject_of, erate, epooled, efac, unreviewed).values(), Fraction(0))
    est_tier_err = qm.estimate(tiers, *qm.rates(tiers, err, judged, judged), unreviewed)[0]
    est_subj_err = qm.estimate(subject_of, *qm.rates(subject_of, err, judged, judged), unreviewed)[0]

    verdicts = em.predictions87(adj_mis, base_mis, adj_err, base_err, boots, est_adj, est_tier, est_subj)
    verdicts["P1_structural"] = all(p1_parts.values())
    for name in sorted(k for k, v in verdicts.items() if isinstance(v, bool)):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    print("[prediction] numbers %s" % {k: v for k, v in sorted(verdicts.items()) if not isinstance(v, bool)})
    print("[estimate] adjusted=%.3f boot95=(%d, %d) tier=%.3f subject=%.3f"
          % (float(est_adj), lo_f, hi_f, float(est_tier), float(est_subj)))

    # ----- Exploratory: other priors -----
    priors = []
    for a in C.EXPLORE_PRIORS:
        cf = em.cross_fold_adjusted(tiers, subject_of, fold, miskey, judged, a)
        r_, p_, f_ = em.fit_adjusted(tiers, subject_of, miskey, judged, judged, a)
        e_ = sum(em.adjusted_predict(tiers, subject_of, r_, p_, f_, unreviewed).values(), Fraction(0))
        priors.append({"prior": float(a), "mae_adj_sum": float(sum((x["mae_adj"] for x in cf), Fraction(0))),
                       "fold_totals": [float(x["adj_expected"]) for x in cf], "estimate_unreviewed": float(e_)})
    print("[priors] %s" % priors)

    # ----- Exploratory: per subject -----
    pt = qm.predict(tiers, rm, pm, unreviewed)
    ps = qm.predict(subject_of, sr, sp, unreviewed)
    per_subject = {}
    for q in unreviewed:
        s = subject_of[q]
        row = per_subject.setdefault(s, {"unreviewed": 0, "tiers_1_3": 0, "adjusted": Fraction(0),
                                         "tier": Fraction(0), "subject": Fraction(0)})
        row["unreviewed"] += 1
        row["tiers_1_3"] += 1 if tiers[q] >= 1 else 0
        row["adjusted"] += p_un[q]
        row["tier"] += pt[q]
        row["subject"] += ps[q]
    subj_rows = []
    for s in sorted(per_subject):
        r = per_subject[s]
        subj_rows.append({"subject": s, "unreviewed": r["unreviewed"], "tiers_1_3": r["tiers_1_3"],
                          "factor": float(fac.get(s, 1)), "expected_adjusted": float(r["adjusted"]),
                          "expected_tier": float(r["tier"]), "expected_subject": float(r["subject"]),
                          "redux_judged": sum(1 for q in judged if subject_of[q] == s),
                          "redux_miskeys": sum(1 for q in miskey if subject_of[q] == s)})

    # ----- The queue, re-ranked by the adjusted probability -----
    rows = []
    for r in queue:
        q = r["qid"]
        rows.append({"qid": q, "rank_85": r["rank"], "tier": r["tier"], "subject": r["subject"],
                     "helm_instance_id": r["helm_instance_id"], "helm_test_position": r["helm_test_position"],
                     "helm_key": r["helm_key"], "consensus_letter": r["consensus_letter"], "margin": r["margin"],
                     "p_wrong_key_adjusted": float(p_un[q]), "subject_factor": float(fac.get(r["subject"], 1))})
    rows.sort(key=lambda x: (-x["p_wrong_key_adjusted"], x["rank_85"]))
    for i, x in enumerate(rows):
        x["rank"] = i + 1
    exp_queue = sum((p_un[r["qid"]] for r in queue), Fraction(0))
    top = {n: float(sum(Fraction(x["p_wrong_key_adjusted"]) for x in rows[:n])) for n in (50, 100, 200)}

    out = {
        "audit": 87,
        "slug": "mcq-mmlu-subject-adjusted-tiers",
        "dataset": ("HELM MMLU release %s (Stanford CRFM, public GCS bucket crfm-helm-public/mmlu) and MMLU-Redux 2.0 "
                    "via the HF datasets-server parquet API. Only model names, counts, rates and probabilities."
                    % C.HELM_RELEASE),
        "fixture": fx,
        "helm": {"release_sha256": H["release_sha256"], "universe": n_q, "universe_counts": H["universe_counts"],
                 "instances_failed": H["inst_fail"], "models": H["n_models"], "included": len(acc), "panel": panel,
                 "flagged": flagged80, "precision": list(prec80)},
        "redux": {"rows": len(redux), "join": rcounts, "key_agree": key_agree, "shards": redux_shards,
                  "groups": {k: len(v) for k, v in g.items()}},
        "p1_parts": p1_parts,
        "reproduced_85": {"tiers": {str(k): v for k, v in tier_counts.items()}, "queue": len(queue),
                          "mae_tier": float(mt85), "mae_subject": float(ms85), "est_tier": float(est_tier),
                          "est_subject": float(est_subj)},
        "predictions": verdicts,
        "held_out_miskeys": [{"fold": a["fold"], "n_test": a["n_test"], "actual": a["actual"],
                              "adjusted_expected": float(a["adj_expected"]), "mae_adjusted": float(a["mae_adj"]),
                              "subject_expected": float(b["subj_expected"]), "mae_subject": float(b["mae_subject"]),
                              "tier_expected": float(b["tier_expected"]), "mae_tier": float(b["mae_tier"]),
                              "boot95_adjusted": list(bt)}
                             for a, b, bt in zip(adj_mis, base_mis, boots)],
        "held_out_errors": [{"fold": a["fold"], "actual": a["actual"],
                             "adjusted_expected": float(a["adj_expected"]), "mae_adjusted": float(a["mae_adj"]),
                             "mae_subject": float(b["mae_subject"]), "mae_tier": float(b["mae_tier"])}
                            for a, b in zip(adj_err, base_err)],
        "estimate_unreviewed": {
            "unreviewed": len(unreviewed),
            "miskeys": {"adjusted": float(est_adj), "adjusted_boot95": [lo_f, hi_f],
                        "adjusted_boot_median": tot_f[len(tot_f) // 2], "tier": float(est_tier),
                        "subject": float(est_subj), "observed_in_redux_sample": len(miskey)},
            "any_error_point": {"adjusted": float(est_adj_err), "tier": float(est_tier_err),
                                "subject": float(est_subj_err), "observed_in_redux_sample": len(err)},
            "tier_rates_all_judged": {str(t): float(v) for t, v in rate.items()},
        },
        "priors_exploratory": priors,
        "per_subject_exploratory": subj_rows,
        "queue": {"rows": len(rows), "expected_wrong_keys_adjusted": float(exp_queue),
                  "expected_in_top": {str(k): v for k, v in top.items()}},
        "note": ("Adjusted model: probability = min(1, tier rate x k_s), k_s = (O_s + 1) / (E_s + 1), O_s the "
                 "subject's wrong keys and E_s the sum of its tier rates among the training questions. Held-out "
                 "halves as audit 85 (sha256 parity of subject|instance id). Bootstrap: 1,000 replicates resampling "
                 "judged training questions within subject, then drawing each target question's outcome; 95% "
                 "predictive interval = 25th and 975th of the sorted totals. P2 HEADLINE: adjusted summed per-subject "
                 "error < subject rates'; P3 each half's actual inside the bootstrap interval built on the other "
                 "half; P4 adjusted estimate strictly between audit 85's subject and tier estimates; P5 P2 for any "
                 "error label."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "review_queue_adjusted.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 87,
                   "note": ("Model-flagged, NOT expert-checked: audit 85's 716 queued MMLU questions (outside "
                            "MMLU-Redux 2.0's sample, tiers 1-3) re-ranked by the subject-adjusted probability of a "
                            "wrong key (ties by audit 85's rank). A row may hold a wrong key, a second defensible "
                            "answer or a mistake strong models share."),
                   "panel": panel, "rows": rows}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and review_queue_adjusted.json")


if __name__ == "__main__":
    main()
