PROCEDURE_OPTIONS = {
    "Coronary Artery Bypass Grafting (CABG)": [150000,120000,80000,65000],
    "Valve Replacement": [150000,120000,80000,65000],
    "PTCA (per event hospitalization)": [130000,100000,70000,50000],
    "Total Knee Replacement (per event hospitalization)": [130000,100000,70000,50000],
    "Total Hip Replacement": [150000,120000,80000,65000],
    "Arthroscopic Surgeries": [150000,120000,80000,65000],
    "Cholecystectomy": [35000,25000,20000,20000],
    "Kidney Stone Removal (incl. DJ Stent Removal)": [35000,30000,25000,20000],
    "Appendectomy": [30000,25000,20000,15000],
    "Hysterectomy": [35000,25000,20000,15000],
    "Fistulectomy": [35000,25000,20000,15000],
    "Septoplasty": [35000,25000,20000,15000],
    "Hernia Repair": [35000,25000,20000,15000],
    "Haemorrhoidectomy": [25000,20000,15000,15000],
    "Tympanoplasty": [25000,20000,15000,15000],
    "Arthroscopy": [25000,20000,10000,10000],
    "Cataract (one eye)": [35000,25000,20000,15000],
    "Tonsillectomy": [20000,15000,10000,10000],
    "Dialysis (per session)": [5000,4000,2000,2000],
}

def map_procedure_amount(procedure: str, amount: int):
    options = PROCEDURE_OPTIONS.get(procedure)
    if not options: return None
    for idx, value in enumerate(options, 1):
        if int(amount) == value:
            return f"Option {idx}"
    return None
