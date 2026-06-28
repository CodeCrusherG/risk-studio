# MARVIS Capability acceptance status

> Unique status matrix; route range available[roadmap.md](roadmap.md)
>
> Current candidate status update: 2026-08-09.V2.3.0 Candidates have completed code review, real interface acceptance,
> Real Model Security Assessment and Complete Localrelease gate;We'll see the evidence in summary.
> [V2.3.0 Issue review readiness](reviews/2026-08-09-v2-3-0-release-readiness.md).
> Can not get folder: %s: %scommit,tag,release push Or a counter.SHA Far EndCI,
> As a result, these layers of delivery remain in place`NOT_PROVEN`,The results cannot be extrapolated locally.
>
> 2026-08-13/14 Incremental update (90 days planned):SQL Read-only access, strategic history retrospective, leaks and
> Select the deviation detection, the amount/Pricingtyped Impact, equity evidence module, anti-fact re-centre (both
> Core+Single vertical cut, not answeredAgent/UI Levels maintainedNOT_PROVEN);Two super-stylish file physics.
> Split completed (see local structure table). Add new rowsAPI/Agent/Browser The floor is on the line and running.
> Stay in front of the journey.NOT_PROVEN,No upgrades due to single-checking.

## Status caliber

- `VERIFIED`:There is evidence of duplication at this capability level.
- `IN_PROGRESS`:Current candidate is being integrated or validated and has not yet become finalverdict.
- `PARTIAL`:A full user journey is available vertically but does not cover the layer.
- `IMPLEMENTED`:kernel presence; cannot be inferred from thisAPI,Agent,Browser or production is available.
- `NOT_PROVEN`:There is not currently sufficient evidence of acceptance.
- `FAILED`:There is currently repetitious evidence, but the threshold for acceptance of the layer is not met.
- `BLOCKED`:The conditions of closure depend on the necessary input or responsible person evidence outside the current working area.
- `NOT_DELIVERED`:The product is clearly not yet delivered.
- `N/A`:This layer does not apply to this capability.

The following table shows the separate columns.`implemented=VERIFIED` No automatic upgrade of any column on the right.
of which`VERIFIED` / `PARTIAL` Evidence is available at the records capability level, which does not mean that it is currentlydirty candidate It's passed.
Launch door; candidate delivery status is based on the delivery door immediately following.

## Current candidate delivery door

| Delivery Layer| Status| Current evidence| Completion Conditions|
|---|---|---|---|
| Code integration andcode review | VERIFIED | Final integrated review not found reoccurableP0/P1/P2;LLM/Planner/Eval No remaining special review found.P0-P3 | Include all realization and return documents when submitted and freeze for reviewSHA |
| Focus Test and Static Check| VERIFIED | Integrated review 378passed,1 skipped;LLM/Planner/Eval Review 385passed;Ruff,CoreJS Syntax:diff check It's all passed.| The next change must be reruning the affected door.|
| Full Local`scripts/check` | VERIFIED | `MARVIS_RUN_PLAYWRIGHT_SMOKE=1` Down exit code 0:12135passed,8 skipped,32 warnings;Ruff,Node anddiff check Synchronize Pass| Use remote after releasefull CI Review of the same issuanceSHA |
| Real Browser Acceptance| VERIFIED | Realin-app browser Covers the eight-entry, batch validation and main positive and negative branches; status bar by default closes, downloads, refreshs,typed gate,Error Interrupts andCandidate Lab The response layout is available.| Repeat the journey when the product adds or changes the user path|
| Commit / release push | NOT_PROVEN | Current candidate not yet availablecommit,tag orpush | Check and close the local door, press`scripts/release_push.py` Freezing and publishing the sameSHA |
| GitHub FarCI | NOT_PROVEN | Current candidate does not match the remoteworkflow Result| ReleaseSHA CompleteGitHub CI All green, check localHEAD,Remote Branches andtag Point to the same point.|

## Current Matrix

