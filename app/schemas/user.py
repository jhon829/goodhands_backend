from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# 사용자 인증 관련 스키마
class UserLogin(BaseModel):
    user_code: str
    password: str

class UserCreate(BaseModel):
    user_code: str
    user_type: str
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None
    country: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    user_code: str
    user_type: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user_type: str

class TokenData(BaseModel):
    user_code: Optional[str] = None

# 케어기버 관련 스키마
class CaregiverCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    
class CaregiverResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# 가디언 관련 스키마
class GuardianCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    country: Optional[str] = None
    relationship: Optional[str] = None

class GuardianResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    country: Optional[str] = None
    relationship: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
