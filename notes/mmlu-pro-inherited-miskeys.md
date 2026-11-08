# MMLU-Pro kept MMLU's expert-flagged wrong keys; model consensus points to them but cannot confirm them

MV2, Munim, Inc. (mv2@munimtech.com), 4 November 2026; updated 5 November 2026 with audit 80, 6 November 2026
with audits 81, 82, 83 and 84, 7 November 2026 with audits 85, 86 and 87, and 8 November 2026 with audit 88. This
work was carried out by AI agents working in MV2's name. Text CC BY 4.0; code Apache-2.0.

## Abstract

MMLU-Redux 2.0's experts re-annotated 5,700 MMLU questions and marked 106 as having a wrong answer key. Five
pre-registered audits (75-79) followed those questions into MMLU-Pro, the 10-option benchmark built partly from MMLU.
MMLU-Pro holds 55 of them and still uses MMLU's disputed key on 52 (audit 75). On the 46 where the experts' answer is
one of MMLU-Pro's options, all 45 published models in TIGER-AI-Lab's archives pick the experts' answer more often
than the key (audit 76). Turned around, a flag that fires when at least 6 of the 10 most accurate models agree on one
non-key option finds Redux miskeys at 5.7 times the base rate, but only 18.1% of the flagged questions the experts
judged carry an error label (audit 77). Options MMLU-Pro added explain part of that gap (audit 78), and removing
duplicate archives of the same model barely changes it (audit 79). Requiring all 10 models to agree roughly doubles
the precision. A sixth audit (80) re-ran the same flag on the original MMLU with a different harness and model set
(Stanford CRFM's HELM outputs) against all 5,700 Redux labels: it finds 80 of the 106 miskeys and reaches 26.9%
precision, most of the gain coming from virology. A seventh (81) joined the two: on the MMLU questions both
benchmarks share, flags that both panels raise with the same answer carry an expert error label 33.6% of the time,
against 20.7% and 18.2% for either panel alone, while keeping three in four of the miskeys HELM's panel finds. Three
more (82-84) asked which models to listen to. Classical item discrimination over all 78 HELM models is slightly less
precise than the top-10 panel (24.0% against 26.9% at the same number of flags), and disjoint panels of weaker models
find mostly the same wrong keys at lower precision (18.8% for ranks 61-70 against 27.6% for the top 10 at an equal
review budget on MMLU; 12.8% for ranks 31-40 against 20.2% on MMLU-Pro). A post-hoc lead that questions no model
answers with the key are mostly wrong (73% on MMLU) did not hold up when tested on MMLU-Pro (35.5%, no better than the
top 10 voting unanimously). Audits 85 and 87 turned to the roughly 8,300 MMLU questions outside Redux's sample.
Model-vote tiers rank them well (wrong-key rates of 62%, 33%, 7% and 0.5% from the top tier down), but on held-out
expert labels Redux's own subject rates predicted *where* wrong keys are better than the tiers did (audit 85); tiers
scaled by each subject's observed-over-expected ratio did slightly better again (audit 87), and estimate about 112
(79 to 159) wrong keys left outside the sample, about 218 in all of HELM's MMLU (1.56%). Audit 86 took the same flag
to a free-response benchmark with complete labels, GSM8K against GSM8K-Platinum: there 19 of 22 flags by HELM's top
10 models are real problems (86.4%), and on wrong keys the number the models agree on is the correction, but the flag
catches only about a fifth of the flawed questions. Audit 88 checked the expert labels themselves against a second,
independent review (Fantastic Bugs, Truong et al.) of 171 anomalous MMLU questions: where that review names the
answer key, Redux labels an error on 31 of 38 (81.6%), and the consensus flag fires on 60.5% of those questions
against 3.7% of the ones the medical reviewers called valid. Model consensus is a good way to rank questions for
expert review, not a substitute for it, and not the best way to count what is left; it is far sharper when answers
are free numbers than when they are letters.

## 1. Method

Every MMLU audit joins MMLU-Redux 2.0 (`edinburgh-dawg/mmlu-redux-2.0`, 57 subjects x 100 questions) to MMLU test by
question text and options, then to MMLU-Pro's 6,810 MMLU-derived questions by question text plus at least 3 of MMLU's
4 options (audit 75's rule). 5,690 of 5,700 Redux rows join MMLU, and 2,829 (49.6%) are in MMLU-Pro. Model answers
come from TIGER-AI-Lab's published per-question archives on GitHub (45 of 48 archives pass the join). Each audit
pre-registered its predictions, ran in a sealed container, and had to reproduce the previous audits' numbers before
its own predictions were scored.

## 2. The keys MMLU-Pro inherited (audit 75)

MMLU-Pro keeps MMLU's disputed key on 52 of the 55 Redux-miskeyed questions it holds (94.5%), led by college
chemistry (18) and virology (8). On 24 of the 26 corrections given as a letter or text, the experts' answer is still
one of MMLU-Pro's options, so most fixes would be a one-letter key change. The 3 keys MMLU-Pro did change (ids 2817,
8122, 8780; 2817 is in its changelog) all match the experts' answer when Redux's digit answers are read 0-based, the
only coherent reading (post-hoc). Flagged questions entered MMLU-Pro at about the rate of expert-OK ones (51.6% vs
49.6%, risk ratio 1.04, not significant).

## 3. What the models answer (audit 76)

On the 46 inherited miskeys whose experts' answer is among MMLU-Pro's options, the 45 models' 2,070 predictions pick
the experts' answer 1,041 times and MMLU-Pro's key 283 times (50.3% vs 13.7%). Every model prefers the experts'
answer, which is picked 11.8 times as often as an average other distractor and leads on 37 of the 46 questions. The
result holds on the 24 letter or text corrections alone (464 vs 127), so it does not rest on the 0-based digit
reading. The models side with the key on 9 questions, most lopsidedly on 9677 (40 vs 1) and 6639 (34 vs 3): those
expert labels are the first to re-check. Rescoring the 46 would lift every model by +0.04 to +0.23 points.

## 4. A consensus flag, and its precision (audit 77)

A question is flagged when at least 6 of the 10 most accurate archives pick the same non-key option and more of them
pick it than the key. The flag fires on 36 of 55 Redux-miskeyed questions (65.5%) and on 294 of 2,553 Redux-OK ones
(11.5%), a ratio of 5.68, and recovers 34 of audit 76's 46. But the pre-registered precision prediction failed: only
65 of the 359 flagged questions the experts judged (18.1%) carry any error label. Across MMLU-Pro the flag fires on
1,210 questions (10.1%). Requiring all 10 to agree flags 201 and raises the precision to 36.4% (exploratory). On ids
6639, 8972, 9677 and 9947 all 10 panel models pick MMLU-Pro's key over the experts' answer.

## 5. Where flags on cleared questions point (audit 78)

On flagged miskeys the consensus option is one of MMLU's own four options 36 of 36 times. On flagged Redux-OK questions
it is an option MMLU-Pro added in 185 of 290 cases (63.8%), more than the 56.7% of the panel's scattered wrong picks
but about the 64.1% share added options have among all non-key options. So added options, which can make a second
answer defensible, explain part of the gap, while 105 flags on cleared questions still point at MMLU's own
distractors. Law, predicted to stand out, did not (69 of 139 added).

## 6. Duplicate archives (audit 79)

Audit 77's ten panel slots held only six model lines: three Claude 3.5 Sonnet archives, two GPT-4o versions and two
runs labelled `arx`. Archives of one model share wrong answers more often than the median pair of different models
(64.4-70.5% vs 55.3%), but a panel with one archive per named line is barely more precise: 60 of 315 (19.0%) against
65 of 359 (18.1%). Some differently named pairs share wrong answers more than any same-name pair (up to 81.5%), so
names capture only part of the dependence. The agreement threshold matters far more: with the one-per-line panel,
precision rises from 19.0% at 6 of 10 to 34.5% at 10 of 10 (20 of 58), while recall falls from 34 to 17 of 55.

## 7. An independent replication on MMLU (audit 80)

Audit 80 applied audit 77's flag, unchanged, to the original 4-option MMLU test set, using the per-question outputs of
HELM MMLU release v1.13.0 (78 models whose answers reproduce HELM's own scores; the panel is the 10 most accurate, from
Claude 3.5 Sonnet at 87.7% to Qwen2.5 72B at 83.3%) and all 5,700 Redux labels (106 miskeys, all joined). The flag
fires on 80 of the 106 miskeys (75.5%) and on 354 of 5,285 Redux-OK questions (6.7%), a ratio of 11.3, and 130 of the
484 flagged questions the experts judged (26.9%) carry an error label, against a 6.0% base rate. At 10 of 10 the
precision is 67 of 132 (50.8%). Five of six predictions held; the structural check failed on one part, because MMLU's
test set has 58 duplicated or unkeyed questions, not the at most 42 the pre-registration allowed for.

The gain over MMLU-Pro is mostly one subject. Virology holds 33 of the 106 miskeys, 30 of them flagged, and 39 of its
42 flagged, judged questions carry an error label. Without virology the precision is 91 of 442 (20.6%), close to
MMLU-Pro's 18.1%. Outside Redux's sample, all 10 panel models pick the same non-key option on 16 more virology
questions (post-hoc; listed in audit 80), the first MMLU questions this line of work would send to an expert.

## 8. Two harnesses agreeing (audit 81)

Audit 81 joined MMLU-Pro's MMLU-derived questions one-to-one to HELM's MMLU questions (same subject and question text,
at least 3 shared options; 6,155 pairs, 6,127 with the same key text) and compared three flags on those 6,127: HELM's
panel, the MMLU-Pro panel, and their agreement (both flag, with the same answer text). Both earlier audits were
reproduced exactly first, and all six predictions held. Agreement flags 227 questions; 38 of the 113 the experts
judged carry an error label (33.6%), against 64 of 309 (20.7%) for HELM's flag and 65 of 358 (18.2%) for MMLU-Pro's
on the same questions. It keeps 29 of the 39 miskeys HELM's panel flags (74.4%) but only 75 of the 245 cleared
questions (30.6%). The gain holds without virology (31 of 106, 29.2%, vs 55 of 300, 18.3%) and, post-hoc, without
virology and college chemistry (24.2% vs 15.5%). With both panels unanimous, 16 of 27 judged flags (59.3%) carry an
error label. Taking either panel's flag is the least precise choice (16.7%). The 113 agreement flags outside Redux's
sample lean on professional law (43) and moral disputes (11), where the judged agreement flags were mostly cleared,
so that list is likely less precise than 33.6%.

## 9. Item discrimination over every model (audit 82)

Audit 82 computed, for every MMLU question, the classical item-rest correlation r across HELM's 78 models: does a
model's accuracy on the other questions predict that it picks this question's key? A negative r means stronger models
pick the key less often. Negative r does find wrong keys: 78 of the 106 miskeys have r < 0, against 389 of 5,285
cleared questions (73.6% vs 7.4%). But the pre-registered headline failed. Taking the 1,207 questions with the most
negative r (the consensus flag's count), 121 of 504 judged carry an error label (24.0%), against 130 of 484 (26.9%)
for the top-10 consensus flag, and the threshold-free AUC is 0.898 against 0.912; without virology the order is the
same (18.3% vs 20.6%). The two flags share 765 questions, and those are the most precise set (102 of 301, 33.9%, about
the same as two harnesses agreeing). Post-hoc, the very top of the r ranking is the most precise short list in this
series: on 88 questions none of the 78 models picks the key, and 27 of the 37 the experts judged carry an error label
(73.0%), 21 of the 88 in virology.

## 10. How strong the panel must be (audit 83)

Audit 83 ranked HELM's 78 models by accuracy and cut them into seven disjoint panels of 10 (ranks 1-10 down to
61-70; mean accuracy 0.855 down to 0.641), each using audit 77's rule and scored against the same labels. Five of six
predictions held. Weaker panels flag more questions (2,405 for ranks 61-70 against 1,207) but catch about as many
miskeys (65 to 80 of 106 across panels), so the fixed rule's precision falls from 26.9% to 13.9%. Ranked by margin at
an equal review budget of 1,207 questions, precision falls more gently, from 27.6% to 18.8%, still three times the
6.0% base rate, and even the ten weakest models HELM ran (mean accuracy 0.52) reach 17.1%. The AUC barely moves from
the top panel to the sixth (0.886 to 0.912) and drops to 0.871 for the seventh. Adding ranks 11-20 to the top 10 did
not help (26.3% against 27.6% at the same budget), so strength, not size, carried the signal here.

## 11. The same question on MMLU-Pro, and a lead that did not hold (audit 84)

Audit 84 repeated audit 83 on TIGER-AI-Lab's 45 MMLU-Pro archives: four disjoint panels of 10 (ranks 1-10 to 31-40,
mean accuracy 0.779, 0.605, 0.439 and 0.327 on 10-option questions), the same rule, and an equal review budget of
1,210 questions, scored against the 2,725 Redux-judged MMLU-Pro questions (6.3% base rate). Six of seven predictions
held. Equal-budget precision falls 20.2%, 15.6%, 13.9%, 12.8% from the strongest panel to the weakest, which is just
over twice the base rate, and the margin AUC falls at every step (0.863, 0.817, 0.783, 0.710), more steeply than on
HELM's MMLU; these panels also span a much wider accuracy range. Pooling ranks 1-20 again did not beat the top 10 (19.2%
against 20.2%). The seventh prediction tested audit 82's post-hoc lead before looking and failed: 194 MMLU-Pro
questions are answered with the key by none of the 45 archives, and 22 of the 62 the experts judged carry an error
label (35.5%), no better than the top 10 voting unanimously (28 of 77, 36.4%), which also catches more of the 55
miskeys (21 against 15). Both are well above the base rate, but the 73% seen on MMLU did not carry over.

