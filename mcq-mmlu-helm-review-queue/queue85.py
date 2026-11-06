"""How many wrong MMLU answer keys are left outside MMLU-Redux's sample, and which questions should experts read
first? Core logic for audit 85.

MMLU-Redux 2.0's experts re-annotated a random 100 questions per subject (5,700 of MMLU's test questions). The other
~8,300 have never been expert-reviewed. This audit sorts every MMLU test question into four frozen tiers from HELM's
model outputs (T1: none of HELM's included models picks the key; T2: all 10 most accurate models pick the same non-key
option; T3: audit 77's consensus flag; T0: the rest), then tests, on Redux-judged questions with a fixed 2-fold split,
whether tier rates estimated on one half predict the other half's wrong keys (per subject, against a subject-rate
baseline, and against the estimate's own 95% interval), and whether Redux's sample carries over to the unreviewed
questions. It then estimates the wrong keys left among the unreviewed questions and writes a ranked review queue.

The HELM, Redux, panel, flag and margin functions are copied unchanged from audit 83 (panel83.py). New here: the
key-picker counts, tiers, fold assignment, cell rates, estimates with intervals, the cross-fold test, the transport
check, Wilson intervals, the queue rows and the verdicts. Standard library only. Apache-2.0. Authored by AI agents
working in the name of MV2, Munim, Inc.
"""

import hashlib
import math
from fractions import Fraction

LETTERS = "ABCDEFGHIJ"
OK = "ok"
MISKEY = "wrong_groundtruth"
ERROR_TYPES = ("bad_question_clarity", "bad_options_clarity", "no_correct_answer", "multiple_correct_answers",
               MISKEY)
STANDARD_KEYS = ("subject", "method", "model", "eval_split", "groups")


def norm(s):
    return " ".join(("" if s is None else str(s)).split())


def label_of(error_type):
    return "" if error_type is None else str(error_type).strip().lower()


def pred_index(pred, k):
    """Index of a predicted letter A-J within k options, or None when missing / malformed / out of range."""
    if not isinstance(pred, str):
        return None
    p = pred.strip().upper()
    if len(p) != 1 or p not in LETTERS:
        return None
    i = LETTERS.index(p)
    return i if i < k else None


def suite_version(suite):
    """'v1.13.0' -> (1, 13, 0); anything unparsable sorts last."""
    try:
        return tuple(int(x) for x in str(suite).lstrip("v").split("."))
    except ValueError:
        return (10 ** 6,)


# ----- HELM run names and files (copied from audit 83) -----

def parse_run(name):
    """'mmlu:subject=X,method=M,model=Y,eval_split=test,groups=G' -> {arg: value}, or None if not an MMLU run."""
    if not isinstance(name, str) or not name.startswith("mmlu:"):
        return None
    out = {}
    for part in name[len("mmlu:"):].split(","):
        if "=" not in part:
            return None
        k, v = part.split("=", 1)
        out[k] = v
    return out


def select_runs(run_suites, method="multiple_choice_joint", split="test"):
    """{(model, subject): (run_name, suite)} from a release's runs_to_run_suites map. Per (model, subject) the run
    with the fewest non-standard arguments wins, then the smallest name. Returns (chosen, n_duplicates_dropped)."""
    cands = {}
    for name, suite in run_suites.items():
        a = parse_run(name)
        if a is None or a.get("method") != method or a.get("eval_split") != split:
            continue
        if not a.get("model") or not a.get("subject"):
            continue
        extra = sum(1 for k in a if k not in STANDARD_KEYS)
        cands.setdefault((a["model"], a["subject"]), []).append((extra, name, suite))
    chosen, dups = {}, 0
    for key in sorted(cands):
        lst = sorted(cands[key])
        chosen[key] = (lst[0][1], lst[0][2])
        dups += len(lst) - 1
    return chosen, dups


def qkey(question, options):
    return (norm(question), tuple(norm(o) for o in (options or [])))


def iid_num(iid):
    s = str(iid)
    return int(s[2:]) if s.startswith("id") and s[2:].isdigit() else 10 ** 9


