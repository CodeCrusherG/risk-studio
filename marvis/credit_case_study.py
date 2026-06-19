"""Reproducible public credit-default validation; no synthetic outcomes or dates."""

from __future__ import annotations

import hashlib
import io
import json
import platform
import shutil
import ssl
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

import certifi
import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.special import logit
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from marvis.feature.metrics import feature_auc
from marvis.validation.binning import (
    bin_distribution, compute_ks, compute_psi, equal_frequency_bin_edges,
)

SEED = 20261004
SOURCE_URL = "https://archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip"
SOURCE_SHA256 = "56c885f84457f6680f8438f02bfcdac9579323d8a94465ee5f26e32baa727602"
LANDING_URL = "https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients"
TARGET = "default payment next month"
STATUS_FEATURES = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
AMOUNT_FEATURES = ["LIMIT_BAL"] + [f"BILL_AMT{i}" for i in range(1, 7)] + [f"PAY_AMT{i}" for i in range(1, 7)]
FEATURES = AMOUNT_FEATURES + STATUS_FEATURES
PARTITIONS = ("development", "calibration", "holdout")
REFERENCE_MODEL = "calibrated_gradient_boosting"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_source(cache: Path, *, offline: bool = False) -> tuple[pd.DataFrame, dict]:
    """Fetch only the fixed UCI URL and reject changed or corrupted bytes."""
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / "source.zip"
    manifest_path = cache / "source_manifest.json"
    if not archive.exists():
        if offline:
            raise FileNotFoundError("No cached UCI source; run once without --offline.")
        req = Request(SOURCE_URL, headers={"User-Agent": "RiskStudio-public-research/1.0"})
        context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(req, timeout=60, context=context) as response:
            body = response.read(10_000_001)
        if len(body) > 10_000_000 or hashlib.sha256(body).hexdigest() != SOURCE_SHA256:
            raise ValueError("UCI source checksum changed; review source before updating the pin.")
        archive.write_bytes(body)
        write_json(manifest_path, {
            "retrieved_at": datetime.now(UTC).isoformat(),
            "archive_sha256": SOURCE_SHA256,
        })
    if sha256(archive) != SOURCE_SHA256:
        raise ValueError("UCI source checksum mismatch; cached archive is not the reviewed source.")
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    # A missing retrieval record is reported as unknown, never replaced with today's date.
    manifest.update({
        "url": SOURCE_URL, "landing_page": LANDING_URL,
        "archive_sha256": SOURCE_SHA256, "archive_bytes": archive.stat().st_size,
        "retrieved_at": manifest.get("retrieved_at"),
        "citation": "Yeh, I. (2009). Default of Credit Card Clients [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C55S3H.",
        "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "source_period": "Payment and bill histories April–September 2005; observed next-month default flag",
        "data_type": "Observed historical anonymized customer records; probabilities are model estimates.",
    })
    with zipfile.ZipFile(archive) as zf:
        workbook = zf.read("default of credit card clients.xls")
    manifest["workbook_sha256"] = hashlib.sha256(workbook).hexdigest()
    df = pd.read_excel(io.BytesIO(workbook), header=1)
    if len(df) != 30_000 or df["ID"].nunique() != 30_000 or set(df[TARGET].unique()) != {0, 1}:
        raise ValueError("Unexpected UCI row count, identifier, or binary target contract.")
    if df.isna().any().any() or not np.isfinite(df.select_dtypes("number").values).all():
        raise ValueError("Unexpected missing or non-finite source data.")
    write_json(manifest_path, manifest)
    return df, manifest


