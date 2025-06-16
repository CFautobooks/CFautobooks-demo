# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models.user import Base as UserBase
# import your auth router
from routers.auth import router as auth_router

# Create tables
UserBase.metadata.create_all(bind=engine)

# Instantiate FastAPI
app = FastAPI(title="CF AutoBooks API")

# Allow CORS from your front end
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can lock this down later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the auth router under /auth
app.include_router(auth_router, prefix="/auth", tags=["auth"])

@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}

