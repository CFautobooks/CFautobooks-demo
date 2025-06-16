# backend/main.py  (or whichever file you start uvicorn on)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models.user import Base as UserBase
from routers.auth import router as auth_router

# Create tables
UserBase.metadata.create_all(bind=engine)

app = FastAPI(title="CF AutoBooks API")

# === Temporarily allow all origins so we can rule out mismatches ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # <-- wildcard covers any subdomain typo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount your auth routes (router already has prefix="/auth")
app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}
