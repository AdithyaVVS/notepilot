from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    auth_url: str = "http://auth:8000"
    notes_url: str = "http://notes:8000"
    ai_url: str = "http://ai:8000"


settings = Settings()
