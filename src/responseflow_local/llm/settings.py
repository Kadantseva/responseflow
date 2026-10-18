import os
from pathlib import Path
from dotenv import load_dotenv

from pydantic import BaseModel, Field

load_dotenv()

def get_database_path() -> Path:
    return Path(
        os.getenv("DATABASE_PATH", "data/responseflow.db")
    )

class LlmSettings(BaseModel):
    api_key: str = Field(min_length=1)
    base_url: str = "https://api.vsellm.ru/v1"
    model: str
    timeout_seconds: float = Field(gt=0, default=30)
    max_output_tokens: int = Field(gt=0, le=4000, default=1200)


def load_settings() -> LlmSettings:
    return LlmSettings(
        api_key=os.environ["VSELLM_API_KEY"],
        base_url=os.getenv("VSELLM_BASE_URL", "https://api.vsellm.ru/v1"),
        model=os.environ["VSELLM_MODEL"],
        timeout_seconds=float(os.getenv("VSELLM_TIMEOUT_SECONDS", "30")),
        max_output_tokens=int(os.getenv("VSELLM_MAX_OUTPUT_TOKENS", "1200")),
    )
