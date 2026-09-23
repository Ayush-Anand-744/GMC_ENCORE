from datetime import date
import pandas as pd
from backend.core.demography_engine import standardize_demography, summary, age_last_birthday
from backend.core.extraction_engine import split_room_rent, build_rows, decompose_field_group
from backend.masters.dropdown_masters import SME_THRESHOLD
from backend.masters.procedure_master import map_procedure_amount
from backend.masters.field_master import FIELD_GROUPS

def test_age_last_birthday():
    assert age_last_birthday("15-09-2000", date(2026,9,15)) == 26
    assert age_last_birthday("16-09-2000", date(2026,9,15)) == 25

def test_demography_synonyms_and_boundary():
    df=pd.DataFrame([{"EMP DOB":"01-01-1990","SI":500000,"Relation":"Self","Employee Name":"A","Employee Code":"1","Sex":"F"}])
    rows=standardize_demography(df,date(2026,1,1)); assert rows[0]["Age"]==36
    fake=[{"Relationship":"Self"} for _ in range(SME_THRESHOLD)]
    assert summary(fake)["sme"]=="YES"
    fake.append({"Relationship":"Self"}); assert summary(fake)["sme"]=="NO"

def test_parse_dob_robust_and_no_action_column():
    from backend.core.demography_engine import parse_dob_robust
    # Test variants: mm/yyyy/dd, dd/yyyy/mm, yyyy/mm/dd, yyyy/dd/mm, mm/dd/yyyy, dd/mm/yyyy, ISO
    assert parse_dob_robust("09/1995/15") == date(1995, 9, 15)
    assert parse_dob_robust("15/1995/09") == date(1995, 9, 15)
    assert parse_dob_robust("1995/09/15") == date(1995, 9, 15)
    assert parse_dob_robust("1995/15/09") == date(1995, 9, 15)
    assert parse_dob_robust("09/15/1995") == date(1995, 9, 15)
    assert parse_dob_robust("15/09/1995") == date(1995, 9, 15)
    assert parse_dob_robust("1995-09-15 00:00:00") == date(1995, 9, 15)
    # Test standardize_demography outputs dd/mm/yyyy and removes Action column
    df = pd.DataFrame([
        {"DOB": "09/1995/15", "SI": 300000, "Relation": "Self", "Name": "John", "EmpCode": "E1", "Gender": "M", "Action": "Delete"},
        {"Birth Date": "1995/15/09", "SI": 300000, "Relation": "Spouse", "Name": "Jane", "EmpCode": "E1", "Gender": "F", "Action Required": "Review"}
    ])
    res = standardize_demography(df, date(2026, 1, 1))
    assert res[0]["Date of Birth"] == "15/09/1995"
    assert res[1]["Date of Birth"] == "15/09/1995"
    assert "Action" not in res[0] and "Action Required" not in res[1]

def test_room_rent_split():
    r=split_room_rent("2% of SI for Normal and 4% for ICU. Normal Room Rent is inclusive of Nursing Charges.")
    assert "Room Rent" in r and "Room Rent for Normal Room" in r and "Room Rent for ICU & Specialty Rooms" in r

def test_procedure_mapping():
    assert map_procedure_amount("Appendectomy",25000)=="Option 2"
    assert map_procedure_amount("Appendectomy",26000) is None

def test_defaults_and_unmatched():
    quote,_,_,notes,_=build_rows("Room Rent: totally custom room condition",{"group_size":10,"primary_members":4,"sme":"YES"})
    room=next(x for x in quote if x["field"]=="Room Rent")
    assert room["valid_dropdown"] is False
    assert notes

def test_decomposition_example_a_modern_treatments():
    # Example A verbatim from §15.5
    cov_text = "• Oral chemotherapy • Uterine Artery Embolization and HIFU • Balloon Sinuplasty • Deep Brain stimulation • Immunotherapy - Monoclonal Antibody to be given as injection • Intra vitreal injections (Injection Lucentis & Avastin restricted to Rs. 50000 per family) • Bronchial Thermoplasty • Cochlear Implant • Vaporisation of the prostate (Green laser treatment or holmium laser treatment)"
    prop_text = "50% Co-Pay for cyberknife treatment/Stem Cell Transplantation. Cochlaer Implant treatment shall be restricted to 50% of the SI"

    cov_assign, _ = decompose_field_group(cov_text, FIELD_GROUPS["modern_treatments"], "coverage")
    prop_assign, _ = decompose_field_group(prop_text, FIELD_GROUPS["modern_treatments"], "proposed")

    assert "Oral Chemotherapy" in cov_assign
    assert "Uterine Artery Embolization and HIFU" in cov_assign
    assert "Balloon Sinuplasty" in cov_assign
    assert "Deep Brain Stimulation" in cov_assign
    assert "Immunotherapy (incl. Monoclonal Antibody Injection)" in cov_assign
    assert "Intravitreal Injections" in cov_assign
    assert "Bronchial Thermoplasty" in cov_assign
    assert "Cochlear Implant Treatment" in cov_assign
    assert "Vaporisation of the Prostate (Green/Holmium Laser)" in cov_assign

    # Proposed shared condition rule
    assert "Gamma Knife/CyberKnife Surgery" in prop_assign
    assert "Stem Cell Therapy" in prop_assign
    assert "50% Co-Pay for cyberknife treatment/Stem Cell Transplantation" in prop_assign["Gamma Knife/CyberKnife Surgery"]
    assert "50% Co-Pay for cyberknife treatment/Stem Cell Transplantation" in prop_assign["Stem Cell Therapy"]
    assert "Cochlear Implant Treatment" in prop_assign

