# Methodology: from claim submission to business decision

## 1. Start with the decision—not the model

The question was whether a claims team could reduce manual processing without allowing payment errors to erase the savings.

A **claim** is a provider's request for payment. A **payable outcome** means the submission is ultimately eligible for payment under the project's outcome process. The operational decision happens earlier: approve automatically or send it to review.

Keeping these concepts separate matters. A claim can need review and still be valid. A claim can pass visible checks and later prove nonpayable.

## 2. Build a useful comparison population

Public CMS data supplied procedure-level submitted amounts, allowed amounts, payments and denied-service summaries. These aggregates describe groups of services; they do not provide individual patient histories.

The project therefore generated 24,000 reproducible demo submissions, calibrated where possible to CMS 2023 benchmarks. It included routine claims, duplicates, corrections, missing documentation, coverage failures, billing anomalies and legitimate unusual claims.

Each submission received an independent eventual payment outcome. The model did not create its own target. This avoids the circular result of teaching a model to repeat a rule and then claiming it discovered payment validity.

The scope covers five procedure codes and office services. The [source notes](docs/DATA_SOURCES.md) explain the public benchmarks; the [assumption register](docs/ASSUMPTIONS.md) distinguishes them from project design choices.

## 3. Organize the data around the claims workflow

Three source tables hold **claims**, **patients** and **providers**. Separate outcome evidence records what was ultimately payable and when that information became known.

PostgreSQL runs locally and turns these records into a documented `claim_features` table. One row represents one submission attempt, so a correction counts as another administrative submission rather than a new patient encounter.

The analytical flow is:

**CMS benchmarks → operational records → historical SQL features → probability model → approval policies → cost and payment-error comparison.**

## 4. Look backward from each submission

For each incoming claim, SQL asks questions such as:

- How many claims had this patient or provider submitted recently?
- How long had it been since a similar service was observed?
- What did earlier, completed provider claims tell us about payable history?
- How did the billed amount and units compare with earlier submissions for that procedure?
- Were there visible coverage, documentation or billing exceptions?

The key restriction is **only use information already available at submission**. Earlier claims whose outcomes were still unknown could not contribute payment outcomes. Current and simultaneous submissions were excluded from their own history.

These controls prevent data leakage: using future knowledge to make past decisions appear more accurate than they could have been.

## 5. Develop the score in time order

| Period | Purpose |
|---|---|
| Jan–Sep 2025 | Learn relationships between available features and eventual payment outcomes |
| Oct–Nov 2025 | Adjust predicted probabilities to observed outcomes, a step called calibration |
| Dec 2025–Jan 2026 | Choose the automatic-approval threshold using cost and an error constraint |
| Feb–Jun 2026 | Evaluate the final policies on 6,627 later submissions |

Development records were used only when their outcomes were available by the relevant cutoff. The final period was kept separate from model fitting and threshold selection.

A gradient boosting model estimated the probability that a submission would be payable. The selected threshold was **0.955**. This is an estimated probability requirement, not a guarantee of payment accuracy. The validation error constraint was a project choice, not a CMS standard.

## 6. Compare three routes through the same workload

The manual baseline sends everything to review. Basic checks automatically approve submissions without the modeled intake exceptions. Checks plus score adds the probability threshold to those same checks.

A high score cannot override a failed check. Everything outside the automatic-approval conditions goes to review; no automatic denial is modeled.

Applying all three policies to the same submissions makes the trade-off visible without confusing different case mixes with policy performance.

## 7. Count the cost of being wrong

The analysis measures approval volume, review volume, incorrect approvals, handling effort and total decision cost.

**Net savings = avoided review expense − automatic-processing expense − incorrect-approval costs.**

The default incorrect-approval cost includes $250 remediation plus the scheduled Medicare payment proxy. Submitted charges are not used as payment losses. Correct payments are treated as common across policies and excluded from the comparison.

Review costs, error costs and thresholds are varied to show how sensitive the decision is to assumptions. Processing times are explicit scenarios rather than observed operational improvements.

## 8. Interpret the result as a trade-off

Basic checks approved 88.4% automatically but allowed 159 incorrect approvals. Adding the score reduced automatic approvals to 77.3% and incorrect approvals to 59. Net savings increased from approximately $56,762 to $73,194.

The combined policy therefore gave up some throughput to reduce payment-error costs. It still referred valid claims for review and did not eliminate incorrect payments.

Reliability checks also exposed a limitation: probability calibration slightly worsened the final Brier score, a measure of probability prediction error. The calibration step was not presented as an improvement simply because it had been performed.

When review became cheaper and incorrect approvals more expensive, manual processing became preferable to the combined policy at its existing threshold. The preferred decision therefore depends on costs as well as predictive performance.

## 9. Check the analysis before making a recommendation

Validation checks source checksums, record counts, historical timestamps, cost arithmetic and saved results. Tests deliberately change future records and verify that earlier features do not change. Both notebooks are executed and retain their calculations and figures.

These checks support the internal consistency of the analysis. They do not establish production readiness. The limited procedure mix, simplified payment rules, perfect-review assumption and excluded implementation costs constrain interpretation.

## 10. Recommend the next business step

Checks plus score is the stronger candidate under the default assumptions. The next step would be validation on representative claims with actual processing costs and matured adjudication evidence, followed by shadow evaluation before changing payment routing.

Monitor incorrect-payment dollars, valid claims sent to review, processing time and probability reliability alongside the automatic-processing rate. Success means improving the overall claims operation—not maximizing one metric.

For technical evidence, see [Notebook 1](notebooks/01_data_and_sql.ipynb), [Notebook 2](notebooks/02_decision_economics.ipynb) and the [SQL files](sql).
