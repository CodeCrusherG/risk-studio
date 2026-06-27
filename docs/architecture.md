# Risk Studio architecture

This document describes the runtime, module responsibilities, workflow execution, and evidence checks. See the [product roadmap](roadmap.md) for scope and terminology.

### 0.1 Runtime terminology

The runtime uses these terms:

- **Plugin**:Capable of installation or built-in capacity packages (`marvis/packs/*` It's an inner package. Every one.`manifest.json`).
- **Tool**:Plugin Specific action to call inside (`tools.py` Lee.`tool_*` a function that is named.
- **Hook**:Plugin Actions triggered by Platform events (inline)`plugins/hooks.py` It's...`HookDispatcher`,Events like`CONSOLIDATION_TRIGGERS`).
- **Workflow**:Agent Generated, built-in to the platform, or user-readyTool/Hook task series (templates).`orchestrator/templates/*.py` Is an internal template,`orchestrator/templates/skills.py` Loading users can prepare templates.
- **Skill**:SOP/Playbook/Methodological knowledge, written by usersWorkflow Templates — Declaration, only trusted tools, exemplifying`PlanValidator`,**No other.runtime**.

Execution uses plugins, tools, hooks, and workflows. Skills provide declarative workflow templates rather than a separate runtime.

### 0.2 Key environmental variables (local access and isolation switches)

These environment variables are`app.py` / `pipeline.py` The Chinese hard-coded entry is the key to understanding the "local priority" and "separated" borders:

| Variables| Role| Source|
|---|---|---|
| `MARVIS_ALLOW_REMOTE_READ` | Allow Remote Read-onlyAPI(Default level, unsafe method always 403)| `app.py:_remote_read_enabled` |
| `MARVIS_TRUSTED_PROXY_HOSTS` | Trusted Reverse Agent Address (referend header only trust Visible Agent)| `app.py:_trusted_proxy_hosts` |
| `MARVIS_LOCAL_TOKEN` | Shared host hardening: Local reading and writing requirementsBasic / `X-Marvis-Token` | `app.py:_configured_local_token` |
| `MARVIS_ALLOW_LEGACY_LIVE_NOTEBOOK_EXECUTION` | legacy live kernel Three.opt-in One of them.| `pipeline.py:LEGACY_LIVE_NOTEBOOK_ENV_VAR` |

---

## 1. Run the timer (entry and start)

Run the timer is "FastAPI Group Roots+ Two persevering (in the case of theSQLite / DuckDB)+ Separatization process+ Front end monomer.

```
python -m marvis            → marvis/__main__.py It's...main()
  └─ serve(Default Command)→ _serve() → configure_logging() → create_app() → uvicorn.run()
```

### 1.1 Entry and startup file

- `marvis/__main__.py`(644 Lines) -CLI Enter. Suborder:`serve`(And by default, by the order of no son.`validate`(Go straight.V1 Checking the currents,`update`,`version`,`eval-llm`,`backup`,`restore`.`--profile` Pass.`_profile_defaults()` Map tohost/port/workspace(Default`127.0.0.1:8000` + `./workspace`;`dev`→`:8001`;`vN-M`→Port by version number. When detected, the current port isconda base The blog is also available.`serve`/`validate` I'll commission it to the exclusive.conda Environment (%)`_should_delegate_to_dedicated_conda_env`).`_serve()` Eventually.`uvicorn.run(app, ...)`.
- `marvis/app.py`(903 Lines) -`create_app()` It's a global combination root:`init_db`,Various start-upGC/Recovery,`_configure_plugin_runtime()`(assemblyPluginRegistry / ToolRegistry / ToolRunner / HookDispatcher / AgentMemory Scheduler,`_configure_orchestrator()`(assemblyPlanValidator / Planner / Reviewer / IntentRouter / SubAgentDispatcher / PlanExecutor),`reclaim_running_plans`,`sweep_heartbeat_lost_jobs`,`JobHeartbeatWatchdog` Wait for the doordogs, register 27`include_router`,Mount`/static`,Definitions`/api/health`,`/`,`/branding/assets`,The first is the use of the Internet to create a new version of the Internet.`_static_asset_version` / `_static_import_map`,Cache Key Overwrite All`*.js`/`*.css`).Two.`http` Middle:`_local_access_guard`(Local/Remote access to borders+ Shared Hosttoken)and`_static_cache_control`(`?v=` One year.immutable,Otherwise...no-cache).
- `marvis/api.py`(186 Lines) - Old`/api` group root. Document string specifies:validation-agent It's...HTTP Group logic pressedARCH-1 Move to`marvis/agent/validation_app_service.py`,This paper only retains compatibilityre-export(Mass`_xxx = _vas.xxx`),For old tests/Extension point import. New code should be directimport The leaf module.
- `marvis/routers/`——24 individualrouter Modules (see§2.4).And then there's something else.`marvis/operations/router.py` and`marvis/production_governance/router.py` Two are not here.`routers/` Downrouter,Add`api.py` It's...`/api` The root of the combination,`app.py` Total`include_router` 27 - Second.

### 1.2 Enduring

- `marvis/db.py`(47 Lines - purere-export Door: From`db_schema` and`repositories/*` Transfer`init_db`,`connect`,`sqlite_health`,Each`*Repository`,Hold on.`from marvis.db import ...` history import face.
- `marvis/db_schema.py`(4,609 Lines) -SQLite schema and migration (in the case of`SCHEMA_VERSION`,`_ensure_column`,`_MIGRATION_TABLES` , and so on. The table covers`tasks`/`jobs`/`plans`/`plan_steps`/`datasets`/`strategies`/`llm_calls`/`audit` Wait.
- `marvis/agent_memory_schema.py`——Agent The independence of memory.schema,By`db_schema` Creates it at initialization.
- `marvis/data/backend.py`——DuckDB It's...`DataBackend`(Workspace-level backend to data set,`duckdb_health` ) is used to create new connections instead of sharing default connections.

### 1.3 Frontend

`marvis/static/`:`index.html` + Styles (Phone)`css/`,`styles.css`)+ FrontendJS.JS 3-Step: Mono-System`app.js`(8,382 Lines, first round of break-ups`js/`(31 1 module, 6,409 Okay.V2 It's undiscovered.`js/v2/`(32 1 module, 18,937 All right.`app.py` It's...`/` Routes with static version numbersimport-map Injection`index.html`,Achievedcache-busting.

---

## 2. Module boundary

Each section identifies the module responsibilities, principal files, and boundaries.

### 2.1 `validation/` —— Validation algorithm

- Duties: Validation of the kernel for validation of the model: sub-boxes (infra).`binning.py`),KS/AUC/PSI and other platform indicators (in thousands of US dollars)`platform_metrics.py`,The entrance.`compute_platform_validation_results`),PMML Rating (%2)`pmml_scoring.py` / `pmml_score_artifacts.py`),Recoverability (%)`reproducibility.py`),Memory Model Scores (%2)`in_memory_scores.py`),Pressure test (Performance test)`stress_test.py` / `pmml_stress.py`),Vintage(`vintage.py`),Type of result (%)`results.py` It's...`ConsistencyStatus` Wait.
- Validation kernels are independent of the database, HTTP layer, agent, and task lifecycle.

### 2.2 `output/` —— From Structurepayload Rendering Document

- Duties: Structuralizationpayload Render asExcel/Word/chart.`excel.py`,`word.py`,`strategy_report_bundle.py`(The strategy report, in the fourth format, is projected. See you.§3),`xlsx_safety.py`,`styles.py`.
- Key constraints:`strategy_report_bundle.py` Document string claims to be "renderer,No, it's not.analysis layer],It checks out the authentication.bundle Back-up.**The same fact.**ProjectionJSON/Markdown/XLSX/DOCX.
- Report renderers consume structured results; they do not execute uploaded plugins or recalculate metrics.

### 2.3 `pipeline.py` + `pipeline_*` —— V1 Verify flow line organization

- Duties:V1 Model validation three-stage presentation`notebook → metrics → report`.Entry:`run_notebook_stage`,`run_metrics_stage`,`run_report_stage`,`run_staged_pipeline`,`run_pipeline`.`PipelineSettings` Yes.frozen dataclass(Ham`notebook_isolated_execution`,`allow_legacy_live_notebook_execution`,See§4.3).
- File Structure (self-speeched by document string)ARCH-6 Split:`pipeline.py`(2,324 Okay, phase entrance.+ Bymonkeypatch The name must be here.`pipeline_errors.py`(`PipelineError`/`PipelineCancelled`),`pipeline_cellgen.py`(IntoNotebook It's...cell Source generation,`pipeline_io.py`(Path resolution, sample loading, product hygiene,`pipeline_memory.py`(Press`auto_distill` Policy capture successful/Loser.agent Memory.
- Not to own: does not carry the authentication algorithm (twice) per se`validation/`),UnmountHTTP.

### 2.4 `api.py` + `routers/` —— HTTP Layer

- Duties:HTTP Routes, mission creation,active job,Frontendpayload.`routers/` Split by domain:`data.py`,`tasks.py`,`plans.py`,`modeling.py`,`plugins.py`,`artifacts.py`,`agent_memory.py`,`validation_agent.py`,`validation_batches.py`,`validation_contracts.py`,`validation_stages.py`,`scans.py`,`reports.py`,`evidence.py`,`drafts.py`,`audit.py`,`llm.py`,`skills.py`,`materials.py`,`stage_controls.py`,`strategy_candidate_lab.py`,`branding.py`,`data_analysis.py`,`report_fields.py`.`app.py` Reycérouter There's another one in the row.`api_*_helpers.py` / `api_schemas.py`(78,995 Bytes, Request/Responseschema)Support layer.
- HTTP handlers delegate validation calculations to the validation modules and validation-agent coordination to `agent/validation_app_service.py`.

### 2.5 `static/` —— Frontend

- Duties: based onAPI payload Renders the front-end state.`js/` It's generic./First-round split module (`api.js`,`state.js`,`polling.js`,`metric-tables.js`,`render-agent.js` The blogger adds:`js/v2/` Yes.V2 Workstation module (Phone module)`plan_rail_controller.js`,`strategy_candidate_lab_*`,`data_workspace_*`,Eachgate controller Wait.
- The frontend renders structured API state; free-form backend text does not establish a calculated result.

### 2.6 `agent/` —— Intent, plan drivers and task levelsturn loop

- Duties: intention to identify, interpret, summarize, draft,PlanDriver and task levelAgent turn loop.
- `plan_driver.py` —— [One.driver Service AllV2 Generic plan dialogue driver: by template+Filledslot Construction plan, real.`PlanExecutor` Up and running, meet.`needs_confirmation` gate And then you can turn the output from the last step to the output.append-only assistant The news is that**Yes.gate Pause before step**,User confirms that it's just finished. Document string claims to be "pure-ish]:Change your schedule.repo/executor,But...**Back**The message is not durable, and it is easy to be offline and single.
- `turn_handlers/`(Package, original 17,868 Line single physical split, see§6)——Type of taskturn Handle the entrance, pressworkflow lane Split to 17 drive files (in %2)`_shared`/`join`/`feature`/`modeling`/`vintage`/`portfolio`/`strategy_*`/`c1`/`typed_ui` Wait+ `_registry`,By`__init__.py` Here.exec-merge The sequence of the method is inserted into a single named space (Run-time syntax corresponds to the original body, includingmonkeypatch).`DRIVER_AGENT_TASK_TYPES`(data_join / feature_analysis / modeling / strategy / vintage / portfolio)Let's go.driver The government is not going to be able to control the situation.validation Go on, get on your own.scan/notebook Flue.
- `strategy_request_compiler/`(Package, original 14,449 Line single physical split, see§6)——Strategic Natural Language Compiler, to be broken down by the requested family to 10 drive-by files (`core`/`sample_design`/`tree`/`cross`/`voting`/`pool`/`impact`/`scorecard`/`model_evidence`/`refinement_report`),Same thing.exec-merge Injection; public face (`__all__` 29 The document is identical to the original document. See§3.
- `strategy_workflows/`——Standard policyworkflow Contents`_catalog.py`,`_univariate_scorecard.py`,`_tree_workflows.py`,`_pool_workflows.py`,`_foundation_delivery.py` (and other)`resolve_strategy_request` / `prepare_strategy_plan`.
- `gates/`——gate Adaptive Layer (Female)`adapters.py`,`contracts.py`),Complement`gate_execution_adapter.py`,`gate_param_schema.py`,`gate_response_adapter.py`.
- Other:`service.py`,`validation_app_service.py`(ARCH-1 Service level,`validation_service.py`,`validation_runner.py`,`validation_stages.py`,`semantic_authorization.py`,`instruction_router.py`,`renderers.py`,`presenters/`,Each`*_setup.py`(`strategy_setup.py`/`modeling_setup.py`/`feature_setup.py` Wait.
- The agent plans and explains work. Platform tools calculate metrics and retain the supporting evidence.

### 2.7 `agent_memory/` —— Memory storage/Search/Compression/Audit

- Duties:`store.py`(`AgentMemoryStore`),`capture.py`(`save_memory_candidate`),`retrieval.py`,`consolidation.py`(`ConsolidationScheduler`,ByHook The event triggers,`distillation.py`(`DistillationEngine`),`evolution.py`(`EvolutionManager`),`extractors.py`,`models.py`,`policy.py`(Red Line Classification, see§5.3),`api_support.py`,`prompting.py`.
- Memory supports explanations, recommendations, and review context; it cannot change task metrics.

### 2.8 `plugins/` + `packs/` —— Plugin/Tool/Hook runtime and capacity kit

- `plugins/`(runtime):`loader.py`(`load_builtin_packs`/`sync_builtin_packs`),`registry.py`(`PluginRegistry`/`ToolRegistry`),`runner.py`(`ToolRunner`,2,175 Okay, tool execution.+ And Hashi./receipt),`manifest.py`,`schema_validation.py`,`contracts.py`,`hooks.py`(`HookDispatcher`),`sdk.py`,`subprocess_worker.py`(The tool subprocess is isolated.
- `packs/`(Identified capability package, each one.`manifest.json` + `tools.py`):`data_ops`,`feature`,`modeling`(Max.`train_tools.py`/`prepare_tools.py`/`score_evidence_tools.py`/`tune_*.py`/`recipes/` Wait, wait, wait, wait.`strategy`(Largest and most finest, including`sample_design*.py`,`candidate_evidence.py`,`backtest.py`,`pool_*.py`,`interactive_tree_*.py`,`report_bundle.py`,`dsl.py` Wait, wait, wait, wait.`analysis`,`v1_compat`,`risk_analysis`,`labeling`,`drafts`,`_sample`.
- Shouldn't have:Plugin I'm not holding it myself.DB Life cycle;`packs/strategy` The evidence contract is clear "that only development evidence is described and cannot be used to claim authentication/"Accept, not lasting."

### 2.9 `data/` —— DuckDB Data backend and dataset processing

- Duties:`backend.py`(DuckDB `DataBackend`),Import`csv_ingest.py`/`excel_ingest.py`/`schema_infer.py`),`join_engine.py`,`transforms.py`/`transform_semantics.py`,`sampler.py`,`profiler.py`,`registry.py`(Dataset Registration and`content_hash`),`fingerprint.py`,`workspace.py`,`data_dictionary.py`,`dedup.py`/`align.py`,`label_construction.py`/`labels.py`,andGC(`dataset_source_gc.py`/`task_filesystem_gc.py`/`validation_batch_upload_gc.py`).
- Should not have: not load workflow layout (it is)orchestrator/agent Something.

### 2.10 `repositories/` —— Data access layer by domain

- Duties:SQLite Data access, one per domainRepository:`tasks.py`(`TaskRepository`),`datasets.py`,`plans.py`,`plugins.py`,`strategy.py`,`drafts.py`,`modeling.py`,`audit.py`,`llm_calls.py`,`validation_contracts.py`,`validation_batches.py`,`data_workspace.py`,`task_artifacts.py`,`strategy_*.py`(Multiple policy sub-areas) etc.`db.py` Turn out the main entrance.
- Not owned: Business algorithms andHTTP(Just lasting.

### 2.11 `governance/` —— maker/checker Governance

- Duties:`repository.py`(`GovernanceRepository`,Ensorted Localsession/TTL),`service.py`(`GovernanceService`,The tool binding is authorized to resolve,`contracts.py`,`errors.py`(`AuthorizationError`).`app.py` On startupreconcile,And put`governance_service` Injection`ToolRunner`/`PlanExecutor` As`authorizer`/`binding_resolver`.

### 2.12 `production_governance/` —— Production activated evidence.

- Duties:`evidence.py`(`ActivationEvidenceVerifier`),`repository.py`,`router.py`,`errors.py`.`create_app` Accept`production_activation_verifiers` Injection (injection)`app.state.production_activation_verifiers`).Path`/api/production-governance` By`_is_local_only_path` Be classified as local exclusive.

### 2.13 `decision_twin/` —— Counterfact/Re-show the sandbox.

- Duties:`replay.py`,`comparison.py`,`reconciliation.py`,`_canonical.py`,`artifacts.py`,`authenticated_entry.py`,`contracts.py`.PlannedB-11 Product it (see§6 ) , this document does not expand its details.

### 2.14 `operations/` —— Monitor/Schedule Time

- Duties:`router.py`,`scheduler.py`(`MonitoringExecutor`),`integration.py`(`build_operations_runtime`,Injection`app.state.operations_runtime`),`notifications.py`,`repository.py`,`contracts.py`,`schema.py`.`create_app` Accept`operations_executor_allowlist` White list.

### 2.15 `orchestrator/` —— Scheduled time

- Duties: to insert "declaration"Workflow Other Organiser`Plan` and progressively implement.
  - `contracts.py`——`Plan`/`PlanStep`/`StepStatus`/`PlanStatus`/`plan_fingerprint` The core type.
  - `templates/`——Internal Templates (`strategy.py`,`validation.py`,`modeling.py`,`feature.py`,`join.py`,`portfolio.py`,`monitoring.py`,`sample.py` Wait+ `skills.py`(`load_user_skill_templates`,User-readyWorkflow Template source.
  - `validator.py`——`PlanValidator`:Verifytool Quoted,`{slot:...}` placeholder,`post_checks`(`schema`/`range`/`rowcount`/`invariant`/`nonempty`/`match_rate`/`one_of`)And the indicator is safe.`orchestrator/safety.py` It's...`METRIC_FIELDS`).
  - `executor.py`——`PlanExecutor`:Progressive implementation, citation,`needs_confirmation` gate Timeout,canonical Results authentication (%1)`canonical_results.py`),Retry and Failed (Recovery)`plan_recovery.py`).
  - Other:`planner.py`(`Planner`,LLM (a) Generating the plan,`reviewer.py`(`Reviewer`),`intent.py`(`IntentRouter`),`subagent.py`(`SubAgentDispatcher`),`harness_state.py`,`evidence.py`(`artifact_refs`/`payload_hash`),`references.py`,`capability.py`((a) the capability hierarchy,`context/`(Budget/Account books/Watch.`eval/`(`eval-llm` Evaluationharness).

### 2.16 `notebooks.py` / `notebook_worker.py` —— Isolation.

- Duties:Jupyter Notebook The session and the quarantine execution.`notebooks.py`(1,810 (lines) Management`NotebookExecutionSession`,`register/get/close_live_notebook_session`,`prepare_execution_notebook_v3`,`run_notebook(isolated=...)`,`_run_notebook_in_subprocess`(`subprocess.Popen` Start`marvis.notebook_worker`,`start_new_session` Step out of process group)`NOTEBOOK_RESULT_SENTINEL` Mark.`notebook_worker.py`(84 ) is a child processworker:Fromstdin Read it.job JSON → `run_notebook(... isolated=False)` → Here.sentinel+UTF-8 Original Byte Retrievalstdout.The contract level is in.`notebook_contract.py`(747 Okay, see you.§4.1).
- Notebook isolation uses a subprocess whose worker creates its own kernel. `notebook_isolated_execution` selects this path; the legacy live-kernel option is described in section 4.3.

### 2.17 Adjacent module (this task is not separate, but new readers are often encountered)

- `marvis/artifacts/`——governedtask artifact Abstract:`__init__.py`(`ArtifactUnitOfWork`),`model_score_vector.py`(Score vector+ Hash's retesting,`recovery.py`(`reconcile_workspace_artifacts`,(b) Reconciliation at start-up,`transactional.py`.
- `marvis/drafts/`——Subsystem for Draft Reports:`registry.py`(`DraftRegistry`),`sandbox.py`(`DraftSandbox`),`authoring.py`,`promotion.py`,`learning.py`,`language.py`,`tools.py`,`web_search.py`.`app.py` assembly`DraftRegistry`/`DraftSandbox`.
- `marvis/feature/`——Feature Project Pure Algorithm (Prem)`binning.py`,`iv.py`,`correlation.py`,`univariate.py`,`weighted_rule_tree.py`,`preprocessing.py`,`screen.py` I'm not sure I'm gonna be able to do this.`packs/feature`(The latter is...Tool Packaging, the former being the algorithmic body).
- `marvis/workspace/`——Run-time workspace directory (%2)`datasets/`,`tasks/`,`plugins/`,`logs/`,`marvis.sqlite`,`plugin_admin_token`),By`settings.py` It's...`Settings` Positioning, non-code.
- Top layer support module:`domain.py`(`TaskStatus`/`TaskRecord`/`FileArtifact` Area type,`state_machine.py`(`IllegalTransition`,`app.py` Captured to 409,`files.py`(`sha256_file`/`write_json_atomic`/`scan_source_dir`),`llm_client.py`(`OpenAICompatibleLLMClient`),`llm_prompts.py`(77,089 Bytesprompt Text,`llm_settings.py`(Model resolution,`api_schemas.py`(Request/Responseschema),`safe_paths.py`(Path escape protection,`redaction.py`,`reconcile.py`.

---

## 3. One.workflow End-to-end data stream (policy development as an example)

For example, the Natural Language Strategy Development Request is linked to the following (each link has a corresponding code file):

1. **Natural Language Request** → Task levelAgent turn loop(`agent/turn_handlers/` Distribution of packages+ `agent/plan_driver.py` It's...driver).The strategic task is`DRIVER_AGENT_TASK_TYPES` One, go.driver Chemically planned stream (in thousands of years)manual andagent Both models go through.agent Endpoints;agent Mode byLLM Operation control,manual Mode is user-operated.
2. **Intent to compile** → `agent/strategy_request_compiler/` The bag.`compile_strategy_request`:LLM Just translate one sentence into one sentence.draft,This module is then fixed by a wordlist (in the following way):`STRATEGY_OPERATIONS` / `STRATEGY_TYPES` / `STRATEGY_REQUEST_KINDS`),Strategy DSL(`packs/strategy/dsl.py` It's...`parse_strategy_spec`),Dataset White List to Verifydraft.Document string clear:**It doesn't execute any.tool,And I'm not going to accept the model's indicators.**.
3. **workflow Parsing and Plan Generation** → `agent/strategy_workflows/__init__.py` It's...`resolve_strategy_request` / `prepare_strategy_plan`:Resolve the compilation results to standardworkflow(fresh/replay/legacy Three, then by`orchestrator/templates/strategy.py` It's...`WorkflowTemplate` The example is turned to a belt.`post_checks` It's...`Plan`.
4. **Schedule Validation** → `orchestrator/validator.py` It's...`PlanValidator`:Verifytool Quoted,slot Placeholder, every step`post_checks`(Scope/Non-empty/The following are the indicators of the indicator security rules:
5. **Planned implementation** → `orchestrator/executor.py` It's...`PlanExecutor`:Progressive implementation, adoption`plugins/runner.py` It's...`ToolRunner` Call`packs/strategy/*` tools; in`needs_confirmation` gate Suspended before forward, and the output just calculated in the previous step is translated into confirmation messages.
6. **Evidence outputs** → `packs/strategy` The purpose of the tool is to provide a source of information on the content of the tool ' s outputs, and to provide evidence of certainty (e.g.,`candidate_evidence.py` It's...`StrategyCandidateEvidence`,`sample_design_v2.py` It's...`StrategySampleDesign`),The platform code calculates the indicators.LLM Just explain./Summary/Drafting.
7. **IV. Format report** → `packs/strategy/report_bundle.py` Generate**Custom**It's...`StrategyReportBundle`(`report_id` and`content_sha256` By RegulationJSON Recalculate)`output/strategy_report_bundle.py`(renderer)Projection to four formats:**canonical JSON,Markdown,No FormulaXLSX,No MacroDOCX**.Missing values remain blank and their type-usable availability and cause remain in the evidence index.

`PlanExecutor` pauses before steps marked `needs_confirmation`. `plan_driver.py` presents the preceding step's recorded output in the conversation; confirmation resumes execution. Manual and agent modes use the same driver for supported workflows. Manual model validation retains its separate scan/Notebook path.

Data stream wrapping:

```
Natural languages→ strategy_request_compiler(Compile+Check, no.LLM (Indicators)
        → strategy_workflows.resolve(fresh/replay/legacy)
        → templates/strategy.py(WorkflowTemplate → Plan)
        → PlanValidator(tool References+ post_checks + (indicator security)
        → PlanExecutor(ToolRunner Tranquilitypacks/strategy Tools,gate (Previously suspended)
        → packs/strategy Evidence (content location, platform calculation indicators)
        → StrategyReportBundle(# Self-Accreditation #→ output/strategy_report_bundle((Four formats)
```

### 3.1 Model validationV1-compat Path (parallel briefly)

- `orchestrator/templates/validation.py` Definitions`MODEL_VALIDATION` Template, step in order`scan_materials` → `run_notebook` → `compute_validation_metrics` → `render_reports`,tool All points to`v1_compat` Pack, and bring`post_checks`(`status` Value,`ks`/`auc` It's...`0..1` Scope,`psi` It's empty.
- `packs/v1_compat/tools.py` These.tool and beyond:`tool_run_notebook` Tranquility`pipeline.run_notebook_stage`,`tool_compute_validation_metrics` Tranquility`pipeline.run_metrics_stage`,`tool_render_reports` Tranquility`pipeline.run_report_stage` —— That's what I'm talking about.`pipeline.py` It's...V1 Phase three, wrapper.orchestrator Organizedtool.
- And so...V1-compat Path= **orchestrator Templates→ v1_compat Tools→ pipeline Phase three.→ validation/ Accuracy algorithm→ output/ Render**,andnative The same policy path is shared.PlanValidator/PlanExecutor Run time.

---

## 4. Compatible borders

### 4.1 Notebook Contract (in %)`RMC_*`)

Notebook Four names must be defined in the top level domain before implementation is completed (`notebook_contract.py` UseAST Individually, missing or wrongly reported:

- `RMC_SAMPLE_DF`:pandas DataFrame,Platform for fractional consistency,KS,PSI,A box, original sample of the pressure test; it must be visible at the top level and not only in the function area.
- `RMC_TARGET_COL`:Target listed string.
- `RMC_ALGORITHM`:Algorithm (e. g.)`"lgb"`).
- `RMC_SCORE_FN(df)`:Callable, ReceivedDataFrame,Returns a 1-dimensional numerical fraction of length equal to the number of rows.

Authorization documents:[notebook_contract.md](./notebook_contract.md)(The Platform's operational compacts are summarized below.[notebook_submission_requirements.md](./notebook_submission_requirements.md)(The following is a list of the most recent submissions by the Modellers:`RMC_FEATURES` obsolete;code model andPMML The conversion should be done by taking the same original sample.

### 4.2 Notebook Memory Scoresvs PMML min

The main score is consistent with the**Notebook Model score in memory`RMC_SCORE_FN(sample_df)` vs Proposed commissioning in the table of contentsPMML ♪ And the score ♪**(`validation/in_memory_scores.py` and`validation/pmml_scoring.py` / `pmml_score_artifacts.py` It's...`build_pmml_scoring_identity` / `validate_pmml_score_artifact`).Notebook Extra ExportPMML As audit material, but no new export from the platformPMML As the main object of comparison.

### 4.3 legacy live kernel Three.opt-in

`pipeline.py` It's...`legacy_live_notebook_execution_allowed()` Request**Three satisfy both.**I'll let you do it.legacy live kernel Implementation:

1. `PipelineSettings.notebook_isolated_execution == False`(Default`True`);
2. `PipelineSettings.allow_legacy_live_notebook_execution == True`(Default`False`);
3. Environmental variables`MARVIS_ALLOW_LEGACY_LIVE_NOTEBOOK_EXECUTION=1`.

Any non-fatisfactory rule`_require_legacy_live_notebook_execution` Throw!`PipelineError`,Error Text`LEGACY_LIVE_NOTEBOOK_DISABLED_MESSAGE` Lists three requirements precisely. Default path-step processes are isolated (§2.16).

### 4.4 legacy vs native sample design Double Track

- `packs/strategy/sample_design.py`——V1 It's...`StrategySampleDesign`:Single border, content location, freeze "materialized"active dataset The border is defined by the following:
- `packs/strategy/sample_design_v2.py`——V2 Contract: in the same exact analysisuniverse Freeze Up**approval andrisk Two crowds.**,Hold each otherdevelopment/validation/OOT Member quotes; accepting only 'certified 'membership header + Parsed Booleansmask + "Calculated Numerical Statistics" not ownedDB/DataFrame Filter/Tool/Agent.
- Implementation of the border:`sample_design_v2_native_tools.py` Document string labeled "Native active-dataset execution boundary]——That's...native The path is straight.active dataset (a) Calculation;`sample_design_v2_tools.py` It's shared. The two are made up together."legacy((Performance)vs native(active-dataset The government has also been monitoring the situation.

---

## 5. Trust mechanisms

### 5.1 hash / provenance / Retest Before Drop

- `provenance.py`:`NumberProvenance` It's the minimum trace four.`(dataset_fingerprint, code_version, params_digest, seed)`,The decision-making figures that are in front of everyone are the answer to "Where are you from?"`dataset_fingerprint` Reuse`data/registry.py` It's...sha256 `content_hash`,`params_digest` Reuse`orchestrator/executor.py:_payload_hash` the Convention on the Elimination of All Forms of Discrimination against WomenJSON Hash promised.
- **Retest Before Drop**(Recalculate before accept, not trust in the field:`packs/strategy/report_bundle.py` It's...`validate_strategy_report_bundle` It's from the norm.JSON **Recost** `report_id`(`strategy-report-` + body Hashi ex 24 bit)`content_sha256`,Again.`hmac.compare_digest` Compare, match or throw.`StrategyReportBundleError`.Same "Hol-Hashi"+ `hmac.compare_digest`]Present`routers/artifacts.py`(Next issueartifact Pre-match`content_hash`),`download_snapshot.py`(The photo was printed while the photo was printed.`artifacts/model_score_vector.py`(Hashi's been examined, and he's been replaced during the hashi's period.`plugins/runner.py`(`_payload_hash` / `_manifest_receipt_hash` / `result_hash`).
- **Evidence envelope (Evidentiary envelope)evidence envelope)**:`orchestrator/evidence.py` Provision`payload_hash`,`artifact_refs`,`dataset_refs`,`artifact_bindings`,`result_dataset_ids`,`executor.py` Use it to hit every step of the output.`input_hash` and the list of references.`provenance.py` It's...`params_digest` and`executor.py:_payload_hash` Keep the same norm Hashi as agreed, and the two are comparable (see para.`provenance.py` Document string clear "matches marvis/orchestrator/executor.py:_payload_hash]).

### 5.2 fail-closed Practice

- `canonical_results.py`:`authenticate_canonical_result` It's governed.canonical tool (b) The resulting trust gates;`CANONICAL_RESULT_TOOLS` Return Outside`False`,canonical You don't match the same one.**Singlefail-closed Unusual**,The caller cannot downgrade it to "Presentity-Filter-Filter-Filter."
- `app.py` It's...`_local_access_guard`:Non-local and unauthorised requests, non-safe methods, 403;`_is_local_only_path`(Ham`/api/settings`,`/api/operations`,`/api/production-governance` (e) All-telemetry 403; forward header only trust in visible configuration`MARVIS_TRUSTED_PROXY_HOSTS`,I don't believe it.loopback Forward headers to the endfail-closed.
- `strategy_adoption.py` It's...`normalize_adoption_reason`:When a placeholder to be determined is encounteredfail-closed(Document String "fail closed on pending placeholders]).

### 5.3 agent_memory Red Line (Closed What)

`agent_memory/policy.py` filters candidate and distilled memories through `classify_memory_candidate` and `classify_distillation_payload`. It rejects raw customer records, identity details, Notebook source, model and PMML contents, credentials, database connections, private report text, and absolute local paths. `MEMORY_CANDIDATE_TEXT_MAX_CHARS = 12000` and `PAYLOAD_FIELD_ALLOWLISTS` bound permitted content.

### 5.4 Identification indicators attributed to Platform code

`validation/platform_metrics.py:compute_platform_validation_results` calculates KS, AUC, PSI, score consistency, and other validation metrics. The agent interprets requests, plans work, explains results, and drafts text from recorded evidence; model-generated values are not accepted as calculated metrics.

---

## 6. Structural debt and fragmentation (status quo and direction)

**2026-08-14 UpdateB-4/B-6 Landed)**:Two mega-documents were physically split at the time of writing in this section:

- `marvis/agent/turn_handlers.py`(17,868 Line→ `marvis/agent/turn_handlers/` Package: 17 drive-by files+ `_registry`,`__init__.py` Here.exec-merge Designed to inject the driveway source code into a single named space in a dependent order - the syntax of running is fully consistent with the original body (name resolution, name interpretation,monkeypatch (b) 865 tests passed,ruff Clean.
- `marvis/agent/strategy_request_compiler.py`(14,449 Line→ `marvis/agent/strategy_request_compiler/` Package: 10 family lanes requested, sameexec-merge;`__all__` Consistent with original document by name (29), relevant 1,993 Test passed (1 test factor)`inspect.getsource` Reads the module source code and migrates to read the combined drive code, which remains the same.
- `marvis/static/app.js`:8,465 → 8,382 All right.B-6 Verification findings:`static/js/` The modules are...**A deliberate thinly adapted layer.**,No real duplicates with a single body; only the confirmation code (14 functions, 5 unused) is deleted from this cycleimport),507 A front end static test passed.

**Remaining structural debt (as it is)**:

- `marvis/static/app.js` Still about 8.4k It's okay.JS Mono-body, the largest single file at present; continued enrichment requires functional migration rather than deletion.
- Largest driveway file after split:`turn_handlers/strategy_turns.py`(About 3.0k Okay.`turn_handlers/strategy_candidates.py`(About 4.5k Okay.`strategy_request_compiler/core.py`(About 2.7k Okay.`pool.py`(About 2.5k Okay.`tree.py`(About 2.4k Line) - still subdivided in lanes but no longer crossworkflow - The monomer.
- `.bandit-baseline.json` 83 acceptedfinding(Subject isB608 f-string SQL),B-5 Baselines have been re-established and incremental gates added.`docs/reviews/2026-08-13-bandit-baseline-review.md`.

Split direction and execution records to[2026-08-13-next-90-days-development-plan.md](./superpowers/plans/2026-08-13-next-90-days-development-plan.md) Then, this paper will only state the status quo.

## 7. Read-entry guide

If you want to understand a subject, read these documents in the following order (paths versus warehouse roots),`marvis/` Prefix omission`marvis/` Next:

| Theme| Read first (in order of order, i.e., recommendation)|
|---|---|
| How the process is started and how it is assembled| `marvis/__main__.py` → `marvis/app.py` → `marvis/settings.py` |
| HTTP Layers and routers belong to| `marvis/api.py` → `marvis/routers/tasks.py` → `marvis/routers/validation_agent.py` |
| Sustainability andschema | `marvis/db.py` → `marvis/db_schema.py` → `marvis/agent_memory_schema.py` |
| V1 Validation of current lines| `marvis/pipeline.py`(Read modules firstdocstring)→ `marvis/pipeline_errors.py` → `marvis/pipeline_cellgen.py` → `marvis/pipeline_io.py` |
| Validation algorithm| `marvis/validation/platform_metrics.py` → `marvis/validation/results.py` → `marvis/validation/pmml_scoring.py` |
| Notebook Implementation and compacts| `marvis/notebook_contract.py` → `marvis/notebooks.py` → `marvis/notebook_worker.py` → `docs/notebook_contract.md` |
| Scheduled time| `marvis/orchestrator/contracts.py` → `marvis/orchestrator/templates/strategy.py` → `marvis/orchestrator/validator.py` → `marvis/orchestrator/executor.py` |
| Plugin/Tool runtime | `marvis/plugins/registry.py` → `marvis/plugins/runner.py` → `marvis/plugins/manifest.py` → `marvis/packs/strategy/manifest.json` |
| Policy to End| `marvis/agent/strategy_request_compiler.py`(Read the head.docstring)→ `marvis/agent/strategy_workflows/__init__.py` → `marvis/packs/strategy/report_bundle.py` → `marvis/output/strategy_report_bundle.py` |
| Agent turn loop anddriver | `marvis/agent/plan_driver.py` → `marvis/agent/driver_turn.py` → `marvis/agent/turn_handlers.py` |
| Memory and Red Line| `marvis/agent_memory/store.py` → `marvis/agent_memory/policy.py` → `marvis/agent_memory/consolidation.py` |
| Governance and delegation of authority| `marvis/governance/service.py` → `marvis/governance/repository.py` → `marvis/production_governance/evidence.py` |
| Trust and traceability| `marvis/provenance.py` → `marvis/canonical_results.py` → `marvis/packs/strategy/report_bundle.py`(`validate_strategy_report_bundle`) |
| Compatible borders| `marvis/notebook_contract.py` → `marvis/pipeline.py`(`legacy_live_notebook_execution_allowed`)→ `marvis/packs/strategy/sample_design_v2_native_tools.py` → `marvis/packs/v1_compat/tools.py` |
| Frontend| `marvis/static/app.js` → `marvis/static/js/api.js` → `marvis/static/js/state.js` → `marvis/static/js/v2/plan_rail_controller.js` |
