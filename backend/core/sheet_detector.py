from backend.masters.field_master import DEMOGRAPHY_SYNONYMS
from backend.core.text_utils import norm

def score_demography_headers(headers) -> int:
    normalized = {norm(h) for h in headers if h is not None}
    score = 0
    for variants in DEMOGRAPHY_SYNONYMS.values():
        if any(norm(v) in normalized for v in variants): score += 1
    return score

def pick_best_demography_sheet(sheets: dict):
    best_name, best_score = None, -1
    for name, df in sheets.items():
        score = score_demography_headers(list(df.columns))
        if score > best_score:
            best_name, best_score = name, score
    return best_name, best_score
