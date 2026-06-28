# Real Materials Machine Pre-Check Report

> **A snapshot of historical failure is no longer valid and cannot be used as evidence of current acceptance.** The report is in the old version of the acceptance script.
> Generate, whereA2/A4/A5/B5 It's...`N/A` Now they'll be judged as missing evidence.`FAIL`.Current script requirements
> It's also a copy of the same actual material.JOIN andVintage Mission; besides, Ben's already been in the picture.
> `BLOCKED_MACHINE`,And it's been recorded.A1 Failures and failure of model monitoring must be repaired and regenerated.

- Generating:`2026-07-23T16:50:11.028447+00:00`
- Mission:`<governed-real-material-task>` · Controlled real-material modelling mission
- Planned:`<completed-modeling-plan>` · `done`
- Machine determines:**FAIL**
- The conclusion is that:**BLOCKED_MACHINE**

> Only the warehouse is verified in this report/SQLite/Evidence of machine-verifiable production is not equivalent to artificial signature.
> External finance, provisions, risk statement calibres and the signatory signature are never automatically filled.

## A/B/C/D Verify

| Item| Status| Conclusions| Evidence| Manual Actions|
|---|---|---|---|---|
| A1 | FAIL | The sentry values were detected, but the lead model ' s pre-processing chain was not traceable.| screen_features Detectedsentinel Columns; precise columns are retained only in the audit of controlled assignments;model_artifacts.params.preprocessing_chain_traceable=false | — |
| A2 | N/A | Current mission is model development, not implementedvintage Calculate.| plan.template_id=modeling | — |
| A3 | PASS | The feature filter did not discard the label and no silent exclusion was observed.| screen_features Unreported tags dropped; accurate count retained only in the audit of controlled assignments.| — |
| A4 | N/A | Did you finish the modelling program?join gate,No modeling products can be reviewed.ID key.| plan steps do not contain data_join tools | — |
| A5 | N/A | Did you finish the modelling program?join gate,The model product can't review the void./Zero fill key.| plan steps do not contain data_join tools | — |
| A6 | PASS | Other OrganiserOOT,The splitting evidence is retroactive.| split_col andholdout_values Recorded;train/test/oot Neither is empty, and the exact number of business lines is retained only in the audit of controlled assignments.| — |
| B1 | MANUAL | vintage The accumulated bad debt rate must be reconciled with external business calibres and there is no alternative real ground value in the warehouse.| no external finance/risk ground truth supplied | Fill out external caliber sources, measurementsvs caliber and signature by responsible person (CLUS)B1). |
| B2 | MANUAL | GroupELThere must be a reconciliation with external operations, and there is no alternative ground value in the warehouse.| no external finance/risk ground truth supplied | Fill out external caliber sources, measurementsvs caliber and signature by responsible person (CLUS)B2). |
| B3 | MANUAL | Groupbad_rateThere must be a reconciliation with external operations, and there is no alternative ground value in the warehouse.| no external finance/risk ground truth supplied | Fill out external caliber sources, measurementsvs caliber and signature by responsible person (CLUS)B3). |
| B4 | MANUAL | Internal to the PlatformKS Aligns the selection results with the model card; with independent recalculation/External reconciliations of historical models still need to be performed manually.| internal_consistency=True;train/test/OOT KS The source code was not written in the managed mission audit.| Provide independent recalculation or historical modelKS,♪ And finishB4 Signature.|
| B5 | N/A | No current completion planjoin Steps;join Matching rates are subject to separate acceptances for data processing tasks.| no data_join step in completed modeling plan | — |
| C1 | PASS | The training output recorded real selection of indicators.| train_models.selection_metric='test_ks(overfit-penalized)'; select_experiment.selection_reason='User-assigned experiment.' | — |
| C2 | PASS | The step evidence envelope contains code lists of Hash, parameter Hash, data references and random seeds.| manifest_hash=True; input_hash=True; source_dataset_refs=True; seed=True | — |
| C3 | PASS | Red flag for reconciliation by anti-shaped shape/Double-track reconciliations are validated on the regression network and do not depend on visual observations by the operational staff.| tests/test_dirty_shape_regression.py + tests/test_reconcile_reference_numbers.py | — |
| D1 | PASS | Select feature onlytrain Proposed above.| select_features.fit_split='train';The number of training lines was recorded in the audit of controlled assignments.| — |
| D2 | PASS | None of this assignmentNaN (a) Labels;NaN The door is also covered by the re-entry of the opposing shape.| The tag missing count is retained only in the audit of the controlled missions;tests/test_dirty_shape_regression.py::test_nan_label_screen_requires_confirmation | — |
| D3 | PASS | The assignment was not carried outtrain+test refit,There is no random 5%headline Imposing a problem.| select_experiment.refit={'applied': False, 'requested': False, 'reason': 'No full training requested(refit_on_train_plus_test=false).'} | Ifrefit=true,Checking model cardspre-refit/Variance in deployment.|

## Products

- report: PASS
- native_model: PASS
- pmml: PASS
- model_card: PASS

## Model governance

- Monitor status:`fail` · Model risk review required before delivery
- Limitation: Pre-treatment chain is not retroactive: the training data set does not have pre-processed blood records and cannot confirm the integrity of the scoring re-laying.
- Limitation: Select strategy alert:train-test KS The gap exceeds the threshold 0.1,There was a risk of alignment (no interruption of selection); precise indicators were retained only in the audit of the controlled missions.
- Limitation: Model risk review required before delivery

## It's still manual.

- B1-B5 external ground-truth reconciliation and accountable signatures; the script cannot and will not fabricate them.
- The finisher should be`docs/plans/v2-real-materials-reconciliation-checklist.md` Fill in external calibres, measured values and signatures.

## Counter-shape and double-track reconciliation back

Implementation:

```bash
PYTHONPATH=.:tests /opt/miniconda3/envs/py_313/bin/python -m pytest -q \
  tests/test_dirty_shapes_generator.py \
  tests/test_dirty_shape_regression.py \
  tests/test_reconcile.py \
  tests/test_reconcile_reference_numbers.py
```

Results:`66 passed in 2.00s`.
