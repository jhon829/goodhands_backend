from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, Float, DECIMAL, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# 돌봄 세션 관련 모델 (MariaDB 최적화)
class CareSession(Base):
    __tablename__ = "care_sessions"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"), nullable=False)
    senior_id = Column(Integer, ForeignKey("seniors.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    status = Column(String(20), default="active")  # active, completed, cancelled
    start_location = Column(String(255))
    end_location = Column(String(255))
    start_photo = Column(String(255))
    end_photo = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    caregiver = relationship("Caregiver")
    senior = relationship("Senior")

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id"), nullable=False)
    type = Column(String(20), nullable=False)  # checkin, checkout
    location = Column(String(255))
    attendance_status = Column(String(100))  # 출석 상태 메시지
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    care_session = relationship("CareSession")

class ChecklistResponse(Base):
    __tablename__ = "checklist_responses"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id"), nullable=False)
    question_key = Column(String(100), nullable=False)  # nutrition_1, hypertension_1 등
    selected_score = Column(Integer, nullable=False)  # 1-4점
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    care_session = relationship("CareSession")

class CareNote(Base):
    __tablename__ = "care_notes"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id"), nullable=False)
    selected_question_id = Column(Integer, ForeignKey("care_note_questions.id"))
    question_number = Column(Integer)  # 질문 번호 (1-6)
    question_type = Column(String(50), nullable=False)
    question_text = Column(Text)
    content = Column(Text, nullable=False)
    is_final = Column(Boolean, default=True)  # 수정 방지용
    modification_blocked = Column(Boolean, default=True)  # 수정 방지용
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    care_session = relationship("CareSession")
    selected_question = relationship("CareNoteQuestion")


# ChecklistType은 checklist.py에서 정의됨


class WeeklyChecklistScore(Base):
    __tablename__ = "weekly_checklist_scores"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    senior_id = Column(Integer, ForeignKey("seniors.id"), nullable=False)
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"), nullable=False)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id"))
    checklist_type_code = Column(String(20))  # nutrition, hypertension, depression
    week_start_date = Column(Date, nullable=False)
    week_end_date = Column(Date, nullable=False)
    week_date = Column(Date)  # 돌봄 주차 날짜
    total_score = Column(Integer, nullable=False)
    max_possible_score = Column(Integer, nullable=False)
    score_percentage = Column(Integer, nullable=False)  # 100% 환산 점수
    status_code = Column(Integer)  # 1:개선, 2:유지, 3:악화
    checklist_count = Column(Integer, nullable=False)
    score_breakdown = Column(JSON)
    trend_indicator = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    senior = relationship("Senior")
    caregiver = relationship("Caregiver")


class CareNoteQuestion(Base):
    __tablename__ = "care_note_questions"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    question_number = Column(Integer, nullable=False)
    question_title = Column(String(100), nullable=False)
    question_text = Column(Text, nullable=False)
    guide_text = Column(Text)
    examples = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
