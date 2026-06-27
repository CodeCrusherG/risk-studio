# ModellingNotebook Compacts with the Platform

Submitted by the executive developers of the PlatformJupyter Notebook,Use it together.Notebook Rating of the model object left in memory after running, and the intended commissioning in the submitted directoryPMML Rating results for consistency comparison.
Model effects and stability verifications are added to the same.Notebook kernel Executed, Direct ReuseNotebook Samples in MemoryDataFrame.

Full submission request.[notebook_submission_requirements.md](./notebook_submission_requirements.md).This document is a summary of the development of the platform ' s operational compact.

## Core principles

- A certificationer does not need to fill in model variables, model types, feature fields or rating expressions.
- Notebook The platform must be exposed in a visible manner and the platform does not automatically guess the model object.
- The main consistency test is`RMC_SCORE_FN(sample_df)` and submissionPMML The score.
- Notebook Additional exportablePMML As audit material, but no new export from the platformPMML As the main object of comparison.
- `RMC_FEATURES` No longer required. Code model andPMML It should be able to get from the same original sample.DataFrame .

## It's a contract.

Notebook Before the end of implementation, the top level domain definition must be:

```python
RMC_SAMPLE_DF = modeling_sample
RMC_TARGET_COL = "target"
RMC_ALGORITHM = "lgb"

def RMC_SCORE_FN(df):
    return final_model.predict_proba(df)[:, 1]
```

`RMC_SAMPLE_DF` Requests:

- Type ispandas DataFrame.
- It's for the platform to score consistency,KS,PSI,Subboxes, original samples of pressure tests.
- Includes target columns, group columns, time columns, andPMML scorer and`RMC_SCORE_FN` Required fields.
- It must be.Notebook The top level field is visible and cannot be found in only the function local variable.

`RMC_SCORE_FN(df)` Requests:

- Receivepandas DataFrame.
- Returns a 1-dimensional numerical fraction.
- Returns the length of the line that you enter.
- Do not return empty or infinity.
- Internal processing of feature selection, field order, missing values,WOE/Standardized scoring logic.

`RMC_TARGET_COL` Requests:

- Type is string.
- Corresponding fields must be present in sample data.

`RMC_ALGORITHM` Requests:

- Type is string.
- The platform will be consolidated into an internal listing:`lgb`,`xgb`,`lr`,`catboost`,`scorecard`,`dnn`.
- Accept common aliases, for example`lightgbm`,`lgbm`,`LGBMClassifier` -> `lgb`,`xgboost`,`XGBClassifier` -> `xgb`,`LogisticRegression`,`Logical regression` -> `lr`,`CatBoostClassifier` -> `catboost`,`Scorecard`,`score_card` -> `scorecard`,`deep neural network`,`Neural network` -> `dnn`.
- Unknown algorithms fail at static contract check. Developers need to fix them.Notebook,The certificationer does not select when the platform is being created.

## Optional compacts

```python
RMC_SPLIT_COL = "sample_type"
RMC_TIME_COL = "apply_month"
RMC_PMML_OUTPUT_FIELD = "probability_1"
RMC_SCORE_DECIMAL_PLACES = 6
```

- `RMC_SPLIT_COL`:Sample grouping fields fortrain/test/OOT Indicator.
- `RMC_TIME_COL`:Time fields for monthly effects and stability.
- `RMC_PMML_OUTPUT_FIELD`:PMML Normal output field, default`probability_1`.
- `RMC_SCORE_DECIMAL_PLACES`:Code ModelsPMML Model points are more accurate than the model points, default 6 bits.

## Characteristic importance

If the report is to be characterized as important,Notebook It should be defined as:

```python
RMC_FEATURE_IMPORTANCE = pd.DataFrame({
    "feature": feature_names,
    "Category": feature_categories,  # Optional or named"category"
    "importance": importance_values,
})
```

Requests:

- Type ispandas DataFrame.
- Must Contain`feature`,`importance` Two rows.
- Organisation`Category` or`category` columns;platforms are written uniformlyWeb,Excel andWord , the (Category) column.
- Pressure tests will be non-empty.`Category` or`category` Consider it final.`feature` Authoritative classification of names.
- The data dictionary will only accurately supplement the empty category by full feature name, without prefixing, suffixing or derivative feature name.
- If you still have entry characteristics that cannot be classified, the overall state of the pressure test is`partial`;No entry characteristics are classified as`failed`,Do not show as complete.
- `importance` It must be a value.
- Platform Press`importance` Downshow display.
- The platform does not decide whether to take absolute values.LR The coefficient is being developed by the developers.Notebook It is so decided.

Transitional period compatible with the old variable name:

```python
FEATURE_IMPORTANCE = RMC_FEATURE_IMPORTANCE
```

## Model Parameters

If model parameters are reported to be required,Notebook It should be defined as:

