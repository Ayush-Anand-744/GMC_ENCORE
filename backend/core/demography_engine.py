from datetime import date, datetime
from typing import Iterable
import pandas as pd
from backend.core.text_utils import norm, clean_text
from backend.masters.field_master import DEMOGRAPHY_COLUMNS, DEMOGRAPHY_SYNONYMS
from backend.masters.dropdown_masters import SME_THRESHOLD


import re

def parse_dob_robust(v) -> date | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v

    if isinstance(v, (int, float)):
        try:
            num = float(v)
            if 10000 <= num <= 60000:
                dt = pd.to_datetime(num, unit='D', origin='1899-12-30')
                if 1920 <= dt.year <= 2030:
                    return dt.date()
        except Exception:
            pass

    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "null", "n/a", "not available", "not stated", "-"):
        return None

    if " " in s:
        s = s.split(" ")[0].strip()
    if "T" in s:
        s = s.split("T")[0].strip()

    if s.endswith(".0"):
        try:
            num = float(s)
            if 10000 <= num <= 60000:
                dt = pd.to_datetime(num, unit='D', origin='1899-12-30')
                if 1920 <= dt.year <= 2030:
                    return dt.date()
        except Exception:
            pass
        s = s[:-2].strip()

    parts = re.split(r"[/\-\.\s]+", s)
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        nums = [int(p) for p in parts]
        y_idx = -1
        for i, n in enumerate(nums):
            if 1900 <= n <= 2030:
                y_idx = i
                break

        if y_idx != -1:
            year = nums[y_idx]
            other = [nums[i] for i in range(3) if i != y_idx]
            n1, n2 = other[0], other[1]

            if y_idx == 0:  # yyyy/mm/dd or yyyy/dd/mm
                if 1 <= n1 <= 12 and 1 <= n2 <= 31 and not (1 <= n2 <= 12 and n1 > 12):
                    try: return date(year, n1, n2)
                    except Exception: pass
                if 1 <= n2 <= 12 and 1 <= n1 <= 31:
                    try: return date(year, n2, n1)
                    except Exception: pass

            elif y_idx == 1:  # mm/yyyy/dd or dd/yyyy/mm
                if 1 <= n1 <= 12 and 1 <= n2 <= 31 and not (1 <= n2 <= 12 and n1 > 12):
                    try: return date(year, n1, n2)
                    except Exception: pass
                if 1 <= n2 <= 12 and 1 <= n1 <= 31:
                    try: return date(year, n2, n1)
                    except Exception: pass

            elif y_idx == 2:  # dd/mm/yyyy or mm/dd/yyyy
                if n1 > 12 and 1 <= n2 <= 12:
                    try: return date(year, n2, n1)
                    except Exception: pass
                if n2 > 12 and 1 <= n1 <= 12:
                    try: return date(year, n1, n2)
                    except Exception: pass
                if 1 <= n1 <= 31 and 1 <= n2 <= 12:
                    try: return date(year, n2, n1)
                    except Exception: pass
                if 1 <= n2 <= 31 and 1 <= n1 <= 12:
                    try: return date(year, n1, n2)
                    except Exception: pass

        # Handle 2-digit years e.g. 15/09/90 or 09/15/90
        n1, n2, n3 = nums[0], nums[1], nums[2]
        if n3 <= 99:
            year = 1900 + n3 if n3 >= 25 else 2000 + n3
            if 1 <= n2 <= 12 and 1 <= n1 <= 31:
                try: return date(year, n2, n1)
                except Exception: pass
            if 1 <= n1 <= 12 and 1 <= n2 <= 31:
                try: return date(year, n1, n2)
                except Exception: pass

    for df in [True, False]:
        try:
            dt = pd.to_datetime(s, dayfirst=df, errors="raise")
            if isinstance(dt, pd.Timestamp) and not pd.isna(dt):
                if 1900 <= dt.year <= 2030:
                    return dt.date()
        except Exception:
            pass

    return None

def _parse_date(v):
    return parse_dob_robust(v)

