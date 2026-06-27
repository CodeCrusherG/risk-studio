# ModellingNotebook Submission requirements

## 1. Purpose

This document only describesMARVIS V2.5.0 The current embedded model validation workflow does not mean that the platform can only perform a model validation.Jupyter Notebook,and useNotebook Run and leave the memory with the model object to score and submit it to the developer's directoryPMML Model results are rated for consistency comparison.

The objectives of this request are:

- The certifier doesn't need to understand.Notebook Code, model variable name, model type, feature field or rating method.
- Developers rate functions, target fields, optional reporting materials through fixed compact exposure models.
- Platforms can be checked automaticallyNotebook Whether or not to meet the requirements and to give a clear error in the absence of a contract or when the operation fails.
- Platform PressNotebook Title shows progress in implementation, but the order of implementation remains unchangedNotebook Original order.

## 2. Documentation requirements

Submitted by the developersNotebook It is essential to satisfy:

- File format is as`.ipynb`.
- Notebook It's complete from scratch.
- Not dependent on manual clicks, manual input, temporary interactive confirmation.
- No certification officer is required to modifyNotebook Code.
- The certifying officer is not required to fill in model variables, model types, feature fields or rating expressions.
- Notebook Finally, you must define the platform ' s contractual variables and functions.

The developers submitted it at the same time.PMML It is essential to satisfy:

- PMML It is the final proposed input model document.
- PMML OrganisationDataFrame mapper,pipeline or equivalent, which can be passed directly to the original sample entered on the platformDataFrame Rating.
- PMML No list of characteristics is required for the certification officer.
- PMML Output field name is defaulted on`probability_1`,If not, inNotebook As specified in the contract.

## 3. Notebook Title requirements

Platform will resolveNotebook MediumMarkdown Title and display the steps of implementation by title.

Supported title level:

```markdown
# Data readiness
## Characteristic processing
### Model training
```

Requests:

- RecommendationsNotebook The main steps are used.Markdown Title separated.
- Code under Titlecell It would be the step to the title.
- Code before the first titlecell It's gonna be like...`Notebook Initialize`.
- The platform will show progress by title only, and it will not changeNotebook Order of implementation.
- The platform won't skip.cell,The government has also been able to provide support to the government and the government.
- The whole thing.Notebook It's gonna be the same.kernel .
- The model effects and stability validation will be added to the same one that's just completed in step 2.kernel,Directly reuse memory`RMC_SAMPLE_DF`.

Recommended title structure:

```markdown
# 1. Environment and parameters
# 2. Data Read
# 3. Sample processing
# 4. Characteristic processing
# 5. Model training
# 6. Model assessment
# 7. Platform validation compacts
```

## 4. It's a contract.

Notebook Before the end of implementation, the following must be defined as the top level domain:

```python
RMC_SAMPLE_DF = modeling_sample
RMC_TARGET_COL = "target"
RMC_ALGORITHM = "lgb"

def RMC_SCORE_FN(df):
    return final_model.predict_proba(df)[:, 1]
```

### 4.1 `RMC_SAMPLE_DF`

`RMC_SAMPLE_DF` It's a sample used for platform validation.DataFrame.

Requests:

- It must be.pandas DataFrame.
- It must be.Notebook Top level fields are visible.
- Must include target, group, time, and`RMC_SCORE_FN` andPMML scorer Required fields.
- 2nd Step Score Consistency and 3rd Step Model Effect&The stability certification will be used directly and will not allow the Platform process to reread the sample document for analysis.

### 4.2 `RMC_SCORE_FN`

`RMC_SCORE_FN` It is the only entry to the platform to call memory models for scoring.

Format requirements:

```python
def RMC_SCORE_FN(df):
    ...
    return scores
```

Requests:

- must be a callable function.
- The admission must be acceptable to one.pandas DataFrame.
- The platform will take the same sample as the original.DataFrame Passes to the function.
- The function does the feature selection, field sequence, missing value processing,WOE/Logic required to score models such as standardization.
- Return value must be a 1-dimensional fraction, length equals inputDataFrame Line number.
- Returns value must be a value.
- Return value cannot contain empty, infinity value.
- The return value shall be the normal probability category or model score required for the Platform report.

Do not let the platform guess the model object.Notebook It must be clearly provided`RMC_SCORE_FN`.

Example:

```python
def RMC_SCORE_FN(df):
    return final_model.predict_proba(df)[:, 1]
```

If the model requires a specific field or conversion, it is handled within the function:

```python
def RMC_SCORE_FN(df):
    x = df[["age", "income", "loan_cnt"]].copy()
    x["income"] = x["income"].fillna(0)
    return final_model.predict_proba(x)[:, 1]
```

### 4.3 `RMC_TARGET_COL`

`RMC_TARGET_COL` is the target label column in the sample forKS,AUC,• Validation indicators such as box effects.

