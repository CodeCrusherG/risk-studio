"""Agent-mode gate-instruction router.

At a confirmation gate the user (agent mode) may reply with free text instead of
[Confirmed –e.g. "Flow threshold to 0.1", "n_trials To 20", "Changexgb Remodel". This routes
that instruction into a structured action the driver can execute:

  - confirm: the text actually means "proceed" → confirm the gate.
  - adjust:  tweak the parameters of the just-computed step and re-run it.
  - replan:  a structural change (add/remove steps, switch algorithm) → regenerate
             the remaining plan with the instruction as a constraint.
  - clarify: the instruction is unclear / unactionable → ask the user.

Pure + offline-testable: the LLM client is injected, so a FakeLLM drives it in
tests (the platform may have no LLM configured yet).
"""

from __future__ import annotations

import json

from marvis.agent.adjust_specs import normalize_adjust_params
from marvis.agent.json_reply import load_json_object, rejects_positive_decision
from marvis.llm_prompts import GATE_INSTRUCTION_ROUTER_SYS as _GATE_INSTRUCTION_ROUTER_SYS_SPEC

_ACTIONS = ("confirm", "adjust", "replan", "clarify")
_ROUTE_FIELDS = (
    "action",
    "params",
    "constraint",
    "reason",
    "confidence",
    "explicit_authorization",
)

# LLM-10: text/version now live in marvis.llm_prompts; kept as a module-level
# constant so existing imports of _SYSTEM from here keep working unchanged.
_SYSTEM = _GATE_INSTRUCTION_ROUTER_SYS_SPEC.text

_ROUTE_SCHEMA = {
    "name": "gate_instruction_route",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": list(_ACTIONS)},
            "params": {"type": "object"},
            "constraint": {"type": "string"},
            "reason": {"type": "string"},
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
            },
            "explicit_authorization": {"type": "boolean"},
        },
        "required": list(_ROUTE_FIELDS),
        "additionalProperties": False,
    },
}


def route_instruction(
    client,
    *,
    gate_context,
    instruction,
    tables=None,
    param_schema=None,
    strict_contract=False,
):
    """Ask the injected LLM to classify one free-text gate instruction.

    ``param_schema`` (optional, AGT-5): the current gate's adjustable-parameter
    summary — a list of ``{"name", "type", "current", "bounds"}`` dicts assembled
    from the gate's dependency step inputs (see
    ``marvis.agent.gate_param_schema.gate_param_schema``). Injected into the
    prompt so the routing LLM extracts ``adjust`` params against real parameter
    names/bounds instead of guessing key names from the instruction text alone."""
    prompt = _format(gate_context, instruction, tables or [], param_schema or [])
    raw = client.complete(
        system_prompt=_SYSTEM,
        user_prompt=prompt,
        temperature=0.0,
        response_format={"type": "json_object"},
        json_schema=_ROUTE_SCHEMA,
        stream=False,
        caller="router",
        prompt_name=_GATE_INSTRUCTION_ROUTER_SYS_SPEC.name,
        prompt_version=_GATE_INSTRUCTION_ROUTER_SYS_SPEC.version,
    )
    route, ok = _parse_route(raw, strict_contract=strict_contract)
    if ok:
        route = _recover_declared_parameter_adjustment(
            client,
            route=route,
            prompt=prompt,
            instruction=instruction,
            param_schema=param_schema or [],
        )
        return _recover_declared_selection_decision(
            client,
            route=route,
            prompt=prompt,
            param_schema=param_schema or [],
        )
    if strict_contract:
        return route
    retry_prompt = (
        f"{prompt}\n\n"
        f"[Last Return Unresolved]\n{raw}\n\n"
        'Please return strictly.JSON Object:{"action":"confirm|adjust|replan|clarify","params":{},'
        '"constraint":"","reason":"Chinese in one sentence","confidence":"high|medium|low",'
        '"explicit_authorization":false}.'
    )
    raw = client.complete(
        system_prompt=_SYSTEM,
        user_prompt=retry_prompt,
        temperature=0.0,
        response_format={"type": "json_object"},
        json_schema=_ROUTE_SCHEMA,
        stream=False,
        caller="router",
        prompt_name=_GATE_INSTRUCTION_ROUTER_SYS_SPEC.name,
        prompt_version=_GATE_INSTRUCTION_ROUTER_SYS_SPEC.version,
    )
    route = parse_route(raw)
    route = _recover_declared_parameter_adjustment(
        client,
        route=route,
        prompt=prompt,
        instruction=instruction,
        param_schema=param_schema or [],
    )
    return _recover_declared_selection_decision(
        client,
        route=route,
        prompt=prompt,
        param_schema=param_schema or [],
    )


