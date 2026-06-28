# 2026-08-10 All-warehouse code review and re-engineering

**Date:** 2026-08-10

**Modalities:** Main process correction, multiple independentssubagent Read only review; not pending, not submitted, not published.
**Scope:** HTTP/Share host boundaries,Draft Generate and re-establish, run the plugin and historical transport,URL Capture, Task/Output services, data aggregation, front-end proxy mount paths, dependence and static door barriers.

## Conclusions

Proofable from this roundP0/P1/P2 All are code repair and targeted return. The focus of the overhaul is not to continue to accumulate a blacklist, but to change the trust boundary to a verifiable certificate, restricted language, durable identity receipt and ownership of atomic resources.

And then all the way to the warehouse.pytest The production code snapshot of this working tree was completed:**12,208 passed,11 skipped,32 warnings,Time-consuming 1:55:07**.The automated tree test file, which was tightened upon completion, was verified in a separate document, as detailed in the evidence below.

## High priority issues closed

### CR-01 / P0:Share hostloopback No longer equals a certified user

Settings`MARVIS_LOCAL_TOKEN` The past is anonymous.loopback The first page will manage local and pluginsbearer token WritingHTML;Another process of sharing the mainframe can inherit the capacity of private reading and writing and plugin management.

- [`marvis/app.py:199`](../../marvis/app.py#L199) Only the deployed direct proxy endend is used as the forward border;XFF Trust is not granted in itself.
- [`marvis/app.py:497`](../../marvis/app.py#L497) Require private readingBasic(token is the password) or`X-Marvis-Token`,Write requests only for visible`X-Marvis-Token`,Avoid browser cacheBasic .
- Certified private response and home page use`no-store`;First Page At the same time`Vary: Authorization`,I won't.token Hand it to an uncertified or remote reader.
- [`docs/runbook.md`](../runbook.md) and[`docs/deploy-linux-env-checklist.md`](../deploy-linux-env-checklist.md) Synchronise DescriptionBasic bootstrap,Visible Writingtoken,Credible Proxy OverrideXFF andHTTPS Request.

Independent review did not reveal private ownershipGET/HEAD,unsafe (a) The conflicting high faith in the meaning of the request, credible representation or cache;`tests/test_app_security.py` 46 Passed, certified/API Adopted in combination with 75 items.

### CR-02 / P1:Draft No more relyingPython Blacklist and keep the limit when it's back on the line.

OriginalDraft AST gate Allow language structure and global objects with loaded modules to be bypassedbuiltins;The change is then run as a normal plugin, lostDraft Limit.

- Add[`marvis/draft_language.py:181`](../../marvis/draft_language.py#L181),Here.Draft Language v1 A list of visible authentication syntax, name, attributes, call and limited capacity.
- Draft Source Removedimport ControlledAST Upward, use minimumDraftContext;Run without providing rawimporter Or complete host context.
- [`marvis/plugins/manifest.py:266`](../../marvis/plugins/manifest.py#L266) It's...`DraftPromotionReceipt` Willdraft,Plugin Name/Version/Validation values, tools andexecution profile Tie it up.
- [`marvis/plugins/registry.py:216`](../../marvis/plugins/registry.py#L216) Move historical work by receipt or a verifiable time line; old source not clearDraft Mark as`draft_repromotion_required`,Yes.resolve,planner andrunner None of them is enforceable.

It is a strict set of small languages and operational boundaries that should not be expressed as arbitrary against hostility.Python It's...OS/container Segregation. Need to enforce arbitrary third partiesPython , process should be used/Packaging class isolation and minimum host privileges.

### CR-03 / P1:Validation of (needs to review) is no longer a success

[`marvis/pipeline.py:1399`](../../marvis/pipeline.py#L1399) There's only consistency.PASS The government has been able to make the final decision.REVIEW andFAIL All in.`REVIEW_REQUIRED`.The corresponding replicability is covering a small amount of inconsistency.REVIEW Status.

### CR-04 / P2:URL CapturedSSRF,Re-lock and responder ceilings tight

[`marvis/drafts/web_search.py:51`](../../marvis/drafts/web_search.py#L51) Accept onlyHTTP(S),Refusal of evidence and non-globalization/Mixed the solver address and keep the verified address bound during the redirection and connection phase; it disables environmental agents, limits the number of jumps, limits the declaration and actual current response size, and refuses to compress content to avoid a defunct post-pressure limit.

OrientationDraft/Web Test to cover private addresses, mixDNS,Redirection, re-locking, response caps and normal open address control paths.

## Closed core correctness and consistency issues

- `slice_aggregate` Now ask source column sorting keys to both`group_by`,or selected;avoidingDuckDB Yes.`GROUP BY` ♪ And then accept it illegal ♪`ORDER BY`.See[`marvis/agent/adhoc_analysis.py:219`](../../marvis/agent/adhoc_analysis.py#L219) and[`marvis/packs/data_ops/tools.py:2265`](../../marvis/packs/data_ops/tools.py#L2265).
- The memory loss after the failure has been isolated:SQLite/Memory records will never be replaced.notebook,See the original failure of the indicator or report.[`marvis/pipeline.py:2131`](../../marvis/pipeline.py#L2131).
- AuthenticationExcel Other Organiser`ArtifactUnitOfWork`;Father's affairs will not stay.`.staging/excel_images`.See[`marvis/pipeline.py:1283`](../../marvis/pipeline.py#L1283) and[`marvis/output/excel.py:45`](../../marvis/output/excel.py#L45).
- The return of the automatic rule tree abnormal path is no longer more a long life.pytest ProcessFD Total, but directly authenticate the creation of this testsource FD,snapshot FD andParquet reader They're just closing; they're successful, they're not.schema Failures, failures of implementation andABA Paths are covered. No changes to the production closure logic are made because 500 inspections andFD The list does not prove a leak in production.

## Front-end compatibility with deployment

Front end before the end`/api/...` Asorigin-root URL,Yes.JupyterHub It's...`/user/.../proxy/.../` Mounting down will jump out the application prefix.

- API wrapper,XHR,Download links,iframe Preview,Plan Rail andMarkdown Co-sources of the experienceAPI The links are changed to the relative application base.
- [`marvis/static/js/url-safety.js`](../../marvis/static/js/url-safety.js) Co-source first.API Verify, return againapp-relative Address;[`marvis/static/js/render-agent.js:296`](../../marvis/static/js/render-agent.js#L296) Yeah.Markdown Use the same rule.
- Return of 418 Passes and Add`document.baseURI` YesJupyterHub proxy Prefixed decryption contract.

## Validation of evidence

- Final full-scale:`conda run --no-capture-output -n py_313 python -m pytest -q -x`:**12,208 passed,11 skipped,32 warnings,Time-consuming 6,907.68s**.warning For what?LightGBM API Discarded, fixed budgetMLP Unaccompanied and compatible samplingAPI discard;no failure orerror.
- Safe, safe.Draft,Plugins,pipeline,Data aggregation, front end and audit-related combinationspytest:**855 passed**.
- Automatic rule tree file:**26 passed**;of which resource closure target examples andABA The examples have been adopted separately.
- Return to front end of impact:**418 passed**;And then there's something else.candidate/static/artifact Group**372 passed**.
- Ruff(`marvis` and`tests`),64 A static.JS It's...`node --check`,`git diff --check`,`uv lock --check --offline`,Bandit Baseline and`scripts/check --fast --audit --skip-pytest`:Averageexit 0.
- `pip-audit` Use lock dependency instead of environment arbitraryconda Package; no known gaps in this report.

## Remaining borders and follow-up recommendations

1. **Shared mainframe deployment is a configuration compact.** Set up a secure workspace when necessary`MARVIS_LOCAL_TOKEN`;JupyterHub/Reverse agent must overwrite forwarding header with a credible proxyHTTPS.`MARVIS_ALLOW_REMOTE_READ` It is a clear transport option that reduces the private read-out borders and does not apply to scenarios that require isolation from air tenants.
2. **Draft Compatibility is intentional tightening.** Unable to prove history of originDraft They're gonna ask for a new correction; this is to avoid a default retreat.unrestricted plugin.Check these entries and arrange for rewrite before going online/Re-correct.
3. **Validation of syntax can continue to harden (%1)P3).** Turning the path.receipt Verify value in`manifest.json` Before writing, it is not a tree-wide Hashy of the final directory. It does not constitute a certified round bypass for execution (in the current round).restricted loader Could not close temporary folder: %s/profile),But if the field is to have the meaning of "full deployment works Hashi" it should be designed in isolation from itself.canonical manifest/source hash.
4. **Environmental acceptance and acceptance still need to be performed.** Local return is not a substitute for real.JupyterHub,Real reverse agent,Windows Signing of original documents semantics, authentic materials and those responsible for production.

## Decision

**PASS(Local code and automated door-bar).** Not currently retained known unclosedP0/P1/P2;The deployment and separation of the border described above should not be misreported as (automated local acceptance).
