from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    llm_provider: str = "fake"
    max_attempts: int = 2


settings = Settings()