_MODELING_ADJUST_PARAM_NAMES = frozenset(
    {"split_config", "target_type", "recipes", "n_trials", "sample_weight_col"}
)
_MODELING_ADJUST_CUES = (
    "oot",
    "Severation",
    "Division",
    "Training Set",
    "Test Set",
    "Time push",
    "Just leave it at random.",
    "Algorithm",
    "Model",
    "Transfer",
    "Wheel",
    "lgb",
    "lightgbm",
    "xgb",
    "xgboost",
    "catboost",
    "scorecard",
    "Scorecard",
    "Logical regression",
    "mlp",
    "Sample weights",
)
_STRUCTURAL_REPLAN_CUES = (
    "Reordering steps",
    "Reordering Steps",
    "Change process",
    "Change process",
    "Switch Process",
)


def _recover_declared_parameter_adjustment(
    client,
    *,
    route: dict,
    prompt: str,
    instruction,
    param_schema,
) -> dict:
    """Give a modeling control request one bounded completeness review.

    Modeling setup now exposes algorithms, tuning budget, target family, sample
    weight, and split configuration as typed controls on the current gate.  The
    historical router prompt treated any algorithm change as a structural
    replan, which sent an otherwise local patch through a much broader
    best-effort planner.  We only reconsider when the requested concepts are
    declared by this gate and the text does not explicitly add/remove/reorder
    steps.  The returned params still pass the driver's normal gate-scoped
    validation before any step is reset.
    """

    if route.get("action") not in {"adjust", "replan"}:
        return route
    declared = {
        str(item.get("name") or "").strip()
        for item in list(param_schema or [])
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    fallback = dict(route)
    if fallback.get("action") == "adjust":
        fallback["params"] = normalize_adjust_params(fallback.get("params"))
        fallback = _canonicalize_sample_weight_selection(
            fallback,
            declared=declared,
        )
    if not (declared & _MODELING_ADJUST_PARAM_NAMES):
        return fallback
    text = str(instruction or "").strip()
    lowered = text.lower()
    changes_steps = "Steps" in text and any(
        verb in text
        for verb in ("Add", "Increase", "Add", "Delete", "Remove", "Get rid of it.", "Skip", "Reorder")
    )
    if changes_steps or any(cue in text for cue in _STRUCTURAL_REPLAN_CUES):
        return fallback
    if not any(cue in lowered for cue in _MODELING_ADJUST_CUES):
        return fallback

    declared_text = ",".join(sorted(declared & _MODELING_ADJUST_PARAM_NAMES))
    first_pass = json.dumps(
        route,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    review_prompt = (
        f"{prompt}\n\n"
        "[Current Node Parameter Adjustment Review]\n"
        f"The first structured result:{first_pass}\n"
        f"The current node has stated that these modelling parameters can be safely recosted:{declared_text}."
        "Algorithms, number of reference rounds, target type, sample weights, time/Random/NoneOOT Slice,"
        "If you can map the above parameters in their entirety, it is.adjust,No, it's not.replan;"
        "Only add, delete, reschedule or switchWorkflow It's the one.replan."
        "Please draw in each control that the user has clearly named against the original sentence and the results of the first sessionparams,"
        "No omissions; expressly stating that (no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no"
        "The algorithm is not allowed in.recipes.TimeOOT Usesplit_config.oot_by_time,"
        "RandomOOT Usesplit_config.random_oot=true,NoneOOT Do not set these two."
        "sample_weight_candidates It is a read-only diagnosis and must not be used as an adjustment parameter:"
        "Revert to explicitly enable a columnsample_weight_col=\"Listing\","
        "Return when we clearly do not use weightssample_weight_col=\"\";"
        "If there are multiple candidates, but no clear choice, we must return.clarify."
        "Return when information is insufficientclarify,Do not guess listing or percentage.\n"
        'Please return strictly.JSON Object:{"action":"adjust|replan|clarify","params":{},'
        '"constraint":"","reason":"Chinese in one sentence","confidence":"high|medium|low",'
        '"explicit_authorization":false}.'
    )
    raw = client.complete(
        system_prompt=_SYSTEM,
        user_prompt=review_prompt,
        temperature=0.0,
        response_format={"type": "json_object"},
        json_schema=_ROUTE_SCHEMA,
        stream=False,
        caller="router",
        prompt_name=_GATE_INSTRUCTION_ROUTER_SYS_SPEC.name,
        prompt_version=_GATE_INSTRUCTION_ROUTER_SYS_SPEC.version,
    )
    candidate, ok = _parse_route(raw)
    if ok and candidate.get("action") == "adjust":
        candidate["params"] = normalize_adjust_params(candidate.get("params"))
        candidate = _canonicalize_sample_weight_selection(
            candidate,
            declared=declared,
        )
    allowed = declared & _MODELING_ADJUST_PARAM_NAMES
    if (
        ok
        and candidate.get("action") == "adjust"
        and candidate.get("params")
        and set(candidate["params"]) <= allowed
    ):
        return candidate
    if ok and candidate.get("action") in {"clarify", "replan"}:
        return candidate
    return fallback


def _canonicalize_sample_weight_selection(
    route: dict,
    *,
    declared: set[str],
) -> dict:
    """Translate one LLM-decided weight selection into the writable control.

    ``sample_weight_candidates`` is evidence produced by ``choose_modeling_spec``;
    it is not a user-editable selection. Some model replies nevertheless put a
    clearly selected single column there. The semantic ``adjust`` decision still
    comes from the LLM; this bounded canonicalizer only maps that one unambiguous
    value to ``sample_weight_col``. It never chooses among multiple candidates.
    """

    params = dict(route.get("params") or {})
    if "sample_weight_candidates" not in params:
        return route

    raw_candidates = params.pop("sample_weight_candidates")
    if "sample_weight_col" in params:
        return {**route, "params": params}

    candidates = (
        [
            value.strip()
            for value in raw_candidates
            if isinstance(value, str) and value.strip()
        ]
        if isinstance(raw_candidates, list)
        else []
    )
    candidates = list(dict.fromkeys(candidates))
    if "sample_weight_col" in declared and len(candidates) == 1:
        params["sample_weight_col"] = candidates[0]
        return {**route, "params": params}

    return {
        "action": "clarify",
        "params": {},
        "constraint": "",
        "reason": (
            "Multiple sample weight candidates are identified, and please select either a column or a non-use weight."
            if len(candidates) > 1
            else "No explicit sample weights are identified, please specify a column or indicate that the weights are not used."
        ),
        "confidence": "low",
        "explicit_authorization": False,
    }


def _recover_declared_selection_decision(
    client,
    *,
    route: dict,
    prompt: str,
    param_schema,
) -> dict:
    """Give a candidate-selection gate one bounded semantic consistency pass.

    A live modeling turn exposed a subtle failure mode: the user named the
    platform-starred experiment and explicitly asked to adopt it, but the first
    router pass called that a structural replan.  The trigger here is the
    *declared gate contract* (``selected_experiment_id``), not words in the
    utterance.  The LLM still decides what the complete sentence means; the
    driver later validates the returned id against the persisted candidate set
    before any governed confirmation is recorded.
    """

    if route.get("action") not in {"confirm", "adjust", "replan", "clarify"}:
        return route
    selection_spec = next(
        (
            item
            for item in list(param_schema or [])
            if isinstance(item, dict)
            and str(item.get("name") or "").strip() == "selected_experiment_id"
        ),
        None,
    )
    if selection_spec is None:
        return route

    allowed_values = _selection_enum_values(selection_spec)
    if not allowed_values:
        return {
            "action": "clarify",
            "params": {},
            "constraint": "",
            "reason": "There are currently no alternative candidate experiments.",
            "confidence": "low",
            "explicit_authorization": False,
        }
    if route.get("action") == "confirm":
        selected_id = str(
            (route.get("params") or {}).get("selected_experiment_id") or ""
        ).strip()
        if (
            selected_id in allowed_values
            and route.get("confidence") == "high"
            and route.get("explicit_authorization") is True
        ):
            canonical = dict(route)
            canonical["params"] = {"selected_experiment_id": selected_id}
            return canonical
        return {
            "action": "clarify",
            "params": {},
            "constraint": "",
            "reason": "Candidates for experimenting or for the use of mandates are not clear, and please select clearly from the current candidate.",
            "confidence": "low",
            "explicit_authorization": False,
        }

    first_pass = json.dumps(
        route,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    candidate_context = selection_spec.get("candidates")
    if not isinstance(candidate_context, list):
        candidate_context = [
            {
                "experiment_id": experiment_id,
                "recipe": "",
                "display_name": experiment_id,
                "recommended": experiment_id == selection_spec.get("current"),
            }
            for experiment_id in allowed_values
        ]
    candidate_json = json.dumps(
        candidate_context,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    review_prompt = (
        f"{prompt}\n\n"
        "[Candidature Node Review]\n"
        f"The first structured result:{first_pass}\n"
        f"Current CandidateJSON:{candidate_json}\n"
        "The current node has been compared with the candidate.selected_experiment_id It's...enum It's a platform."
        "The blog is a very interesting example of the way in which the election is actually presented and the choice is allowed.current is the current recommendation of the Platform;candidates And give it to me at the same time."
        "Every candidate.experiment_id,recipe,display_name andrecommended."
        "Please re-understand the whole user sentence: the user can use the experiment.id,recipe,Algorithms to show names or recommended relationships"
        "expressing selection;only by name orrecipe Only one match and the user explicitly authorizes the introduction or entry"
        "Returned on next stepsconfirm,"
        "params Keep Onlyselected_experiment_id,and set upconfidence=high,"
        "explicit_authorization=true;This is just the choice of the current decision node, not the modification.DAG."
        "If the same name orrecipe Multiple candidates, no single match, or users merely asking, evaluating"
        "Or discuss candidates without authorization, returnclarify."
        "Only real new, deleted, re-scheduled or switchedWorkflow ♪ I'm keeping it ♪replan."
        "No guess.enum Outsideid.\n"
        'Please return strictly.JSON Object:{"action":"confirm|replan|clarify","params":{},'
        '"constraint":"","reason":"Chinese in one sentence","confidence":"high|medium|low",'
        '"explicit_authorization":false}.'
    )
    raw = client.complete(
        system_prompt=_SYSTEM,
        user_prompt=review_prompt,
        temperature=0.0,
        response_format={"type": "json_object"},
        json_schema=_selection_route_schema(allowed_values),
        stream=False,
        caller="router",
        prompt_name=_GATE_INSTRUCTION_ROUTER_SYS_SPEC.name,
        prompt_version=_GATE_INSTRUCTION_ROUTER_SYS_SPEC.version,
    )
    candidate, ok = _parse_route(raw)
    if not ok:
        return route
    if candidate.get("action") == "confirm":
        selected_id = str(
            (candidate.get("params") or {}).get("selected_experiment_id") or ""
        ).strip()
        allowed = _selection_enum(selection_spec)
        if (
            selected_id
            and selected_id in allowed
            and candidate.get("confidence") == "high"
            and candidate.get("explicit_authorization") is True
            and set(candidate.get("params") or {}) == {"selected_experiment_id"}
        ):
            return candidate
        return {
            "action": "clarify",
            "params": {},
            "constraint": "",
            "reason": "Candidates for experimenting or for the use of mandates are not clear, and please select clearly from the current candidate.",
            "confidence": "low",
            "explicit_authorization": False,
        }
    if candidate.get("action") in {"clarify", "replan"}:
        return candidate
    return route


def _selection_enum(spec: dict) -> set[str]:
    return set(_selection_enum_values(spec))


def _selection_enum_values(spec: dict) -> list[str]:
    raw = spec.get("enum")
    if not isinstance(raw, list):
        bounds = spec.get("bounds")
        raw = bounds.get("enum") if isinstance(bounds, dict) else None
    values: list[str] = []
    for item in list(raw or []):
        value = str(item).strip()
        if value and value not in values:
            values.append(value)
    return values


def _selection_route_schema(allowed_values: list[str]) -> dict:
    """Constrain the one-shot candidate review to persisted experiment ids.

    Recipe ids and display names remain semantic evidence for the LLM, but the
    only executable value it can emit is one of the current gate's experiment
    ids. The driver performs the same persisted-candidate validation again
    before recording authorization.
    """

    return {
        "name": "candidate_selection_route",
        "strict": False,
        "schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["confirm", "replan", "clarify"],
                },
                "params": {
                    "type": "object",
                    "properties": {
                        "selected_experiment_id": {
                            "type": "string",
                            "enum": list(allowed_values),
                        }
                    },
                    "additionalProperties": False,
                },
                "constraint": {"type": "string"},
                "reason": {"type": "string"},
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                },
                "explicit_authorization": {"type": "boolean"},
            },
            "required": [
                "action",
                "params",
                "constraint",
                "reason",
                "confidence",
                "explicit_authorization",
            ],
            "additionalProperties": False,
        },
    }


