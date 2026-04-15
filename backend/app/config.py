from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    supabase_url: str
    supabase_key: str
    twilio_auth_token: str = ""
    export_token: str = ""


settings = Settings()
