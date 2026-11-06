"""How many wrong MMLU answer keys are left outside MMLU-Redux's sample, and which should experts read first? (audit 85)

Rebuilds audit 80 (HELM MMLU release v1.13.0: 78 included models, audit 77's flag on the 10 most accurate, MMLU-Redux
2.0 labels) and audit 82's no-key count, both gated. Sorts every question into frozen tiers (T1 no included model
picks the key; T2 all 10 panel models on one non-key option; T3 the panel's flag; T0 the rest). Then:
- a fixed 2-fold split of the Redux-judged questions (sha256 parity of subject|instance id): tier rates from one half
  predict the other half's wrong keys, per subject against a subject-rate baseline, and in total against the
  estimate's own 95% interval;
- a transport check: unreviewed questions should land in tiers 1-3 as often as reviewed ones of the same subject;
- the estimate of wrong keys among the questions outside Redux's sample (tier-based and subject-based), per subject;
- the review queue: every unreviewed question in tiers 1-3, ranked.

Gates: the hand-traced fixtures must match before any download; the Redux join must place at least 4,000 rows; audit
80 and audit 82's no-key count must be reproduced (P1). Writes results.json and review_queue.json (ids, letters,
votes, counts and 16-hex sha256 prefixes only; no question, option or model text).
Usage: python job.py --out-dir /out (network required). Apache-2.0.
"""

import argparse
import hashlib
import io
import json
import math
import os
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

import pyarrow.parquet as pq