_MAX_PARAM_SCHEMA_ITEMS = 12
_MAX_PARAM_VALUE_CHARS = 80
_MAX_PARAM_CANDIDATES = 12
_MAX_PARAM_CANDIDATE_CHARS = 2400


def _format(gate_context, instruction, tables, param_schema):
    lines = ["[Current Node]", str(gate_context or "")]
    for table in tables:
        lines.append(f"Table:{table.get('title', '')} Columns={table.get('columns')}")
    schema_lines = _format_param_schema(param_schema)
    if schema_lines:
        lines.append("[Arguable(Returnedparams The key can only be taken from here.)")
        lines.extend(schema_lines)
    lines.append("[User Commands]")
    lines.append(str(instruction or ""))
    return "\n".join(lines)


def _format_param_schema(param_schema) -> list[str]:
    """Render a length-bounded Parameter Name/Type/Current value [p](/Value range) summary line per
    adjustable parameter (AGT-5). Silently drops malformed entries rather than
    erroring — this is prompt context, not a validated control payload."""
    lines: list[str] = []
    for item in list(param_schema or [])[:_MAX_PARAM_SCHEMA_ITEMS]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        kind = str(item.get("type") or "").strip() or "unknown"
        current = _truncate(item.get("current"))
        bounds = item.get("bounds") if isinstance(item.get("bounds"), dict) else None
        line = f"- {name} (Type={kind}, Current value [p]={current})"
        if bounds:
            bounds_text = ", ".join(f"{k}={v}" for k, v in bounds.items())
            line += f" Value range: {bounds_text}"
        candidates = item.get("candidates")
        if isinstance(candidates, list) and candidates:
            candidate_text = json.dumps(
                candidates[:_MAX_PARAM_CANDIDATES],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if len(candidate_text) > _MAX_PARAM_CANDIDATE_CHARS:
                candidate_text = (
                    candidate_text[:_MAX_PARAM_CANDIDATE_CHARS] + "…"
                )
            line += f" Candidate Context: {candidate_text}"
        lines.append(line)
    return lines


def _truncate(value) -> str:
    text = str(value if value is not None else "-")
    if len(text) > _MAX_PARAM_VALUE_CHARS:
        return text[:_MAX_PARAM_VALUE_CHARS] + "…"
    return text


def parse_route(raw):
    """Normalize the LLM reply; default to a safe clarify on junk or empty adjust."""
    route, _ok = _parse_route(raw)
    return route


def _parse_route(raw, *, strict_contract=False) -> tuple[dict, bool]:
    if strict_contract:
        data, error = _load_strict_route_object(raw)
    else:
        data, error = load_json_object(raw)
    if data is None:
        return {
            "action": "clarify",
            "params": {},
            "constraint": "",
            "reason": "Could not close temporary folder: %s",
            "confidence": "low",
            "explicit_authorization": False,
        }, False
    if strict_contract and (
        set(data) != set(_ROUTE_FIELDS)
        or not isinstance(data.get("action"), str)
        or data.get("action") not in _ACTIONS
        or not isinstance(data.get("params"), dict)
        or not isinstance(data.get("constraint"), str)
        or not isinstance(data.get("reason"), str)
        or not isinstance(data.get("confidence"), str)
        or data.get("confidence") not in {"high", "medium", "low"}
        or type(data.get("explicit_authorization")) is not bool
    ):
        return {
            "action": "clarify",
            "params": {},
            "constraint": "",
            "reason": "Command route return structure is incomplete and has been processed as unauthorized.",
            "confidence": "low",
            "explicit_authorization": False,
        }, False
    action = str(data.get("action") or "").strip().lower()
    if action not in _ACTIONS:
        action = "clarify"
    params = data.get("params") if isinstance(data.get("params"), dict) else {}
    constraint = str(data.get("constraint") or "").strip()
    reason = str(data.get("reason") or "").strip()
    confidence = str(data.get("confidence") or "").strip().lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"
    explicit_authorization = data.get("explicit_authorization") is True
    if action == "confirm" and rejects_positive_decision(reason):
        return {
            "action": "clarify",
            "params": {},
            "constraint": "",
            "reason": "The model action contradicts the rationale and the user is requested to confirm whether to continue.",
            "confidence": "low",
            "explicit_authorization": False,
        }, False
    # An "adjust" with no extractable parameters is not actionable → clarify.
    if action == "adjust" and not params:
        action = "clarify"
        reason = reason or "No parameters are identified for adjustment, please specify the parameter name and the value to be taken."
    return {
        "action": action,
        "params": params,
        "constraint": constraint,
        "reason": reason,
        "confidence": confidence,
        "explicit_authorization": explicit_authorization,
    }, error is None


def _load_strict_route_object(raw) -> tuple[dict | None, str | None]:
    """Load one exact JSON object and reject wrappers or duplicate keys."""

    if not isinstance(raw, str):
        return None, "reply is not text"

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    try:
        data = json.loads(raw.strip(), object_pairs_hook=unique_object)
    except (TypeError, ValueError) as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "JSON value is not an object"
    return data, None


__all__ = ["route_instruction", "parse_route"]
