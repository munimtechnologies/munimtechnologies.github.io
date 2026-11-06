"""Is classical item discrimination (do stronger models pick the key LESS often?) a better miskey flag for MMLU than
the top-10 model consensus of audits 77-81? Core logic for audit 82.

For every MMLU question in Stanford CRFM's HELM MMLU release, the item-rest correlation r is the Pearson correlation,
across HELM's 78 included models, between "this model picked the key" (0/1) and the model's accuracy on all its other
questions. A negative r means stronger models pick the key less often than weaker ones, the classical psychometric
sign of a miskeyed item. This audit ranks questions by r, compares the ranking with audit 80's consensus flag at an
equal number of flags and without a threshold (AUC), and scores both against MMLU-Redux 2.0's expert labels.

The HELM, Redux, panel and flag functions are copied unchanged from audit 81 (cross81.py), which copied them from
audit 80. New here: the item-rest correlation, the rank flags, the consensus margin, the AUC and the verdicts.
Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
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


# ----- HELM run names and files (copied from audits 80-81) -----

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


# ----- MMLU-Redux 2.0 -> HELM questions (copied from audits 80-81) -----

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


def restrict(g, keep):
    """Every group of g restricted to the qids in `keep`, order kept (copied from audit 81)."""
    return {name: [q for q in ids if q in keep] for name, ids in g.items()}


# ----- The panel and the consensus flag (audit 77's rule, copied from audits 80-81) -----

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
    how many carry an error label. Unsure / conflicting labels are left out, as in audits 77-81."""
    err = n_flagged(g["miskey"], flags) + n_flagged(g["other_error"], flags)
    return err, err + n_flagged(g["ok"], flags)


# ----- New in audit 82: item-rest discrimination, rank flags, consensus margin, AUC, verdicts -----

def pearson(xs, ys):
    """Pearson correlation of two equal-length number lists, or None when either has zero variance."""
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def discrimination(models, preds, acc, gold_of, n_q):
    """Item-rest correlation per question. For question q and every model m with a prediction for q (a missing or
    invalid answer counts as not picking the key): x = 1 if m picked the key, y = m's accuracy on its other covered
    questions, (correct_m - x) / (covered_m - 1). r = Pearson(x, y). Conventions: every model picked the key -> r = +1
    ('all_correct'); none did -> r = -1 ('all_wrong'); fewer than 2 models or no spread in y -> r = 0 ('too_few',
    'flat'). Returns (r list, n_models list, n_key list, counts)."""
    r, n_models, n_key = [], [], []
    counts = {"defined": 0, "all_correct": 0, "all_wrong": 0, "too_few": 0, "flat": 0}
    for q in range(n_q):
        xs, ys = [], []
        for m in models:
            pm = preds.get(m, {})
            if q not in pm:
                continue
            c_m, n_m = acc[m]
            if n_m < 2:
                continue
            x = 1 if (pm[q] is not None and pm[q] == gold_of[q]) else 0
            xs.append(x)
            ys.append((c_m - x) / (n_m - 1))
        n_models.append(len(xs))
        n_key.append(sum(xs))
        if len(xs) < 2:
            r.append(0.0)
            counts["too_few"] += 1
        elif sum(xs) == len(xs):
            r.append(1.0)
            counts["all_correct"] += 1
        elif sum(xs) == 0:
            r.append(-1.0)
            counts["all_wrong"] += 1
        else:
            v = pearson(xs, ys)
            if v is None:
                r.append(0.0)
                counts["flat"] += 1
            else:
                r.append(v)
                counts["defined"] += 1
    return r, n_models, n_key, counts


def rank_order(r):
    """Question ids from most negative r to most positive; ties by id."""
    return sorted(range(len(r)), key=lambda q: (r[q], q))


def rank_flags(r, budget):
    """{q: (flagged, None)}: the `budget` questions with the most negative r."""
    top = set(rank_order(r)[:budget])
    return {q: (q in top, None) for q in range(len(r))}


def neg_flags(r):
    """{q: (r < 0, None)}."""
    return {q: (r[q] < 0, None) for q in range(len(r))}


def margin(counts, key_i):
    """Consensus margin of a panel's votes: the most-picked non-key option's votes minus the key's votes."""
    other = max([n for i, n in enumerate(counts) if i != key_i] or [0])
    return other - counts[key_i]


def auc(pos, neg):
    """Probability that a positive scores above a negative, ties counting one half (Mann-Whitney), as a Fraction;
    None if either list is empty. Doubled average ranks keep the arithmetic exact."""
    if not pos or not neg:
        return None
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg], key=lambda t: t[0])
    n = len(allv)
    rank2_pos, i = 0, 0
    while i < n:
        j = i
        while j + 1 < n and allv[j + 1][0] == allv[i][0]:
            j += 1
        r2 = (i + 1) + (j + 1)
        rank2_pos += r2 * sum(1 for t in allv[i:j + 1] if t[1] == 1)
        i = j + 1
    n_pos, n_neg = len(pos), len(neg)
    return Fraction(rank2_pos - n_pos * (n_pos + 1), 2 * n_pos * n_neg)


def both(f1, f2):
    return {q: (bool(f1[q][0] and f2[q][0]), None) for q in f1}


def _beats(a, b):
    return bool(a[1] and b[1] and Fraction(a[0], a[1]) > Fraction(b[0], b[1]))


def predictions82(g, gx, cons, budget, neg, s_disc, s_cons, th):
    """Pre-registered P2-P6 with their counts (P1 is decided in job.py). g: Redux groups on the universe; gx: the same
    without virology. cons: audit 80's consensus flag; budget: the K most negative r (K = consensus flag count); neg:
    r < 0. s_disc[q] = -r[q]; s_cons[q] = the top-10 panel's consensus margin."""
    nm, no = len(g["miskey"]), len(g["ok"])
    m_neg, o_neg = n_flagged(g["miskey"], neg), n_flagged(g["ok"], neg)
    pb, pc = flag_precision(budget, g), flag_precision(cons, g)
    a_d = auc([s_disc[q] for q in g["miskey"]], [s_disc[q] for q in g["ok"]])
    a_c = auc([s_cons[q] for q in g["miskey"]], [s_cons[q] for q in g["ok"]])
    p2 = flag_precision(both(cons, budget), g)
    pbx, pcx = flag_precision(budget, gx), flag_precision(cons, gx)
    return {
        "P2_negative_discriminates": bool(nm and no and m_neg and m_neg * no >= th["P2_ratio"] * o_neg * nm),
        "P2_counts": [m_neg, nm, o_neg, no],
        "P3_budget_beats_consensus": _beats(pb, pc),
        "P3_counts": [pb[0], pb[1], pc[0], pc[1]],
        "P4_auc_beats_consensus": bool(a_d is not None and a_c is not None and a_d > a_c),
        "P4_auc": [None if a_d is None else float(a_d), None if a_c is None else float(a_c)],
        "P5_both_beats_each": _beats(p2, pb) and _beats(p2, pc),
        "P5_counts": [p2[0], p2[1]],
        "P6_budget_beats_consensus_no_virology": _beats(pbx, pcx),
        "P6_counts": [pbx[0], pbx[1], pcx[0], pcx[1]],
    }
