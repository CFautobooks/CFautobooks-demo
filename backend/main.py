from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models.user import Base as UserBase
from routers.auth import router as auth_router

# Create all tables
UserBase.metadata.create_all(bind=engine)

app = FastAPI(title="CF AutoBooks API")

# === Enable CORS for your front-end ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # you can narrow this to ["https://cfautobooks-demo.onrender.com"] later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the auth router (its prefix="/auth" lives in routers/auth.py)
app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}
