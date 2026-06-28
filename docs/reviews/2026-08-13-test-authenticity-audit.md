# Test authenticity audit (plan entry)B-1)

- Date: 2026-08-13
- Scope: kernel of definitive indicators (indicator)KS / AUC / PSI / Box/ Stability/ Pressure/ Bad rate/ Pass rate/ Impact/ waterfall / (Consistent fractions)
- Nature of conclusion: Audit only. No code changes; only product is in this document.

## 1. Methodology and calibration

### 1.1 Attention.

As required by the mandate, focus on the following definitive indicators and their testing:

| Domain| kernel realization| Main Tests|
|---|---|---|
| KS / AUC / PSI Platform reference realization| `marvis/feature/metrics.py`(`feature_ks` / `feature_auc` / `compute_psi` / Weighted variant)| `tests/test_feature_metrics.py` |
| Certification LevelKS/AUC/PSI/Box| `marvis/validation/effectiveness.py`,`marvis/validation/binning.py` | `tests/validation/test_effectiveness.py`,`tests/validation/test_binning.py` |
| Modelling indicator layers| `marvis/…/modeling`(`compute_model_metrics`) | `tests/test_modeling_recipes.py` |
| Bad rate/ Pass rate/ Impact| `marvis/packs/strategy/backtest.py`,`tradeoff.py`,`typed_backtest.py` | `tests/test_strategy_tradeoff.py`,`tests/test_strategy_typed_backtest.py` |
| Stability/ waterfall / PSI Normalization| `marvis/packs/strategy/pool_stability.py`,`candidate_stability.py` | `tests/test_strategy_pool_stability.py` |
| Consistency of scores| `marvis/validation/reproducibility.py` | `tests/validation/test_reproducibility.py` |
| Sample statistics (bad rate)/Distribution)| `marvis/validation/sample_stats.py` | `tests/validation/test_sample_stats.py` |
| Pressure test/ Risk slotting| `marvis/validation/stress_test.py`,`stress_risk.py` | `tests/validation/test_stress_test.py` |
| Datajoin / dedup / profiling | `marvis/data/join_engine.py`,`dedup.py`,`descriptive.py`,`profiler.py` | `tests/test_join_engine.py`,`tests/test_data_dedup.py`,`tests/test_data_descriptive.py`,`tests/test_sampler_profiler.py` |
| Rendering indicator tables| `marvis/metric_tables.py` | `tests/test_metric_tables.py` |

### 1.2 Classification (task-based)

- **A**:It's a word of the hand./External gold constant - numbers coded hard in tests, not extrapolated from the realization formula.
- **B**:Only internal consistency is measured - with another module/Algorithms are calculated, or only structural nature (scope, direction, non-negative, certainty).
- **C**:Expectations by Import/Copy the calculated function formula (self-identify)/ Mirrors are fulfilled.

### 1.3 Methodological note

1. For each key indicator function, locate the only one/Main test, judging the source of the desired value by article: hard-coding constant (in the case of a single-digit test)A),Independent recovery or structural assertion (A/AC.254/5/Add.1 and Corr.1)B),Call for the same realization or handwritten formula (C).
2. Yeah.C Class test records`Documentation:Line Number`.
3. Check five key indicators (in thousands of US dollars)KS,AUC,PSI,Is there at least one of them?A Gold anchor type.
4. - The mutation spot check.**Read and finish the drill**(No actual injection of mutations, no code changes) and judgment that "class sequence reverses"/ The following is a list of the most recent examples of the "symmetrical error" that has been used to make the existing tests red.

> Note: This audit was conducted by `test function ' instead of `12 ',000+ The number is this audit.**Actual graded**, not full count.

## 2. Classified statistical tables by indicator area,A/B/C Test Function Count)

