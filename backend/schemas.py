from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class Invoice(BaseModel):
    id: int
    total: float
    created_at: str

    class Config:
        orm_mode = True
