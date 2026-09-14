# Data basis and CMS calibration

The claim-level data are reproducible **synthetic demo records**, generated with seed **73129**: 24,000 single-line submission attempts, 2,200 patients and 120 providers, January 2025–June 2026. No beneficiary records or individual CMS histories are used. Outcomes represent an independent event-based adjudication process; they are not labels copied from a routing score. Results describe this portfolio scenario, not measured insurer performance.

## Public comparison population

[CMS Physician/Supplier Procedure Summary (PSPS)](https://data.cms.gov/summary-statistics-on-use-and-payments/physiciansupplier-procedure-summary), **calendar year 2023**, published/modified August 21, 2024. This release precedes every modeled submission. Five HCPCS codes (99213, 99214, 80053, 93000, 97110), **place of service 11**, all available carriers, localities, specialties and modifiers. This is a deliberately limited office-service comparison, not all Part B or all Medicare.

Pinned [2023 API](https://data.cms.gov/data-api/v1/dataset/b72adfb6-22cf-4241-9c64-050ad9061e03/data) and [original CSV](https://data.cms.gov/sites/default/files/2024-08/65dc6580-8726-4de0-b609-5138e8eff22e/Physician_Supplier_Procedure_Summary_2023.csv). Retrieval: September 13, 2026. `scripts/fetch_sources.py` records filters, pagination, raw records and SHA-256 receipts. `data/sources/cms_benchmarks.csv` contains exact numerators, denominators and transformations. Keep the pinned release for reproduction; the catalog's latest release is not used.

### Suppression and allowed services

The actual extract contains submitted-service counts, denied-service counts, submitted/allowed charges and Medicare payments. It does **not** expose a separate allowed-service count. We derive **allowed services = submitted − denied** within the same complete-cell cohort. Assigned services are not substituted for allowed services. This derived complement is explicitly labeled in every benchmark export.

An asterisk is suppressed, not zero. Retain only error-indicator 0 cells with numeric values in all five fields used by the calculation. Count excluded cells and report submitted-volume retention. This preserves approximately 97.1%–99.5% of submitted volume for the five codes, but low-volume cells are disproportionately excluded; retained-cell rates are not unbiased national estimates. The complete-cell sums remain actual public CMS aggregate observations.

| Calibrated quantity | Source/year | Comparison and transformation | Application |
|---|---|---|---|
| Base nonpayable incidence by procedure | PSPS 2023 office-service complete cells | denied services / submitted services | Baseline probability of an invalid submission event; a service-level rate is a proxy for single-line attempt validity, not an exact target |
| Submitted unit-dollar center | Same cells | total submitted charges / submitted services | Lognormal unit-dollar center before scenario anomalies and unit multiplication |
| Allowed unit-dollar benchmark | Same cells | allowed charges / (submitted − denied services) | Comparison only; not treated as the Medicare payment |
| Scheduled payment unit-dollar proxy | Same cells | NCH payment / (submitted − denied services) | Units × public historical mean, rounded to cents; not an official fee-schedule adjudication |

No CMS statistic calibrates workflow cost, handling time, entity histories, documentation prevalence, or model effectiveness. See `ASSUMPTIONS.md` for all such design assumptions. A balanced five-code mix supports readable comparisons; it intentionally differs from the observed national mix. Dollar and denial distributions will differ after exceptions, multi-unit claims and temporal drift. The calibration audit compares per-unit dollars and service-weighted denial rates as well as submission counts, with explicit differences rather than asserting an exact fit.

## Policy sources

* [Medicare Claims Processing Manual, chapter 1](https://www.cms.gov/regulations-and-guidance/guidance/manuals/downloads/clm104c01.pdf): §70 timely filing and exceptions; §120.1–120.3 duplicate processing, including physician/supplier matching elements and modifier exceptions. The demo refers these cases for review; it does not implement the full CMS denial workflow.
* [CMS NCCI Medically Unlikely Edits](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-medically-unlikely-edits-mues): motivates checks on units. Our 2/6-unit thresholds are **local demonstration review gates, not official code-specific MUE values**. Modifier, adjudication-indicator and medical-necessity exceptions require real policy implementation before operational use.
* [CMS review reason codes](https://www.cms.gov/data-research/monitoring-programs/medicare-fee-service-compliance-programs/review-reason-codes-and-statements): motivates distinguishing documentation, coverage and billing evidence from final payment validity. Our outcome-reason strings are project labels, not CMS reason codes.

Guidance was inspected September 13, 2026. These are design references, not a versioned implementation of every rule in force during 2025–26. There is no claim that this prototype adjudicates Medicare according to all applicable CMS/MAC policy.

## Earlier project inspected

[Medicare Claims Auto-Approval Pipeline](https://github.com/thrinesh13/Medicare-Claims-AutoApproval-pipeline), README retrieved September 13, 2026. It describes four features, a random stratified split, routing-based approval labels and a gross review-savings framing. This new repository introduces independent adjudication evidence, strict timestamp histories, chronological maturity controls, three policy counterfactuals, calibrated probabilities, cost sensitivity and reproducible source receipts. No earlier reported savings are reused.