```python
RMC_MODEL_PARAMS = {
    "learning_rate": 0.05,
    "num_leaves": 31,
}
```

Requests:

- Type isdict.
- key A string must be the string.
- value RecommendedJSON Sequencable simple values; the platform is only for display and does not explain the syntax of the model.

Transitional period compatible with the old variable name:

```python
MODEL_HYPERPARAMETERS = RMC_MODEL_PARAMS
```

## Recommended full contractCell

SuggestedNotebook Last regular codecell.

```python
import pandas as pd

RMC_TARGET_COL = "target"
RMC_ALGORITHM = "lgb"
RMC_SPLIT_COL = "sample_type"
RMC_TIME_COL = "apply_month"
RMC_PMML_OUTPUT_FIELD = "probability_1"
RMC_SCORE_DECIMAL_PLACES = 6
RMC_SAMPLE_DF = modeling_sample

def RMC_SCORE_FN(df):
    return final_model.predict_proba(df)[:, 1]

RMC_FEATURE_IMPORTANCE = pd.DataFrame({
    "feature": feature_names,
    "importance": importance_values,
})

RMC_MODEL_PARAMS = {
    "learning_rate": 0.05,
    "num_leaves": 31,
    "n_estimators": 300,
}
```

## Platform inspection

Pre-static check:

- Scan Codecell text.
- Missing`RMC_SAMPLE_DF`,`RMC_SCORE_FN`,`RMC_TARGET_COL` or`RMC_ALGORITHM` , Do Not executeNotebook,Directly fails.
- The transition period can be`RMC_MODEL_PARAMS["algorithm"]` or`MODEL_HYPERPARAMETERS["algorithm"]` Read algorithms, but newNotebook Should be used`RMC_ALGORITHM`.

Run-time check after execution:

- In the same one.kernel Run Platform End Checkingcell.
- Authentication`RMC_SAMPLE_DF` Yes.pandas DataFrame.
- Authentication`RMC_SCORE_FN` Callable.
- Verify that the target bar exists.
- Call`RMC_SCORE_FN(RMC_SAMPLE_DF.copy())` And write code model points.
- Verify the length of the fraction, the type of value, the empty value, the infinity value.
- Verify the value of the selected features and the format of the model parameters.

## PMML Request

Submitting directoryPMML It's a file of a proposed input model. The platform will take the same original sample.DataFrame Send to SubmissionPMML scorer.

PMML Must ContainDataFrame mapper,pipeline,derived fields The platform does not require a certificate provider to provide a list of features.

Main contrast path:

```text
Notebook Memory Samples-> RMC_SAMPLE_DF
Notebook Memory Model-> RMC_SCORE_FN(RMC_SAMPLE_DF.copy()) -> code_model_scores
SubmitPMML -> PMML scorer(RMC_SAMPLE_DF.copy()) -> submitted_pmml_scores
code_model_scores vs submitted_pmml_scores -> Consistency conclusions
```

Default full stream line, step 3 "Model Effects"&Stability Validation will not be re-executedNotebook,The sample document will not be read again by the Platform process; it will be isolated at the same timeNotebook Add Authentication at the end of the executioncell,Direct Use`RMC_SAMPLE_DF`,`RMC_SCORE_FN` and`RMC_FEATURE_IMPORTANCE`.

If the user re-implements the 3rd step separately, the platform re-implements the originalNotebook,To identify the target for the above-mentioned compact for the purpose of reconstruction, with additional targets at the end of the performance periodcell.Platform does not re-use old, withdrawn or potentially contaminatedkernel,And I won't go around.Notebook , and then re-explanes the original feature classification.

## Frequent failures

- `Notebook contract check failed before execution: missing RMC_SCORE_FN`
  - Notebook No rating function defined.
- `Notebook contract check failed before execution: missing RMC_SAMPLE_DF`
  - Notebook No exposure at the top.DataFrame.
- `RMC_SCORE_FN returned N scores for M rows`
  - The rating function returns the length of the sample line.
- `RMC_SCORE_FN returned null scores`
  - The rating function returns the empty value.
- `RMC_FEATURE_IMPORTANCE must be a pandas DataFrame`
  - The format of the feature importance does not meet the requirements.
- `RMC_MODEL_PARAMS must be a dict`
  - Model parameter formats do not meet the requirements.
- `unsupported model algorithm`
  - `RMC_ALGORITHM` or the algorithms in the transition model parameters cannot be unified.
- `submitted PMML scorer returned N scores for M rows`
  - PMML The output length of the score is abnormal.

## Minimal Qualification Example

```python
RMC_SAMPLE_DF = modeling_sample
RMC_TARGET_COL = "target"
RMC_ALGORITHM = "lgb"

def RMC_SCORE_FN(df):
    return final_model.predict_proba(df)[:, 1]
```