import queue85 as qm
import cases85 as C

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"
TIERS = (1, 2, 3, 0)


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
    idx = {m: {q: qm.pred_index(p, C.FIX_QUESTIONS[q][0]) for q, p in d.items()} for m, d in C.FIX_PREDS.items()}
    panel = qm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
    flags, tallies = qm.panel_flags(panel, idx, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
    parsed = {s: qm.parse_instances(items) for s, items in C.FIX_INST.items()}
    qids, info, counts = qm.build_universe(parsed)
    t = C.FIX_UNIVERSE_TARGET
    preds_ok = all(qm.map_predictions(C.FIX_PRED[s], parsed[s], s, qids) == C.FIX_PRED_TARGET[s]
                   for s in ("virology", "anatomy"))
    rj = qm.redux_join(C.FIX_REDUX, qids, C.FIX_GOLD)
    kc = qm.key_pickers(idx, sorted(C.FIX_ACC), C.FIX_QUESTIONS)
    rows = qm.queue_rows(sorted(C.FIX_QUESTIONS), C.FIX_TIERS, flags, tallies, C.FIX_KEY_COUNTS, C.FIX_Q_INFO)
    tr = qm.transport(C.FIX_T_FLAGGED, C.FIX_T_SUBJ, C.FIX_T_REVIEWED, C.FIX_T_UNREVIEWED)
    return {"panel_flags": panel == C.FIX_TARGET["panel"] and flags == C.FIX_TARGET["flags"],
            "runs": qm.select_runs(C.FIX_RUNS) == C.FIX_RUNS_TARGET,
            "universe": qids == t["qids"] and info == t["info"] and counts == t["counts"],
            "predictions": preds_ok,
            "redux_join": rj == C.FIX_REDUX_TARGET and qm.groups(3, rj[0]) == C.FIX_GROUPS_TARGET,
            "tiers": (kc == (C.FIX_KEY_COUNTS, C.FIX_NOKEY)
                      and qm.assign_tiers(flags, tallies, C.FIX_TIER_NOKEY, C.FIX_PANEL_SIZE) == C.FIX_TIERS
                      and all(qm.tier_of(*a) == w for a, w in C.FIX_TIER_OF)),
            "queue": [r["qid"] for r in rows] == C.FIX_Q_ORDER and rows[0] == C.FIX_Q_FIRST,
            "cross_fold": (qm.cross_fold(C.FIX_CF_TIERS, C.FIX_SUBJ, C.FIX_FOLD, C.FIX_CF_TARGET, C.FIX_CF_JUDGED)
                           == C.FIX_CF),
            "estimate": qm.estimate(C.FIX_E_CELLS, C.FIX_E_RATE, C.FIX_E_POOLED, C.FIX_E_DEN,
                                    C.FIX_E_QS) == C.FIX_E_TARGET,
            "transport": tr == C.FIX_T_TARGET,
            "verdicts": qm.predictions85(C.FIX_CF, tr, C.FIX_V_RATES, C.Z2) == C.FIX_VERDICTS}


# ----- HELM: audit 80, rebuilt (copied from audit 83's job.py) -----

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


# ----- Helpers for the outputs -----

def fl(x):
    return None if x is None else float(x)


def interval(exp, var):
    sd = math.sqrt(float(var))
    return {"expected": float(exp), "sd": sd, "low95": max(0.0, float(exp) - 1.96 * sd),
            "high95": float(exp) + 1.96 * sd}


def by_group(ids, g):
    s = set(ids)
    return {name: sum(1 for q in g[name] if q in s) for name in g}


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
    reviewed = set(labels)
    unreviewed = list(g["unreviewed"])
    print("[base] miskey=%d other_error=%d ok=%d unsure=%d unreviewed=%d"
          % (len(g["miskey"]), len(g["other_error"]), len(g["ok"]), len(g["unsure_or_conflict"]), len(unreviewed)))

    # ----- Gates: audit 80's panel and flag; audit 82's no-key count -----
    panel = qm.select_panel(acc, C.PANEL_SIZE)
    f1, t1 = qm.panel_flags(panel, preds, h_questions, C.MIN_AGREE)
    flagged80 = {name: qm.n_flagged(g[name], f1) for name in C.EXPECTED_80["flagged"]}
    prec80 = qm.flag_precision(f1, g)
    repro80 = (n_q == C.EXPECTED_80["universe"] and len(acc) == C.EXPECTED_80["included"]
               and panel == C.EXPECTED_80["panel"] and flagged80 == C.EXPECTED_80["flagged"]
               and prec80 == C.EXPECTED_80["precision"])
    key_counts, nokey = qm.key_pickers(preds, sorted(acc), h_questions)
    nokey_groups = by_group(nokey, g)
    repro82 = nokey_groups == C.EXPECTED_82_NOKEY
    print("[repro80] flagged=%s precision=%s ok=%s" % (flagged80, prec80, repro80))
    print("[repro82] no-key=%s ok=%s" % (nokey_groups, repro82))

    # ----- Tiers -----
    tiers = qm.assign_tiers(f1, t1, nokey, C.PANEL_SIZE)
    subject_of = {q: info[q][0] for q in range(n_q)}
    fold = {q: qm.fold_of(info[q][0], info[q][1]) for q in range(n_q)}
    rm, pm_, dm = qm.rates(tiers, miskey, judged, judged)
    re_, pe, de = qm.rates(tiers, err, judged, judged)
    tier_table = []
    for t in TIERS:
        ids = [q for q in range(n_q) if tiers[q] == t]
        grp = by_group(ids, g)
        nj = dm.get(t, 0)
        n_mis = grp["miskey"]
        n_err = grp["miskey"] + grp["other_error"]
        nu = grp["unreviewed"]
        tier_table.append({"tier": t, "questions": len(ids), "by_redux_group": grp, "judged": nj,
                           "miskeys": n_mis, "miskey_rate": fl(rm.get(t)), "miskey_wilson95": qm.wilson(n_mis, nj),
                           "error_labelled": n_err, "error_rate": fl(re_.get(t)),
                           "error_wilson95": qm.wilson(n_err, nj), "unreviewed": nu,
                           "expected_miskeys_unreviewed": fl(nu * rm[t]) if t in rm else None,
                           "expected_errors_unreviewed": fl(nu * re_[t]) if t in re_ else None})
    print("[tiers] %s" % [(r["tier"], r["questions"], r["judged"], r["miskeys"], r["error_labelled"], r["unreviewed"])
                          for r in tier_table])

    # ----- P2/P3: the held-out test; P4: transport; P5: order -----
    folds_mis = qm.cross_fold(tiers, subject_of, fold, miskey, judged)
    folds_err = qm.cross_fold(tiers, subject_of, fold, err, judged)
    flagged_set = {q for q in range(n_q) if tiers[q] >= 1}
    tr = qm.transport(flagged_set, subject_of, reviewed, unreviewed)
    verdicts = qm.predictions85(folds_mis, tr, [rm.get(1), rm.get(2), rm.get(3), rm.get(0)], C.Z2)
    p1_parts = {"fixtures": all(fx.values()), "reproduce_80": repro80, "reproduce_82_nokey": repro82}
    verdicts["P1_structural"] = all(p1_parts.values())
    verdicts["P1_counts"] = [n_q, len(acc), qm.n_flagged(range(n_q), f1), len(nokey)]
    print("[P1] %s" % p1_parts)
    for name in sorted(v for v in verdicts if not any(v.endswith(x) for x in ("_counts", "_mae", "_folds", "_rates"))):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    print("[prediction] numbers %s" % {k: v for k, v in sorted(verdicts.items())
                                       if any(k.endswith(x) for x in ("_counts", "_mae", "_folds", "_rates"))})

    def folds_json(fs):
        return [{"fold": f["fold"], "n_test": f["n_test"], "actual": f["actual"],
                 "tier": interval(f["tier_expected"], f["tier_var"]), "subject_expected": float(f["subj_expected"]),
                 "per_subject_abs_error_tier": float(f["mae_tier"]),
                 "per_subject_abs_error_subject": float(f["mae_subject"])} for f in fs]

    # ----- The estimate outside Redux's sample -----
    est = {}
    for name, target in (("miskeys", miskey), ("errors", err)):
        tr_, tp_, td_ = qm.rates(tiers, target, judged, judged)
        sr_, sp_, sd_ = qm.rates(subject_of, target, judged, judged)
        te, tv, trows = qm.estimate(tiers, tr_, tp_, td_, unreviewed)
        se, sv, _srows = qm.estimate(subject_of, sr_, sp_, sd_, unreviewed)
        est[name] = {"tier_based": interval(te, tv), "subject_based": interval(se, sv),
                     "tier_rows": [{"tier": r["cell"], "unreviewed": r["n"], "rate": float(r["rate"]),
                                    "expected": float(r["expected"])} for r in trows],
                     "observed_in_redux_sample": sum(1 for q in judged if q in target)}
    print("[estimate] %s" % {k: (v["tier_based"], v["subject_based"]) for k, v in est.items()})

    # Per subject (exploratory): unreviewed count, tier counts, expected wrong keys by both estimators.
    tmr, tmp_, _ = qm.rates(tiers, miskey, judged, judged)
    smr, smp_, _ = qm.rates(subject_of, miskey, judged, judged)
    pt = qm.predict(tiers, tmr, tmp_, unreviewed)
    ps = qm.predict(subject_of, smr, smp_, unreviewed)
    per_subject = {}
    for q in unreviewed:
        s = subject_of[q]
        row = per_subject.setdefault(s, {"unreviewed": 0, "tier1": 0, "tier2": 0, "tier3": 0,
                                         "expected_miskeys_tier": Fraction(0), "expected_miskeys_subject": Fraction(0)})
        row["unreviewed"] += 1
        if tiers[q] >= 1:
            row["tier%d" % tiers[q]] += 1
        row["expected_miskeys_tier"] += pt[q]
        row["expected_miskeys_subject"] += ps[q]
    for s in per_subject:
        r = per_subject[s]
        r["redux_judged"] = sum(1 for q in judged if subject_of[q] == s)
        r["redux_miskeys"] = sum(1 for q in miskey if subject_of[q] == s)
        r["expected_miskeys_tier"] = float(r["expected_miskeys_tier"])
        r["expected_miskeys_subject"] = float(r["expected_miskeys_subject"])
    subj_rows = [dict(subject=s, **per_subject[s]) for s in sorted(per_subject)]

    # ----- The review queue -----
    rows = qm.queue_rows(unreviewed, tiers, f1, t1, key_counts, info)
    text_of = {qid: key[1][0] for key, qid in qids.items()}
    for r in rows:
        r["question_sha256_16"] = qm.question_hash(text_of[r["qid"]])
        r["est_miskey_rate_of_tier"] = fl(rm.get(r["tier"]))
        r["est_error_rate_of_tier"] = fl(re_.get(r["tier"]))
    print("[queue] %d rows, by tier %s" % (len(rows), {t: sum(1 for r in rows if r["tier"] == t) for t in (1, 2, 3)}))

    out = {
        "audit": 85,
        "slug": "mcq-mmlu-helm-review-queue",
        "dataset": ("HELM MMLU release %s (Stanford CRFM, public GCS bucket crfm-helm-public/mmlu) and MMLU-Redux 2.0 "
                    "via the HF datasets-server parquet API. Only model names, counts, rates and hashes."
                    % C.HELM_RELEASE),
        "fixture": fx,
        "helm": {"release_sha256": H["release_sha256"], "universe": n_q, "universe_counts": H["universe_counts"],
                 "instances_failed": H["inst_fail"], "models": H["n_models"], "included": len(acc),
                 "panel": panel, "flagged": flagged80, "precision": list(prec80), "reproduces_80": repro80,
                 "nokey_by_group": nokey_groups, "reproduces_82_nokey": repro82},
        "redux": {"rows": len(redux), "join": rcounts, "key_agree": key_agree, "shards": redux_shards,
                  "groups": {k: len(v) for k, v in g.items()}},
        "p1_parts": p1_parts,
        "predictions": verdicts,
        "tiers": tier_table,
        "cross_fold_miskeys": folds_json(folds_mis),
        "cross_fold_errors_exploratory": folds_json(folds_err),
        "fold_sizes": {"judged_fold0": sum(1 for q in judged if fold[q] == 0),
                       "judged_fold1": sum(1 for q in judged if fold[q] == 1)},
        "transport": {"observed": tr[0], "expected": float(tr[1]), "sd": math.sqrt(float(tr[2])),
                      "skipped_subjects": tr[3]},
        "estimate_unreviewed": est,
        "per_subject_exploratory": subj_rows,
        "queue_size": len(rows),
        "note": ("Tiers (exclusive, in order): T1 none of the included HELM models picks the key; T2 all 10 most "
                 "accurate models pick the same non-key option; T3 audit 77's flag (>= 6 of 10 on one non-key option, "
                 "more than on the key); T0 the rest. Rates are shares of Redux-judged questions (wrong key, OK or "
                 "another error label). Folds: sha256('subject|instance id') parity. Intervals: expected +- 1.96 sd, "
                 "sd from each question's own spread plus the rate's sampling spread. P2 HEADLINE tier rates predict "
                 "each held-out half's wrong keys per subject with a smaller summed absolute error than subject rates; "
                 "P3 the held-out total falls inside the tier estimate's 95% interval in both halves; P4 unreviewed "
                 "questions land in tiers 1-3 as often as reviewed ones of the same subject (95%); P5 wrong-key rates "
                 "fall T1 > T2 > T3 > T0."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    queue = {"audit": 85,
             "note": ("Model-flagged, NOT expert-checked: the MMLU test questions (HELM release v1.13.0) outside "
                      "MMLU-Redux 2.0's sample that fall in tiers 1-3, ranked by tier, then the top-10 panel's margin, "
                      "then fewer models picking the key, then subject and position. est_*_rate_of_tier = the share of "
                      "Redux-judged questions in the same tier with a wrong key / any error label. Each row may hold a "
                      "wrong key, a second defensible answer or a mistake strong models share."),
             "panel": panel, "rows": rows}
    with open(os.path.join(args.out_dir, "review_queue.json"), "w", encoding="utf-8") as fh:
        json.dump(queue, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and review_queue.json")


if __name__ == "__main__":
    main()
