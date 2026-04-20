from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from marvis.packs.modeling.contracts import TrainConfig
from marvis.packs.modeling.errors import ModelingError


@dataclass(frozen=True)
class ScenarioTemplate:
    id: str
    description: str
    target_type: str
    default_recipe: str
    target_hint: str
    param_overrides: dict[str, Any]
    feature_guidance: str
    eval_metric: str
    notes: str


SCENARIO_TEMPLATES = {
    "loan_pre_a": ScenarioTemplate(
        "loan_pre_a",
        "Before the loan.ACard (access rating)",
        "binary",
        "scorecard",
        "First PassFPD/30+ @ mob",
        {"max_depth": 3},
        "Strong interpretation, single-telephone boxes, cross-channel stability",
        "ks_auc",
        "Priority of the scorecard;OOT KS Decline requires attention",
    ),
    "pre_screen": ScenarioTemplate(
        "pre_screen",
        "Front-screen (bracked client)",
        "binary",
        "lgb",
        "Bad customer./Show after rejection",
        {},
        "Priority for coverage of external data sources",
        "ks_auc",
        "High rate of rejection, attention to sample deviations (rejection of extrapolation)",
    ),
    "loan_in": ScenarioTemplate(
        "loan_in",
        "Credit (behaviour rating)BCut)",
        "binary",
        "lgb",
        "The future.NOverdue",
        {},
        "Behaviour/Repayment/Subsidized class character is master",
        "ks_auc",
        "Observation period+:: The performance period is defined clearly; age impact",
    ),
    "loan_post": ScenarioTemplate(
        "loan_post",
        "After loan (early warning)/Before we pick up",
        "binary",
        "lgb",
        "Scrolling deterioration/EnterM2+",
        {},
        "Recent repayments+Overdue migration",
        "ks_auc",
        "Targets are always moving.roll_rate",
    ),
    "marketing": ScenarioTemplate(
        "marketing",
        "Marketing response",
        "binary",
        "lgb",
        "Response/Conversion",
        {},
        "Touche./Active/Historical response characteristics",
        "response_lift",
        "Target is to respond to non-risk; uselift/Response rate assessment, no confusionKS",
    ),
    "transaction": ScenarioTemplate(
        "transaction",
        "Transactions (anti-fraud)/Unusual)",
        "binary",
        "lgb",
        "Fraud/Anomalous transaction.",
        {"scale_pos_weight": "auto"},
        "Transaction series/Equipment/Network features",
        "ks_auc",
        "Extremely unbalanced. Attention.recall/Precision, not just reading.KS",
    ),
    "recall": ScenarioTemplate(
        "recall",
        "Recovery (losses)/♪ Sleep awakening ♪",
        "binary",
        "lgb",
        "Use the letter when you wake up./Reboring",
        {},
        "It's been a long time./History/Marketing Touch",
        "response_lift",
        "Target is positive behavior, class marketing.",
    ),
    "income": ScenarioTemplate(
        "income",
        "Income projections",
        "continuous",
        "lgb_regressor",
        "Monthly income/Disposable income(Continuous value [v])",
        {"objective": "regression"},
        "Wages/Provident Fund/Trade in water./Consumption class characteristics",
        "rmse_mae",
        "Return missions: indicators usedRMSE/MAE/R2,No, it's not.KS/AUC;Yescontinuous recipe",
    ),
    "credit_limit": ScenarioTemplate(
        "credit_limit",
        "Amount",
        "binary",
        "lgb",
        "Risk after drawdown/By believing in will.",
        {},
        "Amount utilization/Income/Risk score",
        "ks_auc",
        "Often associated with a scale strategy (in thousands of US dollars)Phase 7)",
    ),
    "pricing": ScenarioTemplate(
        "pricing",
        "Pricing (risk pricing)",
        "binary",
        "lgb",
        "Risk stratification support pricing",
        {},
        "Risk+Price sensitivity characteristics",
        "ks_auc",
        "Output risk split for pricing policy (%)Phase 7)",
    ),
}


def get_scenario(scenario_id: str) -> ScenarioTemplate:
    return SCENARIO_TEMPLATES[scenario_id]


def list_scenarios() -> list[ScenarioTemplate]:
    return list(SCENARIO_TEMPLATES.values())


def apply_scenario(config: TrainConfig, scenario_id: str) -> TrainConfig:
    template = get_scenario(scenario_id)
    user_params = dict(config.params)
    recipe_override = (
        user_params.pop("recipe_id", None)
        or user_params.pop("recipe", None)
        or config.recipe_id
    )
    recipe_id = str(recipe_override or template.default_recipe)
    _assert_recipe_matches_target(recipe_id, template.target_type)
    return replace(
        config,
        params={**template.param_overrides, **user_params},
        recipe_id=recipe_id,
        scenario_id=template.id,
        target_type=template.target_type,
        eval_metric=template.eval_metric,
    )


def _assert_recipe_matches_target(recipe_id: str, target_type: str) -> None:
    is_regression_recipe = recipe_id.endswith("_regressor")
    is_multiclass_recipe = "multiclass" in recipe_id
    if target_type == "continuous":
        if not is_regression_recipe:
            raise ModelingError(
                f"continuous scenario requires a regression recipe, got: {recipe_id}"
            )
        return
    if target_type == "multiclass":
        if not is_multiclass_recipe:
            raise ModelingError(
                f"multiclass scenario requires a multiclass recipe, got: {recipe_id}"
            )
        return
    if target_type == "binary":
        if is_regression_recipe or is_multiclass_recipe:
            raise ModelingError(
                f"binary scenario requires a classification recipe, got: {recipe_id}"
            )
        return
    raise ModelingError(f"unsupported scenario target_type: {target_type}")


__all__ = [
    "SCENARIO_TEMPLATES",
    "ScenarioTemplate",
    "apply_scenario",
    "get_scenario",
    "list_scenarios",
]
