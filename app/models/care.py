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
    checklist_type_code = Column(String(20), ForeignKey("checklist_types.type_code"))  # 새 컬럼
    sub_question_id = Column(String(10))  # A,B,C,D 등 - 새 컬럼
    question_key = Column(String(100), nullable=False)
    question_text = Column(Text)
    answer = Column(JSON)  # Boolean, String, Number 등 다양한 답변 형식
    selected_score = Column(Integer)  # 선택한 점수 (1-4점) - 새 컬럼
    notes = Column(Text)
    score_value = Column(Integer)  # 점수화된 값
    category = Column(String(50))  # 카테고리 분류
    weight = Column(DECIMAL(3,2), default=1.0)  # 가중치
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    care_session = relationship("CareSession")
    checklist_type = relationship("ChecklistType")  # 새 관계

class CareNote(Base):
    __tablename__ = "care_notes"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id"), nullable=False)
    selected_question_id = Column(Integer, ForeignKey("care_note_questions.id"))  # 새 컬럼
    question_number = Column(Integer)  # 질문 번호 (1-6) - 새 컬럼
    question_type = Column(String(50))  # 기존 컬럼 (유지)
    question_text = Column(Text)  # 기존 컬럼 (유지)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    care_session = relationship("CareSession")
    care_note_question = relationship("CareNoteQuestion")  # 새 관계


# 새 모델들 추가
class ChecklistType(Base):
    __tablename__ = "checklist_types"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    type_code = Column(String(20), unique=True, nullable=False)
    type_name = Column(String(50), nullable=False)
    description = Column(Text)
    max_score = Column(Integer, default=16)
    created_at = Column(DateTime, server_default=func.now())


class WeeklyChecklistScore(Base):
    __tablename__ = "weekly_checklist_scores"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    senior_id = Column(Integer, ForeignKey("seniors.id"), nullable=False)
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"), nullable=False)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id"))  # 새로 추가된 컬럼
    checklist_type_code = Column(String(20))  # 새로 추가된 컬럼
    week_start_date = Column(Date, nullable=False)
    week_end_date = Column(Date, nullable=False)
    week_date = Column(Date)  # 새로 추가된 컬럼 (API에서 사용)
    total_score = Column(Integer, nullable=False)
    max_possible_score = Column(Integer, nullable=False)
    score_percentage = Column(DECIMAL(5,2), nullable=False)
    status_code = Column(Integer)  # 새로 추가된 컬럼 (1:개선, 2:유지, 3:악화)
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
