"""Retrieve a fixed CMS 2023 PSPS office-service slice; preserve raw evidence."""
import hashlib
import json
from pathlib import Path
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
API = 'https://data.cms.gov/data-api/v1/dataset/b72adfb6-22cf-4241-9c64-050ad9061e03/data'
CODES = ['99213', '99214', '80053', '93000', '97110']

def main():
    folder = ROOT / 'data' / 'sources'
    folder.mkdir(parents=True, exist_ok=True)
    receipts, benchmarks = [], []
    for code in CODES:
        rows, offset = [], 0
        while True:
            params = {'filter[HCPCS_CD]': code, 'filter[PLACE_OF_SERVICE_CD]': '11', 'size': 5000, 'offset': offset}
            r = requests.get(API, params=params, timeout=120)
            r.raise_for_status()
            page = r.json()
            rows.extend(page)
            if len(page) < 5000:
                break
            offset += len(page)
        raw = json.dumps(rows, indent=2).encode()
        (folder / f'psps_2023_{code}_pos11.json').write_bytes(raw)
        d = pd.DataFrame(rows)
        assert d.HCPCS_CD.eq(code).all() and d.PLACE_OF_SERVICE_CD.eq('11').all()
        names = ['PSPS_SUBMITTED_SERVICE_CNT', 'PSPS_SUBMITTED_CHARGE_AMT', 'PSPS_ALLOWED_CHARGE_AMT', 'PSPS_DENIED_SERVICES_CNT', 'PSPS_NCH_PAYMENT_AMT']
        num = d[names].apply(pd.to_numeric, errors='coerce')
        # Common complete-cell cohort: never convert suppressed '*' to zero.
        keep = num.notna().all(axis=1) & d.PSPS_ERROR_IND_CD.eq('0')
        sums = num.loc[keep].sum()
        s, charges, allowed, denied, payment = sums.tolist()
        benchmarks.append(dict(procedure_code=code, year=2023, place_of_service='11', raw_cells=len(d), complete_cells=int(keep.sum()), submitted_services=s, allowed_services_derived=s-denied, denied_services=denied, submitted_charges=charges, allowed_charges=allowed, payments=payment, denied_service_rate=denied/s, submitted_per_service=charges/s, allowed_per_allowed_service=allowed/(s-denied), payment_per_allowed_service=payment/(s-denied), submitted_volume_retained=float(num.loc[keep,names[0]].sum()/num[names[0]].sum())))
        receipts.append(dict(code=code, api=API, filters={'HCPCS_CD':code,'PLACE_OF_SERVICE_CD':'11'}, page_size=5000, rows=len(rows), sha256=hashlib.sha256(raw).hexdigest(), file=f'psps_2023_{code}_pos11.json', retrieved='2026-09-13'))
        print(code, len(rows), int(keep.sum()), round(denied/s,4), flush=True)
    pd.DataFrame(benchmarks).to_csv(folder/'cms_benchmarks.csv', index=False)
    (folder/'receipts.json').write_text(json.dumps(receipts,indent=2))

if __name__ == '__main__':
    main()
