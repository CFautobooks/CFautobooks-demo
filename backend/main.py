from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import engine, Base
import models.user      # registers User
import models.invoice   # registers Invoice

# create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CF AutoBooks API")

# CORS – lock down origins later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include your routers
from routers.auth import router as auth_router
from routers.dashboard import router as dash_router
from routers.invoices import router as inv_router
from routers.admin import router as admin_router

app.include_router(auth_router)
app.include_router(dash_router)
app.include_router(inv_router)
app.include_router(admin_router)

@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}

