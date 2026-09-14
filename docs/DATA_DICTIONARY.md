# Data dictionary

Grain: one single-line submission attempt. Three operational source tables are `claims`, `patients`, `providers`. `claim_outcomes` is separate adjudication evidence, `claim_features` is SQL-derived, and `claim_decisions` stores holdout claim × policy counterfactuals. Dates use one consistent project clock without local timezone conversion.


## patients

| Column | PostgreSQL type | Nullable | Definition / availability |
|---|---|---|---|
| `patient_id` | integer | NO | Patient surrogate key; known at intake; never used as a predictor. |
| `birth_year` | integer | NO | Context birth year; not a predictor or an entitlement determination. |
| `coverage_start` | date | NO | Effective start of the coverage snapshot, known before the modeled period. |
| `coverage_end` | date | NO | Effective end of the coverage snapshot; no retrospective overwrite. |

## providers

| Column | PostgreSQL type | Nullable | Definition / availability |
|---|---|---|---|
| `provider_id` | integer | NO | Provider surrogate key; joins history, never directly a predictor. |
| `specialty` | text | NO | Descriptive provider group; demo context only. |
| `enrollment_start` | date | NO | Effective provider enrollment start, known before the modeled period. |
| `enrollment_end` | date | NO | Effective provider enrollment end, known before the modeled period. |

## claims

| Column | PostgreSQL type | Nullable | Definition / availability |
|---|---|---|---|
| `claim_id` | integer | NO | Unique single-line submission-attempt key. Corrections and duplicates are separate attempts. |
| `patient_id` | integer | YES | Patient surrogate key; known at intake; never used as a predictor. |
| `provider_id` | integer | YES | Provider surrogate key; joins history, never directly a predictor. |
| `procedure_code` | text | NO | HCPCS code, stored as text; five office-service procedures. |
| `service_date` | date | NO | Date service was furnished; used for repeat-service, filing and duplicate checks. |
| `submitted_at` | timestamp without time zone | NO | Submission timestamp, naive UTC-like project time; decision availability cutoff. No DST conversion is applied. |
| `units` | integer | NO | Billed service units, positive integer; available at submission. |
| `submitted_amount` | numeric | NO | Total submitted dollars for this attempt, including all units. |
| `scheduled_payment` | numeric | NO | Intake payment proxy: CMS payment per allowed-derived service × units, rounded to cents. Used for loss accounting, not as a target or predictor. |
| `place_of_service` | text | NO | CMS place-of-service text; 11 for the modeled office stream. |
| `modifier` | text | NO | Submitted modifier. Empty string means none, not unknown. Modifier exceptions route to review. |
| `documentation_present` | boolean | NO | Intake completeness observation, not final documentation validity. |
| `coverage_response` | text | NO | Intake eligibility-response observation: active/inactive; can disagree with eventual truth. |
| `correction_of` | integer | YES | Nullable FK to earlier invalid submission replaced by this correction. |
| `billing_exception` | boolean | NO | Visible intake billing exception. Not all final billing errors are visible. |

## claim_outcomes

| Column | PostgreSQL type | Nullable | Definition / availability |
|---|---|---|---|
| `claim_id` | integer | NO | Unique single-line submission-attempt key. Corrections and duplicates are separate attempts. |
| `payable` | boolean | NO | Eventual full-claim payable outcome. Current value prohibited from model inputs. |
| `adjudicated_at` | timestamp without time zone | NO | Time final outcome evidence becomes observable. Historical labels require this < submitted_at. |
| `outcome_reason` | text | NO | Retrospective reason for adjudication; not a model input or official CMS reason code. |
| `event_type` | text | NO | Latent generated scenario category retained only for retrospective validation; prohibited from predictors. |

## claim_features

