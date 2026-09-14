SET search_path TO stp;
DROP TABLE IF EXISTS claim_features;
CREATE TABLE claim_features AS
WITH intake AS (
 SELECT c.*,
   (service_date BETWEEN p.coverage_start AND p.coverage_end
      AND coverage_response = 'active') AS coverage_ok,
   (service_date BETWEEN v.enrollment_start AND v.enrollment_end) AS provider_enrolled,
   (submitted_at::date > (service_date + INTERVAL '1 year')::date) AS late_filing,
   EXTRACT(DAY FROM submitted_at-service_date)::integer AS submission_lag_days
 FROM claims c JOIN patients p USING(patient_id) JOIN providers v USING(provider_id)
), history_windows AS (
 SELECT i.*,
   COUNT(*) OVER (PARTITION BY patient_id ORDER BY submitted_at
     RANGE BETWEEN INTERVAL '90 days' PRECEDING AND INTERVAL '1 microsecond' PRECEDING) AS patient_prior_90d,
   COUNT(*) OVER (PARTITION BY provider_id ORDER BY submitted_at
     RANGE BETWEEN INTERVAL '90 days' PRECEDING AND INTERVAL '1 microsecond' PRECEDING) AS provider_prior_90d,
   COUNT(*) OVER pw AS procedure_prior_n,
   AVG(submitted_amount / units) OVER pw AS procedure_prior_mean,
   STDDEV_SAMP(submitted_amount / units) OVER pw AS procedure_prior_sd,
   AVG(units::float) OVER pw AS procedure_prior_units,
   MAX(submitted_at) OVER pw AS procedure_history_max_at
 FROM intake i
 WINDOW pw AS (PARTITION BY procedure_code ORDER BY submitted_at
   RANGE BETWEEN INTERVAL '90 days' PRECEDING AND INTERVAL '1 microsecond' PRECEDING)
), asof_history AS (
 SELECT w.*, r.previous_submission_at, r.previous_service_date,
   (w.service_date-r.previous_service_date)::float AS repeat_service_days,
   h.provider_matured_n, h.provider_payable_n,
   -- Fixed Beta(9,1) prior is a design assumption; no whole-dataset prior.
   (h.provider_payable_n+9.0)/(h.provider_matured_n+10.0) AS provider_payable_rate,
   h.provider_outcome_max_at, d.suspect_duplicate
 FROM history_windows w
 LEFT JOIN LATERAL (
   SELECT MAX(c.submitted_at) AS previous_submission_at, MAX(c.service_date) AS previous_service_date
   FROM claims c WHERE c.patient_id=w.patient_id AND c.procedure_code=w.procedure_code
     AND c.submitted_at < w.submitted_at
 ) r ON true
 LEFT JOIN LATERAL (
   SELECT COUNT(*) AS provider_matured_n, COUNT(*) FILTER(WHERE o.payable) AS provider_payable_n,
      MAX(o.adjudicated_at) AS provider_outcome_max_at
   FROM claims c JOIN claim_outcomes o USING(claim_id)
   WHERE c.provider_id=w.provider_id AND c.submitted_at<w.submitted_at
     AND o.adjudicated_at<w.submitted_at AND c.submitted_at>=w.submitted_at-INTERVAL '180 days'
 ) h ON true
 LEFT JOIN LATERAL (
   SELECT EXISTS(SELECT 1 FROM claims c WHERE c.patient_id=w.patient_id AND c.provider_id=w.provider_id
     AND c.procedure_code=w.procedure_code AND c.service_date=w.service_date
     AND c.place_of_service=w.place_of_service AND c.submitted_amount=w.submitted_amount
     AND c.modifier=w.modifier AND c.submitted_at<w.submitted_at) AS suspect_duplicate
 ) d ON true
)
SELECT *, submitted_amount/units/NULLIF(procedure_prior_mean,0) AS amount_ratio,
 (submitted_amount/units-procedure_prior_mean)/NULLIF(procedure_prior_sd,0) AS amount_z,
 units/NULLIF(procedure_prior_units,0) AS units_ratio,
 (units > CASE WHEN procedure_code='97110' THEN 6 ELSE 2 END) AS units_exception,
 (coverage_ok AND provider_enrolled AND NOT late_filing AND documentation_present
   AND NOT billing_exception AND NOT suspect_duplicate AND correction_of IS NULL
   AND modifier='' AND place_of_service='11'
   AND units <= CASE WHEN procedure_code='97110' THEN 6 ELSE 2 END) AS checks_pass
FROM asof_history;
ALTER TABLE claim_features ADD PRIMARY KEY (claim_id);
COMMENT ON TABLE claim_features IS 'Intake and strict as-of history only. Current outcome and latent event are excluded.';
ANALYZE claim_features;
