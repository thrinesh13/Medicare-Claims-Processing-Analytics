"""Export original executed notebook figures used in the README."""
from pathlib import Path
import json, base64
ROOT=Path(__file__).resolve().parents[1]
book=json.loads((ROOT/'notebooks/02_decision_economics.ipynb').read_text(encoding='utf8'))
figures=[o['data']['image/png'] for c in book['cells'] for o in c.get('outputs',[]) if 'image/png' in o.get('data',{})]
(ROOT/'assets').mkdir(exist_ok=True)
for name,index in [('policy-comparison.png',0),('cost-sensitivity.png',2)]:
    (ROOT/'assets'/name).write_bytes(base64.b64decode(figures[index]))
print('Exported two notebook figures')
