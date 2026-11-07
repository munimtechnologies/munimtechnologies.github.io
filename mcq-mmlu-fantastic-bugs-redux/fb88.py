"""Two expert panels and one model panel: new logic for audit 88.

Fantastic Bugs (Truong et al., NeurIPS 2025 Datasets and Benchmarks, arXiv 2511.16842; data stair-lab/fantastic-bugs,
MIT) sent the 50 or so most anomalous items per benchmark, ranked by an item statistic computed on HELM right/wrong
matrices, to expert reviewers and published the reviewed rows with a free-text review. MMLU-Redux 2.0 (Gema et al.)
labels a random 100 questions per MMLU subject. Audit 77's consensus flag uses which wrong option HELM's 10 most
accurate models pick. This file reads Fantastic Bugs' reviews into three frozen categories, places their rows in the
HELM MMLU universe of audits 80-87, and scores the pre-registered predictions. Standard library only. Apache-2.0.
Authored by AI agents working in the name of MV2, Munim, Inc.
"""

import ast
import json
import re
from fractions import Fraction

from base88 import norm, qkey

# Splits whose published rows include rows the reviewers judged valid ("Valid question. ...").
BOTH_KINDS = ("mmlu_clinical_knowledge", "mmlu_professional_medicine")
MMLU_SPLITS = ("mmlu_clinical_knowledge", "mmlu_professional_medicine", "mmlu_5subject", "mmlu_math")
GSM_SPLIT = "gsm"
CATEGORIES = ("key", "other", "valid")
METHODS = ("exact", "repaired", "question_only", "ambiguous", "none")
_KEY_WORD = re.compile(r"\bkey\b")


def _first_word(r):
    return r.split(" ", 1)[0].strip(",.:;!?") if r else ""


def fb_category(split, review):
    """A Fantastic Bugs review -> 'valid', 'key' (the reviewer points at the answer key) or 'other' (any other
    problem: ambiguous stem, construct, formatting, missing information, grading).
    - Clinical knowledge and professional medicine: first word 'valid' -> valid; else key when the review starts
      with 'incorrect' or contains the word 'key'; else other.
    - GSM8K: key when the review starts with 'incorrect answer key'; else other (every published row is an issue).
    - MMLU 5-subject and math: key when the first word is 'key' or the review contains 'bad key'; else other."""
    r = " ".join((review or "").split()).lower()
    first = _first_word(r)
    if split in BOTH_KINDS:
        if first == "valid":
            return "valid"
        if first == "incorrect" or _KEY_WORD.search(r):
            return "key"
        return "other"
    if split == GSM_SPLIT:
        return "key" if r.startswith("incorrect answer key") else "other"
    if first == "key" or "bad key" in r:
        return "key"
    return "other"


def demojibake(s):
    """Undo UTF-8 text that was decoded as Mac Roman ('‚Äô' -> '’'). Text that cannot be
    re-encoded as Mac Roman, or whose bytes are not valid UTF-8, is returned unchanged."""
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


def redux_group(label):
    """An MMLU-Redux 2.0 label (base88.label_of form, or None) -> 'miskey', 'ok', 'other_error', 'unsure' or
    'unreviewed' (as base88.groups)."""
    if label is None:
        return "unreviewed"
    if label == "wrong_groundtruth":
        return "miskey"
    if label == "ok":
        return "ok"
    if label in ("bad_question_clarity", "bad_options_clarity", "no_correct_answer", "multiple_correct_answers"):
        return "other_error"
    return "unsure"


JUDGED = ("miskey", "ok", "other_error")


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


def kappa(pairs):
    """Cohen's kappa of two binary raters over pairs [(a, b)] as a Fraction; None when there are no pairs or chance
    agreement is 1."""
    n = len(pairs)
    if not n:
        return None
    po = Fraction(sum(1 for a, b in pairs if bool(a) == bool(b)), n)
    pa = Fraction(sum(1 for a, _b in pairs if a), n)
    pb = Fraction(sum(1 for _a, b in pairs if b), n)
    pe = pa * pb + (1 - pa) * (1 - pb)
    if pe == 1:
        return None
    return (po - pe) / (1 - pe)


def _share(t):
    return Fraction(t[0], t[1]) if t[1] else None


def predictions88(key_err, key_mis, other_mis, valid_err, flag_key, flag_valid, gsm_overlap, th):
    """Pre-registered verdicts P2-P7 (P1 is decided in job.py). Every input is a (hits, n) pair:
    key_err / key_mis: Redux error label / wrong_groundtruth among Fantastic Bugs 'key' rows that Redux judged;
    other_mis: wrong_groundtruth among 'other' rows Redux judged; valid_err: Redux error label among 'valid' rows Redux
    judged; flag_key / flag_valid: audit 80's top-10 consensus flag among placed 'key' / 'valid' rows; gsm_overlap:
    (audit 86's S1-flagged, Platinum-kept GSM8K questions that Fantastic Bugs published as issues, all such
    questions). A verdict whose groups are smaller than th's minimum is False and listed as undecidable."""
    mn, mv = th["min_n"], th["min_n_valid"]
    und = []

    def need(name, *pairs_and_mins):
        ok = all(p[1] >= m for p, m in pairs_and_mins)
        if not ok:
            und.append(name)
        return ok

    v = {}
    v["P2_redux_confirms_fb_keys"] = bool(need("P2_redux_confirms_fb_keys", (key_err, mn))
                                          and _share(key_err) >= th["P2_min_share"])
    v["P3_key_type_agrees"] = bool(need("P3_key_type_agrees", (key_mis, mn), (other_mis, mn))
                                   and _share(key_mis) > _share(other_mis))
    v["P4_redux_clears_fb_valid"] = bool(need("P4_redux_clears_fb_valid", (valid_err, mv))
                                         and _share(valid_err) <= th["P4_max_share"])
    v["P5_consensus_separates"] = bool(need("P5_consensus_separates", (flag_key, mn), (flag_valid, mn))
                                       and _share(flag_key) > _share(flag_valid))
    v["P6_consensus_catches_fb_keys"] = bool(need("P6_consensus_catches_fb_keys", (flag_key, mn))
                                             and _share(flag_key) >= th["P6_min_share"])
    v["P7_gsm_kept_flag_confirmed"] = bool(need("P7_gsm_kept_flag_confirmed", (gsm_overlap, 1))
                                           and gsm_overlap[0] >= 1)
    v["undecidable"] = sorted(und)
    return v