def test_decomposition_example_b_room_rent():
    # Example B verbatim from §15.5
    cov_text = "2% of SI for Normal and 4% for ICU. Normal Room Rent is inclusive of Nursing Charges. Rent for Normal Room Up to Single Private Room"
    prop_text = "Daily Room Rent Eligibility - Normal Room: INR 6000 (Single Pvt AC Room)\nDaily Room Rent Eligibility - Normal Room: INR 12000 (At Actuals)"

    cov_assign, _ = decompose_field_group(cov_text, FIELD_GROUPS["room_rent"], "coverage")
    prop_assign, _ = decompose_field_group(prop_text, FIELD_GROUPS["room_rent"], "proposed")

    assert cov_assign["Room Rent"] == cov_text
    assert "2% of SI for Normal" in cov_assign["Room Rent for Normal Room"]
    assert "4% for ICU" in cov_assign["Room Rent for ICU & Specialty Rooms"]

    # Step 8 Tier indicator heuristic
    assert "6000" in prop_assign["Room Rent for Normal Room"]
    assert "12000" in prop_assign["Room Rent for ICU & Specialty Rooms"] or "Actuals" in prop_assign["Room Rent for ICU & Specialty Rooms"]

def test_decomposition_example_c_pre_post_hospitalization():
    # Example C verbatim from §15.5
    cov_text = "Pre-Hosp Expenses - Upto 30 days\nPost-Hosp Expenses - Upto 60 Days"
    prop_text = "Pre-Hosp Expenses - Upto 60 days\nPost-Hosp Expenses - Upto 90 Days"

    cov_assign, _ = decompose_field_group(cov_text, FIELD_GROUPS["hospitalization"], "coverage")
    prop_assign, _ = decompose_field_group(prop_text, FIELD_GROUPS["hospitalization"], "proposed")

    assert cov_assign["Pre Hospitalization"] == "30 days"
    assert cov_assign["Post Hospitalization"] == "60 days"
    assert prop_assign["Pre Hospitalization"] == "60 days"
    assert prop_assign["Post Hospitalization"] == "90 days"

def test_decomposition_example_d_maternity():
    # Example D verbatim from §15.5
    cov_text = "Covered For Upto 125430 For Normal & For C-Section Delivery Upto 125340. Maternity covered for only first 2 children including still birth. 9 Month Waiting Period for Maternity"
    prop_text = "No Limit on Number of child deliveries"

    cov_assign, _ = decompose_field_group(cov_text, FIELD_GROUPS["maternity"], "coverage")
    prop_assign, _ = decompose_field_group(prop_text, FIELD_GROUPS["maternity"], "proposed")

    assert "Maternity Limit – Normal Delivery" in cov_assign
    assert "Maternity Limit – C Section Delivery" in cov_assign
    assert "Number of Deliveries/Kids Covered" in cov_assign
    assert "Maternity Waiting Period" in cov_assign

    # Step 5 Type validation fallback: "No Limit on Number of child deliveries" fails dropdown type check for 1/2/3
    # -> routed to parent field "Maternity Expenses/Benefits"
    assert prop_assign.get("Maternity Expenses/Benefits") == "No Limit on Number of child deliveries"
    assert "Number of Deliveries/Kids Covered" not in prop_assign


def test_mixed_file_sheets_extraction(tmp_path):
    from io import BytesIO
    import pandas as pd
    from backend.orchestration.orchestrator import Orchestrator

    rfq_df = pd.DataFrame([
        ["Sum Insured (SI)", "INR 5,00,000 per Family"],
        ["Policy Tenure", "1 Year"],
        ["Plan", "Floater"]
    ], columns=["Field", "Value"])

    demo_df = pd.DataFrame([
        ["Emp Code", "Name", "DOB", "Gender", "Relationship"],
        ["E001", "Alice", "15/08/1990", "Female", "Employee"],
        ["E002", "Bob", "01/01/1985", "Male", "Employee"]
    ])

    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        rfq_df.to_excel(writer, sheet_name="RFQ_Coverage", index=False)
        demo_df.to_excel(writer, sheet_name="Employee_Demography", index=False, header=False)
    
    excel_bytes = out.getvalue()
    orchestrator = Orchestrator()
    res = orchestrator.process([("Combined_Data.xlsx", excel_bytes)], date(2026, 9, 22))

    assert len(res["demography"]) == 2
    assert len(res["quote_rows"]) > 0
    si_row = next((r for r in res["quote_rows"] if r["field"] == "Sum Insured"), None)
    assert si_row is not None
    assert "5,00,000" in si_row["coverage_details"]


def test_additional_details_excludes_headers_and_demography():
    from backend.core.extraction_engine import build_rows
    from backend.core.file_reader import ReadResult

    df = pd.DataFrame([
        ["Description", "Expiring Terms", "Proposed Terms"],
        ["Emp Code", "E001", "E001"],
        ["DOB", "15/08/1990", "15/08/1990"],
        ["Relationship", "Self", "Self"],
        ["Gender", "Female", "Female"],
        ["Location Sublimit", "1,00,000 per location", "2,00,000 per location"],
        ["Cyber Liability Cover", "Covered up to 1,00,000", "Covered up to 2,00,000"]
    ])

    rr = ReadResult(text="", tables=[("Sheet1", df)])
    quote, hosp, additional, notes, _ = build_rows("", demography_summary=None, read_results=[rr])

    add_fields = [r["field"] for r in additional]
    assert "Description" not in add_fields
    assert "Expiring Terms" not in add_fields
    assert "Emp Code" not in add_fields
    assert "DOB" not in add_fields
    assert "Location Sublimit" in add_fields
    assert "Cyber Liability Cover" in add_fields


