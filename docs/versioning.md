# Version and release rules

This document defines the version of the document as naming, publishing, sending,tag andforward-port Rules. Product phase and uniform terminology`docs/roadmap.md`.

## Current version line

- **V2.x**:Current main line and all defined product ranges; complete in addition to existing multiple workflowsStrategy/Portfolio Workbench,The organization is isolated from production governance, movement control alerts, real-time scoring, decision-making engines and more robust enforcement.`docs/roadmap.md` Yes.
- **V1.1.x**:Model validation compatibility base capacity, already includedAgent Memory Foundation;Memory only supports interpretation, recommendation, historical comparison and audit, and does not change the definitive validation results.
- **V1.0.x**:The previous stabilization model certification line.
- **V3/V4**:Retain only for possible future usemajor Label, not currently distributed product capacity, nor may it be delayedV2 The range of reservoirs has been identified.
- **Open Default**:No private`workspace/branding/` Configure the open source safe running form.

## Version Number Format

The product version is called semantic version number:

```text
V<MAJOR>.<MINOR>.<PATCH>
```

Example:

- `V1.1.1`:V1 History of compatibility linespatch Version.
- `V1.2.0`:Same.major Add user visibility insideminor Version.
- `V2.1.8`:V2 The main line is stable.patch Version.
- `V2.2.0-alpha.1`:V2.x Advance release version of the visible capability of a new group of users.

Meaning:

- `MAJOR`:Changes in product lines or structures, e.g.,V1 Present.V2.
- `MINOR`:Same.major Additional user visibility capabilities are added while maintaining existing process compatibility.
- `PATCH`:Disorders, compatibility, file correction, distribution tool repair, minor experience correction.
- `alpha` / `beta` / `rc` Waiting for pre-published suffix to be used as nodes that cannot be used as stable public versions.

## When will the update be made?

Version update is defined as the boundary "to form identifiable, rollable, demonstrated or releaseable nodes".

If you need to update the version or release the record:

- Published toGitHub Or other far away.
- Hit the stable demonstration line or delivery versiontag.
- User Visiblebugfix To be stable.patch.
- Add, delete or change user-visibility, reporting calibre,API contracts,Notebook contracts,Agent Behaviour, memory behavior,Plugin Behavior or document commitment.

Other Organiser

- Local tests.
- feature branch Intermediate submission.
- Not issued for temporary debugging.
- Pure formatting or small internalization, unless it is itself a delivery node.

## Releasehelper

No nudity in public distribution`git push` Manual Movetag.Unique use`scripts/release_push.py`,Let the version metadata,release commit,annotated tag And it's consistent with the long-range push.

Defaultpatch Published:

```bash
python scripts/release_push.py --bump patch
```

minor / major Published:

```bash
python scripts/release_push.py --bump minor
python scripts/release_push.py --bump major
```

Specified version:

```bash
python scripts/release_push.py --version V1.1.0
```

AssignV2 Advance release:

```bash
python scripts/release_push.py --version V2.0.0-alpha.1
```

Advance Postfix only supported`alpha.N`,`beta.N`,`rc.N`.tag UseSemVer Style
(For example:`V2.0.0-alpha.1`),Python The package metadata will be automatically written.PEP 440 Style
(For example:`2.0.0a1`).

Preview:

```bash
python scripts/release_push.py --bump patch --dry-run
```

Create locally onlyrelease commit andtag,No transfer:

```bash
python scripts/release_push.py --bump patch --no-push
```

Time of implementation: general functionality, repair or document modification completed and validated first, using genericcommit Submitting these changes; confirming`main` After the area is clean, run again.release helper.Do not run when there are unsubmitted changesrelease helper,And don't create it first.release commit I'll go back to business.commit.

Order of recommendation:

```bash
git status --short
git diff --check
git log -1 --oneline
python scripts/release_push.py --version V1.1.0
```

Script will execute:

1. From the latest stable`V<MAJOR>.<MINOR>.<PATCH>` tag Calculate the next version (or use)`--version` Specified stability/Pre-publication version) and check targettag Not at all.
2. The workspace is required to be clean and on target branches.
3. Update`pyproject.toml`,README,runbook,Notebook Requires a version of metadata.
4. Create Versionbump commit.
5. Createannotated tag.
6. Unless`--no-push`,Otherwise...push `main` And newtag.

Releasetag Considers it immutable. After posting, you find a problem and you fix it and create the next one.patch Version, Do Not Move Oldtag.

### Windows Install Package

