"""Do two independent model panels, in two harnesses, agree on which MMLU answer keys are wrong, and is their
agreement a more precise miskey flag than either panel alone? Core logic for audit 81.

Audit 77 flagged MMLU-Pro questions where at least 6 of the 10 most accurate models in TIGER-AI-Lab's published
archives (10-option prompts) pick the same non-key option; audit 80 applied the same rule to the original 4-option
MMLU test set with the 10 most accurate models in Stanford CRFM's HELM MMLU release. This audit joins every
MMLU-derived MMLU-Pro question to its HELM MMLU question and asks whether the questions both panels flag, with the
same consensus answer text, carry MMLU-Redux 2.0 expert error labels more often than either panel's flags alone.

The HELM functions are copied unchanged from audit 80 (helm80.py); the panel and flag functions from audits 77-80.
New here: the MMLU-Pro -> HELM join, the key check, the agreement flag, group restriction and the verdicts.
Standard library only. Apache-2.0. Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import hashlib
from fractions import Fraction

LETTERS = "ABCDEFGHIJ"
OK = "ok"
MISKEY = "wrong_groundtruth"
ERROR_TYPES = ("bad_question_clarity", "bad_options_clarity", "no_correct_answer", "multiple_correct_answers",
               MISKEY)
STANDARD_KEYS = ("subject", "method", "model", "eval_split", "groups")
PRO_PREFIX = "ori_mmlu-"
MIN_OVERLAP = 3


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


# ----- HELM run names and files (copied from audit 80) -----

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


# ----- MMLU-Redux 2.0 -> HELM questions (copied from audit 80) -----

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


# ----- The panel and the flag (audit 77's rule on option indices, copied from audit 80) -----

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
    how many carry an error label. Unsure / conflicting labels are left out, as in audits 77, 79 and 80."""
    err = n_flagged(g["miskey"], flags) + n_flagged(g["other_error"], flags)
    return err, err + n_flagged(g["ok"], flags)


# ----- New in audit 81: MMLU-Pro -> HELM, the key check, the agreement flag -----

def pro_subject(src):
    s = src or ""
    return s[len(PRO_PREFIX):] if s.startswith(PRO_PREFIX) else None


def overlap(choices, options):
    return len(set(norm(c) for c in choices or []) & set(norm(o) for o in options or []))


def helm_options(qids):
    """[normalised option list per HELM qid] from the universe's identity keys."""
    out = [None] * len(qids)
    for (_subj, (_q, opts)), q in qids.items():
        out[q] = list(opts)
    return out


def stem_index(qids):
    """{(subject, normalised question): [HELM qids]}."""
    out = {}
    for (subj, (qn, _opts)), q in qids.items():
        out.setdefault((subj, qn), []).append(q)
    return out


def join_pro_helm(pro_rows, stems, helm_opts):
    """Each MMLU-derived MMLU-Pro row (src 'ori_mmlu-<subject>') -> one HELM question with the same subject and
    normalised question text and at least MIN_OVERLAP shared option texts. Rows matching several HELM questions are
    'ambiguous_helm'; a HELM question claimed by several MMLU-Pro rows is dropped with all of them ('pro_dup').
    Returns ({helm qid: pro question_id}, counts)."""
    counts = {"pro_mmlu_rows": 0, "no_stem": 0, "stem_only": 0, "ambiguous_helm": 0, "pro_dup": 0, "joined": 0}
    claims = {}
    for r in pro_rows:
        subj = pro_subject(r["src"])
        if subj is None:
            continue
        counts["pro_mmlu_rows"] += 1
        cands = stems.get((subj, norm(r["question"])), [])
        if not cands:
            counts["no_stem"] += 1
            continue
        good = [q for q in cands if overlap(helm_opts[q], r["options"]) >= MIN_OVERLAP]
        if not good:
            counts["stem_only"] += 1
            continue
        if len(good) > 1:
            counts["ambiguous_helm"] += 1
            continue
        claims.setdefault(good[0], []).append(int(r["question_id"]))
    pairs = {}
    for q in sorted(claims):
        if len(claims[q]) > 1:
            counts["pro_dup"] += len(claims[q])
            continue
        pairs[q] = claims[q][0]
    counts["joined"] = len(pairs)
    return pairs, counts


def same_key(helm_opts_q, helm_gold, pro_opts_p, pro_key):
    """True when the HELM key's option text equals the MMLU-Pro key's option text (normalised)."""
    return norm(helm_opts_q[helm_gold]) == norm(pro_opts_p[pro_key])


def agree_flags(J, pairs, helm_flags, pro_flags, helm_opts, pro_opts):
    """{helm qid: (agreed, HELM consensus index or None)} for every qid in J. Agreed = both panels flag the question
    and their consensus options have the same (normalised) text."""
    out = {}
    for q in J:
        fh, ch = helm_flags[q]
        p = pairs[q]
        fp, cp = pro_flags[p]
        ok = bool(fh and fp and ch is not None and cp is not None
                  and norm(helm_opts[q][ch]) == norm(pro_opts[p][cp]))
        out[q] = (ok, ch if ok else None)
    return out


def restrict(g, keep):
    """Every group of g restricted to the qids in `keep`, order kept."""
    return {name: [q for q in ids if q in keep] for name, ids in g.items()}


def predictions81(gJ, gJx, helmJ, proJ, agree, th):
    """Pre-registered P2-P6 with their counts (P1 is decided in job.py). gJ: groups restricted to the joined set J;
    gJx: the same without virology. helmJ / proJ / agree: flags keyed by HELM qid on J."""
    eh, jh = flag_precision(helmJ, gJ)
    ep, jp = flag_precision(proJ, gJ)
    ea, ja = flag_precision(agree, gJ)
    m_h, m_a = n_flagged(gJ["miskey"], helmJ), n_flagged(gJ["miskey"], agree)
    o_h, o_a = n_flagged(gJ["ok"], helmJ), n_flagged(gJ["ok"], agree)
    ehx, jhx = flag_precision(helmJ, gJx)
    eax, jax = flag_precision(agree, gJx)
    return {
        "P2_agree_beats_helm": bool(ja and jh and Fraction(ea, ja) > Fraction(eh, jh)),
        "P2_counts": [ea, ja, eh, jh],
        "P3_agree_beats_pro": bool(ja and jp and Fraction(ea, ja) > Fraction(ep, jp)),
        "P3_counts": [ea, ja, ep, jp],
        "P4_miskey_retention": bool(m_h and Fraction(m_a, m_h) >= th["P4_min_retention"]),
        "P4_counts": [m_a, m_h],
        "P5_ok_retention_low": bool(m_h and o_h and m_a and o_a * m_h * th["P5_ratio"] <= m_a * o_h),
        "P5_counts": [o_a, o_h, m_a, m_h],
        "P6_agree_beats_helm_no_virology": bool(jax and jhx and Fraction(eax, jax) > Fraction(ehx, jhx)),
        "P6_counts": [eax, jax, ehx, jhx],
    }