def parse_instances(items):
    """HELM instances.json -> {instance id: (qkey, k, gold index or None)} for test-split items. The gold is None
    unless exactly one reference carries the 'correct' tag."""
    out = {}
    for it in items or []:
        if not isinstance(it, dict) or it.get("split") != "test":
            continue
        refs = it.get("references") or []
        opts = [(r.get("output") or {}).get("text") for r in refs]
        correct = [i for i, r in enumerate(refs) if "correct" in (r.get("tags") or [])]
        gold = correct[0] if len(correct) == 1 else None
        out[it.get("id")] = (qkey((it.get("input") or {}).get("text"), opts), len(opts), gold)
    return out


def build_universe(inst_by_subject):
    """{subject: parsed instances} -> (qids {(subject, qkey): qid}, info [(subject, iid, k, gold, position)], counts).
    Questions are numbered by subject, then instance id. A (subject, question, options) identity that occurs more
    than once is dropped (all copies), as is a question without exactly one gold. position = 0-based rank of the
    instance id among that subject's test instances."""
    seen, pos = {}, {}
    for subj in sorted(inst_by_subject):
        inst = inst_by_subject[subj]
        for rank, iid in enumerate(sorted(inst, key=lambda x: (iid_num(x), str(x)))):
            pos[(subj, iid)] = rank
        for iid, (qk, k, gold) in inst.items():
            seen.setdefault((subj, qk), []).append((iid_num(iid), str(iid), k, gold))
    order = sorted(seen, key=lambda key: (key[0], min(e[0] for e in seen[key]), min(e[1] for e in seen[key])))
    qids, info, counts = {}, [], {"dup_dropped": 0, "no_gold": 0}
    for key in order:
        lst = seen[key]
        if len(lst) > 1:
            counts["dup_dropped"] += len(lst)
            continue
        _n, iid, k, gold = lst[0]
        if gold is None:
            counts["no_gold"] += 1
            continue
        qids[key] = len(info)
        info.append((key[0], iid, k, gold, pos[(key[0], iid)]))
    return qids, info, counts


def map_predictions(preds, inst, subject, qids):
    """One run's display_predictions.json items -> ({qid: option index or None}, counts). The index comes from the
    predicted letter; when that is not a valid letter, from HELM's mapped_output if it equals exactly one option.
    Only train_trial_index 0 is used. em_correct counts HELM's own exact_match on the mapped items."""
    out = {}
    c = {"n": 0, "other_trial": 0, "unmapped": 0, "valid": 0, "from_mapped": 0, "invalid": 0, "consistent": 0,
         "inconsistent": 0, "no_mapped_output": 0, "em_correct": 0}
    for p in preds or []:
        c["n"] += 1
        if not isinstance(p, dict):
            c["unmapped"] += 1
            continue
        if p.get("train_trial_index", 0) != 0:
            c["other_trial"] += 1
            continue
        rec = inst.get(p.get("instance_id"))
        qid = None if rec is None else qids.get((subject, rec[0]))
        if qid is None:
            c["unmapped"] += 1
            continue
        qk, k, _gold = rec
        opts = qk[1]
        mo = p.get("mapped_output")
        i = pred_index(p.get("predicted_text"), k)
        if i is not None:
            c["valid"] += 1
            if mo is None:
                c["no_mapped_output"] += 1
            elif norm(mo) == opts[i]:
                c["consistent"] += 1
            else:
                c["inconsistent"] += 1
        elif mo is not None:
            hits = [j for j, o in enumerate(opts) if o == norm(mo)]
            if len(hits) == 1:
                i = hits[0]
                c["from_mapped"] += 1
            else:
                c["invalid"] += 1
        else:
            c["invalid"] += 1
        em = (p.get("stats") or {}).get("exact_match")
        if isinstance(em, (int, float)) and em >= 0.5:
            c["em_correct"] += 1
        if qid not in out:
            out[qid] = i
    return out, c


def question_hash(question):
    return hashlib.sha256(norm(question).encode("utf-8")).hexdigest()[:16]


# ----- MMLU-Redux 2.0 -> HELM questions (copied from audit 83) -----

