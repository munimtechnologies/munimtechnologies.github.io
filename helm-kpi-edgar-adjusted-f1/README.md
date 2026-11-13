# helm-kpi-edgar-adjusted-f1 (audit 116)

**Status: desk check, 2026-11-13. Code-certain, not pre-registered. HELM publishes no KPI-EDGAR runs (its public
archive has no enterprise project, and https://crfm.stanford.edu/helm/enterprise/latest/ returned 404 on
2026-11-13), so no published number is re-computed here. A small check job that scores fixed reference answers on
the real test split is queued; its results will be added below.**

HELM's KPI-EDGAR scenario (added in PR #3495, 2025-04-18, from IBM's enterprise benchmark) asks a model to tag
the KPIs and the current-year, prior-year and two-years-past values in a sentence from a 10-K report, as
`phrase [tag]` items with the tags `kpi`, `cy`, `py` and `py1`. Its main metric (`main_name` in
`schema_enterprise.yaml`) is `adjusted_macro_f1_score`, described as "adjusted for partial matches following the
KPI-Edgar paper". IBM's Enterprise Benchmarks paper ([arXiv 2410.12857](https://arxiv.org/abs/2410.12857)) reports
this "Adj F1" for 13 models, from 0.011 (flan-ul2) to 0.714 (llama2.70b).

