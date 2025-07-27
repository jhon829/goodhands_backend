from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# AI 리포트 관련 모델 (MariaDB 최적화)
class AIReport(Base):
    __tablename__ = "ai_reports"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id"), nullable=False)
    keywords = Column(JSON)  # 키워드 리스트
    content = Column(Text, nullable=False)  # 리포트 본문
    ai_comment = Column(Text)  # AI 코멘트
    status = Column(String(20), default="generated")  # generated, read, reviewed
    
    # 새로 추가된 컬럼들
    checklist_score_total = Column(Integer)
    checklist_score_percentage = Column(DECIMAL(5,2))
    trend_comparison = Column(JSON)
    special_notes_summary = Column(Text)
    n8n_workflow_id = Column(String(100))
    ai_processing_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    care_session = relationship("CareSession")

class Feedback(Base):
    __tablename__ = "feedbacks"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    ai_report_id = Column(Integer, ForeignKey("ai_reports.id"), nullable=False)
    guardian_id = Column(Integer, ForeignKey("guardians.id"), nullable=False)
    message = Column(Text, nullable=False)
    requirements = Column(Text)  # 특별 요구사항
    status = Column(String(20), default="pending")  # pending, reviewed, implemented
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계 설정
    ai_report = relationship("AIReport")
    guardian = relationship("Guardian")

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)  # report, feedback, announcement
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    data = Column(JSON)  # 추가 데이터
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
