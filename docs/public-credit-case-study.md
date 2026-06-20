# Observed public credit-default case study

Risk Studio includes a populated **Observed defaults** panel at `/` and `/risk-studio`, above the institutional portfolio summary. Open its details to inspect holdout comparisons, calibration, sample stability, and outstanding model-review findings. The panel reads the reproduced report and verifies its checksum. Download the 30,000 observed records for the `/workbench` data-processing workflow, or download all predictions to reconcile outcomes and model metrics.

## Run

From the repository root, using the existing environment:

```bash
.venv/bin/python scripts/run_public_credit_case_study.py --offline
.venv/bin/python -m marvis serve --host 127.0.0.1 --port 8000 --workspace workspace
```

The checked source archive supports a fully offline run. If starting without the cache, omit `--offline` to fetch the fixed HTTPS UCI URL. Unexpected source bytes cause an error; the script never silently changes datasets. Model fitting runs with one computation thread for reproducibility. Python and package versions are recorded in `report.json`; different package versions may produce different fitted results.

The command writes reviewable deliverables to `evidence/credit-default/` and populates `workspace/case-studies/credit-default/`. An explicit `--workspace` supports another running workspace. The API prefers that workspace's evidence and otherwise uses the repository evidence. A missing build is reported as unavailable.

## Provenance and use

[UCI Default of Credit Card Clients](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients), attributed to Yeh (2009), DOI [10.24432/C55S3H](https://doi.org/10.24432/C55S3H), is distributed by UCI under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). It contains 30,000 observed Taiwanese credit-card records, 6,636 next-month payment-default outcomes, and payment histories for April–September 2005. The source definitions, archive checksum, retrieval timestamp and transformation descriptions are in `data/public/uci_credit_default/source_manifest.json` and the report copy. The project MIT license does not replace the dataset license.

This implementation excludes ID and demographics from model predictors, fits a logistic baseline and a fixed gradient-boosting challenger, then fits a sigmoid calibrator on a separate calibration population. The holdout population is untouched by fitting or selection. Identical predictor profiles stay in the same partition. Risk Studio's existing AUC, KS and PSI kernels calculate risk metrics; AUC and KS reconcile against independent scikit-learn calculations on every model and partition.

The report includes calibrated and uncalibrated results. Calibration is not presumed to improve performance. Score and feature PSI assess random-split stability within this one cohort; no invented calendar vintages or out-of-time validation are used. Estimated PD is clearly separate from the observed default flag. This dataset supplies no LGD, recovery, EAD-at-default or trading exposure measurements.

Predictions are rounded to 12 decimal places before metric calculation and CSV export. This preserves a consistent score-tie definition across CSV parsers; metrics reconcile directly from the downloaded file.

The artifacts document model fitting, challenger comparison, calibration assessment, performance reporting, and source lineage on observed data. They do not establish production model approval, corporate underwriting performance, SIMM, trading exposure calibration, or regulatory compliance.

## Evidence

- [Executed validation report](../evidence/credit-default/report.md): results, uncertainty, source quality findings and review actions.
- [Complete metrics](../evidence/credit-default/report.json): parameters, versions, calibration bins, feature stability, checks and limitations.
- [Artifact manifest](../evidence/credit-default/artifact_manifest.json): source-code and deliverable SHA-256 hashes; integrity metadata, not a signed audit.
- [Observed clients](../evidence/credit-default/observed_clients.csv): all original data plus reproducible partition; no synthesized dates.
- [Predictions](../evidence/credit-default/predictions.csv): observed labels, source IDs, partition and fitted probabilities.
- [Validation chart](../evidence/credit-default/validation.png): holdout ROC and calibration alongside same-cohort score distributions.

Read-only endpoints: `GET /api/risk-studio/credit-case-study` and `GET /api/risk-studio/credit-case-study/artifacts/{name}`. Only explicit public artifact names can be downloaded; modified files fail checksum validation.

```bash
.venv/bin/python -m pytest tests/test_credit_case_study.py
.venv/bin/python -m ruff check marvis/credit_case_study.py marvis/credit_case_api.py scripts/run_public_credit_case_study.py tests/test_credit_case_study.py
node --check marvis/static/credit-case-study.js
```

## Executed verification

Executed on 4 October 2026 (India time), using the existing `.venv`:

| Command or check | Result |
|---|---|
| `.venv/bin/python scripts/run_public_credit_case_study.py --offline` | Completed; 30,000 observed records, 6,636 defaults; 18,000 development / 6,000 calibration / 6,000 holdout |
| `.venv/bin/python -m pytest tests/test_credit_case_study.py -q` | 9 passed in 5.82 seconds; one existing Starlette/httpx deprecation warning |
| `.venv/bin/python -m ruff check marvis/credit_case_study.py marvis/credit_case_api.py scripts/run_public_credit_case_study.py tests/test_credit_case_study.py` | All checks passed |
| `node --check marvis/static/credit-case-study.js` | Exit code 0 |
| `.venv/bin/python -m marvis serve --host 127.0.0.1 --port 8093 --workspace workspace` | Live app started; new report API, downloads and existing workbench returned HTTP 200 |
| Playwright Chromium, 1440×1080 and 390×844 | No JavaScript errors; report download reconciled to 30,000 records; chart loaded; no mobile horizontal overflow |
| Independent offline rerun via `run_case_study(Path.cwd(), offline=True, output=Path.cwd() / '.scratch-credit-repeat')` | Report identical except generation timestamp; predictions, observed source CSV, dictionary, source manifest, report text and chart byte-identical |

Held-out calibrated-booster AUC: **0.779859** (95% bootstrap interval **0.763649–0.793001**); KS: **0.424455**; Brier: **0.135375**; observed/expected defaults: **0.975604**. Logistic baseline AUC: **0.770991**, Brier: **0.137722**. Raw-booster Brier: **0.135294**: calibration slightly worsened the holdout probability score, and the report preserves that finding. Development-to-holdout PSI is **0.002541**, interpreted strictly as sample stability within one cohort.

The tests cover pinned real-data schema, corrupt/missing cache handling, deterministic disjoint predictor groups, independent AUC/KS/Brier reconciliation, all persisted predictions against source labels, artifact hashes, API corruption rejection and path containment. They do not claim a full repository regression suite or production model approval.

Machine-readable evidence: [verification.json](../evidence/credit-default/verification.json), [offline reproduction check](../evidence/credit-default/reproduction_check.json), [desktop screenshot](../evidence/credit-default/dashboard-desktop.png), and [mobile screenshot](../evidence/credit-default/dashboard-mobile.png).
