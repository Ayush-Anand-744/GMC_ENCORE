import re
import pandas as pd
from difflib import SequenceMatcher
from backend.core.text_utils import clean_text, norm, best_allowed_match
from backend.masters.field_master import QUOTE_SECTIONS, HOSPITAL_SECTIONS, FIELD_SYNONYMS, FIELD_GROUPS, TIER_INDICATOR_KEYWORDS
from backend.masters.dropdown_masters import DROPDOWN_MASTERS, DEFAULTS
from backend.masters.zone_master import resolve_zone

ALL_FIXED_FIELDS = [f for s in QUOTE_SECTIONS.values() for f in s] + [f for s in HOSPITAL_SECTIONS.values() for f in s]

HEADER_KEYWORDS = {
    "description", "expiring", "expiring terms", "proposed", "proposed terms", "particulars", "particular",
    "header", "headers", "s.no", "s.no.", "sr no", "sr.no.", "sl no", "sl.no.", "index", "details", "terms",
    "section", "category", "remark", "remarks", "coverage", "coverage details", "proposed details",
    "requirements", "requirement", "benefit", "benefits", "existing policy", "policy details", "rfq details",
    "quotation details", "specification", "specifications", "item", "no.", "number", "type", "list of category",
    "list of categories", "rfq / customer details", "source", "source status", "confidence level",
    "evidence & notes", "sn", "sr. no", "sl. no", "sr", "sl", "no", "s. no.", "sl. no.", "field", "fields",
    "value", "values", "midterm inclusion", "mid-term inclusion"
}

DEMO_KEYWORDS = {
    "emp code", "empcode", "employee code", "emp id", "employee id", "staff id", "member id", "insured id",
    "dob", "date of birth", "birth date", "emp dob", "dependent dob", "birth_date", "birthdate",
    "relationship", "relation", "relationship with employee", "relation with employee", "dependent", "dep",
    "gender", "sex", "name", "employee name", "member name", "insured name", "full name", "dependent name",
    "age", "emp age", "employee age", "member age", "doj", "date of joining", "joining date",
    "marital status", "department", "designation", "grade", "location", "active emp", "census", "sum insured"
}


