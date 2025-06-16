# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models.user import Base as UserBase
from routers.auth import router as auth_router

# Create all database tables
UserBase.metadata.create_all(bind=engine)

# Instantiate FastAPI
app = FastAPI(title="CF AutoBooks API")

# Enable CORS for your front-end
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # lock this down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the auth router (router itself defines prefix="/auth")
app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}

