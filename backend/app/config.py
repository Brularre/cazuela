from pydantic import ConfigDict
from pydantic_settings import BaseSettings


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


settings = Settings()
