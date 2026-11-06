"""How strong must a model panel be to find wrong MMLU answer keys? (audit 83)

Rebuilds audit 80 (HELM MMLU release v1.13.0: 78 included models, audit 77's flag, MMLU-Redux 2.0 labels), gated to
reproduce its published counts with S1 = audit 80's panel. Then ranks the included models by accuracy, cuts them into
seven disjoint panels of 10 (S1 = ranks 1-10 ... S7 = ranks 61-70), and scores each panel's frozen flag and vote
margin against Redux's expert labels: flag count and precision, AUC (miskeys vs OK) and expected precision when each
panel sends the same number of questions to review (K = S1's flag count, ties at the cut shared evenly). A 20-model
panel (ranks 1-20) is scored the same way.

Gates: the hand-traced fixtures must match before any download; the Redux join must place at least 4,000 rows; at
least 70 models must be included. Writes results.json (aggregates, verdicts, per-panel and sliding-window numbers;
model names and accuracies are public HELM leaderboard facts; no question, option or model text).
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

import panel83 as pm
import cases83 as C

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
                         "answer": int(a) if a is not None else None, "label": pm.label_of(et)})
    return rows, shards


def fixture_ok():
    idx = {m: {q: pm.pred_index(p, C.FIX_QUESTIONS[q][0]) for q, p in d.items()} for m, d in C.FIX_PREDS.items()}
    panel = pm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
    flags, _t = pm.panel_flags(panel, idx, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
    parsed = {s: pm.parse_instances(items) for s, items in C.FIX_INST.items()}
    qids, info, counts = pm.build_universe(parsed)
    t = C.FIX_UNIVERSE_TARGET
    preds_ok = all(pm.map_predictions(C.FIX_PRED[s], parsed[s], s, qids) == C.FIX_PRED_TARGET[s]
                   for s in ("virology", "anatomy"))
    rj = pm.redux_join(C.FIX_REDUX, qids, C.FIX_GOLD)
    return {"panel_flags": panel == C.FIX_TARGET["panel"] and flags == C.FIX_TARGET["flags"],
            "runs": pm.select_runs(C.FIX_RUNS) == C.FIX_RUNS_TARGET,
            "universe": qids == t["qids"] and info == t["info"] and counts == t["counts"],
            "predictions": preds_ok,
            "redux_join": rj == C.FIX_REDUX_TARGET and pm.groups(3, rj[0]) == C.FIX_GROUPS_TARGET,
            "margin_auc": (all(pm.margin(c, k) == w for (c, k), w in C.FIX_MARGIN)
                           and all(pm.auc(p, n) == w for (p, n), w in C.FIX_AUC)),
            "strata": (pm.strata(C.FIX_S_ACC, 2, 3) == C.FIX_S_TARGET and pm.strata(C.FIX_S_ACC, 3, 3) is None),
            "budget": all(pm.budget_counts(C.FIX_B_SCORE, C.FIX_B_SETS, b) == w for b, w in C.FIX_B_CASES),
            "stratum_stats": (pm.stratum_stats(C.FIX_P_FLAGS, C.FIX_P_SCORE, C.FIX_P_G, C.FIX_P_BUDGET)
                              == C.FIX_P_TARGET),
            "verdicts": pm.predictions83(C.FIX_V_ST, C.FIX_V_TOP20, C.FIX_V_BASE[0], C.FIX_V_BASE[1],
                                         C.THRESHOLDS) == C.FIX_VERDICTS}


def mean_acc(acc, panel):
    return float(sum(pm.accuracy(*acc[m]) for m in panel) / len(panel)) if panel else None


# ----- HELM: audit 80, rebuilt (copied from audit 82's job.py) -----

def build_helm():
    release_url = "%s/releases/%s/runs_to_run_suites.json" % (C.HELM_BASE, C.HELM_RELEASE)
    raw_release = _get(release_url)
    run_suites = json.loads(raw_release.decode("utf-8"))
    chosen, dups = pm.select_runs(run_suites)
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
            return key, pm.parse_instances(_json(run_url(suite, inst_src[key], "instances.json"))), None
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
        if s not in base_suite or pm.suite_version(suite) < pm.suite_version(base_suite[s]):
            base_suite[s] = suite
    qids, info, ucounts = pm.build_universe({s: instances[(base_suite[s], s)] for s in base_suite})
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
        out, c = pm.map_predictions(data, inst, s, qids)
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
    labels, rcounts, key_agree = pm.redux_join(redux, qids, gold_of)
    print("[redux] rows=%d %s key_agree=%d" % (len(redux), rcounts, key_agree))
    if rcounts["joined"] < C.ABORT_REDUX_JOINED:
        raise SystemExit("Redux join placed only %d rows -- aborting" % rcounts["joined"])
    g = pm.groups(n_q, labels)
    base_err = len(g["miskey"]) + len(g["other_error"])
    base_judged = base_err + len(g["ok"])
    print("[base] miskey=%d other_error=%d ok=%d -> %d of %d judged carry an error label"
          % (len(g["miskey"]), len(g["other_error"]), len(g["ok"]), base_err, base_judged))

    S = pm.strata(acc, C.PANEL_SIZE, C.N_STRATA)
    if S is None:
        raise SystemExit("only %d included models; %d needed" % (len(acc), C.PANEL_SIZE * C.N_STRATA))
    ranked = pm.select_panel(acc, len(acc))

    # ----- S1 = audit 80's panel: the reproduction gate -----
    f1, t1 = pm.panel_flags(S[0], preds, h_questions, C.MIN_AGREE)
    flagged80 = {name: pm.n_flagged(g[name], f1) for name in C.EXPECTED_80["flagged"]}
    prec80 = pm.flag_precision(f1, g)
    repro80 = (n_q == C.EXPECTED_80["universe"] and len(acc) == C.EXPECTED_80["included"]
               and S[0] == C.EXPECTED_80["panel"] and flagged80 == C.EXPECTED_80["flagged"]
               and prec80 == C.EXPECTED_80["precision"])
    print("[repro80] flagged=%s precision=%s ok=%s" % (flagged80, prec80, repro80))
    K = pm.n_flagged(range(n_q), f1)

    # ----- Each stratum -----
    flags_by, score_by, st, strata_out = [], [], [], []
    for i, panel in enumerate(S):
        fl, tl = (f1, t1) if i == 0 else pm.panel_flags(panel, preds, h_questions, C.MIN_AGREE)
        sc = pm.margins(tl, h_questions)
        s = pm.stratum_stats(fl, sc, g, K)
        flags_by.append(fl)
        score_by.append(sc)
        st.append(s)
        row = {"stratum": "S%d" % (i + 1), "ranks": [10 * i + 1, 10 * i + 10], "mean_accuracy": mean_acc(acc, panel),
               "models": [{"model": m, "accuracy": float(pm.accuracy(*acc[m]))} for m in panel],
               "unreviewed_flags": pm.n_flagged(g["unreviewed"], fl)}
        row.update(pm.stats_json(s))
        strata_out.append(row)
        print("[stratum] %s" % {k: v for k, v in row.items() if k != "models"})

    # ----- The 20-model panel (ranks 1-20) -----
    top20 = ranked[:C.TOP20_SIZE]
    f20, t20 = pm.panel_flags(top20, preds, h_questions, C.TOP20_MIN_AGREE)
    s20 = pm.stratum_stats(f20, pm.margins(t20, h_questions), g, K)
    top20_out = {"ranks": [1, C.TOP20_SIZE], "min_agree": C.TOP20_MIN_AGREE, "mean_accuracy": mean_acc(acc, top20)}
    top20_out.update(pm.stats_json(s20))
    print("[top20] %s" % top20_out)

    verdicts = pm.predictions83(st, s20, base_err, base_judged, C.THRESHOLDS)
    p1_parts = {"fixtures": all(fx.values()), "reproduce_80": repro80}
    verdicts["P1_structural"] = all(p1_parts.values())
    verdicts["P1_counts"] = [n_q, len(acc), K]
    print("[P1] %s" % p1_parts)
    for name in sorted(v for v in verdicts if v.count("_") and not any(
            v.endswith(x) for x in ("_counts", "_auc", "_precision"))):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    print("[prediction] numbers %s" % {k: v for k, v in sorted(verdicts.items())
                                       if any(k.endswith(x) for x in ("_counts", "_auc", "_precision"))})

    # ----- Exploratory: sliding 10-model windows, overlaps, all-error AUC -----
    windows = []
    for start in C.WINDOW_STARTS:
        panel = ranked[start:start + C.PANEL_SIZE]
        if len(panel) < C.PANEL_SIZE:
            continue
        fl, tl = pm.panel_flags(panel, preds, h_questions, C.MIN_AGREE)
        row = {"ranks": [start + 1, start + C.PANEL_SIZE], "mean_accuracy": mean_acc(acc, panel)}
        row.update(pm.stats_json(pm.stratum_stats(fl, pm.margins(tl, h_questions), g, K)))
        windows.append(row)
    print("[windows] %s" % [(w["ranks"][0], round(w["mean_accuracy"], 4), w["flags"], w["auc_miskey_vs_ok"],
                             w["budget"]["precision"]) for w in windows])

    errs = g["miskey"] + g["other_error"]
    overlap = []
    s1_set = {q for q in range(n_q) if f1[q][0]}
    for i in range(1, len(S)):
        si = {q for q in range(n_q) if flags_by[i][q][0]}
        both = s1_set & si
        overlap.append({"stratum": "S%d" % (i + 1), "flags": len(si), "shared_with_S1": len(both),
                        "shared_miskeys": sum(1 for q in g["miskey"] if q in both),
                        "S1_miskeys_missed": sum(1 for q in g["miskey"] if q in s1_set and q not in si),
                        "new_miskeys": sum(1 for q in g["miskey"] if q in si and q not in s1_set)})
    any_err_auc = [{"stratum": "S%d" % (i + 1),
                    "auc_any_error_vs_ok": (lambda a: None if a is None else float(a))(
                        pm.auc([score_by[i][q] for q in errs], [score_by[i][q] for q in g["ok"]]))}
                   for i in range(len(S))]
    print("[overlap] %s" % overlap)
    print("[auc any error] %s" % any_err_auc)

    out = {
        "audit": 83,
        "slug": "mcq-mmlu-helm-panel-strength",
        "dataset": ("HELM MMLU release %s (Stanford CRFM, public GCS bucket crfm-helm-public/mmlu) and MMLU-Redux 2.0 "
                    "via the HF datasets-server parquet API. Only model names, accuracies, counts and hashes."
                    % C.HELM_RELEASE),
        "fixture": fx,
        "helm": {"release_sha256": H["release_sha256"], "universe": n_q, "universe_counts": H["universe_counts"],
                 "instances_failed": H["inst_fail"], "models": H["n_models"], "included": len(acc),
                 "flagged_S1": flagged80, "precision_S1": list(prec80), "reproduces_80": repro80},
        "redux": {"rows": len(redux), "join": rcounts, "key_agree": key_agree, "shards": redux_shards,
                  "groups": {k: len(v) for k, v in g.items()}, "base_error_labelled": base_err,
                  "base_judged": base_judged},
        "budget_K": K,
        "p1_parts": p1_parts,
        "predictions": verdicts,
        "strata": strata_out,
        "top20": top20_out,
        "windows_exploratory": windows,
        "overlap_with_S1_exploratory": overlap,
        "auc_any_error_exploratory": any_err_auc,
        "note": ("Strata: HELM's included models ranked by MMLU accuracy (ties by name), cut into disjoint panels of 10 "
                 "(S1 = ranks 1-10 = audit 80's panel ... S7 = ranks 61-70). flags = audit 77's rule (>= 6 of 10 on "
                 "one non-key option, more than on the key). precision = share of flagged Redux-judged questions (wrong "
                 "key, OK or another error label) with an error label. AUC: Redux miskeys vs Redux-OK by the panel's "
                 "margin (top non-key votes minus key votes). budget: the K questions with the highest margin, K = S1's "
                 "flag count, ties at the cut shared evenly (expected counts, exact fractions). P2 S7 flags more than "
                 "S1; P3 HEADLINE AUC S1 > S4 > S7; P4 budget precision S1 > S4 > S7; P5 S7 budget precision >= 2x "
                 "the base rate; P6 ranks 1-20 as one panel beats S1 at the same budget."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json")


if __name__ == "__main__":
    main()
