# Document-Code Consistency Verify (Cluster Consistency)architecture.md / capability-status.md)

- Date: 2026-09-03
- Scope:`docs/architecture.md` (a) A full mechanically verifiable scale and code semantic assertions;
  `docs/capability-status.md` Number of individual measurements by module
- Nature of conclusions:**Read-only audit**.No code changes, only product is in this document
- Conclusion: 34 claims**32 Number of hits, 2 inaccuracies**(Organisation`architecture.md` §5.1)

## 1. Checking the baseline: triple-state comparisons

The verification is preceded by a determination of "the code that you see when you write the document" or else you cannot distinguish between two completely different types of deviations.

```text
git log --diff-filter=A -- docs/architecture.md
  → a3580695  (docs: record 90-day plan execution status, architecture, audit, capability matrix)
git branch --show-current
  → feat/validation-module-upgrade  (HEAD = 45c83aa2,Yes.main Up 1doc-only commit)
```

`a3580695` Both documents introducedcommit,Exactly.`main` It's...HEAD.Therefore:

| Comparison| Nature of deviation|
|---|---|
| Document Value≠ HEAD Value| **The document was wrong.** |
| HEAD Value≠ Workspace value| Failure to submit changes**Code Floating**,No document ever|
| Document Value= HEAD Value= Workspace value| Unanimously|

This benchmark is applied to all decisions in this report. Note that 69 documents are available in the current working area.+4477/−653 Line Unsubmitted Changes
(Branch`feat/validation-module-upgrade`),Therefore, the difference between the " workspace value " and " document value " does not mean that the document is not authentic.

## 2. Accurate hit list (32 items)

### 2.1 Document size assertion (11)/11 Yes.HEAD (As agreed)

| Documentation| Document Name| HEAD | Workspace| Decision|
|---|---:|---:|---:|---|
| `marvis/__main__.py` | 644 | 644 | 644 | Unanimously|
| `marvis/app.py` | 903 | 903 | 903 | Unanimously|
| `marvis/api.py` | 186 | 186 | 186 | Unanimously|
| `marvis/db.py` | 47 | 47 | 47 | Unanimously|
| `marvis/db_schema.py` | 4609 | 4609 | 4609 | Unanimously|
| `marvis/pipeline.py` | 2324 | 2324 | **2351** | HEAD - Yes, sir. - Workspace.+27 |
| `marvis/plugins/runner.py` | 2175 | 2175 | 2175 | Unanimously|
| `marvis/notebooks.py` | 1810 | 1810 | 1810 | Unanimously|
| `marvis/notebook_worker.py` | 84 | 84 | 84 | Unanimously|
| `marvis/notebook_contract.py` | 747 | 747 | 747 | Unanimously|
| `marvis/static/app.js` | 8382 | 8382 | **8858** | HEAD - Yes, sir. - Workspace.+476 |

### 2.2 §6 Number of lanes where debts are split (5)/5,The document gives you about, and it's all in the range.

| Drive file| Document approximate| Actual|
|---|---:|---:|
| `turn_handlers/strategy_turns.py` | ~3.0k | 3014 |
| `turn_handlers/strategy_candidates.py` | ~4.5k | 4551 |
| `strategy_request_compiler/core.py` | ~2.7k | 2704 |
| `strategy_request_compiler/pool.py` | ~2.5k | 2549 |
| `strategy_request_compiler/tree.py` | ~2.4k | 2401 |

### 2.3 Frontend and Bytes (4)/4)

| Item| Document Name| HEAD Actual|
|---|---:|---:|
| `static/js/` Module/ Lines| 31 / 6409 | 31 / 6409 |
| `static/js/v2/` Module/ Lines| 32 / 18937 | 32 / 18937 |
| `llm_prompts.py` Bytes| 77,089 | 77,089 |
| `api_schemas.py` Bytes| 78,995 | 78,995 |

### 2.4 Code semantic assertion (12)/12)

