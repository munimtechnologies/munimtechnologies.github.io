"""Functions copied unchanged for audit 89: from base88.py (audits 80-88: question normalisation, HELM instance
parsing, the question universe, prediction mapping, audit 77's panel and consensus flag, the margin, the no-key
pickers, HELM Lite run selection (select_gsm_runs, used here with other prefixes) and the Mann-Whitney AUC) and from
fb88.py (audit 88: Mac Roman repair, Fantastic Bugs answer-key parsing, placement, first unit per question, counts).
Only the pieces audit 89 calls are kept. Standard library only. Apache-2.0. Authored by AI agents working in the name
of MV2, Munim, Inc.
"""

import ast
import json
from fractions import Fraction

LETTERS = "ABCDEFGHIJ"


def norm(s):
    return " ".join(("" if s is None else str(s)).split())


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


# ----- The panel and the consensus flag (audit 77's rule) -----

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


def margin(counts, key_i):
    """Consensus margin of a panel's votes: the most-picked non-key option's votes minus the key's votes."""
    other = max([n for i, n in enumerate(counts) if i != key_i] or [0])
    return other - counts[key_i]


def key_pickers(preds_by_model, models, questions):
    """questions {q: (k, key)} -> ({q: (models covering q, models picking the key)}, no-key set). A model covers q
    when q is among its mapped predictions, even with an invalid answer. The no-key set holds the questions covered
    by at least 2 models and answered with the key by none (audit 82's r = -1 questions)."""
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


# ----- HELM Lite run selection (gsm86.py via base88.py) -----

def _version(s):
    out = []
    for p in (s or "").lstrip("v").split("."):
        try:
            out.append(int(p))
        except ValueError:
            out.append(-1)
    return tuple(out)


def run_model(run):
    """'gsm:model=x_y,stop=none' -> 'x_y' (None if no model= part)."""
    body = run.split(":", 1)[1] if ":" in run else run
    for part in body.split(","):
        if part.startswith("model="):
            return part[len("model="):]
    return None


def select_gsm_runs(run_suites, prefix="gsm:"):
    """gsm86.select_runs: one run per model among keys starting with `prefix`: the newest suite, then the shortest
    and alphabetically first key. Returns ({model: (run, suite)}, number of runs dropped as duplicates)."""
    best, dropped = {}, 0
    for run, suite in run_suites.items():
        if not run.startswith(prefix):
            continue
        m = run_model(run)
        if m is None:
            continue
        cand = (run, suite)
        if m in best:
            dropped += 1
            cur = best[m]
            if (_version(suite), -len(run), [-ord(c) for c in run]) > (_version(cur[1]), -len(cur[0]),
                                                                           [-ord(c) for c in cur[0]]):
                best[m] = cand
        else:
            best[m] = cand
    return best, dropped


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


# ----- From fb88.py (audit 88) -----

METHODS = ("exact", "repaired", "question_only", "ambiguous", "none")


def demojibake(s):
    """Undo UTF-8 text that was decoded as Mac Roman. Text that cannot be re-encoded as Mac Roman, or whose bytes
    are not valid UTF-8, is returned unchanged."""
    try:
        return s.encode("mac_roman").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def parse_answer_key(s):
    """Fantastic Bugs' answer_key string (a JSON list of {"output": {"text": ...}, "tags": [...]}; a Python-literal
    list is also accepted) -> (normalised option texts, index of the single 'correct' option or None). Returns
    (None, None) when the string cannot be read as such a list."""
    data = None
    for loader in (json.loads, ast.literal_eval):
        try:
            data = loader(s)
            break
        except (ValueError, SyntaxError, TypeError):
            continue
    if not isinstance(data, list):
        return None, None
    opts, correct = [], []
    for i, d in enumerate(data):
        if not isinstance(d, dict):
            return None, None
        opts.append(norm((d.get("output") or {}).get("text")))
        if "correct" in (d.get("tags") or []):
            correct.append(i)
    return opts, (correct[0] if len(correct) == 1 else None)


def place(rows, qids):
    """rows: [(question, options)]; qids: the universe {(subject, qkey): qid}. Each row -> (qid or None, method):
    'exact' = one universe question with the same normalised question and options (any subject); 'repaired' = the
    same after demojibake(); 'question_only' = exactly one universe question has the (raw or repaired) question
    text; 'ambiguous' = more than one does; 'none' = no match. Returns (placements, counts by method)."""
    full, by_q = {}, {}
    for (_subj, qk), q in qids.items():
        full.setdefault(qk, []).append(q)
        by_q.setdefault(qk[0], []).append(q)
    out, counts = [], {m: 0 for m in METHODS}
    for question, options in rows:
        opts = list(options or [])
        k1 = qkey(question, opts)
        k2 = qkey(demojibake(norm(question)), [demojibake(norm(o)) for o in opts])
        hit, how = None, "none"
        if len(full.get(k1, [])) == 1:
            hit, how = full[k1][0], "exact"
        elif k2 != k1 and len(full.get(k2, [])) == 1:
            hit, how = full[k2][0], "repaired"
        else:
            cand = set(by_q.get(k1[0], [])) | set(by_q.get(k2[0], []))
            if len(cand) == 1:
                hit, how = cand.pop(), "question_only"
            elif len(cand) > 1:
                how = "ambiguous"
        counts[how] += 1
        out.append((hit, how))
    return out, counts


def first_per_qid(units):
    """units: list of dicts with 'qid' (None = unplaced). Keeps placed units, the first one per qid. Returns
    (kept, number of later units dropped because their qid was already taken)."""
    seen, kept, dropped = set(), [], 0
    for u in units:
        q = u.get("qid")
        if q is None:
            continue
        if q in seen:
            dropped += 1
            continue
        seen.add(q)
        kept.append(u)
    return kept, dropped


def count(units, where, hit):
    """(units satisfying where and hit, units satisfying where)."""
    sel = [u for u in units if where(u)]
    return sum(1 for u in sel if hit(u)), len(sel)
