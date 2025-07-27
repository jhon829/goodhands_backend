from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# 시니어 관련 모델 (MariaDB 최적화)
class Senior(Base):
    __tablename__ = "seniors"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    age = Column(Integer)
    gender = Column(String(10))
    photo = Column(String(255))
    nursing_home_id = Column(Integer, ForeignKey("nursing_homes.id"))
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"))
    guardian_id = Column(Integer, ForeignKey("guardians.id"))
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    caregiver = relationship("Caregiver")
    guardian = relationship("Guardian")
    nursing_home = relationship("NursingHome")

class SeniorDisease(Base):
    __tablename__ = "senior_diseases"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    senior_id = Column(Integer, ForeignKey("seniors.id"), nullable=False)
    disease_type = Column(String(50), nullable=False)  # 치매, 당뇨, 고혈압 등
    severity = Column(String(20))  # 경증, 중등도, 중증
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    senior = relationship("Senior")

class NursingHome(Base):
    __tablename__ = "nursing_homes"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(255))
    phone = Column(String(20))
    contact_person = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
