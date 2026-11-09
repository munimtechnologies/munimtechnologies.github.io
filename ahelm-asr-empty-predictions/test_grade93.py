"""Unit tests for audit 93 (standard library only). Every expectation is traced by hand below. Apache-2.0."""

import unittest

import cases93 as C
import grade93 as g


class TestNormalize(unittest.TestCase):
    def test_normalize(self):
        """HELM normalize_text, articles kept (as wer/mer/cer call it):
        'Hello, World!' -> lower 'hello, world!' -> drop ',' '!' -> 'hello world'.
        '  A-B  c. ' -> '  a-b  c. ' -> drop '-' '.' -> '  ab  c ' -> collapse -> 'ab c'.
        '...' -> '' (all ASCII punctuation). 'The cat' -> 'the cat' (articles kept).
        U+3002 (ideographic full stop) is not in string.punctuation -> unchanged."""
        for t, want in C.FIX_NORM:
            self.assertEqual(g.normalize_text(t, should_remove_articles=False), want)

    def test_articles_removed_when_asked(self):
        """'The cat' with articles removed -> 'the cat' -> ' cat' -> 'cat'."""
        self.assertEqual(g.normalize_text("The cat"), "cat")


class TestClasses(unittest.TestCase):
    def test_pred_class(self):
        """'' and '  \\n ' strip to '' -> empty (HELM's `if not pred: return 0` fires after compute_reference_metrics
        strips). None -> missing. '...' and ' - ' are non-empty after strip but normalise to '' -> punct_only.
        'hi' -> text. U+3002 survives normalisation -> text."""
        for t, want in C.FIX_CLASS:
            self.assertEqual(g.pred_class(t), want, repr(t))

    def test_model_of(self):
        """Text after the last 'model='; only the first contains 'gemini'."""
        for run, model, gem in C.FIX_MODEL:
            self.assertEqual(g.model_of(run), model)
            self.assertEqual(g.is_gemini(model), gem)


class TestRunSummary(unittest.TestCase):
    def test_summarize_run(self):
        """Seven records: id0..id3, a second id3 (duplicate, skipped), id4 at trial 1 (skipped), id5.
        Kept 5: id0 text, id1 empty, id2 text, id3 punct_only ('...'), id5 empty (' ').
        wer_score: values 0.5, 0.0, 0.0, 1.0, 0.25 -> n 5, sum 1.75; empties id1 (0.0) and id5 (0.25) -> n_empty 2,
          empty_nonzero 1 (id5), sum_empty 0.25, corrected 1.75 - 0.25 + 2 x 1.0 = 3.5; zeros id1, id2 -> 2,
          zero_empty 1 (id1).
        mer_score: id0..id3 only -> 0.5, 0.0, 0.0, 1.0 -> n 4, sum 1.5; empty id1 (0.0) -> n_empty 1, nonzero 0,
          sum_empty 0.0, corrected 1.5 - 0 + 1.0 = 2.5; zeros 2, zero_empty 1."""
        r = g.summarize_run(C.FIX_RECORDS)
        t = C.FIX_RUN_TARGET
        self.assertEqual(r["counts"], t["counts"])
        self.assertEqual(r["classes"], t["classes"])
        self.assertEqual(r["metrics"], t["metrics"])
        self.assertEqual([e[0] for e in r["empties"]], t["empty_ids"])
        self.assertEqual([p[0] for p in r["punct"]], t["punct_ids"])

    def test_stat_mean(self):
        """The perturbed wer_score (9.0) is skipped; the unperturbed one is 0.3; num_instances 500; cer absent."""
        for name, want in C.FIX_STAT_TARGET.items():
            self.assertEqual(g.stat_mean(C.FIX_STATS, name), want)


class TestGroups(unittest.TestCase):
    def test_collect(self):
        """run_spec_names under any key at any depth: x, y, z from table 1's cells and q from the subtable."""
        self.assertEqual(g.collect_run_names(C.FIX_GROUP), C.FIX_GROUP_RUNS)

    def test_wer_cells(self):
        """First table, header 'WER' is column 1; M1 has 0.2 over runs x, y; M2's value is None -> skipped."""
        self.assertEqual(g.wer_cells(C.FIX_GROUP), C.FIX_GROUP_CELLS)

    def test_ranks(self):
        """Lower is better: d 0.05 -> 1; a 0.1 -> 1 + 1 = 2; b, c 0.2 -> 1 + 2 = 3 (tie)."""
        self.assertEqual(g.min_ranks_low(C.FIX_RANKS_IN), C.FIX_RANKS_OUT)

    def test_mean(self):
        self.assertEqual(g.mean([0.5, 1.5]), 1.0)
        self.assertIsNone(g.mean([]))


class TestVerdicts(unittest.TestCase):
    def test_cases(self):
        """A, on every boundary: 10 empties all 0 -> P2; 5/10 = 1/2 Gemini -> P3; 10/1000 = 1% -> P4; rise 0.01 ->
        P5; 1 rank change -> P6; 0 multi-reference runs -> P7.
        B, just past: not all 0 -> P2 F; 5/11 < 1/2; 11/1000 > 1%; 0.0099 < 0.01; 0 changes; 1 run -> all F.
        C, no empties: P2 and P3 F (nothing to test), P4 T (0 <= 1%), P5 F, P6 F, P7 T."""
        for args, want in C.FIX_V_CASES:
            self.assertEqual(g.predictions93(*args, C.THRESHOLDS), want)


if __name__ == "__main__":
    unittest.main()
