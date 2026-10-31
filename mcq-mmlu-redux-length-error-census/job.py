"""MMLU-Redux LENGTH x ANNOTATION-ERROR census (audit 69): does the length cue point to the expert-corrected answer?

MMLU-Redux 2.0 (Gema et al. 2024, arXiv 2406.04127; CC BY 4.0) gives expert error labels for 100 questions from each
of MMLU's 57 subjects and, for miskeyed ones, the answer the experts think is right. Its paper builds synthetic
wrong-ground-truth errors by picking a random wrong option and reports no length analysis. Audits 52/60 found a
small pick-longest shortcut in MMLU (0.2805 vs 0.25). This job measures, on the same released rows:

1. the length floor per error label and on the expert-OK subset;
2. on miskeyed questions, pick-longest credit and length rank of the published key vs the corrected key (paired);
3. whether question-free length flags pick out miskeyed questions (pooled 2x2 and subject-stratified CMH).

Six predictions were written down (below) before any real number was seen. Only aggregates are written out: no
question, option or suggested-answer text.

Usage: python job.py --out-dir /out   (network: HF datasets-server parquet API and the mcq-length-floor release)
Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import argparse
import hashlib
import importlib.util
import io
import json
import os
import urllib.request

import pyarrow.parquet as pq

import cases
import redux_length as rl

UA = {"User-Agent": "mv2-eval-reliability-audits/1.0 (research; contact mv2@munimtech.com)"}
PARQUET_API = "https://datasets-server.huggingface.co/parquet?dataset=%s"


def _get(url, tries=4):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry transient network errors
            last = e
    raise RuntimeError("GET failed after %d tries: %s (%s)" % (tries, url, last))


def load_redux():
    """Rows as dicts (subject, options, key, label, correct), the parquet shard sha256s and columns seen."""
    data = json.loads(_get(PARQUET_API % cases.HF_DATASET).decode("utf-8"))
    files = sorted((f["config"], f["url"]) for f in data["parquet_files"] if f["split"] == cases.SPLIT)
    rows, shards, missing = [], [], {}
    for config, url in files:
        raw = _get(url)
        shards.append({"config": config, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        t = pq.read_table(io.BytesIO(raw))
        cols = {c: t.column(c).to_pylist() for c in ("choices", "answer", "error_type", "correct_answer")
                if c in t.column_names}
        for c in ("choices", "answer", "error_type", "correct_answer"):
            if c not in cols:
                missing[c] = missing.get(c, 0) + 1
                cols[c] = [None] * t.num_rows
        for ch, ans, et, ca in zip(cols["choices"], cols["answer"], cols["error_type"], cols["correct_answer"]):
            rows.append({"subject": config, "options": list(ch) if ch is not None else None,
                         "key": int(ans) if ans is not None else None, "label": rl.normalise_label(et),
                         "correct": ca})
    return rows, shards, missing


def fixture_summary(rows):
    c = rl.census(rows)
    p, why = rl.miskey_pairs(rows)
    s = rl.paired(p)
    p0, _ = rl.miskey_pairs(rows, digit_base=0)
    s0 = rl.paired(p0)
    _p1, why1 = rl.miskey_pairs(rows, digit_base=1)
    out = {"n_rows": c["n_rows"], "n_invalid": c["n_invalid"], "labels": c["labels"]}
    for k in ("ALL", "class=ok", "class=error", "class=unsure", "label=wrong_groundtruth", "ok|subject=S1"):
        out[k] = rl.exact(c["accs"][k])
    out["pairs_digits_unresolved"] = (s["n"], s["d"], s["dr"])
    out["pairs_digits_0_based"] = (s0["n"], s0["d"], s0["dr"])
    out["why_digits_unresolved"] = why
    out["why_digits_1_based"] = why1
    out["detector_key_shortest_vs_miskey"] = rl.detector(rows, rl.flag_key_unique_shortest,
                                                         (rl.MISKEY,))["pooled"]["table"]
    out["detector_other_longest_vs_miskey"] = rl.detector(rows, rl.flag_other_unique_longest,
                                                          (rl.MISKEY,))["pooled"]["table"]
    out["detector_other_longest_vs_any_error"] = rl.detector(rows, rl.flag_other_unique_longest,
                                                             rl.ERROR_TYPES)["pooled"]["table"]
    return out


def tool_check(rows, out_dir, mine):
    """Re-run the ALL slice with the published mcq-length-floor 0.1.0 and compare with this module."""
    try:
        raw = _get(cases.TOOL_URL)
    except RuntimeError as e:
        return {"status": "unavailable", "error": str(e)}
    path = os.path.join(out_dir, "_tool_mcq_length_floor.py")
    with open(path, "wb") as fh:
        fh.write(raw)
    spec = importlib.util.spec_from_file_location("mcq_length_floor_v010", path)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    recs = [{"choices": r["options"], "answer": r["key"]} for r in rows if rl.is_valid(r["options"], r["key"])]
    reports, skipped = tool.census(recs, options_col="choices", answer_col="answer")
    os.remove(path)
    t = reports.get("ALL", {})
    keys = ("n", "chance", "pick_longest", "pick_shortest", "lift")
    agree = all(t.get(k) == mine.get(k) for k in keys) and not skipped
    return {"status": "agree" if agree else "MISMATCH", "tool_version": getattr(tool, "__version__", None),
            "tool_sha256": hashlib.sha256(raw).hexdigest(), "tool_all": {k: t.get(k) for k in keys},
            "tool_skipped": skipped}


def predictions(c, floors, mk, detectors):
    """Pre-registered, each a finding either way; decided before any real number was seen."""
    # P1 (structural): 57 subjects, 5,700 rows, 0 invalid, label histogram identical to audit 58's.
    p1 = (len(c["subjects"]) == cases.EXPECTED_N_SUBJECTS and c["n_rows"] == cases.EXPECTED_N_ROWS
          and c["n_invalid"] == 0 and c["labels"] == cases.EXPECTED_LABELS)
    # P2: on the expert-OK subset the pick-longest floor is above chance: lift > 0 and z > 3.29.
    ok = floors["class=ok"]
    p2 = ok["lift"] > 0 and ok["z"] is not None and ok["z"] > rl.Z_CRIT_0001
    # P3: scored against the PUBLISHED key, miskeyed questions carry a smaller pick-longest lift than OK ones.
    wg = floors.get("label=wrong_groundtruth", {"n": 0})
    p3 = wg["n"] > 0 and wg["lift"] < ok["lift"]
    # P4 (HEADLINE): on miskeyed questions with one usable corrected answer (letters or exact text), pick-longest
    # credit is higher against the corrected key than against the published key (mean paired difference > 0;
    # direction only; vacuous below P4_MIN_N pairs).
    m = mk["primary"]
    p4_vac = m["n"] < cases.P4_MIN_N
    p4 = (not p4_vac) and m["mean_diff"] > 0
    # P5: "the key is the unique shortest option" enriches for miskeyed questions among judged ones: pooled risk
    # ratio > 1 AND subject-stratified CMH direction positive.
    d = detectors["key_is_unique_shortest|wrong_groundtruth"]
    rr = d["pooled"]["risk_ratio"]
    p5 = rr is not None and rr > 1 and d["by_subject_cmh"]["sum_observed_minus_expected"] > 0
    # P6: dropping the non-OK rows moves the pooled floor by less than half a point.
    shift = ok["pick_longest"] - floors["ALL"]["pick_longest"]
    p6 = abs(shift) < cases.P6_MAX_SHIFT
    return {
        "P1_structural_gate": bool(p1),
        "P2_ok_subset_floor_above_chance": bool(p2),
        "P3_miskeyed_smaller_lift_vs_published_key": bool(p3),
        "P4_length_cue_points_to_corrected_key": bool(p4),
        "P4_vacuous": bool(p4_vac),
        "P5_key_shortest_flags_miskeys": bool(p5),
        "P6_cleanup_moves_floor_under_half_point": bool(p6),
        "P6_shift": shift,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)  # unused; data fetched over the network
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1) Hand-traced fixture: exact equality before any real data is read.
    fx = fixture_summary(cases.FIXTURE_ROWS)
    fx_ok = fx == cases.FIXTURE_TARGET
    print("[fixture] == FIXTURE_TARGET : %s" % fx_ok)
    if not fx_ok:
        for k in cases.FIXTURE_TARGET:
            if fx.get(k) != cases.FIXTURE_TARGET[k]:
                print("[fixture-diff] %s got %r want %r" % (k, fx.get(k), cases.FIXTURE_TARGET[k]))
        raise SystemExit("fixture mismatch -- aborting before real data")

    # 2) Real data and the structural gate.
    rows, shards, missing = load_redux()
    c = rl.census(rows)
    print("[load] subjects=%d rows=%d invalid=%d missing_columns=%s" % (len(c["subjects"]), c["n_rows"],
                                                                        c["n_invalid"], missing))
    print("[labels] %s" % dict(sorted(c["labels"].items())))
    gate = (len(c["subjects"]) == cases.EXPECTED_N_SUBJECTS and c["n_rows"] == cases.EXPECTED_N_ROWS
            and c["labels"] == cases.EXPECTED_LABELS)
    print("[gate] matches audit 58: %s" % gate)

    floors = {s: rl.floor_report(a) for s, a in sorted(c["accs"].items())}
    for s, r in floors.items():
        if not s.startswith("ok|"):
            print("[floor] %-34s n=%5d chance=%.4f longest=%.4f shortest=%.4f lift=%+.4f z=%s"
                  % (s, r["n"], r["chance"], r["pick_longest"], r["pick_shortest"], r["lift"],
                     "%.2f" % r["z"] if r["z"] is not None else "-"))

    tc = tool_check(rows, args.out_dir, floors["ALL"])
    print("[tool] %s %s" % (tc["status"], tc.get("tool_all")))
    if tc["status"] == "MISMATCH":
        raise SystemExit("mcq-length-floor 0.1.0 disagrees with this module on ALL -- aborting")

    formats = rl.correction_formats(rows)
    print("[formats] %s" % formats)

    mk, why = {}, {}
    variants = {"primary": {}, "digits_0_based": {"digit_base": 0}, "digits_1_based": {"digit_base": 1},
                "primary_without_virology": {"exclude_subjects": ("virology",)}}
    for name, kw in variants.items():
        pairs, w = rl.miskey_pairs(rows, **kw)
        mk[name] = rl.paired_report(rl.paired(pairs))
        why[name] = w
        r = mk[name]
        if r["n"]:
            print("[miskey] %-26s n=%3d PL published=%.4f corrected=%.4f diff=%+.4f z=%s | rank %.4f -> %.4f "
                  "| unique-longest %d -> %d | unique-shortest %d -> %d | left out %s"
                  % (name, r["n"], r["pick_longest_vs_published_key"], r["pick_longest_vs_corrected_key"],
                     r["mean_diff"], "%.2f" % r["diff_z"] if r["diff_z"] is not None else "-",
                     r["length_rank_published_key"], r["length_rank_corrected_key"],
                     r["published_key_unique_longest"], r["corrected_key_unique_longest"],
                     r["published_key_unique_shortest"], r["corrected_key_unique_shortest"], w))
        else:
            print("[miskey] %-26s n=0 left out %s" % (name, w))

    detectors = {}
    for fname, flag in rl.FLAGS.items():
        for tname, targets in (("wrong_groundtruth", (rl.MISKEY,)), ("any_error", rl.ERROR_TYPES)):
            d = rl.detector(rows, flag, targets)
            detectors["%s|%s" % (fname, tname)] = d
            p, h = d["pooled"], d["by_subject_cmh"]
            print("[detector] %-34s vs %-17s table=%s rate flagged=%s unflagged=%s RR=%s chi2=%s | CMH=%s O-E=%s "
                  "MH-OR=%s" % (fname, tname, p["table"], p["rate_1"], p["rate_2"], p["risk_ratio"],
                                p["chi_square_stat"], h["cmh_stat"], h["sum_observed_minus_expected"],
                                h["mh_odds_ratio"]))

    wg_by_subject = {}
    for r in rows:
        if r["label"] == rl.MISKEY:
            wg_by_subject[r["subject"]] = wg_by_subject.get(r["subject"], 0) + 1
    print("[miskeyed-by-subject] %s" % dict(sorted(wg_by_subject.items(), key=lambda kv: -kv[1])))

    preds = predictions(c, floors, mk, detectors)
    for k, v in preds.items():
        if k.startswith("P") and not k.endswith(("_vacuous", "_shift")):
            print("[prediction] %s = %s" % (k, "HELD" if v else "FAILED"))
    print("[prediction] P4_vacuous = %s ; P6_shift = %+.5f" % (preds["P4_vacuous"], preds["P6_shift"]))

    out = {
        "audit": 69,
        "slug": "mcq-mmlu-redux-length-error-census",
        "dataset": ("MMLU-Redux 2.0 (edinburgh-dawg/mmlu-redux-2.0, CC BY 4.0; Gema et al. 2024, arXiv 2406.04127), "
                    "57 subject configs, split test, read from the HuggingFace auto-converted parquet via the "
                    "datasets-server parquet API. Lengths are characters after stripping (as mcq-length-floor "
                    "0.1.0). Only aggregates are written: no question, option or suggested-answer text."),
        "fixture_target_met": fx_ok,
        "structural_gate_audit58": gate,
        "parquet_shards": shards,
        "missing_columns": missing,
        "n_rows": c["n_rows"],
        "n_invalid": c["n_invalid"],
        "label_counts": dict(sorted(c["labels"].items())),
        "subject_row_counts": dict(sorted(c["subjects"].items())),
        "mmlu_reference": cases.MMLU_REFERENCE,
        "floors": floors,
        "tool_check": tc,
        "correction_formats": formats,
        "miskey_paired": mk,
        "miskey_left_out": why,
        "detectors": detectors,
        "miskeyed_by_subject": dict(sorted(wg_by_subject.items())),
        "predictions": preds,
        "note": ("P1 structural gate (57 subjects, 5,700 rows, 0 invalid, labels = audit 58). P2 expert-OK floor "
                 "above chance (z > 3.29). P3 miskeyed questions carry a smaller lift against the published key "
                 "than OK ones. P4 HEADLINE: on miskeyed questions with one usable correction (letters or exact "
                 "text), pick-longest credit is higher against the corrected key (direction only; vacuous below 30 "
                 "pairs). P5 'key is the unique shortest option' enriches for miskeyed questions (pooled RR > 1 and "
                 "CMH direction > 0). P6 dropping non-OK rows moves the floor by under 0.005. Digit-format "
                 "corrections are 0- or 1-based (undocumented) and are reported as two sensitivity variants. "
                 "Observational: a correlation with length is a property of how options were written and keyed."),
    }
    path = os.path.join(args.out_dir, "results.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=True)
    print("[done] wrote %s" % path)


if __name__ == "__main__":
    main()
