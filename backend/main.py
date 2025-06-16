from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from database import engine
from models.user import Base as UserBase
from models.invoice import Base as InvoiceBase
from routers.auth import router as auth_router
from routers.dashboard import router as dashboard_router
from routers.admin import router as admin_router
from routers.invoices import router as invoices_router

# Create all tables (users, invoices, etc.)
UserBase.metadata.create_all(bind=engine)
InvoiceBase.metadata.create_all(bind=engine)

app = FastAPI(title="CF AutoBooks Backend")

# CORS: allow all origins for testing; lock this down once frontend<->API are confirmed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # <— allow requests from any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers under their prefixes
app.include_router(auth_router,      prefix="/auth",      tags=["auth"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(admin_router,     prefix="/admin",     tags=["admin"])
app.include_router(invoices_router,  prefix="/invoices",  tags=["invoices"])

@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}

@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}

