# backend/app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from jose import jwt
from app.core.database import engine, get_db, Base
from app.routers.auth import router as auth_router
from app.models.user import User

# create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CF AutoBooks API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

# Protected admin route
@app.get("/admin/invoices")
def admin_invoices(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, __import__("app.core.config").core.config.settings.SECRET_KEY, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    if payload.get("plan") != "CARMICHAEL":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: admin only")
    # dummy response
    return [{"id": 1, "filename": "inv.pdf", "total": 123.45}]
