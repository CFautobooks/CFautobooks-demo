from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from routers.auth import auth_router
from routers.admin import admin_router
from routers.invoices import invoices_router

app = FastAPI(title="CF AutoBooks API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(invoices_router, prefix="/invoices", tags=["invoices"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])

@app.get("/")
def root():
    return {"message": "CF AutoBooks API up and running"}