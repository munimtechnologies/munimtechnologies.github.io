# Faithful reproduction of IFEval's ParagraphChecker
# (length_constraints:number_paragraphs) from
# google-research/instruction_following_eval (instructions.py). The checker
# verifies a response contains EXACTLY num_paragraphs paragraphs, where
# paragraphs are "separated with the markdown divider: ***".
#
# Reproduced verbatim in behaviour (confirmed against upstream instructions.py):
#   paragraphs = re.split(r"\s?\*\*\*\s?", value)      # NOT line-anchored
#   num_paragraphs = len(paragraphs)
#   for index, paragraph in enumerate(paragraphs):
#       if not paragraph.strip():
#           if index == 0 or index == len(paragraphs) - 1:
#               num_paragraphs -= 1          # boundary empty: trim
#           else:
#               return False                 # interior empty: HARD FAIL
#   return num_paragraphs == self._num_paragraphs       # EXACT equality
#
# Two things make this brittle, and the EXACT-equality pass turns both into
# verdict flips in BOTH directions:
#   1. The divider pattern r"\s?\*\*\*\s?" is NOT line-anchored, so an inline
#      markdown emphasis span like "***important***" is matched TWICE (once at
#      each run of three asterisks), splitting a single paragraph into extra
#      pieces and OVER-counting. A single prose line that uses "***" as a visual
#      separator ("a *** b *** c") is likewise read as multiple paragraphs.
#   2. A DOUBLED divider ("\n***\n***\n") leaves an empty segment in the MIDDLE
#      of the split, which the interior-empty rule turns into an immediate
#      HARD FAIL, failing a response that visually has the right paragraphs.
#
# No network, no live system. Audit code by AI agents working in MV2's name
# (Munim, Inc.). Apache-2.0.

import re

# Upstream divider pattern, reproduced verbatim (optional single whitespace on
# each side of the literal '***'; no re.MULTILINE, no line anchoring).
_DIVIDER = re.compile(r"\s?\*\*\*\s?")

# A "real" paragraph divider is a STANDALONE line that is exactly '***' (with
# only optional leading/trailing horizontal whitespace). Used to define a
# corrected count for measuring flips; not proposed as the canonical replacement.
_STANDALONE = re.compile(r"(?m)^[ \t]*\*\*\*[ \t]*$")


def count_paragraphs(value):
    """Reproduce the upstream paragraph count for `value`.

    Returns (num, hard_fail): `num` is the boundary-trimmed segment count and
    `hard_fail` is True when an interior segment is empty after strip (upstream
    returns False in that case regardless of the count)."""
    paragraphs = _DIVIDER.split(value)
    num = len(paragraphs)
    for index, paragraph in enumerate(paragraphs):
        if not paragraph.strip():
            if index == 0 or index == len(paragraphs) - 1:
                num -= 1
            else:
                return num, True
    return num, False


def check_following(value, num_paragraphs):
    """Upstream pass condition: no interior-empty hard fail AND the trimmed
    segment count equals num_paragraphs (EXACT equality)."""
    num, hard_fail = count_paragraphs(value)
    if hard_fail:
        return False
    return num == num_paragraphs


def corrected_count(value):
    """Count paragraphs by splitting only on a STANDALONE '***' divider line and
    keeping non-empty blocks -- what a human reader would count. Inline
    '***emphasis***' and doubled dividers no longer distort the total."""
    blocks = _STANDALONE.split(value)
    return len([b for b in blocks if b.strip()])


def n_upstream_dividers(value):
    """How many divider matches the upstream regex finds (standalone + inline)."""
    return len(_DIVIDER.findall(value))


def n_standalone_dividers(value):
    """How many dividers sit alone on their own line."""
    return len(_STANDALONE.findall(value))


def classify(value, num_required, intended_true_count):
    """Compare the checker's EXACT-equality pass/fail with the ground-truth
    number of deliberate paragraphs. Returns:
    'match'       -- checker passes and the response really has num_required;
    'correct_neg' -- checker fails and the response really does NOT have it;
    'false_pass'  -- checker passes but the real paragraph count != num_required
                     (inline '***' separators made the total land on it);
    'false_fail'  -- checker fails but the response really has num_required
                     (inline emphasis over-counted, or a doubled divider forced
                     an interior-empty hard fail)."""
    checker_pass = check_following(value, num_required)
    true_pass = (intended_true_count == num_required)
    if checker_pass and true_pass:
        return "match"
    if (not checker_pass) and (not true_pass):
        return "correct_neg"
    if checker_pass and not true_pass:
        return "false_pass"
    return "false_fail"
