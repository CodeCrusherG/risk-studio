# V2.4.0 Release candidate validation records

> Date: 2026-09-17.Conclusion: Full local door access is forbidden before publication.
> This document records local candidate evidence; remote distribution andCI The state should be matched.tag,commit andActions The result is the same.

## Scope

- Include consolidated[issue #23 RehabilitationPR #24](https://github.com/eddyzzl/marvis-risk-agent/pull/24):Authenticated snapshots are published first, then set to read-only, and keptWindows Reaction of authority.
- Include locally unpublished read-onlySQL Access, certainty strategy analysis of kernels, restricted counter-fact re-enactment,Agent Modules are split and their governance, compatibility testing and documentation.
- Uniform model validation portal, support 1–10 Models; models maintain independent progress, evidence and editable draft reports. Single models generate only themselvesWord/Excel,Additional generation of non-recosted indicators by multiple modelsExcel.
- UpdateT/A Cartwright,Lift/The compartments explain, report risk markers, task suspension information and model transition experience; certainty indicators are still calculated by platform code.

## The issue of the closed circle of this cycle

- When the draft report enters the confirmation door, the batch is no longer miscalculated as a failure; the parent batch is synchronized after the report is generated.
- Automatically review the draft final report on reservations to confirm the door; all confirm the validity of the amendment number, enter the contract and take the assignment within the same service, and roll back the whole in case of conflict.
- The failure of a model report does not block the remaining confirmed models; the failure status is still in batch aggregation.
- Autorun the fixesPromise Unreleased; maintain user edits when creating form to update default narratives.
- IncrementalBandit Harmonize baseline and scanning file paths without changing the original baseline or lowering the level of the inspection; regression coverage is denied for existing problem identification and additional problems.
- Updates the front-end test folders and old source text that lack the context of the workstation, and maintains the original business assertion; public examples use generic names.

## Validation of evidence

| Certification Level| Result|
|---|---|
| Full local release doorbar| `scripts/check -- -q` Exit code 0;12,415 passed,8 skipped,33 warnings,Time-consuming 6,185.93 sec1:43:05) |
| Static check| Ruff,Node Syntax:`git diff --check` Pass.|
| Incremental security check| and`origin/main` ComparedBandit Inspection passed; not complete security audit findings|
| Front-end orientation returns| `tests/test_frontend_static_v2.py` ;no examples of failures deleted or skipped|
| Real modelling and delivery| Actual servicesJOIN→Modelling→PMML,Delivery of business materials, 30 orientation tests for model products, validation of handover, natural language delivery passed; complete door closure again passed|
| Real Browser Create Page| Single/Multimodel creation,Agent Choose,T/A Default file and retention of user editsDOM Check passed; console checked without error|
| Candidateswheel | 726 bytes of files in a package matching the tree of the candidate; adding new modules,JS Existence of photographs with reports, no local work area or abandoned module; health check after quarantine installation and sixHTTP Resource check passed.|
| Consistency of candidatures| Aligning the fingerprints before and after the complete doorbar with the new check script Hashi; no change in candidate code during the test|

Full door is disabled.`MARVIS_RUN_PLAYWRIGHT_SMOKE=1`,Unusedfast/affected .
8 All skipping items require a visible displayDeepSeek Online diagnostics of the workspace configuration, from
`test_semantic_authorization_live_profile.py`,`test_semantic_intent_live_profile.py`
and`test_strategy_sample_binding_semantic_delegation.py`;These real online models are not called during this cycle.

## Environment and borders

This is the machine.`py_313` Mediumscikit-learn 1.9.1 Beyond currentsklearn2pmml 0.131.0 The range of converters,
♪ Has made it true ♪PMML Export failed. Repository lock file specifiedscikit-learn 1.9.0;In the middle of a...`py_313` A birth,
The real process and complete door are blocked after the lock version is installed in the temporary isolation environment, where the rest of the dependencies are re-established.
No day changeconda The environment is still not relaxed.Plugin worker Rules of environmental segregation.
This is not to claim that every reliance on the temporary environment is exactly the same as the lock-in document.

Indicative command (the path needs to be replaced by actual candidate and isolation):

```bash
MARVIS_RUN_PLAYWRIGHT_SMOKE=1 \
PYTHONPATH=/path/to/candidate \
PYTHON=/path/to/release-venv/bin/python \
CHECK_DIFF_RANGE=origin/main \
scripts/check -- -q
```

Candidateswheel Validation before release metadata upgrade; official version by`scripts/release_push.py` Created,
Formalwheel The original development snapshot and local untraceed material are kept locally.
Do not enter a public release history or install packages.

This round doesn't prove birth.Windows/NTFS,Windows Installation packages, real institutional materials, realLLM All the journeys,
Production deployment or operational signature; these borders cannot be created or published with local testing, browserstag Alternative.
