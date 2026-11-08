from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    llm_provider: str = "fake"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    max_attempts: int = 2
    user_daily_limit: int = 10
    global_daily_limit: int = 80


settings = Settings()