def redux_join(redux_rows, qids, gold_of):
    """Each Redux row -> a universe question by (subject, question, choices). Returns (labels {qid: label},
    counts, key_agree), where key_agree counts joined rows whose published `answer` equals HELM's gold."""
    counts = {"joined": 0, "no_match": 0, "conflict": 0}
    labels, key_agree = {}, 0
    for r in redux_rows:
        q = qids.get((r["subject"], qkey(r["question"], r["choices"])))
        if q is None:
            counts["no_match"] += 1
            continue
        counts["joined"] += 1
        if r.get("answer") is not None and r["answer"] == gold_of[q]:
            key_agree += 1
        lab = r["label"]
        if q in labels and labels[q] != lab:
            counts["conflict"] += 1
            labels[q] = "conflict"
        elif q not in labels:
            labels[q] = lab
    return labels, counts, key_agree


def groups(n, labels):
    g = {"all": list(range(n)), "miskey": [], "ok": [], "other_error": [], "unsure_or_conflict": [],
         "unreviewed": []}
    for q in range(n):
        lab = labels.get(q)
        if lab is None:
            g["unreviewed"].append(q)
        elif lab == MISKEY:
            g["miskey"].append(q)
        elif lab == OK:
            g["ok"].append(q)
        elif lab in ERROR_TYPES:
            g["other_error"].append(q)
        else:
            g["unsure_or_conflict"].append(q)
    return g


# ----- The panel and the consensus flag (audit 77's rule, copied from audit 83) -----

def accuracy(correct, n):
    return Fraction(correct, n) if n else Fraction(0)


def select_panel(acc, size):
    return sorted(acc, key=lambda m: (-accuracy(*acc[m]), m))[:size]


def votes(idxs, k):
    counts, none = [0] * k, 0
    for i in idxs:
        if i is None or not (0 <= i < k):
            none += 1
        else:
            counts[i] += 1
    return counts, none


def consensus(counts, key_i):
    best, top, tied = None, 0, False
    for i, n in enumerate(counts):
        if i == key_i:
            continue
        if n > top:
            best, top, tied = i, n, False
        elif n == top and n > 0:
            tied = True
    if best is None or tied:
        return None, top
    return best, top


def flag_question(counts, key_i, min_agree):
    ci, n = consensus(counts, key_i)
    flagged = ci is not None and n >= min_agree and n > counts[key_i]
    return flagged, ci, n


def panel_flags(panel, preds_by_model, questions, min_agree):
    flags, tallies = {}, {}
    for q, (k, key_i) in questions.items():
        counts, none = votes([preds_by_model.get(m, {}).get(q) for m in panel], k)
        f, ci, _n = flag_question(counts, key_i, min_agree)
        flags[q] = (f, ci)
        tallies[q] = (counts, none)
    return flags, tallies


def n_flagged(ids, flags):
    return sum(1 for q in ids if flags[q][0])


def flag_precision(flags, g):
    """(error-labelled, judged): among flagged questions MMLU-Redux judged (wrong key, OK or another error label),
    how many carry an error label. Unsure / conflicting labels are left out, as in audits 77-83."""
    err = n_flagged(g["miskey"], flags) + n_flagged(g["other_error"], flags)
    return err, err + n_flagged(g["ok"], flags)


def margin(counts, key_i):
    """Consensus margin of a panel's votes: the most-picked non-key option's votes minus the key's votes."""
    other = max([n for i, n in enumerate(counts) if i != key_i] or [0])
    return other - counts[key_i]


# ----- New in audit 85 -----

def key_pickers(preds_by_model, models, questions):
    """questions {q: (k, key)} -> ({q: (models covering q, models picking the key)}, no-key set). A model covers q
    when q is among its mapped predictions, even with an invalid answer (as audit 82's item-rest correlation). The
    no-key set holds the questions covered by at least 2 models and answered with the key by none (audit 82's
    r = -1 questions)."""
    counts, nokey = {}, set()
    for q, (_k, key_i) in questions.items():
        cov = pick = 0
        for m in models:
            d = preds_by_model.get(m, {})
            if q in d:
                cov += 1
                if d[q] is not None and d[q] == key_i:
                    pick += 1
        counts[q] = (cov, pick)
        if cov >= 2 and pick == 0:
            nokey.add(q)
    return counts, nokey


