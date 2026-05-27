import ast
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from marvis.notebook_io import read_notebook


_HEADING_RE = re.compile(r"^\s{0,3}(#{1,3})\s+(.+?)\s*$")
_SYSTEM_STEP_TITLES = {
    "head": ("system-head", "Initialization of the platform"),
    "tail": ("system-tail", "Platform compact inspection"),
    "repro-pmml": ("system-repro-pmml", "PMML Score"),
    "repro-compare": ("system-repro-compare", "Consistency of scores"),
    "metrics-prepare": ("system-metrics-prepare", "Indicator data preparation"),
    "metrics-score": ("system-metrics-score", "RMC_SCORE_FN Full score."),
    "metrics-basic": ("system-metrics-basic", "Overview of samples and variables"),
    "metrics-ks": ("system-metrics-ks", "KS Calculate"),
    "metrics-psi": ("system-metrics-psi", "PSI Calculate"),
    "metrics-binning": ("system-metrics-binning", "Box Count"),
    "metrics-effectiveness": ("system-metrics-effectiveness", "KS / PSI / Box Count"),
    "metrics-stress": ("system-metrics-stress", "Pressure test"),
    "metrics-output": ("system-metrics-output", "Writing indicator products"),
}


@dataclass(frozen=True)
class NotebookStep:
    id: str
    title: str
    cell_indexes: list[int] = field(default_factory=list)
    source_previews: list[str] = field(default_factory=list)
    system: bool = False


@dataclass(frozen=True)
class NotebookStepPlan:
    steps: list[NotebookStep]
    cell_to_step: dict[int, str]


def notebook_step_plan(notebook: Any) -> NotebookStepPlan:
    steps_by_id: dict[str, NotebookStep] = {}
    cell_to_step: dict[int, str] = {}
    current_step_id = "notebook-init"
    current_title = "Notebook Initialize"
    has_headings = _has_markdown_headings(notebook)

    for cell_index, cell in enumerate(notebook.cells):
        system_kind = cell.get("metadata", {}).get("marvis")
        if system_kind in _SYSTEM_STEP_TITLES and cell.cell_type == "code":
            step_id, title = _SYSTEM_STEP_TITLES[system_kind]
            _append_cell(
                steps_by_id,
                cell_to_step,
                step_id=step_id,
                title=title,
                cell_index=cell_index,
                source=cell.source,
                system=True,
            )
            continue

        if cell.cell_type == "markdown":
            heading = _first_heading(str(cell.source))
            if heading:
                current_title = heading
                current_step_id = f"step-{cell_index + 1}"
            continue

        if cell.cell_type != "code":
            continue
        if not has_headings:
            current_step_id = f"cell-{cell_index + 1}"
            current_title = _infer_code_cell_title(str(cell.source))
        _append_cell(
            steps_by_id,
            cell_to_step,
            step_id=current_step_id,
            title=current_title,
            cell_index=cell_index,
            source=cell.source,
            system=False,
        )

    return NotebookStepPlan(steps=list(steps_by_id.values()), cell_to_step=cell_to_step)


def notebook_step_preview(notebook_path: Path) -> list[dict]:
    notebook = read_notebook(notebook_path, as_version=4)
    plan = notebook_step_plan(notebook)
    return [
        {
            "id": step.id,
            "step_order": order,
            "title": step.title,
            "status": "pending",
            "cell_count": len(step.cell_indexes),
            "cell_indexes": step.cell_indexes,
            "source_previews": step.source_previews,
            "system": step.system,
        }
        for order, step in enumerate(plan.steps, start=1)
    ]


def _first_heading(source: str) -> str | None:
    for line in source.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            return match.group(2).strip()
    return None


def _has_markdown_headings(notebook: Any) -> bool:
    return any(
        cell.cell_type == "markdown" and _first_heading(str(cell.source))
        for cell in notebook.cells
    )


