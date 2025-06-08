from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    plan: str  # "DIY", "WHITE_LABEL", "CARMICHAEL"

class UserResponse(UserBase):
    id: int
    plan: str

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class InvoiceBase(BaseModel):
    filename: str

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceResponse(InvoiceBase):
    id: int
    status: str
    total_amount: Optional[float]
    created_at: datetime

    class Config:
        orm_mode = True