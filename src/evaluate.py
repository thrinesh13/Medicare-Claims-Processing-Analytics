"""Chronological learning, policy routing and explicit decision economics."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

ROOT=Path(__file__).resolve().parents[1]
FEATURES=['patient_prior_90d','provider_prior_90d','provider_matured_n','provider_payable_rate',
 'procedure_prior_n','amount_ratio','amount_z','units_ratio','repeat_service_days',
 'submission_lag_days','units','documentation_present','coverage_ok','provider_enrolled',
 'late_filing','billing_exception','suspect_duplicate','units_exception']

def wilson(k,n):
    if not n: return (0.,1.)
    z=1.96; p=k/n; den=1+z*z/n
    mid=(p+z*z/(2*n))/den; half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return float(mid-half),float(mid+half)

def decision(d,policy,threshold):
    if policy=='Manual': return np.zeros(len(d),dtype=bool)
    eligible=d.checks_pass.to_numpy(bool)
    return eligible if policy=='Checks' else eligible & (d.score.to_numpy()>=threshold)

def metrics(d,policy,threshold,c):
    auto=decision(d,policy,threshold); wrong=auto & ~d.payable.to_numpy(bool)
    losses=wrong*(c['wrong_approval_cost']+d.scheduled_payment.to_numpy(float)*c['payment_loss_multiplier'])
    costs=np.where(auto,c['auto_cost'],c['review_cost'])+losses
    n=len(d); a=int(auto.sum()); w=int(wrong.sum())
    low,high=wilson(w,a)
    return dict(policy=policy,n_claims=n,auto_approved=a,reviewed=n-a,wrong_approvals=w,
       auto_rate=a/n,wrong_auto_rate=w/a if a else None,wrong_rate_low=low if a else None,wrong_rate_high=high if a else None,
       wrong_per_1000=1000*w/n,gross_review_savings=a*c['review_cost'],
       automation_cost=a*c['auto_cost'],wrong_approval_loss=float(losses.sum()),net_cost=float(costs.sum()),
       net_savings=float(n*c['review_cost']-costs.sum()),
       handling_hours=float((a*c['auto_minutes']+(n-a)*c['review_minutes'])/60),
       mean_turnaround_hours=float((a*c['auto_minutes']/60+(n-a)*(c['review_queue_hours']+c['review_minutes']/60))/n))

def run(c):
    out=ROOT/'results'; out.mkdir(exist_ok=True)
    d=pd.read_csv(ROOT/'data/generated/claim_features.csv',dtype={'procedure_code':str})
    o=pd.read_csv(ROOT/'data/generated/claim_outcomes.csv')
    d=d.merge(o,on='claim_id',validate='one_to_one')
    t=pd.to_datetime(d.submitted_at); maturity=pd.to_datetime(d.adjudicated_at)
    train=(t<c['train_end']) & (maturity<c['train_end'])
    cal=(t>=c['train_end']) & (t<c['calibration_end']) & (maturity<c['calibration_end'])
    val=(t>=c['calibration_end']) & (t<c['validation_end']) & (maturity<c['validation_end'])
    test=(t>=c['validation_end']) & (maturity<c['evaluation_as_of'])
    X=d[FEATURES].astype(float)
    model=HistGradientBoostingClassifier(max_iter=110,max_leaf_nodes=9,l2_regularization=10,min_samples_leaf=80,early_stopping=False,random_state=c['seed'])
    model.fit(X.loc[train],d.loc[train,'payable'])
    raw=np.clip(model.predict_proba(X)[:,1],1e-6,1-1e-6)
    logits=np.log(raw/(1-raw)).reshape(-1,1)
    calibrator=LogisticRegression(C=1.,random_state=c['seed']).fit(logits[cal],d.loc[cal,'payable'])
    d['raw_score']=raw; d['score']=calibrator.predict_proba(logits)[:,1]
    d['split']=np.select([train,cal,val,test],['train','calibration','validation','holdout'],default='maturity_excluded')
    grid=np.unique(np.r_[np.arange(.80,1.0,.005),1.0])
    tuning=pd.DataFrame([dict(threshold=float(th),**metrics(d.loc[val],'Checks + score',th,c)) for th in grid])
    feasible=tuning[(tuning.auto_approved>=100)&(tuning.wrong_rate_high<=c['max_validation_wrong_rate'])]
    chosen=float(feasible.sort_values(['net_cost','threshold'],ascending=[True,False]).iloc[0].threshold) if len(feasible) else 1.0
    if c['threshold'] is not None: chosen=float(c['threshold'])
    tuning.to_csv(out/'validation_thresholds.csv',index=False)
    h=d.loc[test].copy(); h['month']=pd.to_datetime(h.submitted_at).dt.strftime('%Y-%m')
    policies=['Manual','Checks','Checks + score']
    summary=pd.DataFrame([metrics(h,p,chosen,c) for p in policies]); summary.to_csv(out/'policy_summary.csv',index=False)
    sensitivity=[]
    for review in [8.,18.,35.]:
      for penalty in [100.,250.,750.,2000.]:
       scenario={**c,'review_cost':review,'wrong_approval_cost':penalty}
       for th in np.unique(np.r_[grid,chosen]):
        for p in policies:
         sensitivity.append(dict(review_cost=review,wrong_approval_cost=penalty,threshold=float(th),**metrics(h,p,th,scenario)))
    pd.DataFrame(sensitivity).to_csv(out/'sensitivity.csv',index=False)
    monthly=[]; segments=[]; facts=[]
    for p in policies:
        auto=decision(h,p,chosen); wrong=auto & ~h.payable.to_numpy(bool)
        f=h[['claim_id','procedure_code','provider_id','patient_id','month','score','payable','event_type']].copy()
        f['policy']=p; f['auto_approved']=auto.astype(int); f['wrong_approval']=wrong.astype(int)
        f['reviewed']=(~auto).astype(int)
        f['wrong_payment']=wrong*h.scheduled_payment.to_numpy(float)
        f['net_cost']=np.where(auto,c['auto_cost'],c['review_cost'])+wrong*c['wrong_approval_cost']+f.wrong_payment*c['payment_loss_multiplier']
        f['net_savings']=c['review_cost']-f.net_cost
        f['handling_minutes']=np.where(auto,c['auto_minutes'],c['review_minutes'])
        f['turnaround_hours']=np.where(auto,c['auto_minutes']/60,c['review_queue_hours']+c['review_minutes']/60)
        facts.append(f)
        for month,group in h.groupby('month'): monthly.append(dict(month=month,**metrics(group,p,chosen,c)))
        for event,group in h.groupby('event_type'): segments.append(dict(event_type=event,**metrics(group,p,chosen,c)))
    pd.concat(facts).to_csv(out/'fact_decisions.csv',index=False)
    pd.DataFrame(monthly).to_csv(out/'monthly.csv',index=False)
    pd.DataFrame(segments).to_csv(out/'segments.csv',index=False)
    bins=pd.cut(h.score,bins=[0,.5,.8,.9,.95,.97,.98,.99,1.],include_lowest=True)
    calibration=h.groupby(bins,observed=True).agg(n=('claim_id','size'),mean_predicted=('score','mean'),observed_payable=('payable','mean')).reset_index(names='bin')
    calibration['bin']=calibration.bin.astype(str)
    bounds=[wilson(round(r.n*r.observed_payable),r.n) for r in calibration.itertuples()]
    calibration['observed_low']=[x[0] for x in bounds]; calibration['observed_high']=[x[1] for x in bounds]
    calibration.to_csv(out/'calibration.csv',index=False)
    d.to_csv(out/'scored_claims.csv',index=False)
    report={'threshold':chosen,'threshold_basis':'validation-only constrained net-cost minimum (or explicit config override)',
      'split_counts':d.split.value_counts().to_dict(),'features':FEATURES,'config':c,
      'holdout_start':str(h.submitted_at.min()),'holdout_end':str(h.submitted_at.max()),
      'brier_raw':brier_score_loss(h.payable,h.raw_score),'brier_calibrated':brier_score_loss(h.payable,h.score),
      'log_loss':log_loss(h.payable,h.score),'roc_auc':roc_auc_score(h.payable,h.score),
      'ece':float((calibration.n*abs(calibration.mean_predicted-calibration.observed_payable)).sum()/len(h)),
      'validation_feasible_thresholds':len(feasible)}
    # Provider-cluster bootstrap: describe sampling variation, not model uncertainty.
    scored_fact=facts[-1]; by_provider=scored_fact.groupby('provider_id').net_savings.sum().to_numpy()
    rng=np.random.default_rng(c['seed']+1)
    boot=np.array([rng.choice(by_provider,len(by_provider),replace=True).sum() for _ in range(1000)])
    report['net_savings_provider_bootstrap_95']=[float(x) for x in np.quantile(boot,[.025,.975])]
    (out/'run_summary.json').write_text(json.dumps(report,indent=2))
    joblib.dump({'model':model,'calibrator':calibrator,'features':FEATURES,'threshold':chosen},out/'model.joblib')
    print(summary.to_string(index=False)); print(json.dumps(report,indent=2))
    return report
