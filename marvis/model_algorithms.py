from __future__ import annotations

import re


DEFAULT_ALGORITHM = "lgb"
SUPPORTED_ALGORITHM_TEXT = "xgb, lgb, lr, catboost, scorecard, dnn"

ALGORITHM_LABELS: dict[str, str] = {
    "xgb": "XGBoost",
    "lgb": "LightGBM",
    "lr": "Logical regression",
    "catboost": "CatBoost",
    "scorecard": "Scorecard",
    "dnn": "DNN",
}

ALLOWED_ALGORITHMS = frozenset(ALGORITHM_LABELS)

_ALGORITHM_ALIASES = {
    "xgb": "xgb",
    "xgbm": "xgb",
    "xgbmclassifier": "xgb",
    "xgboost": "xgb",
    "xgbclassifier": "xgb",
    "xgboostclassifier": "xgb",
    "xgboostxgbclassifier": "xgb",
    "xgboostsklearnxgbclassifier": "xgb",
    "lgb": "lgb",
    "lgbm": "lgb",
    "lightgbm": "lgb",
    "lighgbm": "lgb",
    "lgbclassifier": "lgb",
    "lgbmclassifier": "lgb",
    "lightgbmclassifier": "lgb",
    "lightgbmsklearnlgbmclassifier": "lgb",
    "lr": "lr",
    "logit": "lr",
    "logistic": "lr",
    "logisticregression": "lr",
    "logisticregressioncv": "lr",
    "sklearnlinearmodellogisticregression": "lr",
    "Logical regression": "lr",
    "cat": "catboost",
    "catboost": "catboost",
    "catboostclassifier": "catboost",
    "catboostcatboostclassifier": "catboost",
    "scorecard": "scorecard",
    "scorecards": "scorecard",
    "Scorecard": "scorecard",
    "Score card": "scorecard",
    "dnn": "dnn",
    "deeplearning": "dnn",
    "deepneuralnetwork": "dnn",
    "neuralnetwork": "dnn",
    "mlp": "dnn",
    "mlpclassifier": "dnn",
    "Neural network": "dnn",
    "Deep neuronet.": "dnn",
}