def tier_of(flagged, top_votes, panel_size, no_key):
    """T1: no model picks the key. T2: the panel's flag with every panel model on the same non-key option. T3: the
    panel's flag otherwise. T0: everything else. Checked in that order."""
    if no_key:
        return 1
    if flagged and top_votes == panel_size:
        return 2
    if flagged:
        return 3
    return 0


def assign_tiers(flags, tallies, nokey, panel_size):
    out = {}
    for q in flags:
        f, ci = flags[q]
        n = tallies[q][0][ci] if ci is not None else 0
        out[q] = tier_of(f, n, panel_size, q in nokey)
    return out


def fold_of(subject, iid):
    """Fixed 2-fold split of questions: parity of the sha256 of 'subject|instance id'."""
    return int(hashlib.sha256(("%s|%s" % (subject, iid)).encode("utf-8")).hexdigest(), 16) % 2


def rates(cells, target, judged, train):
    """Rates of `target` among the judged questions in `train`, by cell. Returns (rate {cell: Fraction}, pooled
    Fraction over all of them, den {cell: judged count})."""
    num, den = {}, {}
    for q in judged:
        if q not in train:
            continue
        c = cells[q]
        den[c] = den.get(c, 0) + 1
        if q in target:
            num[c] = num.get(c, 0) + 1
    tot_d, tot_n = sum(den.values()), sum(num.values())
    pooled = Fraction(tot_n, tot_d) if tot_d else Fraction(0)
    return {c: Fraction(num.get(c, 0), den[c]) for c in den}, pooled, den


def predict(cells, rate, pooled, qs):
    """Each question's expected hit: its cell's rate, or the pooled rate when the cell had no judged question."""
    return {q: rate.get(cells[q], pooled) for q in qs}


def estimate(cells, rate, pooled, den, qs):
    """Expected hits among qs = sum over cells of n * r. Variance = the questions' own spread (n r (1 - r)) plus the
    rate's sampling spread (n^2 r (1 - r) / judged in that cell; left out for a cell with no judged question).
    Returns (expected, variance, rows by cell)."""
    count = {}
    for q in qs:
        c = cells[q]
        count[c] = count.get(c, 0) + 1
    exp, var, rows = Fraction(0), Fraction(0), []
    for c in sorted(count):
        r, n, nj = rate.get(c, pooled), count[c], den.get(c, 0)
        exp += n * r
        var += n * r * (1 - r) + (Fraction(n * n, nj) * r * (1 - r) if nj else 0)
        rows.append({"cell": c, "n": n, "rate": r, "expected": n * r})
    return exp, var, rows


def subject_abs_error(pred, target, subject_of):
    """Sum over subjects of |predicted hits - actual hits| for the questions in pred."""
    p, a = {}, {}
    for q, v in pred.items():
        s = subject_of[q]
        p[s] = p.get(s, 0) + v
        a[s] = a.get(s, 0) + (1 if q in target else 0)
    return sum(abs(p[s] - a[s]) for s in p)


def cross_fold(tiers, subject_of, fold, target, judged):
    """For each fold f: rates from the judged questions of the other fold, predictions for the judged questions of
    fold f by tier (with estimate()'s interval) and by subject; per-subject absolute errors of both."""
    out = []
    for f in (0, 1):
        train = {q for q in judged if fold[q] != f}
        test = [q for q in sorted(judged) if fold[q] == f]
        tr, tp, td = rates(tiers, target, judged, train)
        sr, sp, _sd = rates(subject_of, target, judged, train)
        pt = predict(tiers, tr, tp, test)
        ps = predict(subject_of, sr, sp, test)
        e, v, _rows = estimate(tiers, tr, tp, td, test)
        out.append({"fold": f, "n_test": len(test), "actual": sum(1 for q in test if q in target),
                    "tier_expected": e, "tier_var": v, "subj_expected": sum(ps.values(), Fraction(0)),
                    "mae_tier": subject_abs_error(pt, target, subject_of),
                    "mae_subject": subject_abs_error(ps, target, subject_of)})
    return out


