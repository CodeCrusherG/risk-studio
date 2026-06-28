# V2 Model validation module upgrade plan

Status: Achieved, release validation in progress.

Basis: Models validate problems found in practice; examples of people and channels are generalized.

Relevant specifications:[v2-validation-batch-spec.md](v2-validation-batch-spec.md),[docs/roadmap.md](../../roadmap.md)

## 1. A word of purpose.

Put what's done.**Single Model ValidationAgent Workstation**Expand to add multiple models at a time: only the "model validation" is retained on the welcome page; 1 can be added when created–N Package of materials. Add only one to be the same as the current single model validation, without generating aggregationsExcel;I've added more than one set of conversations./Sequenced validation in the steps and an additional summaryExcel.

User's ideal path:

```text
Click Model Validation→ Create dialogue box to add multiple models (default one)
  → Individual models say "start validation" in dialogue; default "Autoreview" after multiple models are created, automatically executed in sequence
  → Agent List the identification results and only the entries identified by the user
  → I'm gonna see every single scanned model./ Score/ Indicators/ Conclusions
  → Every one of them.Word/Excel;As Model Number Only≥ 2 And then another summary.Excel
  → After reading it, the dialogue is modified and regenerated
```

No other authentication algorithms, no nine models.KS/AUC/PSI SqueezeAgent Free text.

## 2. The platform that we're getting from this real experiment.

These problems are happening on the real path, not on synthetic tests.

| Problem| phenomena| Gene.|
|---|---|---|
| Welcome page to two entrances.| [Model validation and "volume model validation " ; batch entry in the back of table, click on contract/Start, right step and evidence area hidden. Father's mission even`run_mode=agent`,Sending messages will also be 501.| Create and`task_type` Open by the entrance.UI:`welcomeValidationBatchCard`;`app.js` Yeah.batch Hide`progressRail` / notebook / metric.Backend:`WIRED_AGENT_TASK_TYPES` Does Not Contain`validation_batch` |
| The mass can hardly see the results of the single model.| (a) The parent job is only a summary table;`?task=parent&item=child` Just highlight lines, don't open the model conversation./Figure/Indicators| Specifications§6 - No, I'm not.child Raise to current task on left;completeAgent UX Select a different sub-task|
| The bulk will write its own conclusions, and the bulk will come out of it.Word | After the mission,`_write_report_conclusions` Directly Generate & DropWord,The user doesn't have a single model for a "confirming conclusion" conversation.| `marvis/validation_batch_runner.py` - Put it on.Agent One step behind the dialogue door.|
| Cover placeholders are always empty.| Word Stay.`{{TEXT:drafter}}` wait;page "Report field" appears to be of value| `GET /report-fields` Use`default_report_values()` **Presentation**Default value;Agent OutWord Only those stored in the library.`report_values`.Page creation will write to author/Date/Sample definition,API/Batch creation almost unwritten|
| The report cannot be revised in dialogue| Tasks`succeeded` Back`POST /report` returns 409; this time only re-fields outside the platform, locally re-emergenceWord.User sawWord/Excel When not satisfied, cannot be modified and generated during the dialogue| Reporting period allowed only`writing_artifacts` / `review_required`;Agent There's no "transformation."→ RevertWord/Excel]Closed|
| The file is written in letters.| T The card summary and the "user requesting the letter" are wrong.| Default template sentence is a letter; workspaceWord The template killed the "user applying for a letter"|
| Dictionary Missingimportance Times experience is bad.| Scan directly failed; this time the external operator has to fill the column manually, and the user does not see "what column is missing and how" in the conversation| `feature_metadata.py` - Put it on.importance (a) To be filled in;Agent/The explicit reminder on the door of the contract is not to change the column to optional|
| Agent The gate is broken.| Each set must start→ Confirmation of contracts→ Keep score.→ Continue indicators→ Continuation of conclusions→ Confirm.Word] | The user also has to say "continue" at the low-risk stage; the volume is more like a contract form for each model point|
| SummaryExcel Inconsistencies with the Business Sheet| Platform Batch Audit (Byline)PMML/Pressure/Integrity/SubmissionID);What we really want this time isKS×100 A decimal,PSI Two, green.| `validation_batch_excel.py` Not the same as the certificationer's custom sheet.|

The binding force remains unchanged:Notebook contracts,PMML Comparison,KS/AUC/PSI By the platform;Agent No indicators can be created or evidence can be bypassed.

## 3. This is an outsider's decision-making exercise.