Format requirements:

```python
RMC_TARGET_COL = "target"
```

Requests:

- A string must be the string.
- This field must be in the sample data of the platform.
- Field values should express good and bad sample labels.

### 4.4 `RMC_ALGORITHM`

`RMC_ALGORITHM` It's model algorithm type. By developers.Notebook The contract is filled in so that the certifying officer is no longer selected for the new task of the platform.

Format requirements:

```python
RMC_ALGORITHM = "lgb"
```

Only the following normative values are saved within the platform:

- `lgb`:LightGBM.
- `xgb`:XGBoost.
- `lr`:Logical regression.
- `catboost`:CatBoost.
- `scorecard`:Score card.
- `dnn`:Deep neuronet.

The platform would accept and normalize common aliases, such as:

- `lgb`,`lgbm`,`lightgbm`,`Lightgbm`,`LGBMClassifier` -> `lgb`.
- `xgb`,`xgboost`,`XGBClassifier`,`xgboost.XGBClassifier` -> `xgb`.
- `lr`,`logistic`,`LogisticRegression`,`Logical regression` -> `lr`.
- `catboost`,`CatBoostClassifier` -> `catboost`.
- `scorecard`,`score_card`,`Scorecard`,`Scorecard` -> `scorecard`.
- `dnn`,`deep neural network`,`neural network`,`Neural network`,`Deep neuronet.` -> `dnn`.

Unknown algorithms fail at the static contract check. Developer should modifyNotebook The contract should not require the certifying officer to choose from the platform interface.

## 5. No request.`RMC_FEATURES`

Platform doesn't requireNotebook Definitions`RMC_FEATURES`.

Reason:

- Code Model Rating By`RMC_SCORE_FN(df)` It is up to you to decide which fields you want to use.
- PMML The side request was submitted by the developers.PMML OrganisationDataFrame mapper Or the equivalent.pipeline,I can get my own way from the original.DataFrame Take the field.
- The platform will only ensure that the same sample is originalDataFrame Separately`RMC_SCORE_FN` andPMML scorer.

Therefore, the certificationer does not need to complete the feature list and the Platform will not use the feature list as a mandatory entry for the master consistency verification.

## 6. Optional compacts

The following variables are not mandatory for all tasks. The platform reads and writes in the report when the variable exists; skips the corresponding content or uses the default value when it does not exist.

### 6.1 `RMC_SPLIT_COL`

Sample grouping fields, such as training, testing,OOT.

```python
RMC_SPLIT_COL = "sample_type"
```

Requests:

- Optional.
- If the report requires a sample set to demonstrate the results, it is recommended.
- A string must be the string.
- When a field exists, the Platform groups indicators by that field.

### 6.2 `RMC_TIME_COL`

Time fields, e.g. month of application, month of observation.

```python
RMC_TIME_COL = "apply_month"
```

Requests:

- Optional.
- If the report requiresPSI,Stability, performance over time, recommended.
- A string must be the string.

### 6.3 `RMC_PMML_OUTPUT_FIELD`

PMML Output field name.

```python
RMC_PMML_OUTPUT_FIELD = "probability_1"
```

Requests:

- Optional.
- Default value is`probability_1`.
- IfPMML Output field is not`probability_1`,You must specify.

### 6.4 `RMC_SCORE_DECIMAL_PLACES`

Models are more precise in their consistency.

```python
RMC_SCORE_DECIMAL_PLACES = 6
```

Requests:

- Optional.
- Default value is`6`.
- The Platform will judge the code model by this configuration in a uniform comparison function.PMML Is the model split consistent; by default,
  6 (a) The points of consistency are determined to be adopted when the decimal rounded to a 98 per cent convergence rate and the maximum absolute difference does not exceed the threshold for tolerance on the platform;
  The consistency rate is 95 to 98% and varies by hours and is considered to be subject to review.

## 7. Characteristic importance requirements

If the report needs to be characterized as important,Notebook It should be defined as:

```python
RMC_FEATURE_IMPORTANCE = pd.DataFrame({
    "feature": feature_names,
    "Category": feature_categories,  # Optional or named"category"
    "importance": importance_values,
})
```

Format requirements:

- The type must bepandas DataFrame.
- There must be two columns:`feature`,`importance`.
- Organisation`Category` or`category` columns;platforms are written uniformlyWeb,Excel andWord , the (Category) column.
- Pressure testing prioritizes the non-empty category here and considers it the same line as the end of the line.`feature` Authoritative classification of names.
- The uploading data dictionary only adds an exact empty category by full feature name, without prefixing, suffixing or blurring.
- Pressure tests show partial completion when the entry characteristics are still unclassified; failure is shown when all cannot be classified, rather than being done silently.
- `feature` is the feature name, and is recommended as the string.
- `importance` is the material value.
- Platform will press`importance` Declines the presentation and writing of the report.
- The platform does not decide whether to take absolute values.
- IfLR coefficient, developer shouldNotebook It's up to you to decide whether to pass the original coefficient or not.`abs(coef)`.

