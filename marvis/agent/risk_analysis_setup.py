"""Conversation-first setup for the user-facing risk-analysis task.

The public task type remains ``vintage`` for compatibility, but an agent task
must not guess which business report the user wants.  This module persists a
small intake state in assistant-message metadata and only returns a driver
template after the selected report's deterministic data contract is satisfied.

The state is deliberately stored on assistant messages (the same pattern as
the join C1 and portfolio-state gates).  ``_run_driver_turn`` stores the current
user message before calling setup, so state lookup must ignore user messages.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import re

from marvis.agent.vintage_setup import VintageSetupError, build_vintage_proposal
from marvis.domain import FileRole
from marvis.files import scan_source_dir


RISK_ANALYSIS_INTAKE_META_KEY = "risk_analysis_intake"

VTG_TERMINAL = "vtg_terminal"
PROFITABILITY = "profitability"
STANDARD_VINTAGE = "standard_vintage"

_REPORT_TEMPLATE_ID = "risk_analysis_report"


@dataclass(frozen=True)
class RiskAnalysisSetupDecision:
    """One setup transition, either a chat pause or a ready driver contract."""

    content: str
    metadata: dict
    template_id: str | None = None
    slots: dict | None = None

    @property
    def intake_state(self) -> dict:
        state = self.metadata.get(RISK_ANALYSIS_INTAKE_META_KEY)
        return dict(state) if isinstance(state, dict) else {}


@dataclass(frozen=True)
class _MaterialContract:
    analysis_kind: str
    table_name: str
    grain: str
    required: tuple[str, ...]
    optional: tuple[str, ...]
    one_of: tuple[str, ...] = ()
    alternative_groups: tuple[tuple[str, ...], ...] = ()
    conditional_groups: Mapping[str, tuple[tuple[str, ...], ...]] | None = None
    aliases: Mapping[str, tuple[str, ...]] | None = None

    @property
    def all_columns(self) -> tuple[str, ...]:
        alternatives = tuple(
            column for group in self.alternative_groups for column in group
        )
        conditional = tuple(
            column
            for groups in (self.conditional_groups or {}).values()
            for group in groups
            for column in group
        )
        return tuple(
            dict.fromkeys(
                (
                    *self.required,
                    *self.one_of,
                    *alternatives,
                    *conditional,
                    *self.optional,
                )
            )
        )


_VTG_CONTRACT = _MaterialContract(
    analysis_kind=VTG_TERMINAL,
    table_name="canonical VTG input",
    grain="Summary mode per product × cohort One line.;Original Balance Curve Mode Each product × cohort × MOB One line.",
    required=(
        "product",
        "as_of_date",
        "cohort",
        "amount_unit",
        "disbursement_amount",
        "mob14_bad_rate",
    ),
    one_of=(
        "terminal_bad_rate",
        "long_term_recovery_rate",
        "auxiliary_terminal_bad_rate",
    ),
    alternative_groups=(
        ("turnover",),
        ("mob", "mob_days", "day_count_basis", "mob_balance_rate"),
        ("mob", "mob_days", "day_count_basis", "mob_balance_amount"),
    ),
    optional=(
        "avg_daily_balance",
        "scenario",
        "channel",
        "tenor_months",
        "terminal_method",
        "selection_rule",
        "previous_mob14_bad_rate",
        "previous_terminal_bad_rate",
        "previous_turnover",
        "previous_annualized_bad_rate",
        "previous_disbursement_amount",
        "previous_avg_daily_balance",
        "auxiliary_terminal_bad_rate",
    ),
    aliases={
        "product": ("Products", "Product name", "product_name"),
        "as_of_date": ("Cross-section Day", "Data Date", "Date of measurement", "as_of_period"),
        "cohort": ("Month of the loan", "Month of loan", "cohort_month", "vintage"),
        "amount_unit": ("Amount units", "Currency units"),
        "disbursement_amount": ("Amount released", "Amounts released", "disbursed_amount"),
        "mob14_bad_rate": (
            "mob14Bad rate",
            "mob14_bad",
            "14mob_bad_rate",
            "MOB14 vtg30+",
            "MOB14_vtg30+",
        ),
        "turnover": ("Liquidity", "Number of turnovers", "Annual liquidity", "annual_turnover"),
        "mob": ("MOB", "Ageing", "Month age", "mob_month"),
        "mob_days": ("MOBDays", "Number of days", "Days", "day_weight", "days_in_mob"),
        "day_count_basis": ("Interest-bearing days base", "Number of days per year", "day_basis"),
        "mob_balance_rate": (
            "MOBBalance rate",
            "Balance rate",
            "balance_ratio",
            "balance_curve_rate",
        ),
        "mob_balance_amount": ("MOBBalance", "Balance", "balance_amount", "mob_balance"),
        "terminal_bad_rate": ("End-value bad rate", "vtgEnd value", "terminal_rate"),
        "long_term_recovery_rate": ("Long-term recovery rate", "Final recovery rate"),
        "avg_daily_balance": ("Average balance per day", "Average daily balance", "Average balance per month", "Average balance per year"),
        "terminal_method": ("End-of-value method", "Final caliber", "terminal_basis"),
        "selection_rule": ("Selection Rule", "End Value Selection Rules"),
        "scenario": ("Programme", "scene", "Version", "Contrast caliber", "scenario_name"),
        "channel": ("Channels", "channel_name"),
        "tenor_months": ("Duration", "Term", "loan_tenor_months"),
        "previous_mob14_bad_rate": ("Prior periodMOB14Bad rate",),
        "previous_terminal_bad_rate": ("Disadvantage rate at end of prior period",),
        "previous_turnover": ("Prior period turnover",),
        "previous_annualized_bad_rate": ("Prior-period annualized downscaling rate",),
        "previous_disbursement_amount": ("Prior period released", "Amount of prior period  s loan"),
        "previous_avg_daily_balance": ("Average balance at prior period",),
        "auxiliary_terminal_bad_rate": ("Assisted end", "Assisted end-of-life rate"),
    },
)

_PROFITABILITY_CONTRACT = _MaterialContract(
    analysis_kind=PROFITABILITY,
    table_name="canonical economics",
    grain="Every one. product × as_of_period × scenario × asset_class One line.",
    required=(
        "product",
        "as_of_period",
        "asset_class",
        "weight",
        "weight_basis",
        "customer_rate",
        "acquisition_cost_rate",
        "payment_cost_rate",
        "collection_cost_rate",
        "funding_cost_rate",
        "other_cost_rate",
    ),
    conditional_groups={
        "Risk cost": (
            ("risk_cost_rate",),
            ("terminal_vintage_rate", "risk_turnover"),
        ),
        "Loss of interest": (
            ("interest_loss_rate",),
            ("loss_timing_factor",),
        ),
        "Earning costs": (
            ("revenue_share_rate",),
            ("profit_share_ratio",),
        ),
        "Data cost": (
            ("data_cost_rate",),
            (
                "per_application_cost",
                "credit_approval_rate",
                "draw_initiation_rate",
                "draw_approval_rate",
                "average_ticket",
                "data_annualization_factor",
                "amount_unit",
            ),
        ),
        "Tax costs": (
            ("tax_rate",),
            ("tax_method", "tax_inclusive_divisor", "tax_combined_rate"),
        ),
    },
    optional=(
        "scenario",
        "amount_unit",
        "customer_stage",
        "transaction_weight",
    ),
    aliases={
        "product": ("Products", "Product name", "product_name"),
        "as_of_period": ("as_of_date", "Cross-section Day", "Cross-section period", "Period of measurement", "Data Date"),
        "scenario": ("Programme", "scene", "Version", "Contrast caliber", "scenario_name"),
        "asset_class": ("Type of asset", "Asset class", "asset_type"),
        "weight": ("Weights", "Percentage"),
        "weight_basis": ("Weight caliber", "weight_type"),
        "customer_rate": ("Client interest rate", "Guest interest rate"),
        "risk_cost_rate": ("Risk cost rate", "Risk cost"),
        "funding_cost_rate": ("Cost of funds", "Cost of funds"),
        "interest_loss_rate": ("Interest rate",),
        "revenue_share_rate": (
            "Annualized estuarine cost factor",
            "Accrual cost of the asset",
            "Rates of depreciation",
        ),
        "acquisition_cost_rate": ("Cost-of-takers rate",),
        "data_cost_rate": ("Data cost rate",),
        "payment_cost_rate": ("Cost of payment",),
        "collection_cost_rate": ("Routine cost",),
        "tax_rate": ("Annualized tax rates", "Asset caliber rate", "Tax and tariff cost rate"),
        "other_cost_rate": ("Other cost rates",),
        "terminal_vintage_rate": ("VTGEnd value", "End-value bad rate", "terminal_bad_rate"),
        "risk_turnover": ("Risk turnover", "Annual turnover", "risk_annual_turnover"),
        "loss_timing_factor": ("Time factor for loss", "loss_factor"),
        "profit_share_ratio": ("Contract share", "Scalable ratio", "contract_share_ratio"),
        "per_application_cost": ("Single application cost", "Cost of application", "application_unit_cost"),
        "credit_approval_rate": ("Pass rate",),
        "draw_initiation_rate": ("Startup rate with letters",),
        "draw_approval_rate": ("Passage rate",),
        "average_ticket": ("Average", "Average", "average_loan_amount"),
        "data_annualization_factor": ("Data cost annualization factor", "Annualization factor"),
        "tax_method": ("Tax and excise methodology", "Tax caliber"),
        "tax_inclusive_divisor": ("Including tax division", "Price tax separation factor"),
        "tax_combined_rate": ("Combined tax rates", "Additional tax rates"),
        "amount_unit": ("Amount units", "Currency units"),
        "customer_stage": ("Client phase", "First buy-back phase", "stage"),
        "transaction_weight": ("Pen weight", "Trade weights", "stage_weight"),
    },
)

_CONTRACTS = {
    VTG_TERMINAL: _VTG_CONTRACT,
    PROFITABILITY: _PROFITABILITY_CONTRACT,
}


def advance_risk_analysis_setup(
    registry,
    backend,
    task_id: str,
    source_dir,
    *,
    user_text: str | None,
    conversation: Sequence[dict],
    analysis_kind_override: str | None = None,
    target_col: str | None = None,
    time_col: str | None = None,
) -> RiskAnalysisSetupDecision:
    """Advance the persisted intake state by one user turn.

    No-data and bad-contract conditions are normal chat pauses, not setup
    exceptions.  A ready decision is the only result carrying a template id.
    """

    previous = latest_risk_analysis_intake(conversation)
    if previous is None:
        return _ask_goal()

    phase = str(previous.get("phase") or "")
    semantic_kind = (
        analysis_kind_override
        if analysis_kind_override in {VTG_TERMINAL, PROFITABILITY, STANDARD_VINTAGE}
        else None
    )
    if phase == "ask_goal":
        analysis_kind = semantic_kind or parse_analysis_kind(user_text)
        if analysis_kind is None:
            return _ask_goal(clarify=True)
        return _request_materials(
            analysis_kind,
            analysis_scope=_bounded_scope(user_text),
            label_semantics=(
                _parse_label_semantics(user_text)
                if analysis_kind == STANDARD_VINTAGE
                else None
            ),
        )

    analysis_kind = str(previous.get("analysis_kind") or "")
    analysis_scope = _bounded_scope(previous.get("analysis_scope"))
    changed_kind = semantic_kind or _parse_explicit_analysis_switch(user_text)
    if changed_kind is not None and changed_kind != analysis_kind:
        return _request_materials(
            changed_kind,
            analysis_scope=_bounded_scope(user_text),
            label_semantics=(
                _parse_label_semantics(user_text)
                if changed_kind == STANDARD_VINTAGE
                else None
            ),
        )
    if analysis_kind not in {VTG_TERMINAL, PROFITABILITY, STANDARD_VINTAGE}:
        return _ask_goal(clarify=True)

    label_semantics = None
    if analysis_kind == STANDARD_VINTAGE:
        persisted_semantics = str(previous.get("label_semantics") or "").strip()
        if persisted_semantics in {"incremental", "snapshot"}:
            label_semantics = persisted_semantics
        label_semantics = (
            _parse_label_semantics(user_text)
            or label_semantics
            or _parse_label_semantics(analysis_scope)
        )

    datasets = _ensure_registered_datasets(registry, task_id, source_dir)
    if not datasets:
        return _await_no_data(
            analysis_kind,
            analysis_scope=analysis_scope,
            label_semantics=label_semantics,
        )

    if analysis_kind == STANDARD_VINTAGE:
        return _prepare_standard_vintage(
            registry,
            backend,
            task_id,
            source_dir,
            target_col=target_col,
            time_col=time_col,
            analysis_scope=analysis_scope,
            label_semantics=label_semantics,
        )

    contract = _CONTRACTS[analysis_kind]
    match = _best_contract_match(registry, backend, datasets, contract)
    if match["missing_columns"]:
        return _await_missing_columns(
            analysis_kind,
            contract,
            match,
            analysis_scope=analysis_scope,
        )
    return _ready_report(
        analysis_kind,
        contract,
        match,
        analysis_scope=analysis_scope,
    )


def latest_risk_analysis_intake(conversation: Sequence[dict]) -> dict | None:
    """Return the latest assistant-owned intake state.

    User messages are intentionally ignored: the current user turn has already
    been appended when setup runs.
    """

    for message in reversed(conversation):
        if message.get("role") != "assistant":
            continue
        state = (message.get("metadata") or {}).get(RISK_ANALYSIS_INTAKE_META_KEY)
        if isinstance(state, dict):
            return dict(state)
    return None


def parse_analysis_kind(user_text: str | None) -> str | None:
    text = _normalize_text(user_text)
    if not text:
        return None
    # Specific terminal/annualized requests must win over the generic
    # ``vintage`` token.
    if (
        "vtgEnd value" in text
        or "End and year-old poor" in text
        or ("End value" in text and "Unenviable age" in text)
        or "vtgterminal" in text
    ):
        return VTG_TERMINAL
    if any(
        token in text
        for token in ("Proceeds measure", "Profit measurement", "Profit measurement", "profitability", "economics")
    ):
        return PROFITABILITY
    if any(
        token in text
        for token in (
            "Standardvintage",
            "vintageAnalysis",
            "Standard ageing",
            "An age curve",
            "standardvintage",
        )
    ):
        return STANDARD_VINTAGE
    return None


def _parse_explicit_analysis_switch(user_text: str | None) -> str | None:
    text = _normalize_text(user_text)
    if not text or not any(
        token in text
        for token in ("Change", "For", "Switch to", "Switch to", "Replace", "Reselect")
    ):
        return None
    return parse_analysis_kind(user_text)


def _parse_label_semantics(user_text: str | None) -> str | None:
    text = _normalize_text(user_text)
    if not text:
        return None
    incremental_tokens = ("incremental", "Incremental Label", "Add for the current period", "New events occurring in the period")
    snapshot_tokens = ("snapshot", "Quick-Signator Label", "Status as of current", "everbad")

    def explicitly_negated(token: str) -> bool:
        return any(
            f"{prefix}{token}" in text
            for prefix in ("No, its not.", "Not really.", "Not", "Not", "not", "Dont.")
        )

    incremental = any(
        token in text and not explicitly_negated(token)
        for token in incremental_tokens
    )
    snapshot = any(
        token in text and not explicitly_negated(token)
        for token in snapshot_tokens
    )
    if incremental == snapshot:
        return None
    return "incremental" if incremental else "snapshot"


def material_contract(analysis_kind: str) -> dict:
    """Expose a JSON-safe contract for UI/tests without leaking internals."""

    if analysis_kind == STANDARD_VINTAGE:
        return {
            "table": "vintage panel",
            "grain": "Every one. cohort × MOB One line.(or account × MOB Details)",
            "required_columns": ["cohort", "mob", "bad"],
            "one_of_columns": [],
            "optional_columns": ["product", "loan_id", "exposure"],
        }
    contract = _CONTRACTS[analysis_kind]
    return {
        "table": contract.table_name,
        "grain": contract.grain,
        "required_columns": list(contract.required),
        "one_of_columns": list(contract.one_of),
        "alternative_column_groups": [
            list(group) for group in contract.alternative_groups
        ],
        "conditional_column_groups": {
            label: [list(group) for group in groups]
            for label, groups in (contract.conditional_groups or {}).items()
        },
        "optional_columns": list(contract.optional),
    }


def _ask_goal(*, clarify: bool = False) -> RiskAnalysisSetupDecision:
    prefix = (
        "Im not sure which risk analysis youre going to take.."
        if clarify
        else "Just check it out.:What are you trying to analyze??"
    )
    content = (
        f"{prefix}\n"
        "1. **VTGEnd and year-old poor**:By Product/cohort Measurement end value,Unrevolving and annualization;\n"
        "2. **Proceeds measure**:Summary of income by product and asset type,Risk/Funds/Operating costs and benefits;\n"
        "3. **Standard Vintage**:Press cohort × MOB Generate a bad-account curve.\n"
        "Please answer one of them directly.,And add a range or contrast.(Like a product.,Observation period,Baseline version)."
    )
    return _chat_decision(content, {"phase": "ask_goal"})


def _request_materials(
    analysis_kind: str,
    *,
    analysis_scope: str | None = None,
    label_semantics: str | None = None,
) -> RiskAnalysisSetupDecision:
    scope_line = (
        f"\n- Your target has been recorded./Scope:{analysis_scope};Report overwrite all lines in upload table."
        if analysis_scope
        else ""
    )
    if analysis_kind == VTG_TERMINAL:
        content = (
            "Target confirmed.:**VTGEnd and year-old poor**.Please, one. canonical VTG input:\n"
            "- Summarize the particle size of the mode:Every one. product × cohort One line.,And provide turnover;\n"
            "- Particleity of original balance curve:Every one. product × cohort × MOB One line.,Provision "
            "mob, mob_days, day_count_basis,and mob_balance_rate or mob_balance_amount;"
            "These two balance fields must be each MOB Average daily balance rate/Amount,Not the end of the month.;The system will be as you wish."
            " day_count_basis Self-suspension of average annual daily balances and turnover;\n"
            "- Both models are required in common:product, as_of_date, cohort, amount_unit, "
            "disbursement_amount, mob14_bad_rate;The amount of the loan must be greater than 0;\n"
            "- Enter the final three or one.:terminal_bad_rate;or long_term_recovery_rate;or at the same time "
            "terminal_method=min_mob14_auxiliary and auxiliary_terminal_bad_rate;\n"
            "- Optional Columns:scenario, channel, tenor_months, selection_rule, avg_daily_balance, "
            "previous_terminal_bad_rate, previous_turnover, previous_annualized_bad_rate, "
            "auxiliary_terminal_bad_rate, terminal_method;\n"
            "- One. VTG Only one can be included in the combination report. as_of_date And one. scenario;"
            "Multi-face/Multi scenes are uploaded and generated separately.,Avoiding double-counting in the group;\n"
            "- caliber:All percentages used as decimal(For example: 2.5% Fill 0.025),turnover Filling year turnover;"
            "mob14_bad_rate It has to be real. MOB14 Or project it in a clear way. MOB14 Its... VTG30+,"
            "Cant fill it directly. MOB3/MOB6 Current value;"
            "If the ancillary end value is provided and the end value is derived from the long-term recovery rate,It must also be visible. "
            "selection_rule=min_auxiliary_recovery,Ill take it. terminal = min(Assisted end, "
            "End value derived from recovery rate).The end-of-life approach may vary from one product to another.,"
            "Here you go. terminal_method Annotations,No system guess.."
            f"{scope_line}\n"
            "Reply after upload(Materials uploaded),Ill check the contract by table.,If youre missing, youll make it clear.."
        )
    elif analysis_kind == PROFITABILITY:
        content = (
            "Target confirmed.:**Proceeds measure**.Please provide a standardized data sheet:\n"
            "- Table:canonical economics;\n"
            "- Particleity:Every one. product × as_of_period × scenario × asset_class One line.;Single programme omitted "
            "scenario,System as(Benchmark);\n"
            "- Common Required Column:product, as_of_period, asset_class, weight, weight_basis, "
            "customer_rate, acquisition_cost_rate, payment_cost_rate, collection_cost_rate, "
            "funding_cost_rate, other_cost_rate;weight_basis It must be. average_balance;\n"
            "- Risk cost is selected for one:risk_cost_rate;or terminal_vintage_rate + risk_turnover;\n"
            "- The interest rate is lost by one.:interest_loss_rate;or loss_timing_factor(System Press "
            "customer_rate × risk_cost_rate × factor Insulation);\n"
            "- One for the cost of the split.:revenue_share_rate(Annualized cost rate);or "
            "profit_share_ratio(Contract share,Conversion of system to revenue_share_rate);\n"
            "- acquisition_cost_rate For independent client costs that differ from those for the contracts;"
            "If no explicit filling is required 0,The same contract cannot be split into two fields at the same time.;\n"
            "- Data cost is selected for one:data_cost_rate;or per_application_cost, credit_approval_rate, "
            "draw_initiation_rate, draw_approval_rate, average_ticket, data_annualization_factor;\n"
            "  If the first pen/Repurchase branch,And add. customer_stage and transaction_weight;System-by-stage"
            "Insulation,Summarized as the cost of data for asset classes by weight of numbers(Sample 1:9 No hard code.);\n"
            "- Taxes and charges are selected for one.:tax_rate;or tax_method=sample_net_revenue_vat_surcharge, "
            "tax_inclusive_divisor, tax_combined_rate;The tax base of the model is clearly defined as loss of interest rate reduction on customers.,"
            "Duplicate,Independently.,Data,Payment and collection costs,No risk./Cost of funds;in the sample /2,1.06,6.72% "
            "The equation must be used as input,Not buried as default;\n"
            "- Optional Columns:scenario, amount_unit, customer_stage, transaction_weight;Original Amount Driver"
            "I have to explain. amount_unit.\n"
            "- caliber:Consistent units of measurement and annualization are used in each line;All scale decimals;"
            "weight Its the same product./Period/The asset weights under the programme shall be aggregated 1;Please explain that taxes and taxes are tax-inclusive.,"
            "Pre-tax deduction or post-tax calibration.;revenue_share_rate Must have been converted to the asset yield calibre."
            "Rates of depreciation,Cant just fill out the contract ration ratio.;Original contract sub-contracts requested profit_share_ratio."
            "Costs of non-occupying and no driver must be filled in visibly 0,"
            "The system doesnt take missing costs silently. 0."
            f"{scope_line}\n"
            "Reply after upload(Materials uploaded),Ill check the contract by table.,If youre missing, youll make it clear.."
        )
    else:
        content = (
            "Target confirmed.:**Standard Vintage**.Please provide Vintage panel:\n"
            "- Table:vintage panel;\n"
            "- Particleity:Every one. cohort × MOB One line.,or account × MOB Details;\n"
            "- Required Columns:cohort(Releases/Month),mob(Month age),bad(Bad tag or bad debt increment);\n"
            "- Optional Columns:product, loan_id, exposure;\n"
            "- caliber:Please describe bad Yes. incremental(Add for the current period)Or is it? snapshot(Status as of current),"
            "No system guess..\n"
            f"{scope_line}\n"
            "Reply after upload(Materials uploaded),Ill check the fields and generate standards. Vintage Planned."
        )
    state = {"phase": "request_materials", "analysis_kind": analysis_kind}
    if analysis_scope:
        state["analysis_scope"] = analysis_scope
    if analysis_kind == STANDARD_VINTAGE and label_semantics is not None:
        state["label_semantics"] = label_semantics
    return _chat_decision(
        content,
        state,
        contract=material_contract(analysis_kind),
    )


def _await_no_data(
    analysis_kind: str,
    *,
    analysis_scope: str | None = None,
    label_semantics: str | None = None,
) -> RiskAnalysisSetupDecision:
    state = {"phase": "await_materials", "analysis_kind": analysis_kind}
    if analysis_scope:
        state["analysis_scope"] = analysis_scope
    if analysis_kind == STANDARD_VINTAGE and label_semantics is not None:
        state["label_semantics"] = label_semantics
    return _chat_decision(
        "Not registered data form detected.Press the watch above./Particleity/Field List Pass CSV,XLSX or Parquet;"
        "Reply after upload completion(Materials uploaded),Ill do the contract check..",
        state,
        contract=material_contract(analysis_kind),
    )


def _await_missing_columns(
    analysis_kind: str,
    contract: _MaterialContract,
    match: dict,
    *,
    analysis_scope: str | None = None,
) -> RiskAnalysisSetupDecision:
    missing = list(match["missing_columns"])
    ambiguous = list(match.get("ambiguous_columns") or [])
    observed = ", ".join(match["observed_columns"]) or "(Unread Column)"
    ambiguity_line = (
        "\nField Name Conflict:"
        + ";".join(
            f"{item['canonical']} Matches {', '.join(item['source_columns'])}"
            for item in ambiguous
        )
        + ".Please retain a clear and sole listing for uploading."
        if ambiguous
        else ""
    )
    content = (
        f"Checked the closest data table to the contract `{match['dataset_name']}`,We cant start the measurements yet..\n"
        f"Missing:{', '.join(missing)}.\n"
        f"Recognized Columns:{observed}.{ambiguity_line}\n"
        "Please fill these columns and re-up and upload them.;Im not replacing a similar but undefined field.,Im not gonna start the program without a column.."
    )
    state = {
        "phase": "await_materials",
        "analysis_kind": analysis_kind,
        "dataset_id": match["dataset_id"],
        "missing_columns": missing,
    }
    if ambiguous:
        state["ambiguous_columns"] = ambiguous
    if analysis_scope:
        state["analysis_scope"] = analysis_scope
    return _chat_decision(
        content, state, contract=material_contract(contract.analysis_kind)
    )


def _ready_report(
    analysis_kind: str,
    contract: _MaterialContract,
    match: dict,
    *,
    analysis_scope: str | None = None,
) -> RiskAnalysisSetupDecision:
    column_map = dict(match["column_map"])
    state = {
        "phase": "ready",
        "analysis_kind": analysis_kind,
        "dataset_id": match["dataset_id"],
        "column_map": column_map,
    }
    if analysis_scope:
        state["analysis_scope"] = analysis_scope
    scope_confirmation = (
        f"Reserved Target/Scope({analysis_scope});Specific coverage to be matched by the full upload form of the contract."
        if analysis_scope
        else "All behaviour of the above-mentioned pass forms is consistent."
    )
    return RiskAnalysisSetupDecision(
        content=(
            f"The material contract has been approved.:To be used `{match['dataset_name']}` Generate"
            f"{'VTGEnd and year-old poor' if analysis_kind == VTG_TERMINAL else 'Proceeds measure'}Report,"
            f"and list key indicators in the outcome,Anomalous,Assumptions and downloadable files.{scope_confirmation}"
        ),
        metadata={
            "intent": "vintage",
            RISK_ANALYSIS_INTAKE_META_KEY: state,
            "risk_analysis_contract": material_contract(contract.analysis_kind),
        },
        template_id=_REPORT_TEMPLATE_ID,
        slots={
            "analysis_kind": analysis_kind,
            "dataset_id": match["dataset_id"],
            "column_map": column_map,
        },
    )


def _prepare_standard_vintage(
    registry,
    backend,
    task_id: str,
    source_dir,
    *,
    target_col: str | None,
    time_col: str | None,
    analysis_scope: str | None = None,
    label_semantics: str | None = None,
) -> RiskAnalysisSetupDecision:
    try:
        proposal = build_vintage_proposal(
            registry,
            backend,
            task_id,
            source_dir,
            target_col=target_col,
            time_col=time_col,
        )
    except VintageSetupError as exc:
        state = {
            "phase": "await_materials",
            "analysis_kind": STANDARD_VINTAGE,
            "validation_error": str(exc),
        }
        if analysis_scope:
            state["analysis_scope"] = analysis_scope
        if label_semantics is not None:
            state["label_semantics"] = label_semantics
        return _chat_decision(
            f"Standard Vintage The material is not field-checked yet:{exc} Please re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up and re-up..",
            state,
            contract=material_contract(STANDARD_VINTAGE),
        )
    state = {
        "phase": "ready",
        "analysis_kind": STANDARD_VINTAGE,
        "dataset_id": proposal.dataset_id,
        "column_map": {
            "cohort": proposal.cohort_col,
            "mob": proposal.mob_col,
            "bad": proposal.bad_col,
        },
    }
    if analysis_scope:
        state["analysis_scope"] = analysis_scope
    if label_semantics is not None:
        state["label_semantics"] = label_semantics
    slots = proposal.template_slots()
    if label_semantics is not None:
        slots["label_semantics"] = label_semantics
    semantics_confirmation = (
        f",Label Semantics `{label_semantics}`" if label_semantics is not None else ""
    )
    return RiskAnalysisSetupDecision(
        content=(
            f"Standard Vintage The material is approved.:Sample `{proposal.dataset_name}`,cohort "
            f"`{proposal.cohort_col}`,MOB `{proposal.mob_col}`,Bad accounts `{proposal.bad_col}`"
            f"{semantics_confirmation}."
        ),
        metadata={
            "intent": "vintage",
            RISK_ANALYSIS_INTAKE_META_KEY: state,
            "risk_analysis_contract": material_contract(STANDARD_VINTAGE),
        },
        template_id=proposal.template_id,
        slots=slots,
    )


def _chat_decision(
    content: str,
    state: dict,
    *,
    contract: dict | None = None,
) -> RiskAnalysisSetupDecision:
    metadata = {"intent": "vintage", RISK_ANALYSIS_INTAKE_META_KEY: dict(state)}
    if contract is not None:
        metadata["risk_analysis_contract"] = dict(contract)
    return RiskAnalysisSetupDecision(content=content, metadata=metadata)


def _ensure_registered_datasets(registry, task_id: str, source_dir) -> list:
    datasets = list(registry.list_for_task(task_id))
    if datasets:
        return datasets
    raw_source = str(source_dir or "").strip()
    if not raw_source:
        return []
    source_path = Path(raw_source)
    if not source_path.is_dir():
        return []
    try:
        artifacts = scan_source_dir(source_path)
    except (OSError, ValueError):
        return []
    registration_errors: list[Exception] = []
    for artifact in artifacts:
        if artifact.role != FileRole.SAMPLE:
            continue
        try:
            registry.register_from_upload(task_id, Path(artifact.path), role="sample")
        except Exception as exc:
            # Try every candidate so one stale file does not hide a usable table.
            # If none can be registered, re-raise the first typed ingest error:
            # the driver converts it into the existing structured, retryable
            # workflow diagnostic instead of silently claiming no material exists.
            registration_errors.append(exc)
            continue
    datasets = list(registry.list_for_task(task_id))
    if datasets:
        return datasets
    if registration_errors:
        raise registration_errors[0]
    return []


def _best_contract_match(
    registry, backend, datasets: Iterable, contract: _MaterialContract
) -> dict:
    matches = []
    for upload_order, dataset in enumerate(datasets):
        match = _contract_match(registry, backend, dataset, contract)
        match["upload_order"] = upload_order
        matches.append(match)
    return max(
        matches,
        key=lambda item: (
            -len(item["missing_columns"]),
            int(item["upload_order"]),
        ),
    )


def _contract_match(registry, backend, dataset, contract: _MaterialContract) -> dict:
    columns = _dataset_columns(registry, backend, dataset)
    lookup: dict[str, list[str]] = {}
    for column in columns:
        if not str(column).strip():
            continue
        lookup.setdefault(_normalize_column(column), []).append(column)
    aliases = contract.aliases or {}
    column_map: dict[str, str] = {}
    ambiguous_columns: list[dict[str, object]] = []
    for canonical in contract.all_columns:
        candidates = (canonical, *aliases.get(canonical, ()))
        for candidate in candidates:
            matches = lookup.get(_normalize_column(candidate), [])
            if not matches:
                continue
            if len(matches) == 1:
                column_map[canonical] = matches[0]
            else:
                ambiguous_columns.append(
                    {
                        "canonical": canonical,
                        "source_columns": list(matches),
                    }
                )
            break
    ambiguous_canonicals = {
        str(item["canonical"]) for item in ambiguous_columns
    }
    missing = [
        column
        for column in contract.required
        if column not in column_map and column not in ambiguous_canonicals
    ]
    missing.extend(
        f"{item['canonical']}(Match multiple source columns after integration)"
        for item in ambiguous_columns
    )
    if contract.one_of and not any(column in column_map for column in contract.one_of):
        missing.append(" or ".join(contract.one_of) + "(At least one.)")
    if (
        contract.analysis_kind == VTG_TERMINAL
        and "auxiliary_terminal_bad_rate" in column_map
        and "terminal_bad_rate" not in column_map
        and "long_term_recovery_rate" not in column_map
        and "terminal_method" not in column_map
    ):
        missing.append(
            "terminal_method(Use only auxiliary_terminal_bad_rate Required when extrapolating end value)"
        )
    if (
        contract.analysis_kind == VTG_TERMINAL
        and "long_term_recovery_rate" in column_map
        and "auxiliary_terminal_bad_rate" in column_map
        and "selection_rule" not in column_map
    ):
        missing.append("selection_rule(Recovery extrapolation end value necessary when the supporting end is present)")
    if contract.alternative_groups and not any(
        all(column in column_map for column in group)
        for group in contract.alternative_groups
    ):
        group_labels = [
            group[0] if len(group) == 1 else "(" + " + ".join(group) + ")"
            for group in contract.alternative_groups
        ]
        missing.append(" or ".join(group_labels) + "(Meet a group)")
    for label, groups in (contract.conditional_groups or {}).items():
        if any(all(column in column_map for column in group) for group in groups):
            continue
        group_labels = [
            group[0] if len(group) == 1 else "(" + " + ".join(group) + ")"
            for group in groups
        ]
        missing.append(f"{label}: " + " or ".join(group_labels) + "(Meet a group)")
    if (
        contract.analysis_kind == PROFITABILITY
        and "customer_stage" in column_map
        and "transaction_weight" not in column_map
    ):
        missing.append("transaction_weight(customer_stage Sub-lines required)")
    return {
        "dataset_id": str(getattr(dataset, "id", "")),
        "dataset_name": _dataset_name(dataset),
        "row_count": int(getattr(dataset, "row_count", 0) or 0),
        "observed_columns": columns,
        "column_map": column_map,
        "missing_columns": missing,
        "ambiguous_columns": ambiguous_columns,
    }


def _dataset_columns(registry, backend, dataset) -> list[str]:
    try:
        return [
            str(column)
            for column in backend.column_names(registry.resolve_path(dataset.id))
        ]
    except Exception:
        profiles = getattr(dataset, "columns", ()) or ()
        return [str(getattr(profile, "name", profile)) for profile in profiles]


def _dataset_name(dataset) -> str:
    sheet = str(getattr(dataset, "sheet", "") or "").strip()
    if sheet:
        return sheet
    source = str(getattr(dataset, "source_path", "") or "").strip()
    return Path(source).stem if source else str(getattr(dataset, "id", ""))


def _normalize_column(value: str) -> str:
    return re.sub(r"[\s_\-./()()]+", "", str(value).strip().casefold())


def _normalize_text(value: str | None) -> str:
    return re.sub(r"[\s_\-./()()]+", "", str(value or "").strip().casefold())


def _bounded_scope(value: object, *, max_chars: int = 240) -> str | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


__all__ = [
    "PROFITABILITY",
    "RISK_ANALYSIS_INTAKE_META_KEY",
    "RiskAnalysisSetupDecision",
    "STANDARD_VINTAGE",
    "VTG_TERMINAL",
    "advance_risk_analysis_setup",
    "latest_risk_analysis_intake",
    "material_contract",
    "parse_analysis_kind",
]
