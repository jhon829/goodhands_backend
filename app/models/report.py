from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# AI 리포트 관련 모델 (실제 DB 스키마와 일치)
class AIReport(Base):
    __tablename__ = "ai_reports"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id"), nullable=False)
    senior_id = Column(Integer, ForeignKey("seniors.id"))  # 시니어 ID
    report_type = Column(String(30))  # nutrition_report, hypertension_report, depression_report, care_note_comment
    checklist_type_code = Column(String(20))  # 체크리스트 타입 코드
    content = Column(Text, nullable=False)  # 리포트 본문
    ai_comment = Column(Text)  # AI 코멘트
    status_code = Column(Integer)  # 1:개선, 2:유지, 3:악화
    trend_analysis = Column(Text)  # 3주차 추이 분석 내용
    status = Column(String(20), default="generated")  # generated, read, reviewed
    
    # 실제 DB에 있는 컬럼들
    checklist_score_total = Column(Integer)  # 체크리스트 총점
    checklist_score_percentage = Column(DECIMAL(5,2))  # 체크리스트 백분율
    special_notes_summary = Column(Text)  # 특이사항 요약
    n8n_workflow_id = Column(String(50))  # n8n 워크플로우 ID
    ai_processing_status = Column(String(20), default="pending")  # AI 처리 상태
    
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    care_session = relationship("CareSession")
    senior = relationship("Senior")

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
