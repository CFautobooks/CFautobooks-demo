from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = Field(..., min_length=1)
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:3000"

    APP_BASE_URL: str = "http://localhost:3000"
    API_BASE_URL: str = "http://localhost:8000"

    STRIPE_API_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_PRICE_ID: str | None = None

    RACING_FORM_PROVIDER: str = "generic_http"
    RACING_FORM_API_BASE_URL: str | None = None
    RACING_FORM_API_KEY: str | None = None
    RACING_FORM_API_KEY_HEADER: str = "Authorization"
    RACING_FORM_MEETINGS_PATH: str = "/racecards"
    RACING_FORM_RACECARD_PATH: str = "/racecards/{meeting_id}"
    RACING_FORM_RESULTS_PATH: str = "/results"

    ODDS_PROVIDER: str = "generic_http"
    ODDS_API_BASE_URL: str | None = None
    ODDS_API_KEY: str | None = None
    ODDS_API_KEY_HEADER: str = "Authorization"
    ODDS_MARKETS_PATH: str = "/odds"

    SCRAPING_RATE_LIMIT_SECONDS: float = 3.0
    SCRAPING_HTTP_TIMEOUT_SECONDS: float = 20.0
    SCRAPING_USER_AGENT: str = "HorseRacingAnalyticsBot/0.1"
    TAB_SCRAPE_URL: str | None = None
    SPORTSBET_SCRAPE_URL: str | None = None
    RACING_COM_SCRAPE_URL: str | None = None
    PUNTERS_SCRAPE_URL: str | None = None

    ADMIN_API_TOKEN: str | None = None
    SYNC_LOOKAHEAD_DAYS: int = 1
    HTTP_TIMEOUT_SECONDS: float = 15.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("RACING_FORM_API_BASE_URL", "RACING_FORM_API_KEY", "ODDS_API_BASE_URL", "ODDS_API_KEY", "ADMIN_API_TOKEN", mode="before")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def racing_form_configured(self) -> bool:
        return bool(self.RACING_FORM_API_BASE_URL and self.RACING_FORM_API_KEY)

    @property
    def odds_configured(self) -> bool:
        return bool(self.ODDS_API_BASE_URL and self.ODDS_API_KEY)

    @property
    def stripe_configured(self) -> bool:
        return bool(self.STRIPE_API_KEY and self.STRIPE_PRICE_ID and self.STRIPE_WEBHOOK_SECRET)


settings = Settings()