| Capacity| Implemented | Unit | API | Agent | Browser | Fresh workspace | Real data | Sign-off | Production | Current product conclusions|
|---|---|---|---|---|---|---|---|---|---|---|
| Data processing/ JOIN | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | One of the eight official desktop portals; double-table upload, role/Keys/Target identification, diagnosis, execution and downloading are in progress|
| SQL Read-only data access| VERIFIED | VERIFIED | NOT_PROVEN | NOT_PROVEN | NOT_PROVEN | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | Core and single measurement completed (`data/sql_ingest.py`:DuckDB/SQLite/PostgreSQL Read-only, singleSELECT White list, line budget/(b) Timeout, de-sensitive proof, same rights and responsibilities as the import of documents;tests);Not yet receivedAgent/UI,- We're going to press the 90-day plan.A-6 To be confirmed by user|
| Characteristic analysis| VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | The entire indicator, selected sub-boxes and jumper branches are all aligned; indicators and reporting are covered by the certainty tool|
| Model development| VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | LR NoneOOT,XGB RandomOOT,LGB TimeOOT The outputs were individually rotated;T4-2 Not Closed|
| Model validation| VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | Manual,Agent,Failure to block and download reports; no substitute for independent certification responsibilities|
| Model validation (multi-model)| VERIFIED | VERIFIED | VERIFIED | PARTIAL | PARTIAL | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | (b) Discontinue to be the first entry point for the independent screen;N≥2 Create flow organization from Model Validation, connectAgent Dialogue confirms the contract; the old final batch is still available for download.VERIFIED Meaning|
| Policy development| VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | Phase VIICandidate Lab With the main strategy approach, stability/Replay, compile/Application,ProjectContext The report in the fourth format is out of line; local adoption is not equivalent to production deployment|
| Policy history backdown score| VERIFIED | VERIFIED | NOT_PROVEN | NOT_PROVEN | NOT_PROVEN | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | as-of Replay core and single measurement completed on a monthly basis (`packs/strategy/historical_backtest.py`:Moonfail-closed,backtested/unvalidated Marking;15tests);Not answeredAgent/UI |
| Leak and Selection Dividing Test| VERIFIED | VERIFIED | NOT_PROVEN | NOT_PROVEN | NOT_PROVEN | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | Time to leak red flags+ Two-population comparison core versus single measurement (%)`packs/strategy/leakage_diagnostics.py`;12 tests),Pure evidence, not automatically blocked; not answeredAgent/UI |
| Amount/Pricingtyped Impact| VERIFIED | VERIFIED | NOT_PROVEN | NOT_PROVEN | NOT_PROVEN | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | Open/EL Incremental, pricing gains-Bad debts,segment×month Matrix Core and Single Test Completion (`packs/strategy/limit_pricing_impact.py`;20 tests),Missing caliber=unavailable;Not answeredAgent/UI |
| Vintage / roll-rate / Profit analysis| VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | Standard Vintage,VTG,base-only VTG,The profit analysis and the incompatibility mixed scenes are all out of hand.|
| Labels and Sample Definitions| VERIFIED | VERIFIED | VERIFIED | VERIFIED | PARTIAL | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | Governance as part of data processingworkflow;Focused evidence of caliber proposals, maturity doors, double confirmation, derivative data sets and downloads, not silent replacementactive dataset;Current candidate still needs to rerun the real browser trip.|
| Multi-model fraction comparison| VERIFIED | VERIFIED | VERIFIED | VERIFIED | NOT_PROVEN | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | Authentication updateSampleDesign At least two models are implemented with each model score evidence; output compares evidence without automatically selecting the champion, adopting or deploying|
| Model/ Policy monitoring| IMPLEMENTED | VERIFIED | PARTIAL | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | Only single diagnosis is supported/Disposed vertically, not production monitoring systems|
| Portfolio / Concentration/ EL | VERIFIED | VERIFIED | VERIFIED | VERIFIED | VERIFIED | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | no-trend Balance of synthetic journey completed/EAD,Grouping, loss pattern,LGD,Duration, reports and downloads; true institutional combination still not accepted|
| Ongoing operations and movement control/ Announcements| PARTIAL | VERIFIED | VERIFIED | NOT_DELIVERED | NOT_DELIVERED | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | There's a permanent operation.scheduler,Notification, retry andAPI Base; not bound to implement, long termcadence,Watch and fail exercises|
| Real time/ Bulk scoring decision-making services| PARTIAL | PARTIAL | NOT_DELIVERED | NOT_DELIVERED | NOT_DELIVERED | NOT_PROVEN | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | Local scores and deliverables exist, production decision-making services not delivered|
| Multi-UserRBAC / maker-checker | PARTIAL | VERIFIED | VERIFIED | NOT_DELIVERED | NOT_DELIVERED | PARTIAL | N/A | NOT_PROVEN | NOT_DELIVERED | Localsession principal,maker/checker/admin,Promotion and RollbackAPI Existing; not source of business identity,SSO or governance of organizational competencies|
| Promotions by Environment/ Activate/ Roll back| PARTIAL | VERIFIED | VERIFIED | NOT_DELIVERED | NOT_DELIVERED | PARTIAL | N/A | NOT_PROVEN | NOT_DELIVERED | Service-side generation is immutabledeployment manifest,Activate Accept onlyallowlisted verifier content-research evidence;default noverifier So we can't claim to be real active.|
| Credit decision-making digital twin| VERIFIED | VERIFIED | NOT_DELIVERED | NOT_DELIVERED | NOT_DELIVERED | PARTIAL | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | LocalCAS,Freezemanifest/facts/Field Source/adapter andtransitive helper,Champion/Challenger/Counter-fact union binding andproposal-only FSP-8 Bridges; 2026-08-13 Add a new anti-fact re-core (BFR)`decision_twin/counterfactual.py`:White list.delta,Line budgetfail-closed,counterfactual_only Mark, 10tests);Not yet officialAPI,UI,External signature or remote storage is not tampered with|
| Equity/ Reason for rejection/ The complaint| PARTIAL | VERIFIED | NOT_DELIVERED | PARTIAL | NOT_DELIVERED | NOT_PROVEN | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | 2026-08-13 Add a new group pass rate/Bad rate/Evidence module for the reason of refusal (`packs/strategy/fairness_evidence.py`,Complimentary, non-declared, drafting template, 14tests);Still not a full compliance desk|
| Recover.| NOT_DELIVERED | NOT_DELIVERED | NOT_DELIVERED | NOT_DELIVERED | NOT_DELIVERED | NOT_PROVEN | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | Not in current delivered workflow|
| Anti-fraud| NOT_DELIVERED | NOT_DELIVERED | NOT_DELIVERED | NOT_DELIVERED | NOT_DELIVERED | NOT_PROVEN | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | Universal modelling capability does not amount to a complete anti-fraud system|
| Letter of request/ Triangular access| NOT_DELIVERED | NOT_DELIVERED | NOT_DELIVERED | NOT_DELIVERED | NOT_DELIVERED | NOT_PROVEN | NOT_PROVEN | NOT_PROVEN | NOT_DELIVERED | Undelivered Production Parsing and Access|