Releasetag The blogger says:Windows Personal computer installation package asrelease Attached Process Build, Not`scripts/release_push.py` directly generated. The builder must beWindows x64,and installPython,micromamba andInno Setup:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\packaging\windows\build-installer.ps1
```

The product is`dist\windows\MARVIS-Setup-<version>-win-x64.exe` Same name`.sha256`.Install package to include privatePython runtime andOpenJDK runtime,The user machine doesn't need preloading.Python,Java,Git,conda,WSL orDocker.Build scripts run first`marvis version`,Coreimport and built-inJava smoke check;Uploadrelease It should be clean before it's too late.Windows Double-click installation in user environment and confirm`/api/health` and the first page can be opened.

## Parallel maintenance andforward-port

V1 It can be stable, and at the same time,V2+ In independenceworktree Or branch development.V2 And the subsequent version cannot be lost.V1 The act was confirmed.

Rules:

1. **Hold on.V1 Compatibility stability**

   V1.1 The model certification contract remains compatible:Notebook variables,PMML Comparison, definitive indicators, reporting outputs, manual models andAgent No auxiliary authentication can be made.V2 Platform-based changes destroyed.

2. **V2 Current main line platform**

   V2 It can be changed.Agent planner,Plugin/Tool/Hook runtime,Workflow Implementation, extension and new operationsworkflow.IfV2 Impact of changesV1 Compatibility, must be designed./spec/The route document contains the reasons for the migration and supplements the regression test.

3. **V1 fix I have to.forward-port**

   Just...V1 It's about stabilizing the process, reporting output,Notebook Compacts, front-end status, downloads, mission life cycle,branding,The issue of the compatibility of the publication of tools, memory behaviors or deployments is not a problem.V2+ It should be synchronized whenever it exists.

4. **Use Prioritymerge orcherry-pick**

   Do not manually copy the code.

   ```bash
   # Yes.V2 worktree SynchronisingV1 Rehabilitation
   git switch <v2-branch>
   git merge <v1-stable-branch>

   # Yes.V2 worktree only one syncV1 Rehabilitation
   git switch <v2-branch>
   git cherry-pick <v1-fix-commit>
   ```

5. **Pre-emptive behaviour in conflict**

   - V1 The user's visible behaviour and regression tests cannot be lost.
   - V2 The same behaviour could be achieved through a new architecture.
   - IfV2 I'm changing.V1 Behavior, must be justified and a new contract tested.

6. **Tests are the basis of the conflict.**

   forward-port Then run the corresponding regression test. There's no test.V1 fix,The minimum useful testing should be supplemented.

## Worktree Rule

Long-term parallel maintenancemajor line Use independents from time to timeworktree,Avoid pollution of services, caches and non-submission of changes.

Recommended form:

```text
/path/to/marvis-v1   V1 Stabilization line andV1.1 memory Line
/path/to/marvis-v2   V2 plugin/tool runtime Line
```

Clear path for maintaining parallel product lines:

```text
Only/path/to/marvis-v1 DevelopmentV1.1 memory.
Only/path/to/marvis-v2 DevelopmentV2 plugin/tool runtime.
```

Do not switch back and forth in a workspacemajor line,Unless the mission itself is...forward-port Or conflict management.

## Branding With Open Versions

Change onlybranding Do not create new product version.Branding Fromworkspace-local File is run on time configuration.

Rules:

- No, I'm not.branding Use open during configurationMARVIS Default value.
- Localbranding Configure Paths to`workspace/branding/brand.json`.
- Privatelogo,Name of institution, address of the Intranet, customer sample, localbranding Assets may not be submitted to open warehouses.
- The source code default asset must remain publicly available.

## Check before posting

At least:

```bash
git status --short
scripts/check
```

If it's just a document revision, it's usually just a document revision.`scripts/check --skip-pytest --skip-ruff --skip-node`.The final statement indicates the reasons for not running the code test.

Check must run without before posting`--affected`/`--fast` Complete`scripts/check`.Optional Plus`--audit` Run!`pip-audit` DependencyCVE Scan (printing the cause of skipping without installation, does not fail).

The facility is available for the development of the workspace.`conda run -n py_313 python -m pytest ...` and
`conda run -n py_313 python -m ruff check ...` Conducting the same group of inspections; publicREADME/runbook Example still uses normal
`python`,Avoiding the use of individuals.conda Environment is written as a user installation prerequisite.

This machine is visible if it needs to use a specified environmentPython:

```bash
PYTHON=/opt/miniconda3/envs/py_313/bin/python scripts/check
```
