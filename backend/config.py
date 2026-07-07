from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Runtime configuration for the backend.

    Provider keys are intentionally optional at startup. Individual routes or
    service modules should validate the specific key they need before calling
    upstream providers.
    """

    app_name: str = "Kaogu Tools API"
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias=AliasChoices("KAOGU_CORS_ORIGINS", "CORS_ORIGINS"),
    )
    max_upload_mb: int = Field(
        default=25,
        validation_alias=AliasChoices("KAOGU_MAX_UPLOAD_MB", "MAX_UPLOAD_MB"),
    )
    max_ocr_upload_mb: int = Field(
        default=8,
        validation_alias=AliasChoices("KAOGU_MAX_OCR_UPLOAD_MB", "MAX_OCR_UPLOAD_MB"),
    )
    max_ocr_pdf_pages: int = Field(
        default=50,
        validation_alias=AliasChoices("KAOGU_MAX_OCR_PDF_PAGES", "MAX_OCR_PDF_PAGES"),
    )

    exa_api_key: str = ""
    firecrawl_api_key: str = ""
    baidu_ocr_api_key: str = ""
    baidu_ocr_secret_key: str = ""
    baidu_ocr_app_id: str = ""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def max_ocr_upload_bytes(self) -> int:
        return self.max_ocr_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
