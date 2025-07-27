from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# 사용자 관련 모델 (MariaDB 최적화)
class User(Base):
    __tablename__ = "users"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_code = Column(String(10), unique=True, index=True, nullable=False)
    user_type = Column(String(20), nullable=False)  # caregiver, guardian, admin
    email = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계 설정
    caregiver_profile = relationship("Caregiver", back_populates="user", uselist=False)
    guardian_profile = relationship("Guardian", back_populates="user", uselist=False)
    admin_profile = relationship("Admin", back_populates="user", uselist=False)

class Caregiver(Base):
    __tablename__ = "caregivers"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(50), nullable=False)
    phone = Column(String(20))
    profile_image = Column(String(255))
    status = Column(String(20), default="active")  # active, inactive
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    user = relationship("User", back_populates="caregiver_profile")

class Guardian(Base):
    __tablename__ = "guardians"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(50), nullable=False)
    phone = Column(String(20))
    country = Column(String(50))
    relationship_type = Column(String(30))  # 자녀, 손자 등
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    user = relationship("User", back_populates="guardian_profile")

class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(50), nullable=False)
    permissions = Column(JSON)  # 권한 정보
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    user = relationship("User", back_populates="admin_profile")
