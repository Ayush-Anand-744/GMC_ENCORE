from datetime import date

from backend.core.file_reader import read_file, ReadResult
from backend.agents.file_classifier_agent import classify_content, classify_table
from backend.agents.demography_agent import extract_demography
from backend.agents.quote_extraction_agent import extract_quote
from backend.agents.quote_generation_agent import validation_findings, deviations_from_rows
from backend.core.demography_engine import summary as demo_summary


def _clean_cell(value):
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _extracted_data_rows(rfq_reads, classifications):
    """Build a read-only parser view for the Extracted Data tab.

    This intentionally consumes the already-read source representation and does
    not participate in field extraction, matching, decomposition, or defaults.
    """
    out = []
    rfq_names = [x["filename"] for x in classifications if x["category"] != "demography"]
    for file_index, rr in enumerate(rfq_reads):
        filename = rfq_names[file_index] if file_index < len(rfq_names) else f"RFQ {file_index + 1}"
        if rr.tables:
            for sheet_name, df in rr.tables:
                for row_num, (_, row) in enumerate(df.iterrows(), start=1):
                    vals = [_clean_cell(v) for v in row.tolist()]
                    vals = [v for v in vals if v]
                    if not vals:
                        continue
                    out.append({
                        "File": filename,
                        "Label": vals[0],
                        "Coverage": vals[1] if len(vals) > 1 else "",
                        "Proposed": " | ".join(vals[2:]) if len(vals) > 2 else "",
                    })
        else:
            has_lines = False
            if rr.text.strip():
                for row_num, line in enumerate(rr.text.splitlines(), start=1):
                    line = line.strip()
                    if not line:
                        continue
                    has_lines = True
                    if ":" in line:
                        label, value = line.split(":", 1)
                    else:
                        label, value = line, ""
                    out.append({
                        "File": filename,
                        "Label": label.strip(),
                        "Coverage": value.strip(),
                        "Proposed": "",
                    })
            if not has_lines:
                out.append({
                    "File": filename,
                    "Label": "(File Attached)",
                    "Coverage": "",
                    "Proposed": "",
                })
    return out[:5000]


def _quote_exceptions(rows):
    out = []
    seen = set()
    for r in rows:
        status = r.get("source_status")
        conflict = r.get("valid_dropdown") is False or bool(r.get("unmatched_value"))
        if status != "Not Available" and not conflict:
            continue
        field = r.get("field", "")
        key = (field, status, r.get("unmatched_value"))
        if key in seen:
            continue
        seen.add(key)
        if conflict:
            issue = f"Extracted value '{r.get('unmatched_value') or r.get('coverage_details')}' does not match the configured value set."
            resolution = "Confirm the correct value with the RM before submission."
        else:
            issue = f"{field} is not clearly available in the RFQ and needs RM/UW confirmation."
            resolution = "Review manually before quote submission."
        out.append({
            "Section": r.get("section", ""),
            "Field": field,
            "Issue": issue,
            "Suggested Resolution": resolution,
        })
    return out


import pandas as pd

def _df_to_text(sheet_name: str, df: pd.DataFrame) -> str:
    lines = [f"[SHEET: {sheet_name}]"]
    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row if v is not None and not (isinstance(v, float) and pd.isna(v)) and str(v).strip() != ""]
        if not vals:
            continue
        if len(vals) == 1:
            lines.append(vals[0])
        elif len(vals) == 2:
            lines.append(f"{vals[0]}: {vals[1]}")
        else:
            lines.append(f"{vals[0]}: {vals[1]} | {vals[2]}")
    return "\n".join(lines)


class Orchestrator:
    def process(self, files: list[tuple[str, bytes]], reference_date: date):
        rfq_text = []
        rfq_reads = []
        demo_reads = []
        classifications = []

        for name, data in files:
            rr = read_file(name, data)
            overall_kind = classify_content(name, rr.text, rr.tables)
            classifications.append({"filename": name, "category": overall_kind})

            if rr.tables and len(rr.tables) > 0:
                for sheet_name, df in rr.tables:
                    t_kind = classify_table(sheet_name, df)
                    sheet_text = _df_to_text(sheet_name, df)
                    sheet_rr = ReadResult(text=sheet_text, tables=[(sheet_name, df)], metadata=rr.metadata)
                    if t_kind == "demography":
                        demo_reads.append(sheet_rr)
                    else:
                        rfq_reads.append(sheet_rr)
                        rfq_text.append(sheet_text)
            else:
                if overall_kind == "demography":
                    demo_reads.append(rr)
                else:
                    rfq_text.append(rr.text)
                    rfq_reads.append(rr)

        # Fallback safeguard: If no demography reads were classified but a table across any uploaded file contains demography rows, include it
        if not demo_reads:
            for name, data in files:
                rr = read_file(name, data)
                if rr.tables:
                    for sheet_name, df in rr.tables:
                        demo_reads.append(ReadResult(text=rr.text, tables=[(sheet_name, df)], metadata=rr.metadata))

        demography = extract_demography(demo_reads, reference_date)
        ds = demo_summary(demography)
        text = "\n\n".join(rfq_text)
        quote, hospital, additional, notes, _ = extract_quote(text, ds, rfq_reads)

        validation = validation_findings(demography)
        deviations = deviations_from_rows(quote + hospital)
        quote_exceptions = _quote_exceptions(quote + hospital)
        extracted_data = _extracted_data_rows(rfq_reads, classifications)

        total_fields = len(quote)
        filled = sum(1 for r in quote if r["source_status"] != "Not Available")
        auto = int(round((filled / total_fields) * 100)) if total_fields else 0
        review = sum(
            1
            for r in quote
            if r["source_status"] == "Not Available" or r.get("valid_dropdown") is False
        )

        return {
            "quote_rows": quote,
            "additional_rows": additional,
            "hospital_rows": hospital,
            "demography": demography,
            "validation_rows": validation,
            "demography_exceptions": validation,
            "quote_exceptions": quote_exceptions,
            "extracted_data": extracted_data,
            "deviations": deviations,
            "unmatched_notes": notes,
            "summary": {
                "total_fields": total_fields,
                "auto_fill_rate": auto,
                "review_required": review,
                "deviations": len(deviations),
                "total_tokens": 0,
                "demo_lives": len(demography),
            },
            "extraction_mode": "hybrid (AI on)",
            "remark_by": "template",
            "classifications": classifications,
        }
