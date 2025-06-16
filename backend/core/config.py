import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    STRIPE_API_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    OCR_SERVICE_URL: str
    SENDGRID_API_KEY: optional str
    FROM_EMAIL: cfautobooks@gmail.com str

    class Config:
        env_file = ".env"

settings = Settings()
