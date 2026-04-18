from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    supabase_url: str
    supabase_key: str
    twilio_auth_token: str = ""
    twilio_skip_validation: bool = False
    export_token: str = ""
    session_secret: str = ""
    cookie_secure: bool = False
    twilio_account_sid: str = ""
    twilio_from_number: str = ""
    anthropic_api_key: str = ""
    use_ai_agent: bool = False


settings = Settings()
