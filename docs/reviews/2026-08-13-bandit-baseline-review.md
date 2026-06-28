# Bandit Baseline reconstruction and classification review (2026)-08-13)

> Schedule EntryB-5 delivery. Baseline document`.bandit-baseline.json` The project was rebuilt on the current day;
> `scripts/check` Added to Change Documentbandit Incremental check.

## Conclusions

- Baselines are not"Large list of expired":Here.CI Parameters for the same paragraph (in thousands of United States dollars)bandit 1.9.4,`-r marvis -ll -ii`)
  Rescan, currentfinding Total**83 Article**(The old baseline is the same as 83, with only 1 line number drifting).
  Large original file (9),500 Okay.JSON)It's because of every one of them.finding It's...JSON Expand about 110 lines, no.
  finding Quantity explosion.
- Difference with old baseline: Remove 1 (`packs/data_ops/tools.py:2029` B608,Line number drifting,
  Add 1 new article (same file, row 2030)B608).The net change is zero.
- Run again with a new baselineCI Same order`bandit -r marvis -ll -ii -b .bandit-baseline.json`
  Exit code 0: Launch door pass.

## 83 Articlefinding Classification

| test id | Number| Serious| Confidence| Description of classification|
|---|---|---|---|---|
| B608(f-string SQL I'm going to inject it.| 71 | MEDIUM | 71 MEDIUM | Subject.DuckDB/DataWorkspace the governance of theSQL construction;parameters from controlledidentifier Validation and ExistingDSL compiler,Non-user freedomSQL Straight-link. Baseline accepted, but attributable"It's worth a special review."Category I (see below).|
| B103(Easier File Permissions)| 3 | MEDIUM | 3 HIGH | Workspace/Temporary directory access; accepted under local single table of work model.|
| B314(xml Parsing)| 3 | MEDIUM | 3 HIGH | PMML/Document resolution path.|
| B310(urllib) | 2 | MEDIUM | 2 HIGH | Internal Upgrade/Downloading support.|
| B102(exec (Detect trigger points)| 2 | MEDIUM | 2 HIGH | - Yeah.nosec Comment's Controlled Execution Border (plugins/subprocess_worker (e) The note is still in force.|
| B301(pickle) | 1 | MEDIUM | 1 MEDIUM | Controlled work inverse sequence.|
| B317(socket) | 1 | MEDIUM | 1 HIGH | Local return loop service support.|

- 12 ArticleHIGH Trust entries are concentratedB103/B314/B310/B102/B317——NotB608.
- All 83 were clearly accepted in the baseline; no new security signals were introduced into the reconstruction.

## Follow-up Actions

1. **B608 Specialized review**(Proposed inclusion in the next review window, non-existent 90-day planP0/P1):71 Article
   f-string SQL All through, check that every input of the construction points is through.identifier White list./Type
   verifying;verifiable plus`# nosec B608` + Reason, unverifiable repair.
2. Keep the incremental door:`scripts/check` Now relative`HEAD`(or`CHECK_DIFF_RANGE`)Changed
   `marvis/*.py` File Run`bandit -ll -ii -b .bandit-baseline.json`,Addmedium/high
   finding (a) The failure of the door;`--skip-bandit` Skipped. Environment's missing.bandit ♪ And then you can't stop ♪
   pip-audit The same pattern).

## Validation records

- `bash -n scripts/check`:Pass.
- `PYTHON=<conda py_313>/bin/python scripts/check --skip-pytest --skip-ruff --skip-node --skip-diff`:
  Pass"no changed marvis/*.py files")
- `conda run -n py_313 python -m bandit -r marvis -ll -ii -b .bandit-baseline.json`:exit 0
