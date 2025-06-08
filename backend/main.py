from fastapi import FastAPI
from core.config import settings
from database import engine
from models.user import Base as UserBase
from models.invoice import Base as InvoiceBase
from routers import auth, dashboard, admin
from fastapi.middleware.cors import CORSMiddleware

# Create all tables
UserBase.metadata.create_all(bind=engine)
InvoiceBase.metadata.create_all(bind=engine)

app = FastAPI(title="CF AutoBooks Backend")

# CORS
origins = ["*"]  # Restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(admin.router)

@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}