from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import timedelta
from core.database import get_db
from core.config import settings
from schemas import UserCreate, Token
import jwt
from models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
auth_router = APIRouter()

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

@auth_router.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = pwd_context.hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed, plan=user.plan)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    access_token = create_access_token({"sub": new_user.email, "plan": new_user.plan}, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.post("/login", response_model=Token)
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not pwd_context.verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": db_user.email, "plan": db_user.plan}, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}