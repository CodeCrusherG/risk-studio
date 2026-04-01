# Risk Studio Glossary of fields

This document is a glossary only: a single language for recording items (see table 2).ubiquitous language),The details of the implementation are not included.`docs/superpowers/plans/2026-08-13-next-90-days-development-plan.md`;Historical plans and reviews filed to`docs/history-archive.md`;The range of products and acceptance status are shown.`docs/roadmap.md` and`docs/capability-status.md`.

## Quality and trust

- **Trust Level (%1)Trust Layer)**:Every number of decisions that the platform presents"It's a direct decision."The common name of the entire mechanism - semantic contract door, double-track reconciliation, digital bloodline, three-tier data."Capability level".
- **Capability level (CLUS)Capability Layer)**:Expand the platform to cover the credit risk management life cycle (label construction, deployment, monitoring automation, external data access, etc.).
- **Data compacts (Data compacts)Data Contract)**:Semantics in which a tool trusts input data without validation/Shape assumptions (e.g.,"Tab Column 1=Bad","Every bad customer is only getting worse at the time of the first.").The worst model of platform failure is when the contract breaks down.
- **Semantic Compact Gate()Semantics Gate)**:Put a key data compact from"Implicit assumptions"Upgrade to"Force user confirmation"It's...typed gate.Precedents:NaN Label confirmation door.
- **Dirty shape (Dirty Shape)**:Real business data can pierce the specific form of a data contract (sentinel -999,Quick-sampling panels,NULL Labels,float64 Stores the document number, blank key, zero fill key, etc.).
- **Three-tier data test (%2)Three-Tier Data Criteria)**:Phase The main export judgement, which was replaced by"No new findings from the review":①Combat injection regression (dirty shape generator, in)CI)②Open Data Set End to End+ KS Benchmark③Manual reconciliation of real business materials.
- **Reconciliation (in millions of United States dollars)Reconciliation / (d) Double-track reconciliation)**:Same.headline Numbers are achieved independently by two (e.g.DuckDB SQL Paths andpandas The path) is calculated separately and is mandatory, and inconsistently, the red flag is blocked."Double-entry"Ideas on indicators.
- **Light blood (Little blood)Light Provenance)**:gate Minimum trace metagroups (data set fingerprints, code versions, parameters, data sets) carried by a numberseed),Distinguished from full blood map and one key replay (all behind).
- **Scopereview(Scoped Review)**:Current period onlydiff ♪ A round of reviews, only fixed ♪critical/high,Do not cycle. Differentiate from fullreview(Large re-engineering triggers as required).

## Labels and calibrations

- **Label Semantics (Physical)label_semantics)**:Two cross-references to bad label columns in panel data -**Incremental (Incremental)incremental)**:The client will only be in bad condition in the first part of the period;**Scrap (Choose)snapshot / ever-bad)**:Clients mark 1 every period from bad.vintage Cumulative calibres are correct only in the incremental type; the snapshot type input must be either marginal or converted first.
- **Stereotype (%2)Bad Definition)**:Show overtime (%)DPD/Status string) map to 0/1 Rules for bad labels, including observation periods, performance periods, overdue thresholds (30)+/60+/90+)Three elements.
- **Mature (%2)Maturity)**:A loan.cohort Is the performance period closed enough to be bad enough? In maturity.cohort . The label is not used for modelling.
- **Altitude change (%)Metric Basis Change)**:bug The restoration leads to inconsistencies between historical reports and new code numbers on the same data. The platform agrees to: directly amend, not to make old values compatible, and to include them in the release note.

## Existing core words (continuation)

- **Certain kernel (%2)INV-1)**:The calculation layer of the indicators that must be the same as the output; the two areas are at variance with the achievement of the two are a direct violation of the indicator.
- **anchor left connection**:It's a sample, it's a constant line.join pattern, the line number deviation is the hard failure rollback.
- **typed gate / Force confirmation**:Untwisted artificial identification point, carrying structured evidence.payload.
- **evidence envelope**:The tool output is accompanied by structured evidence.gate Rendering data sources.
