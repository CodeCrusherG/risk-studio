# Guide to the use of sample weights (in thousands of US dollars)leakage-risk / business-rationale)

`sample_weight_col`(Modeling Settings"Sample weight column")The proposed mix weights are used to give different samples different weights during training.**Not as a feature.**,But it changes the proposed target of the model - it is more dangerous to use the wrong weight than to use it, because it does not appear in the importance of the characteristic, it only distorts it quietly.KS/AUC The assessment indicators and final scores.

This Guide explains when the sample weight should be used, what signals indicate the risk of leakage in the weighting, and when approval should be given/A template of business reasons that you can cite during the evaluation. Corresponding track items:LT-14.

## When should we use sample weights?

The sample weights are valid for only three types of uses and should be independent of the label itself:

1. **Sample weights (%)sampling weight)**:Training samples are not obtained by simple random sampling (e.g. by layer, by time period, by rare group oversampling)/The weight is used to correct the sample distribution back to the overall distribution. The reason should be clear."What's the sample design?",Not"How's the sample?".
2. **Rejects inference of weight (in thousands of years)reject inference weight)**:When samples are included in training that are rejected, undiscounted or not observed, weights are used to demonstrate the credibility of the samples/Coverage adjustment (e.g.,parceling,fuzzy augmentation The weights that arise should be used to justify the rejection of extrapolation, rather than the strength or weakness of the label.
3. **Business strategy weights (BDS)business weight)**:Business clearly requires models for certain categories of clients/Channels/The product is more sensitive (e.g., the new customer acquisition strategy requires a sampling channel) and weights are derived from the rules of business document rather than from the reverse coefficients from the outcome data.

If it's not clear which weight comes from the above, or which weight is the value itself,"A function calculated with a label",Sample weights should not be used.

## Leak risk signal

Any of the following signals should be treated as**After-prime results leaked.**Treatment, not simple"Data quality issues":

- **Weights are strongly associated with labels**:The weight column is highly correlated with the target column (good and bad labels, overdue days, etc.). This usually indicates that weight is not set independently, but is derived from the result itself — for example, by taking the overdue days directly, the interest rate penalty amount as weight, which is equivalent to feeding the label information back to the model)s proposed assembly process.
  - Platform side signals:`choose_modeling_spec` Modeling door ()modeling setup gate)The candidate weight column is calculated as the coefficient associated with the sample of the target column, written in`sample_weight_diagnostics[].leakage_risk`(`"high"` / `"low"`)and`target_correlation`;Corresponding coefficient absolute value≥ 0.3 Mark as`"high"`,And at the door.`override_guidance` It gives a hint in Chinese (see below)"Platform Inline Hint").It's a crude particle size signal, not a final conclusion.`"low"` It doesn't mean it's safe.`"high"` Nor does it imply a refusal, but a reminder requires manual confirmation of business reasons.
- **Weights are derived from post-prime information**:The weighting of the weighting depends on the field that arises after the loan (late state, catalytic result, actual repayment performance, post-prime risk disposal action, etc.). Any information structure that exists after loaning will allow the model to train for weighting."Yeah."Information for the future.
- **weight column name/Can't be traced.**:The weight column does not have the corresponding sample design document, rejection of the inference method description, or source of the business rules, but is a column of data that is empty.
- **Weights drift over time and change with the latest bad rate**:If the weight is on a monthly basis,/The process of generating weights is generally illustrated by the results themselves, when the batch is generated in order of batch and distribution is highly consistent with the trend over time and the actual bad debt rate.

## Business case template

When modelling settings confirm sample weighting, it is proposed to supplement the business case (in the mission note or evaluation record) with the following template:

```
weight column:<column_name>
Weight type: sample weight/ Rejects extrapolation of weights/ Business strategy weights (three or three)
Source of weights:<Sample design document number/ Description of the method of rejecting extrapolation/ Business rule document links>
Whether to use a post-credit field: No (if yes, it must be explained why this information can be used at the assembly stage)
Factors associated with the target column:<The Platform's diagnosis gave ustarget_correlation,If no, how to calculate>
Evaluation findings: Approval of use/ Replacing weights is required/ Do not use sample weights
```

The weighting column, which has no clear justification, should be changed directly to the sample weighting instead of the modelling setting phase (see also para.`sample_weight_col` ♪ Leave it, not ♪"Let's get this done.".

## Platform Inline Tip (Status)

- `choose_modeling_spec`(`marvis/packs/modeling/feature_tools.py`)Automatically removes and prompts the weight column when it appears in the list of candidate features at the same time"Sample weighting removed from the mode character".
- Modeling door (`_modeling_override_guidance`,`marvis/agent/gate_payloads.py`)Always hint when the user selects a weight column"The weight column will change the intended target and will not be modelled.";When a diagnostic signal is determined to be a high risk of leakage (weight associated with target height), it is upgraded to`level: "warning"` , and then the message contains a relevant coefficient, requiring the user to change the weight of the weight of the weight of the weight of the weight of the sample or not to use it.
- Validity diagnosis of weight columns (missing value, indecisive weight, etc.)`_sample_weight_diagnostics`(`marvis/agent/modeling_setup.py`)The number of people who have been killed is about 50%.`leakage_risk`/`target_correlation` Fields return with validity diagnosis for front end and door file reuse.

## Fixtures(Test Overwrite)

Belowfixtures The above decision logic is covered and is situated in:

- `tests/test_modeling_recipes.py::test_build_modeling_proposal_flags_high_leakage_risk_when_weight_correlates_with_target` — The following is a list of the most important features of the article:`sample_weight_diagnostics[].leakage_risk == "high"`.
- `tests/test_modeling_recipes.py::test_build_modeling_proposal_leakage_risk_low_when_weight_independent_of_target` — Weights and labels stand alone (business)/(a) when the sample weight is typical)`leakage_risk == "low"`.
- `tests/test_plan_driver.py::test_modeling_screen_gate_warns_when_selected_sample_weight_has_high_leakage_risk` — Modeling settings doors upgrade the hint to a high-spill risk weight column`level: "warning"` and bring out the relevant coefficient.

Add a corresponding decision logic or hint to the three test files when adding weightfixture,Hold on."Guides withfixtures Keep it rich."(LT-14 The original claim.