def _infer_code_cell_title(source: str) -> str:
    compact = _compact_code(source)
    call_names = _call_names(source)
    if not compact:
        return "Execute Code"
    if _contains_all(compact, ("rmc_sample_df", "rmc_target_col")) or "rmc_score_fn" in compact:
        return "Notebook Contract Configuration"
    if _imports_only(source):
        return "Import Dependence"
    if _calls_pmml_export(call_names):
        return "PMML Export"
    if _contains_any(
        compact,
        (
            "readcsv",
            "readexcel",
            "readparquet",
            "readfeather",
            "readdata",
            "loaddata",
            "loadsample",
            "readtable",
        ),
    ):
        return "Read Data"
    if _contains_any(compact, ("merge(", ".merge(", "join(", ".join(", "concat(", "leftjoin", "innerjoin")):
        return "Data Collapse"
    if _contains_any(
        compact,
        (
            "columns.tolist",
            "columns.tolist()",
            "columns.values",
            "vars1.remove",
            "feature_columns",
            "selectcolumns",
            "select_columns",
        ),
    ):
        return "Feature Filter"
    if _contains_any(
        compact,
        (
            "train_test_split",
            "traintestsplit",
            "split_col",
            "split_tag",
            "sample_split",
            "splitdata",
        ),
    ):
        return "Sample splitting"
    train_like = _contains_any(
        compact,
        (
            "fitmodel",
            "trainmodel",
            "xgbclassifier",
            "lgbmclassifier",
            "catboostclassifier",
            "logisticregression",
            "randomforestclassifier",
        ),
    ) or _has_call_suffix(call_names, ("fit",))
    score_like = _contains_any(
        compact,
        (
            "predictproba",
            "predict_proba",
            "scorefn",
            "score_fn",
            "rmc_score_fn",
            "modelscore",
            "model_score",
        ),
    ) or _has_call_suffix(call_names, ("predict", "predict_proba", "score"))
    metric_like = _contains_any(
        compact,
        (
            "rocaucscore",
            "auc",
            "ks",
            "psi",
            "confusionmatrix",
            "classificationreport",
            "metric",
            "evaluate",
            "validation",
        ),
    )
    if train_like and score_like:
        return "Model training and scoring"
    if train_like:
        return "Model training"
    if "pmml" in compact and _contains_any(compact, ("predict", "score", "evaluate")):
        return "PMML Score"
    if score_like and metric_like:
        return "Model scores and indicator calculations"
    if score_like:
        return "Model score"
    if _contains_any(
        compact,
        (
            "fillna",
            "dropna",
            "dropduplicates",
            "astype",
            "clip(",
            "replace(",
            "getdummies",
            "onehot",
            "standardscaler",
            "minmaxscaler",
            "woe",
            "binning",
            "chimerge",
            "preprocess",
            "cleandata",
        ),
    ):
        return "Data cleansing and pre-processing"
    if _contains_any(
        compact,
        (
            "featureimportance",
            "feature_importance",
            "featureimportances",
            "feature_importances",
            "varimportance",
            "shap",
            "selectfeatures",
            "select_features",
            "ivvalue",
            "informationvalue",
        ),
    ):
        return "Characteristic analysis"
    if _contains_any(
        compact,
        ("tocsv", "toexcel", "toparquet", "tojson", "pickle.dump", "joblib.dump", "json.dump"),
    ):
        return "Save Results"
    if metric_like:
        return "Calculation of indicators"
    if _contains_any(compact, ("savefig", ".plot(", "plt.", "seaborn", "matplotlib")):
        return "Chart Drawing"

    first_call = _first_call_name(source)
    if first_call:
        return f"Implementation{first_call}"
    first_line = _source_preview(source, limit=36)
    return f"Executing code:{first_line}" if first_line else "Execute Code"


def _compact_code(source: str) -> str:
    return re.sub(r"[\W_]+", "", source.casefold(), flags=re.UNICODE)


def _contains_any(source: str, needles: tuple[str, ...]) -> bool:
    return any(_compact_code(needle) in source for needle in needles)


def _contains_all(source: str, needles: tuple[str, ...]) -> bool:
    return all(_compact_code(needle) in source for needle in needles)


def _imports_only(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    body = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.Expr)
            and isinstance(getattr(node, "value", None), ast.Constant)
            and isinstance(node.value.value, str)
        )
    ]
    return bool(body) and all(isinstance(node, (ast.Import, ast.ImportFrom)) for node in body)


def _first_call_name(source: str) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    finder = _FirstCallName()
    finder.visit(tree)
    return finder.name


def _call_names(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    collector = _CallNameCollector()
    collector.visit(tree)
    return collector.names


def _has_call_suffix(call_names: set[str], suffixes: tuple[str, ...]) -> bool:
    normalized_suffixes = {suffix.casefold() for suffix in suffixes}
    for name in call_names:
        parts = [part.casefold() for part in name.split(".") if part]
        if parts and parts[-1] in normalized_suffixes:
            return True
    return False


def _calls_pmml_export(call_names: set[str]) -> bool:
    return _has_call_suffix(
        call_names,
        (
            "sklearn2pmml",
            "to_pmml",
            "topmml",
            "skl_to_pmml",
            "export_pmml",
            "save_pmml",
        ),
    )


class _FirstCallName(ast.NodeVisitor):
    def __init__(self) -> None:
        self.name: str | None = None

    def visit_Call(self, node: ast.Call) -> Any:
        if self.name is None:
            self.name = _call_name(node.func)
        if self.name is None:
            self.generic_visit(node)


class _CallNameCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Call(self, node: ast.Call) -> Any:
        name = _call_name(node.func)
        if name:
            self.names.add(name)
        self.generic_visit(node)


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _call_name(node.value)
        return f"{owner}.{node.attr}" if owner else node.attr
    return None


def _append_cell(
    steps_by_id: dict[str, NotebookStep],
    cell_to_step: dict[int, str],
    *,
    step_id: str,
    title: str,
    cell_index: int,
    source: str,
    system: bool,
) -> None:
    existing = steps_by_id.get(step_id)
    preview = _source_preview(source)
    if existing is None:
        steps_by_id[step_id] = NotebookStep(
            id=step_id,
            title=title,
            cell_indexes=[cell_index],
            source_previews=[preview],
            system=system,
        )
    elif system and existing.system:
        for existing_cell_index in existing.cell_indexes:
            cell_to_step.pop(existing_cell_index, None)
        steps_by_id[step_id] = NotebookStep(
            id=existing.id,
            title=existing.title,
            cell_indexes=[cell_index],
            source_previews=[preview],
            system=existing.system,
        )
    else:
        steps_by_id[step_id] = NotebookStep(
            id=existing.id,
            title=existing.title,
            cell_indexes=[*existing.cell_indexes, cell_index],
            source_previews=[*existing.source_previews, preview],
            system=existing.system,
        )
    cell_to_step[cell_index] = step_id


def _source_preview(source: str, limit: int = 120) -> str:
    first_line = next((line.strip() for line in source.splitlines() if line.strip()), "")
    return first_line[:limit]
