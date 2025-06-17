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
    allow_origins=[
      "https://cfautobooks-demo.onrender.com",      # your frontend URL
      "http://localhost:8000",                      # for local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}