MODEL_TRAINING_DESCRIPTIONS: dict[str, str] = {
    "xgb": (
        "XGBoost It's a gradient up to the tree integration algorithm.CART The tree is designed to combine the residual or gradient of the front-line model,"
        "It supports regularization, sampling, sampling, learning contraction, and learning."
        "The default direction of the missing value and the cutter, which allows for credit with more variables, non-linear relationships, and complex features"
        "Keeps a strong alignment capacity in the risk managementled scene.KS,AUC The difference,"
        "OOT Stability, concentration of variable materiality, single-modular reasonableness, missing and extreme value sensitivity, and parameters"
        "The report should be prepared with an indication of whether there is a risk of over-street, over-learning or over-oversulation."
        "Models are super-involved with multiple weak learners to rank risks, and it is not appropriate to interpret tree models as a single variable causality and should"
        "Test conclusions in the light of sample changes, calibration controls and bindings on input, avoiding single point indicator decision-making."
    ),
    "lgb": (
        "LightGBM An efficient integrated algorithm based on gradients, using a histogram of division, preferential leaf growth and"
        "Mechanisms such as parallel features that balance training efficiency in credit wind modeling with larger samples and more variable dimensions"
        "and differentiates between abilities. The model automatically captures non-linear relationships, variables interact, and the loss function gradients are developed in consecutive iterative ways."
        "The test is based on a training set, a test set, and a test set.OOT It's...KS,AUC,PSI The performance,"
        "Check the legitimacy of parameters such as leaves, learning rates, minimum sample numbers, and iterative rotations, and assess whether the variables are important"
        "Over-concentration and confirmation of models in crowd migration, data drift and abnormal input, combined with case-segregation, missing values and pressure tests"
        "The report should be prepared in such a way that the algorithm is more oriented towards learning the complex partition structure and that conclusions should be relied upon simultaneously."
        "Exogenous performance, stability and operational interpretability, with caution and concern for consistency in production."
    ),
    "lr": (
        "Logical regression is a linear model of the second classification commonly used in credit styles, with a special mass sumLogit Functions"
        "Converting to the probability of default, the model is structured clearly and interpretable, suitable for the scorecard, access strategy and benchmarking model construction."
        "Its advantages are that variables are oriented, power is small, marginal impacts and strategic implications are easily reviewed, and it is also easy to reconcile with business rules, and the rules of engagement are not applicable to the business sector."
        "Single-touch binding and box-out results combined."
        "Coefficient direction, prominence, training set and test setKS/AUC Variance,OOT Stability,PSI Drifting, calibration"
        "Show and score distribution. Check if missing values, extreme values, class merge and standardized process of variables are relevant to production"
        "The report should be prepared in a manner that is consistent and avoids a caliber deviation."
        "Common findings of stability, calibration and operational interpretability, with attention to linear boundaries."
    ),
    "catboost": (
        "CatBoost It's a gradient up-to-date tree integration algorithm, focusing on optimizing the type characterization and sequencing.boosting,Yes."
        "Decreases the burden of manual coding when the variable contains more than a few count, channel, area or behavioral category fields. It is done by multiple trees"
        "The loss gradient is to be applied in turn, and the non-linear relationship and characterization interaction is to be studied automatically.OOT "
        "SampleKS/AUC,PSI,Category extraction values drift, missing values processing, tree depth, learning rate and iterative rotations, and check"
        "The category code, unknown category and model export format in the input chain are consistent with the development environment."
        "Description of the model ' s reliance on tree integration structures and type characterization mechanisms, with conclusions to be combined with stability, interpretation and consistency of output"
        "Joint judgment."
    ),
    "scorecard": (
        "The score card usually uses the variables behind the box.WOE Conversion and logical regression factors based on a default probability map to facilitate"
        "The fractional system used for operations. It emphasizes the direction of variables, the single-boxing, the fractional contribution and the strategy interpretation, and applies to access,"
        "The test must focus on sample size of the box, bad debt rate, etc."
        "Mono-tempo.WOE/IV,Coefficient direction, training tests/OOT It's...KS andAUC,Score distribution,PSI,Refuse threshold"
        "The report should indicate the linear nature of the score card."
        "Assumptions and cross-sections avoid the ranking of only one voucher indicator to judge validity."
    ),
    "dnn": (
        "DNN It's a multilayer neural network model that learns complex combinations of variables through several hidden layers and non-linear activation functions."
        "The modulus is usually less interpretable than"
        "Tree model and scorecard, with greater focus on the outside of the sample during validationKS/AUC,OOT Stability, calibration performance, training process,"
        "Regularize, stop early, standardize features, process missing values, random seeds and model versions."
        "The tension structure, pre-treatment of water flow lines, threshold selection and commissioning reasoning environment avoid inconsistencies in training reasoning calibres."
        "The contents of the box should be clearly defined and carefully concluded in conjunction with the requirements of stability, pressure testing and monitoring."
    ),
}


def normalize_algorithm(value: str | None, *, allow_empty: bool = False) -> str:
    key = str(value or "").strip()
    if not key:
        if allow_empty:
            return ""
        raise ValueError(
            f"model algorithm is required; supported algorithms: {SUPPORTED_ALGORITHM_TEXT}"
        )
    if key in ALLOWED_ALGORITHMS:
        return key
    normalized = _algorithm_key(key)
    if normalized in _ALGORITHM_ALIASES:
        return _ALGORITHM_ALIASES[normalized]
    raise ValueError(
        f"unsupported model algorithm; supported algorithms: {SUPPORTED_ALGORITHM_TEXT}"
    )


PENDING_MODEL_TRAINING_DESCRIPTION = (
    "- Wait.Notebook ContractsRMC_ALGORITHM Auto-generated model training notes after confirmation."
)

