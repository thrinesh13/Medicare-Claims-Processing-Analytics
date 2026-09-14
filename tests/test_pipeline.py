import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.database import connect
from src.generate import generate
from src.evaluate import FEATURES,metrics,decision

@pytest.fixture(scope='module')
def scored(): return pd.read_csv(ROOT/'results/scored_claims.csv')

def test_generator_reproducible(tmp_path):
    c=json.loads((ROOT/'config.json').read_text()); c['n_claims']=250
    generate(c,tmp_path/'a'); generate(c,tmp_path/'b')
    for f in (tmp_path/'a').glob('*.csv'): assert f.read_bytes()==(tmp_path/'b'/f.name).read_bytes()

def test_source_checksums_and_suppression():
    for receipt in json.loads((ROOT/'data/sources/receipts.json').read_text()):
        raw=(ROOT/'data/sources'/receipt['file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==receipt['sha256']
    b=pd.read_csv(ROOT/'data/sources/cms_benchmarks.csv')
    assert (b.complete_cells<b.raw_cells).all()
    assert np.allclose(b.submitted_services,b.allowed_services_derived+b.denied_services)
    assert b.denied_service_rate.between(0,1).all()

def test_grain_maturity_and_available_timestamps(scored):
    assert len(scored)==json.loads((ROOT/'config.json').read_text())['n_claims'] and scored.claim_id.is_unique
    submitted=pd.to_datetime(scored.submitted_at)
    for col in ['previous_submission_at','provider_outcome_max_at','procedure_history_max_at']:
        dates=pd.to_datetime(scored[col]); assert (dates.isna() | (dates<submitted)).all()
    c=json.loads((ROOT/'config.json').read_text())
    for split,cutoff in [('train','train_end'),('calibration','calibration_end'),('validation','validation_end'),('holdout','evaluation_as_of')]:
        assert (pd.to_datetime(scored.loc[scored.split.eq(split),'adjudicated_at'])<c[cutoff]).all()
    assert not {'payable','event_type','outcome_reason','adjudicated_at','claim_id','provider_id','patient_id','scheduled_payment'} & set(FEATURES)

def test_legitimate_exceptions_and_separate_outcome(scored):
    unusual=scored[scored.event_type.eq('legitimate_unusual')]
    assert unusual.payable.all() and (unusual.amount_ratio>1.5).any()
    assert ((scored.payable)&(~scored.checks_pass)).any()
    assert ((~scored.payable)&scored.checks_pass).any()
    assert scored.event_type.nunique()>=9

def test_cost_arithmetic_independent(scored):
    c=json.loads((ROOT/'config.json').read_text()); r=json.loads((ROOT/'results/run_summary.json').read_text())
    h=scored[scored.split.eq('holdout')]; summaries=pd.read_csv(ROOT/'results/policy_summary.csv')
    for row in summaries.itertuples():
        approvals=decision(h,row.policy,r['threshold']); wrong=approvals&~h.payable
        expected=(~approvals).sum()*c['review_cost']+approvals.sum()*c['auto_cost']+wrong.sum()*c['wrong_approval_cost']+h.loc[wrong,'scheduled_payment'].sum()*c['payment_loss_multiplier']
        assert row.net_cost==pytest.approx(expected)
        assert row.net_savings==pytest.approx(len(h)*c['review_cost']-expected)
        assert row.auto_approved+row.reviewed==len(h)

def test_extreme_threshold_and_costs(scored):
    c=json.loads((ROOT/'config.json').read_text()); h=scored[scored.split.eq('holdout')]
    assert not decision(h,'Checks + score',1.01).any()
    assert np.array_equal(decision(h,'Checks + score',0),decision(h,'Checks',0))
    cheap=metrics(h,'Checks',0,c); costly=metrics(h,'Checks',0,{**c,'wrong_approval_cost':10000})
    assert costly['net_savings']<cheap['net_savings']

def test_fact_reconciliation():
    f=pd.read_csv(ROOT/'results/fact_decisions.csv'); summary=pd.read_csv(ROOT/'results/policy_summary.csv').set_index('policy')
    for policy,g in f.groupby('policy'):
        r=summary.loc[policy]
        assert g.claim_id.is_unique
        assert len(g)==r.n_claims
        assert g.auto_approved.sum()==r.auto_approved
        assert g.wrong_approval.sum()==r.wrong_approvals
        assert g.net_savings.sum()==pytest.approx(r.net_savings)
        assert g.handling_minutes.sum()/60==pytest.approx(r.handling_hours)

def test_sql_hand_calculation_and_same_time_ties():
    # Transaction-scoped fixture rolls back all changes to the real project data.
    con=connect()
    try:
        con.execute('TRUNCATE claims CASCADE')
        for i,t,amt in [(1,'2025-01-01 12:00',100),(2,'2025-01-02 12:00',200),(3,'2025-01-02 12:00',300),(4,'2025-01-03 12:00',400)]:
            con.execute("INSERT INTO claims VALUES (%s,1,1,'99213','2025-01-01',%s,1,%s,80,'11','',true,'active',NULL,false)",(i,t,amt))
        con.execute("INSERT INTO claim_outcomes VALUES (1,false,'2025-01-02 18:00','invalid','billing_anomaly'),(2,true,'2025-01-02 12:00','valid','routine'),(3,true,'2025-01-04','valid','routine'),(4,true,'2025-01-05','valid','routine')")
        con.execute((ROOT/'sql/02_features.sql').read_text())
        rows=con.execute('SELECT claim_id,patient_prior_90d,procedure_prior_mean,provider_matured_n,provider_payable_rate FROM claim_features ORDER BY claim_id').fetchall()
        assert rows[0][1]==0 and rows[0][2] is None
        assert rows[1][1]==rows[2][1]==1  # simultaneous peer excluded
        assert float(rows[1][2])==float(rows[2][2])==100
        assert rows[1][3]==rows[2][3]==0  # equal adjudication timestamp excluded
        assert rows[3][1]==3 and float(rows[3][2])==200
        assert rows[3][3]==2 and float(rows[3][4])==pytest.approx(10/12)
    finally: con.rollback(); con.close()

def test_future_perturbation_cannot_change_past_features():
    con=connect()
    try:
        before=con.execute("SELECT claim_id,patient_prior_90d,provider_payable_rate,amount_ratio,repeat_service_days FROM claim_features WHERE submitted_at<'2026-02-01' ORDER BY claim_id").fetchall()
        con.execute("UPDATE claims SET submitted_amount=submitted_amount*7,units=units+3 WHERE submitted_at>='2026-02-01'")
        con.execute("UPDATE claim_outcomes SET payable=NOT payable WHERE adjudicated_at>='2026-02-01'")
        con.execute((ROOT/'sql/02_features.sql').read_text())
        after=con.execute("SELECT claim_id,patient_prior_90d,provider_payable_rate,amount_ratio,repeat_service_days FROM claim_features WHERE submitted_at<'2026-02-01' ORDER BY claim_id").fetchall()
        assert before==after
    finally: con.rollback(); con.close()
