# Assumption register

Every numeric design choice is either tied to the 2023 CMS transformation in `DATA_SOURCES.md` or listed here. Values are scenario settings, not externally measured operations.

| Parameter | Value / distribution | Basis and effect |
|---|---|---|
| Population and seed | 24,000 attempts; 2,200 patients; 120 providers; seed 73129 | Demo scale and reproducibility |
| Submission window | 546 days from 2025-01-01, uniform integer seconds, sorted | Covers Jan 2025–Jun 2026; no calendar workload seasonality |
| Code mix | Equal probability over five selected procedures | Portfolio coverage, not national utilization weights |
| Patient/provider assignments | Uniform IDs, except linked duplicates/corrections | Repeated entities build history; not realistic referral geography |
| Patient birth years | Uniform integers 1935–1960 | Context only; not a predictor or coverage rule |
| Enrollment records | Patients 2024–2027; providers 2023–2027 | Known prior to simulation. Intake coverage response may disagree/fail; real changing dimensions require versioned snapshots |
| Provider specialties | Three equally likely descriptive groups | Context only, not verified clinical specialty mapping |
| Provider process quality | 15% latent poor-workflow providers; incidence multiplier .35 + 4 × poor flag | Heterogeneous repeat billing quality; latent flag never enters feature table |
| Error drift | Multiply event incidence by 1.35 from 2026-02-01; cap probability at .65 | Predeclared temporal stress test, aligned with holdout |
| Invalid event shares | duplicate .22, coverage .18, billing .12, unresolved documentation .12, medical necessity .36 | Categories sampled after incidence draw. Independent clinical/billing event adjudication creates payable outcome; no model score creates labels |
| Valid exceptions | 12% of remaining valid events: unusual .35, correction .20, documentation resolved .20, repeat/modifier .25 | Legitimate exceptions prevent unusual = invalid circularity |
| Submission lag | Uniform integer 1–21 days | Intake availability context; 20% of coverage-failure events instead use 400 days to exercise late filing |
| Units | 97110: 1/2/3/4 with .18/.22/.38/.22; other codes 1 | Multi-unit stress; not CMS-fitted units distribution |
| Dollar dispersion | Lognormal sigma .30, mu = −.5 × .30² | Mean-one multiplier around CMS submitted unit-dollar benchmark |
| Unusual valid dollars | Additional uniform 1.8–3.0 multiplier; 97110 units set to 8 | High cost can still be payable |
| Billing anomaly dollars | Additional uniform 1.4–2.8 multiplier; add 1–4 units | Billing errors can have visible amount/units signals |
| Duplicate/correction links | Sample from last 150 preceding attempts; correction picks nonpayable nonduplicate original, 3% amount adjustment | Linked submission history. A correction is reviewed, not auto-paid; valid replacement assumes original payment was zero |
| Modifier exception | '59' on valid repeat/modifier events | A simplified signal requiring review, not universal modifier compatibility validation |
| Documentation visibility | Invalid unresolved docs appear complete 35% of the time; resolved-doc events incomplete at intake | Avoids equating an intake flag with final payable truth |
| Coverage visibility | Coverage failures show inactive 85% of the time | Unobserved evidence can still invalidate checks-passing claims |
| Billing visibility | 45% of billing events have intake exception flag | Allows residual errors after deterministic checks |
| Adjudication evidence lag | Uniform 5–30 days plus 30 days if intake docs missing | Frozen common evidence clock across policies; not their counterfactual completion time |
| Historical windows | Frequency/amount 90 days; matured provider outcomes 180 days | Design windows; strict earlier timestamps |
| Provider shrinkage | Beta(9,1), adding 9 payable / 10 total pseudo-observations | Fixed prior .90, never derived from future labels |
| Unit review gates | 6 for 97110, 2 otherwise | Local gates, not official MUE limits |
| Missing history | SQL NULL; native tree missing-value handling | No full-data mean imputation; counts begin at zero |
| Model | Histogram gradient boosting, 110 iterations, 9 leaves, L2=10, minimum leaf 80, early stopping off | Fixed hyperparameters before holdout; Platt logistic calibration C=1 on separate period |
| Threshold grid | .80–1.00 in .005 steps | Validation-only minimum realized cost subject to 95% Wilson upper error rate ≤2% and ≥100 approvals; otherwise threshold 1 |
| Review cost | $18; sensitivity $8/$18/$35 | Configurable operations scenario |
| Automatic processing | $0.35 and .25 minutes per auto approval | Variable per-approval cost; manual cost includes intake checks |
| Wrong approval | $250 remediation plus 100% scheduled payment; sensitivity $100/$250/$750/$2,000 remediation | Avoids confusing allowed or submitted charges with payment loss |
| Manual baseline | Perfect final adjudication; 12 handling minutes and 24 queue hours | Benchmark assumption; no manual errors, automation setup cost, queue congestion or staffing response modeled |
| Sampling interval | 1,000 bootstrap resamples of provider totals; seed + 1 | Conditional provider sampling variation, not calibration/model or real-world uncertainty |

All costs are USD, without inflation adjustment. Correct payment amounts cancel between policies. Net cost includes processing and incorrect-payment costs only. Fixed implementation costs, appeals, recoveries, delayed valid-payment harm and reviewer errors are omitted. Set payment loss multiplier below 1 to explore recoveries; it is not a recovery forecast. The manual time assumption includes completion of evidence work; the generator's label-availability lag is an observation delay and must not be presented as turnaround.
