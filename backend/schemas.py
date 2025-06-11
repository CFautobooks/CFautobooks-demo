# backend/schemas.py

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ─── User Schemas ──────────────────────────────────────────────────────────────
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    plan: str    # "DIY", "WHITE_LABEL", or "CARMICHAEL"

class UserResponse(UserBase):
    id: int
    plan: str

    class Config:
        orm_mode = True

# Token returned on login
class Token(BaseModel):
    access_token: str
    token_type: str

# ─── Invoice Schemas ────────────────────────────────────────────────────────────
class InvoiceResponse(BaseModel):
    id: int
    filename: str
    status: str
    total_amount: Optional[float]
    created_at: datetime

    class Config:
        orm_mode = True

# For the admin list view
class InvoiceAdmin(BaseModel):
    id: int
    owner_id: int
    total_amount: Optional[float] = None
    created_at: datetime

    class Config:
        orm_mode = True
