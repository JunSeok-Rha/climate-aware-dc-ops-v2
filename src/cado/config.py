from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_role_key: str
    anthropic_api_key: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    cloudwatch_target_instance_id: str | None = None
    env: str


settings = Settings()
