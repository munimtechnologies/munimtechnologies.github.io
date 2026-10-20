# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0.
#
# Faithful minimal transcription of IFEval's PlaceholderChecker predicate, which counts
# "placeholders" with a single over-broad regex, alongside a conservative INTENDED counter
# that excludes four markdown constructs that are provably not fill-in placeholders. This
# lets a reviewer reproduce, with the Python standard library alone, the divergence between
# the two.
#
# Upstream source audited (Apache-2.0):
#   google-research/google-research/instruction_following_eval/instructions.py
#   PlaceholderChecker.check_following  (confirmed on master, 2026-10-20):
#       placeholders = re.findall(r"\[.*?\]", value)
#       num_placeholders = len(placeholders)
#       return num_placeholders >= self._num_placeholders
#   Instruction id: detectable_content:number_placeholders ; kwarg: num_placeholders ;
#   description: "The response must contain at least {num_placeholders} placeholders
#   represented by square brackets, such as [address]."
#
# We transcribe ONLY the matching logic, verbatim in behaviour, not the surrounding
# description-generation machinery.

import re

# Upstream pattern, verbatim: a single lazy bracketed span, no DOTALL, no exclusions.
_UPSTREAM_PATTERN = r"\[.*?\]"


# ---------------------------------------------------------------------------
# number_placeholders (PlaceholderChecker)
# ---------------------------------------------------------------------------
def upstream_placeholder_count(value):
    """Transcribed verbatim: every square-bracket span counts as a placeholder."""
    return len(re.findall(_UPSTREAM_PATTERN, value))


def upstream_placeholder(value, num_placeholders):
    """Upstream check_following: True (PASS) iff count >= num_placeholders."""
    return upstream_placeholder_count(value) >= num_placeholders


def _is_markdown_noise(span, after):
    """True if a bracketed span is a markdown construct, not a fill-in placeholder.

    span is the full match including brackets, e.g. "[address]"; `after` is the single
    character immediately following the span in the source text (or "").
    Excluded constructs (each provably not a template placeholder):
      - inline markdown link anchor:      [text](url)        -> span followed by "("
      - reference-style link anchor:      [text][ref]        -> span followed by "["
      - reference/footnote definition:    [id]: url          -> span followed by ":"
      - footnote reference / definition:  [^1]               -> inner starts with "^"
      - task-list checkbox:               - [ ] / - [x]      -> inner is "", " ", "x", "X"
      - pure numeric citation marker:      [12]               -> inner is all digits
    """
    inner = span[1:-1]
    if after in ("(", "[", ":"):
        return True
    if inner.startswith("^"):
        return True
    if inner in ("", " ", "x", "X"):
        return True
    if inner.strip().isdigit():
        return True
    return False


def intended_placeholder_count(value):
    """Conservative placeholder count: bracket spans minus the markdown constructs above.

    Uses re.DOTALL so a genuine placeholder that wraps a line break (e.g. "[Full\\nName]")
    is still counted -- the upstream pattern, lacking DOTALL, silently drops it.
    """
    count = 0
    for m in re.finditer(r"\[.*?\]", value, flags=re.DOTALL):
        after = value[m.end():m.end() + 1]
        if not _is_markdown_noise(m.group(0), after):
            count += 1
    return count


def intended_placeholder(value, num_placeholders):
    """Intended semantics: True (PASS) iff the conservative count >= num_placeholders."""
    return intended_placeholder_count(value) >= num_placeholders


# ---------------------------------------------------------------------------
# Case runner
# ---------------------------------------------------------------------------
def run_case(case):
    """Run one case; return (upstream_outcome, intended_outcome).

    Each outcome is "PASS" or "FAIL". PlaceholderChecker never raises (its pattern is
    fixed), so there is no CRASH class here -- unlike the user-supplied-regex hazards.
    """
    def outcome(fn):
        return "PASS" if fn() else "FAIL"

    if case["checker"] != "placeholder":
        raise ValueError("unknown checker: %r" % (case["checker"],))
    n = case["num_placeholders"]
    up = outcome(lambda: upstream_placeholder(case["value"], n))
    it = outcome(lambda: intended_placeholder(case["value"], n))
    return up, it
