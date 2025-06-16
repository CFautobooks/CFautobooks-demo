from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models.user    import Base as UserBase
from models.invoice import Base as InvoiceBase
from routers.auth   import router as auth_router

# Create all tables (must import both models before this)
UserBase.metadata.create_all(bind=engine)
InvoiceBase.metadata.create_all(bind=engine)

app = FastAPI(title="CF AutoBooks API")

# Open CORS for everything (you can lock it later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)  # mounts /auth/register and /auth/login

@app.get("/")
def root():
    return {"message": "CF AutoBooks API is running"}