| Document assertion§ | Code Position| Decision|
|---|---|---|
| §4.1 RMC Four Compacts (`RMC_SAMPLE_DF`/`RMC_TARGET_COL`/`RMC_ALGORITHM`/`RMC_SCORE_FN`) | `notebook_contract.py:15-18` | Unanimously|
| §4.1 `RMC_FEATURES` Observed| No more contract list| Unanimously|
| §4.3 legacy live kernel Three.opt-in | `pipeline.py:233-236`,Three logical equals and one is not possible.| Unanimously|
| §5.1 `NumberProvenance` Four-member group| `provenance.py:73-79` | Unanimously|
| §5.2 `CANONICAL_RESULT_TOOLS` = 8 individualpresenter | `canonical_results.py:23-34`,Item 8 of the report| Unanimously|
| §5.3 `MEMORY_CANDIDATE_TEXT_MAX_CHARS = 12000` | `agent_memory/policy.py:122` | Unanimously|
| §5.3 `PAYLOAD_FIELD_ALLOWLISTS` + Two.classify Functions| `policy.py:49/125/141` | Unanimously|
| §5.4 `compute_platform_validation_results` | `validation/platform_metrics.py:445` | Unanimously|
| §3.1 v1_compat Four.tool Functions| `packs/v1_compat/tools.py:23/37/52/60` | Unanimously|
| §3.1 `MODEL_VALIDATION` Four steps in sequence.| `templates/validation.py:19-63`,scan → run_notebook → compute → render | Unanimously|
| §3.1 Templatespost_checks(status Value/ ks,auc 0..1 / psi allow_null) | `templates/validation.py:46-49` | Unanimously|
| §1.1 Registered 27`include_router` | `app.py:609-635`,Cha, 27 times.| Unanimously|

### 2.5 Quantity determination of test (6)/6)

| Module| Document Name| AST Numeric Functions| `pytest --collect-only` | Decision|
|---|---:|---:|---:|---|
| `sql_ingest.py` | 22 | 13 | **22** | Unanimously|
| `historical_backtest.py` | 15 | 15 | — | Unanimously|
| `leakage_diagnostics.py` | 12 | 12 | — | Unanimously|
| `limit_pricing_impact.py` | 20 | 12 | **20** | Unanimously|
| `fairness_evidence.py` | 14 | 14 | — | Unanimously|
| `counterfactual.py` | 10 | 10 | — | Unanimously|

> **Parametered Trap**:`sql_ingest` and`limit_pricing_impact` 3 and 2 respectively
> `@pytest.mark.parametrize`.Use onlyAST Statistics`test_*` The function will get 13 and 12,
> Miscalculated as "9 over-documentation"/ 8 "Long."`pytest --collect-only` The real collection,
> Parameters are expanded to 22 and 20, fully consistent with the document.**The number of tests to verify parameterization must be usedcollect-only.**

### 2.6 [12135 passed]Volume Cross-check

Full LibraryAST Statistics: 687 test documents, 8427`test_*` Function, 928 placesparametrize.
Press everywhereparametrize Expand average of 5 instances inverse:`8427 − 928 + 928 × 5 ≈ 12139`,With Document Claim
12135 passed Matches. This is a quantitative validation, and the price is not equal (in the case of a price)skipped / failed / Parametrically defined actual extension numbers are affected.

## 3. Inconsistent items (2 items)`architecture.md` §5.1)

### 3.1 `plugins/runner.py` Not used`hmac.compare_digest`

Original document:

> Same "Hol-Hashi"+ `hmac.compare_digest`]Present`routers/artifacts.py`,
> `download_snapshot.py`,`artifacts/model_score_vector.py`,**`plugins/runner.py`**
> (`_payload_hash` / `_manifest_receipt_hash` / `result_hash`).

Based on the results: full library`hmac.compare_digest` Hit 100+ A file, but...`plugins/runner.py` **Not in it.**;
None in this document`import hmac` And nothing.`compare_digest` Call.

Actual`runner.py:2115-2133`):

```python
def _result_payload_hash(output: dict) -> str: ...
def _manifest_receipt_hash(manifest: PluginManifest) -> str:
    return _result_payload_hash(manifest_to_dict(manifest))
```

