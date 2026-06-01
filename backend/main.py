from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.database import Base, engine
from backend.routers.auth import router as auth_router
from backend.routers.billing import router as billing_router
from backend.routers.racing import router as racing_router
import backend.models  # noqa: F401 - register SQLAlchemy models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Horse Racing Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Token", "Stripe-Signature"],
)

app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(racing_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
