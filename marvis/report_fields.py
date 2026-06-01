from __future__ import annotations

from dataclasses import dataclass, asdict

from marvis.domain import TaskRecord
from marvis.validation_report_copy import seed_report_values


@dataclass(frozen=True)
class ReportField:
    key: str
    label: str
    stage: str
    multiline: bool = False


REPORT_FIELDS: tuple[ReportField, ...] = (
    ReportField("TEXT:report_title", "Title of report", "cover"),
    ReportField("TEXT:drafter", "Author", "cover"),
    ReportField("TEXT:draft_date", "Date of writing", "cover"),
    ReportField("TEXT:revision_version", "Revision", "cover"),
    ReportField("TEXT:revision_date", "Revision date", "cover"),
    ReportField("TEXT:revision_author", "Revision", "cover"),
    ReportField("TEXT:revision_description", "Revised Notes", "cover", True),
    ReportField("TEXT:model_overview", "Summary of the model", "before", True),
    ReportField("TEXT:model_scope", "Scope of application", "before", True),
    ReportField("TEXT:bad_sample_definition", "Bad sample definition", "before"),
    ReportField("TEXT:good_sample_definition", "Good sample definition", "before"),
    ReportField("TEXT:model_training_description", "Model training notes", "during", True),
    ReportField("TEXT:pressure_recommendation_summary", "Pressure test recommendations", "after", True),
    ReportField("TEXT:pressure_recommendation_action", "Pressure risk disposal", "after", True),
    ReportField("TEXT:pressure_recommendation_monitoring", "Pressure monitoring advice", "after", True),
    ReportField("TEXT:pressure_recommendation_high_impact", "High impact stress recommendations", "after", True),
    ReportField("TEXT:pressure_recommendation_medium_impact", "..in the middle of the pressure-impact proposal.", "after", True),
    ReportField("TEXT:pressure_recommendation_low_impact", "Low impact stress recommendations", "after", True),
    ReportField("TEXT:final_validation_conclusion", "Final validation conclusion", "after", True),
)


def default_report_values(
    model_name: str,
    model_version: str,
    validator: str,
    algorithm: str = "",
) -> dict[str, str]:
    values = seed_report_values(model_name, model_version, validator, algorithm)
    values.update({
        "TEXT:pressure_recommendation_summary": "The results of the pressure test and risk tips are to be supplemented.",
        "TEXT:pressure_impact_recommendation": "The results of the pressure test and risk tips are to be supplemented.",
        "TEXT:pressure_recommendation_action": "It is proposed to develop differentiated access and monitoring strategies in conjunction with stress test performance.",
        "TEXT:pressure_recommendation_monitoring": "It is recommended that the model be continuously monitored after it has been online for differentiation, stability and key characterization drift.",
        "TEXT:pressure_recommendation_high_impact": "Yes.KS orPSI Largely changing feature categories, it is recommended that the variable dependence and strategy bottoming options be reviewed.",
        "TEXT:pressure_recommendation_medium_impact": "For the characterization categories of medium impact, it is proposed to include a focus on monitoring and setting early warning thresholds after the line is in place.",
        "TEXT:pressure_recommendation_low_impact": "For the less influential feature categories, it is recommended that regular monitoring and regular review of stability be maintained.",
        "TEXT:final_validation_conclusion": "Final validation conclusions to be added.",
    })
    return values


def report_field_payload(
    task: TaskRecord,
    values: dict[str, str],
    revision: int,
    metric_values: dict[str, str] | None = None,
    metric_table_sections: list[dict] | None = None,
) -> dict:
    display_defaults = default_report_values(
        task.model_name,
        task.model_version,
        task.validator,
        task.algorithm,
    )
    stored_values = dict(values)
    text_values = dict(display_defaults)
    text_values.update(stored_values)
    return {
        "fields": [asdict(field) for field in REPORT_FIELDS],
        "text_values": text_values,
        "stored_values": stored_values,
        "display_defaults": display_defaults,
        "revision": revision,
        "metric_values": metric_values or {},
        "metric_table_sections": metric_table_sections or [],
    }
