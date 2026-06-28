# V2 Model validation multi-model specifications

## 1. Target and product boundary

Multimodel validation**No, it's not.**Independent front-screen entrance. Only Model Validation is retained on the welcome page; a dialogue box is created to create a default line of material to add a Model.

| Number of Models when Created| Tasks seen by users| Report|
|---|---|---|
| 1 | Validation of existing single modelAgent Workstation| The modelWord + Excel,**No, no.**Generate SummaryExcel |
| 2–10 | Same set of dialogues/Stepbar/Evidence area; internal user father/Sub-mission quarantine.| ModelsWord + Excel,**And...**A summary of non-recosted indicatorsExcel |

It repeats the scans that are validated by single models.PMML Rating, certainty indicators and reporting chain, without a second set of validation algorithms.N≥2 The inside is still going.`validation_batches` Schedule.

The functions of the batch are to organize, isolate, restore and aggregate:

- Create separate sets of materials`validation` Submissions, each of which is to be retained in its own state, contract, evidence,Word Reporting andExcel Analytical report.
- Parental task to save batch membership, overall progress and (only)N≥2)SummaryExcel,Do not flatten the single model to free text.
- Subtasks performed in creation order; current version is not rated in parallel to the same setUI Evidence.
- The default "automatic review" after multiple models are created: it is not necessary to say "start" or "continue" to each model. The contract automatically confirms and runs with the only result identified; and stops at a time of conflict, confirming the current model and then continuing the follow-up model.
- Failure of individual sub-missions must not prevent subsequent sub-missions.
- The table can be kept for cross-checking.
- No automatic selection of the champion model. No selection of the champion model.OOT KS The ranking is interpreted as productive and does not substitute for the findings of the independent certifying officer.
- Old non-Agent `run_validation_batch` **No way.**Skip the conclusion confirmation door, not silently in the back.Word.N≥2 OutWord Go on the task.Agent job(Automatic reviews automatically review the calibration confirmation findings and report them on a single model).

Old independent "volume model validation" welcome card deleted. Existing final batch tasks can still be downloadedWord/Excel/, no longer serve as the creation portal for new missions.

## 2. Creation contract

N=1 Go to the existing ones.`POST /api/tasks`(or the PEF model created) and do not put an empty layer of batch shell.

N≥2 Let's go.`POST /api/validation-batches`,Receive batch names (with first model names), certifyers and 2–10 individualitem.Every one.item It must be visible that:

- Model names and optional versions;
- Notebook,Samples,PMML and the data dictionary has four clear file characters.

The four categories of files for the first model are classified by role from the upload area of the Unified Creation Dialogue; the subsequent model is uploaded by each of the four categories. The files for the second model are not copied to the first model.

The platform must standardize the path and verify the material role. No two characters in the same set can be reused. The creation failed without a semi-father job or an isolated batch directory.

Current multi-model mode of running fixed to`agent`,And connect.`WIRED_AGENT_TASK_TYPES`.Indicators, status and final batchoutcome By the platform code.

## 3. Status machine and confirmation door

Parent batch status:

```text
created -> running -> awaiting_confirmation -> running
                                      \-> completed
                                      \-> partial_failure
                                      \-> failed
```

Agent Workstation (Pilot)N≥2 Created by default "Autoreview" and pressordinal Start a child task by oneAgent job.Automatically confirm and score the contract when it is clear./Indicators/Conclusions/reporting;current model entry in case of conflict`awaiting_confirmation`,Continue the follow-up model after confirmation. Re-up of uncompleted batches will continue and completed batches will not run again.

Old.`POST /api/validation-batches/{id}/start` runner Press stillordinal Scan all operational subtasks for user-identifiable subtasks to enter`awaiting_confirmation`,And no silent confirmation of the contract, no silent writing.Word.That path is no longer the same.Agent The portal is automatically implemented after the desk is created.

Run while father is on task`active_job_kind` I have to keep it.`validation_batch`.The details are first checked, but the father's job is still on the line.job The front end cannot be cleared before it is closedbusy Status.

## 4. Implementation, failure to isolate and restore

Contractsready The recovery phase of the sub-mission duplicate model:

1. `scan`
2. `pmml_scoring`
3. `metrics`
4. Draft conclusions identical to single models; automatic review of the recognition of calibre and report under single models
5. If the contract is ambiguous or the user stops, confirm and continue the model.Word/Excel

Every one.item It's...stage,Error code and open error files processed at borders are independently and permanently. The anomaly only lasts for the currentitem Mark as`failed`,The cycle continues on the next one.

Process is in.queued job The government has not started or is running an unexpected exit.startup recovery The event must be closed.job,Release Father Taskbusy state and reduce the batch to an interpretable and retryable failure. Open error shall not release an absolute path outside the permitted material root directory.

## 5. Results and download contracts

Every one done.item Keep the current single model download address:

- `validation_report.docx`:Word (a) Validation reports;
- `validation.xlsx`:Structured analysis and indicator reporting.

**As Model Number Only≥ 2** , the father task atoms are generated`validation_batch_summary.xlsx`.The workbook contains two tables:`Model validation summary`(Audit door-bargaining, manual checking of links) and`Summary of operations`(The following is a list of the following:YYYYYearMMonth validationNModel; validityKS Industry caliber×100 A decimal, stability.PSI Two, consistency./Recoverability/The green light of integrity.N=1 No summary may be generated or displayedExcel.

Batch final rule:

- Allitem (a) Has passed or only needs manual review:`completed`;If the father's mission is reviewed,`review_required`.
- At least one failed, but not all:`partial_failure`,The father's mission is`review_required`.
- Allitem Failed, or failed to aggregate report generation:`failed`.

The single model reports that have been successfully generated must be retained regardless of the final batch. The aggregation failure must not delete or overwrite these reports.

## 6. Front-end interactive contracts

- Only the Model Validation card is kept on the welcome page; a dialogue box is created to add a model.
- N=1 The project will be launched in the next few days.
- Multimodel task displays dialogue, step bar, current model evidence area; no longer hidden`progressRail` / notebook / metric.
- Tables are used only as an attachment to the overview; do not use the " point table cells " as the main path.
- URL `?task=<parent>&item=<child>` Focus only on line matching/Projection, no.child Raises to the current top level task on the left.
- Delete, generic scan or general-purpose material modification shall not destroy the father or the sonmembership.

## 7. Safety and inspection

At least verify before release:

- N=1 No batches, no aggregations.Excel;N≥2 The first step is to create batches and generate aggregations.
- schema Rejects more than 10 additional fields and incomplete materials;
- Path boundaries, symbolic link output directories, repeat material paths and open error dissensitization;
- Moreitem (a) Fixed order, continuation of individual failures, partial failure only retrying of failure items;
- The dialogue is still available "by this means" and the dialogue is not "by this means"
- Single ModelWord/Excel All retained, summaryExcel Downloadable and not recalculated for certainty;
- Father Jobactive job Life cycle, collapse recovery and recurrence of conflict;
- Wide desktop real browser complete: welcome page single entry, add model, dialogue confirmation, running, downloading item by item, aggregate download.

Real materials, independent authentication of signatures, birthWindows The file occupancy and production movements are not supported by synthesis tests of this specification or by local browsers.
