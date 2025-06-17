# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models.user import Base as UserBase
from models.invoice import Base as InvoiceBase
from routers.auth import router as auth_router

# ─── Create all tables ─────────────────────────────────────────────────────────────
# Make sure both UserBase and InvoiceBase are imported above before calling this.
UserBase.metadata.create_all(bind=engine)
InvoiceBase.metadata.create_all(bind=engine)

# ─── Initialize App ────────────────────────────────────────────────────────────────
app = FastAPI(title="CF AutoBooks API")

# ─── CORS Middleware ───────────────────────────────────────────────────────────────
# This allows any front-end origin to call your API. You never have to touch it again.
app.add_middleware(
    CORSMiddleware,               # <— must be exactly CORSMiddleware
    allow_origins=["*"],          # wide-open for now; you can lock to your domain later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ────────────────────────────────────────────────────────────────────────────────────

# ─── Mount Routers ─────────────────────────────────────────────────────────────────
# All /auth routes (register & login) come from routers/auth.py
app.include_router(auth_router)


@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}

