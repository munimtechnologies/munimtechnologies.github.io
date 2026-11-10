"""Unit tests for audit 98 with the hand traces of every fixture in cases98.py. Standard library only. Apache-2.0.

Hand traces
- output_class: None -> missing; "   " strips to "" -> empty; "Rating:4 good" matches Rating:\\s*([1-5]) -> rating_text;
  "Rating: 6" cannot match [1-5] -> text; "**Rating:** 3" has "*" right after "Rating:" -> text; "The rating: 2" is
  lower-case (the regex is case-sensitive) -> text; "x Rating:\\n2" (\\s matches the newline) -> rating_text.
- summarize_run on FIX_RECORDS (9 records): id4 is trial 1 (other_trial), id5 is perturbed, the second id3 is a
  duplicate, so 6 are kept: id0 text judged 4.0; id1 empty with no judge key (unjudged); id2 rating_text judged 5.0;
  id3 text with judge None (unjudged); id6 missing text judged 2.5 (hist 'other'); id7 lower-case 'rating:' -> text,
  judge value True is a bool, not a number (unjudged). judged 3, sum 4 + 5 + 2.5 = 11.5.
- corrected_mean(10, 3, 1) = 11 / 4 = 2.75; (8, 2, 0) = 4.0; (0, 0, 0) -> None.
- stat_entry skips the perturbed entry and the junk string; bleu_4 is absent -> None.
- cell_rule: [(500, 1500), (500, 1600)] pooled 3100 / 1000 = 3.1 -> 'pooled'; [(400, 1200), (500, 2000)] pooled
  3200 / 900 = 3.556, mean of means (3.0 + 4.0) / 2 = 3.5 -> 'mean_of_means' for 3.5 and None for 3.6; an empty list
  or a zero count -> None.
- cell_value: pooled [(500, 1500, 0), (498, 1494, 2)] = (2994 + 2) / 1000 = 2.996; mean_of_means [(400, 1200, 0),
  (3, 12, 1)] = (3.0 + 13 / 4) / 2 = 3.125; pooled with no drops = 3100 / 1000 = 3.1; rule None -> None.
- ranks_high {a 3.0, b 2.0, c 3.0, d 4.5}: d 1; a and c 1 + 1 = 2; b 1 + 3 = 4.
- top_k_sum of {5, 1, 3, 2} with k 3 = 5 + 3 + 2 = 10.
- verdicts: case 1 sits on every boundary (10 / 1000 = 1%, 5 / 10 = 1/2, fall 0.01, 1 rank change, 4 / 10 < 1/2);
  case 2 is just past each (11 / 1000, 5 / 11, 0.0099, 0, 5 / 10 is not below 1/2) while P2 still holds; case 3 has
  no drops (P3 holds at 0 / 1000, P4 and P7 need a drop); case 4: requested 0 fails P3, fall None fails P5,
  1 / 1 concentrated, 0 / 1 empty.
"""

import unittest

import cases98 as C
import grade98 as g


class TestGrade98(unittest.TestCase):
    def test_model_of(self):
        for run, model in C.FIX_MODEL:
            self.assertEqual(g.model_of(run), model)

    def test_output_class(self):
        for text, cls in C.FIX_CLASS:
            self.assertEqual(g.output_class(text), cls, text)

    def test_summarize_run(self):
        s = g.summarize_run(C.FIX_RECORDS)
        t = C.FIX_RUN_TARGET
        self.assertEqual(s["counts"], t["counts"])
        self.assertEqual(s["classes"], t["classes"])
        self.assertEqual(s["judged"], t["judged"])
        self.assertEqual(s["sum"], t["sum"])
        self.assertEqual(s["hist"], t["hist"])
        self.assertEqual(s["unjudged"], t["unjudged"])
        self.assertEqual(s["unjudged_classes"], t["unjudged_classes"])
        self.assertEqual(s["rating_text"], t["rating_text"])

    def test_summarize_empty(self):
        s = g.summarize_run([])
        self.assertEqual(s["judged"], 0)
        self.assertEqual(s["sum"], 0.0)
        self.assertEqual(s["unjudged"], [])

    def test_stat_entry(self):
        for name, want in C.FIX_STAT_TARGET.items():
            self.assertEqual(g.stat_entry(C.FIX_STATS, name), want, name)
        self.assertIsNone(g.stat_entry(None, "gpt4_audio_critique"))

    def test_num_respondents(self):
        for spec, want in C.FIX_SPECS:
            self.assertEqual(g.num_respondents(spec), want)

    def test_corrected_mean(self):
        for args, want in C.FIX_CORRECTED:
            self.assertEqual(g.corrected_mean(*args), want, args)

    def test_judge_cells(self):
        self.assertEqual(g.judge_cells(C.FIX_GROUP), C.FIX_GROUP_CELLS)
        self.assertIsNone(g.judge_cells(C.FIX_GROUP_NO_COL))
        self.assertIsNone(g.judge_cells([]))
        self.assertIsNone(g.judge_cells(None))

    def test_cell_rule(self):
        for (value, runs), want in C.FIX_RULES:
            self.assertEqual(g.cell_rule(value, runs, 1e-9), want, (value, runs))

    def test_cell_value(self):
        for (rule, runs), want in C.FIX_CELL_VALUES:
            self.assertEqual(g.cell_value(rule, runs), want, (rule, runs))

    def test_ranks(self):
        self.assertEqual(g.ranks_high(C.FIX_RANKS_IN), C.FIX_RANKS_OUT)

    def test_top_k(self):
        per_model, k, want = C.FIX_TOPK
        self.assertEqual(g.top_k_sum(per_model, k), want)

    def test_verdicts(self):
        for args, want in C.FIX_V_CASES:
            self.assertEqual(g.predictions98(*args, C.THRESHOLDS), want, args)


if __name__ == "__main__":
    unittest.main()