def decompose_field_group(raw_text: str, group: dict, source_column: str = "coverage") -> tuple[dict[str, str], list[str]]:
    """
    Deconstructs a raw extracted text block into canonical field assignments per §15.3.
    """
    if not raw_text or not group:
        return {}, []

    parent_field = group.get("parent_field")
    child_fields = group.get("child_fields", {})
    assignments = {}
    unassigned = []

    if not str(raw_text).strip():
        return assignments, unassigned

    # Step 1: Capture in full - Parent field holds full original unsplit text per §15.4
    full_text = re.sub(r"\s+", " ", str(raw_text).replace("\u00a0", " ")).strip()
    if parent_field:
        assignments[parent_field] = full_text

    # Step 2: Segment into statement units (preserve line breaks and bullet markers at line start)
    prep_text = str(raw_text).replace("\u00a0", " ")
    prep_text = re.sub(r"(?:\r?\n|^)\s*[-•\*]\s+", "\n• ", prep_text)
    raw_units = []
    for line in prep_text.splitlines():
        line_str = clean_text(line)
        if not line_str: continue
        if line_str.startswith("•"):
            line_str = clean_text(line_str[1:])
        if not line_str: continue
        parts = re.split(r";\s*|(?<=[.!?])\s+(?=[A-Z0-9•\-\*])", line_str)
        for p in parts:
            p_clean = clean_text(p)
            if p_clean:
                raw_units.append(p_clean)

    # Sub-segment units by child-field keyword boundaries if unit contains multiple child fields
    segmented_units = []
    for u in raw_units:
        kw_matches = []
        u_low = u.lower()
        for fname, fcfg in child_fields.items():
            for kw in fcfg.get("keywords", []):
                idx = u_low.find(kw.lower())
                if idx != -1:
                    kw_matches.append((idx, fname))
                    break
        kw_matches.sort(key=lambda x: x[0])
        unique_matches = []
        seen_f = set()
        for idx, fname in kw_matches:
            if fname not in seen_f:
                unique_matches.append((idx, fname))
                seen_f.add(fname)
        
        if len(unique_matches) > 1 and unique_matches[1][0] > 0:
            start = 0
            for idx, _ in unique_matches[1:]:
                sub = clean_text(u[start:idx])
                if sub: segmented_units.append(sub)
                start = idx
            last_sub = clean_text(u[start:])
            if last_sub: segmented_units.append(last_sub)
        else:
            segmented_units.append(u)

    # Step 6: Distinguish split-boundary "and" / "&" from same-clause "and"
    units = []
    for u in raw_units:
        m_split = re.split(r"\s+(?:and|&)\s+", u, flags=re.I)
        if len(m_split) == 2:
            left, right = clean_text(m_split[0]), clean_text(m_split[1])
            left_kw = [fname for fname, fcfg in child_fields.items() if any(kw in left.lower() for kw in fcfg.get("keywords", []))]
            right_kw = [fname for fname, fcfg in child_fields.items() if any(kw in right.lower() for kw in fcfg.get("keywords", []))]
            if left_kw and right_kw and set(left_kw) != set(right_kw):
                if not any(k in left.lower() for k in ["co-pay", "copay", "deductible", "sublimit", "capped", "restricted"]):
                    units.append(left)
                    units.append(right)
                    continue
        units.append(u)

    # Step 8: Positional/tier heuristic for Room Rent parallel statements
    if "Room Rent for Normal Room" in child_fields and "Room Rent for ICU & Specialty Rooms" in child_fields:
        normal_kw = TIER_INDICATOR_KEYWORDS.get("normal_capped", [])
        icu_kw = TIER_INDICATOR_KEYWORDS.get("icu_uncapped", [])
        tier_normal = [u for u in units if any(k in u.lower() for k in normal_kw)]
        tier_icu = [u for u in units if any(k in u.lower() for k in icu_kw)]
        if tier_normal and tier_icu:
            assignments["Room Rent for Normal Room"] = " ".join(tier_normal)
            assignments["Room Rent for ICU & Specialty Rooms"] = " ".join(tier_icu)

    # Step 3, 4, 5: Keyword scan per unit, type validation, and assignment
    for unit in units:
        matched_fields = []
        for fname, fcfg in child_fields.items():
            keywords = fcfg.get("keywords", [])
            for kw in keywords:
                if kw in unit.lower():
                    matched_fields.append(fname)
                    break

        if not matched_fields:
            if not parent_field:
                unassigned.append(unit)
            continue

        for fname in matched_fields:
            fcfg = child_fields[fname]
            expected_type = fcfg.get("expected_type", "free_text")
            valid_value = unit

            if expected_type == "dropdown":
                dropdown_ref = fcfg.get("dropdown_ref")
                allowed = DROPDOWN_MASTERS.get(dropdown_ref, []) if dropdown_ref else []

                if fname == "Number of Deliveries/Kids Covered":
                    m_digit = re.search(r"(?:first|upto|up to|max)?\s*(\d+)\s*(?:children|child|deliveries|kids)", unit, re.I)
                    if not m_digit:
                        m_digit = re.search(r"\b([1-3])\b", unit)
                    if m_digit and m_digit.group(1) in allowed:
                        valid_value = m_digit.group(1)
                    elif "no limit" in unit.lower():
                        if parent_field:
                            assignments[parent_field] = unit
                        continue
                    else:
                        matched_opt = best_allowed_match(unit, allowed)
                        if matched_opt:
                            valid_value = matched_opt
                        else:
                            if parent_field:
                                assignments[parent_field] = unit
                            continue
                elif fname == "Maternity Waiting Period":
                    if "waived off" in unit.lower() or "waived" in unit.lower() or "no waiting period" in unit.lower():
                        valid_value = "Waived Off"
                    elif "9 month" in unit.lower():
                        valid_value = "9 Months Waiting Period"
                    elif "covered" in unit.lower():
                        valid_value = "Covered"
                    else:
                        matched_opt = best_allowed_match(unit, allowed)
                        if matched_opt:
                            valid_value = matched_opt
                        else:
                            continue

            elif expected_type == "days":
                if fname == "Pre Hospitalization":
                    m_days = re.search(r"pre[- ]?hosp\w*\D*?(\d+\s*days?)", unit, re.I)
                    if m_days:
                        valid_value = m_days.group(1).lower()
                    else:
                        m_days = re.search(r"(\d+\s*days?)", unit, re.I)
                        if m_days:
                            valid_value = m_days.group(1).lower()
                elif fname == "Post Hospitalization":
                    m_days = re.search(r"post[- ]?hosp\w*\D*?(\d+\s*days?)", unit, re.I)
                    if m_days:
                        valid_value = m_days.group(1).lower()
                    else:
                        m_days = re.search(r"(\d+\s*days?)", unit, re.I)
                        if m_days:
                            valid_value = m_days.group(1).lower()
                else:
                    m_days = re.search(r"(\d+\s*days?)", unit, re.I)
                    if m_days:
                        valid_value = m_days.group(1).lower()

            elif expected_type == "amount":
                if fname == "Maternity Limit – Normal Delivery":
                    m_norm = re.search(r"(\d{4,6})\s*(?:for\s*)?normal", unit, re.I)
                    if not m_norm:
                        m_norm = re.search(r"normal[^\d]*(\d{4,6})", unit, re.I)
                    if m_norm:
                        valid_value = m_norm.group(1)
                elif fname == "Maternity Limit – C Section Delivery":
                    m_csec = re.search(r"(?:c-section|c section|cesarean)[^\d]*(\d{4,6})", unit, re.I)
                    if not m_csec:
                        m_csec = re.search(r"(\d{4,6})[^\d]*(?:c-section|c section|cesarean)", unit, re.I)
                    if m_csec:
                        valid_value = m_csec.group(1)

            # Step 7: Shared trailing clauses / assign to child field
            if fname not in assignments:
                assignments[fname] = valid_value
            elif valid_value not in assignments[fname]:
                assignments[fname] = assignments[fname] + ". " + valid_value

    return assignments, unassigned