Open HELM issue [#4348](https://github.com/stanford-crfm/helm/issues/4348) and open PR
[#4350](https://github.com/stanford-crfm/helm/pull/4350) (both September 2026, no replies yet) report that
`kpi_edgar_metrics.py` passes the gold as the prediction and the prediction as the gold, which leaves the
symmetric word F1 unchanged but changes the adjusted score. This desk check reproduces their example
(0.45 instead of 0.416667) and adds four things neither covers.

The work was carried out by AI agents working in MV2's name (MV2 of Munim, Inc.).

## 1. What the adjusted score is once it is pooled (code-certain)

For each tag, HELM sums three counts over every evaluated sentence: the distinct words both sides share (O),
the distinct predicted words (P) and the distinct gold words (G). It then sets tp = O/G, fn = 1 - O/G and
fp = 1 - O/P **once for the whole set** and takes F1 = 2tp / (2tp + fp + fn). With pooled recall r = O/G and
precision p = O/P (G and P above 0):

| Order | Per-tag score |
| --- | --- |
| PR #4350's order (prediction first) | 2r / (2 + r - p) |
| HELM's current, swapped order | 2p / (2 + p - r) |
| plain word F1 (`word_macro_f1_score`, either order) | 2pr / (p + r) = 2O / (P + G) |

The KPI-EDGAR paper (Deußer et al., ICMLA 2022, [arXiv 2210.09163](https://arxiv.org/abs/2210.09163), eqs. 7-12)
defines these tp, fn and fp **for one relation**, as partial credit for one pair of entities. HELM applies them to
one tag across the whole test set, so the false-positive term can never exceed 1 however many wrong words a
model adds, and the false-negative term can never exceed 1 however many gold words it misses.

## 2. Both orders have a floor of 2/3 per tag (code-certain)

- **HELM's current code:** in any tag where every predicted word is right (p = 1), the score is 2 / (3 - r),
  so at least 0.667 however little the model finds. One right word out of ten gold words scores **0.690** for
  that tag; word F1 gives 0.182.
- **PR #4350's order:** in any tag whose answer contains every gold word (r = 1), the score is 2 / (3 - p), at
  least 0.667 however many wrong words are added. An answer that repeats the input sentence once under each of
  the four tags contains every gold word, so it scores **at least 0.667** whenever all four tags occur in the
  evaluated set. For scale only: 11 of the 13 models in IBM's table are below 0.667, though those numbers were
  computed before any fix and are not directly comparable. HELM's run spec allows 100 output tokens, which cuts
  that answer short on longer sentences; the queued check measures how often.

## 3. The swap always favours the same kind of model (code-certain)

Per tag, HELM's current order scores higher than PR #4350's order **exactly when pooled precision exceeds
recall**, and lower when recall exceeds precision. Word F1 always lies between the two. So the current code
rewards a model that tags too little, and the fix would reward a model that tags too much. Neither is the
paper's per-relation partial credit. Word F1, which HELM already reports, is order-free and has no floor.

## 4. One unexpected tag fails the whole run (code-certain)

`_compute_tag_to_words` builds a dictionary with only the four tags and then indexes it with each parsed tag.
The parser accepts any tag made of lower-case letters and digits, so a single answer such as `2021 [year]`,
`... [none]` or `... [increase]` (an entity type in KPI-EDGAR's own data, which HELM leaves out) raises
`KeyError`. `Runner.run_one` does not catch errors from `metric.evaluate`, so the run writes no scores.
`run_all` logs the error and lists the run as failed, or stops if `exit_on_error` is set. Smaller points:
upper-case or hyphenated tags (`[KPI]`, `[kpi-coref]`) are ignored without a warning, and a period after the
last tag (`100 [cy].`) drops that item. A tag with no gold and no predicted words in the evaluated set scores 0,
not 1, so on a small subset a perfect answer can score below 1 (one sentence with only `kpi` and `cy`, answered
exactly, scores 0.5).

## Examples (from the unit tests)

| Example | HELM now | PR #4350 order | Word F1 |
| --- | --- | --- | --- |
| #4348's example (gold `revenue increased [kpi], 100 [cy], 90 [py]`, answer `revenue [kpi], 100 [cy]`) | 0.4500 | 0.4167 | 0.4167 |
| the sentence `Revenue was 100 , 90 and 80 .` repeated under all four tags (one gold word per tag) | 0.2222 | 0.6957 | 0.2222 |
| 1 of the 3 gold `kpi` words, the three values exact | 0.9375 | 0.8750 | 0.8750 |
| all 3 gold `kpi` words plus 2 wrong ones, the three values exact | 0.9375 | 0.9583 | 0.9375 |
| one tag only: 1 of 10 gold words, nothing wrong (that tag's score) | 0.6897 | 0.1818 | 0.1818 |
| answer containing `2021 [year]` | KeyError | KeyError | KeyError |

## Limits

- **No model output is scored.** HELM publishes no KPI-EDGAR runs, so how much the swap or the floors moved any
  real model's score cannot be measured here. Real models are not degenerate; the floors show what the metric
  allows, not what any model did.
- IBM's numbers come from IBM's own code. HELM's metric was contributed in #3495 with two of the paper's authors
  as co-authors, but we could not open IBM's copy of the file to check its order.
- The paper does not say how per-relation scores are combined, so "per relation" describes its equations, not a
  confirmed aggregation.

## Suggested fix

Keep PR #4350's order fix. Then either make `word_macro_f1_score` the main metric, or apply the partial credit
per gold entity as the paper does, rather than once per tag over the whole set, so that each wrong or missed
entity costs something. Count an unknown tag as a wrong prediction instead of raising.

## Reproduce

```
python -m unittest -v test_kpi_edgar_check.py
python kpi_edgar_check.py
python job.py --out-dir out   # downloads the pinned kpi_edgar.json HELM uses; scores fixed answers on its test split
```

Standard library only. `kpi_edgar_check.py` transcribes HELM's `kpi_edgar_metrics.py` as of commit 0d02c1b
(2025-08-27, the last commit to touch it).

## Prior art

A search of HELM's issues and PRs for "kpi" (2026-11-13) finds only #3495 (the scenario), #4348 and #4350 (the
swap). A web search found no published critique of the KPI-EDGAR adjusted F1. The floors, the direction rule, the
`KeyError` and the empty-tag zero are not mentioned in either thread.

## Licence

Code is Apache-2.0; the transcribed HELM functions keep HELM's Apache-2.0 licence. This write-up is CC BY 4.0.
Made with AI agents working in MV2's name (Munim, Inc.).
