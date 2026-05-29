import os

from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings
from zoneinfo import ZoneInfo


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_key: str
    export_token: str = ""
    session_secret: str = ""
    cookie_secure: bool = False
    meta_app_secret: str = ""
    meta_phone_number_id: str = ""
    meta_access_token: str = ""
    meta_webhook_verify_token: str = ""
    meta_skip_validation: bool = False
    anthropic_api_key: str = ""
    use_ai_agent: bool = False
    dashboard_url: str = ""
    backend_url: str = ""

    classifier_provider: str = "anthropic"
    classifier_api_key: str | None = None
    classifier_model: str = "claude-haiku-4-5-20251001"

    responder_provider: str = "anthropic"
    responder_api_key: str | None = None
    responder_model: str = "claude-haiku-4-5-20251001"

    @model_validator(mode="after")
    def _backfill_from_legacy(self) -> "Settings":
        if self.use_ai_agent and self.anthropic_api_key:
            if not self.classifier_api_key:
                self.classifier_api_key = self.anthropic_api_key
            if not self.responder_api_key:
                self.responder_api_key = self.anthropic_api_key
        if not self.use_ai_agent:
            if self.classifier_provider == "anthropic" and not self.classifier_api_key:
                self.classifier_provider = "none"
            if self.responder_provider == "anthropic" and not self.responder_api_key:
                self.responder_provider = "none"
        return self


settings = Settings()

TZ = ZoneInfo(os.environ.get("DEFAULT_TZ", "America/Santiago"))
