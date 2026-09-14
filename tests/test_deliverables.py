"""Check that the publication artifacts remain connected to the evaluated data."""
import json
import re
from pathlib import Path
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]

def test_notebooks_have_executed_outputs_without_errors():
    for path in (ROOT/'notebooks').glob('*.ipynb'):
        book=json.loads(path.read_text(encoding='utf8'))
        cells=[c for c in book['cells'] if c['cell_type']=='code']
        assert cells and all(c.get('execution_count') is not None for c in cells)
        outputs=[o for c in cells for o in c.get('outputs',[])]
        assert not any(o['output_type']=='error' for o in outputs)
        assert any('image/png' in o.get('data',{}) for o in outputs)

def test_story_links_and_notebook_figures_exist():
    for file in ['README.md','methodology.md']:
        text=(ROOT/file).read_text(encoding='utf8')
        for href in re.findall(r'\]\(([^)]+)\)',text):
            if not href.startswith(('https:','http:','#')):
                assert (ROOT/href).exists(),href
    for name in ['policy-comparison.png','cost-sensitivity.png']:
        assert (ROOT/'assets'/name).read_bytes().startswith(b'\x89PNG')

def test_exported_policy_results_match_claim_decisions():
    facts=pd.read_csv(ROOT/'results/fact_decisions.csv')
    summary=pd.read_csv(ROOT/'results/policy_summary.csv')
    for row in summary.itertuples():
        group=facts[facts.policy.eq(row.policy)]
        assert len(group)==row.n_claims
        assert group.auto_approved.sum()==row.auto_approved
        assert group.wrong_approval.sum()==row.wrong_approvals
        assert group.net_cost.sum()==pytest.approx(row.net_cost)
        assert group.net_savings.sum()==pytest.approx(row.net_savings)
