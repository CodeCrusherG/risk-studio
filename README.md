<p align="center">
  <img src="marvis/static/brand/risk-studio-mark.svg" alt="Risk Studio logo" width="94" />
</p>

<h1 align="center">Risk Studio</h1>

<p align="center">A local workbench for credit analysis, model validation, and strategy development.</p>

Risk Studio combines a risk dashboard with an AI-assisted workbench. The dashboard includes a reproducible study of observed credit defaults, public FX reference rates, and portfolio calculations from imported data. The workbench supports data preparation, model development and validation, strategy analysis, and reports. Platform tools calculate the metrics; the agent helps clarify inputs, plan work, and explain results.

## Contributors

| Pair | Contributors | Responsibility |
|---|---|---|
| Pair 1 | [Gopesh (@CodeCrusherG)](https://github.com/CodeCrusherG) and [Prateek (@PrateekIITMandi)](https://github.com/PrateekIITMandi) | Data preparation and model development |
| Pair 2 | [Manav (@manav-bidawat)](https://github.com/manav-bidawat) and [Abhay (@immortal-coder-abhay)](https://github.com/immortal-coder-abhay) | Model validation and strategy workflows |

## Explore the dashboard

After starting the app, open [Risk Studio](http://127.0.0.1:8000/) or the [workbench](http://127.0.0.1:8000/workbench).

| View | Available data and analysis |
|---|---|
| **Observed defaults** | 30,000 UCI credit-card records and 6,636 observed defaults; logistic and boosting models; a separate calibration sample and 6,000-record holdout; AUC, KS, Brier score, calibration intervals, sample stability, and downloadable predictions. |
| **Market reference rates** | Daily ECB FX reference rates with observation and retrieval timestamps. |
| **Credit review** | Financial ratios, visible warning thresholds, indicative rating bands, and counterparty summaries from imported JSON. |
| **Exposure** | Positive mark to market, collateral, an illustrative potential future exposure add-on, limit utilization, and movement against a supplied previous snapshot. |
| **Methodology** | Historical one-day VaR and expected shortfall, rolling backtest exceptions, an illustrative margin buffer, and product stress scenarios from imported returns. |

The **Observed defaults** case is populated. Institutional portfolio calculations require your own JSON inputs. The UCI study concerns historical retail credit; it supplies no trading exposure or LGD observations, and temporal validation and independent model approval remain outstanding.

Read the [executed credit report](evidence/credit-default/report.md), [reproduction guide](docs/public-credit-case-study.md), or [dashboard methodology and input contract](docs/risk-studio.md).

## Quick start

Use this workspace's `risk-studio` directory. Source installation supports Python 3.11–3.13; Python 3.12 is recommended for a new environment.

From the parent workspace:

```bash
cd risk-studio
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
risk-studio
```

Open `http://127.0.0.1:8000/`. On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`. The equivalent module command is:

```bash
python -m marvis serve --host 127.0.0.1 --port 8000 --workspace workspace
```

The checked source archive supports reproducing the public credit study offline:

```bash
.venv/bin/python scripts/run_public_credit_case_study.py --offline
```

PMML scoring requires a Java runtime compatible with `pypmml`. The [runbook](docs/runbook.md) covers installation, material directories, shared hosts, updates, and backups. Agent workflows also require a configured LLM provider; the public credit study can be reproduced without one.

## Workbench workflows

| Workflow | Capabilities and outputs |
|---|---|
| **Data processing** | Register CSV/Excel files, profile fields, diagnose and confirm joins, deduplicate, transform data, and export derived datasets with lineage. |
| **Labels, samples, and features** | Define labels and observation windows, check maturity, prepare development/validation/OOT samples, calculate IV/KS/AUC/PSI/lift/coverage, bin and select features, and export analysis workbooks. |
| **Model development** | Train and compare binary, regression, and multiclass recipes; assess leakage and sample weights; tune, calibrate, score, and export reports, model cards, and PMML for supported recipes. |
| **Model validation** | Inspect Notebook, sample, PMML, and dictionary materials; compare scores and calculate performance, stability, binning, and stress metrics; produce Excel and Word reports. One task accepts 1–10 models, with a summary workbook for two or more. |
| **Strategy development** | Build rules, trees, cross matrices, scorecard cutoffs, and Voting/n-of-k combinations; manage Strategy Pools; measure impact and stability; validate on independent partitions; export Python, DuckDB SQL, JSON, and review reports. |
| **Vintage and risk analysis** | Confirm fields, units, dates, and assumptions before calculating VTG-terminal/annualized bad rate or profitability. Standard Vintage and roll-rate analyses produce separate evidence and reports. |
| **Portfolio and monitoring** | Analyze migration, segments, concentration, expected loss, and limit/pricing trade-offs; inspect model and strategy stability and prepare follow-up tasks. The documented portfolio workflow covers analysis without time-series trends. |

The seven main workbench entries are Data Processing, Feature Analysis, Risk Analysis, Portfolio Analysis, Model Development, Model Validation, and Strategy Development. Label construction is part of Data Processing; monitoring is integrated into model and strategy workflows.

Manual controls and agent mode share workflow definitions and calculation tools. The agent asks for missing files and definitions, proposes a plan, pauses at required confirmation steps, and returns evidence and artifacts. See [capability status](docs/capability-status.md) for workflow support and limitations.

## Strategy development

The strategy workflow follows seven steps:

1. Review the current project's population, approval rate, risk, profitability, and constraints.
2. Compare historical strategy versions, results, and assumptions.
3. Define approval and risk populations, sample partitions, labels, maturity rules, and weights.
4. Evaluate variables and models on the selected samples.
5. Build candidates for approval, rejection, limits, pricing, and segmentation in a Strategy Pool.
6. Measure impact by month, segment, amount, and partition; check stability and independent validation results.
7. Deliver a canonical strategy, equivalent Python/DuckDB SQL/JSON implementations, and JSON/Markdown/XLSX/DOCX review reports.

Missing optional report fields remain blank when the user confirms that the information is unavailable. Missing inputs that affect the calculation must be resolved before execution. Local strategy adoption does not deploy a production decision service.

## Example requests

> Join the application table with the bureau features. Check key precision, duplicate keys, match rate, and row inflation before I approve the join.

> Compare logistic regression, LightGBM, and a scorecard. Keep an OOT sample and explain any leakage concerns before I select a model.

> Build a new-customer approval strategy with bad rate no higher than 5% and approval rate at least 60%. Confirm the sample definition first.

> Calculate VTG terminal and annualized bad rate. List the required tables, fields, units, cut-off date, and assumptions.

## Review and deployment limits

Deterministic tools calculate metrics, rules, sample membership, backtests, and report values. The agent explains those results and retains source references. Memory can retain permitted preferences, field definitions, and summaries; it cannot change calculated metrics. Raw customer rows, full model files, credentials, private reports, and database connections are excluded from agent memory.

Strategy adoption and other actions that change approved state require human authorization. Production use still requires representative data, agreed definitions, independent reconciliation, and responsible-party approval. Full organizational RBAC, production promotion and rollback, live decision-engine integration, and cross-device synchronization are not established by the local workflows.

## Documentation

- [Dashboard methodology](docs/risk-studio.md) and [public credit case study](docs/public-credit-case-study.md)
- [Runbook](docs/runbook.md) and [Linux environment checklist](docs/deploy-linux-env-checklist.md)
- [Product scope and roadmap](docs/roadmap.md) and [capability status](docs/capability-status.md)
- [Notebook contract](docs/notebook_contract.md) and [submission requirements](docs/notebook_submission_requirements.md)
- [Architecture](docs/architecture.md), [branding](docs/branding.md), and [versioning](docs/versioning.md)

For contributor checks, install the development extras with `python -m pip install -e ".[dev]"` and run `scripts/check`. Run the focused credit-study checks with `.venv/bin/python -m pytest tests/test_credit_case_study.py`. The [reproduction guide](docs/public-credit-case-study.md) documents the checks and saved results.

## License and attribution

Risk Studio is based on [MARVIS](https://github.com/eddyzzl/marvis-risk-agent) and is distributed under the [MIT License](LICENSE). The dashboard and public credit study in this workspace extend the upstream application. Public datasets retain their own licenses; the [credit study provenance](docs/public-credit-case-study.md#provenance-and-use) includes the UCI citation and license.