def _line_candidates(text: str):
    out = []
    for raw in text.splitlines():
        line = clean_text(raw)
        if not line: continue
        parts = re.split(r"\s*[:|\t]\s*", line, maxsplit=1)
        if len(parts) == 2 and parts[0] and parts[1]:
            out.append((parts[0], parts[1]))
        elif "," in line:
            csv_parts = [clean_text(p) for p in line.split(",") if clean_text(p)]
            if len(csv_parts) >= 2:
                out.append((csv_parts[0], csv_parts[1]))
        else:
            m = re.match(r"^(.{2,70}?)\s+-\s+(.+)$", line)
            if m: out.append((m.group(1), m.group(2)))
    return out


HEADER_EXACT = {
    "description", "expiring", "expiring terms", "proposed", "proposed terms", "particulars", "particular",
    "header", "headers", "s.no", "s.no.", "sr no", "sr.no.", "sl no", "sl.no.", "index", "details", "terms",
    "section", "category", "remark", "remarks", "coverage details", "proposed details", "list of category",
    "list of categories", "rfq / customer details", "source status", "confidence level", "evidence & notes",
    "sn", "sr. no", "sl. no", "sr", "sl", "no", "s. no.", "sl. no.", "field", "fields", "value", "values",
    "s.no / particulars", "sr.no / particulars", "particulars / benefits"
}

DEMO_EXACT = {
    "emp code", "empcode", "employee code", "emp id", "employee id", "staff id", "member id", "insured id",
    "dob", "date of birth", "birth date", "emp dob", "dependent dob", "birth_date", "birthdate", "d.o.b", "date_of_birth",
    "relationship", "relation with employee", "gender", "sex", "employee name", "member name", "insured name"
}


def is_header_label_or_data(label: str, cov: str = "", prop: str = "") -> bool:
    nl = norm(label)
    ncov = norm(cov)
    nprop = norm(prop)

    if not nl:
        return False

    if nl in HEADER_EXACT:
        return True

    if ncov in HEADER_EXACT and nprop in HEADER_EXACT:
        return True

    return False


def is_demography_label_or_data(label: str, cov: str = "", prop: str = "") -> bool:
    nl = norm(label)
    ncov = norm(cov)
    nprop = norm(prop)

    if not nl:
        return False

    if nl in DEMO_EXACT:
        return True

    if re.fullmatch(r"e-?\d{3,8}", nl, re.I) or re.fullmatch(r"emp\d+", nl, re.I):
        return True

    if re.fullmatch(r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}", nl):
        return True

    REL_TERMS = {"self", "spouse", "husband", "wife", "child", "son", "daughter", "father", "mother", "parent"}
    if nl in REL_TERMS:
        return True
    if ncov in REL_TERMS and nprop in REL_TERMS:
        return True

    return False


