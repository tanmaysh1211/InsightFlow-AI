import os
# from pydantic_settings import BaseSettings
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
    
    # LLM Settings
    OPENAI_API_KEY: str = Field(default="", validation_alias="OPENAI_API_KEY")
    OPENROUTER_API_KEY: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    
    # App Mode: "simulation" or "live". If live, it will try calling OPENAI/OpenRouter.
    APP_MODE: str = Field(default="simulation", validation_alias="APP_MODE")
    
    # Metadata Database URL (stores connections, query history, logs)
    METADATA_DATABASE_URL: str = "sqlite+aiosqlite:///copilot_metadata.db"
    
    # Encryption key for securing connection passwords.
    # In production, this must be a secure random 32-byte key.
    ENCRYPTION_KEY: str = "InsightFlow-AISecretKey="

    # class Config:
    #     env_file = ".env"
    #     case_sensitive = True

settings = Settings()