Nature: This is**Insufficient assessment (%)understatement)Not overstatement.**.`runner.py` And what they do is, "Calculate and
The blog posts a video of the event.`_result_payload_hash`,`_manifest_receipt_hash`,`result_hash`),belong to
**Generate**Evidence;`compare_digest` Yes.**Match**Compared constant time between the two Hashi values, time-proof side-link.
The two are different kinds of operations.Runner Only the former, which was not needed. The document puts "heavy" on
[`hmac.compare_digest`]Merge in a mode to apply toRunner Up, it's misclassified.

**Proposed law reform**:Will`plugins/runner.py` From this sentence`compare_digest` The blog is a good example of the problem.
Or reword it to read "Runner Compute and bind every call`_result_payload_hash` / `_manifest_receipt_hash` /
`result_hash`,For downstream matching`hmac.compare_digest`].

### 3.2 Function Writing`_payload_hash`,Actual`_result_payload_hash`

Idem. The actual function is`_result_payload_hash`(`runner.py:2115`).
(`_manifest_receipt_hash` and`result_hash` Two are correct.

**Proposed law reform**:For`_result_payload_hash`.

## 4. Workspace drift (no document but impact)capability-status Conclusions

| Documentation| HEAD | Workspace| Floating|
|---|---:|---:|---:|
| `static/app.js` | 8382 | 8858 | +476 |
| `static/js/` | 31 Module/ 6409 Okay.| 33 Module/ 7540 Okay.| +2 Module/ +1131 Okay.|
| `marvis/pipeline.py` | 2324 | 2351 | +27 |
| `marvis/llm_prompts.py` | 77089 B | 77696 B | +607 B |

**Need to be singled out**:`capability-status.md` "'B-6 Front-end monomer condensation✅ The article is "Fine of the people."
The current working area has been substantially overturned -

```text
B-6 Before the split.app.js = 8,465
B-6 After(main)    app.js = 8,382
Current Workspaceapp.js = 8,858   (No changes submitted+653 / −177)
```

This is the upgrade of the unsubmitted validation module that allows for a net increase of 476 lines in the front end monomer, and the following is the first step in the process:**More than the eight before Operation Repression.,465 Okay.**.
The present report does not change the document but merely suggests that the conclusion needs to be reassessed and updated before the change is submitted.

## 5. Limitations of current round verification

1. Unrun full`pytest`(12135 (Performance)gate Exit code 0, only a quantitative cross-check.
2. Not verified article by article`capability-status.md` Medium`VERIFIED` Layers**Evidentiary sufficiency**(That's the question of judgment.
   The number of mechanically verifiable tests was only verified.
3. Uncertified`roadmap.md` The product range assertion - it's product decision, not code fact.
4. Code synonyms verify that "Indices exist"+ Function reading', no behavioural-level running validation.
5. `hmac.compare_digest` Full house 100+ Unchecked by one, only 5 files named in the document were verified
   `plugins/runner.py`(Discrepancies found; remaining 4 (`packs/strategy/report_bundle.py`,
   `routers/artifacts.py`,`download_snapshot.py`,`artifacts/model_score_vector.py`)
   All in the library hit list, no discrepancies were found.

## 6. Methodological recommendations

1. **Logical assertion must read full functions**.Current round of`pipeline.py:236` It's...
   `return _truthy_env(LEGACY_LIVE_NOTEBOOK_ENV_VAR)` Single-line, three times miscalculation.opt-in Only environment variables tested
   one; after reading a function confirm that the first two short-circuit conditions of row 234 are covered.grep Single-line output is not sufficient to determine logic.
2. **Number of tests with parameterisation`pytest --collect-only`**,AST Numerical functions are systematically underestimated.
3. **Run the program test with absolute path.** `/opt/miniconda3/envs/py_313/bin/python -m pytest`.
   `conda run -n py_313 python` ♪ will resolve to ♪workbuddy managed python(Nonepytest).
