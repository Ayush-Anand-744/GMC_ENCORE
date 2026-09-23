from openai import AzureOpenAI
from backend.config import settings

_client = None

def get_client():
    global _client
    if _client is not None: return _client
    if not (settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_VERSION):
        return None
    _client = AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        timeout=40.0,
        max_retries=2,
    )
    return _client
