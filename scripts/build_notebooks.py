"""Generate and execute reviewable notebooks and portable HTML evidence."""
import json
import os
import sys
from pathlib import Path
import nbformat as nb
from nbclient import NotebookClient
from nbconvert import HTMLExporter
ROOT=Path(__file__).resolve().parents[1]

def md(text): return nb.v4.new_markdown_cell(text)
def code(text): return nb.v4.new_code_cell(text)

def main():
    (ROOT/'work/ipython').mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('IPYTHONDIR',str(ROOT/'work/ipython'))
    folder=ROOT/'notebooks'; folder.mkdir(exist_ok=True)
    setup="""from pathlib import Path
import json, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path.cwd().parent if Path.cwd().name=='notebooks' else Path.cwd()
sys.path.insert(0,str(ROOT))
plt.rcParams.update({'figure.figsize':(10,4.5),'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
summary=pd.read_csv(ROOT/'results/policy_summary.csv')
run=json.loads((ROOT/'results/run_summary.json').read_text())
scored=pd.read_csv(ROOT/'results/scored_claims.csv',dtype={'procedure_code':str})
"""
    cells=[md('# 01 · Data, SQL features and leakage validation\n\n## Context & methods\nThe decision unit is one single-line submission attempt. Current adjudication is separate from intake; only earlier available evidence can enter history. See [methodology](../docs/METHODS.md).'),code(setup),
      md('## Data\n24,000 synthetic claim-level demo attempts are calibrated to actual CMS 2023 PSPS office-service summaries. Public aggregates do not contain patient histories. Suppressed cells remain unknown. See [source receipt and transformations](../docs/DATA_SOURCES.md).'),
      code("bench=pd.read_csv(ROOT/'data/sources/cms_benchmarks.csv',dtype={'procedure_code':str})\ndisplay(bench[['procedure_code','submitted_services','allowed_services_derived','denied_services','denied_service_rate','submitted_volume_retained']].round(4))"),
      md('### Comparable calibration audit\nCompare dollars per unit and service-weighted nonpayable incidence. Claim-level denial incidence is also shown because service counts and submission counts differ. The balanced code mix, exceptions and drift intentionally move the generated distribution away from the source.'),
      code("""audit=scored.groupby('procedure_code').apply(lambda g: pd.Series({'demo_submitted_per_unit':g.submitted_amount.sum()/g.units.sum(),'demo_nonpayable_service_rate':g.loc[~g.payable,'units'].sum()/g.units.sum(),'demo_nonpayable_attempt_rate':(~g.payable).mean()}),include_groups=False).reset_index()
audit=audit.merge(bench[['procedure_code','submitted_per_service','denied_service_rate']],on='procedure_code')
audit['dollar_difference_pct']=audit.demo_submitted_per_unit/audit.submitted_per_service-1
audit['denial_difference_pp']=100*(audit.demo_nonpayable_service_rate-audit.denied_service_rate)
audit.to_csv(ROOT/'results/calibration_audit.csv',index=False)
display(audit.round(4))
x=np.arange(len(audit)); fig,ax=plt.subplots()
ax.bar(x-.18,audit.denied_service_rate*100,.36,label='CMS retained-cell services',color='#73849b')
ax.bar(x+.18,audit.demo_nonpayable_service_rate*100,.36,label='Demo nonpayable units',color='#087f8c')
ax.set(xticks=x,xticklabels=audit.procedure_code,ylabel='Percent of submitted services / units',title='Procedure-level comparison · 2023 CMS vs Jan 2025–Jun 2026 demo'); ax.legend(); plt.tight_layout(); plt.show()
"""),
      md('### SQL lineage\nThe executable feature query uses CTEs, timestamp RANGE windows and lateral as-of joins. Frequency and amount windows cover 90 days; provider payable history uses outcomes already available from the preceding 180 days. No full-period aggregate is joined back to prior claims.'),
      code("sql=(ROOT/'sql/02_features.sql').read_text()\nprint(sql)"),
      md('### Availability and independent sample checks'),
      code("""from src.database import connect
with connect() as con:
    q=con.execute("SELECT COUNT(*), COUNT(DISTINCT claim_id), COUNT(*) FILTER (WHERE provider_outcome_max_at >= submitted_at OR procedure_history_max_at >= submitted_at OR previous_submission_at >= submitted_at) FROM claim_features").fetchone()
assert q==(24000,24000,0), q
sample=scored.sort_values('claim_id').iloc[12000]
past=scored[(scored.patient_id==sample.patient_id)&(pd.to_datetime(scored.submitted_at)<pd.Timestamp(sample.submitted_at))&(pd.to_datetime(scored.submitted_at)>=pd.Timestamp(sample.submitted_at)-pd.Timedelta(days=90))]
assert len(past)==sample.patient_prior_90d
display(pd.DataFrame([{'claims':q[0],'unique_claims':q[1],'availability_violations':q[2],'independent_sample_prior_count':len(past)}]))
display(scored.groupby('split').agg(n=('claim_id','size'),payable_rate=('payable','mean')))
"""),
      md('## Takeaways\nFeature timestamps satisfy strict availability checks. The automated test suite additionally mutates future dollars, units and outcomes and proves that earlier feature values remain identical; a four-claim fixture tests simultaneous timestamps and label maturity. Maturity exclusions in training and tuning are documented, not silently dropped from the source population.')]
    n=nb.v4.new_notebook(cells=cells)
    cells2=[md('# 02 · Policy comparison and decision economics\n\n## Context & methods\nA chronological holdout compares manual processing, checks, and checks plus a calibrated probability. The threshold is fixed on validation data before this period. Values below are recomputed from the saved run; costs and time are scenario assumptions.'),code(setup),
      md('## Results · throughput is not net value'),code("display(summary.round(3))\nprint('Threshold:',round(run['threshold'],3), '| Holdout:',run['holdout_start'],'to',run['holdout_end'])"),
      code("""colors=['#73849b','#d58435','#087f8c']
fig,axes=plt.subplots(1,2,figsize=(12,4.5))
axes[0].bar(summary.policy,summary.auto_rate*100,color=colors); axes[0].set(ylabel='Auto approvals / submissions (%)',title='Straight-through processing rate',ylim=(0,100))
axes[1].bar(summary.policy,summary.net_cost,color=colors); axes[1].set(ylabel='Processing + incorrect-payment cost ($)',title='Net cost · identical holdout population')
for ax in axes: ax.tick_params(axis='x',rotation=12)
plt.tight_layout(); plt.show()
"""),
      md('### Net savings independently recomputed'),code("""from src.evaluate import decision
h=scored[scored.split.eq('holdout')].copy(); c=run['config']
auto=decision(h,'Checks + score',run['threshold']); wrong=auto&~h.payable
gross=auto.sum()*c['review_cost']; auto_cost=auto.sum()*c['auto_cost']
loss=wrong.sum()*c['wrong_approval_cost']+h.loc[wrong,'scheduled_payment'].sum()*c['payment_loss_multiplier']
net=gross-auto_cost-loss
assert abs(net-summary.iloc[2].net_savings)<1e-6
display(pd.DataFrame({'component':['Avoided review cost','Automatic processing cost','Wrong-approval loss','Net savings'],'USD':[gross,-auto_cost,-loss,net]}).round(2))
print('Conditional provider-bootstrap 95% interval:',run['net_savings_provider_bootstrap_95'])
"""),
      md('### Calibration and drift\nThe calibration step is fitted only in Oct–Nov 2025. Compare raw and calibrated Brier scores explicitly; lower is better. The holdout contains a predeclared 35% error-incidence stress.'),code("""display(pd.DataFrame([{k:run[k] for k in ['brier_raw','brier_calibrated','log_loss','roc_auc','ece']}]))
reliability=pd.read_csv(ROOT/'results/calibration.csv')
fig,ax=plt.subplots(); ax.plot([0,1],[0,1],'--',color='#73849b',label='Perfect calibration')
ax.errorbar(reliability.mean_predicted,reliability.observed_payable,yerr=[reliability.observed_payable-reliability.observed_low,reliability.observed_high-reliability.observed_payable],fmt='o-',color='#087f8c',label='Holdout bins · Wilson 95%')
ax.set(xlabel='Mean predicted P(payable)',ylabel='Observed payable share',title='Reliability · count-weighted holdout bins',xlim=(0,1),ylim=(0,1)); ax.legend(); plt.tight_layout(); plt.show()
display(reliability.round(4))
"""),
      md('### Economic sensitivity\nHoldout curves are descriptive and do not reselect the reported threshold. Review cost and wrong-approval remediation costs are assumptions; scheduled payment loss is added separately.'),code("""s=pd.read_csv(ROOT/'results/sensitivity.csv')
fig,ax=plt.subplots()
for penalty in [100,250,750,2000]:
    g=s[(s.policy=='Checks + score')&(s.review_cost==18)&(s.wrong_approval_cost==penalty)].sort_values('threshold')
    ax.plot(g.threshold,g.net_savings,label=f'Remediation ${penalty:,}')
ax.axvline(run['threshold'],color='#555',ls=':',label='Locked threshold'); ax.axhline(0,color='#555',lw=.8)
ax.set(xlabel='P(payable) threshold',ylabel='Net savings vs manual ($)',title='Decision economics · full holdout, $18 review cost'); ax.legend(); plt.tight_layout(); plt.show()
"""),
      md('### Legitimate exceptions and workload over time'),code("""segments=pd.read_csv(ROOT/'results/segments.csv')
display(segments[segments.policy.eq('Checks + score')][['event_type','n_claims','auto_approved','reviewed','wrong_approvals','net_savings']].round(2))
monthly=pd.read_csv(ROOT/'results/monthly.csv'); fig,ax=plt.subplots()
for policy,g in monthly.groupby('policy'):
    ax.plot(g.month,g.wrong_per_1000,marker='o',label=policy)
ax.set(ylabel='Incorrect auto approvals per 1,000 submissions',title='Monthly payment-error burden · holdout'); ax.legend(); plt.tight_layout(); plt.show()
"""),
      md('## Takeaways\nChecks plus score trades some automatic throughput for fewer incorrect payments and higher net savings at the default settings. The decision can change when loss assumptions rise. Calibration slightly worsens holdout Brier score, so recalibration and prospective validation are required before operational use. Review is not denial; valid unusual claims retain their payable outcome. Fixed queues, perfect manual adjudication and common historical feedback constrain interpretation. See [full methods and limitations](../docs/METHODS.md).')]
    for name,book in [('01_data_and_sql',n),('02_decision_economics',nb.v4.new_notebook(cells=cells2))]:
        book.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]}}
        nb.validate(book)
        NotebookClient(book,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}}).execute()
        nb.write(book,folder/f'{name}.ipynb')
        html,_=HTMLExporter().from_notebook_node(book)
        (folder/f'{name}.html').write_text(html,encoding='utf8')
        print('Executed',name,flush=True)

if __name__=='__main__': main()
