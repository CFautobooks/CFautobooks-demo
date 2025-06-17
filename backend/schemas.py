from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    email: str
    password: str
    plan: str

class Token(BaseModel):
    access_token: str
    token_type: str

class Invoice(BaseModel):
    id: int
    client_email: str
    amount: float
    created_at: str

    class Config:
        orm_mode = True