def _field_for_label(label: str):
    if not label: return None
    nl = norm(label)
    if not nl: return None

    # Disambiguation rules
    if nl in {"location", "city", "address"}:
        return None
    if "group mediclaim benefits" in nl or nl in {"company name", "organization name", "client name", "proposer name", "employer name", "policyholder name"}:
        return "Organization Name"
    if "policy scope type" in nl or "scope of policy" in nl:
        return "Plan"

    # Tier 1: Exact match with canonical field or any synonym
    for field, synonyms in FIELD_SYNONYMS.items():
        for s in [field] + synonyms:
            if nl == norm(s):
                return field

    # Tier 2: Key phrase containment (prefer longest matching synonym)
    GENERIC_SYNONYMS = {
        "sublimit", "sub-limit", "sub limit", "limit", "limits", "capping", "cover", "coverage",
        "clause", "benefit", "benefits", "treatment", "treatments", "expenses", "charges",
        "allowance", "type", "mode", "option", "tier", "room", "day", "care", "baby",
        "location", "state", "city", "plan", "zone", "name", "code", "id", "period", "waiting", "ambulance"
    }
    matches = []
    for field, synonyms in FIELD_SYNONYMS.items():
        for s in [field] + synonyms:
            ns = norm(s)
            if not ns or ns in GENERIC_SYNONYMS:
                continue
            if " " in ns and len(ns) >= 5 and re.search(r"\b" + re.escape(ns) + r"\b", nl):
                matches.append((len(ns), field))
    if matches:
        matches.sort(reverse=True)
        return matches[0][1]

    # Tier 3: Fuzzy similarity matching for typos
    scored = []
    for field, synonyms in FIELD_SYNONYMS.items():
        for s in [field] + synonyms:
            ns = norm(s)
            if not ns or ns in GENERIC_SYNONYMS or " " not in ns: continue
            ratio = SequenceMatcher(None, nl, ns).ratio()
            if ratio >= 0.78:
                scored.append((ratio, field))
    if scored:
        scored.sort(reverse=True)
        return scored[0][1]

    return None


def parse_table_like_text(text: str):
    extracted = {}; unmapped = []
    for label, value in _line_candidates(text):
        if is_header_label_or_data(label, value) or is_demography_label_or_data(label, value):
            continue
        field = _field_for_label(label)
        if field and field not in extracted:
            extracted[field] = value
        elif not field and len(label) <= 100:
            unmapped.append((label, value))
    return extracted, unmapped


def split_room_rent(value: str):
    full = clean_text(value); result = {"Room Rent": full}
    if not full: return result
    normal = []; icu = []
    for sent in re.split(r"(?<=[.!?])\s+|\n", full):
        low = sent.lower()
        m = re.search(r"([^.;]*?\b(?:\d+(?:\.\d+)?%|single private room|twin sharing)[^.;]*?)\b(?:for\s+)?normal\b.*?\b(?:and|,|/)\b\s*([^.;]*?\b(?:\d+(?:\.\d+)?%|\d+[^.;]*)[^.;]*?)\b(?:for\s+)?icu\b", sent, re.I)
        if m:
            normal.append(clean_text(m.group(1) + " for Normal"))
            icu.append(clean_text(m.group(2) + " for ICU"))
            continue
        if "normal" in low: normal.append(sent)
        if "icu" in low or "specialty" in low: icu.append(sent)
    if normal: result["Room Rent for Normal Room"] = " ".join(normal)
    if icu: result["Room Rent for ICU & Specialty Rooms"] = " ".join(icu)
    return result


def split_pre_post_hospitalization(value: str):
    res = {}
    if not value: return res
    m_pre = re.search(r"pre[- ]?hosp\w*\D*?(\d+\s*days?)", value, re.I)
    if m_pre: res["Pre Hospitalization"] = m_pre.group(0)
    m_post = re.search(r"post[- ]?hosp\w*\D*?(\d+\s*days?)", value, re.I)
    if m_post: res["Post Hospitalization"] = m_post.group(0)
    return res


