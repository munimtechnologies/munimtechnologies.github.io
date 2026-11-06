"""Is classical item discrimination a better MMLU miskey flag than the top-10 model consensus? (audit 82)

Rebuilds audit 80 (HELM MMLU release v1.13.0: 78 included models, the 10 most accurate as the consensus panel,
audit 77's flag, MMLU-Redux 2.0 labels), gated to reproduce its published counts. Then computes, for every question,
the item-rest correlation r across all 78 included models (does a model's accuracy on the other questions predict
picking this question's key?), flags the K questions with the most negative r (K = the consensus flag's count), and
compares the two flags against Redux's expert labels at equal budget and without a threshold (AUC).

Gates: the hand-traced fixtures must match before any download; the Redux join must place at least 4,000 rows.
Writes results.json (aggregates, verdicts, curves, per-subject counts) and discrimination_candidates.json (the K
questions with the most negative r: subject, HELM instance id and position, letters, r, vote counts, Redux status and
a 16-hex sha256 of the normalised question; no question, option or model text). Usage: python job.py --out-dir /out
(network required). Apache-2.0.
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

import disc82 as dm
import cases82 as C

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
                         "answer": int(a) if a is not None else None, "label": dm.label_of(et)})
    return rows, shards


def fixture_ok():
    idx = {m: {q: dm.pred_index(p, C.FIX_QUESTIONS[q][0]) for q, p in d.items()} for m, d in C.FIX_PREDS.items()}
    panel = dm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
    flags, _t = dm.panel_flags(panel, idx, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
    parsed = {s: dm.parse_instances(items) for s, items in C.FIX_INST.items()}
    qids, info, counts = dm.build_universe(parsed)
    t = C.FIX_UNIVERSE_TARGET
    preds_ok = all(dm.map_predictions(C.FIX_PRED[s], parsed[s], s, qids) == C.FIX_PRED_TARGET[s]
                   for s in ("virology", "anatomy"))
    rj = dm.redux_join(C.FIX_REDUX, qids, C.FIX_GOLD)
    r, n_models, n_key, dcounts = dm.discrimination(C.FIX_D_MODELS, C.FIX_D_PREDS, C.FIX_D_ACC, C.FIX_D_GOLD, 5)
    disc_ok = (len(r) == len(C.FIX_D_R) and all(abs(a - b) < 1e-12 for a, b in zip(r, C.FIX_D_R))
               and n_models == C.FIX_D_N_MODELS and n_key == C.FIX_D_N_KEY and dcounts == C.FIX_D_COUNTS
               and dm.rank_order(r) == C.FIX_D_ORDER and dm.rank_flags(r, 2) == C.FIX_D_RANK2
               and dm.neg_flags(r) == C.FIX_D_NEG)
    return {"panel_flags": panel == C.FIX_TARGET["panel"] and flags == C.FIX_TARGET["flags"],
            "runs": dm.select_runs(C.FIX_RUNS) == C.FIX_RUNS_TARGET,
            "universe": qids == t["qids"] and info == t["info"] and counts == t["counts"],
            "predictions": preds_ok,
            "redux_join": rj == C.FIX_REDUX_TARGET and dm.groups(3, rj[0]) == C.FIX_GROUPS_TARGET,
            "discrimination": disc_ok,
            "margin_auc": (all(dm.margin(c, k) == w for (c, k), w in C.FIX_MARGIN)
                           and all(dm.auc(p, n) == w for (p, n), w in C.FIX_AUC)),
            "verdicts": dm.predictions82(C.FIX_V_G, C.FIX_V_GX, C.FIX_V_CONS, C.FIX_V_BUDGET, C.FIX_V_NEG,
                                         C.FIX_V_SDISC, C.FIX_V_SCONS, C.THRESHOLDS) == C.FIX_VERDICTS}


def share(a, n):
    return float(Fraction(a, n)) if n else None


def letter(i):
    return None if i is None else dm.LETTERS[i]


def prec_dict(pair):
    e, j = pair
    return {"error_labelled": e, "judged": j, "share": share(e, j)}


def fauc(x):
    return None if x is None else float(x)


# ----- HELM: audit 80, rebuilt (copied from audit 81's job.py) -----

def build_helm():
    release_url = "%s/releases/%s/runs_to_run_suites.json" % (C.HELM_BASE, C.HELM_RELEASE)
    raw_release = _get(release_url)
    run_suites = json.loads(raw_release.decode("utf-8"))
    chosen, dups = dm.select_runs(run_suites)
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
            return key, dm.parse_instances(_json(run_url(suite, inst_src[key], "instances.json"))), None
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
        if s not in base_suite or dm.suite_version(suite) < dm.suite_version(base_suite[s]):
            base_suite[s] = suite
    qids, info, ucounts = dm.build_universe({s: instances[(base_suite[s], s)] for s in base_suite})
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
        out, c = dm.map_predictions(data, inst, s, qids)
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

    # ----- HELM panel and consensus flags (audit 80) -----
    H = build_helm()
    qids, info, n_q, gold_of = H["qids"], H["info"], H["n_q"], H["gold_of"]
    subj_of = [r[0] for r in info]
    h_questions = {q: (info[q][2], info[q][3]) for q in range(n_q)}
    redux, redux_shards = read_redux()
    labels, rcounts, key_agree = dm.redux_join(redux, qids, gold_of)
    print("[redux] rows=%d %s key_agree=%d" % (len(redux), rcounts, key_agree))
    if rcounts["joined"] < C.ABORT_REDUX_JOINED:
        raise SystemExit("Redux join placed only %d rows -- aborting" % rcounts["joined"])
    g = dm.groups(n_q, labels)
    panel = dm.select_panel(H["acc"], C.PANEL_SIZE)
    cons, tallies = dm.panel_flags(panel, H["preds"], h_questions, C.MIN_AGREE)
    flagged80 = {name: dm.n_flagged(g[name], cons) for name in C.EXPECTED_80["flagged"]}
    prec80 = dm.flag_precision(cons, g)
    repro80 = (n_q == C.EXPECTED_80["universe"] and len(H["acc"]) == C.EXPECTED_80["included"]
               and panel == C.EXPECTED_80["panel"] and flagged80 == C.EXPECTED_80["flagged"]
               and prec80 == C.EXPECTED_80["precision"])
    print("[repro80] flagged=%s precision=%s ok=%s" % (flagged80, prec80, repro80))

    # ----- Item-rest discrimination over all included models -----
    models = sorted(H["acc"])
    r, n_models, n_key, dcounts = dm.discrimination(models, H["preds"], H["acc"], gold_of, n_q)
    print("[discrimination] models=%d %s" % (len(models), dcounts))
    K = dm.n_flagged(range(n_q), cons)
    budget = dm.rank_flags(r, K)
    neg = dm.neg_flags(r)
    s_disc = {q: -r[q] for q in range(n_q)}
    s_cons = {q: dm.margin(tallies[q][0], h_questions[q][1]) for q in range(n_q)}

    gx = dm.restrict(g, {q for q in range(n_q) if subj_of[q] != "virology"})
    verdicts = dm.predictions82(g, gx, cons, budget, neg, s_disc, s_cons, C.THRESHOLDS)
    p1_parts = {"fixtures": all(fx.values()), "reproduce_80": repro80}
    verdicts["P1_structural"] = all(p1_parts.values())
    verdicts["P1_counts"] = [n_q, len(H["acc"]), K]
    print("[P1] %s" % p1_parts)
    for name in sorted(v for v in verdicts if not (v.endswith("_counts") or v.endswith("_auc"))):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    print("[prediction] counts %s" % {k: v for k, v in sorted(verdicts.items())
                                      if k.endswith("_counts") or k.endswith("_auc")})

    # ----- Exploratory -----
    by_group = {}
    for name in ("all", "miskey", "ok", "other_error", "unsure_or_conflict", "unreviewed"):
        ids = g[name]
        by_group[name] = {"n": len(ids), "consensus": dm.n_flagged(ids, cons), "budget": dm.n_flagged(ids, budget),
                          "neg": dm.n_flagged(ids, neg), "both": dm.n_flagged(ids, dm.both(cons, budget)),
                          "all_wrong": sum(1 for q in ids if n_models[q] >= 2 and n_key[q] == 0)}
        print("[group] %s %s" % (name, by_group[name]))

    errs = g["miskey"] + g["other_error"]
    aucs = {
        "miskey_vs_ok": {"discrimination": fauc(dm.auc([s_disc[q] for q in g["miskey"]], [s_disc[q] for q in g["ok"]])),
                         "consensus_margin": fauc(dm.auc([s_cons[q] for q in g["miskey"]],
                                                         [s_cons[q] for q in g["ok"]]))},
        "any_error_vs_ok": {"discrimination": fauc(dm.auc([s_disc[q] for q in errs], [s_disc[q] for q in g["ok"]])),
                            "consensus_margin": fauc(dm.auc([s_cons[q] for q in errs],
                                                            [s_cons[q] for q in g["ok"]]))},
        "miskey_vs_ok_no_virology": {
            "discrimination": fauc(dm.auc([s_disc[q] for q in gx["miskey"]], [s_disc[q] for q in gx["ok"]])),
            "consensus_margin": fauc(dm.auc([s_cons[q] for q in gx["miskey"]], [s_cons[q] for q in gx["ok"]]))},
    }
    print("[auc] %s" % aucs)

    disc_order = dm.rank_order(r)
    cons_order = sorted(range(n_q), key=lambda q: (-s_cons[q], q))
    curve = []
    for b in sorted(set(C.CURVE_BUDGETS + [K])):
        fd = {q: (False, None) for q in range(n_q)}
        fc = {q: (False, None) for q in range(n_q)}
        for q in disc_order[:b]:
            fd[q] = (True, None)
        for q in cons_order[:b]:
            fc[q] = (True, None)
        curve.append({"budget": b, "discrimination": prec_dict(dm.flag_precision(fd, g)),
                      "discrimination_miskeys": dm.n_flagged(g["miskey"], fd),
                      "consensus_margin": prec_dict(dm.flag_precision(fc, g)),
                      "consensus_margin_miskeys": dm.n_flagged(g["miskey"], fc)})
    print("[curve] %s" % curve)

    precision = {"consensus": prec_dict(dm.flag_precision(cons, g)), "budget": prec_dict(dm.flag_precision(budget, g)),
                 "neg": prec_dict(dm.flag_precision(neg, g)),
                 "both": prec_dict(dm.flag_precision(dm.both(cons, budget), g)),
                 "consensus_only": prec_dict(dm.flag_precision(
                     {q: (cons[q][0] and not budget[q][0], None) for q in range(n_q)}, g)),
                 "budget_only": prec_dict(dm.flag_precision(
                     {q: (budget[q][0] and not cons[q][0], None) for q in range(n_q)}, g)),
                 "no_virology": {"consensus": prec_dict(dm.flag_precision(cons, gx)),
                                 "budget": prec_dict(dm.flag_precision(budget, gx))}}
    print("[precision] %s" % precision)

    by_subject = {}
    for s in sorted(set(subj_of)):
        ids = [q for q in range(n_q) if subj_of[q] == s]
        gs = dm.restrict(g, set(ids))
        by_subject[s] = {"n": len(ids), "consensus": dm.n_flagged(ids, cons), "budget": dm.n_flagged(ids, budget),
                         "neg": dm.n_flagged(ids, neg), "miskeys": len(gs["miskey"]),
                         "consensus_precision": list(dm.flag_precision(cons, gs)),
                         "budget_precision": list(dm.flag_precision(budget, gs)),
                         "budget_unreviewed": dm.n_flagged(gs["unreviewed"], budget)}

    qtext = [None] * n_q
    for key, q in qids.items():
        qtext[q] = key[1][0]
    candidates = []
    for rank, q in enumerate(disc_order[:K]):
        s, iid, k, gold, pos = info[q]
        counts, none = tallies[q]
        fc, ci = cons[q]
        candidates.append({"rank": rank + 1, "subject": s, "helm_instance_id": iid, "helm_test_position": pos,
                           "helm_key": letter(gold), "r": round(r[q], 4), "n_models": n_models[q],
                           "n_models_picking_key": n_key[q], "consensus_flag": bool(fc),
                           "consensus_letter": letter(ci) if fc else None,
                           "top10_votes": counts, "top10_no_answer": none,
                           "redux": labels.get(q, "not_in_redux_sample"),
                           "question_sha256_16": dm.question_hash(qtext[q])})

    out = {
        "audit": 82,
        "slug": "mcq-mmlu-helm-discrimination-miskeys",
        "dataset": ("HELM MMLU release %s (Stanford CRFM, public GCS bucket crfm-helm-public/mmlu) and MMLU-Redux 2.0 "
                    "via the HF datasets-server parquet API. Only ids, letters, counts and hashes." % C.HELM_RELEASE),
        "fixture": fx,
        "helm": {"release_sha256": H["release_sha256"], "universe": n_q, "universe_counts": H["universe_counts"],
                 "instances_failed": H["inst_fail"], "models": H["n_models"], "included": len(H["acc"]),
                 "panel": [{"model": m, "accuracy": float(dm.accuracy(*H["acc"][m]))} for m in panel],
                 "flagged": flagged80, "precision": list(prec80), "reproduces_80": repro80},
        "redux": {"rows": len(redux), "join": rcounts, "key_agree": key_agree, "shards": redux_shards},
        "discrimination": {"models": len(models), "counts": dcounts, "budget_K": K,
                           "r_at_budget": round(r[disc_order[K - 1]], 6) if K else None},
        "p1_parts": p1_parts,
        "predictions": verdicts,
        "by_group": by_group,
        "auc": aucs,
        "precision": precision,
        "curve": curve,
        "by_subject_exploratory": by_subject,
        "n_candidates": len(candidates),
        "note": ("r = item-rest correlation across HELM's included models (picked the key 0/1 vs accuracy on the "
                 "model's other questions); every model right -> +1, none -> -1. consensus = audit 80's flag (>= 6 of "
                 "the 10 most accurate models on one non-key option, more than on the key); budget = the K questions "
                 "with the most negative r, K = the consensus flag's count; neg = r < 0. Precision = share of flagged "
                 "Redux-judged questions (wrong key, OK or another error label) with an error label. AUC: Redux "
                 "miskeys vs Redux-OK, scores -r and the consensus margin (top non-key votes minus key votes). P1 "
                 "structural; P2 r < 0 rate on miskeys >= 5x on OK; P3 HEADLINE budget precision > consensus; P4 AUC "
                 "-r > AUC margin; P5 both flags together more precise than each; P6 P3 without virology."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "discrimination_candidates.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 82, "note": ("Model-flagged, NOT expert-checked: the MMLU questions (HELM release v1.13.0) "
                   "whose item-rest correlation r across HELM's included models is most negative, i.e. where stronger "
                   "models pick the key less often than weaker ones. top10_votes = votes of the 10 most accurate models "
                   "per option (A-D). Each may hold a wrong key, a second defensible answer or a mistake strong models "
                   "share."), "candidates": candidates}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and discrimination_candidates.json (%d candidates)" % len(candidates))


if __name__ == "__main__":
    main()
