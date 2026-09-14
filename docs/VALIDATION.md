# Validation evidence

This edition contains the SQL, Python analysis and executed notebooks for the default run described in the README.

## Execution

Both notebooks were executed again from this publication folder against local PostgreSQL 17.5. They completed without cell errors and retain tables and figures. The analytical exports cover 24,000 submissions and a 6,627-submission chronological holdout.

The original full pipeline generated the data, executed the SQL, fitted the model and calculated the policy results. This publication pass re-executed the notebooks and checked the retained results; it did not refit the model.

## Checks

The test suite checks deterministic generation, CMS source checksums and suppression, feature availability, outcome maturity, legitimate exceptions, independent cost arithmetic, extreme thresholds and agreement between decision records and summary metrics. PostgreSQL fixtures test simultaneous submissions and confirm that changes to future records do not alter earlier features.

Publication checks verify completed notebook outputs, chart files and document links. The machine-readable result is in [tests.xml](../results/tests.xml).

## Interpretation

These checks support reproducibility and consistency within the defined analysis. They do not establish that the decision policy is ready for operational Medicare payment processing. The [methodology](../methodology.md) and [assumption register](ASSUMPTIONS.md) describe the limits.