## Local structure and credible chain state

| Border| Status| Current evidence| The conclusion that you can't push out.|
|---|---|---|---|
| Strategy workflow Factual sources| VERIFIED | 44/44 spec The blogger says:validator/confirmation/preparer (a) Full coverage;compiler shadow Branch 0;singlecanonical turn entry | It doesn't mean that two super-sequenced files have been physically split.|
| Super-largely organized file physical splits| VERIFIED | 2026-08-14:`turn_handlers.py`(17,868 Disassembly into 17 drive bag,`strategy_request_compiler.py`(14,449 Lines) to 10, use allexec-merge Namespace design (Run-time syntax corresponds to the original monomer and containsmonkeypatch);turn_handlers Related 865tests,compiler Related 1,993 tests(1 individual`inspect.getsource` Test migration to combined drive code, no change in semantics) pass; two packagesruff Clean;`__all__` Same by name.| Not representing the remaining large driveway files (in thousands of dollars)strategy_candidates About 4.5k (Class-only) andapp.js The unit has continued to be broken down.|
| Canonical result Presentation| VERIFIED | 8 individualpresenter;ToolRunner Do it before it works.live authentication,And bind.invocation/output/tool version/manifest;Repository Retest with the display endexact binding | Not to imply that external storage or host administrator cannot be tampered with|
| Results data set download| VERIFIED | URL Tieplan/step/output/hash;registry,Documentation andevidence retesting;listdescriptor Private snapshot closedverify-to-open competition;freezing snapshot supportRange/206/416 | Do not represent remote object storage,CDN or trans-regional transfer accepted|
| Crash recovery| VERIFIED | Fathers bound to a complete conflict will putCHECKING step andRUNNING plan Concentrating asFAILED;startup reclaim There's a return.| Not to imply that the production-level process layout and failure exercise has been completed|
| Manually screen the evidence boundary| VERIFIED | Manualselection Atom bindinggate inputs,Do not overwrite finishedscreen Tool It's...output ref/hash/succeeded run receipt;RealModeling API E2E and independent review of the| Not representing manual approval as an alternative to independent validation or segregation of production responsibilities|
| Segregation of execution and ownership of resources| VERIFIED | Notebook worker Use`-I` Trustable.bootstrap And refuse.notebook (a) Directory shadow packs;automatic-tree Parquet reader exact-once Close it,`xb` Export ownership constraintscleanup,Overwrite Interrupted,close failure Create with Co-Creation| It's not external.sandbox,Container isolation or birthWindows Document semantics accepted|
| High faith cleanup| VERIFIED | `marvis` InternalDB façade import Zero;`memory.before_save` All true save paths are connected;pet catalog monolithic; durability documentsGC;artifact identity All TreesAST guard;JS/CSS/renderer First round split; staticimmutable URL TieJS/CSS ContentsSHA-256 | It does not mean that the warehouse is out of technical debt or that compatible codes can be deleted in bulk|

## Current blockage

| Door.| Status| Current evidence| Close Conditions|
|---|---|---|---|
| Agent fast safety eval | VERIFIED | Semantic authorization,Planner/Validator,typed provenance,replan,Explore andLLM error fail-closed Integration/Specialized returns, 378 respectively.passed,1 skipped and 317passed | Same after the release.SHA Run again.blocking safety eval |
| Current local full candidategate | VERIFIED | Complete`scripts/check` Exit code 0:12135passed,8 skipped,32 warnings;Ruff,Node anddiff check Synchronize Pass| Subsequent source changes need to be re-run completegate |
| T4-2 Open Data Reference Gate| BLOCKED | `scripts/ks_baseline.py --status` returns 2;GiveMeSomeCredit/Home Credit Documentation not aligned with the manual retroactive baseline| Pre-registrationsplit/seed/Characteristics/Budget/The tolerance is low. Both data sets are passing.|
| T4-3 Real-material reconciliation| NOT_PROVEN | checklist and machine precheck frames exist; not currently completedB1-B5 and liabilityrepo/workspace Evidence| At least one set of real materials completes pre-screening, external reconciliation and signature|
| Current Candidates FarCI | NOT_PROVEN | Candidatures have not yet been frozen, published or triggeredGitHub workflow;A distant success cannot be covered by the currentdirty worktree | Conserve as subject to reviewSHA,And let's make itSHA Through Full RemoteCI |
| Real Browser at the Eighth Entrance| VERIFIED | 2026-08-08 to 2026-08-09 Use Realin-app browser Cover eight portals, batch verification, main methods/Datasets/button/Agent Phrase and negative branches, and keep screenshots, downloads, tasks and logs| Reruns after entry or interactive contract changes|
| Current candidate for release| NOT_PROVEN | Not yetcommit,tag orrelease push,There's no current candidate at the far end.SHA | Local integritygate Closes with real browser acceptance, usingrelease helper Publish and check remote references|
| RealLLM Security assessment| VERIFIED | Current Candidate Generation`marvis.eval.report.v2` Full report: 0LLM/harness error;`autonomous` 13/13,guardrail 3/3,pass rate andguardrail pass rate Average 1.00,To be the only one that can be recommended.tier;`balanced` and`conservative` Becauseguardrail Irrefinable and incomplete.| Models,prompt,corpus or the governance threshold must be reruned; not recommendedtier Extrapolation to Production Authorization|
| NativeWindows / NTFS | NOT_PROVEN | macOS/POSIX Behaviour and sharinghandle adapter Single-checked; not yet trueWindows sharing violation,Delete/Try again/Restore evidence| In the originalWindows/NTFS Upshow Files and Task TreeGC,Intended files, retested and received|
| Production operations| NOT_DELIVERED | Local Schedules Only/Notification andmaker-checker/Promotions; absence of real identity sources, integration of production agents and decision-making, long-term alert duty and failure exercises| Completion and operation of signature in accordance with approved production structure and through failure exercise|

## Portfolio andLabeling Decision

1. Portfolio Formally completedHTTP Agent,pre-plan The first video was posted on the blog of the Quest, which was posted on the blog of the Quest of the Quest of the Quest of the Quest of the Quest of the Quest of the Quest of the Quest of the Quest of the Quest.
   For now, only theno-trend As a certified public journey, the full report must still have a balance./EAD and business sub-clusters,
   When missingsetup failed to close;real grouping, cycletrend The production movement still has not been accepted.
2. Labeling Do not add the top layer for the time beingtask type.It should be a high risk in data processing tasks first.workflow:
   Label definition, observation window, performance window, bad sample threshold, maturityoverride Both need to write and to produce data.
   Structured confirmation, version,lineage and audit; results may not be replaced silentlyactive dataset.
3. The above decision is the product ' s reach boundary and is not a reason to delete the kernel code.

## (The current answer to whether an operational expert is independent in managing the business line)

The current platform allows operational experts to independently complete a large number of local development and analysis work, but the conclusion remains that
`NOT_PROVEN`.Current real model assessment is recommended`autonomous` tier,But it only proves the present.
13-case Planning and security performance under the contract cannot be assessed as a (one-person production line system).
Production data, independent validation, approval, compliance,
Increased responsibility for publishing, rolling back, duty and auditingAgent The level of autonomy is eliminated. The current precise location is:

> Local wind management development and analysis desk; a business specialist becomes the high-love core of a small risk management team.
