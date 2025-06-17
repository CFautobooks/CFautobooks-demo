from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from schemas import UserCreate, Token          # ← import from schemas.py at repo root
from core.database import get_db
from core.security import (
    verify_password,
    get_password_hash,
    create_access_token
)
from models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # check for existing user
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # create & persist new user
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        plan=user_in.plan
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # issue token
    access_token = create_access_token(data={"user_id": user.id, "plan": user.plan})
    return Token(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=Token)
def login(form_data: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.email).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    access_token = create_access_token(data={"user_id": user.id, "plan": user.plan})
    return Token(access_token=access_token, token_type="bearer")
