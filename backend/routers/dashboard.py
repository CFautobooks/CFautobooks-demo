from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from utils.security import decode_access_token
from models.user import User               # keeps your User ORM for auth
from schemas import InvoiceResponse        # <-- Pydantic schema only
from models.invoice import Invoice         # ORM model only for querying

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid authentication")
    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


@router.get("/", response_model=list[InvoiceResponse])
def read_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvoiceResponse]:
    @router.get("/", response_model=List[InvoiceResponse])
def read_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[InvoiceResponse]
    orm_invoices = (
        db.query(Invoice)
          .filter(Invoice.owner_id == current_user.id)
          .all()
    )
    return [InvoiceResponse.from_orm(inv) for inv in orm_invoices]


@router.post("/upload")
def upload_invoice():
    # Placeholder: actual OCR upload runs in a separate service
    return {"message": "Upload endpoint placeholder"}