def transport(flagged, subject_of, reviewed, unreviewed):
    """Do unreviewed questions land in tiers 1-3 as often as Redux-reviewed questions of the same subject? Returns
    (observed, expected, variance, skipped subjects). expected = sum over subjects of n_unreviewed * the reviewed
    flag share; variance adds the share's sampling spread and the unreviewed questions' own spread. Subjects without
    a reviewed question are skipped (and left out of observed)."""
    nr, fr, nu, fu = {}, {}, {}, {}
    for q in reviewed:
        s = subject_of[q]
        nr[s] = nr.get(s, 0) + 1
        fr[s] = fr.get(s, 0) + (1 if q in flagged else 0)
    for q in unreviewed:
        s = subject_of[q]
        nu[s] = nu.get(s, 0) + 1
        fu[s] = fu.get(s, 0) + (1 if q in flagged else 0)
    obs, exp, var, skipped = 0, Fraction(0), Fraction(0), []
    for s in sorted(nu):
        if not nr.get(s):
            skipped.append(s)
            continue
        f = Fraction(fr[s], nr[s])
        obs += fu[s]
        exp += nu[s] * f
        var += Fraction(nu[s] * nu[s], nr[s]) * f * (1 - f) + nu[s] * f * (1 - f)
    return obs, exp, var, skipped


def wilson(k, n, z=1.96):
    """95% Wilson score interval for k of n, as floats; None when n = 0."""
    if not n:
        return None
    p, z2 = k / n, z * z
    d = 1 + z2 / n
    c = (p + z2 / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / d
    return [c - h, c + h]


def queue_rows(qs, tiers, flags, tallies, key_counts, info):
    """The review queue: every question of qs in tiers 1-3, ordered by tier, then panel margin (high first), then
    fewer models picking the key, then subject and test position. info[q] = (subject, iid, k, gold, position)."""
    rows = []
    for q in qs:
        t = tiers[q]
        if t == 0:
            continue
        subj, iid, _k, gold, pos = info[q]
        counts, none = tallies[q]
        _f, ci = flags[q]
        cov, pick = key_counts[q]
        rows.append({"qid": q, "tier": t, "subject": subj, "helm_instance_id": iid, "helm_test_position": pos,
                     "helm_key": LETTERS[gold], "consensus_letter": None if ci is None else LETTERS[ci],
                     "top10_votes": list(counts), "top10_no_answer": none, "margin": margin(counts, gold),
                     "n_models": cov, "n_models_picking_key": pick})
    rows.sort(key=lambda r: (r["tier"], -r["margin"], r["n_models_picking_key"], r["subject"],
                             r["helm_test_position"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows


def predictions85(folds, tr, tier_rates, z2):
    """Pre-registered P2-P5 (P1 is decided in job.py). folds: cross_fold output for wrong keys; tr: transport output;
    tier_rates: wrong-key rates among all judged questions for [T1, T2, T3, T0]; z2: the squared z of a 95% interval."""
    mt = sum((f["mae_tier"] for f in folds), Fraction(0))
    ms = sum((f["mae_subject"] for f in folds), Fraction(0))
    obs, exp, var, _sk = tr
    r = tier_rates
    return {
        "P2_tier_beats_subject": mt < ms,
        "P2_mae": [float(mt), float(ms)],
        "P3_tier_calibrated": all((f["actual"] - f["tier_expected"]) ** 2 <= z2 * f["tier_var"] for f in folds),
        "P3_folds": [[f["actual"], float(f["tier_expected"]), float(f["tier_var"])] for f in folds],
        "P4_transport": (obs - exp) ** 2 <= z2 * var,
        "P4_counts": [obs, float(exp), float(var)],
        "P5_tiers_ordered": bool(all(x is not None for x in r) and r[0] > r[1] > r[2] > r[3]),
        "P5_rates": [None if x is None else float(x) for x in r],
    }
