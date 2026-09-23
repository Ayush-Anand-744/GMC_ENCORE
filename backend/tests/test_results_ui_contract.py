from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_upload_js_uses_real_results_route_transition():
    js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "window.location.assign" in js
    assert "/results/" in js
    assert "renderResult()" not in js


def test_results_filters_and_status_contract():
    js = (ROOT / "frontend" / "results.js").read_text(encoding="utf-8")
    html = (ROOT / "frontend" / "results.html").read_text(encoding="utf-8")
    for label in ("All", "Needs Review", "Conflicts"):
        assert f">{label}<" in html
    assert "Not stated" not in html
    assert "Low Confidence" not in html
    assert "RFQ Data ✅" in js
    assert "RFQ Data ❌" in js
    assert "Stable" in js and "High" in js and "Medium" in js and "Low" in js
    assert "Demography Exception" in html
    assert "Quote Exception" in html
    assert "Extracted Data" in html


def test_quote_table_has_requested_columns():
    js = (ROOT / "frontend" / "results.js").read_text(encoding="utf-8")
    expected = "<th>List of Category</th><th>RFQ / Customer Details</th><th>Proposed Details</th><th>Source Status</th><th>Confidence Level</th>"
    assert expected in js
    assert "<th>Section</th>" not in js
    assert "<th>conf.</th>" not in js
    assert "<th>Evidence & Notes</th>" not in js