## 12. How many wrong keys are left, and which to read first (audit 85)

Audit 85 sorted all 13,984 HELM MMLU questions into four exclusive tiers: T1, no included model picks the key; T2,
the top 10 unanimous on one non-key option; T3, the top-10 flag otherwise; T0, the rest. Four of five predictions
held, and the tiers are cleanly ordered: among Redux-judged questions the wrong-key rate is 23 of 37 (62.2%) in T1,
34 of 102 (33.3%) in T2, 24 of 346 (6.9%) in T3 and 25 of 5,136 (0.49%) in T0, so tiers 1-3 hold 81 of the 106
wrong keys in 8.6% of the judged questions. Unreviewed questions land in tiers 1-3 as often as Redux's random sample
predicts (716 against 679.5 expected, z = 0.53).

The headline failed. On two fixed held-out halves of the expert labels, Redux's own subject rates predicted each
subject's wrong keys better than the tier rates (summed per-subject absolute error 91.3 against 115.5). Both got each
half's total about right, and the tier estimate's 95% interval held in both halves; the tiers lose on *where*,
because rates pooled over subjects cannot follow how damaged each subject's keys are: they expect far fewer wrong
keys in virology than Redux found there, and more in subjects where strong models often miss questions with sound
keys (on the unreviewed questions, the two estimates differ most in professional law, virology and moral scenarios).
Among the 8,331 unreviewed questions the subject rates estimate 92.5 wrong keys (95% interval 44 to 141) and the tier
rates 150.8 (118 to 183); with Redux's 106 that is about 199 (1.42%) or 257 (1.84%) in HELM's 13,984 MMLU questions.
These are estimates, not counts, and a subject with no wrong key in its sample gets an estimate of 0 with no spread,
so the subject interval is too narrow there. For any error label, the subject-rate figure for all of MMLU is 6.53%,
close to Redux's own 6.49% (post-hoc check).

