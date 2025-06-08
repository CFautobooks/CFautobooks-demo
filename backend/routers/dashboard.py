from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from utils.security import decode_access_token
from schemas import InvoiceResponse
from models.user import User      # keep this for `get_current_user`
from models.invoice import Invoice  # we still need this to fetch from the DB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
        )
    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


@router.get("/", response_model=list[InvoiceResponse])
def read_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvoiceResponse]:
    # 1) Fetch the raw ORM Invoice objects
    orm_invoices = (
        db.query(Invoice)
        .filter(Invoice.owner_id == current_user.id)
        .all()
    )
    # 2) Convert each one into your Pydantic schema
    return [InvoiceResponse.from_orm(inv) for inv in orm_invoices]


@router.post("/upload")
def upload_invoice():
    # Placeholder: actual upload logic lives in the OCR microservice
    return {"message": "Upload endpoint placeholder"}
