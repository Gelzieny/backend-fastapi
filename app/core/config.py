from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Benchmark IA API"
    DATABASE_URL: str = "postgresql+asyncpg://benchmark_user:benchmark_password@localhost:5432/benchmark_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