2026-08-19 When running the nine set, a lot of judgment happens.MARVIS Outside.+ Script+ Click. The goal for the upgrade is:**These judgements are to be made by the platform as far as possible.Agent The user is advised to apply only those items that are ambiguous or responsible.**

### 3.1 Decision-making checklist and handover

| Who's deciding this time?| Specific content| Who should I give it to?| What else do the users do?|
|---|---|---|---|
| External operator| No "model validation"(Manual).ipynb],Select tapeRMC It's...notebook | **Platform Scan**By Role+ RMC Detection; multiple copiesnotebook TimeAgent List Candidates| Just pick one in multiple conflicts.|
| External operator| 06/08 Use`Data dictionary.xlsx` Not`Data dictionary_20260810.xlsx` | **Platform**Press "Renewed non-backup"/ The first time that the document is written, the first time that the document is written, the first time that the document is written, the first time the document is written, is written.Agent Which one is it?| The user said "supplex" for "other."|
| External operator| Missing`importance` When a manual column outside the platform is available to scan| **Platform scan still requiredimportance Required**;When you're missing, you write "Data dictionary missing" in dialogue and contract doorsimportance,Please re-scan after adding. ".0,And don't change the column to optional.| Continue after the reminder supplement|
| External operator| Target column`y`,Severation`split_tag` or`model_flag`,Time`loan_actv_dt` or`apply_dt`,PMML Output`probability_1` | **Platform field recognition already selected**;Agent Summarize the recommendations in one sentence, and be confident and non-conflictable to follow automatic mode| Confirm a sentence when conflict or faith is compromised|
| External operator| Time particle picks day or moon.| **Platform**See column value pattern (date)vs `YYYYMM`);Still written in the contract| Confirm when the pattern is in conflict|
| External operator| Algorithms, running or not.Notebook | V2 Already.PMML Rating, no training.notebook;**No more user questions** | None|
| External operator| "Continue" "Confirm" every step.| **Agent Auto Mode**:After scanning, scoring, indicators automatically move into the next stage; only contract ambiguity, draft conclusions, releaseWord Stop!| Each model is about 1–2 Sub-confirmation, not 5–6 Number of times|
| External operator| Author/The reviser writes the default position before the actual certifying officer| **Platform**Write with "Certifier" when creating a task`TEXT:drafter` / `TEXT:revision_author`,Don't.LLM Guess what.| Fill in name once when creating|
| External operator| (a) Model overview, scope of application, good and bad sample sentences;T The card is used instead of the one that is spent.A Card Retention Letter| **Agent Drafting+ User confirmation**((See section 5)| Read the draft, say "Push this" or change the caliber.|
| External operator| Group name: Self-employed GeneralTCut./ Channel One.TCut./ Channel 2/ Channel 1 and Channel 2| **Platform**Parsing from user-provided model names; leaving user-supplied when no clear boundaries do not maintain the agency hard-coded list| Add a sentence when name does not contain guests|
| External operator| Re-script locally after successful taskWord | **PlatformAgent Report modified closed loop**:User indicatesWord/Excel What's wrong?Agent Only allowed narrative fields are modified and reconfirmed and regeneratedWord **and** Excel,No need to run again.| What to change in the conversation? Download the new report after confirmation.|
| External operator| 9 Report download+ Handwritten SummaryExcel | **Models Only≥ 2** Time the platform generates operational matrices and supports package downloads; individual models only come out of the modelWord/Excel,No summary generatedExcel | None|
| Must stay with the user| Whether the material is intended for this inspection; if the definition of the business of the bad sample is not available in the material; and whether the signature is eventually used| People| Upload, confirm, and see the conclusions.|

### 3.2 How much pressure should the user handle be on?

Single model:

```text
Now: Create→ Start Authentication→ Fill/Point contracts→ Keep score.→ Continue indicators→ Continuation of conclusions→ Confirm.Word → If placeholder is empty, reset field and report
Objective: Create (with the name of the certifying officer)→[Start validation."→ The contract is clear, and the draft report is completed.→ We're gonna have to check the file.Word/Excel → If you are not satisfied with the reading, continue the dialogue and then change it.
```

Multimodels (two or more added when created):

```text
Now: take another "volume model validation" card→ Table Gerry by model point confirmation of contract→ Point Start Batch→ I can hardly see the process.→ Download separately
Target: Still point "model validation" and add multiple models to the same creation box→ Same set of dialogues and steps→ Run automatically after creation (no need for each model to say "start" and "continue")→ The contract was compromised before we stopped to confirm it.→ Switch to see the results of each model→ ModelsWord/Excel + A summaryExcel
```

Auto Mode Only**Low risk, evidence of platform**The contract conflicts,A/T Unable to judge from name, not in sample definition material, ultimatelyWord The file still requires the user)s express consent. This is consistent with the existing (automated model only for low-risk nodes) and does not make certification undeserved.

