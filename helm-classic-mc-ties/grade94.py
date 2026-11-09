"""Pure functions for audit 94: ties in HELM Classic's log-probability multiple-choice scores. Apache-2.0.

HELM scores a `multiple_choice_separate_original` / `_calibrated` run by giving every answer option a score (its
log-probability, length-normalised or calibrated) and picking the best. Two versions of the tie rule exist:
- current HELM (`basic_metrics.py`, the code HELM issue #4363 is about): exact_match = |correct & tied| / |tied|,
  a fraction when several options share the top score;
- HELM v0.2.2: exact_match = float(max(all scores) == max(correct scores)), i.e. a tie that includes a correct option
  scores 1.
Both record predicted_index = the FIRST option with the top score. So, per record:
- `frac`: exact_match is neither 0 nor 1 -> a tie scored by the current (fractional) rule;
- `old_tie`: exact_match 1 but predicted_index is not a correct option -> a tie credited in full by the v0.2.2 rule;
- `inconsistent`: exact_match 0 but predicted_index is a correct option (impossible under either rule);
- `plain`: anything else (no visible tie); `unmatched`: no unperturbed instance with that id; `missing`: no score.
F, the first-argmax binary grade (the fix proposed in #4363 / PR #4364), is 1 iff predicted_index is a correct option.
"""

from fractions import Fraction

SEPARATE = ("multiple_choice_separate_original", "multiple_choice_separate_calibrated")


def _param(run, key):
    for part in run.split(","):
        if part.startswith(key + "="):
            return part[len(key) + 1:]
        if ":" in part and part.split(":", 1)[1].startswith(key + "="):
            return part.split(":", 1)[1][len(key) + 1:]
    return None


def model_of(run):
    return _param(run, "model")


def method_of(run):
    return _param(run, "method")


def group_of(run):
    """The run name without its model=... part: runs in one group differ only by model."""
    return ",".join(p for p in run.split(",") if not p.startswith("model="))


def scenario_of(run):
    """Scenario label for tallies: the prefix plus its dataset=/phenomenon=/subject= value if any."""
    head = run.split(",")[0]
    return head


def has_dup_correct(texts, correct):
    """True when some correct option and some wrong option have the same text after strip()."""
    cs = set(correct)
    good = {texts[j].strip() for j in cs if 0 <= j < len(texts)}
    return any(texts[k].strip() in good for k in range(len(texts)) if k not in cs)


def build_inst_map(instances):
    """id -> {'correct': [...], 'texts': [...], 'dup': bool} from UNPERTURBED instances; also their split."""
    out, split = {}, None
    for inst in instances:
        if inst.get("perturbation"):
            continue
        refs = inst.get("references") or []
        texts = [((r.get("output") or {}).get("text") or "") for r in refs]
        correct = [i for i, r in enumerate(refs) if "correct" in (r.get("tags") or [])]
        out[inst.get("id")] = {"correct": correct, "texts": texts, "dup": has_dup_correct(texts, correct)}
        if split is None:
            split = inst.get("split")
    return out, split


def classify(em, pi, correct):
    if em is None or pi is None:
        return "missing"
    if em != 0.0 and em != 1.0:
        return "frac"
    if em == 1.0 and pi not in correct:
        return "old_tie"
    if em == 0.0 and pi in correct:
        return "inconsistent"
    return "plain"


def summarize_run(preds, inst_map):
    counts = {"records": 0, "plain": 0, "old_tie": 0, "frac": 0, "inconsistent": 0, "unmatched": 0, "missing": 0}
    ua = {"n": 0, "pub": 0.0, "f": 0.0}
    u0 = {"n": 0, "pub": 0.0, "f": 0.0}
    ties, frac_values = [], {}
    for rec in preds:
        counts["records"] += 1
        st = rec.get("stats") or {}
        em = st.get("exact_match")
        pi = st.get("predicted_index")
        pi = None if pi is None else int(round(pi))
        pert = rec.get("perturbation") or None
        pname = pert.get("name") if pert else None
        trial = rec.get("train_trial_index", 0)
        inst = inst_map.get(rec.get("instance_id"))
        if em is None or pi is None:
            counts["missing"] += 1
            continue
        if inst is None:
            counts["unmatched"] += 1
            f = em
        else:
            cls = classify(em, pi, inst["correct"])
            counts[cls] += 1
            f = 1.0 if pi in inst["correct"] else 0.0
            if cls in ("old_tie", "frac"):
                ties.append((rec.get("instance_id"), pname, cls, em, inst["dup"], pi, list(inst["correct"])))
                if cls == "frac":
                    key = "%.6g" % em
                    frac_values[key] = frac_values.get(key, 0) + 1
        if pname is None:
            ua["n"] += 1
            ua["pub"] += em
            ua["f"] += f
            if trial == 0:
                u0["n"] += 1
                u0["pub"] += em
                u0["f"] += f
    return {"counts": counts, "unpert_all": ua, "unpert_t0": u0, "ties": ties, "frac_values": frac_values}


def stat_mean(stats, name, split):
    for s in stats:
        nm = s.get("name") or {}
        if nm.get("name") == name and nm.get("split") == split and not nm.get("perturbation"):
            return s.get("mean")
    return None


def reproduce(summary, pub_em, num_instances, tol):
    """(basis, ok): basis 'all' if the mean over all unperturbed records equals HELM's exact_match mean, else 't0'
    if the first-trial mean does; requires as many first-trial unperturbed records as HELM's num_instances."""
    ua, u0 = summary["unpert_all"], summary["unpert_t0"]
    if pub_em is None or num_instances is None or u0["n"] == 0 or u0["n"] != int(round(num_instances)):
        return None, False
    if ua["n"] and abs(ua["pub"] / ua["n"] - pub_em) <= tol:
        return "all", True
    if abs(u0["pub"] / u0["n"] - pub_em) <= tol:
        return "t0", True
    return None, False


def ranks_high(d):
    """1 + number of keys with a strictly higher value."""
    return {k: 1 + sum(1 for v in d.values() if v > d[k]) for k in d}


def top_share(by_model, k):
    vals = sorted(by_model.values(), reverse=True)
    return sum(vals[:k])


def predictions94(old_tie, frac, records, topk, max_move, dup, th):
    ties = old_tie + frac
    return {
        "P2_ties_exist": ties >= 1,
        "P3_pre_fix_rule": old_tie >= 1 and frac == 0,
        "P4_rare": records > 0 and Fraction(ties, records) <= th["P4_max_share"],
        "P5_concentrated": ties >= 1 and Fraction(topk, ties) >= th["P5_min_share"],
        "P6_headline_moves": max_move is not None and max_move >= th["P6_min_move"],
        "P7_duplicates": ties >= 1 and Fraction(dup, ties) >= th["P7_min_share"],
    }
