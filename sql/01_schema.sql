-- Run only in a dedicated project database. Operational inputs stay in three tables.
CREATE SCHEMA IF NOT EXISTS stp;
SET search_path TO stp;
DROP TABLE IF EXISTS claim_features, claim_outcomes, claims, patients, providers CASCADE;
CREATE TABLE patients (
 patient_id integer PRIMARY KEY, birth_year integer NOT NULL,
 coverage_start date NOT NULL, coverage_end date NOT NULL,
 CHECK (coverage_end >= coverage_start)
);
CREATE TABLE providers (
 provider_id integer PRIMARY KEY, specialty text NOT NULL,
 enrollment_start date NOT NULL, enrollment_end date NOT NULL
);
CREATE TABLE claims (
 claim_id integer PRIMARY KEY, patient_id integer REFERENCES patients,
 provider_id integer REFERENCES providers, procedure_code text NOT NULL,
 service_date date NOT NULL, submitted_at timestamp NOT NULL,
 units integer NOT NULL CHECK (units > 0), submitted_amount numeric(12,2) NOT NULL CHECK (submitted_amount > 0),
 scheduled_payment numeric(12,2) NOT NULL CHECK (scheduled_payment >= 0),
 place_of_service text NOT NULL, modifier text NOT NULL,
 documentation_present boolean NOT NULL, coverage_response text NOT NULL,
 correction_of integer REFERENCES claims, billing_exception boolean NOT NULL,
 CHECK (service_date <= submitted_at::date), CHECK (correction_of < claim_id)
);
-- Separate adjudication evidence: forbidden as current-claim model inputs.
CREATE TABLE claim_outcomes (
 claim_id integer PRIMARY KEY REFERENCES claims,
 payable boolean NOT NULL, adjudicated_at timestamp NOT NULL,
 outcome_reason text NOT NULL, event_type text NOT NULL
);
CREATE INDEX ON claims (patient_id, submitted_at);
CREATE INDEX ON claims (provider_id, submitted_at);
CREATE INDEX ON claims (procedure_code, submitted_at);
CREATE INDEX ON claims (patient_id, provider_id, service_date, procedure_code);
CREATE INDEX ON claim_outcomes (adjudicated_at, claim_id);
