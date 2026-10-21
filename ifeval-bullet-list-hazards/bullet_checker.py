# Faithful reproduction of IFEval's BulletListChecker
# (detectable_format:number_bullet_lists) from
# google-research/instruction_following_eval (instructions.py). The checker
# verifies a response contains EXACTLY num_bullets markdown bullet points,
# "such as:\n* This is a point.\n* This is another point."
#
# Reproduced verbatim in behaviour (confirmed against upstream instructions.py):
#   bullet_lists   = re.findall(r"^\s*\*[^\*].*$", value, flags=re.MULTILINE)
#   bullet_lists_2 = re.findall(r"^\s*-.*$",       value, flags=re.MULTILINE)
#   num_bullet_lists = len(bullet_lists) + len(bullet_lists_2)
#   pass iff num_bullet_lists == self._num_bullets   (EXACT equality)
#
# Two things make this brittle, and the EXACT-equality pass turns both into
# verdict flips in BOTH directions:
#   1. The dash pattern "^\s*-.*$" counts ANY line starting with '-', with no
#      requirement of a following space. CommonMark needs a space after the
#      marker, so a negative number ("-5 degrees"), a horizontal rule ("---") or
#      a stray leading dash is NOT a rendered bullet, yet the checker counts it.
#   2. The asterisk pattern "^\s*\*[^\*].*$" counts a line like "*italic*" (one
#      asterisk, then a non-asterisk) as a bullet, though it renders as italic
#      text, not a list item. (It correctly skips "**bold**" via "[^\*]".)
# Because the pass condition is '== num_bullets', an over-count can make a
# response with the RIGHT number of real bullets fail (false fail) or, when the
# accidental lines happen to make the total land on the target, let a response
# with too few real bullets pass (false pass).
#
# No network, no live system. Audit code by AI agents working in MV2's name
# (Munim, Inc.). Apache-2.0.

import re

# Upstream patterns, reproduced verbatim.
_ASTERISK = re.compile(r"^\s*\*[^\*].*$", flags=re.MULTILINE)
_DASH = re.compile(r"^\s*-.*$", flags=re.MULTILINE)

# A "real" markdown bullet requires the marker to be followed by whitespace and
# then some content (CommonMark: a list marker is followed by one or more spaces
# or a tab, then the item). Used only to define a corrected count for measuring
# flips; it is not proposed as the canonical replacement.
_DASH_REAL = re.compile(r"^\s*-\s+\S", flags=re.MULTILINE)
_ASTERISK_REAL = re.compile(r"^\s*\*\s+\S", flags=re.MULTILINE)


def count_bullets(value):
    """Reproduce the upstream num_bullet_lists count for `value`."""
    return len(_ASTERISK.findall(value)) + len(_DASH.findall(value))


def check_following(value, num_bullets):
    """Upstream pass condition: num_bullet_lists == num_bullets (EXACT)."""
    return count_bullets(value) == num_bullets


def corrected_count(value):
    """Count only lines whose bullet marker is followed by a space and content
    (an actual rendered markdown list item). corrected <= upstream always."""
    return len(_DASH_REAL.findall(value)) + len(_ASTERISK_REAL.findall(value))


def classify(value, num_required, intended_true_count):
    """Compare the checker's EXACT-equality pass/fail with the ground-truth
    number of deliberate bullet points. Returns:
    'match'       -- checker passes and the response really has num_required;
    'correct_neg' -- checker fails and the response really does NOT have it;
    'false_pass'  -- checker passes but the real bullet count != num_required
                     (accidental dash/asterisk lines made the total land on it);
    'false_fail'  -- checker fails but the response really has num_required
                     (accidental lines inflated the count past the target)."""
    checker_pass = check_following(value, num_required)
    true_pass = (intended_true_count == num_required)
    if checker_pass and true_pass:
        return "match"
    if (not checker_pass) and (not true_pass):
        return "correct_neg"
    if checker_pass and not true_pass:
        return "false_pass"
    return "false_fail"
