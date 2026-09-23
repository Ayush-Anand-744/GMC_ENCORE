from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_TEXT_DEPLOYMENT: str = ""
    AZURE_OPENAI_VISION_DEPLOYEMNT: str = ""  # Intentional: matches required .env key
    AZURE_OPENAI_TRANSCRIBE_DEPLOYMENT: str = ""
    AZURE_OPENAI_API_VERSION: str = ""
    AI_EXTRACTION_ENABLED: bool = True
    AI_CONFIDENCE_THRESHOLD: float = 0.85
    AI_MAX_INPUT_CHARACTERS: int = 60000
    MAX_UPLOAD_MB: int = 50
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")

    @property
    def azure_openai_vision_deployment(self) -> str:
        return self.AZURE_OPENAI_VISION_DEPLOYEMNT

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