One outside check, read after the fact: PlatinumBench (Vendrow et al.) hand-checked every MMLU high-school-mathematics
question that any of its models got wrong and relabelled none. For that subject's 170 unreviewed questions the tier
method expected 3.6 wrong keys and the subject method 0, so the independent review sided with the subject rates, as
the held-out test did. Audit 85 also published a ranked review queue: the 716 unreviewed questions in tiers 1-3 (51,
136 and 529), each with its tier's measured rates. Professional law fills 276 of the 716 rows, and those are the
rows most likely to overstate a wrong key.

## 13. Tiers scaled by subject, a narrow win (audit 87)

Audit 87 tested the repair suggested by audit 85's failure, designed after seeing it: keep the tier rates, but scale
them in each subject by k = (observed + 1) / (expected + 1) wrong keys among that subject's training questions, so a
subject with no wrong key in its sample is shrunk rather than set to 0, and virology is raised. On the same two
held-out halves, four of five predictions held. The summed per-subject error was 88.0, against 91.3 for subject rates
and 115.5 for tier rates, and the adjusted model won in both halves, but only by 1.7 and 1.6. The win depends on the
frozen prior: with a prior of 2 the error would have been 92.1, a loss; with 1/2 it is 84.3. Each half's actual count
fell inside the bootstrap 95% interval built on the other half (57 in 43-78; 49 in 37-65). For any error label the
adjusted model lost (199.0 against 195.5), so audit 85's subject-rate figure stays the reference there.

