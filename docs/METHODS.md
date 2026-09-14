# Decision design and analytical limits

**Question:** which incoming Part B submission attempts can be auto-approved, and what do throughput, payment error and total decision cost look like under each policy?

## Policy contract

1. **Manual:** every attempt is reviewed. This benchmark assumes accurate adjudication.
2. **Checks:** automatically approve only if coverage/enrollment pass, filing is timely, documents are present, and no correction, modifier, duplicate, unit, place-of-service or billing exception is present.
3. **Checks + score:** apply the same checks, then require calibrated P(payable) ≥ threshold. The default threshold is chosen before opening the holdout.

Everything else is referred for review; referral is not a denial. No automatic rejection is modeled. Auto-processing rate therefore equals auto-approval rate in this project. Unusual valid cases may be routed to review and incur cost/delay, but they retain a payable final outcome. The project concerns straight-through processing, not fraud identification or review ranking.

## Event model and time

The generator first samples an operational/clinical event using public procedure-level denial incidence, latent provider workflow quality and predeclared drift. The event creates a final payable outcome. Intake fields are imperfect observations of that event. The learned model never creates or relabels the outcome. Unobserved medical-necessity and documentation failures remain after checks.

`claim_outcomes` is a separate derived evidence artifact. Current-claim outcomes and event types are prohibited from model inputs. Historical outcomes enter a provider aggregate only when both submission and adjudication timestamps are strictly before the new submission. Corrections are separate attempts linked to an earlier invalid original. Attempts, rather than unique clinical episodes, are the operational cost denominator; repeated attempts are intentional.

| Stage | Submission dates | Labels available before | Use |
|---|---|---|---|
| Train | Jan–Sep 2025 | Oct 1, 2025 | Fit fixed feature model |
| Calibration | Oct–Nov 2025 | Dec 1, 2025 | Fit logistic probability calibration |
| Validation | Dec 2025–Jan 2026 | Feb 1, 2026 | Select threshold with cost and error guardrail |
| Holdout | Feb–Jun 2026 | Sep 1, 2026 | Final untouched evaluation |

Within the first three periods, rows whose labels have not matured by the next cutoff are excluded from fitting/tuning, but their intake can contribute to later submission history. This maturity selection may underrepresent slow documentation cases; all holdout outcomes mature by the evaluation date. No refit occurs after threshold selection. Scenario curves on the holdout are descriptive sensitivity, not a second optimization set.

SQL uses `RANGE ... 1 microsecond PRECEDING` to exclude current rows and simultaneous peers. Lateral joins independently enforce strict availability predicates. Rolling procedure mean and SD are fitted from prior submissions, not from full-data medians. Code-level CMS dollar centers are fixed before the simulation. Entity IDs are not predictors. Future corruption and timestamp-tie tests execute against PostgreSQL.

## Economic equations

For an auto-approved claim: cost = auto cost + I(nonpayable) × (wrong-approval remediation + scheduled payment × loss multiplier).

For a reviewed claim: cost = review cost. Correct benefit payments are common to policies and excluded from the comparison.

**Net savings = N × review cost − policy cost.** Gross avoided review cost is displayed separately. Handling hours sum assumed staff/processing minutes; mean turnaround includes a fixed queue delay for referred claims. These are scenario estimates, not queueing or causal productivity estimates.

Wrong-auto-approval rate uses auto approvals as denominator; wrong approvals per 1,000 uses all submissions. Wilson intervals describe binomial sampling variability and do not capture provider clustering; a separate provider-cluster bootstrap describes net-savings variation. Calibration uses Brier, log loss, ECE and count-weighted reliability bins. AUC is secondary because payment decisions depend on probability and cost.

## Interpretation boundaries

CMS denied services are not identical to final invalid submission attempts: denial may change after correction, unit counts differ from attempts, and public aggregates suppress cells. The calibration audit makes this comparison explicit. Complete-cell aggregation mixes modifiers and specialties, whereas the demo is a simplified office stream.

The experiment uses a common historical adjudication clock for all policies, isolating the routing comparison. Faster auto decisions do not feed back into future provider history. Operational deployment would require event-driven replay with policy-dependent histories, concurrent duplicate locking, versioned eligibility/enrollment, complete CMS/MAC edit libraries, multi-line adjudication, secure handling of identifiable data, reviewer-error modeling and prospective validation. No production policy recommendation follows directly from a portfolio scenario.