def partition_rows(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Keep identical model predictor profiles together, including conflicting labels."""
    groups = pd.util.hash_pandas_object(df[FEATURES], index=False).to_numpy()
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    folds = np.empty(len(df), dtype=int)
    for fold, (_, rows) in enumerate(splitter.split(df[FEATURES], df[TARGET], groups)):
        folds[rows] = fold
    partitions = np.where(folds == 0, "holdout", np.where(folds == 1, "calibration", "development"))
    group_sets = [set(groups[partitions == name]) for name in PARTITIONS]
    if any(group_sets[i] & group_sets[j] for i in range(3) for j in range(i + 1, 3)):
        raise AssertionError("Predictor group leakage between partitions")
    return partitions, groups


def reliability(y: np.ndarray, p: np.ndarray) -> list[dict]:
    """Fixed probability bins and Wilson intervals; empty bins are omitted."""
    assignments = np.minimum((p * 10).astype(int), 9)
    rows = []
    for band in range(10):
        mask = assignments == band
        n = int(mask.sum())
        if not n:
            continue
        obs = float(y[mask].mean())
        z = 1.959963984540054
        denom = 1 + z**2 / n
        center = (obs + z**2 / (2 * n)) / denom
        half = z * np.sqrt(obs * (1 - obs) / n + z**2 / (4 * n**2)) / denom
        rows.append({"lower": band / 10, "upper": (band + 1) / 10, "count": n,
                     "defaults": int(y[mask].sum()), "mean_predicted_pd": float(p[mask].mean()),
                     "observed_default_rate": obs, "wilson_95_low": float(center - half),
                     "wilson_95_high": float(center + half)})
    return rows


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    bins = reliability(y, p)
    auc = feature_auc(p, y)
    fpr, tpr, _ = roc_curve(y, p)
    # Independent reconciliation of the platform kernels, including score ties.
    if not np.isclose(auc, roc_auc_score(y, p), atol=1e-12):
        raise AssertionError("Platform AUC differs from independent sklearn result")
    ks = compute_ks(p, y)
    if not np.isclose(ks, np.max(np.abs(tpr - fpr)), atol=1e-12):
        raise AssertionError("Platform KS differs from ROC reference")
    return {
        "rows": int(len(y)), "defaults": int(y.sum()), "default_rate": float(y.mean()),
        "auc": float(auc), "ks": float(ks), "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])), "mean_predicted_pd": float(p.mean()),
        "expected_defaults": float(p.sum()), "observed_expected_ratio": float(y.sum() / p.sum()),
        "ece_10_fixed_bins": float(sum(b["count"] * abs(b["mean_predicted_pd"] - b["observed_default_rate"]) for b in bins) / len(y)),
        "reliability": bins,
    }


def score_psi(reference: np.ndarray, comparison: np.ndarray) -> dict:
    edges = equal_frequency_bin_edges(reference, 10)
    expected = bin_distribution(reference, edges)
    actual = bin_distribution(comparison, edges)
    return {"psi": float(compute_psi(expected, actual)),
            "edges": [float(x) if np.isfinite(x) else ("-inf" if x < 0 else "inf") for x in edges],
            "reference_distribution": expected.tolist(), "comparison_distribution": actual.tolist()}


def bootstrap_intervals(y: np.ndarray, p: np.ndarray, baseline: np.ndarray, *, repetitions: int = 300) -> dict:
    """Fixed-label-count bootstrap; intervals condition on this historical cohort."""
    rng = np.random.default_rng(SEED)
    good, bad = np.flatnonzero(y == 0), np.flatnonzero(y == 1)
    draws = {key: [] for key in ("auc", "ks", "brier", "auc_minus_logistic", "brier_minus_logistic")}
    for _ in range(repetitions):
        ix = np.r_[rng.choice(good, len(good)), rng.choice(bad, len(bad))]
        auc = feature_auc(p[ix], y[ix])
        brier = float(np.mean((p[ix] - y[ix])**2))
        for key, value in {"auc": auc, "ks": compute_ks(p[ix], y[ix]), "brier": brier,
                           "auc_minus_logistic": auc - feature_auc(baseline[ix], y[ix]),
                           "brier_minus_logistic": brier - np.mean((baseline[ix] - y[ix])**2)}.items():
            draws[key].append(float(value))
    return {"method": "Stratified percentile bootstrap; fixed class counts; conditional on fitted models and cohort",
            "repetitions": repetitions, "seed": SEED, "confidence": 0.95,
            "intervals": {key: {"low": float(np.quantile(values, .025)), "high": float(np.quantile(values, .975))} for key, values in draws.items()}}


def make_figures(report: dict, predictions: pd.DataFrame, destination: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    holdout = predictions[predictions.partition == "holdout"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for key, label in (("logistic", "Logistic baseline"), (REFERENCE_MODEL, "Calibrated boosting")):
        fpr, tpr, _ = roc_curve(holdout.observed_default, holdout[key])
        axes[0].plot(fpr, tpr, label=f"{label} ({report['models'][key]['holdout']['auc']:.3f})")
        bins = report["models"][key]["holdout"]["reliability"]
        axes[1].plot([b["mean_predicted_pd"] for b in bins], [b["observed_default_rate"] for b in bins], "o-", label=label)
    axes[0].plot([0, 1], [0, 1], "--", color="gray")
    axes[0].set(xlabel="False positive rate", ylabel="True positive rate", title="Untouched holdout: ROC")
    axes[1].plot([0, 1], [0, 1], "--", color="gray")
    axes[1].set(xlabel="Mean predicted PD", ylabel="Observed default fraction", title="Calibration: fixed probability bins")
    for partition in PARTITIONS:
        axes[2].hist(predictions.loc[predictions.partition == partition, REFERENCE_MODEL], bins=np.linspace(0, 1, 21), density=True, histtype="step", label=partition)
    axes[2].set(xlabel="Estimated next-month PD", ylabel="Density", title="Same-cohort score distributions")
    for ax in axes:
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    fig.suptitle("UCI observed credit defaults · historical research validation · no OOT claim")
    fig.tight_layout()
    fig.savefig(destination / "validation.png", dpi=150, metadata={"Software": "Risk Studio"})
    plt.close(fig)


def render_markdown(report: dict) -> str:
    holdout = report["models"][REFERENCE_MODEL]["holdout"]
    lines = ["# Observed credit-default model validation", "",
             "Historical public-data research case study. Model review status: **research only; no production approval**.", "",
             f"Source: [{report['source']['citation']}]({LANDING_URL}) · CC BY 4.0.", "",
             f"{report['data_quality']['rows']:,} observed records; {report['data_quality']['defaults']:,} observed defaults. Payment histories cover April–September 2005. Default means the publisher's next-month binary payment-default flag, not a harmonized regulatory default definition.", "",
             "## Experiment design", "", report["protocol"]["split_description"], "",
             "Fixed logistic regression baseline and fixed histogram gradient boosting challenger. Logistic preprocessing and both estimators are fitted on development only. A sigmoid of the booster's log-odds is fitted on calibration only. The calibrated challenger is designated before holdout evaluation; no holdout tuning or champion selection occurs.", "",
             "ID and SEX, EDUCATION, MARRIAGE, AGE are excluded from the 19 model predictors. Removing demographics alone does not establish fairness. Exact matching predictor profiles are assigned to the same partition, including conflicting observed outcomes.", "",
             "| Partition | Records | Defaults | Observed default rate |", "|---|---:|---:|---:|"]
    for key, values in report["partitions"].items():
        lines.append(f"| {key} | {values['rows']:,} | {values['defaults']:,} | {values['default_rate']:.2%} |")
    lines += ["", "## Holdout validation", "", "| Model | AUC | KS | Brier | Log loss | Mean PD | O/E |", "|---|---:|---:|---:|---:|---:|---:|"]
    for key, model in report["models"].items():
        m = model["holdout"]
        lines.append(f"| {key} | {m['auc']:.5f} | {m['ks']:.5f} | {m['brier']:.5f} | {m['log_loss']:.5f} | {m['mean_predicted_pd']:.2%} | {m['observed_expected_ratio']:.4f} |")
    lines += ["", "Brier and log loss are proper probability scores that combine calibration and discrimination; the reliability table assesses calibration directly. O/E is observed defaults divided by summed estimated PD. Fixed 10-point probability bins include Wilson intervals in the JSON report.", "",
              "![Held-out ROC, calibration and score distribution](validation.png)", "",
              "### Uncertainty", "", report["bootstrap"]["method"] + "; 300 resamples, 95% intervals.", ""]
    for key, interval in report["bootstrap"]["intervals"].items():
        lines.append(f"- {key}: [{interval['low']:.5f}, {interval['high']:.5f}]")
    lines += ["", "## Stability and review findings", "",
              f"Score PSI, development to holdout: {report['stability']['score']['holdout']['psi']:.6f}. Bins use development quantiles and platform PSI smoothing 1e-6. These partitions share one historical cohort; this is sample stability, **not evidence of time drift or out-of-time performance**.", ""]
    for finding in report["governance"]["findings"]:
        lines.append(f"- **{finding['severity']} — {finding['finding']}** {finding['action']}")
    lines += ["", "## Interpretation boundaries", ""] + [f"- {s}" for s in report["limitations"]]
    lines += ["", "## Reproduce and reconcile", "", "```bash", ".venv/bin/python scripts/run_public_credit_case_study.py --offline", ".venv/bin/python -m pytest tests/test_credit_case_study.py", "```", "",
              "The CSV preserves source ID, observed outcome, fixed partition, predictor-group hash, and each estimated PD. `source_manifest.json` pins downloaded and workbook bytes. `artifact_manifest.json` hashes source code, inputs, predictions, charts and reports. `report.json` records versions, parameters, checks, bootstrap and model review findings. These are reproducibility checks, not an independent reviewer sign-off.", "",
              f"Holdout predicted defaults: {holdout['expected_defaults']:.2f}; observed defaults: {holdout['defaults']}.", ""]
    return "\n".join(lines)


@threadpool_limits.wrap(limits=1)
def run_case_study(root: Path, *, offline: bool = False, workspace: Path | None = None, output: Path | None = None) -> dict:
    destination = output or root / "evidence" / "credit-default"
    destination.mkdir(parents=True, exist_ok=True)
    df, source = load_source(root / "data" / "public" / "uci_credit_default", offline=offline)
    partitions, groups = partition_rows(df)
    x, y = df[FEATURES], df[TARGET].to_numpy(dtype=int)
    train, cal = partitions == "development", partitions == "calibration"
    numeric = make_pipeline(StandardScaler())
    preprocessor = ColumnTransformer([("amounts", numeric, AMOUNT_FEATURES),
                                      ("repayment_status", OneHotEncoder(handle_unknown="ignore", sparse_output=False), STATUS_FEATURES)])
    baseline = make_pipeline(preprocessor, LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000, random_state=SEED))
    booster_params = {"max_iter": 150, "max_leaf_nodes": 15, "learning_rate": .08,
                      "l2_regularization": 10.0, "early_stopping": False, "random_state": SEED}
    challenger = HistGradientBoostingClassifier(**booster_params)
    baseline.fit(x[train], y[train])
    challenger.fit(x[train], y[train])
    raw_pd = challenger.predict_proba(x)[:, 1]
    raw_logits = logit(np.clip(raw_pd, 1e-8, 1 - 1e-8)).reshape(-1, 1)
    calibrator = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000, random_state=SEED)
    calibrator.fit(raw_logits[cal], y[cal])
    probabilities = {"constant_development_rate": np.repeat(y[train].mean(), len(y)),
                     "logistic": baseline.predict_proba(x)[:, 1],
                     "gradient_boosting": raw_pd,
                     REFERENCE_MODEL: calibrator.predict_proba(raw_logits)[:, 1]}
    # Define ties before both metric computation and portable decimal CSV export.
    # Full binary precision can spuriously separate equal-profile scores on reload.
    probabilities = {name: np.round(p, 12) for name, p in probabilities.items()}
    results = {name: {part: metrics(y[partitions == part], p[partitions == part]) for part in PARTITIONS}
               for name, p in probabilities.items()}
    predictions = pd.DataFrame({"source_id": df.ID, "partition": partitions, "predictor_group": groups.astype(str),
                                "observed_default": y, **probabilities})
    predictions.to_csv(destination / "predictions.csv", index=False, float_format="%.12f")
    # Preserve every observed source column for reuse in the workbench; no invented dates.
    df.assign(partition=partitions).to_csv(destination / "observed_clients.csv", index=False)
    pd.DataFrame({"feature": FEATURES, "kind": ["repayment category" if f in STATUS_FEATURES else "observed NT dollar amount" for f in FEATURES]}).to_csv(destination / "feature_dictionary.csv", index=False)
    hold = partitions == "holdout"
    calibrated = probabilities[REFERENCE_MODEL]
    stability = {"interpretation": "Same-cohort split stability only; no dates fabricated, no time-drift claim.",
                 "score": {part: score_psi(calibrated[train], calibrated[partitions == part]) for part in ("calibration", "holdout")},
                 "features": {f: score_psi(x.loc[train, f].to_numpy(), x.loc[hold, f].to_numpy()) for f in FEATURES}}
    payoff = STATUS_FEATURES
    undefined = {f: {str(k): int(v) for k, v in df[f].value_counts().items() if k in (-2, 0)} for f in payoff}
    source["transformations"] = ["Read second Excel row as column headers", "Exclude identifier and demographics from modeling", "Retain original repayment codes, including undocumented -2 and 0, as distinct categories in logistic model", "Derive grouped random partitions and estimated PD; no dates or labels synthesized"]
    write_json(destination / "source_manifest.json", source)
    h = results[REFERENCE_MODEL]["holdout"]
    findings = [
        {"severity": "BLOCKER", "finding": "One historical cohort cannot support out-of-time approval.", "action": "Acquire newer, dated cohorts and validate temporal and geographic transportability before any use."},
        {"severity": "REVIEW", "finding": "Repayment statuses -2 and 0 occur outside UCI's described scale.", "action": "Preserved as source values; seek publisher/business definitions before operational adoption."},
        {"severity": "REVIEW", "finding": "No independent reviewer approval or policy threshold.", "action": "Record independent model challenge, fairness review, and explicit decision authority before approval."},
        {"severity": "INFO", "finding": f"Holdout observed/expected defaults = {h['observed_expected_ratio']:.3f}.", "action": "Review reliability bins and uncertainty; training and calibration metrics are fitted diagnostics."},
        {"severity": "REVIEW", "finding": f"Calibration changes holdout Brier by {h['brier'] - results['gradient_boosting']['holdout']['brier']:+.6f} versus the raw booster.", "action": "A positive change is worse. Calibration is not assumed to improve holdout performance; preserve both results for challenge."},
    ]
    report = {
        "schema_version": 1, "case_study_id": "uci-credit-default-v1", "title": "Observed credit-default validation",
        "generated_at": datetime.now(UTC).isoformat(), "reference_model": REFERENCE_MODEL, "source": source,
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__, "scikit_learn": sklearn.__version__, "compute_threads": 1},
        "protocol": {"seed": SEED, "split_description": "Deterministic shuffled 5-fold stratified group split: three development folds, one calibration fold, one untouched holdout fold. Equal 19-predictor profiles share a group. Fold sizes are approximate 60/20/20, not dates or vintages.",
                     "split_algorithm": "StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=20261004)",
                     "features": FEATURES, "excluded": ["ID", "SEX", "EDUCATION", "MARRIAGE", "AGE", TARGET],
                     "logistic": {"C": 1.0, "solver": "lbfgs", "max_iter": 2000, "preprocessing": "Development-only StandardScaler for amounts; OneHotEncoder for repayment codes"},
                     "gradient_boosting": booster_params, "calibration": {"method": "sigmoid on clipped model log odds; fitted only on calibration", "C": 1e6, "coefficient": float(calibrator.coef_[0, 0]), "intercept": float(calibrator.intercept_[0])},
                     "selection": "Calibrated booster designated before evaluating holdout; fixed parameters, no hyperparameter search.", "oot_available": False},
        "data_quality": {"rows": len(df), "defaults": int(y.sum()), "default_rate": float(y.mean()), "missing_cells": int(df.isna().sum().sum()),
                         "unique_ids": int(df.ID.nunique()), "unique_predictor_groups": int(len(np.unique(groups))), "duplicate_predictor_rows": int(len(df) - len(np.unique(groups))),
                         "undocumented_status_counts": undefined, "negative_bill_records": int((df[[f"BILL_AMT{i}" for i in range(1, 7)]] < 0).any(axis=1).sum()),
                         "handling": "No observed rows dropped; negative bills and undocumented statuses retained and flagged."},
        "partitions": {part: {"rows": int((partitions == part).sum()), "defaults": int(y[partitions == part].sum()), "default_rate": float(y[partitions == part].mean())} for part in PARTITIONS},
        "models": results, "stability": stability,
        "bootstrap": bootstrap_intervals(y[hold], calibrated[hold], probabilities["logistic"][hold]),
        "checks": {"source_checksum": "passed", "id_overlap": 0, "predictor_group_overlap": 0,
                   "platform_auc_vs_sklearn": "passed for every model and partition", "platform_ks_vs_roc": "passed for every model and partition",
                   "prediction_rows": int(len(predictions)), "finite_predictions_in_unit_interval": bool(all(np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all() for p in probabilities.values()))},
        "governance": {"status": "research_only", "approved_for_production": False, "independent_review": "pending", "findings": findings},
        "limitations": ["Retail Taiwan credit-card cohort with 2005 histories; not current corporate or fund credit evidence.",
                        "No dated application cohorts; no OOT or macroeconomic drift validation.",
                        "Estimated next-month default probabilities are model outputs, not observed true PDs.",
                        "No observed recoveries, LGD, EAD-at-default, collateral, trades, netting, margin or regulatory capital evidence; no expected-loss amount is asserted.",
                        "Bootstrap intervals condition on fixed fitted models and class counts; they omit refitting, macro uncertainty and selection effects.",
                        "Predictor-profile grouping mitigates exact duplicate leakage; household identities and unrecorded dependence are unavailable.",
                        "Protected and demographic variables are excluded as predictors; a full fairness assessment remains outstanding."],
    }
    report["protocol"]["prediction_precision"] = "All scores rounded to 12 decimal places before metrics and CSV export; ties share a stable definition."
    write_json(destination / "report.json", report)
    (destination / "report.md").write_text(render_markdown(report), encoding="utf-8")
    make_figures(report, predictions, destination)
    artifact_files = ("report.json", "report.md", "source_manifest.json", "predictions.csv", "observed_clients.csv", "feature_dictionary.csv", "validation.png")
    manifest = {"case_study_id": report["case_study_id"], "source_archive_sha256": SOURCE_SHA256,
                "code_sha256": {str(Path(__file__).relative_to(root)): sha256(Path(__file__)),
                                "scripts/run_public_credit_case_study.py": sha256(root / "scripts/run_public_credit_case_study.py")},
                "artifacts": {name: {"sha256": sha256(destination / name), "bytes": (destination / name).stat().st_size} for name in artifact_files}}
    write_json(destination / "artifact_manifest.json", manifest)
    if workspace is not None:
        target = workspace / "case-studies" / "credit-default"
        if target.resolve() != destination.resolve():
            target.mkdir(parents=True, exist_ok=True)
            for name in (*artifact_files, "artifact_manifest.json"):
                shutil.copy2(destination / name, target / name)
    return report
