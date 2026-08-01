import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "InsightFlow-AI"
    API_V1_STR: str = "/api/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    OPENAI_API_KEY: str = Field(default="", validation_alias="OPENAI_API_KEY")
    OPENROUTER_API_KEY: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    
    APP_MODE: str = Field(default="simulation", validation_alias="APP_MODE")
    
    METADATA_DATABASE_URL: str = "sqlite+aiosqlite:///copilot_metadata.db"
    
    ENCRYPTION_KEY: str = "InsightFlow-AISecretKey="

settings = Settings()
