from datetime import date
import pandas as pd
from backend.core.demography_engine import standardize_demography

def extract_demography(read_results, reference_date: date):
    candidates = []
    for rr in read_results:
        for _, df in rr.tables:
            rows = standardize_demography(df, reference_date)
            if rows:
                candidates.append(rows)
    if not candidates:
        return []

    merged = []
    seen = set()
    for cand in candidates:
        for r in cand:
            sig = (r.get("EmpCode"), r.get("Name"), r.get("Date of Birth"), r.get("Relationship"), r.get("Gender"))
            if sig not in seen:
                seen.add(sig)
                merged.append(r)
    return merged
