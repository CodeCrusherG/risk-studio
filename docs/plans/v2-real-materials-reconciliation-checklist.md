# Real-material reconciliationChecklist(3rd floor data test. 3rd floor.

> **Attribution**:Trust-First Planned (archived to[docs/history-archive.md](../history-archive.md) §2.1)T4-3;The third-level data test.**Manual acceptance floor**(First floor=Counter shape injection.CI,Second floor.=Open Data Set End to End+KS Baseline, third floor=This list.
> **Use**:Phase T The manual step to shut down. No.CI——It requires real business materials and external calibre (financial)/Provision/The only person who can sign is the known statement.**Every new real data set that you access, run this list.**.
> **Basis**:2026-07-04 8 data syntax confirmed in full read code reportbug All Diversions"Real data compared to test data dirty"——The list cross-checks the Platform ' s outputs against external factsheadline Numbers, put"Numbers go straight to decision-making."From assumption to signature.

## Use method

For each real business data set that is accessed, the itemized, measured and external caliber values are recorded, and signed.→ Block the portal and return to the corresponding repair item.

### - Let's run the machine pre-screening.

Pre-reading of planned, step-in evidence envelopes, model cards and real products, automatic check-ups
A/B/C/D I'm sure it's something that you can determine from the evidence in the warehouse, but...**No external calibre or signature.**:

```bash
python scripts/closure_acceptance.py \
  --workspace workspace \
  --task-id <completed-real-material-task-id> \
  --join-task-id <completed-join-task-id-for-the-same-material> \
  --vintage-task-id <completed-vintage-task-id-for-the-same-material> \
  --output docs/reviews/closure-real-materials-machine-check-2026-07-24.md \
  --json-output <temporary-output.json>
```

- The modelling plan itself is already covered.JOIN Time to omit`--join-task-id`;Otherwise, we have to import the same copy.
  The real stuff is done.JOIN Mission.Vintage Semantics must be passed.`--vintage-task-id` Provision.
- History block:[closure-real-materials-machine-check-2026-07-24.md](../reviews/closure-real-materials-machine-check-2026-07-24.md).
  It is a failed snapshot of the old script, not the current acceptance pass evidence, and must be regenerated according to the above parameters.
- `PASS/FAIL` (a) from evidence of durability;A1-A6,B4-INTERNAL,B5-INTERNAL,C/D
  No more allowed`N/A` Go around.`MANUAL` Only for items for which an external ground truth or sample signature is required.
- The current machine failure must be repaired; after repair, the machine must be repaired.**B1-B5 External caliber reconciliation and the signature of the responsible person on this page are the only artificial blockage allowed for retention**.
- No synthetic data, platform itself, orAgent The text is summarized in (external calibre sources) and may not be signed.

---

## A. Data compacts and dirty shapes (relationships)T1,Access is on the way.

| # | Checkpoint| How?| By judgement| Actual| Signature|
|---|---|---|---|---|---|
| A1 | sentinel Value| Whether the value column contains-999/-9999/9999 Wait for the sentry.| If yes, confirm pre-treatment chainsentinel step(Rating-999 (Inappropriate value)| | |
| A2 | vintage Label Semantics| bad Yes, sir."It's new and bad."Or is it?"Quickshotever-bad" | The Quickshot must be in place.gate Statementsnapshot,Curve value reasonable (not stalely high)| | |
| A3 | NULL/No Tab Line| Is the sample empty?/Non-0/1 Label| bad_rate The parent removes unmarked lines.gate Showunlabeled_count | | |
| A4 | LongID Keys| ID number./Do you have a cell phone number?float64 Storage,>15 bit| join Key matches normal or triggers precision red flag (not 100% silently not matching)| | |
| A5 | Space/Zero Fill Key| join Whether the key contains a blank or a lead zero code| Blank keys match well (Performance Column)NULL),Zero Filling Key Crosses Filedtype Unanimously| | |
| A6 | TimeOOT | Is it specified?time_col | Non-alignment listing triggers the time.OOT(Non-quiet random cut)| | |

## B. Headline Numbers to external calibre (core reconciliation, manual layers outside the two-way reconciliation)

| # | Numbers| Platform outputs| External caliber sources| By judgement| Actualvs caliber| Signature|
|---|---|---|---|---|---|---|
| B1 | **vintage Cumulative bad debt rate** | Policyvintage Curve| Financial/Age bad debts in risk departments| Same age as the othercohort Volume level is consistent (not one order of magnitude)| | |
| B2 | **GroupEL(total_el)** | analysis EL estimate| Provision/Impairment caliber (US$)IFRS9 (or internal)| Reference Scatter MoonEL Consistent with the level of the required calibre (no)~N ♪ I'm not even taller ♪| | |
| B3 | **Groupbad_rate** | slice_aggregate | Known sub-channels/Monthly bad accounts statement| Slice badness rates are consistent with the report (after removal without label)| | |
| B4 | **ModelKS** | Modelling reporttest/OOT KS | Independent recalculation or historical model| OOT KS In the reasonable space, with the champion.gate Evidence.selection_metric Complimentary| | |
| B5 | **join Match Rate** | join propose/confirm gate | Manually check for sample key matching| Double-track reconciliations without red flags; sample key matching and displaying consistent| | |

## C. Evidence and interaction (reciprocal)T1 (Category of evidentiary distortion)

| # | Checkpoint| How?| By judgement| Signature|
|---|---|---|---|---|
| C1 | The winner's choice is evidence.| Look.train_models gate Evidence sentence| Show Trueselection_metric(I'm not writing about death."PressOOT KS"),Direction term corresponds to the actual size| |
| C2 | Digital trace| Expandgate The blood details of the numbers.| Every one.headline Digital tape data sets fingerprints/Code Version/Parameters/seed | |
| C3 | Red flag for reconciliation| I'm gonna feed you a data that's not gonna be the same.| When reconciliations are inconsistentgate Break the red flag.AUTO You can't confirm it automatically.| |

## D. Methodology (compacting)T1-D,Modelling over and over again.

| # | Checkpoint| By judgement| Signature|
|---|---|---|---|
| D1 | The selected feature is not leaking.| Yes.OOT Only selectedtrain Proposed (in %2)IV/corr Does Not Containtest Label)| |
| D2 | screen NaN Door.| HamNaN When tabingscreen Trigger confirmation door (instant silence counted on labeled subset)| |
| D3 | refit Indicator integrity| refit Backheadline No random 5%test_ks;Model card descriptionpre-refit/Variance in deployment| |

---

## Signature and conclusion

- Dataset identifier:____________　Access date:____________　Executing:____________
- Machine pre-screening report:____________　The machine pre-screening concluded:____________
- AllA/B/C/D Pass.→ The data setheadline Figures can be used directly in decision-making.
- Any one of them won't pass.→ Record, block, back-check and rerun the list of repairs.

> **Relationship to the export of the receiving officer**(DoD-11 Revision:Phase T Shut up.= First tier (injectors)CI All Green+ Second tier (public data sets)KS Accomplishment)+ This list (signed by at least one genuine material)+ Round of scopereview(Just fix it.critical/high,Don't recycle.
