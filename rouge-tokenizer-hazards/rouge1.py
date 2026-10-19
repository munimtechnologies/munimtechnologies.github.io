"""Stdlib-only reproduction of the DOCUMENTED default ROUGE tokenizer and
ROUGE-1 scoring, for inspecting a specific non-Latin-text hazard.

This does NOT vendor any upstream file. It reproduces the *documented* behaviour
of two public Apache-2.0 components so the behaviour can be hand-traced and unit
tested with the standard library alone:

  1. google-research/google-research `rouge/tokenize.py` `tokenize()`, which
     lowercases, replaces every run of non `[a-z0-9]` characters with a space,
     splits on whitespace, and keeps only tokens matching `^[a-z0-9]+$`
     (the default, use_stemmer=False, so no stemmer is applied here).
  2. The count-based ROUGE-N scoring in `rouge/rouge_scorer.py`
     (`_score_ngrams`): precision = overlap / max(pred_count, 1),
     recall = overlap / max(ref_count, 1), f = 2pr/(p+r) or 0.

For real evaluations, use the upstream `rouge_score` package (optionally with a
language-aware `tokenizer=`). This module exists only to document a failure mode.

Author: MV2 of Munim, Inc. Made with AI. Code Apache-2.0.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import List

# The three patterns are documented in google-research/rouge/tokenize.py.
_NON_ALPHANUM_RE = re.compile(r"[^a-z0-9]+")
_SPACES_RE = re.compile(r"\s+")
_VALID_TOKEN_RE = re.compile(r"^[a-z0-9]+$")


def tokenize(text: str) -> List[str]:
    """Reproduce the documented default ROUGE tokenizer (no stemmer)."""
    text = text.lower()
    text = _NON_ALPHANUM_RE.sub(" ", text)
    tokens = _SPACES_RE.split(text)
    return [t for t in tokens if _VALID_TOKEN_RE.match(t)]


def _fmeasure(precision: float, recall: float) -> float:
    if precision + recall > 0:
        return 2.0 * precision * recall / (precision + recall)
    return 0.0


def rouge1(reference: str, prediction: str) -> dict:
    """ROUGE-1 precision/recall/fmeasure, count-based, as in rouge_scorer."""
    ref = Counter(tokenize(reference))
    pred = Counter(tokenize(prediction))
    overlap = sum(min(ref[g], pred[g]) for g in ref)
    ref_n = sum(ref.values())
    pred_n = sum(pred.values())
    precision = overlap / max(pred_n, 1)
    recall = overlap / max(ref_n, 1)
    return {
        "precision": precision,
        "recall": recall,
        "fmeasure": _fmeasure(precision, recall),
        "ref_tokens": list(tokenize(reference)),
        "pred_tokens": list(tokenize(prediction)),
    }
