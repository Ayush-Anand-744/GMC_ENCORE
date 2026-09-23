import re
from difflib import SequenceMatcher
from backend.masters.field_master import TERM_EQUIVALENTS

NEGATIVE_VARIANTS = {"not found", "not applicable", "not covered", "waived off", "no waiting period"}

def clean_text(value) -> str:
    if value is None: return ""
    text = str(value).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()

def norm(value) -> str:
    return re.sub(r"[^a-z0-9%]+", " ", clean_text(value).lower()).strip()

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()

def equivalent_label(value: str) -> str:
    n = norm(value)
    for canonical, variants in TERM_EQUIVALENTS.items():
        if n == norm(canonical) or any(n == norm(v) for v in variants):
            return canonical
    return clean_text(value)

def normalize_for_match(value: str) -> str:
    n = norm(value)
    if n in {norm(x) for x in NEGATIVE_VARIANTS}:
        return n
    return norm(equivalent_label(value))

def best_allowed_match(value: str, allowed: list[str], threshold: float = 0.75):
    if not value or not allowed: return None
    nv = norm(value)
    # 1. Exact norm match
    for option in allowed:
        if nv == norm(option):
            return option
    # 2. Check normalize_for_match equality
    for option in allowed:
        if normalize_for_match(value) == normalize_for_match(option):
            return option
    # 3. Numeric matching (e.g. '30 days' -> '30', 'only 2 children' -> '2')
    digits = re.findall(r"\d+", str(value))
    for option in allowed:
        if str(option).isdigit():
            if str(option) in digits or re.search(r"\b" + re.escape(str(option)) + r"\b", str(value)):
                return option
    # 4. Key phrase containment match (e.g. 'waived off' in text -> 'Waived Off')
    for option in allowed:
        no = norm(option)
        if len(no) >= 3 and (no in nv or nv in no):
            return option
    # 5. Fuzzy similarity match
    ranked = sorted(((similarity(value, x), x) for x in allowed), reverse=True)
    return ranked[0][1] if ranked and ranked[0][0] >= threshold else None


def normalize_money(value):
    if value is None: return None
    digits = re.sub(r"[^0-9.]", "", str(value).replace(",", ""))
    try: return int(float(digits))
    except: return None
