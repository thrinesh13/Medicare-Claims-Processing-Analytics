import os
from pathlib import Path
import psycopg
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DSN=os.getenv('DATABASE_URL','postgresql://portfolio@127.0.0.1:55432/postgres')

def connect():
    con=psycopg.connect(DSN,connect_timeout=10)
    con.execute('SET search_path TO stp')
    return con

def load():
    with connect() as con:
        con.execute((ROOT/'sql/01_schema.sql').read_text())
        for name in ['patients','providers','claims','claim_outcomes']:
            options='FORMAT CSV, HEADER TRUE'+(', FORCE_NOT_NULL (modifier)' if name=='claims' else '')
            with con.cursor().copy(f'COPY {name} FROM STDIN WITH ({options})') as copy:
                copy.write((ROOT/f'data/generated/{name}.csv').read_bytes())
        con.execute('ANALYZE')

def features():
    with connect() as con:
        con.execute((ROOT/'sql/02_features.sql').read_text())
        cur=con.execute('SELECT * FROM claim_features ORDER BY claim_id')
        frame=pd.DataFrame(cur.fetchall(),columns=[x.name for x in cur.description])
    frame.to_csv(ROOT/'data/generated/claim_features.csv',index=False)
    return frame

def load_reporting():
    with connect() as con:
        con.execute((ROOT/'sql/03_reporting.sql').read_text())
        with con.cursor().copy('COPY claim_decisions FROM STDIN WITH (FORMAT CSV, HEADER TRUE)') as copy:
            copy.write((ROOT/'results/fact_decisions.csv').read_bytes())
