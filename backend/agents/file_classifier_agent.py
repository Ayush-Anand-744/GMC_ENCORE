from pathlib import Path
import pandas as pd
from backend.core.text_utils import norm
from backend.core.password_handler import is_password_protected

DEMO_HINTS = {
    "dob", "date of birth", "birth date", "employee code", "emp code", "emp id", 
    "employee id", "relationship", "relation", "rel", "gender", "sex", 
    "employee name", "emp name", "member name", "insured name", "marital status", "doj"
}

RFQ_HINTS = {
    "policy", "coverage", "proposed", "maternity", "room rent", "copay", "co-pay",
    "waiting period", "quote", "rfp", "sum insured", "brokerage", "tpa", "insurer", 
    "tenure", "rater type", "zone", "plan", "claim servicing"
}


def classify_table(sheet_name: str, df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "rfq"
    
    norm_name = norm(sheet_name)
    if any(k in norm_name for k in ["demography", "employee", "census", "lives", "member", "active emp"]):
        return "demography"
    if any(k in norm_name for k in ["rfq", "quote", "coverage", "terms", "slip", "gmc data"]):
        return "rfq"

    col_str = " ".join(norm(str(c)) for c in df.columns)
    demo_score = sum(3 for h in DEMO_HINTS if h in col_str)
    rfq_score = sum(1 for h in RFQ_HINTS if h in col_str)

    sample_cells = []
    for r_idx in range(min(15, len(df))):
        row = df.iloc[r_idx]
        for val in row:
            if pd.notna(val):
                s_val = norm(str(val))
                if s_val and s_val not in {"nan", "none"}:
                    sample_cells.append(s_val)
    
    sample_text = " ".join(sample_cells[:100])
    demo_score += sum(1 for h in DEMO_HINTS if h in sample_text)
    rfq_score += sum(1 for h in RFQ_HINTS if h in sample_text)

    if demo_score >= max(3, rfq_score + 1):
        return "demography"
    return "rfq"


def classify_content(filename: str, text: str, tables=None) -> str:
    sample = norm(text[:12000])
    demo = sum(1 for h in DEMO_HINTS if h in sample)
    rfq = sum(1 for h in RFQ_HINTS if h in sample)
    if tables:
        for name, df in tables:
            t_kind = classify_table(name, df)
            if t_kind == "demography":
                demo += 4
            else:
                rfq += 2
    return "demography" if demo >= max(4, rfq + 1) else "rfq"


def scan_file(filename: str, data: bytes):
    return {"filename": filename, "extension": Path(filename).suffix.lower(), "locked": is_password_protected(filename, data), "size": len(data)}

