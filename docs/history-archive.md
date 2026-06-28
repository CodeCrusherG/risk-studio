# MARVIS Historical Document Archive (read-only)

> 2026-08-13 Integration product of document cleanup. This document replaces previously scattered`docs/plans/`,
> `docs/plans/specs/`,`docs/releases/`,`docs/reviews/`,`docs/superpowers/`
> Historical plans, review and award documents with the repository root directory: each removed document is kept in a row below
> Summary and disposition conclusions are no longer maintained separately.
>
> From now on:
> - **Develop implementation**Here.[docs/superpowers/plans/2026-08-13-next-90-days-development-plan.md](superpowers/plans/2026-08-13-next-90-days-development-plan.md) Whichever is the applicable;
> - **Product scope and terminology**Here.[docs/roadmap.md](roadmap.md) Whichever is the applicable;
> - **Level acceptance status**Here.[docs/capability-status.md](capability-status.md) Whichever is the applicable;
> - **Publication rules**Here.[docs/versioning.md](versioning.md) Yes.
>
> All removed documents remain in their original languagegit In history, if you need it,
> `git log --all -- <path>` Get back.

## 1. Disposal caliber

| Disposal| Meaning|
|---|---|
| Delivery| The project planned for the document is landed and enteredV2.1–V2.3 Release line, original is invalid|
| Replaced| Follow-up plan/Review/Document has all its contents overwrited|
| Invalid| The decision in the document has been reversed by subsequent scope changes (e.g.LT-9 / LT-18) |
| Reservations| Still in force (see§6 List)|

## 2. Historical plans and activitiesSpec(Removed)

### 2.1 `docs/plans/`(Main axes and phases of the planspec)