def split_maternity_details(value: str):
    res = {}
    if not value: return res
    res["Maternity Expenses/Benefits"] = "Covered"
    if "waived off" in value.lower() or "waived" in value.lower():
        res["Maternity Waiting Period"] = "Waived Off"
    elif "9 month" in value.lower():
        res["Maternity Waiting Period"] = "9 Months Waiting Period"
    m_norm = re.search(r"normal\D*?(\d{4,6})", value, re.I)
    if m_norm: res["Maternity Limit – Normal Delivery"] = m_norm.group(1)
    m_csec = re.search(r"(?:c-section|c section)\D*?(\d{4,6})", value, re.I)
    if m_csec: res["Maternity Limit – C Section Delivery"] = m_csec.group(1)
    return res


def parse_sum_insured(value: str):
    if not value: return None
    m = re.search(r"(\d+(?:\.\d+)?\s*(?:lakhs?|lacs?|lac|lakh|k|m|cr|crore)|inr\s*[\d,]+|\b\d{5,8}\b)", value, re.I)
    if m: return clean_text(m.group(0))
    return clean_text(value)


def detect_incumbent(text: str):
    low = text.lower()
    patterns = [r"(?:incumbent|current insurer|existing insurer|proposing company)\s*[:\-]?\s*([^\n|,;]+)"]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m: return clean_text(m.group(1))
    if "bajaj" in low and ("insurer" in low or "renewal" in low): return "Bajaj"
    return ""


def parse_structured_tables(read_results):
    """Extract field/coverage/proposed triples from tabular RFQs using header and positional semantics."""
    mapped = {}
    unmapped = []
    for rr in read_results or []:
        for _, df in rr.tables:
            if df is None or df.empty: continue
            
            header_row_idx = None
            field_col = 0
            coverage_cols = []
            proposed_cols = []

            num_cols = len(df.columns)
            for r_idx in range(min(10, len(df))):
                row_vals = [norm(str(v)) for v in df.iloc[r_idx] if pd.notna(v)]
                if any(k in " ".join(row_vals) for k in ["coverage", "proposed", "requirement", "particular", "benefit"]):
                    header_row_idx = r_idx
                    for c_idx, val in enumerate(df.iloc[r_idx]):
                        nc = norm(str(val))
                        if any(k in nc for k in ["requirement", "benefit", "particular", "field", "category"]):
                            field_col = c_idx
                        if "proposed" in nc:
                            proposed_cols.append(c_idx)
                        elif "policy" in nc or "coverage" in nc or "current" in nc or "details" in nc:
                            coverage_cols.append(c_idx)
                    break

            start_row = (header_row_idx + 1) if header_row_idx is not None else 0

            if not coverage_cols:
                if num_cols == 2:
                    coverage_cols = [1]
                elif num_cols >= 3:
                    coverage_cols = [1]
                    if not proposed_cols:
                        proposed_cols = [2]

            last_mapped_field = None
            for r_idx in range(start_row, len(df)):
                row = df.iloc[r_idx]
                raw_label = clean_text(row.iloc[field_col]) if field_col < num_cols and pd.notna(row.iloc[field_col]) else ""
                
                cov = ""
                for c in coverage_cols:
                    if c < num_cols and pd.notna(row.iloc[c]):
                        val = clean_text(row.iloc[c])
                        if val and val.lower() not in {"nan", "none"}:
                            cov = val
                            break

                prop = ""
                for c in proposed_cols:
                    if c < num_cols and pd.notna(row.iloc[c]):
                        val = clean_text(row.iloc[c])
                        if val and val.lower() not in {"nan", "none"}:
                            prop = val
                            break

                if not raw_label or raw_label.lower() in {"nan", "none"}:
                    if last_mapped_field and (cov or prop):
                        cur = mapped[last_mapped_field]
                        if cov:
                            cur["coverage"] = (cur["coverage"] + "\n" + cov) if cur["coverage"] else cov
                        if prop:
                            cur["proposed"] = (cur["proposed"] + "\n" + prop) if cur["proposed"] else prop
                    continue

                nl_raw = norm(raw_label)
                if "pre" in nl_raw and "post" in nl_raw:
                    for f in ["Pre Hospitalization", "Post Hospitalization"]:
                        cur = mapped.setdefault(f, {"coverage": "", "proposed": ""})
                        if cov: cur["coverage"] = (cur["coverage"] + "\n" + cov) if cur["coverage"] else cov
                        if prop: cur["proposed"] = (cur["proposed"] + "\n" + prop) if cur["proposed"] else prop
                    last_mapped_field = "Pre Hospitalization"
                    continue

                field = _field_for_label(raw_label)
                if field:
                    last_mapped_field = field
                    cur = mapped.setdefault(field, {"coverage": "", "proposed": ""})
                    if cov:
                        cur["coverage"] = (cur["coverage"] + "\n" + cov) if cur["coverage"] else cov
                    if prop:
                        cur["proposed"] = (cur["proposed"] + "\n" + prop) if cur["proposed"] else prop
                elif cov or prop:
                    last_mapped_field = None
                    if not is_header_label_or_data(raw_label, cov, prop) and not is_demography_label_or_data(raw_label, cov, prop):
                        unmapped.append((raw_label, cov, prop))
    return mapped, unmapped


