# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import engine, Base
from routers.auth import router as auth_router

# create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CF AutoBooks API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}


