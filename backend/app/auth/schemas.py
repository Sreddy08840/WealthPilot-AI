from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class UserBase(BaseModel):
    email: str
    first_name: str
    last_name: str
    role: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(UserBase):
    id: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    email: Optional[str] = None
