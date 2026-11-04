"""Does audit 77's model-consensus miskey flag replicate on MMLU with HELM's models? (audit 80)

Reads Stanford CRFM's public HELM MMLU release (runs_to_run_suites.json, then each run's instances.json and
display_predictions.json), builds one question universe from the earliest suite per subject, maps every model's
answers onto it, keeps models with full coverage whose answers reproduce HELM's own exact_match, picks the 10 most
accurate, applies audit 77's flag (at least 6 of 10 agree on one non-key option, and more than pick the key), and
scores the flag against all 5,700 MMLU-Redux 2.0 expert labels.

Gates: the hand-traced fixtures must match before any download; the Redux join must place at least 4,000 rows or the
job aborts. Writes results.json (aggregates, panel, curve, per-subject counts, per-model inclusion) and
candidates.json (every flagged question: subject, HELM instance id, position, letters, votes, Redux status and a
16-hex sha256 of the normalised question; no question, option or model text). Usage: python job.py --out-dir /out
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

import helm80 as hm
import cases80 as C

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
                         "answer": int(a) if a is not None else None, "label": hm.label_of(et)})
    return rows, shards


def fixture_ok():
    idx = {m: {q: hm.pred_index(p, C.FIX_QUESTIONS[q][0]) for q, p in d.items()} for m, d in C.FIX_PREDS.items()}
    panel = hm.select_panel(C.FIX_ACC, C.FIX_PANEL_SIZE)
    flags, _t = hm.panel_flags(panel, idx, C.FIX_QUESTIONS, C.FIX_MIN_AGREE)
    parsed = {s: hm.parse_instances(items) for s, items in C.FIX_INST.items()}
    qids, info, counts = hm.build_universe(parsed)
    t = C.FIX_UNIVERSE_TARGET
    preds_ok = all(hm.map_predictions(C.FIX_PRED[s], parsed[s], s, qids) == C.FIX_PRED_TARGET[s]
                   for s in ("virology", "anatomy"))
    rj = hm.redux_join(C.FIX_REDUX, qids, C.FIX_GOLD)
    return {"panel_flags": panel == C.FIX_TARGET["panel"] and flags == C.FIX_TARGET["flags"],
            "runs": hm.select_runs(C.FIX_RUNS) == C.FIX_RUNS_TARGET,
            "universe": qids == t["qids"] and info == t["info"] and counts == t["counts"],
            "predictions": preds_ok,
            "redux_join": rj == C.FIX_REDUX_TARGET and hm.groups(3, rj[0]) == C.FIX_GROUPS_TARGET,
            "verdicts": hm.predictions80(C.FIX_G, C.FIX_FLAGS, C.FIX_CURVE, C.THRESHOLDS) == C.FIX_VERDICTS}


def share(a, n):
    return float(Fraction(a, n)) if n else None


def letter(i):
    return None if i is None else hm.LETTERS[i]


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

    # ----- Runs -----
    release_url = "%s/releases/%s/runs_to_run_suites.json" % (C.HELM_BASE, C.HELM_RELEASE)
    raw_release = _get(release_url)
    run_suites = json.loads(raw_release.decode("utf-8"))
    chosen, dups = hm.select_runs(run_suites)
    models = sorted({m for m, _s in chosen})
    subjects = sorted({s for _m, s in chosen})
    print("[runs] release entries=%d chosen=%d duplicates_dropped=%d models=%d subjects=%d"
          % (len(run_suites), len(chosen), dups, len(models), len(subjects)))
    if len(subjects) != C.N_SUBJECTS:
        print("[runs] WARNING subject count %d != %d" % (len(subjects), C.N_SUBJECTS))

    # ----- Instances: one file per (suite, subject), from the alphabetically first model's run -----
    inst_src = {}
    for (m, s), (run, suite) in sorted(chosen.items()):
        inst_src.setdefault((suite, s), run)
    inst_keys = sorted(inst_src)

    def fetch_inst(key):
        suite, s = key
        try:
            return key, hm.parse_instances(_json(run_url(suite, inst_src[key], "instances.json"))), None
        except Exception as e:  # noqa: BLE001 - recorded, never patched
            return key, None, str(e)[:200]

    instances, inst_fail = {}, []
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        for key, parsed, err in ex.map(fetch_inst, inst_keys):
            if parsed is None:
                inst_fail.append({"suite": key[0], "subject": key[1], "error": err})
            else:
                instances[key] = parsed
    print("[instances] files=%d failed=%d" % (len(instances), len(inst_fail)))

    base_suite = {}
    for suite, s in instances:
        if s not in base_suite or hm.suite_version(suite) < hm.suite_version(base_suite[s]):
            base_suite[s] = suite
    qids, info, ucounts = hm.build_universe({s: instances[(base_suite[s], s)] for s in base_suite})
    n_q = len(info)
    gold_of = [r[3] for r in info]
    questions = {q: (info[q][2], info[q][3]) for q in range(n_q)}
    subj_of = [r[0] for r in info]
    print("[universe] questions=%d %s base_suites=%s" % (n_q, ucounts, sorted(set(base_suite.values()))))

    # ----- Predictions -----
    jobs = sorted(chosen.items())

    def fetch_pred(item):
        (m, s), (run, suite) = item
        inst = instances.get((suite, s))
        if inst is None:
            return m, s, None, {"error": "no instances for suite"}
        try:
            data = _json(run_url(suite, run, "display_predictions.json"))
        except Exception as e:  # noqa: BLE001
            return m, s, None, {"error": str(e)[:200]}
        out, c = hm.map_predictions(data, inst, s, qids)
        return m, s, out, c

    preds, stats = {m: {} for m in models}, {m: {} for m in models}
    with ThreadPoolExecutor(max_workers=C.WORKERS) as ex:
        for m, s, out, c in ex.map(fetch_pred, jobs):
            stats[m][s] = c
            if out is not None:
                preds[m].update(out)
    print("[predictions] runs=%d" % len(jobs))

    # ----- Inclusion -----
    acc, inclusion = {}, {}
    for m in models:
        ss = stats[m]
        tot = {k: sum(v.get(k, 0) for v in ss.values() if "error" not in v)
               for k in ("n", "valid", "from_mapped", "invalid", "consistent", "inconsistent", "em_correct")}
        n_subj = sum(1 for v in ss.values() if "error" not in v)
        covered = len(preds[m])
        correct = sum(1 for q, i in preds[m].items() if i is not None and i == gold_of[q])
        mapped_items = tot["valid"] + tot["from_mapped"] + tot["invalid"]
        checked = tot["consistent"] + tot["inconsistent"]
        cons = Fraction(tot["consistent"], checked) if checked else Fraction(1)
        em_gap = abs(Fraction(correct - tot["em_correct"], mapped_items)) if mapped_items else Fraction(1)
        ok = (n_subj == C.N_SUBJECTS and n_q and Fraction(covered, n_q) >= C.MIN_COVERAGE
              and cons >= C.MIN_CONSISTENT and em_gap <= C.MAX_EM_GAP)
        inclusion[m] = {"subjects": n_subj, "covered": covered, "correct": correct, "accuracy": share(correct, covered),
                        "helm_em_correct": tot["em_correct"], "em_gap": float(em_gap), "consistent_share": float(cons),
                        "from_mapped": tot["from_mapped"], "invalid": tot["invalid"],
                        "errors": sorted(s for s, v in ss.items() if "error" in v),
                        "included": bool(ok)}
        if ok:
            acc[m] = (correct, covered)
    included = sorted(acc)
    print("[inclusion] included=%d of %d" % (len(included), len(models)))

    # ----- Redux -----
    redux, redux_shards = read_redux()
    n_redux_miskey = sum(1 for r in redux if r["label"] == hm.MISKEY)
    labels, rcounts, key_agree = hm.redux_join(redux, qids, gold_of)
    print("[redux] rows=%d miskey_rows=%d %s key_agree=%d" % (len(redux), n_redux_miskey, rcounts, key_agree))
    if rcounts["joined"] < C.ABORT_REDUX_JOINED:
        raise SystemExit("Redux join placed only %d rows -- aborting" % rcounts["joined"])
    g = hm.groups(n_q, labels)

    # ----- Panel, flag, curve -----
    panel = hm.select_panel(acc, C.PANEL_SIZE)
    print("[panel] %s" % [(m, round(float(hm.accuracy(*acc[m])), 4)) for m in panel])
    flags, tallies = hm.panel_flags(panel, preds, questions, C.MIN_AGREE)
    curve, curve_prec = [], {}
    for mm in range(4, 11):
        fl = {q: hm.flag_question(tallies[q][0], questions[q][1], mm)[:2] for q in tallies}
        e, j = hm.flag_precision(fl, g)
        curve_prec[mm] = (e, j)
        row = {"min_agree": mm, "flagged": hm.n_flagged(g["all"], fl), "miskey": hm.n_flagged(g["miskey"], fl),
               "ok": hm.n_flagged(g["ok"], fl), "other_error": hm.n_flagged(g["other_error"], fl),
               "error_labelled": e, "judged": j, "unreviewed": hm.n_flagged(g["unreviewed"], fl)}
        curve.append(row)
        print("[curve] %s" % row)

    verdicts = hm.predictions80(g, flags, curve_prec, C.THRESHOLDS)
    p1_parts = {
        "fixtures": all(fx.values()),
        "subjects": len(subjects) == C.N_SUBJECTS and len(base_suite) == C.N_SUBJECTS,
        "universe": n_q >= C.MIN_UNIVERSE,
        "redux_rows": len(redux) == C.N_REDUX_ROWS and n_redux_miskey == C.N_REDUX_MISKEY_ROWS,
        "redux_joined": rcounts["joined"] >= C.MIN_REDUX_JOINED,
        "key_agree": bool(rcounts["joined"]) and Fraction(key_agree, rcounts["joined"]) >= C.MIN_KEY_AGREE,
        "models": len(included) >= C.MIN_INCLUDED_MODELS,
    }
    verdicts["P1_structural"] = all(p1_parts.values())
    verdicts["P1_counts"] = [len(subjects), n_q, len(redux), n_redux_miskey, rcounts["joined"], key_agree,
                             len(included)]
    print("[P1] %s" % p1_parts)
    for name in sorted(v for v in verdicts if not v.endswith("_counts")):
        print("[prediction] %s = %s" % (name, "HELD" if verdicts[name] else "FAILED"))
    print("[prediction] counts %s" % {k: v for k, v in sorted(verdicts.items()) if k.endswith("_counts")})

    # ----- Exploratory -----
    by_group = {}
    for name in ("all", "miskey", "ok", "other_error", "unsure_or_conflict", "unreviewed"):
        f = hm.n_flagged(g[name], flags)
        by_group[name] = {"n": len(g[name]), "flagged": f, "rate": share(f, len(g[name]))}
        print("[group] %s %s" % (name, by_group[name]))
    e, j = hm.flag_precision(flags, g)
    precision = {"error_labelled": e, "judged": j, "share": share(e, j)}
    print("[precision] %s" % precision)

    by_subject = {}
    for s in subjects:
        ids = [q for q in range(n_q) if subj_of[q] == s]
        rev = [q for q in ids if q in labels]
        mk = [q for q in ids if labels.get(q) == hm.MISKEY]
        by_subject[s] = {"n": len(ids), "flagged": hm.n_flagged(ids, flags), "redux_joined": len(rev),
                         "redux_flagged": hm.n_flagged(rev, flags), "miskey": len(mk),
                         "miskey_flagged": hm.n_flagged(mk, flags),
                         "unreviewed_flagged": hm.n_flagged([q for q in ids if q not in labels], flags)}

    qtext = [None] * n_q
    for key, q in qids.items():
        qtext[q] = key[1][0]
    candidates = []
    for q in range(n_q):
        f, ci = flags[q]
        if not f:
            continue
        s, iid, k, gold, pos = info[q]
        counts, none = tallies[q]
        candidates.append({"subject": s, "helm_instance_id": iid, "helm_test_position": pos, "k": k,
                           "key": letter(gold), "consensus": letter(ci),
                           "votes": [counts[ci], counts[gold], none],
                           "redux": labels.get(q, "not_in_redux_sample"),
                           "question_sha256_16": hm.question_hash(qtext[q])})

    out = {
        "audit": 80,
        "slug": "mcq-mmlu-helm-consensus-miskeys",
        "dataset": ("HELM MMLU release %s (Stanford CRFM, public GCS bucket crfm-helm-public/mmlu): "
                    "runs_to_run_suites.json, per-run instances.json and display_predictions.json; MMLU-Redux 2.0 via "
                    "the HF datasets-server parquet API. Only ids, letters, counts and hashes." % C.HELM_RELEASE),
        "fixture": fx,
        "release": {"url": release_url, "sha256": hashlib.sha256(raw_release).hexdigest(),
                    "entries": len(run_suites), "chosen_runs": len(chosen), "duplicates_dropped": dups,
                    "models": len(models), "subjects": len(subjects)},
        "instances": {"files": len(instances), "failed": inst_fail, "base_suites": base_suite,
                      "universe": n_q, "universe_counts": ucounts},
        "redux": {"rows": len(redux), "miskey_rows": n_redux_miskey, "join": rcounts, "key_agree": key_agree,
                  "shards": redux_shards},
        "inclusion": inclusion,
        "panel": [{"model": m, "accuracy": float(hm.accuracy(*acc[m])), "correct": acc[m][0], "covered": acc[m][1]}
                  for m in panel],
        "p1_parts": p1_parts,
        "predictions": verdicts,
        "by_group": by_group,
        "precision": precision,
        "curve_exploratory": curve,
        "by_subject_exploratory": by_subject,
        "n_candidates": len(candidates),
        "note": ("Flag (audit 77's rule): at least 6 of the 10 most accurate included HELM models pick one non-key "
                 "option and more of them pick it than the key. Precision = share of flagged Redux-judged questions "
                 "(wrong key, OK or another error label) that carry an error label. P1 structural; P2 miskey flag "
                 "rate >= 5x OK rate; P3 >= half the joined miskeys flagged; P4 HEADLINE precision > 65/359; P5 "
                 "other-error flag rate >= 2x OK rate; P6 precision at 10 of 10 > at 6 of 10."),
    }
    with open(os.path.join(args.out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    with open(os.path.join(args.out_dir, "candidates.json"), "w", encoding="utf-8") as fh:
        json.dump({"audit": 80, "note": ("Model-flagged, NOT expert-checked: MMLU test questions where at least 6 of "
                   "the 10 most accurate HELM models agree on one option other than the key. votes = [consensus, "
                   "key, no valid answer] out of 10. helm_test_position = 0-based rank of the instance id among the "
                   "subject's HELM test instances. Each may hold a wrong key, a second defensible answer or a shared "
                   "model mistake."), "candidates": candidates}, fh, indent=1, ensure_ascii=True)
    print("[done] wrote results.json and candidates.json (%d candidates)" % len(candidates))


if __name__ == "__main__":
    main()
