from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any

from .contracts import (
    PreparedStrategyPlan,
    StrategyWorkflowPreparationContext,
    StrategyWorkflowResolutionContext,
    StrategyWorkflowValidationError,
    deep_freeze,
    deep_thaw,
)


_PROFIT_PARAMETER_FIELDS = {
    "annual_rate",
    "funding_rate",
    "lgd",
    "operating_cost_per_loan",
    "term_months",
}


def validate_profit_inputs(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    allowed = {"segment_col", "ead_col", "pd_col", "profit_params"}
    _reject_fields(inputs, allowed, workflow="profit_calc")
    missing = sorted({"ead_col", "pd_col", "profit_params"} - set(inputs))
    if missing:
        raise StrategyWorkflowValidationError(
            "profit_calc Missing field:" + ",".join(missing) + "."
        )
    params = inputs["profit_params"]
    if not isinstance(params, Mapping):
        raise StrategyWorkflowValidationError(
            "profit_calc It's...profit_params Must be the object."
        )
    if any(not isinstance(key, str) for key in params):
        raise StrategyWorkflowValidationError(
            "profit_calc It's...profit_params Field names must be text."
        )
    missing_params = sorted(_PROFIT_PARAMETER_FIELDS - set(params))
    unexpected_params = sorted(set(params) - _PROFIT_PARAMETER_FIELDS)
    if missing_params:
        raise StrategyWorkflowValidationError(
            "profit_calc It's...profit_params Missing field:"
            + ",".join(missing_params)
            + "."
        )
    if unexpected_params:
        raise StrategyWorkflowValidationError(
            "profit_calc It's...profit_params Contains unsupported fields:"
            + ",".join(unexpected_params)
            + "."
        )
    normalized_params = {
        "annual_rate": _bounded_number(
            params["annual_rate"], name="Profitannual_rate", maximum=1
        ),
        "funding_rate": _bounded_number(
            params["funding_rate"], name="Profitfunding_rate", maximum=1
        ),
        "lgd": _bounded_number(params["lgd"], name="Profitlgd", maximum=1),
        "operating_cost_per_loan": _bounded_number(
            params["operating_cost_per_loan"],
            name="Profitoperating_cost_per_loan",
        ),
    }
    term_months = params["term_months"]
    if (
        isinstance(term_months, bool)
        or not isinstance(term_months, int)
        or term_months < 1
    ):
        raise StrategyWorkflowValidationError(
            "Profitterm_months Must be an integer greater than or equal to 1."
        )
    normalized_params["term_months"] = term_months
    normalized: dict[str, Any] = {
        "ead_col": _column(
            inputs["ead_col"],
            name="ProfitEAD Columnsead_col",
            whitelist=context.allowed_columns,
        ),
        "pd_col": _column(
            inputs["pd_col"],
            name="ProfitPD Columnspd_col",
            whitelist=context.allowed_columns,
        ),
        "profit_params": normalized_params,
    }
    if "segment_col" in inputs:
        normalized["segment_col"] = _column(
            inputs["segment_col"],
            name="profit_calc segment_col",
            whitelist=context.allowed_columns,
        )
    return normalized


def validate_roll_rate_inputs(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    allowed = {
        "id_col",
        "time_col",
        "status_col",
        "states",
        "balance_col",
        "observation_semantics",
    }
    _reject_fields(inputs, allowed, workflow="roll_rate_matrix")
    required = {"id_col", "time_col", "status_col", "states"}
    missing = sorted(required - set(inputs))
    if missing:
        raise StrategyWorkflowValidationError(
            "roll_rate_matrix Missing field:" + ",".join(missing) + "."
        )
    normalized: dict[str, Any] = {
        key: _column(
            inputs[key],
            name=f"roll_rate_matrix {key}",
            whitelist=context.allowed_columns,
        )
        for key in ("id_col", "time_col")
    }
    status_whitelist = context.allowed_columns
    if context.target_col is not None and context.target_col not in status_whitelist:
        status_whitelist = (*status_whitelist, context.target_col)
    normalized["status_col"] = _column(
        inputs["status_col"],
        name="roll_rate_matrix status_col",
        whitelist=status_whitelist,
    )
    if len(set(normalized.values())) != len(normalized):
        raise StrategyWorkflowValidationError(
            "roll_rate_matrix It's...id_col,time_col,status_col It must be different."
        )
    states = inputs["states"]
    if (
        not isinstance(states, Sequence)
        or isinstance(states, str | bytes | bytearray)
        or not 2 <= len(states) <= 50
    ):
        raise StrategyWorkflowValidationError(
            "roll_rate_matrix states An orderly array of 2 to 50 states must be included."
        )
    normalized_states = [
        _required_text(state, name="roll_rate_matrix states Status")
        for state in states
    ]
    if len(set(normalized_states)) != len(normalized_states):
        raise StrategyWorkflowValidationError(
            "roll_rate_matrix states Repetition states cannot be included."
        )
    normalized["states"] = normalized_states
    semantics = inputs.get("observation_semantics", "adjacent_observation")
    if semantics != "adjacent_observation":
        raise StrategyWorkflowValidationError(
            "roll_rate_matrix observation_semantics It's just...adjacent_observation;"
            "A fixed month end snapshot should be used for migrationportfolio Workflow."
        )
    normalized["observation_semantics"] = semantics
    if "balance_col" in inputs:
        balance_col = _column(
            inputs["balance_col"],
            name="roll_rate_matrix balance_col",
            whitelist=context.allowed_columns,
        )
        if balance_col in {
            normalized["id_col"],
            normalized["time_col"],
            normalized["status_col"],
        }:
            raise StrategyWorkflowValidationError(
                "roll_rate_matrix balance_col Cannot resetID,Time or status bar."
            )
        normalized["balance_col"] = balance_col
    return normalized


def validate_limit_pricing_inputs(
    inputs: Mapping[str, Any],
    context: StrategyWorkflowResolutionContext,
) -> dict[str, Any]:
    allowed = {
        "score_col",
        "pd_col",
        "target_col",
        "band_edges",
        "n_bands",
        "limit_grid",
        "rate_grid",
        "lgd",
        "funding_rate",
        "term_months",
        "cost_per_loan",
        "el_ead_max",
        "strategy_id",
        "drop_nan_labels",
    }
    _reject_fields(inputs, allowed, workflow="limit_pricing_matrix")
    required = {
        "score_col",
        "limit_grid",
        "rate_grid",
        "lgd",
        "funding_rate",
        "term_months",
        "cost_per_loan",
        "el_ead_max",
    }
    missing = sorted(required - set(inputs))
    if missing:
        raise StrategyWorkflowValidationError(
            "limit_pricing_matrix Missing field:" + ",".join(missing) + "."
        )
    has_pd = "pd_col" in inputs
    has_target = "target_col" in inputs
    if has_pd == has_target:
        raise StrategyWorkflowValidationError(
            "limit_pricing_matrix It's...pd_col andtarget_col There is only one choice."
        )
    has_edges = "band_edges" in inputs
    has_band_count = "n_bands" in inputs
    if has_edges == has_band_count:
        raise StrategyWorkflowValidationError(
            "limit_pricing_matrix It's...band_edges andn_bands There is only one choice."
        )
    normalized: dict[str, Any] = {
        "score_col": _column(
            inputs["score_col"],
            name="limit_pricing_matrix score_col",
            whitelist=context.allowed_columns,
        ),
        "limit_grid": _number_sequence(
            inputs["limit_grid"],
            name="limit_pricing_matrix limit_grid",
            minimum=0,
            exclusive_minimum=True,
            maximum_items=50,
        ),
        "rate_grid": _number_sequence(
            inputs["rate_grid"],
            name="limit_pricing_matrix rate_grid",
            minimum=0,
            maximum=1,
            maximum_items=50,
        ),
        "lgd": _bounded_number(
            inputs["lgd"], name="limit_pricing_matrix lgd", maximum=1
        ),
        "funding_rate": _bounded_number(
            inputs["funding_rate"],
            name="limit_pricing_matrix funding_rate",
            maximum=1,
        ),
        "cost_per_loan": _bounded_number(
            inputs["cost_per_loan"],
            name="limit_pricing_matrix cost_per_loan",
        ),
        "el_ead_max": _bounded_number(
            inputs["el_ead_max"],
            name="limit_pricing_matrix el_ead_max",
            maximum=1,
        ),
    }
    term_months = inputs["term_months"]
    if (
        isinstance(term_months, bool)
        or not isinstance(term_months, int)
        or not 1 <= term_months <= 600
    ):
        raise StrategyWorkflowValidationError(
            "limit_pricing_matrix term_months Must be the integer number of 1 to 600."
        )
    normalized["term_months"] = term_months
    if has_pd:
        normalized["pd_col"] = _column(
            inputs["pd_col"],
            name="limit_pricing_matrix pd_col",
            whitelist=context.allowed_columns,
        )
    else:
        requested_target = _required_text(
            inputs["target_col"], name="limit_pricing_matrix target_col"
        )
        if context.target_col is None or requested_target != context.target_col:
            raise StrategyWorkflowValidationError(
                "limit_pricing_matrix target_col It must be consistent with the currently identified target line of the mandate."
            )
        normalized["target_col"] = requested_target
    if has_edges:
        edges = _number_sequence(
            inputs["band_edges"],
            name="limit_pricing_matrix band_edges",
            minimum=None,
            maximum_items=51,
            minimum_items=2,
        )
        if any(right <= left for left, right in zip(edges, edges[1:], strict=False)):
            raise StrategyWorkflowValidationError(
                "limit_pricing_matrix band_edges It must be strictly incremental."
            )
        normalized["band_edges"] = edges
        band_count = len(edges) - 1
    else:
        n_bands = inputs["n_bands"]
        if (
            isinstance(n_bands, bool)
            or not isinstance(n_bands, int)
            or not 1 <= n_bands <= 20
        ):
            raise StrategyWorkflowValidationError(
                "limit_pricing_matrix n_bands Must be the integer number of 1 to 20."
            )
        normalized["n_bands"] = n_bands
        band_count = n_bands
    if band_count * len(normalized["limit_grid"]) * len(normalized["rate_grid"]) > 2000:
        raise StrategyWorkflowValidationError(
            "limit_pricing_matrix Grid allows up to 2000 combinations."
        )
    if "strategy_id" in inputs:
        normalized["strategy_id"] = _required_text(
            inputs["strategy_id"], name="limit_pricing_matrix strategy_id"
        )
    if "drop_nan_labels" in inputs:
        if not isinstance(inputs["drop_nan_labels"], bool):
            raise StrategyWorkflowValidationError(
                "limit_pricing_matrix drop_nan_labels Must be a boolean value."
            )
        if has_pd:
            raise StrategyWorkflowValidationError(
                "limit_pricing_matrix Usepd_col The following is a video of the video:"
                "Delete unuseddrop_nan_labels."
            )
        normalized["drop_nan_labels"] = inputs["drop_nan_labels"]
    return normalized


def profit_confirmation(inputs: Mapping[str, Any]) -> str:
    params = inputs["profit_params"]
    details = [
        "Recognized as [standard profit analysis]Workflow〕",
        f"EAD Columns{inputs['ead_col']},PD Columns{inputs['pd_col']}",
        "Scope of analysis:"
        + (
            f"Press{inputs['segment_col']} Group"
            if "segment_col" in inputs
            else "Full sample"
        ),
        (
            f"Annual interest rate{params['annual_rate']:.2%},Cost of funds{params['funding_rate']:.2%},"
            f"LGD {params['lgd']:.2%},Single cost{params['operating_cost_per_loan']:g},"
            f"Duration{params['term_months']} Month"
        ),
    ]
    return _confirmation(details)


def roll_rate_confirmation(inputs: Mapping[str, Any]) -> str:
    details = [
        "Recognized as [standard scroll rate matrix]Workflow〕",
        (
            f"ClientID Columns{inputs['id_col']},Timebar{inputs['time_col']},"
            f"Status Bar{inputs['status_col']}"
        ),
        "Status order:" + " → ".join(inputs["states"]),
        "Observation caliber: adjacent observation records, not equivalent to fixed month-end snapshot migration",
    ]
    if "balance_col" in inputs:
        details.append(f"Balance weights:{inputs['balance_col']}")
    return _confirmation(details)


def limit_pricing_confirmation(inputs: Mapping[str, Any]) -> str:
    risk_source = (
        f"PD Columns{inputs['pd_col']}"
        if "pd_col" in inputs
        else f"Target column{inputs['target_col']}"
    )
    banding = (
        "Box boundary" + ",".join(f"{value:g}" for value in inputs["band_edges"])
        if "band_edges" in inputs
        else f"Equivalent{inputs['n_bands']} Trail"
    )
    details = [
        "Recognized as [standardized rating pricing matrix]Workflow〕",
        f"Breakdown of assessments{inputs['score_col']},Sources of risk{risk_source},{banding}",
        "Threshold:" + ",".join(f"{value:,.12g}" for value in inputs["limit_grid"]),
        "Interest rate grid:" + ",".join(f"{value:.2%}" for value in inputs["rate_grid"]),
        (
            f"LGD {inputs['lgd']:.2%},Cost of funds{inputs['funding_rate']:.2%},"
            f"Duration{inputs['term_months']} Month, single cost{inputs['cost_per_loan']:g},"
            f"EL/EAD Upper limit{inputs['el_ead_max']:.2%}"
        ),
    ]
    if "target_col" in inputs:
        details.append(
            "Label missing processing:"
            + (
                "Discard with a clear mandateNaN Tab Line"
                if inputs.get("drop_nan_labels")
                else "Do Not Automatically DiscardNaN Tab Line"
            )
        )
    if "strategy_id" in inputs:
        details.append(f"Association PolicyID:{inputs['strategy_id']}")
    details.append("Platform calculates the complete matrix first; acceptance or export of the matrix is still subject to second explicit confirmation")
    return _confirmation(details)


def prepare_profit(
    inputs: Mapping[str, Any], context: StrategyWorkflowPreparationContext
) -> PreparedStrategyPlan:
    return _prepare_dataset_plan(
        "profit_calc", "strategy_profit_analysis", inputs, context
    )


def prepare_roll_rate(
    inputs: Mapping[str, Any], context: StrategyWorkflowPreparationContext
) -> PreparedStrategyPlan:
    return _prepare_dataset_plan(
        "roll_rate_matrix", "strategy_roll_rate_analysis", inputs, context
    )


def prepare_limit_pricing(
    inputs: Mapping[str, Any], context: StrategyWorkflowPreparationContext
) -> PreparedStrategyPlan:
    if context.dataset_id is None:
        raise StrategyWorkflowValidationError(
            "The range pricing matrix requires the only data set within the current task that is certified.",
            code="strategy_dataset_required",
        )
    if context.bind_sample_design is None:
        raise StrategyWorkflowValidationError(
            "The level pricing matrix requires a certified match between the current data and the label calibreSampleDesign.",
            code="strategy_sample_design_required",
        )
    thawed = deep_thaw(inputs)
    strategy_id = thawed.get("strategy_id")
    if strategy_id is not None and context.validate_strategy_ref is not None:
        context.validate_strategy_ref(
            str(strategy_id),
            frozenset({"limit", "pricing"}),
        )
    sample_design_ref = context.bind_sample_design(True)
    slots = {
        "dataset_id": context.dataset_id,
        **thawed,
        "sample_design_ref": deep_thaw(sample_design_ref),
    }
    if context.drop_nan_labels:
        slots["drop_nan_labels"] = True
    return PreparedStrategyPlan(
        workflow_id="limit_pricing_matrix",
        template_id="strategy_limit_pricing_analysis",
        slots=deep_freeze(slots),
    )


def _prepare_dataset_plan(
    workflow_id: str,
    template_id: str,
    inputs: Mapping[str, Any],
    context: StrategyWorkflowPreparationContext,
) -> PreparedStrategyPlan:
    if context.dataset_id is None:
        raise StrategyWorkflowValidationError(
            f"{workflow_id} Requires the only validated data set within the current task.",
            code="strategy_dataset_required",
        )
    return PreparedStrategyPlan(
        workflow_id=workflow_id,
        template_id=template_id,
        slots=deep_freeze({"dataset_id": context.dataset_id, **deep_thaw(inputs)}),
    )


def _confirmation(details: list[str]) -> str:
    details.append(
        "Please confirm the above calibre.Agent Only trusted tools are organized; all numbers are calculated by the platform ' s certainty."
    )
    return ";".join(details)


def _reject_fields(
    inputs: Mapping[str, Any], allowed: set[str], *, workflow: str
) -> None:
    unexpected = sorted(set(inputs) - allowed)
    if unexpected:
        raise StrategyWorkflowValidationError(
            f"{workflow} workflow_inputs Contains unsupported fields:"
            + ",".join(unexpected)
            + "."
        )


def _required_text(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StrategyWorkflowValidationError(f"{name} It must be non-empty.")
    return value.strip()


def _column(value: object, *, name: str, whitelist: tuple[str, ...]) -> str:
    column = _required_text(value, name=name)
    if column not in whitelist:
        raise StrategyWorkflowValidationError(
            f"{name} Use column of the data set that does not exist{column}]."
        )
    return column


def _bounded_number(
    value: object, *, name: str, maximum: float | None = None
) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise StrategyWorkflowValidationError(f"{name} It must be limited.")
    number = float(value)
    if (
        not math.isfinite(number)
        or number < 0
        or (maximum is not None and number > maximum)
    ):
        if maximum is None:
            raise StrategyWorkflowValidationError(
                f"{name} Must be a limited number greater than 0."
            )
        raise StrategyWorkflowValidationError(
            f"{name} It must be 0 to{maximum:g} There are limited numbers between."
        )
    return number


def _number_sequence(
    value: object,
    *,
    name: str,
    minimum: float | None,
    maximum_items: int,
    maximum: float | None = None,
    exclusive_minimum: bool = False,
    minimum_items: int = 1,
) -> list[float]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, str | bytes | bytearray)
        or not minimum_items <= len(value) <= maximum_items
    ):
        raise StrategyWorkflowValidationError(
            f"{name} Must be included.{minimum_items} Present.{maximum_items} An array of limited numbers."
        )
    numbers: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int | float):
            raise StrategyWorkflowValidationError(f"{name} Only limited numbers can be included.")
        number = float(item)
        if not math.isfinite(number):
            raise StrategyWorkflowValidationError(f"{name} Only limited numbers can be included.")
        if minimum is not None and (
            number < minimum or (exclusive_minimum and number == minimum)
        ):
            relation = "Greater than" if exclusive_minimum else "greater than or equal to"
            raise StrategyWorkflowValidationError(
                f"{name} Every value must be{relation} {minimum:g}."
            )
        if maximum is not None and number > maximum:
            raise StrategyWorkflowValidationError(
                f"{name} Each value must be less than equal{maximum:g}."
            )
        numbers.append(number)
    if len(set(numbers)) != len(numbers):
        raise StrategyWorkflowValidationError(f"{name} Cannot contain duplicate values.")
    return numbers