| Indicator Fields| A(Gold Constant)| B(Coherence/Structure)| C(Self-prove/Mirror)| Is there a non-degradable gold anchor?|
|---|---|---|---|---|
| KS(`feature_ks` ♪ And sealed ♪| 3(Including 1 non-degradable weighted gold`4/7`) | 3 | 1 | Component: Non-weightedKS 0-Five-Five-Five./1 Extreme anchor+ 1 Weighted 4/7 |
| AUC(`feature_auc` ♪ And sealed ♪| 5 | 1(sklearn ♪ And I'm not gonna let you go ♪| 1 | Yes (0).0/1.0/0.5/12⁄14 + sklearn) |
| PSI(`compute_psi`/`feature_psi`) | 1(Decline 0 only.0) | 3 | 4 | **Yes**(No non-degradable gold constant)|
| Bad rate/ Pass rate| 6 | 2 | 0 | Yes.|
| Box/ `bin_table` / Cumulative core| 5(Ham`bin_table` Gold Locked)| 3 | 1(♪ I'm stuck in gold test ♪| Yes.|
| Stability/ waterfall / PSI Normalization| 3 | 4 | 0(Internal verification is achieved)| Yes (waterfall counts + `max_abs_share_delta`) |
| Pressure test/ Risk slotting| 0((Structure direction)| 6 | 0 | No (pressure)KS/PSI Slotting threshold part bybatch runner Cover, see§4) |
| Consistency of fractions (in`scores_match_at_precision` + State threshold)| 4 | 5 | 0 | Yes.|
| Sample statistics (bad rate)/Distribution/(Cyclical)| 3 | 2 | 0 | Yes.|
| Datajoin / dedup / profiling | 6 | 4 | 0 | Yes.|
| Rendering indicator table (in thousands of US dollars)`metric_tables.py`) | 0(Pure rendering, no recalculation)| 8 | 0 | Not applicable (no indicator for rendering layers)|

> Note: The number in the table is based on the article-by-article test function of the audit. When multiple assertions appear in the same test function, they are counted once to the highest level of that function.

## 3. C Type test list (file):Line number)

The expectations of these tests are passed.**Import or copy the tested function formula**Got. Achievement and testing, if driven by the same wrong formula, will "removed together and still green."

1. `tests/test_feature_metrics.py:117` — `test_compute_psi_and_feature_psi_use_shared_edges_and_smoothing`:ExpectationsPSI Write by hand directly by formulae`(0.75-0.5)*log(0.75/0.5) + (0.25-0.5)*log(0.25/0.5)`,Yes.`compute_psi` formulae.
2. `tests/test_feature_metrics.py:130` — `test_compute_psi_renormalizes_after_zero_bucket_smoothing`:I want to do the same "spink smooth"+ The (Approach of the (Approach of the (Approach of the (Appendix) is a combination of the (Appendix to the (Appendix) formula.
3. `tests/validation/test_effectiveness.py:303-308` — `test_psi_stability_table_uses_shared_compute_psi_smoothing`:`sum(row.psi) == compute_psi([expected_pct...], [actual_pct...])`,Use detected`compute_psi` Recalculate expectations.
4. `tests/validation/test_effectiveness.py:170-172` — `test_compute_auc_matches_canonical_feature_auc`:`compute_auc(...) == feature_auc(...)`.`compute_auc` Ben is.`feature_auc` Slare wrapping (direct)`return _feature_auc(...)`),It's a synonym. It's a "floating seal" thing. It's not.AUC The value is correct.
5. `tests/validation/test_effectiveness.py:191-193` — `test_roc_ks_curve_scalar_matches_canonical_feature_ks`:`curve.ks == feature_ks(...)`.This is...ROC CurveKS with cumulative distributionKS Mutual authentication achieved by two platforms (higher than 4 because algorithms have different paths) but still "platform code versus platform code" with no external/Hand count anchor.
6. `tests/test_validation_debt.py:28-29` — `compute_ks == feature_ks`,`compute_psi == feature_compute_psi`:Two.`validation.binning` Encapsulate with`feature.metrics` The synonym of the original function is repeated (encapsulated directly as a commission).
7. `tests/test_feature_iv.py:10-33` — `test_smoothed_woe_iv_kernel_matches_inline_formula`:`_inline_woe_iv` It's a line-by-line mirror of the measured formula.docstring "Specify."kept here as the ground truth the shared kernel must reproduce]).
8. `tests/test_feature_encode.py:85-88` — `test_categorical_woe_encode_matches_hand_computed_smoothed_woe`:ExpectationsWOE Inline with formulae (in`np.log(((5+0.5)/(total_good+0.5*n_groups)) / ...)`).
9. `tests/validation/test_binning.py:97-149` — `test_accumulate_bin_metrics_matches_legacy_loop_both_directions`:`_legacy_accumulate` It is a line-by-line reproduction of cumulative nuclear logic as a expectation.**Notes**:The test itself was mirrored, but was...`test_bin_table_golden_values_preserved`(Article 152-174 Okay, hard code.lift/ks/cum The gold figures are impregnated and the risk is mitigated.
10. `tests/test_modeling_recipes.py:157-158` — `test_compute_model_metrics_uses_platform_feature_metrics_and_overfitting`:`metrics.train_ks == feature_ks(...)`,`metrics.train_auc == feature_auc(...)`.Modelling layers of indicators cross-check with Platform reference functions, non-external anchor.

> Contrast:`tests/test_feature_metrics.py:31-35`(`_naive_ks` Threshold scan)**Not includedC**——It's a stand-alone algorithm (threshold-scan) and not a formula copy.B A valuable one in the category.

## 4. Key indicator gold anchorpoint reconciliation

| Indicators| Is there a problem?A Gold anchors, class| Location and Nature of anchor|
|---|---|---|
| KS | **Yes (but extreme)** | `test_binning.py:56`(`compute_ks` = 1.0 Perfect separation;`test_effectiveness.py:211`(ROC KS = 1.0);`test_modeling_recipes.py:228`(WeightedKS = `4/7`,sole non-degradable arm anchor; degraded 0.0(`test_binning.py:62`,`test_feature_metrics.py:36`) |
| AUC | **Yes.** | `test_feature_metrics.py:103-104`(Directional sensitivity 0.0 / Direction not relevant 1.0);`test_effectiveness.py:116/142/151`(1.0 / 0.0 / 0.5);`test_modeling_recipes.py:227/229`(Weighted`12/14`);Plussklearn # # Match #`test_feature_metrics.py:95`) |
| PSI | **No (no non-degradable gold)** | The only gold is "same distribution."→ 0.0]Decontamination anchor (Danish anchor)`test_binning.py:68`,`test_effectiveness.py:96`,`test_modeling_recipes.py:230`);Non-degradable values only byC Type formula mirrors and`>0` Structure assertion overwhelms|
| Bad rate| **Yes.** | `test_sample_stats.py:42/52`(0.5);`test_strategy_tradeoff.py:42-46`(1/3,0.5,1.0);`test_strategy_typed_backtest.py:135-140`(0.5) |
| Consistency of scores| **Yes.** | `test_reproducibility.py:347-349`(`scores_match_at_precision` Hand rounded to hand; status threshold (98 per cent)/95%/max_abs_diff 1e-4)Sorted (%2)`test_reproducibility.py:86-190`) |

### 4.1 List of indicators for no gold anchors (to be reinforced)

1. **PSI((most important gap)**——The only five key indicators lacking non-degradable statusA The gold-class constant. The current value is only given to theC Mirror+ `>=0`/`>0` Structure assertion overlay, systemic formula error (misagreement)/Normalization/"Flucture" will be "realized."+The mirror test is green together."
2. **Non-weightedKS Non-degradable value**——0-Five-Five-Five..0/1.0 Extreme anchor+ One weight`4/7`;`feature_ks` It's...change-points/cumsum The middle logic is not a hard-coded 'medium'KS Other Organiser`_naive_ks` Threshold scan is independently recalculated, but no hard-coded number is available.
3. **Pressure testKS Decay/ PSI Slotting threshold**(`stress_risk.py::ks_drop_ratio` / `stress_ks_risk` / `stress_psi_risk`)——`ks_drop_ratio` The arithmetic itself does not see direct gold tests;`stress_psi_risk` 0 of.10/0.25 The slots are only available`test_validation_batch_runner.py:651-675` The long run.batch runner Indirect coverage (0).15→medium,0.30→high),`stress_ks_risk` 0 of.10/0.20 The threshold is not seen as a direct anchor.
4. **Indicator Table Rendering Layer (not applicable)**——`test_metric_tables.py` Feeding indicator values with a clamp, claiming only rendering/Layout/Formatting, underB Category; it would not have recalculated the indicator, so "no gold anchor" is not a flaw, but means**The retrofitting layer doesn't go upstream with the wrong numbers.**.

## 5. Conclusions of the random check of variations (extract, not actually injected)

### 5.1 `feature_auc`(AUC)——["The order of categories is reversed."

Achieved`pos = scores[target==1]` / `neg = scores[target==0]` Do it.Mann-Whitney.If you...pos/neg Consensual (equivalent totarget 0/1 Inverted) non-directional undirected pathAUC ♪ Turn it over ♪`1 - auc`.

- Is it red:**Yes.**.`test_feature_metrics_reports_direction_agnostic_auc_for_single_features`(Zero..0 and 1.0),`test_overall_auc_keeps_declared_positive_score_direction`(Zero..0),`test_feature_auc_matches_sklearn_rank_auc`(sklearn I'm not sure I'm gonna make it.
- ConclusionsAUC Other Organiser**Independence anchor**(Hand is gold.+ sklearn)Grab it, protect it with a high intensity.

### 5.2 `feature_ks`(KS)——["Symbols Counter" and "Classure Orders Against"

- Symbol to reverse (deleted)`abs` or plus negative sign:**Red**.`test_compute_ks_known_values` The assertion.+1.0(The negative value does not match)`test_overall_metrics_cover_all_three_splits` The assertion.`0 <= ks <= 1`,`test_roc_ks_curve_scalar_matches_canonical_feature_ks` - No, it's not negative.ROC KS.
- Category Order Reverse (%1)swap bad/good Count:**Not red.**,But it's not.bug——KS Use`abs(cum_bad - cum_good)`,Yeah.bad/good Symmetry.
- It's more hidden.change-points/cumsum Intermediate logic error: only`_naive_ks` Threshold scan ()B (b) Independent recalculation of the category) to withstand the non-degradable median;/1 Extreme gold is powerless.
- Conclusion: symbol error is caught; "non-degradableKS "The value" is still missing a hard-coded gold anchor.KS `4/7`).Proposal for a non-degradableKS Golden anchor (see§6 P1).

### 5.3 `compute_psi`(PSI)——[Symbol takes the opposite of "formula agreement systemic error"

- Add negative sign (%2)`max(0, -sum(...))` → Constant 0:**I'm gonna get it.C Class test grabs.**(`test_compute_psi_and_feature_psi_use_shared_edges_and_smoothing` I'm looking for a positive number. But it's the right thing to do.C The mirror test - the strength of protection depends on "the author of the mirror test is right about the agreement."
- Systematic agreement error (e.g. smooth)/Quite a step, a Zero-Cop deal is wrong, and is achievedC Mirror image written as per wrong agreement:**Not red.**.Because...PSI There's no independence.A The gold-type constant, achieved with mirror tests, is wrong and green.
- Conclusions**PSI It is the weakest of the five key indicators for protection against variability**.This is the most needed anchor for this audit (see§6 P1).

## 6. Ocupine of anchors (in order of priority)

Priority criteria: determining impacts under iron× Current anchor strength gap× Costs of anchoring.

### P1 — PSI Non-degradable gold constant (highest priority)

- Reason: The only key indicator lacking a non-degradable gold anchor;`compute_psi` Yes.PSI Stability,pool/candidate stability,PressurePSI The common base, the error is magnified in multiple reports.
- How?`tests/test_feature_metrics.py` Add a test to the hard-coding manual set for distribution.PSI value. For example:`expected=[0.5, 0.5]`,`actual=[0.6, 0.4]` → Hand count.`(0.6-0.5)*ln(0.6/0.5) + (0.4-0.5)*ln(0.4/0.5)` and**Write dead values directly**(≈ `0.040547`),Don't use it.`np.log` Expression, do not tune`compute_psi`.And we'll add a Zero-Cave-Cave-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Catch-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-Ca-C-+ The government has been working on a new policy for the last two years.

### P2 — Non-weightedKS Non-degradable gold constant

- Rationale:`feature_ks` Yes.KS Full link (inoverall / monthly / ROC / (e) The base of pressure decay; the existing gold is only 0/1 Extreme.
- How to: Construct a small sample of "incomplete separation" (e.g. 8)-12 Fine, good and bad. Use a paper and pen./Independent script calculatesKS Median (e.g. 0).4~0.6),Yes.`tests/validation/test_binning.py` or`tests/test_feature_metrics.py` Hard Encoding of the Number (Reserve)`_naive_ks` ScanB Category supported, but newA Class hard code.

### P3 — Pressure slotting threshold gold (%)`stress_risk.py`)

- Rationale:`ks_drop_ratio` Alc. and`stress_ks_risk` 0 of.10/0.20,`stress_psi_risk` 0 of.10/0.25 Lack of direct anchoring of thresholds (currently onlypsi The long run.batch runner (b) Indirect coverage).
- How to: Add`tests/validation/test_stress_risk.py`,Yeah.`ks_drop_ratio`(Like`(0.5, 0.4) -> 0.2`,Baseline is 0/NaN -> None),`stress_ks_risk`/`stress_psi_risk` Threshold boundary (0).10,0.20,0.25 and`+1e-12` The "F" is a "F" and "F" is a "F"-coding ".

### P4 — C "Golden" of mirrors.

- Rationale:`test_binning.py` It's...`_legacy_accumulate` Mirror has been`test_bin_table_golden_values_preserved` nail; the rest of the mirror (WOE inline,PSI inline)At least one hard-coded digital anchor should be attached.
- How?`test_feature_iv.py` There's one.`total_iv == 2.145917` Gold (good);`test_feature_encode.py` It's...WOE The inner circle wants to add a dead value. Here.§3 Paragraph 1/2 ArticlePSI Inline test to write dead values.

## 7. I can't complete the check.

1. **Full 12,000+ Number of poor steps tested**——This test function is only for the certain kernel, in a hierarchical order, not exhaustively located (especially)strategy Masse2e/Render/Organization test. The rest of the fieldC Class tests may exist but are not listed.
2. **Actual mutation injection validation**——Iron is bound by "no code changes" and no real mutation tests are performed (in the case of the Queen of the West).mutation testing);§5 All for the results of the reading exercise, which is not realistic.
3. **`test_modeling_recipes.py:157-158` It's...C/B Rating**——Not deep`compute_model_metrics` Internal confirmation of direct call`feature_ks/feature_auc`;It is synonymous if it is directly delegated internally.C),If Independent PathB Class intervalidation. Current conservatively recorded as "platform function intervalidation"C(Listed) and may be subject to rigid classification.
4. **`marvis/metric_tables.py` Render Layer**——Non-recalculation indicator (pure rendering) confirmed, but not one by one for formatting of the render layer/Rounded up the possibility of a secondary change in the indicator value.
5. **strategy Domainimpact cube / economics More nuanced anchors**——`test_strategy_impact_cube.py`,`test_strategy_economics.py` Waiting is not graded; the rate is covered in this report only/Pass rate (%)tradeoff/backtest)andwaterfall Stability.