LR Example:

```python
RMC_FEATURE_IMPORTANCE = pd.DataFrame({
    "feature": feature_names,
    "importance": [abs(v) for v in final_model.coef_[0]],
})
```

LightGBM Example:

```python
RMC_FEATURE_IMPORTANCE = pd.DataFrame({
    "feature": feature_names,
    "importance": final_model.feature_importances_,
})
```

Compatibility of old variables:

```python
FEATURE_IMPORTANCE = RMC_FEATURE_IMPORTANCE
```

Platforms can be compatible during the transition period`FEATURE_IMPORTANCE`,But it's new.Notebook Recommended use`RMC_FEATURE_IMPORTANCE`.

## 8. Model Parameter Requirements

If model parameters are required for reporting,Notebook It should be defined as:

```python
RMC_MODEL_PARAMS = {
    "objective": "binary",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "max_depth": -1,
    "n_estimators": 300,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
}
```

Format requirements:

- The type must bedict.
- key A string must be the string.
- value RecommendedJSON Simple type of serialized:`str`,`int`,`float`,`bool`,`None`.
- value - It could be.list ordict,The platform, however, is only for display and does not explain the syntax of the model.
- The platform will rephrase the report as two lists: parameter name, parameter value.

Compatibility of old variables:

```python
MODEL_HYPERPARAMETERS = RMC_MODEL_PARAMS
```

Platforms can be compatible during the transition period`MODEL_HYPERPARAMETERS`,But it's new.Notebook Recommended use`RMC_MODEL_PARAMS`.

During the transition period, if oldNotebook Not completed`RMC_ALGORITHM`,The platform can be used to...`RMC_MODEL_PARAMS["algorithm"]` or`MODEL_HYPERPARAMETERS["algorithm"]` reading algorithms;newNotebook Priority must be given to the use of the fourth.4 The festival.`RMC_ALGORITHM`.

## 9. Recommended full contractcell

SuggestedNotebook Last regular codecell.

```python
import pandas as pd

RMC_TARGET_COL = "target"
RMC_SAMPLE_DF = modeling_sample
RMC_ALGORITHM = "lgb"
RMC_SPLIT_COL = "sample_type"
RMC_TIME_COL = "apply_month"
RMC_PMML_OUTPUT_FIELD = "probability_1"
RMC_SCORE_DECIMAL_PLACES = 6

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

# Transitional compatible old fields, optional
FEATURE_IMPORTANCE = RMC_FEATURE_IMPORTANCE
MODEL_HYPERPARAMETERS = RMC_MODEL_PARAMS
```

## 10. PMML Request

Submitted by the developersPMML It's a model document for the proposed input. The platform will putPMML Rating Results andNotebook Memory model scores against results.

PMML It is essential to satisfy:

- Original sample that can be used to reach the platformDataFrame Rating.
- Internal IncludeDataFrame mapper,pipeline,derived fields Or the logic of price conversion.
- Not dependent on the additional profile list of the certifying officer.
- Output fields can be passed`RMC_PMML_OUTPUT_FIELD` Specifies.

The platform won't beNotebook RedirectedPMML As the main object of comparison.

Main contrast path:

```text
Notebook Memory Samples-> RMC_SAMPLE_DF
Notebook After-implementation memory model-> RMC_SCORE_FN(RMC_SAMPLE_DF.copy()) -> code_model_scores
Submitting directoryPMML -> PMML scorer(RMC_SAMPLE_DF.copy()) -> submitted_pmml_scores
code_model_scores vs submitted_pmml_scores -> Consistency conclusions
```

## 11. Platform check logic

### 11.1 Perform prestatic check

The platform will be operationalNotebook Scan code text before checking if it appears:

- `RMC_SCORE_FN`
- `RMC_SAMPLE_DF`
- `RMC_TARGET_COL`
- `RMC_ALGORITHM`(or in the parameters of the transition model`algorithm`)

If they are missing, the task will fail before it is carried out.

Example error:

```text
Notebook contract check failed before execution:
missing RMC_SCORE_FN

Please add the MARVIS contract cell at the end of the notebook.
```

Static checks are only used for the early detection of obvious deficiencies and do not prove that the function is necessarily correct.

### 11.2 Run-time check after execution

Notebook Originalcell Once all implementation is complete, the platform will be the samekernel In-progress System Checkcell.

The default full stream line will be isolated at the same time.Notebook Add a step 3 indicator at the end of implementationcell,Directly reuse
`RMC_SAMPLE_DF`,`RMC_SCORE_FN` and`RMC_FEATURE_IMPORTANCE`.If the certifier is alone
Reimplement 3 steps and the platform will re-runNotebook To identify the targets for the compacts and add additional targets
cell;Platform does not re-use old, withdrawn or potentially contaminatedkernel.

