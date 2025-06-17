# backend/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db                # ← fixed import
from core.security import verify_password, create_access_token
from core.schemas import UserCreate, Token       # adjust these to your actual Pydantic models
from models.user import User                     # your SQLAlchemy User model

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserCreate)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # hash & store new user, omitted here…
    hashed = get_password_hash(user_in.password)
    user = User(email=user_in.email, hashed_password=hashed, plan=user_in.plan)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(form_data: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.email).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.email, "plan": user.plan}
    )
    return {"access_token": access_token, "token_type": "bearer"}

