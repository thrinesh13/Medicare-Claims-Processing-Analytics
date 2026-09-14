"""Event-based claim lifecycle. No model or model score participates in label creation."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def generate(config, destination=None):
    rng = np.random.default_rng(config['seed'])
    dest = Path(destination or ROOT/'data'/'generated')
    dest.mkdir(parents=True, exist_ok=True)
    b = pd.read_csv(ROOT/'data/sources/cms_benchmarks.csv', dtype={'procedure_code':str}).set_index('procedure_code')
    npat, nprov = config['n_patients'], config['n_providers']
    patients = pd.DataFrame({'patient_id':range(1,npat+1),'birth_year':rng.integers(1935,1961,npat), 'coverage_start':'2024-01-01','coverage_end':'2027-12-31'})
    providers = pd.DataFrame({'provider_id':range(1,nprov+1),'specialty':rng.choice(['Primary care','Multispecialty','Rehabilitation'],nprov),'enrollment_start':'2023-01-01','enrollment_end':'2027-12-31'})
    # Latent provider workflow quality affects error incidence, never exported to features.
    poor = rng.random(nprov)<.15
    rows, outcomes = [], []
    times = np.sort(rng.integers(0,546*86400,config['n_claims']))
    for i, sec in enumerate(times,1):
        t = pd.Timestamp('2025-01-01')+pd.Timedelta(seconds=int(sec))
        pid, vid = int(rng.integers(1,npat+1)), int(rng.integers(1,nprov+1))
        code = str(rng.choice(b.index))  # balanced portfolio across five services
        drift = 1.35 if t>=pd.Timestamp('2026-02-01') else 1.0
        error_prob = min(.65,float(b.loc[code,'denied_service_rate'])*(.35+4.0*poor[vid-1])*drift)
        event = 'routine'
        if rng.random()<error_prob:
            event = str(rng.choice(['duplicate','coverage_failure','billing_anomaly','unresolved_documentation','medical_necessity_failure'],p=[.22,.18,.12,.12,.36]))
        elif rng.random()<.12:
            event = str(rng.choice(['legitimate_unusual','correction','documentation_resolved','repeat_therapy'],p=[.35,.20,.20,.25]))
        payable = event in ['routine','legitimate_unusual','correction','documentation_resolved','repeat_therapy']
        service = (t-pd.Timedelta(days=int(rng.integers(1,22)))).normalize()
        units = int(rng.choice([1,2,3,4],p=[.18,.22,.38,.22])) if code=='97110' else 1
        factor = float(rng.lognormal(-.5*.30**2,.30))
        if event=='legitimate_unusual':
            factor *= float(rng.uniform(1.8,3.0))
            if code=='97110': units=8
        if event=='billing_anomaly':
            factor *= float(rng.uniform(1.4,2.8))
            units += int(rng.integers(1,5))
        amount = round(float(b.loc[code,'submitted_per_service'])*units*factor,2)
        correction, modifier = None, ''
        if event in ['duplicate','correction'] and rows:
            candidates=list(range(max(0,len(rows)-150),len(rows)))
            if event=='correction': candidates=[j for j in candidates if not outcomes[j]['payable'] and outcomes[j]['event_type']!='duplicate']
            if not candidates: candidates=[len(rows)-1]; event='legitimate_unusual'
            original = rows[int(rng.choice(candidates))]
            pid,vid,code,service,units,amount = [original[k] for k in ['patient_id','provider_id','procedure_code','service_date','units','submitted_amount']]
            if event=='correction':
                correction=original['claim_id']; amount=round(amount*.97,2)
        elif event=='duplicate':
            event='medical_necessity_failure'
        if event=='repeat_therapy': modifier='59'
        docs = event not in ['unresolved_documentation','documentation_resolved']
        # Some invalid documentation is superficially complete; some valid claims are incomplete at intake.
        if event=='unresolved_documentation' and rng.random()<.35: docs=True
        coverage = 'inactive' if event=='coverage_failure' and rng.random()<.85 else 'active'
        if event=='coverage_failure' and rng.random()<.20:
            service=(t-pd.Timedelta(days=400)).normalize()
        exception = event=='billing_anomaly' and rng.random()<.45
        lag=int(rng.integers(5,31))+(30 if not docs else 0)
        rows.append(dict(claim_id=i,patient_id=pid,provider_id=vid,procedure_code=code,service_date=str(pd.Timestamp(service).date()),submitted_at=str(t),units=units,submitted_amount=amount,scheduled_payment=round(float(b.loc[code,'payment_per_allowed_service'])*units,2),place_of_service='11',modifier=modifier,documentation_present=bool(docs),coverage_response=coverage,correction_of=correction,billing_exception=bool(exception)))
        outcomes.append(dict(claim_id=i,payable=bool(payable),adjudicated_at=str(t+pd.Timedelta(days=lag)),outcome_reason='payable_after_adjudication' if payable else event,event_type=event))
    frames = {'patients':patients,'providers':providers,'claims':pd.DataFrame(rows),'claim_outcomes':pd.DataFrame(outcomes)}
    frames['claims']['correction_of']=frames['claims'].correction_of.astype('Int64')
    for name,frame in frames.items(): frame.to_csv(dest/f'{name}.csv',index=False)
    return frames

if __name__=='__main__': generate(json.loads((ROOT/'config.json').read_text()))
