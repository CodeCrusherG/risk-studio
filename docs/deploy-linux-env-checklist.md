# MARVIS-Agent Linux Source deployment — Environmental readiness list

**Products**:MARVIS-Agent V2.x(Credit Winds LocalAgent)
**Deployment pattern**:Source Install+ This is the machine.Web Services (in thousands of United States dollars)FastAPI)
**Division of labour**:- Get ready for the ride.OS / System Package/ Python / Java / Account/ Disk/ Networks and privileges; operational side self-installation and start-up.

No, I don't.Node.js,Frontend builder.Docker Not a person./default path;ifIT To be self-packaged in packagings, the operational dependence in this document shall be satisfied.

Relevant documents:

- Local runbook:[`docs/runbook.md`](runbook.md)
- Installation and start-up description:[`README.md`](../README.md)
- Reliance declaration:[`pyproject.toml`](../pyproject.toml)
- Reference lock version:[`uv.lock`](../uv.lock)

---

## 1. Machines andOS

| Item| Request| Reason|
|----|------|------|
| OS | Linux x86_64(RecommendationsUbuntu 22.04/24.04 orRHEL/Rocky 8/9) | Source installation path verifiedmacOS/Linux;wheel ♪ Mostly ♪`manylinux2014_x86_64` |
| Structure| Priorityx86_64;If I have to.aarch64 Requires an advance explanation| Avoid Packaging Failed|
| glibc | ≥ 2.17(`manylinux2014`) | Binarywheel Baseline|
| Time zone/Languages| UTF-8 locale(Like`en_US.UTF-8` or`zh_CN.UTF-8`) | Notebook / Path/ Log to avoid coding problems|
| User| Specialized general users (e.g.,`marvis`),Don't use it.root Run service.| Security and documentation authority|
| SSH | The deploying person can log in to the user and write down the installation directory| Operational side self-deployment|

### Suggested Configuration

