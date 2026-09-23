import base64, json, logging
from backend.config import settings
from backend.core.azure_openai_client import get_client

log = logging.getLogger(__name__)

SYSTEM = """You are a controlled extraction component for a GMC insurance quote workflow. Never invent fields. Return valid JSON only. If a value is not supported by the supplied source, return null or 'Not Found'. Respect the allowed values exactly."""

def extract_fields(text: str, field_specs: dict) -> dict:
    if not settings.AI_EXTRACTION_ENABLED or not settings.AZURE_OPENAI_TEXT_DEPLOYMENT:
        return {}
    client = get_client()
    if not client: return {}
    payload = text[:settings.AI_MAX_INPUT_CHARACTERS]
    prompt = {"fields": field_specs, "source_text": payload, "instruction": "Return an object keyed only by the supplied field names. Include confidence 0..1 per field if possible."}
    try:
        r = client.chat.completions.create(
            model=settings.AZURE_OPENAI_TEXT_DEPLOYMENT,
            temperature=0,
            response_format={"type":"json_object"},
            messages=[{"role":"system","content":SYSTEM},{"role":"user","content":json.dumps(prompt, ensure_ascii=False)}],
        )
        return json.loads(r.choices[0].message.content or "{}")
    except Exception as e:
        log.warning("AI text fallback failed: %s", type(e).__name__)
        return {}

def extract_image_fields(image_bytes: bytes, mime: str, field_specs: dict) -> dict:
    dep = settings.azure_openai_vision_deployment
    if not settings.AI_EXTRACTION_ENABLED or not dep: return {}
    client = get_client()
    if not client: return {}
    data_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"
    try:
        r = client.chat.completions.create(
            model=dep, temperature=0, response_format={"type":"json_object"},
            messages=[{"role":"system","content":SYSTEM},{"role":"user","content":[{"type":"text","text":json.dumps({"fields":field_specs,"instruction":"Extract only these fields."})},{"type":"image_url","image_url":{"url":data_url}}]}],
        )
        return json.loads(r.choices[0].message.content or "{}")
    except Exception as e:
        log.warning("AI vision fallback failed: %s", type(e).__name__)
        return {}
