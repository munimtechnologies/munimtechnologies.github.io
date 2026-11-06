"""How strong must a model panel be to find wrong MMLU answer keys? Core logic for audit 83.

Audits 77-82 flag a multiple-choice question as possibly miskeyed when at least 6 of the 10 most accurate models pick
the same option other than the key. This audit holds the rule and the panel size fixed and changes only the panel's
strength: HELM's 78 included models are ranked by MMLU accuracy and cut into seven disjoint panels of 10 (ranks 1-10,
11-20, ..., 61-70). Each panel's flag and vote margin are scored against MMLU-Redux 2.0's expert labels by flag count,
AUC (miskeys vs OK) and precision at an equal review budget, and a 20-model panel (ranks 1-20) is compared with the
top 10.

The HELM, Redux, panel, flag, margin and AUC functions are copied unchanged from audit 82 (disc82.py), which copied
most of them from audits 80-81. New here: the strata, the expected counts at a fixed budget with ties shared evenly,
the per-panel statistics and the verdicts. Standard library only. Apache-2.0. Authored by AI agents working in the
name of MV2, Munim, Inc.
"""

import hashlib
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


# ----- HELM run names and files (copied from audit 82) -----

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


# ----- MMLU-Redux 2.0 -> HELM questions (copied from audit 82) -----

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
    """Every group of g restricted to the qids in `keep`, order kept (copied from audit 82)."""
    return {name: [q for q in ids if q in keep] for name, ids in g.items()}


# ----- The panel and the consensus flag (audit 77's rule, copied from audit 82) -----

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
    how many carry an error label. Unsure / conflicting labels are left out, as in audits 77-82."""
    err = n_flagged(g["miskey"], flags) + n_flagged(g["other_error"], flags)
    return err, err + n_flagged(g["ok"], flags)


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


# ----- New in audit 83: strata, budget counts with shared ties, per-panel statistics, verdicts -----

def strata(acc, size, n):
    """The included models ranked by accuracy (ties by name, as select_panel), cut into n disjoint panels of `size`:
    ranks 1..size, size+1..2*size, ... None if there are fewer than size * n models."""
    ranked = select_panel(acc, len(acc))
    if len(ranked) < size * n:
        return None
    return [ranked[i * size:(i + 1) * size] for i in range(n)]


def margins(tallies, questions):
    """{q: the panel's consensus margin on q}."""
    return {q: margin(tallies[q][0], questions[q][1]) for q in questions}


def budget_counts(score, sets, budget):
    """Expected counts when the `budget` highest-scoring questions are sent to review and ties at the cut are broken
    uniformly at random: whole score levels are taken from the top; the level that straddles the cut contributes the
    fraction (budget - taken) / level size of its members. Returns one Fraction per set in `sets` (each a set of
    question ids): the expected number of reviewed questions from that set."""
    levels = {}
    for q, v in score.items():
        levels.setdefault(v, []).append(q)
    out = [Fraction(0)] * len(sets)
    taken = 0
    for v in sorted(levels, reverse=True):
        if taken >= budget:
            break
        qs = levels[v]
        f = Fraction(1) if taken + len(qs) <= budget else Fraction(budget - taken, len(qs))
        for i, s in enumerate(sets):
            out[i] += f * sum(1 for q in qs if q in s)
        taken = min(budget, taken + len(qs))
    return out


def stratum_stats(flags, score, g, budget):
    """One panel's numbers: frozen-rule flag count, precision (error-labelled, judged) and miskeys among its flags;
    AUC of its margin for Redux miskeys vs Redux-OK; expected error-labelled, judged and miskey counts among the
    `budget` questions with the highest margin (ties shared)."""
    err = set(g["miskey"]) | set(g["other_error"])
    judged = err | set(g["ok"])
    b_err, b_judged, b_mis = budget_counts(score, [err, judged, set(g["miskey"])], budget)
    return {"flags": n_flagged(g["all"], flags), "prec": flag_precision(flags, g),
            "miskeys": n_flagged(g["miskey"], flags),
            "auc": auc([score[q] for q in g["miskey"]], [score[q] for q in g["ok"]]),
            "b_err": b_err, "b_judged": b_judged, "b_miskey": b_mis}


def stats_json(st):
    """A JSON-safe copy of stratum_stats output (Fractions -> floats; the exact budget counts as 'p/q' strings)."""
    def fr(x):
        return None if x is None else float(x)
    e, j = st["prec"]
    return {"flags": st["flags"], "precision": [e, j, (e / j) if j else None], "miskeys": st["miskeys"],
            "auc_miskey_vs_ok": fr(st["auc"]),
            "budget": {"error_labelled": str(st["b_err"]), "judged": str(st["b_judged"]),
                       "miskeys": str(st["b_miskey"]),
                       "precision": fr(st["b_err"] / st["b_judged"]) if st["b_judged"] else None}}


def _bprec(st):
    return st["b_err"] / st["b_judged"] if st["b_judged"] else None


def predictions83(st, top20, base_err, base_judged, th):
    """Pre-registered P2-P6 with their numbers (P1 is decided in job.py). st: stratum_stats for panels S1..S7 (ranks
    1-10 ... 61-70); top20: stratum_stats for the ranks 1-20 panel; base_err / base_judged: error-labelled and judged
    Redux questions in the whole universe."""
    s1, s4, s7 = st[0], st[3], st[6]
    a = [s1["auc"], s4["auc"], s7["auc"]]
    p = [_bprec(s1), _bprec(s4), _bprec(s7)]
    p20 = _bprec(top20)
    return {
        "P2_weaker_flags_more": s7["flags"] > s1["flags"],
        "P2_counts": [s1["flags"], s7["flags"]],
        "P3_auc_falls_with_strength": bool(all(x is not None for x in a) and a[0] > a[1] > a[2]),
        "P3_auc": [None if x is None else float(x) for x in a],
        "P4_budget_precision_falls": bool(all(x is not None for x in p) and p[0] > p[1] > p[2]),
        "P4_precision": [None if x is None else float(x) for x in p],
        "P5_weakest_still_informative": bool(s7["b_judged"] and base_judged and
                                             s7["b_err"] * base_judged >= th["P5_mult"] * base_err * s7["b_judged"]),
        "P5_counts": [float(s7["b_err"]), float(s7["b_judged"]), base_err, base_judged],
        "P6_top20_beats_top10": bool(p20 is not None and p[0] is not None and p20 > p[0]),
        "P6_precision": [None if p20 is None else float(p20), None if p[0] is None else float(p[0])],
    }
