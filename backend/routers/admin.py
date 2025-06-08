from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from utils.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer
from models.user import User
from models.invoice import Invoice
from typing import List

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

router = APIRouter(prefix="/admin", tags=["admin"])

def get_admin_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication")
    user = db.query(User).filter(User.email == payload["sub"]).first()
    # Placeholder: treat plan "CARMICHAEL" as admin; adjust as needed
    if not user or user.plan != "CARMICHAEL":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return user

@router.get("/invoices", response_model=List[Invoice])
def list_all_invoices(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    invoices = db.query(Invoice).all()
    return invoices