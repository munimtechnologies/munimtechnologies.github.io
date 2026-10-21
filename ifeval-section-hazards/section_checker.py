# Faithful reproduction of IFEval's SectionChecker
# (detectable_format:multiple_sections) from
# google-research/instruction_following_eval (instructions.py). The checker
# verifies a response contains AT LEAST num_sections sections, each marked by
# the section_spliter keyword followed by a number, e.g. "Section 1".
#
# Reproduced verbatim in behaviour (confirmed against upstream instructions.py):
#   section_splitter_patten = r"\s?" + self._section_spliter + r"\s?\d+\s?"
#   sections = re.split(section_splitter_patten, value)   # NO re.escape,
#   num_sections = len(sections) - 1                      # NOT line-anchored
#   return num_sections >= self._num_sections             # >= (minimum)
#
# Two things make this brittle, and the >= pass turns them into verdict flips in
# BOTH directions:
#   1. FALSE PASS -- the pattern is NOT line-anchored, so an inline cross-
#      reference ("see Section 3 below") or even a substring inside a word
#      ("subSection3", because 'Section' is matched case-sensitively anywhere)
#      is counted as a section boundary. Under >= these spurious matches can push
#      the count past the quota, passing a response with too few real sections.
#   2. FALSE FAIL -- the pattern requires a DIGIT (\d+) after the keyword, so a
#      response that correctly marks its sections with spelled-out numbers
#      ("Section One", "Section Two", "Section Three") matches nothing -> num=0,
#      and 0 >= num_sections fails a perfectly good response.
#
# No network, no live system. Audit code by AI agents working in MV2's name
# (Munim, Inc.). Apache-2.0.

import re

_NUMBER_WORDS = "one|two|three|four|five|six|seven|eight|nine|ten"


def _pattern(spliter):
    """Upstream split pattern, reproduced verbatim: NO re.escape, NOT anchored."""
    return r"\s?" + spliter + r"\s?\d+\s?"


def count_sections(value, spliter):
    """Reproduce the upstream num_sections = len(re.split(...)) - 1."""
    sections = re.split(_pattern(spliter), value)
    return len(sections) - 1


def check_following(value, num_sections, spliter):
    """Upstream pass condition: num_sections >= required (minimum, not exact)."""
    return count_sections(value, spliter) >= num_sections


def corrected_count(value, spliter):
    """Count only genuine section headers: a line that STARTS (case-insensitively)
    with the spliter keyword followed by a number -- a digit OR a spelled-out
    number word. This ignores inline cross-references and in-word substrings, and
    credits spelled-out section numbers. Used to measure flips; not proposed as
    the canonical replacement."""
    pat = re.compile(r"(?mi)^[ \t]*" + re.escape(spliter) +
                     r"\s+(?:\d+|" + _NUMBER_WORDS + r")\b")
    return len(pat.findall(value))


def classify(value, spliter, num_required, intended_true_count):
    """Compare the checker's >= pass/fail with the ground-truth number of
    deliberate sections. Returns:
    'match'       -- checker passes and the response really has >= num_required;
    'correct_neg' -- checker fails and the response really has < num_required;
    'false_pass'  -- checker passes but the real section count < num_required
                     (inline/substring matches inflated the count);
    'false_fail'  -- checker fails but the response really has >= num_required
                     (spelled-out section numbers matched nothing)."""
    checker_pass = check_following(value, num_required, spliter)
    true_pass = (intended_true_count >= num_required)
    if checker_pass and true_pass:
        return "match"
    if (not checker_pass) and (not true_pass):
        return "correct_neg"
    if checker_pass and not true_pass:
        return "false_pass"
    return "false_fail"
