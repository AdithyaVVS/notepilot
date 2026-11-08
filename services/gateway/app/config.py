from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    auth_url: str = "http://auth:8000"
    notes_url: str = "http://notes:8000"
    ai_url: str = "http://ai:8000"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    auth_rate_limit: int = 10
    max_body_bytes: int = 65536

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
