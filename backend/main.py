from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models.user import Base as UserBase
from models.invoice import Base as InvoiceBase
from routers.auth import router as auth_router
from routers.dashboard import router as dashboard_router
from routers.invoices import router as invoices_router
from routers.admin import router as admin_router

# create all tables
UserBase.metadata.create_all(bind=engine)
InvoiceBase.metadata.create_all(bind=engine)

app = FastAPI(title="CF AutoBooks API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://cfautobooks-demo.onrender.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(invoices_router)
app.include_router(admin_router)

@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}