## 4. Target product form

### 4.1 Workstation: Single modelAgent Same shell.

- Intermediary: dialogue+ Scan for the current model/Score/Indicators/The conclusion area (now in bulk).
- Right: Stepbar. Individual models remain scans/ Score/ Indicators/ Reporting. Multiple models, batch steps (materials)→ Contracts→ Model-by-model validation→ The current model scans are attached below/ Score/ Indicators/ Report.
- Do not use the " point table cells " as the main path. When there are multiple models, the tables are used as an attachment to the overview, or as a model switchbar for the result area.

### 4.2 One entry, add multiple models

Welcome Page**Only keep Model Validation**,Removes a separate "volume model validation" card. Click to open the same creation dialogue box: Default a line model material to "add a model".

| Number of Models when Created| Tasks seen by users| Report|
|---|---|---|
| 1 | Validation with Current Single ModelAgent Same (dialogue, steps, evidence area)| The modelWord + Excel.**No, no.**Generate SummaryExcel |
| 2–10 | Same workspace; toggle to see model results| ModelsWord + Excel,**And...**A summary of non-recosted indicatorsExcel |

Fathers still available internally/Subtasks are separated from multiple sets of materials (contracts, indicators, reports). This is the same "model validation" mission for users, not the second product. A single model does not have an empty layer of batch shells to avoid a "sum to be generated" in the stepbar and download area.

- Users are always in the current validation dialogue.
- (a) When there are multiple models, the sub-task is the execution module;Agent Organization 'Fixing 3/9 …],And project the evidence of the model to the middle zone.

Existing`validation_batches` Tables, sequenced execution, unblocked individual failures, silent confirmation of contracts, which could be left to**N≥2** . The hard gap that must be changed:

- Connect multi-model missionsAgent API(`WIRED_AGENT_TASK_TYPES` Or message path to currentchild),Otherwise, the dialogue will not be delivered.
- runner No more skippingcontinue / The conclusions confirm the door; the phase is projected to be in the father ' s dialogue.
- UI No longer replaces multiple models with separate tables backstages.

### 4.3 Create Dialogue

File selection is the only necessary point. The dialogue box adds "Add Model" to the existing model validation stream:

- Each line remains the model name/Version+ Notebook / Sample/ PMML / Dictionary.
- The certificationer only fills it once and writes in all the model authors./Revisioner.
- Only one line of work goes by.`POST /api/tasks`(Or the PEQ model created)`/api/validation-batches`.
- Two rows and above and multimodel creationAPI.
- The ceiling is still recommended 10; the floor is 1 and no more "approvals at least 1" is required–10 The government has to make a decision on the issue.

## 5. Report placeholder: available for handing overLLM,But it's a layer.

**Yes, but it's almost off.** `generate_word_conclusions` Three keys only:`TEXT:pressure_test_summary`,`TEXT:pressure_impact_recommendation`,`TEXT:final_validation_conclusion`.Overview, scope of application, good and bad samples, authors absentLLM JSON White list. Batch creation subtasks`TaskCreate` No, I don't.`report_values`,The cover key library is empty. The blank field should have been out.Word FormerAgent Fill out the draft. It's not an external script.`PUT /report-fields`.

Layer:

| Fields| Who fills it?| Rule|
|---|---|---|
| Author, reviser, date, revised note| Platform| Name of the person who certified it+ (a) The day;LLM No name to be made up|
| Summary of the model, scope of application| Agent Draft| (a) Retain the sentence;T Card "Staff Link"/ The project is being implemented in the following areas:A Card "Letter Link"/ Letter application phase; prohibition of "this model"; client group deciphering from model name|
| Bad/Good sample definition| Agent Draft| Templates are prefixed for "positive (bad) sample: " , only red-worded parts, e.g.`MOB6 Overdue>= 30 Oh, my God.` / `MOB6 Not overdue`;MOB Take from name, default for days past due or default for user 30 and indicate assumptions|
| Sample crowd phrase| Platform orAgent | The template for "Users applying for letters" should be replaced with "Users applying for letters":T The card "applicators for user use" is a very important tool for the development of the project.A The card "Putting for Letters"|
| KS/AUC/PSI,Sample cycle, training rate| Platform| Keep moving.`COMPUTED_REPORT_TEXT_KEYS`,LLM No change.|
| Pressure statement, final validation conclusion| Agent Draft+ Confirm.| Existing`generate_word_conclusions`;The single model should confirm that the bulk is not written silently in the back.|

