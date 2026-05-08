from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    tavily_api_key: str

    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_from: str

    data_dir: Path = Path("/data")

    @property
    def db_path(self) -> Path:
        return self.data_dir / "eventbot.db"

    @property
    def db_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_path}"

    @property
    def preferences_dir(self) -> Path:
        return self.data_dir / "preferences"


def get_settings() -> Settings:
    return Settings()