MODEL_TRAINING_OVERVIEWS: dict[str, str] = {
    "xgb": (
        "XGBoost It's a gradient up to the tree integration algorithm.CART The trees are all broken up."
        "A credit-control landscape that is more variable and is visible in non-linear relationships."
    ),
    "lgb": (
        "LightGBM The tree algorithm is based on the hexametric division and the preferential growth of leaves."
        "A credit style model suitable for larger samples and higher variable dimensions."
    ),
    "lr": (
        "Logical regression is a linear model of the second classification, with clear structures and explanations."
        "Suitable scorecard, access strategy and benchmark model."
    ),
    "catboost": (
        "CatBoost The tree algorithm is for the gradients for the type characteristics optimization."
        "A scene suitable for a larger number of fields in the list, channel or class of behaviour."
    ),
    "scorecard": (
        "The scorecards are usually in boxes,WOE and the logical regression factor map fractions,"
        "Emphasis on the direction, semanticity and strategy interpretability of variables."
    ),
    "dnn": (
        "DNN The first is to learn complex characterizations through multilayer non-linear transformations."
        "Explanatorys are usually weaker than tree models and scorecards, and more attention needs to be paid to external stability and consistency of output."
    ),
}

_PREFERRED_HYPERPARAMETER_KEYS = (
    "max_depth",
    "num_leaves",
    "learning_rate",
    "n_estimators",
    "num_boost_round",
    "best_iteration",
    "num_iterations",
    "feature_fraction",
    "colsample_bytree",
    "bagging_fraction",
    "subsample",
    "min_child_samples",
    "min_data_in_leaf",
    "reg_lambda",
    "lambda_l2",
    "reg_alpha",
    "lambda_l1",
)


def model_training_description(algorithm: str | None) -> str:
    normalized = normalize_algorithm(algorithm)
    return MODEL_TRAINING_DESCRIPTIONS[normalized]


def model_training_report_text(
    algorithm: str | None,
    hyperparameters: dict | None = None,
) -> str:
    normalized = normalize_algorithm(algorithm)
    label = ALGORITHM_LABELS[normalized]
    overview = MODEL_TRAINING_OVERVIEWS[normalized]
    clause = format_hyperparameter_clause(hyperparameters)
    if clause:
        return (
            f"This model uses{label}.{overview}"
            f"The training parameters recorded by the Platform include:{clause}."
            "The certification shall be combinedTrain/Test/OOT It's...KS,AUC,PSI And the pressure test."
            "The question is whether these parameters have led to a desired or fraction-caliber drift, and whether they have been used to determine the fate of the population."
            "It is not appropriate to interpret tree division or coefficient direction as a single variable causality."
        )
    return (
        f"This model uses{label}.{overview}"
        "The training is more detailed than currently recorded on the platform, and this section only describes the algorithm category."
        "This cannot be proved as the parameters of this model."
    )


def is_pending_model_training_description(value: str | None) -> bool:
    return not str(value or "").strip() or (
        str(value).strip() == PENDING_MODEL_TRAINING_DESCRIPTION
    )


def is_platform_default_training_description(
    value: str | None,
    algorithm: str | None = None,
) -> bool:
    text = str(value or "").strip()
    if is_pending_model_training_description(text):
        return True
    if text in MODEL_TRAINING_DESCRIPTIONS.values():
        return True
    if text in MODEL_TRAINING_OVERVIEWS.values():
        return True
    candidates = [model_training_report_text(key) for key in ALLOWED_ALGORITHMS]
    if algorithm:
        try:
            candidates.append(model_training_report_text(algorithm))
        except ValueError:
            pass
    return text in candidates


def format_hyperparameter_clause(
    hyperparameters: dict | None,
    *,
    limit: int = 10,
) -> str:
    if not isinstance(hyperparameters, dict) or not hyperparameters:
        return ""
    preferred = [
        key for key in _PREFERRED_HYPERPARAMETER_KEYS
        if key in hyperparameters
    ]
    remaining = [
        key for key in hyperparameters
        if key not in preferred
    ]
    ordered = preferred + remaining
    parts = [
        f"{key}={_format_hyperparameter_value(hyperparameters[key])}"
        for key in ordered[:limit]
    ]
    extra = f" Wait.{len(hyperparameters)} Item" if len(ordered) > limit else ""
    return ",".join(parts) + extra


def _format_hyperparameter_value(value) -> str:
    if isinstance(value, bool) or value is None:
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return text
    text = str(value).strip()
    return text if len(text) <= 48 else f"{text[:45]}..."


def _algorithm_key(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.casefold(), flags=re.UNICODE)
