from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt
from core.config import settings
from schemas import Invoice
from sqlalchemy.orm import Session
from core.database import get_db
from models.invoice import Invoice as DBInvoice

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
admin_router = APIRouter()

@admin_router.get("/invoices", response_model=list[Invoice])
def get_all_invoices(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("plan") != "CARMICHAEL":
        raise HTTPException(status_code=403, detail="Unauthorized - must be a CARMICHAEL plan user")
    return db.query(DBInvoice).all()