def age_last_birthday(dob, ref: date) -> int | None:
    d = parse_dob_robust(dob)
    if not d: return None
    return ref.year - d.year - ((ref.month, ref.day) < (d.month, d.day))

def map_headers(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    headers = [str(c) for c in df.columns]
    matched_cols = 0
    for canonical, variants in DEMOGRAPHY_SYNONYMS.items():
        wanted = {norm(v) for v in variants + [canonical]}
        if any(norm(h) in wanted or any(w in norm(h) for w in wanted if len(w) >= 3) for h in headers):
            matched_cols += 1

    clean_df = df
    if matched_cols < 2 and len(df) > 0:
        for r_idx in range(min(10, len(df))):
            row_str = [norm(str(v)) for v in df.iloc[r_idx] if pd.notna(v)]
            row_matched = 0
            for canonical, variants in DEMOGRAPHY_SYNONYMS.items():
                wanted = {norm(v) for v in variants + [canonical]}
                if any(val in wanted or any(w in val for w in wanted if len(w) >= 3) for val in row_str):
                    row_matched += 1
            if row_matched >= 2:
                new_cols = [str(v).strip() for v in df.iloc[r_idx]]
                clean_df = df.iloc[r_idx + 1:].copy()
                clean_df.columns = new_cols
                break

    out = {}
    for canonical, variants in DEMOGRAPHY_SYNONYMS.items():
        wanted = {norm(v) for v in variants + [canonical]}
        matched = []
        for c in clean_df.columns:
            nc = norm(str(c))
            if nc in wanted or any(w in nc for w in wanted if len(w) >= 3):
                matched.append(c)
        if matched:
            out[canonical] = matched
    return out, clean_df

def standardize_demography(df: pd.DataFrame, reference_date: date | None = None) -> list[dict]:
    reference_date = reference_date or date.today()
    mapping, clean_df = map_headers(df)
    if len(mapping) < 2:
        return []
    rows=[]
    for _, r in clean_df.iterrows():
        if r.isna().all(): continue
        item={}
        for c in DEMOGRAPHY_COLUMNS:
            if c in ("Action", "action", "ACTION"):
                continue
            src_cols = mapping.get(c, [])
            val = None
            for sc in src_cols:
                v = r.get(sc)
                if v is not None and not pd.isna(v) and str(v).strip() != "":
                    val = v
                    break
            item[c] = val

        raw_dob = item.get("Date of Birth")
        dob = parse_dob_robust(raw_dob)
        if dob:
            item["Date of Birth"] = dob.strftime("%d/%m/%Y")
            item["Age"] = age_last_birthday(dob, reference_date)
        else:
            try: item["Age"] = int(float(item["Age"])) if item["Age"] not in (None,"") else None
            except: item["Age"] = None
            item["Date of Birth"] = "Not Available"
        for key in ["Relationship","Name","EmpCode","Gender"]:
            item[key]=clean_text(item.get(key)) or "Not Available"
        si=item.get("Sum Insured")
        if isinstance(si,float) and si.is_integer(): si=int(si)
        item["Sum Insured"] = si if si not in (None,"") else "Not Available"
        # Explicitly remove Action column if present
        for act in ["Action", "action", "ACTION", "Action Required"]:
            item.pop(act, None)
        rows.append(item)
    return rows

def summary(rows: Iterable[dict]) -> dict:
    rows=list(rows); primary=0
    for r in rows:
        rel=norm(r.get("Relationship"))
        if rel in {"self","employee","primary","primary self"}: primary+=1
    return {"group_size":len(rows), "primary_members":primary, "sme":"YES" if primary <= SME_THRESHOLD else "NO"}

def recalculate_ages(rows: list[dict], ref_date: date) -> list[dict]:
    for r in rows:
        dob = parse_dob_robust(r.get("Date of Birth"))
        if dob:
            r["Age"] = age_last_birthday(dob, ref_date)
            r["Date of Birth"] = dob.strftime("%d/%m/%Y")
    return rows