| Column | PostgreSQL type | Nullable | Definition / availability |
|---|---|---|---|
| `claim_id` | integer | NO | Unique single-line submission-attempt key. Corrections and duplicates are separate attempts. |
| `patient_id` | integer | YES | Patient surrogate key; known at intake; never used as a predictor. |
| `provider_id` | integer | YES | Provider surrogate key; joins history, never directly a predictor. |
| `procedure_code` | text | YES | HCPCS code, stored as text; five office-service procedures. |
| `service_date` | date | YES | Date service was furnished; used for repeat-service, filing and duplicate checks. |
| `submitted_at` | timestamp without time zone | YES | Submission timestamp, naive UTC-like project time; decision availability cutoff. No DST conversion is applied. |
| `units` | integer | YES | Billed service units, positive integer; available at submission. |
| `submitted_amount` | numeric | YES | Total submitted dollars for this attempt, including all units. |
| `scheduled_payment` | numeric | YES | Intake payment proxy: CMS payment per allowed-derived service × units, rounded to cents. Used for loss accounting, not as a target or predictor. |
| `place_of_service` | text | YES | CMS place-of-service text; 11 for the modeled office stream. |
| `modifier` | text | YES | Submitted modifier. Empty string means none, not unknown. Modifier exceptions route to review. |
| `documentation_present` | boolean | YES | Intake completeness observation, not final documentation validity. |
| `coverage_response` | text | YES | Intake eligibility-response observation: active/inactive; can disagree with eventual truth. |
| `correction_of` | integer | YES | Nullable FK to earlier invalid submission replaced by this correction. |
| `billing_exception` | boolean | YES | Visible intake billing exception. Not all final billing errors are visible. |
| `coverage_ok` | boolean | YES | Service within known coverage dates AND intake response active. |
| `provider_enrolled` | boolean | YES | Service within known provider enrollment dates. |
| `late_filing` | boolean | YES | Submission date exceeds service date + one calendar year. Exceptions are referred, not automatically denied. |
| `submission_lag_days` | integer | YES | Integer calendar-day lag from service to submission. |
| `patient_prior_90d` | bigint | YES | Prior submissions for this patient in [submitted_at−90 days, submitted_at); same-time peers excluded. |
| `provider_prior_90d` | bigint | YES | Prior submissions for this provider in the same strict 90-day interval. |
| `procedure_prior_n` | bigint | YES | Procedure submission count in prior strict 90-day window. |
| `procedure_prior_mean` | numeric | YES | Mean submitted dollars per unit for this procedure in prior strict 90 days; NULL at cold start. |
| `procedure_prior_sd` | numeric | YES | Sample SD of submitted dollars per unit in prior 90 days; NULL when fewer than two observations. |
| `procedure_prior_units` | double precision | YES | Mean units per submission in prior 90 days; NULL at cold start. |
| `procedure_history_max_at` | timestamp without time zone | YES | Maximum contributing prior submission timestamp, for leakage audit. |
| `previous_submission_at` | timestamp without time zone | YES | Latest earlier submission for same patient and procedure; NULL if absent. |
| `previous_service_date` | date | YES | Maximum service date among earlier submissions for same patient/procedure. This can be later than the current service date on corrections. |
| `repeat_service_days` | double precision | YES | Current service date minus maximum historical service date, in days; NULL at cold start; negatives allowed for retrospective corrections. |
| `provider_matured_n` | bigint | YES | Provider attempts submitted within prior 180 days whose adjudication was also strictly before the current submission. |
| `provider_payable_n` | bigint | YES | Payable count within that matured provider history. |
| `provider_payable_rate` | numeric | YES | (Prior payable + 9)/(prior matured + 10); fixed Beta(9,1) shrinkage. |
| `provider_outcome_max_at` | timestamp without time zone | YES | Latest contributing adjudication timestamp, for leakage audit. |
| `suspect_duplicate` | boolean | YES | Earlier matching beneficiary/provider/service/procedure/POS/amount/modifier exists; a conservative review signal. |
| `amount_ratio` | numeric | YES | Current submitted dollars per unit / historical procedure mean; NULL if no prior mean. |
| `amount_z` | numeric | YES | Difference from historical unit-dollar mean / historical SD; NULL if SD missing or zero. |
| `units_ratio` | double precision | YES | Current units / historical procedure mean units; NULL at cold start. |
| `units_exception` | boolean | YES | Units exceed local review gate: 6 for 97110, otherwise 2. Not an official MUE value. |
| `checks_pass` | boolean | YES | Deterministic auto-approval eligibility; all coverage, enrollment, filing, documentation and exception gates pass. |

## claim_decisions

| Column | PostgreSQL type | Nullable | Definition / availability |
|---|---|---|---|
| `claim_id` | integer | NO | Unique single-line submission-attempt key. Corrections and duplicates are separate attempts. |
| `procedure_code` | text | YES | HCPCS code, stored as text; five office-service procedures. |
| `provider_id` | integer | YES | Provider surrogate key; joins history, never directly a predictor. |
| `patient_id` | integer | YES | Patient surrogate key; known at intake; never used as a predictor. |
| `month` | text | YES | Submission month YYYY-MM; holdout reporting dimension. |
| `score` | double precision | YES | Calibrated predicted probability of eventual payable outcome. |
| `payable` | boolean | YES | Eventual full-claim payable outcome. Current value prohibited from model inputs. |
| `event_type` | text | YES | Latent generated scenario category retained only for retrospective validation; prohibited from predictors. |
| `policy` | text | NO | Manual, Checks, or Checks + score; mutually exclusive counterfactual policy dimension. |
| `auto_approved` | integer | YES | 0/1 route indicator; not eventual payable truth. |
| `wrong_approval` | integer | YES | 1 iff automatically approved AND eventual outcome nonpayable. |
| `reviewed` | integer | YES | 1 iff not automatically approved; no automated denial route. |
| `wrong_payment` | double precision | YES | Scheduled payment dollars on wrong auto approvals, zero otherwise, before the loss multiplier. |
| `net_cost` | double precision | YES | Review/automatic cost + remediation + unrecovered wrong payment, in USD. |
| `net_savings` | double precision | YES | Manual baseline cost minus policy net cost, in USD. |
| `handling_minutes` | double precision | YES | Assumed automatic/review handling minutes, excluding queue delay. |
| `turnaround_hours` | double precision | YES | Assumed queue + handling hours for referred claims; automatic handling only otherwise. |

`claim_features` inherits intake columns; derived-column nullable metadata reflects CREATE TABLE AS. Null historical baselines are meaningful cold starts, not zero. `raw_score` in scored CSVs is the uncalibrated model probability; `split` identifies chronological stage or maturity exclusion. The exact predictor allowlist is saved in `results/run_summary.json`.

## Analytical exports

* `policy_summary`: one row per policy, full holdout; auto rate denominator is claims, error rate denominator is auto approvals.
* `monthly`: one row per month × policy.
* `segments`: one row per event type × policy; event is retrospective only.
* `sensitivity`: one row per review cost × remediation cost × threshold × policy; full holdout, no retuning.
* `calibration`: one row per nonempty probability bin; predicted and observed payable shares, counts and Wilson bounds.
* `cms_benchmarks`: one row per procedure, 2023 POS 11 common complete-cell cohort; exact formulas in DATA_SOURCES.md.
* `calibration_audit`: procedure comparison of generated per-unit dollars/service-weighted nonpayability with public benchmarks.
* `validation_thresholds`: validation policy metrics for every candidate threshold; never holdout-selected.