| Resources| Minimum| Recommendations|
|------|------|------|
| CPU | 4 Nuclear| 8 Nuclear+ |
| Memory| 16 GB | 32 GB+(Modelling+ DuckDB JOIN + PMML JVM Co-exist)|
| System Disk| 20 GB Available (loading environment)| 40 GB+ |
| Disk (Databoard)workspace) | 100 GB | 200 GB+(Task products, data sets,DuckDB (Provisional documents)|
| GPU | No, I don't.| Training DefaultCPU;Linux Go, go, go!xgboost Maybe pull`nvidia-nccl-cu12`,It doesn't mean you have to.CUDA Driver|

---

## 2. System-level software (transportation)

### 2.1 It's a costume.

| Component| Version| Use|
|------|------|------|
| Git | Any Newer| clone / Update Code|
| Python | **3.12.x**(Hardness`>=3.11`,Strong recommendation 3.12;Do not use system 3.8/3.9) | Apply running time|
| OpenJDK / Temurin | **17**(JRE - I'll be fine.| PMML Rating (%2)`pypmml` / JPype / py4j) |
| ca-certificates / openssl | System Default Update| HTTPS Pull!PyPI,TranquilityLLM |
| curl / wget | Any| Connectivity check|
| libgomp | System Package (Package)Debian: `libgomp1`) | LightGBM / XGBoost OpenMP |

It's also available.Miniconda / Micromamba Create a dedicated environment (recommended environment name)`marvis`,Python 3.12).**Don't.**- Put it on.MARVIS Loadconda `base`.

#### Debian / Ubuntu Example:

```bash
sudo apt-get update
sudo apt-get install -y \
  git curl ca-certificates \
  python3.12 python3.12-venv python3.12-dev \
  openjdk-17-jre-headless \
  libgomp1 \
  build-essential
```

`python3.12-dev` and`build-essential`:Most of the bags do.wheel,But in individual circumstances/The structure is used if source code compilation is required.

#### RHEL / Rocky Example:

```bash
sudo dnf install -y git curl ca-certificates \
  python3.12 python3.12-devel \
  java-17-openjdk-headless \
  libgomp gcc gcc-c++ make
```

### 2.2 Java Must be available to the service process

Other Organiser

```bash
java -version    # Should be 17.x
which java       # It must be.PATH Medium
```

Suggested simultaneous configuration:

```bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64   # Path adjusted to actual distribution
export PATH="$JAVA_HOME/bin:$PATH"
```

Write to the user`~/.bashrc`,orsystemd unit It's...`Environment=`.

Note: Application sub-processes pass through`PATH`.Make sure.`java` Yes.PATH Go, don't just set it up.`JAVA_HOME` But he didn't.PATH.

### 2.3 Recommended installation (failure to lower edge)

| Package| Use|
|----|------|
| `graphviz`(System Package)| CatBoost RelevantPython `graphviz` It may be necessary to draw a picture`dot`;Core training is usually not dependent on|
| `fonts-dejavu-core` or Chinese fonts| matplotlib Diagram Missing Warning (not necessary)|

### 2.4 No need for luck.

- Node.js / npm
- Docker / WSL(Unless...IT (Prescribed containers)
- CUDA / nvidia-driver
- Front-end Builder

---

## 3. Python Package Dependence

The mission needs to be assured that:**Deployment user accessPyPI(Or an internal mirror)**,The following packages are also allowed.

Implementation on the operational side deployment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -e .
# Don't pretend..[dev],That's for development testing.
```

### 3.1 Directly dependent (`pyproject.toml`,(Performance required)

| Package| Version Constraint|
|----|----------|
| fastapi | `>=0.115,<1` |
| uvicorn | `>=0.30,<1` |
| python-multipart | `>=0.0.9,<1` |
| pydantic | `>=2.7,<3` |
| filelock | `>=3.13,<4` |
| packaging | `>=16.8,<27` |
| jsonschema | `>=4.0,<5` |
| psutil | `>=5.9,<8` |
| nbformat | `>=5.9,<6` |
| nbclient | `>=0.8,<0.12` |
| ipykernel | `>=6.23.2,<8` |
| ipython | `>=8.20,<10` |
| jupyter-client | `>=8.6,<9` |
| numpy | `>=1.26,<3` |
| pandas | `>=2.2,<4` |
| scipy | `>=1.12,<2` |
| scikit-learn | `>=1.4,<2` |
| statsmodels | `>=0.14,<1` |
| joblib | `>=1.3,<2` |
| pyarrow | `>=15,<25` |
| duckdb | `>=0.9,<2` |
| openpyxl | `>=3.1,<4` |
| xlrd | `>=2.0,<3` |
| python-docx | `>=1.1,<2` |
| rapidfuzz | `>=3,<4` |
| matplotlib | `>=3.8,<4` |
| seaborn | `>=0.13,<1` |
| xgboost | `>=2.0,<4` |
| lightgbm | `>=4.0,<5` |
| catboost | `>=1.2,<2` |
| pypmml | `>=1.5,<2` |
| sklearn2pmml | `>=0.131,<1` |

### 3.2 Critical transmission dependency (often firewalled)/ Audit stuck)

| Package| Use|
|----|------|
| JPype1 | `pypmml` → JVM |
| py4j | `pypmml` |
| dill | `sklearn2pmml` |
| pillow / fonttools / kiwisolver / contourpy | matplotlib |
| lxml / et-xmlfile | docx / Excel |
| pyzmq / tornado / traitlets / jupyter-core | Notebook kernel |
| starlette / anyio / h11 / click | FastAPI / uvicorn |
| nvidia-nccl-cu12 | Linux Go, go, go!xgboost The declaration is based on (the)**No, I don't.GPU/CUDA Driver**,But...PyPI I have to be able to get this bag down.|
| plotly / graphviz(Python) | catboost Relevant|

### 3.3 Reference Locked Version (Stockroom)`uv.lock`,Python ≥3.12)

A white list or offline cache that allows cross-references.**In practical terms`pip install` Parsing is the rule.**;Complete parse tree app. 90+ A running time package.

```text
fastapi==0.138.0
uvicorn==0.49.0
pydantic==2.13.4
numpy==2.5.0
pandas==3.0.3
scipy==1.18.0
scikit-learn==1.9.0
pyarrow==24.0.0
duckdb==1.5.4
xgboost==3.3.0
lightgbm==4.6.0
catboost==1.2.10
pypmml==1.5.8
sklearn2pmml==0.131.0
jpype1==1.7.1
py4j==0.10.9.9
matplotlib==3.11.0
ipykernel==7.3.0
seaborn==0.13.2
statsmodels==0.14.6
openpyxl==3.1.5
python-docx==1.2.0
filelock==3.29.4
psutil==7.2.2
rapidfuzz==3.14.5
jsonschema==4.26.0
nbformat==5.10.4
nbclient==0.11.0
jupyter-client==8.9.1
ipython==9.14.1
joblib==1.5.3
python-multipart==0.0.32
xlrd==2.0.2
packaging==26.2
nvidia-nccl-cu12==2.30.7
```

If the Internet is only a white list name: by§3.1 + §3.2 Release, or offerPyPI Mirror/ Offlinewheelhouse.

---

## 4. Network and firewall

### 4.1 Installation phase (deployment of users)

| Direction| Objective| Annotations|
|------|------|------|
| Out.HTTPS | `pypi.org` + `files.pythonhosted.org`(Or company.PyPI Mirror)| `pip install` |
| Out.HTTPS | Git SourceGitHub Or the Internet.Git) | `git clone` / `git pull` |
| Out.| LLM API Address| Agent dialogue; installation phase is not appropriate and access is required|

### 4.2 Operational phase

| Item| Request|
|----|------|
| Listening| Default`127.0.0.1:8000`(I'm going back to the ring.|
| JupyterHub / Reverse Agent| Release the machine to the proxy port; and configure§6 Security Variable|
| LLM | Service Host AccessibleOpenAI Compatible Peer`api_base_url`) |
| Optional Extranet| Default Detection`example.com`,SearchDuckDuckGo;It can shut down the offline without affecting core authentication./Modelling|

Please confirm and inform the deploying personnel in advance:

1. PyPI Is it straight-link? What's the mirror address? Do you want representation?`HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY`)?
2. LLM It's...`api_base_url`,Do you want an intranet?DNS,Do you want a company?CA(`SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE`)?
3. Is the service only for real or for real?JupyterHub proxy Exposure?

---

## 5. Contents and Permissions

Example path reable. Permission model maintained:

```text
/opt/marvis/app          # Code directory, deploy user-repeated (or first)clone Again.chown)
/data/marvis/workspace   # Run the data directory and deploy the user to read and write
/data/marvis/materials   # Optional: Model material/Sample Directory (if not available)home Down)
/var/log/marvis          # Optional: Log Directory
```

| Path| Permissions|
|------|------|
| Code Directory| Deployment of usersrwx |
| workspace | Deployment of usersrwx(I can write.SQLite,Mission,datasets,`.duckdb_tmp`) |
| Catalogue of materials| At least readable; preferably readable if copied into library|

If the material is not available`$HOME` And not here.workspace Under which the following requirements are required before commencement:

```bash
export RMC_MATERIAL_ROOTS="/data/marvis/materials"
```

Multiple root paths`:` Separate.

---

## 6. Process-related environmental variables

(a) Single-person aircraft may not be installed;**Multi-UserLinux / JupyterHub I'm asking strongly.**At least Configure`MARVIS_LOCAL_TOKEN`.

| Variables| Recommendations| Role|
|------|------|------|
| `MARVIS_LOCAL_TOKEN` | Random 32+ Bytes| Protect Home Home Page/API;Writing operations must be visibletoken,Protection against read-out or misuse by other users of the same machine|
| `MARVIS_TRUSTED_PROXY_HOSTS` | Like`127.0.0.1` | Only the agent.`X-Forwarded-For`;andlocal token Enable token-protected proxy working tables together|
| `MARVIS_ALLOW_REMOTE_READ` | As required`1` | Allow non-in-house reading; write still needs to be visible on the machine or a trusted agenttoken |
| `JAVA_HOME` + PATH | It's a match.| PMML |
| `MARVIS_DUCKDB_MEMORY_LIMIT` | Default`4GB`,Memory is tight to change.`2GB` | DuckDB |
| `MARVIS_DUCKDB_THREADS` | Default`cpu/2` | DuckDB |
| `MARVIS_MAX_CSV_UPLOAD_BYTES` | Default 2GB | Upload limit|
| `MARVIS_MAX_EXCEL_UPLOAD_BYTES` | Default 500MB | Upload limit|
| `MARVIS_MAX_EXCEL_ROWS` | Default 2 million lines| Excel Line Maximum|
| `MARVIS_LOG_LEVEL` | DefaultINFO | Log|

Tool DefaultRSS About 4 of the guardGB/process tree; whole memory recommendations≥16–32GB.

Generatetoken Example:

```bash
export MARVIS_LOCAL_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

After setting, direct link or pass`MARVIS_TRUSTED_PROXY_HOSTS` The browser that specifies the accesses will receive it when it opens its first pageHTTP Basic Hint: The user name is entered at all times, with the password.token.Authentication can be used for private reading; follow-up is still sent by page visible`X-Marvis-Token`,Can't just rely on browser cachesBasic certificate. The agent must cover forged by the client`X-Forwarded-For`,and useHTTPS.

---

## 7. LLM(Agent)Configure Preconditions

Use of Platform**OpenAI Compatible** HTTP API.The network is accessible; the model key is configured by the deployer in the application settings:

- `api_base_url`
- `model_name`
- `api_key`(or the environment variable name`api_key_env`)

Not MatchedLLM Time: Identification tool and validation can still run; natural languageAgent Not available.

---

## 8. Transport-related acceptance and inspection lists (before handed over to the deploying personnel)

Here.**Deployment of users**Execute and retain output:

```bash
uname -m && cat /etc/os-release | head -5
python3.12 -V
java -version
which java
git --version
locale | grep -i utf
df -h
free -h
ulimit -n

# Network
curl -I https://pypi.org/simple/ || curl -I "<Yours.PyPIMirror>"
# curl -I "<LLMIt's...api_base_url>"   # If it is established
```

Check to confirm:

- [ ] Deployment of user-to-code catalogues,workspace Writable
- [ ] `java` Yes.PATH Medium 17
- [ ] PyPI(Or mirrors, which can be large.wheel(catboost ~100MB Level,pyarrow Wait
- [ ] If removed: configuredpip/curl Agency and CompanyCA
- [ ] IfJupyterHub:Ports have been agreed to with`MARVIS_LOCAL_TOKEN` / `MARVIS_TRUSTED_PROXY_HOSTS`
- [ ] The firewall won't stop the station.HTTPS((Acquisition) andLLM Address (Running)
- [ ] UTF-8 locale Enabled

---

## 9. Operational side deployment steps (after environment is ready)

```bash
# 1. Get the code.
cd /opt/marvis
git clone <WarehouseURL> app
cd app

# 2. Environment
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -e .

# 3. Smoke.
java -version
python -c "import fastapi, pandas, lightgbm, xgboost, catboost, duckdb, pypmml; print('ok')"
marvis version

# 4. Start (shared machine must be attached)token)
export MARVIS_LOCAL_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
# export MARVIS_TRUSTED_PROXY_HOSTS=127.0.0.1   # If you're represented
# export RMC_MATERIAL_ROOTS=/data/marvis/materials

marvis serve --host 127.0.0.1 --port 8000 --workspace /data/marvis/workspace
```

Browser or proxy access:`http://127.0.0.1:8000/`(orJupyterHub proxy Path.

Use the built-in command to do not run directly when the service runs`cp` SQLite:

```bash
marvis backup --workspace /data/marvis/workspace --out marvis-backup.tar.gz
```

---

## 10. Frequent failures→ Corresponding operational gaps

| phenomena| I guess I'm missing something.|
|------|------------|
| `pip` Timeout/ SSL Wrong.| PyPI Networks, agents, companiesCA |
| `No matching distribution` / Compiled failed| Python Uncorrect or missing version`python3.12-dev` / `gcc` |
| `pypmml` / JVM Related errors| Not installedJDK 17,or`java` No, I'm not.PATH |
| `libgomp.so.1: cannot open` | Not installed`libgomp1` |
| Importxgboost Pull!`nvidia-nccl-cu12` Failed| PyPI The white list did not release the package (no need to load)CUDA) |
| We can start with someone else who can write the job.| Not set`MARVIS_LOCAL_TOKEN` |
| The long run.proxy The rights are now in disarray.| Not set`MARVIS_TRUSTED_PROXY_HOSTS` |
| Material path denied.| Not set`RMC_MATERIAL_ROOTS` |
| OOM / Process killed.| insufficient memory;or need to be revised downwardsDuckDB / Upload limit|

---

## 11. Fill out the worksheet (take it in when sent to transport)

| Item| Fill|
|----|------|
| Linux Releases and Versions| |
| CPU Structure (Adaptation)x86_64 / aarch64) | |
| Is it possible?JupyterHub / Reverse Agent| |
| Intercept port engagement| Default 8000|
| Code Directory| Example:`/opt/marvis/app` |
| workspace Contents| Example:`/data/marvis/workspace` |
| Catalogue of materials (if any)| |
| PyPI Mirror Address| |
| HTTP(S) Proxy| |
| CompanyCA Certificate Path| |
| LLM `api_base_url` | |
| Deployment of usernames| |
