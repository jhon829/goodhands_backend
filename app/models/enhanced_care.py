"""
AI 리포트 시스템 개선을 위한 추가 모델들
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, Float, Date, Time, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# 정기 케어 스케줄 모델
class CareSchedule(Base):
    __tablename__ = "care_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"), nullable=False)
    senior_id = Column(Integer, ForeignKey("seniors.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=일요일, 1=월요일, ..., 6=토요일
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계 설정
    caregiver = relationship("Caregiver")
    senior = relationship("Senior")

# 주간 체크리스트 점수 집계 모델
class WeeklyChecklistScore(Base):
    __tablename__ = "weekly_checklist_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    senior_id = Column(Integer, ForeignKey("seniors.id"), nullable=False)
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"), nullable=False)
    week_start_date = Column(Date, nullable=False)
    week_end_date = Column(Date, nullable=False)
    total_score = Column(Integer, nullable=False)
    max_possible_score = Column(Integer, nullable=False)
    score_percentage = Column(DECIMAL(5,2), nullable=False)
    checklist_count = Column(Integer, nullable=False)
    score_breakdown = Column(JSON)  # 카테고리별 점수
    trend_indicator = Column(String(20))  # 'improving', 'stable', 'declining'
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    senior = relationship("Senior")
    caregiver = relationship("Caregiver")

# 상태 변화 추이 분석 모델
class HealthTrendAnalysis(Base):
    __tablename__ = "health_trend_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    senior_id = Column(Integer, ForeignKey("seniors.id"), nullable=False)
    analysis_date = Column(Date, nullable=False)
    period_weeks = Column(Integer, default=4)
    trend_summary = Column(JSON)
    key_indicators = Column(JSON)
    ai_insights = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계 설정
    senior = relationship("Senior")

# 특이사항 관리 모델
class SpecialNote(Base):
    __tablename__ = "special_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    senior_id = Column(Integer, ForeignKey("seniors.id"), nullable=False)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id"))
    feedback_id = Column(Integer, ForeignKey("feedbacks.id"))
    note_type = Column(String(50), nullable=False)
    short_summary = Column(String(200), nullable=False)
    detailed_content = Column(Text)
    priority_level = Column(Integer, default=1)  # 1=낮음, 2=보통, 3=높음, 4=긴급
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime)
    
    # 관계 설정
    senior = relationship("Senior")
    care_session = relationship("CareSession")
    feedback = relationship("Feedback")
