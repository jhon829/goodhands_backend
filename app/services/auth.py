from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.models import User
from app.database import get_db

# 암호화 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """비밀번호 해싱"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def authenticate_user(db: Session, user_code: str, password: str):
    """사용자 인증"""
    user = db.query(User).filter(User.user_code == user_code).first()
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """현재 사용자 정보 조회"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
        user_code: str = payload.get("sub")
        if user_code is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.user_code == user_code).first()
    if user is None:
        raise credentials_exception
    
    return user

def get_current_caregiver(current_user: User = Depends(get_current_user)):
    """현재 케어기버 정보 조회"""
    if current_user.user_type != "caregiver":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a caregiver"
        )
    return current_user

def get_current_guardian(current_user: User = Depends(get_current_user)):
    """현재 가디언 정보 조회"""
    if current_user.user_type != "guardian":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a guardian"
        )
    return current_user

def get_current_admin(current_user: User = Depends(get_current_user)):
    """현재 관리자 정보 조회"""
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not an admin"
        )
    return current_user
