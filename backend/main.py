# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
# Bring in both models so SQLAlchemy sees them
from models.user    import Base as UserBase
from models.invoice import Base as InvoiceBase

# Also import your auth router
from routers.auth import router as auth_router

# Create all tables for both models
UserBase.metadata.create_all(bind=engine)
InvoiceBase.metadata.create_all(bind=engine)

app = FastAPI(title="CF AutoBooks API")

# Temporarily open CORS so your JS can hit it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # once it’s working you can lock this to your front‐end URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount your authentication routes
app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}
