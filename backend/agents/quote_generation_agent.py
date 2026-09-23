def validation_findings(demography: list[dict]):
    issues=[]; seen={}
    for idx,row in enumerate(demography, start=2):
        key=(row.get("EmpCode"),row.get("Name"),row.get("Date of Birth"),row.get("Relationship"))
        if key in seen:
            issues.append({"Severity":"Low","Row":idx,"Field":"Duplicate","Issue":f"Duplicate row for {row.get('Name','member')}.","Suggested Resolution":"Remove the duplicate row."})
        else: seen[key]=idx
    self_codes={str(r.get("EmpCode","" )).lower() for r in demography if str(r.get("Relationship","" )).lower() in {"self","employee"}}
    for idx,row in enumerate(demography,start=2):
        rel=str(row.get("Relationship","")).lower()
        code=str(row.get("EmpCode","")).lower()
        if rel not in {"self","employee"} and code and code not in self_codes:
            issues.append({"Severity":"Medium","Row":idx,"Field":"EmpCode","Issue":f"Dependent EmpCode '{row.get('EmpCode')}' has no matching Self record.","Suggested Resolution":"Ensure the employee Self row exists with the same EmpCode."})
    return issues[:500]

def deviations_from_rows(rows):
    out=[]
    for r in rows:
        if r.get("source_status") == "Not Available" and r.get("field") not in {"Brokerage%","Rater Type"}:
            out.append({"Requirement":r.get("field"),"Standard Match":"Not Available","Suggested Action":"Review manually before quote submission.","Suggested UW Remark":f"{r.get('field')} is not clearly available in the RFQ and needs RM/UW confirmation."})
    return out