The platform will check:

- `RMC_SCORE_FN` Existence.
- `RMC_SCORE_FN` Callable.
- `RMC_SAMPLE_DF` Existence andpandas DataFrame.
- `RMC_TARGET_COL` Existence and is a string.
- `RMC_ALGORITHM` An algorithm that exists and can be consolidated to support.
- `RMC_SCORE_FN(RMC_SAMPLE_DF.copy())` Is it running properly?
- Whether the output length equals the number of sample lines.
- whether the output is a value.
- Whether the output contains an empty or infinity value.
- `RMC_FEATURE_IMPORTANCE` is the format correct when it exists.
- `RMC_MODEL_PARAMS` is the format correct when it exists.

If any check fails, the platform will show specific errors and keep the execution log and failureNotebook.

## 12. Not permitted

Do not define the contract variable only within the function:

```python
def main():
    RMC_TARGET_COL = "target"
    def RMC_SCORE_FN(df):
        return model.predict_proba(df)[:, 1]

main()
```

Reason: End of platform checkcell Yes.Notebook The top level domain reads variables, and the internal local variables of the function are not visible.

Do not rely on manual input:

```python
threshold = input("Please enter a threshold")
```

Not here.`RMC_SCORE_FN` , and then amend the external data file:

```python
def RMC_SCORE_FN(df):
    df.to_csv("debug.csv")
    return final_model.predict_proba(df)[:, 1]
```

Don't let`RMC_SCORE_FN` Returns a 2-dimensional array:

```python
def RMC_SCORE_FN(df):
    return final_model.predict_proba(df)
```

The probability of a 1-dimensional positive should be returned:

```python
def RMC_SCORE_FN(df):
    return final_model.predict_proba(df)[:, 1]
```

## 13. Operational environmental requirements

Platforms will be selected in settingsPython,conda orJupyter kernel Environment.

Notebook The development agent must ensure that the environment containsNotebook Dependence, for example:

- pandas
- numpy
- scikit-learn
- lightgbm
- xgboost
- catboost
- pypmml orPMML Related Dependencies
- tensorflow,pytorch or otherDNN ELECTRONIC ACCESS (e.g., model use)
- Other in-house packages used in training code

IfNotebook Dependency on specifiedconda Environment, which should be clearly named in the submission.

Check selected before platform implementationkernel Whether or not to use; run failures due to the missing relying package will be displayed in the execution log.

## 14. Failed to process

Possible types of failures given by the Platform include:

- Not foundNotebook.
- Notebook Static contract check failed.
- Notebook Some.cell Implementation failed.
- `RMC_SCORE_FN` Not at all.
- `RMC_SCORE_FN` The output length is incorrect.
- `RMC_SCORE_FN` Output contains non-value, empty or infinity values.
- `RMC_TARGET_COL` The column does not exist or is missing in the sample.
- PMML The score failed.
- PMML Output field does not exist.
- Code ModelsPMML Models are not consistent.

When a failure occurs, the platform will retain:

- OriginalNotebook Hash.
- Execute copy.
- Execute log.
- Failedcell Information.
- stdout / stderr Summary.
- Results of contract inspection.
- Differences in fractions are detailed if generated.

## 15. Minimal Qualification Example

Here's the minimum contractual inspection.Notebook End code.

```python
RMC_SAMPLE_DF = modeling_sample
RMC_TARGET_COL = "target"
RMC_ALGORITHM = "lgb"

def RMC_SCORE_FN(df):
    return final_model.predict_proba(df)[:, 1]
```

If the report requires more complete content, use the complete contract of section 9cell.

## 16. Self-check list before submission

Before submitting, the developers shall confirm:

- Notebook Can run from scratch to the end.
- Notebook At the end.`RMC_SAMPLE_DF`.
- Notebook At the end.`RMC_SCORE_FN`.
- Notebook At the end.`RMC_TARGET_COL`.
- Notebook At the end.`RMC_ALGORITHM`,The site is supported by a platform-supported algorithm or common aliases.
- `RMC_SCORE_FN(df)` Returns a 1-dimensional numerical fraction.
- `RMC_SCORE_FN(df)` Returns the length of the sample line that you enter.
- SubmittedPMML It can be directly directed to the original sample.DataFrame Rating.
- PMML Output field with`RMC_PMML_OUTPUT_FIELD` Consistent, or default`probability_1`.
- Defined if character importance is required`RMC_FEATURE_IMPORTANCE`.
- Model parameters, if required, defined`RMC_MODEL_PARAMS`.
- Notebook Do not depend on manual input.
- Notebook The certification officer is not required to understand the model variable name or code details.
