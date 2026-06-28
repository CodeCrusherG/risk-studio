# Risk Studio local runbook

Risk Studio supports data processing, feature analysis, modeling, validation, strategy development, and portfolio analysis. This guide covers local installation, operation, and the Notebook/PMML validation workflow. For the populated dashboard case, see the [public credit study](public-credit-case-study.md).

## Requirements

- Python 3.11–3.13; Python 3.12 is recommended for a new environment.
- The source installation has been exercised on macOS and Linux.
- PMML scoring needs a Java runtime compatible with `pypmml`.
- Node.js is used for JavaScript syntax checks. The web service serves static assets and needs no frontend build.
- Agent workflows require a configured LLM provider. The public credit study runs independently of an LLM.

## Install this checkout

Use the `risk-studio` directory supplied in this workspace. It includes local dashboard and case-study extensions to [upstream MARVIS](https://github.com/eddyzzl/marvis-risk-agent); cloning upstream alone does not reproduce this checkout.

From the parent workspace:

```bash
cd risk-studio
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`. For contributor tools, install `python -m pip install -e ".[dev]"`.

Alternatively, from the `risk-studio` directory:

```bash
conda create -n marvis python=3.12
conda activate marvis
python -m pip install -U pip
python -m pip install -e .
```

## Start the service

```bash
risk-studio
```

The default is equivalent to:

```bash
risk-studio serve \
    --host 127.0.0.1 --port 8000 --workspace ./workspace
```

Open `http://127.0.0.1:8000/` for the dashboard or `/workbench` for the workbench. The Python package name is `marvis`, so the equivalent module command is:

```bash
python -m marvis serve \
    --host 127.0.0.1 --port 8000 --workspace ./workspace
```

The `marvis` and `marvis-risk-agent` CLI aliases remain available for compatibility.

## Windows packaging

The inherited Windows packaging uses the filename `MARVIS-Setup-<version>-win-x64.exe`. Build scripts and installer templates are in [`packaging/windows/`](../packaging/windows/). An upstream installer may not include this checkout's local additions.

The installer bundles private Python and Java runtimes. Its default locations are:

| Purpose | Path |
|---|---|
| Installation | `%LOCALAPPDATA%\Programs\MARVIS-Agent` |
| Workspace | `%LOCALAPPDATA%\MARVIS-Agent\workspace` |
| Logs | `%LOCALAPPDATA%\MARVIS-Agent\logs` |

The launcher sets `JAVA_HOME` and `PATH`, starts the service on `127.0.0.1:8000`, and opens the browser. The source workflow does not require Docker.

## Material directories

Task materials must be under the current workspace, the current user's home directory, or an explicitly allowed root. For materials on a Windows data drive:

```powershell
$env:RMC_MATERIAL_ROOTS="D:\model_materials"
risk-studio serve --host 127.0.0.1 --port 8000 --workspace .\workspace
```

Separate multiple roots with the operating system's path separator: semicolons on Windows, colons on macOS/Linux/WSL. Under WSL, enter a Linux path such as `/mnt/c/Users/<you>/Downloads/project`.

## Shared hosts and reverse proxies

By default, the service trusts loopback clients. On a shared machine, another local user can connect to the same port. Configure authentication before using it on a shared host.

### Local token

`MARVIS_LOCAL_TOKEN` protects private API reads and requires `X-Marvis-Token` for writes, including requests from loopback:

```bash
export MARVIS_LOCAL_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
risk-studio serve --host 127.0.0.1 --port 8000 --workspace ./workspace
```

On the first browser visit, HTTP Basic authentication accepts any username and the token as the password. The authenticated page is returned with `Cache-Control: no-store`; its API client includes the token in requests. Basic authentication alone does not authorize write requests.

This token does not isolate processes that can already read the service account's environment or files. Use operating-system account, container, or virtual-machine isolation where that boundary is required.

### Remote read access

By default, remote clients can reach the public page, health endpoint, and static assets. To allow supported read-only API access:

```bash
export MARVIS_ALLOW_REMOTE_READ=1
```

Settings, branding, and other local-only routes remain restricted. This setting does not authorize remote writes or expose the local token to arbitrary remote clients.

### Trusted proxies

For JupyterHub's proxy or another reverse proxy, configure the proxy address explicitly:

```bash
export MARVIS_TRUSTED_PROXY_HOSTS="127.0.0.1"
```

Separate multiple addresses with commas. The access guard uses forwarded client addresses only from trusted proxies; untrusted forwarded headers do not grant local access. With a local token configured, private reads and writes through a trusted proxy still require authentication. The proxy must replace client-supplied forwarding headers and protect token transport with HTTPS.

For a shared JupyterHub host, configure `MARVIS_LOCAL_TOKEN` and the relevant trusted proxy addresses. Enable remote read access only when it is needed. See the [Linux environment checklist](deploy-linux-env-checklist.md) for deployment prerequisites.

## Run multiple versions

Give each running checkout its own port and workspace. Profiles provide defaults:

```bash
risk-studio serve --profile main
# http://127.0.0.1:8000, workspace ./workspace-main

risk-studio serve --profile v2
# http://127.0.0.1:8200, workspace ./workspace-v2
```

Explicit arguments override profile defaults:

```bash
risk-studio serve --profile v2 --port 8217 --workspace ./custom-workspace
```

## Updates

The update command operates on the configured Git remote and branch. Use it only when that remote contains the version and local additions you intend to install. It is not a distribution channel for this workspace's extensions.

For a clean checkout tracking the intended `origin/main`:

```bash
risk-studio update
```

Its default update sequence is:

```text
git fetch origin
git pull --ff-only origin main
python -m pip install -e . --no-deps
```

The command refreshes the editable installation without changing the dependency set. Use `--with-deps` when the intended update requires new dependencies. Tracked local changes must be committed, stashed, or backed up before updating; untracked files remain unless they conflict with the incoming files.

When run from conda `base`, the command creates or reuses a dedicated `marvis` environment and installs there. `--env-name <name>` selects another environment. Compatible launch commands delegate to that environment. Keep application dependencies in the dedicated environment.

If an older installation lacks the update command, run the fetch/pull and editable-install commands manually from its checkout, after confirming the remote and preserving local changes.

## Backup and restore

Task state, audit records, experiments, and memory use `workspace/marvis.sqlite` and files under `workspace/`. SQLite uses WAL mode, so copying the directory while the service is running can miss recent database commits.

The backup command uses SQLite's online backup API to create a consistent database snapshot:

```bash
risk-studio backup --workspace ./workspace --out risk-studio-backup.tar.gz
```

Datasets are excluded by default. Include them when needed:

```bash
risk-studio backup --workspace ./workspace --out full-backup.tar.gz --include-datasets
```

Restore into an empty directory:

```bash
risk-studio restore risk-studio-backup.tar.gz --workspace ./workspace-restored
risk-studio serve --workspace ./workspace-restored
```

Restoring over an existing nonempty directory requires `--force`. Startup reconciliation handles unfinished task artifacts as it would after an interrupted run.

## Validate a submitted model

Create a task through the web interface or API, then run:

```bash
risk-studio validate <task_id> --workspace ./workspace
```

The module equivalent is `python -m marvis validate <task_id> --workspace ./workspace`.

The validation workflow:

1. Records the model name, version, reviewer, material directory, and algorithm.
2. Scans the Notebook, sample, submitted PMML, and data dictionary.
3. Executes a prepared Notebook copy and extracts its runtime contract and in-memory model scores.
4. Compares those scores with the submitted PMML and calculates performance, stability, and stress evidence.
5. Writes Excel and Word reports.

Typical task outputs are:

```text
workspace/tasks/<task_id>/
  execution/
    prepared.ipynb          Notebook copy with injected setup and extraction cells
    executed.ipynb          Executed Notebook
    runtime_contract.json   Extracted RMC_* contract
    code_model_scores.csv   Scores from RMC_SCORE_FN
    feature_importance.csv  Optional feature-importance output
    model_params.json       Optional model parameters
    model_meta.json         Report metadata
    notebook_steps.json     Markdown headings and cell execution evidence
    notebook.log
  outputs/
    validation.xlsx
    validation_report.docx
  images/                   Charts used in the Word report
```

Word templates are loaded from `workspace/report_templates/` and use `{{TEXT:key}}` and `{{IMAGE:key}}` placeholders. See the [Notebook contract](notebook_contract.md) and [submission requirements](notebook_submission_requirements.md) before preparing model materials.

For acceptance on your own materials, run validation, inspect both reports, and reconcile the calculated metrics against an independent reference with the same sample, target, score direction, and rounding rules.
