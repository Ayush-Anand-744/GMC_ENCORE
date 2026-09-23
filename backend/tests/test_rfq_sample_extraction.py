from datetime import date
from pathlib import Path
from backend.orchestration.orchestrator import Orchestrator
from backend.core.text_utils import norm

def test_rfq_sample_extraction():
    sample_path = Path(r"C:\Users\ayush\Downloads\RFQ_Sample.xlsx")
    if not sample_path.exists():
        return
    with open(sample_path, "rb") as f:
        data = f.read()

    orch = Orchestrator()
    res = orch.process([("RFQ_Sample.xlsx", data)], date.today())

    summary = res.get("summary", {})
    assert summary.get("total_fields") > 0
    assert summary.get("auto_fill_rate") >= 40

    quote_rows = {r["field"]: r for r in res.get("quote_rows", [])}
    hosp_rows = {r["field"]: r for r in res.get("hospital_rows", [])}
    add_rows = res.get("additional_rows", [])

    # Verify Organization Name extracted
    assert quote_rows["Organization Name"]["source_status"] == "RFQ Data"
    assert "PHNATOM" in quote_rows["Organization Name"]["coverage_details"] or "PHANTOM" in quote_rows["Organization Name"]["coverage_details"]

    # Verify Sum Insured extracted
    assert quote_rows["Sum Insured"]["source_status"] == "RFQ Data"

    # Verify 1: New Co-payment fields extracted
    assert "Co-pay on all claims" in quote_rows
    assert "Co-Payment on All Parental Claims only" in quote_rows
    assert "Co-pay for Specified Illness" in quote_rows
    assert quote_rows["Co-pay on all claims"]["source_status"] == "RFQ Data"
    assert quote_rows["Co-Payment on All Parental Claims only"]["source_status"] == "RFQ Data"
    assert quote_rows["Co-pay for Specified Illness"]["source_status"] == "RFQ Data"

    # Verify 2: Cataract logic
    assert quote_rows["Waiver of Cataract Sublimit"]["coverage_details"] == "Applicable"
    assert quote_rows["Cataract"]["source_status"] == "RFQ Data"
    assert quote_rows["Cataract"]["coverage_details"] == "Upto SI"

    # Verify 3: Additional Details deduplicated and clean
    seen_add_keys = set()
    for row in add_rows:
        n_key = norm(row["field"])
        assert n_key not in seen_add_keys, f"Duplicate entry found in Additional Details: {row['field']}"
        seen_add_keys.add(n_key)
        assert not row["field"].startswith("[SHEET")