The adjusted model expects 112.3 wrong keys among the 8,331 unreviewed questions (95% interval 79 to 159), between
audit 85's two figures; with Redux's 106 that is about 218 in HELM's MMLU, 1.56% (computed from the reported
figures). Professional law contributes 30.4 of the 112, virology 15.7 and professional psychology 11.5. In the 716-row
queue, re-ranked by the adjusted probability, it expects 85.7 wrong keys, 62.2 of them in the first 200 rows. This is
the best-supported count in this series, with thin evidence that it beats plain subject rates.

## 14. A free-response benchmark with complete labels (audit 86)

Audit 86 asked whether the flag works better when answers are numbers rather than letters. It scored HELM Lite's
per-question GSM8K outputs (90 models, release v1.13.0; HELM scores a fixed 1,000 of GSM8K's 1,319 test questions)
against GSM8K-Platinum (Vendrow et al.), which labels every test question: in HELM's 1,000, 84 removed as flawed, 6
with a corrected answer, 77 reviewed and kept and 833 kept without review, a 9.0% error base rate. Five of seven
predictions held. The top-10 panel (mean accuracy 0.941) flags 22 questions with at least 6 of 10 on one wrong number,
and 19 are error-labelled (86.4%, Wilson 95% interval about 67% to 95%), against 26.9% for the same rule on MMLU and
18.1% on MMLU-Pro. Platinum's own filter, any panel model wrong, flags 204 at 33.3%. The margin AUC is 0.832. At an
equal budget of 22, precision falls from 90.9% for ranks 1-10 to 43.2% for ranks 41-50, a steeper fall than on MMLU.

The flag is a wrong-key detector more than an ambiguity detector: it catches 5 of the 6 corrected keys, and on all 5
the agreed number equals Platinum's correction, but only 14 of the 84 removed questions, so recall is 21.1% and the
pre-registered quarter failed. The no-key flag fires on only 3 questions (2 errors), too few to test. The 3 flags
Platinum kept, read after the run, are shared misreadings rather than label errors: leaving out the host's own seat,
compounding a rise stated as a share of the original price, and answering a total where the question asks per child.

A correction: audit 86's pre-registration said no one had scored HELM's GSM8K outputs against Platinum's labels.
Truong et al. (arXiv 2511.16842) had, from HELM's right-or-wrong matrix for the same 90 models, in a sensitivity
analysis of their item-statistics flags. Audit 86's addition is the answer-level consensus (which wrong number), the
panel-strength comparison, and the split between corrected keys and removed questions.

## 15. A second expert review of the same questions (audit 88)

Every precision figure above is scored against one panel, MMLU-Redux. Audit 88 put a second, independent review next
to it. Truong et al.'s Fantastic Bugs ranked MMLU items by an item statistic on HELM's right-or-wrong matrices and
published reviews of the top items: two licensed medical professionals for clinical knowledge and professional
medicine, a math-assessment psychologist for mathematics, and public sources such as Wikipedia for a five-subject set
(college chemistry, econometrics, computer security, abstract algebra, US foreign policy). We sorted each review as
*valid*, *key* (it names the answer key) or *other*, placed 171 of their 189 MMLU rows in HELM's universe (their key
equals HELM's on all 171), and compared three opinions on each question. All seven predictions held.

Where Fantastic Bugs names the answer key, Redux labels an error on 31 of the 38 it judged (81.6%) and a wrong key on
27 (71.1%), against a wrong key on 1 of 37 *other* questions (2.7%); none of the 32 judged *valid* questions carries a
Redux error label. The top-10 consensus flag fires on 26 of 43 *key* questions (60.5%) against 3 of 82 *valid* ones
(3.7%), and inside the five-subject split on 24 of 40 *key* questions against 6 of 30 *other* ones (post-hoc). Three
cautions: all 38 judged *key* questions come from the five-subject split, reviewed against public sources rather than
by experts; the medical splits hold almost no Redux errors (1 of 36 judged), so the *valid* agreement is expected;
and the sample was chosen for looking anomalous (37.4% of judged questions carry a Redux error label, against 6.0%
in Redux's random sample). Cohen's kappa between the two reviews is 0.41 (107 judged questions).

The flag fires on three questions the medical reviewers called valid. Read after the run, one is a shared model
misconception (the strong models pick an option that names an unusual tuning-fork frequency), and two are defensible
disagreements a vote cannot settle (cooling against fluids in heat illness, and two closely related ethics
principles). On GSM8K, the 16 published Fantastic Bugs rows are not, as a reading of the paper might suggest, 16
problems Platinum missed: Platinum's current release had removed or revised 11 of the 12 rows that name a problem in
the question, and 3 of the 4 it kept are rows the reviewer marked as HELM grading errors. The paper does not say which
Platinum labels it compared with. One of audit 86's three kept flags (GSM8K test position 1016) is among the 16;
Fantastic Bugs calls it a construct issue.

So the precision figures in this note do not look like an artefact of Redux alone, at least for answer-key problems in
the subjects where both reviews exist, and answer-level consensus adds information on top of an item statistic.

## 16. Recommendations

- **MMLU-Pro maintainers:** the 52 inherited keys are listed by `question_id` in audit 75; on 46 of them the experts'
  answer is an option and the models side with the experts. Ids 9677 and 6639, where the models side with the key,
  deserve a second expert look before any change.
- **Benchmark users:** the rescoring effect is small (under a quarter of a point per model), so leaderboards barely
  move; it is still a correctness fix.
- **Anyone using model consensus to find label errors:** treat a flag as a priority for review. At 6 of 10, about 1 in
  5 flags on MMLU-Pro and about 1 in 4 on MMLU carries an expert error label; at 10 of 10, about 1 in 3 and 1 in 2.
  On a free-response benchmark like GSM8K it is about 6 in 7, and the agreed answer is often the correction.
  Precision depends heavily on how damaged a subject's key is. De-duplicating models by name buys less than a point;
  raising the threshold buys much more, at a cost in recall; confirming a flag with a second harness and option list
  also helps (on the shared MMLU questions, 33.6% against about 20% for either panel alone).
- **Combining signals:** an item statistic over right-or-wrong answers (Fantastic Bugs) and answer-level consensus
  pick up overlapping but different problems. Inside items an item statistic already ranks high, consensus still
  separates answer-key problems (60% flagged) from items reviewers call valid (4%), so use both: the item statistic to
  build a short list, consensus to say which items on it are likely miskeys and what the right answer might be.
- **Free-response benchmarks:** consensus finds wrong keys but few ambiguous questions (14 of 84 on GSM8K); pair it
  with a broad "any strong model wrong" filter and a human read for ambiguity. Even 9 or 10 of 10 strong models can
  share one misreading, so read the question before changing a key.
- **Choosing a panel:** use the strongest models you can, and rank by margin at a fixed review budget rather than a
  fixed vote threshold, because a weaker panel's threshold flags grow with its own mistakes. A cheaper panel still
  works, at about two thirds of the precision on MMLU (ranks 61-70) and between about three quarters (ranks 11-20)
  and under two thirds (ranks 31-40) on MMLU-Pro; on GSM8K the fall was steeper (ranks 41-50 at under half). Adding
  weaker models to a strong panel, or pooling every model through item discrimination, did not help on either
  multiple-choice benchmark. Questions no model answers with the key are worth reviewing, but on MMLU-Pro they were
  no better a first pick than questions the top 10 reject unanimously (an earlier version of this note recommended
  them first, from the post-hoc MMLU reading), and on GSM8K there are almost none.
- **Counting what is left:** use model votes to decide *which* questions an expert reads, and a random expert sample
  stratified by subject to estimate *how many* are wrong. In audit 85, rates pooled over subjects from model-vote
  tiers misplaced wrong keys across subjects; in audit 87, scaling the tiers by each subject's sample helped only a
  little, so the votes add at most a small correction to a stratified sample.
- **Re-reviewing MMLU:** read audit 87's re-ranked queue (`review_queue_adjusted.json`) from the top; the model
  expects about 62 of its 86 wrong keys in the first 200 rows. Treat law and moral scenarios rows with more doubt.

## Limits

MMLU-Redux labels are expert judgments, not verified facts, and cover 100 questions per subject. A flag on a cleared
question may be a shared model mistake, a second defensible answer, or an error the experts missed; these audits
cannot tell them apart. Audits 75-79 and 84 use one harness (TIGER-AI-Lab's 5-shot chain-of-thought archives); audits
80, 82, 83, 85, 87 and 88 use another (HELM's joint multiple-choice prompt), with models up to late 2024; audit 81
combines them, but the two panels share model families (Claude 3.5 Sonnet, GPT-4o, Gemini 1.5 Pro). In audits 83, 84
and 86 the panels differ in more than accuracy (size, age and family). The virology finding and the 16 unreviewed
virology questions are post-hoc readings, not tested predictions; audit 82's "no model picks the key" reading was
tested in audit 84 and did not hold on MMLU-Pro. Audits 85 and 87 rest on Redux's random sample of 100 per subject,
and audit 87 was designed after seeing audit 85 and scored on the same halves. In audit 86, GSM8K-Platinum reviewed
only questions its own models missed, so recall is measured against the errors it found; its 22 top-panel flags are
a small sample. The PlatinumBench MMLU comparison covers one subject and was not joined question by question. In
audit 88 the two reviews agree mainly in five subjects reviewed against public sources, the groups are small (32 to
38 judged questions), and the review categories are our reading of the reviews' first words.

## Related work (checked 2026-11-08)

Gema et al., "Are We Done with MMLU?" (NAACL 2025, arXiv 2406.04127) built MMLU-Redux and estimate that 6.49% of MMLU's
questions contain an error. Wang et al., "MMLU-Pro"
(NeurIPS 2024, arXiv 2406.01574) built MMLU-Pro and keep a changelog of key fixes. Kim et al., "Correlated Errors in
Large Language Models" (ICML 2025, arXiv 2506.07962) measure shared wrong answers across models. "Nine Judges, Two
Effective Votes" (arXiv 2605.29800) shows correlated errors limit LLM-judge panels. "Auditing MCQA Benchmarks through
Probability Landscapes" (arXiv 2608.30372) ranks MMLU items for review from model probabilities. Land and Bikel,
"Auditing LLM Benchmarks with Item Response Theory" (EMNLP 2026, arXiv 2605.30504) flag likely mislabels from 114
models' answers on seven benchmarks (not MMLU or MMLU-Pro) and score them against an LLM reviewer. Hofmann et al.,
"Fluid Language Model Benchmarking" (COLM 2025, arXiv 2509.11106) note that low-discrimination items are often
mislabeled and count MMLU-Redux mislabels in the items they select. Jiang et al. (arXiv 2604.03244) compute item-rest
correlations on 567 MMLU items. Nahum et al., "Are LLMs Better than Reported?" (EMNLP 2025, arXiv 2410.18889)
re-label data with an LLM ensemble and report that error detection improves as the ensemble grows. Vendrow et al.,
"Do Large Language Model Benchmarks Test Reliability?" (arXiv 2502.03461) revise fifteen benchmarks into "platinum"
versions with mislabeled and ambiguous items removed, choosing questions for review when any of their models errs;
their MMLU high-school-mathematics review relabels no key and agrees with MMLU-Redux on 99 of the 100 questions both
reviewed. Zhang, Cai and Chen, "Beyond the Singular" (arXiv 2502.08943) read questions one model answers consistently
but is scored wrong on as likely GSM8K label errors. Truong et al., "Fantastic Bugs and Where to Find Them in AI
Benchmarks" (NeurIPS 2025 Datasets and Benchmarks, arXiv 2511.16842) flag invalid items in nine benchmarks (GSM8K, MedQA, OpenBookQA and MMLU subsets among
them) from HELM's right-or-wrong response matrices with tetrachoric correlation, Mokken scalability and item-total
correlation, report up to 84% precision in expert review of their top 50 items, and compare their GSM8K flags with
GSM8K-Platinum's labels; they do not use which wrong answer models give or MMLU-Redux's labels, and they publish their
reviews (`stair-lab/fantastic-bugs`), which audit 88 compares with MMLU-Redux. Paquin and Jain, "What Does MMLU Actually Measure?"
(arXiv 2609.09372) fit item-response models to 1,000 open-weights models on all of MMLU's test items to study
difficulty, not label errors. We found no earlier count of the Redux miskeys MMLU-Pro inherited, or test of answer
consensus, within or across harnesses, of item discrimination or of panel strength, against Redux's expert labels on
MMLU-Pro or MMLU, no held-out test of a model-based estimate of MMLU's remaining wrong keys, no test of an
answer-level consensus flag (agreement on the same wrong number) from HELM's GSM8K outputs against GSM8K-Platinum's
labels, and no comparison of MMLU-Redux's labels with a second published review of the same MMLU questions.

## Code and data

Repository: github.com/munimtechnologies/munimtechnologies.github.io. Folders (Apache-2.0 code, CC BY 4.0 text and
results): mcq-mmlu-pro-redux-inheritance (75), mcq-mmlu-pro-inherited-miskey-models (76),
mcq-mmlu-pro-model-consensus-miskeys (77), mcq-mmlu-pro-consensus-added-options (78),
mcq-mmlu-pro-consensus-distinct-panel (79), mcq-mmlu-helm-consensus-miskeys (80),
mcq-mmlu-cross-harness-consensus (81), mcq-mmlu-helm-discrimination-miskeys (82),
mcq-mmlu-helm-panel-strength (83), mcq-mmlu-pro-panel-strength (84), mcq-mmlu-helm-review-queue (85, with the review
queue), gsm8k-helm-consensus-platinum (86, with the candidate list), mcq-mmlu-subject-adjusted-tiers (87, with the
re-ranked queue), mcq-mmlu-fantastic-bugs-redux (88, with one row per Fantastic Bugs row). Catalogue:
eval-reliability-audits. Only ids, positions, letters, numbers, counts and hashes are published, never question or
option text. MMLU and MMLU-Pro are MIT-licensed; MMLU-Redux 2.0 is CC BY 4.0; GSM8K is MIT; GSM8K-Platinum's labels
are CC BY-SA 4.0; Fantastic Bugs' data is MIT; HELM is Apache-2.0.
