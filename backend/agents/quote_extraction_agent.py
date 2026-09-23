from backend.core.extraction_engine import build_rows

def extract_quote(text: str, demo_summary: dict, read_results=None):
    return build_rows(text, demo_summary, read_results=read_results)