Elements of achievement:

1. The creation task (which contains a mass) must be the one to write the cover identity field to the library, which is the same as the page creation.
2. After the completion of the target, add the "draft reporting file" phase:LLM output only permitted narrative keys;numbers from`validation_results` Injecting hints. Stop writing models.KS.
3. User confirms (reconfirmable) in dialogueWord/Excel.
4. `GET /report-fields` Distinguishing between "real value in library" and "show with default value" to avoid the re-emergence of "page with words,Word Yes.`{{TEXT:}}`].
5. **Report revision of closed loop (in English)Word andExcel (Equal application)**:Mission in.`succeeded` / `review_required` The user says "overview to expense" "bad sample" is written in the following text:MOB6 Overdue>= 30 The day after the day, "return the letter of the conclusion" and so on.Agent Update allowed narrative fields, display draft differences, regenerated after user confirmationWord **and** Excel.Do not run againPMML/The revised curriculum vitae (modified by the person, date, description) is updated by the Platform by this confirmation.KS/PSI The number of people who are not in the world is a matter of certainty.Agent Rejected and pointed to the computational evidence.
6. Multi-model Tasks (Multimodal Tasks)N≥2), the dialogue defaults to "Model currently being looked"; user name "3" or model name is to be used to re-modify the model report to the corresponding sub-task; reset the summary if necessaryExcel.No aggregation of individual modelsExcel,The revision only recreates the modelWord/Excel.

## 6. Phased delivery

Change code after approval by stage; change without approval`docs/roadmap.md` The number of people who have been killed by the attack has been reduced to the number of people who have been killed.

### PhaseA — Single model: less operation, report fill

- Create author/ writeer/(a) Date;API Create andUI Create the same set`report_values`.
- Agent Drafting of the overview after the indicator/Sample definition/A·T Validation, confirm.Word/Excel.
- Fixing Page Defaults≠ The library is median."
- **After success, the report can be changed in dialogue**:Open Task→ NoteWord/Excel Unsatisfactory→ Agent Draft reclassification→ Revert two files after confirmation./Sample definition newWord Without the words,Excel Synchronization of report pages,KS The number remains unchanged."
- Low-risk phase supports automatic mode running (scoring)→Indicators) the only matching contract can recommend "continue with the result of identification" instead of opening an empty drop point.
- Dictionary`importance` **Keep Filled**.Scan failed to close when missing, butAgent The missing and completed form must be indicated in a readable text, prohibiting manual outside the platform and the silent nature of the default.