| Documentation| Theme| Disposal| Status at the receiving office|
|---|---|---|---|
| modeling-agent-roadmap.md | Model developmentAgent Dialogue full-process grinding routes| Delivery| capability-status[Model development line|
| settings-ia-refactor.md | Set up the window information structure re-construct| Delivery| Current frontend achieved|
| v2-completion-plan.md | V2 The main axes of the overall architecture and route (12 decisions) are the following:JOIN I'll be right back.| Delivery| roadmap / capability-status |
| v2-comprehensive-improvement-plan.md | 2026-06-29 Perform the round validation/Record of evidence| Replaced| Its tracking functions were transferredv2-master-backlog((also archived)|
| v2-feature-phase-spec.md | FEATURE Detailed phasespec(Characteristic analysis+Filter)| Delivery| capability-status[Qualification analysis line|
| v2-frontend-layout-spec.md | Frontend layout of Sector 3spec | Delivery| DESIGN.md + Current frontend achieved|
| v2-join-phase-spec.md | JOIN Detailed phasespec(Secured left connection, etc.)| Delivery| capability-status[Data processing/ JOIN]Okay.|
| v2-longtail-adjudications.md | LT-9/10/12/16/17/18 award| Partially lapsed| The award points are retained in this document§4 |
| v2-master-backlog.md | Historical implementation tracking (summary of 115 article reviews)| Replaced| roadmap + capability-status Be the only caliber|
| v2-modeling-phase-spec.md | MODELING Detailed phasespec | Delivery| capability-status[Model development line|
| v2-plan-driver-spec.md | Generic plan dialogue drivenspec(agent Layer)| Delivery| marvis/agent/plan_driver.py |
| v2-strategy-risk-analysis-plan.md | Policy+Risk analysis capability map (RAC)S1a–S6) | Delivery| Strategy seven, 2026.-07-27 (b) Closure;roadmap §Current Status|
| v2-trust-first-plan.md | Trust-First Planned (three-tier data test)T4) | Replaced| T4 The door.capability-status["Continues to block the door."|

### 2.2 `docs/plans/specs/`(Function Levelspec)

| Documentation| Theme| Disposal|
|---|---|---|
| v2-s1a-score-direction-spec.md | Institutionalization of fractional orientation| Delivery|
| v2-s2-strategy-development-spec.md | Policy Development Main Line| Delivery|
| v2-s3-portfolio-analysis-spec.md | Group Analysis Package| Delivery (in thousands of United States dollars)no-trend Even|
| v2-s4-rule-strategy-spec.md | Rule Policy| Delivery|
| v2-s5-monitoring-closure-spec.md | Monitor closed loops and periodic reports| Partial delivery (single diagnosis delivered; movement control still ongoing)PARTIAL,See new planB-15) |
| v2-s6-adhoc-pricing-compare-spec.md | Summary analysis+Amount/Pricing+challenger Present| Partial delivery (summary analysis delivered; level of amount)/Pricingtyped The caliber is on the new plan.B-10) |
| v2-t1-semantic-correctness-spec.md | Semantic Correctness Fixer Package| Delivery|

### 2.3 `docs/superpowers/`(Blueprint, phasing and follow-upplan/spec)

| Documentation| Theme| Disposal|
|---|---|---|
| plans/2026-06-04-v1-1-agent-memory-foundation.md | V1.1 Agent Memory Foundation| Delivery (Memory asV2 (Reservation of compatibility)|
| specs/2026-06-04-v1-1-agent-memory-foundation-design.md | V1.1 Agent Memory Design| Delivery|
| specs/2026-06-13-marvis-platform-blueprint.md | V2 Platform blueprint ()Plugin/Tool/Hook/Workflow (Structure)| Delivery|
| specs/2026-06-13-phase-0-foundation.md … phase-8-draft-zone.md | Phase 0–8 Detailed phasespec | Delivery (phase by phase into release line)|
| specs/2026-06-13-phase-frontend-v2.md | FrontendV2 spec | Delivery|
| plans/2026-07-10-notebook-stress-category-continuity.md | Notebook Pressure classification continuity plan| Delivery|
| specs/2026-07-10-notebook-stress-category-continuity-design.md | Ibid. Design| Delivery|
| plans/2026-07-12-pmml-scoring-validation-non-regression.md | PMML Rating to validate non-return plans| Delivery|
| specs/2026-07-12-pmml-scoring-validation-non-regression-design.md | Ibid. Design| Delivery|
| plans/2026-07-17-strategy-platform-gap-analysis-and-roadmap.md | Gap analysis and route of strategic platforms| Replaced (Strategy 7 Steps 07)-27 Shut up!|
| specs/2026-07-19-strategy-report-bundle-spec.md | Seven steps report.bundle spec | Delivery|

### 2.4 `docs/releases/`

| Documentation| Theme| Disposal|
|---|---|---|
| 2026-07-02-intermediate-pr.md | CentrePR Records| Superseded (by issuing historical opinion)git tag andversioning.md) |
| 2026-07-03-v2-mainline-pr.md | V2 mainline PR Records| Superseded (ibid.)|

## 3. Historical Review Report (removald)

| Documentation| Summary of conclusions| Disposal|
|---|---|---|
| 2026-06-21-v2-full-code-review.md | V2 Comprehensivecode review & Quick check with nonvariant| covered by follow-up review|
| 2026-06-28-v2-improvement-proposals.md | Multi-expert forward-looking proposals for improvement| By 07-02 Synthesis review absorption|
| 2026-06-28-v2-plan-code-review.md | Earlyplan/code The blog is a good one.finding Repaired| Replaced|
| 2026-06-28-v2-runtime-deep-review.md | Branch depth review (counterfeasibility of service-restricted flow, remaining 9 pending final validation)| covered by follow-up review|
| 2026-07-02-v2-comprehensive-improvement-review.md | 115 Item 1: Review of all aspects, outputsmaster-backlog | Completed and reviewed|
| 2026-07-03-fin1-landing-verification.md | FIN-1 Landscape verification: 182/182 All tribes.| Historical evidence|
| 2026-07-03-fin2-fin3-closing-review.md | FIN-2 Full review+ FIN-3 Restoration cycle: shutdown determined| Historical evidence|
| 2026-07-03-vd11-design-token-inventory.md | DesignToken Repression list (%)radius-pill) | Completed|
| 2026-07-04-full-read-and-owner-qa.md | Two full-scale readings.+ Question 5 for Owners, OutputTrust-First Planned| Implemented|
| 2026-07-24-data-feature-model-final-review.md | Data/Characteristics/Final review of the entire process of the model (07)-28 (Revision of amendments)| ByE2E Review coverage|
| 2026-07-24-data-feature-ui-code-review.md | The first time the review was conducted,finding Repaired| Replaced|
| 2026-07-28-e2e-dfm-full-code-review.md | Data processing/Characteristics/ModelE2E:PASS_FOR_PR(Standards+Spec (Direct Axis)| Historical evidence|
| 2026-07-28-e2e-risk-analysis-full-code-review.md | Risk analysisE2E:Adopted by the independent review| Historical evidence|
| 2026-07-28-v2-strategy-full-code-review.md | Strategy development full-scale review: independent review adopted| Historical evidence|
| 2026-07-31-project-agent-architecture-comprehensive-audit.md | Item/Agent/Comprehensive structural health audit (including full process capability VI)| Conclusions incorporated into 08-01 Shut up.|
| 2026-08-01-comprehensive-audit-final-closure.md | Comprehensive audit final: high-confidence zombies cleared; technical debt still available, suitable for targeted governance, no claims"No more shit." | Historical conclusion (has been 08)-09/08-10 (As of the time of the review)|
| 2026-08-01-comprehensive-audit-remediation.md | Consolidated audit consolidation and re-recording| Completed and reviewed|
| 2026-08-01-final-local-closure-code-review.md | Final local closure Review: resumption of the binding conflictBLOCKER Closed| Historical evidence|
| 2026-08-01-presenter-trust-code-review.md | Governed Tool Presenter Trust review:CR-01/02,WR-01 Closed| Historical evidence|
| 2026-08-01-remediation-code-review.md | Change the history of the reviewfinding Quickshot| Replaced|

## 4. Historical decision points (in millions of years)`v2-longtail-adjudications.md` Other Organiser

- **LT-9(OS Class-class sandboxvs subprocess+(Battle)**:2026-07-03 award -V2 The threat model is a single-line user.subprocess+- The fence.OOM Process tree kill, environment white list,kernel It's true. It's a long story.TST-4 (Certified) sufficient; sandbox upgrades were madeV3+ Access entry.**2026-07-17 Reopened**:Multi-User/Production enforcement quarantine migrationV2 Track of implementation.
- **LT-10(legacy live-session Path)**:is determinedtriple-opt-in legacy-only Final (%2)`notebook_isolated_execution=False` + `allow_legacy_live_notebook_execution=True` + Environmental variables, triple threshold)=Debug the back door, production is disabled.
- **LT-12(row-level ♪ Weight it all up ♪**:The decision does not trigger, maintains the status quo; it will appear in the future"We must keep it real."New business requirementsspec Reopen.
- **LT-16(roadmap Phase 3 Open grinding)**:Inkura.EXC Modelling list is zero; real data against experiments are recorded**Visible external dependency waiting for user input**(= Now, the new plan.A-3/T4-3).
- **LT-17((regular review mechanism)**:Three rounds have been shaped and implemented (2026)-06-13 / 06-21 / 07-02);Spacing= For each 2 completed–3 A round of focus reviews in one phase.
- **LT-18(V3+ (Dialogue reservoir)**:2026-07-03 I used to use multiple users/Deployment pack/Decision-making engine/Multi-machine schedule/Real time surveillance access includedV3+.**2026-07-17 Undoed**:Move AllV2 Tracks. Current caliberroadmap:V3/V4 Only for future needs.major Disconnected decisions, omissionsV2 backlog Water reservoir.

## 5. Local work product in the warehouse root directory (never been used)git Tracked, deleted)

| Documentation| Theme| Disposal|
|---|---|---|
| CODE_REVIEW_2026-06-13.md / -round2 / -round3 | 2026-06-13 Code review three rounds| Bydocs/reviews/ Series Replace|
| CODEBASE_DESIGN_AUDIT_2026-06-13.md | Design audit of the code library| Superseded by follow-up comprehensive audit|
| REVIEW.md | V2.1.19 Six.UI Final acceptance and acceptancereview(CLEAN,Tiebase `9845e907`) | Release of evidence byrelease tag anddocs/reviews/ Take over.|
| marvis/agent/word_conclusion_writer.md | Word Draft conclusion template (code not quoted)| Dead file, delete|

## 6. Keep document map (currently in force)

**Authoritative documentation (maintenance)**:

- `README.md`,`DESIGN.md`,`docs/roadmap.md`,`docs/versioning.md`,`docs/capability-status.md`,`docs/runbook.md`,`docs/notebook_contract.md`,`docs/notebook_submission_requirements.md`,`docs/branding.md`,`docs/sample_weight_guide.md`,`docs/deploy-linux-env-checklist.md`,`docs/ks_baseline/README.md`,`CONTEXT.md`((b) A glossary of fields).

**Plans and evidence still in force**:

| Documentation| Why?|
|---|---|
| docs/superpowers/plans/2026-08-13-next-90-days-development-plan.md | Current 90-day implementation plan (development based on this)|
| docs/plans/v2-real-materials-reconciliation-checklist.md | T4-3 Manual steps for real material reconciliation remain in effect|
| docs/plans/specs/v2-validation-batch-spec.md | Byroadmap Reference to batch model validation specifications|
| docs/reviews/2026-08-09-v2-3-0-release-readiness.md | Bycapability-status Quoted release readiness review|
| docs/reviews/2026-08-10-comprehensive-code-review-remediation.md | Updated review record|
| docs/reviews/closure-public-ks-2026-07-24.md | T4-2 PublicKS Evidence of the door.|
| docs/reviews/closure-real-materials-machine-check-2026-07-24.md | T4-3 Pre-screen evidence.|
| docs/reviews/closure-smoke-2026-07-24.md | Smoke Evidence of silence|
