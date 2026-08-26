from typing import List

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    app_name: str = "Sovereignty AI Studio"
    debug: bool = False
    database_url: str
    redis_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    openai_api_key: str = ""

    cors_origins: List[str] = [
        "https://localhost:3000",
        "https://localhost:8080",
        "https://localhost:9898",
        "https://127.0.0.1:9898",
    ]


settings = Settings()
