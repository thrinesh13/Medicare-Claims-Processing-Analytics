SET search_path TO stp;
DROP TABLE IF EXISTS claim_decisions CASCADE;
CREATE TABLE claim_decisions (
 claim_id integer REFERENCES claims, procedure_code text, provider_id integer, patient_id integer,
 month text, score double precision, payable boolean, event_type text,
 policy text, auto_approved integer CHECK(auto_approved IN (0,1)),
 wrong_approval integer CHECK(wrong_approval IN (0,1)), reviewed integer CHECK(reviewed IN (0,1)),
 wrong_payment double precision, net_cost double precision, net_savings double precision,
 handling_minutes double precision, turnaround_hours double precision,
 PRIMARY KEY(claim_id,policy), CHECK(auto_approved+reviewed=1), CHECK(wrong_approval<=auto_approved)
);
CREATE VIEW policy_kpis AS
SELECT policy, COUNT(*) AS n_claims,
 SUM(auto_approved) AS auto_approved, SUM(wrong_approval) AS wrong_approvals,
 AVG(auto_approved::float) AS auto_rate,
 SUM(wrong_approval)::float/NULLIF(SUM(auto_approved),0) AS wrong_auto_rate,
 SUM(net_cost) AS net_cost, SUM(net_savings) AS net_savings,
 SUM(handling_minutes)/60 AS handling_hours, AVG(turnaround_hours) AS mean_turnaround_hours
FROM claim_decisions GROUP BY policy;

CREATE VIEW monthly_kpis AS
SELECT month,policy,COUNT(*) AS n_claims,SUM(auto_approved) AS auto_approved,
 SUM(wrong_approval) AS wrong_approvals,SUM(net_savings) AS net_savings
FROM claim_decisions GROUP BY month,policy;
