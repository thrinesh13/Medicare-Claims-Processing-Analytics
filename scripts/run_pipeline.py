import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.generate import generate
from src.database import load,features,load_reporting
from src.evaluate import run

if __name__=='__main__':
    c=json.loads((ROOT/'config.json').read_text())
    print('1/4 Generate deterministic operational data',flush=True); generate(c)
    print('2/4 Load PostgreSQL',flush=True); load()
    print('3/4 Execute as-of SQL',flush=True); features()
    print('4/4 Fit and evaluate chronological policies',flush=True); run(c)
    load_reporting()