def build_rows(text: str, demography_summary: dict | None = None, read_results=None):
    extracted, unmapped_text = parse_table_like_text(text)
    structured, unmapped_struct = parse_structured_tables(read_results)

    # Run Semantic Field Decomposition Engine (§15) ONCE per Field Group per source column
    for group_name, group_cfg in FIELD_GROUPS.items():
        parent_field = group_cfg.get("parent_field")
        child_fields = group_cfg.get("child_fields", {})

        cov_text = ""
        prop_text = ""

        # Priority 1: Parent field text if available
        if parent_field:
            pair = structured.get(parent_field, {})
            cov_text = pair.get("coverage") or extracted.get(parent_field, "")
            prop_text = pair.get("proposed") or ""

        # Priority 2: Fallback to combining child field text if parent field has no text
        if not cov_text or not prop_text:
            c_cov = []
            c_prop = []
            for cf in child_fields.keys():
                pair = structured.get(cf, {})
                if pair.get("coverage"): c_cov.append(pair["coverage"])
                elif extracted.get(cf): c_cov.append(extracted[cf])
                if pair.get("proposed"): c_prop.append(pair["proposed"])
            if not cov_text and c_cov:
                cov_text = "\n".join(c_cov)
            if not prop_text and c_prop:
                prop_text = "\n".join(c_prop)

        if cov_text:
            cov_assignments, _ = decompose_field_group(cov_text, group_cfg, source_column="coverage")
            for fname, val in cov_assignments.items():
                if val:
                    extracted[fname] = val
                    structured.setdefault(fname, {})["coverage"] = val

        if prop_text:
            prop_assignments, _ = decompose_field_group(prop_text, group_cfg, source_column="proposed")
            for fname, val in prop_assignments.items():
                if val:
                    structured.setdefault(fname, {})["proposed"] = val

    # Cataract Logic Check:
    # If any Cataract-related data is present in input, Waiver of Cataract Sublimit must display "Applicable"
    cat_cov = structured.get("Cataract", {}).get("coverage") or extracted.get("Cataract") or structured.get("Waiver of Cataract Sublimit", {}).get("coverage") or extracted.get("Waiver of Cataract Sublimit")
    cat_prop = structured.get("Cataract", {}).get("proposed") or structured.get("Waiver of Cataract Sublimit", {}).get("proposed")

    if not cat_cov:
        m_cat = re.search(r"\bcataract\b[^\n,;]*", text, re.I)
        if m_cat:
            cat_cov = clean_text(m_cat.group(0))

    if cat_cov:
        extracted["Waiver of Cataract Sublimit"] = "Applicable"
        structured["Waiver of Cataract Sublimit"] = {"coverage": "Applicable", "proposed": "Applicable"}
        extracted["Cataract"] = cat_cov
        structured["Cataract"] = {"coverage": cat_cov, "proposed": cat_prop or "Not Available"}

    incumbent = detect_incumbent(text)
    if incumbent:
        extracted["Type of Proposal"] = "Own Renewal" if "bajaj" in incumbent.lower() else "Roll Over"
    if "Zone" not in extracted:
        zone = resolve_zone(text)
        if zone != "Pan India": extracted["Zone"] = zone

    if "Plan" in extracted and best_allowed_match(extracted["Plan"], DROPDOWN_MASTERS.get("Policy Type", [])):
        extracted["Policy Type"] = best_allowed_match(extracted["Plan"], DROPDOWN_MASTERS["Policy Type"])

    if demography_summary:
        extracted["Group Size"] = str(demography_summary["group_size"])
        extracted["Number of Primary Members"] = str(demography_summary["primary_members"])
        extracted["Flagging SME"] = demography_summary["sme"]

    unmatched_notes = []

    def make_row(section, field, allow_defaults):
        pair = structured.get(field, {})
        raw = pair.get("coverage") or extracted.get(field)
        proposed = pair.get("proposed") or "Not Available"
        valid = None; unmatched = None

        if field == "Brokerage%":
            display = ""; status = "Not Available"
        elif raw not in (None, ""):
            display = clean_text(raw)
            status = "RFQ Data"
            if field in DROPDOWN_MASTERS:
                match = best_allowed_match(display, DROPDOWN_MASTERS[field])
                if match:
                    valid = True
                    if len(display) <= 30 or display.lower() in {m.lower() for m in DROPDOWN_MASTERS[field]}:
                        display = match
                else:
                    valid = False
                    unmatched = display
                    unmatched_notes.append(f'Unmatched word "{unmatched}" was detected for {field}')
        elif pair.get("proposed"):
            display = "Not Available"; status = "RFQ Data"
        elif allow_defaults and field in DEFAULTS:
            display = DEFAULTS[field]; status = "Default Data"
        else:
            display = "Not Available"; status = "Not Available"

        return {
            "section": section,
            "field": field,
            "coverage_details": display,
            "proposed_details": clean_text(proposed),
            "source_status": status,
            "valid_dropdown": valid,
            "unmatched_value": unmatched
        }

    quote = []; hosp = []
    for section, fields in QUOTE_SECTIONS.items():
        quote.extend(make_row(section, f, True) for f in fields)
    for section, fields in HOSPITAL_SECTIONS.items():
        hosp.extend(make_row(section, f, False) for f in fields)

    # Additional Details: Include ONLY dynamic fields present in input that are NOT already in Quote Form or Hospitalization tables
    all_fixed_set = set(ALL_FIXED_FIELDS)
    already_displayed_fields = set()

    for r in quote + hosp:
        if r.get("source_status") != "Not Available" or r.get("field") in set(extracted.keys()) | set(structured.keys()):
            already_displayed_fields.add(r.get("field"))

    additional = []
    seen_additional_keys = set()

    raw_candidates = []
    for item in unmapped_text:
        l, v = item
        raw_candidates.append((l, v, "Not Available"))
    for l, cov, prop in unmapped_struct:
        raw_candidates.append((l, cov or "Not Available", prop or "Not Available"))

    for l, cov, prop in raw_candidates:
        l_clean = clean_text(l)
        if not l_clean or l_clean.startswith("[SHEET") or "sheet:" in l_clean.lower():
            continue

        nl = norm(l_clean)
        if not nl or len(nl) < 2:
            continue

        # 1. Filter out structural headers and column titles (e.g. Description, Expiring, Particulars)
        if is_header_label_or_data(l_clean, cov, prop):
            continue

        # 2. Filter out demographic/census fields (e.g. Emp Code, DOB, Gender, Relation, Name, Age, etc.)
        if is_demography_label_or_data(l_clean, cov, prop):
            continue

        # 3. Filter out labels that map to fixed Quote Form or Hospitalization fields
        mapped_field = _field_for_label(l_clean)
        if mapped_field and mapped_field in all_fixed_set:
            continue

        # 4. Filter out items where coverage or proposed is empty, not available, or repeating header text
        cov_clean = clean_text(cov) if cov and cov.lower() not in {"nan", "none", "not available", "n/a", "-"} else ""
        prop_clean = clean_text(prop) if prop and prop.lower() not in {"nan", "none", "not available", "n/a", "-"} else ""

        if not cov_clean and not prop_clean:
            continue

        if (cov_clean and is_header_label_or_data(cov_clean)) or (prop_clean and is_header_label_or_data(prop_clean)):
            continue

        # Prevent duplicate entries in Additional Details
        if nl in seen_additional_keys:
            continue
        seen_additional_keys.add(nl)

        additional.append({
            "section": "Additional Details",
            "field": l_clean,
            "coverage_details": cov_clean or "Not Available",
            "proposed_details": prop_clean or "Not Available",
            "source_status": "RFQ Data",
            "valid_dropdown": None,
            "unmatched_value": None
        })

    return quote, hosp, additional, unmatched_notes, extracted