Acceptance: use one of the nine sets of this timeT Cards, 1A Card, from the welcome page**[Model validation."**Create (one model only) toWord,Not here.`{{TEXT:}}`,T/A Correct caliber, number of confirmed user≤ 2,**No, I'm not.**SummaryExcel.

### PhaseB — Import Merge+ Multiple models are the same.Agent Shell

- The page removes the " Batch Model Validation" card; leave only the "Model Validation" card. Creates a default line for the dialogue box to "add Models".
- One line of submission of a walk-list model is created; two rows and above are multi-modelled.
- Multimodel task displays dialogue, step bar, current model evidence area; no longer hidden`progressRail` / notebook / metric.
- Model Switch (dialogue says "Four" or top part) only switch to projection, and do not turn subtasks into current top left tasks.
- Multimodelrunner No longer skips the confirmation of conclusions; each submission moves at the same stage as the single model, projecting to dialogue.
- Multi-model task connectAgent API(`WIRED_AGENT_TASK_TYPES` + `agent/start` / `messages`).

Acceptance and acceptance: no batch card on welcome page. Add 2 models and the workstation looks like model validationAgent,You can see the first model's maps and indicators and download the summary.Excel.Add only 1 model time table consistent with current single model, not aggregated in download areaExcel.

### PhaseC — Dialogue organization instead of a point-by-point approach

- [Please confirm that 9 contracts have been replaced withAgent The suggested map is presented in order (or in high letter package) and the user returns "both click this " or indicates a change in the column.
- Remove the phrase "a contract must be confirmed by a line to be activated" as the only path; the form can be left for cross-checking, with the main route being dialogue.
- Single failures continue next; father dialogue clearly indicates the reasons for the failure and the next step.

Acceptance and inspection:9 Model batches need not be "confirmed" nine times when the contract is not conflicting.

### PhaseD — Download and Summary

- Single model: only the model is availableWord/Excel,**Ban**Generate or present a summaryExcel.
- Multiple models: one-key package allWord/Excel,And generate summaryExcel.
- SummaryExcel Alignment of business habits: Title "Model validation:YYYYYearMMonth validationNModels; column with model versions, validityKS(Industry caliber×100,A decimal, stability.PSI(Two, consistency./Recoverability/Complete green light; no recalculation indicator.
- Optional second table:Agent Batch overview (reference only to database numbers, with modeltask_id).
- Once a submodel is revised and the report is re-published, the summary can be updated as necessaryExcel,No recalculation of the model indicator.

Acceptance and inspection:N=1 No summary documentation;N≥2 and 2026-08-19 Manual summary tables and structures, numbers and models`validation_results.json` Unanimously.

### PhaseE — Speculation synchronized with route

- Redo[v2-validation-batch-spec.md](v2-validation-batch-spec.md):No longer as a stand-alone front entrance; changed to model validation creation streamN≥2 , and then the specification.
- Update`docs/roadmap.md`:Delete the "volume model validation" stand-alone entry and replace it with " model validation" to support the addition of multiple models.
- Rerun the mass associated browser journey;`capability-status` Don't follow the old one until the new journey passes.VERIFIED]Meaning.

## 7. Main changes (de-task at time of implementation)

- UI:- Let's get the page off.`welcomeValidationBatchCard`;Create dialogue box with Add Model and enter Model Validation (`create-task-dialog.js` and`validation-batch-create.js` Merge or make multi-line sub-tables of material only).`app.js` Medium`selectedTaskIsValidationBatch` Stepbar/Short circuits in the evidence area should be changed to projection only when required for internal multi-model tasks, rather than to the entire page in the form.
- Organization:`marvis/validation_batch_runner.py`(The main objective of the project is to:`marvis/routers/validation_batches.py`(Sub-task creation writing`report_values`).
- Agent:`WIRED_AGENT_TASK_TYPES`(`validation_app_service.py`)Include parent assignments or visible agents tochild;`marvis/agent/service.py` Expansion of report keys allowed for drafting (still prohibited)computed keys);Father Jobturn loop Select Currentchild.The contract batch mode removes the phrase "time particle size must be selected empty-handedly" (see also the text below).`requireExplicit: batchMode`),For Recommendation for Identification+ The dialogue confirmed.
- Reporting:`marvis/report_fields.py`,`marvis/routers/report_fields.py`,`marvis/routers/validation_stages.py` It's...report Status machine (state)`succeeded` Re-entry is still permitted;Agent The message is sent by the "Revision of the Report" intent; the work areaWord The template says "user applying for a letter" .Excel `Text of the report` sheet andWord Share the same set of confirmed`report_values`.
- Scan:`marvis/validation/feature_metadata.py` Keep asking.importance;We've got a failed case.Agent Dialogue/The contract door, after which users are reminded to update the dictionary, is then cleaned.
- Summary:`marvis/output/validation_batch_excel.py`.
- Test:`tests/test_validation_batch_*.py`,`tests/test_api_v2.py` Report field, front-end static assertion.

## 8. Do not do it explicitly.

- No, I don't.LLM Calculate or rewriteKS/AUC/PSI/The scores are consistent.
- No model automatically labels as champion or as input.
- You don't score the same score in parallel.UI Evidence (can be done later in parallel, first edition in order).
- The name of the certifying officer, the final adoption of the conclusion, is not submitted to the model for fabrication.
- Do not quietly confirm conflicting field maps for less.
- Do not use the data dictionary`importance` Replace with optional, and do not allow silent scanned filling 1.0.
- No summary for individual modelsExcel,The second entry for "volume model validation" is not kept on the welcome page.

## 9. Suggested approval

1. Only the "model validation" is maintained on the welcome page. Multiple models can be added when created: 1 walk-in single model validates and does not generate aggregationsExcel;2 Same set and aboveAgent Workstations, plus one summaryExcel.
2. PlatformAgent Take over the selection of materials, contract proposals, phase runs, report drafting and summary downloads made by the external operator; users only confirm ambiguities and final drafts.
3. Report narrative field byLLM Draft, confirm; identification fields and indicators remain written by the platform.Word/Excel If you're not satisfied, go on and makeAgent Dialogue modified and regenerated, no rerun validation calculations.
