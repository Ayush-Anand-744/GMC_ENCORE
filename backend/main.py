import json
import uuid
from datetime import date
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.logging import configure_logging
from backend.core.password_handler import is_password_protected, unlock_bytes
from backend.core.file_reader import read_file
from backend.agents.file_classifier_agent import classify_content
from backend.orchestration.orchestrator import Orchestrator
from backend.core.excel_export import all_results_xlsx, quote_xlsx, demography_xlsx
from backend.masters.dropdown_masters import DROPDOWN_MASTERS

configure_logging()
ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="GMC ENCORE", version="1.1.0")

@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")
CASES = {}
orch = Orchestrator()


@app.get("/", response_class=HTMLResponse)
def index():
    return (ROOT / "frontend/index.html").read_text(encoding="utf-8")


@app.get("/results/{case_id}", response_class=HTMLResponse)
def results_page(case_id: str):
    if case_id not in CASES:
        raise HTTPException(404, "Case not found or server restarted.")
    return (ROOT / "frontend/results.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "GMC ENCORE"}


@app.get("/api/masters")
def masters():
    return {"dropdowns": DROPDOWN_MASTERS}


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    result = CASES.get(case_id)
    if not result:
        raise HTTPException(404, "Case not found or server restarted.")
    return result


@app.post("/api/scan")
async def scan(files: list[UploadFile] = File(...)):
    out = []
    for f in files:
        data = await f.read()
        locked = is_password_protected(f.filename, data)
        category = "unknown"
        if not locked:
            try:
                rr = read_file(f.filename, data)
                category = classify_content(f.filename, rr.text, rr.tables)
            except Exception:
                pass
        out.append({"filename": f.filename, "size": len(data), "locked": locked, "category": category})
    return out


@app.post("/api/process")
async def process(
    files: list[UploadFile] = File(...),
    passwords_json: str = Form("{}"),
    use_policy_date: bool = Form(False),
    policy_date: str = Form(""),
):
    try:
        passwords = json.loads(passwords_json or "{}")
    except Exception:
        passwords = {}

    ref = date.today()
    if use_policy_date:
        if not policy_date:
            raise HTTPException(422, "Policy Proposal Date is required when proposal-date mode is on.")
        try:
            ref = date.fromisoformat(policy_date)
        except Exception:
            raise HTTPException(422, "Invalid Policy Proposal Date.")

    payload = []
    for f in files:
        data = await f.read()
        if is_password_protected(f.filename, data):
            pwd = passwords.get(f.filename)
            if not pwd:
                raise HTTPException(423, detail={"locked_file": f.filename, "message": "Password required"})
            try:
                data = unlock_bytes(f.filename, data, pwd)
            except ValueError:
                raise HTTPException(401, detail={"locked_file": f.filename, "message": "Incorrect password, try again"})
        payload.append((f.filename, data))

    try:
        result = orch.process(payload, ref)
    except Exception as e:
        raise HTTPException(400, f"Processing failed: {e}")

    case_id = uuid.uuid4().hex
    result["case_id"] = case_id
    CASES[case_id] = result
    # Deliberately return only routing metadata. The processed result is loaded on
    # the dedicated results page through /api/cases/{case_id}.
    return {"case_id": case_id, "results_url": f"/results/{case_id}"}


@app.post("/api/cases/{case_id}/reference-date")
def update_reference_date(
    case_id: str,
    use_policy_date: bool = Form(False),
    policy_date: str = Form(""),
):
    from backend.core.demography_engine import recalculate_ages
    result = CASES.get(case_id)
    if not result:
        raise HTTPException(404, "Case not found or server restarted.")
    ref = date.today()
    if use_policy_date:
        if not policy_date:
            raise HTTPException(422, "Policy Proposal Date is required.")
        try:
            ref = date.fromisoformat(policy_date)
        except Exception:
            raise HTTPException(422, "Invalid Policy Proposal Date.")

    demography = result.get("demography", [])
    recalculate_ages(demography, ref)
    return {"status": "ok", "reference_date": ref.isoformat(), "demography": demography}


@app.put("/api/cases/{case_id}/demography")
def update_demography(case_id: str, payload: list[dict]):
    from backend.core.demography_engine import summary as demo_summary
    result = CASES.get(case_id)
    if not result:
        raise HTTPException(404, "Case not found or server restarted.")
    result["demography"] = payload
    ds = demo_summary(payload)
    result["summary"]["group_size"] = ds["group_size"]
    result["summary"]["primary_members"] = ds["primary_members"]
    result["summary"]["sme"] = ds["sme"]
    result["summary"]["demo_lives"] = len(payload)
    for r in result.get("quote_rows", []):
        if r.get("field") == "Group Size":
            r["coverage_details"] = str(ds["group_size"]) if len(payload) > 0 else "Not Available"
        elif r.get("field") == "Number of Primary Members":
            r["coverage_details"] = str(ds["primary_members"]) if len(payload) > 0 else "Not Available"
        elif r.get("field") == "Flagging SME":
            r["coverage_details"] = ds["sme"] if len(payload) > 0 else "Not Available"
    return result


@app.get("/api/cases/{case_id}/download/{kind}")
def download(case_id: str, kind: str):
    result = CASES.get(case_id)
    if not result:
        raise HTTPException(404, "Case not found or server restarted.")
    if kind == "all":
        data = all_results_xlsx(result)
        name = "GMC_All_Results.xlsx"
    elif kind == "quote":
        data = quote_xlsx(result)
        name = "GMC_Quote_Sheet.xlsx"
    elif kind == "demography":
        data = demography_xlsx(result)
        name = "GMC_Standardized_Demography.xlsx"
    else:
        raise HTTPException(404, "Unknown download type")
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
