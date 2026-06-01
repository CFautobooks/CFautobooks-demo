from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./local-dev.db"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    STRIPE_API_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None

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

    ADMIN_API_TOKEN: str | None = None
    SYNC_LOOKAHEAD_DAYS: int = 1
    HTTP_TIMEOUT_SECONDS: float = 15.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
