"""
현재 배포된 DB v1.4.0 구조에 맞춘 모델 수정
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, Float, DECIMAL, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# 기존 DB 구조에 맞춘 모델들

class ChecklistCategory(Base):
    """기존 checklist_categories 테이블"""
    __tablename__ = "checklist_categories"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    category_code = Column(String(50), unique=True, nullable=False)
    category_name = Column(String(100), nullable=False)
    description = Column(Text)
    icon_name = Column(String(50))
    display_order = Column(Integer)
    is_common = Column(Boolean, default=True)
    max_score = Column(Integer, default=16)
    created_at = Column(DateTime, server_default=func.now())

class ChecklistQuestion(Base):
    """기존 checklist_questions 테이블"""
    __tablename__ = "checklist_questions"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("checklist_categories.id"), nullable=False)
    question_code = Column(String(50), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), default='scale4')
    is_required = Column(Boolean, default=True)
    display_order = Column(Integer)
    target_diseases = Column(JSON)
    scale_labels = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    category = relationship("ChecklistCategory")

class ChecklistResponse(Base):
    """기존 checklist_responses 테이블 (수정됨)"""
    __tablename__ = "checklist_responses"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id"), nullable=False)
    question_key = Column(String(100), nullable=False)
    question_text = Column(Text)
    answer = Column(JSON)
    notes = Column(Text)
    score_value = Column(Integer)
    category = Column(String(50))
    weight = Column(DECIMAL(3,2), default=1.0)
    created_at = Column(DateTime, server_default=func.now())
    
    # 새 컬럼들
    category_id = Column(Integer, ForeignKey("checklist_categories.id"))
    question_id = Column(Integer, ForeignKey("checklist_questions.id"))
    scale_value = Column(Integer)
    max_scale_value = Column(Integer, default=4)
    weighted_score = Column(DECIMAL(5,2))
    category_code = Column(String(50))
    ui_category_mapping = Column(String(50))
    
    # 관계 설정
    care_session = relationship("CareSession")
    category_obj = relationship("ChecklistCategory")
    question_obj = relationship("ChecklistQuestion")

class WeeklyCategoryScore(Base):
    """기존 weekly_category_scores 테이블"""
    __tablename__ = "weekly_category_scores"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    senior_id = Column(Integer, ForeignKey("seniors.id"), nullable=False)
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("checklist_categories.id"), nullable=False)
    week_start_date = Column(Date, nullable=False)
    week_end_date = Column(Date, nullable=False)
    total_score = Column(DECIMAL(8,2), nullable=False)
    max_possible_score = Column(DECIMAL(8,2), nullable=False)
    score_percentage = Column(DECIMAL(5,2), nullable=False)
    question_count = Column(Integer, nullable=False)
    completed_questions = Column(Integer, nullable=False)
    previous_week_score = Column(DECIMAL(5,2))
    score_change = Column(DECIMAL(5,2))
    trend_direction = Column(String(20))  # improving, stable, declining
    risk_level = Column(String(20))  # normal, caution, warning, danger
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계 설정
    senior = relationship("Senior")
    caregiver = relationship("Caregiver")
    category = relationship("ChecklistCategory")

class CareNote(Base):
    """기존 care_notes 테이블 (수정됨)"""
    __tablename__ = "care_notes"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id"), nullable=False)
    
    # 새로 추가된 컬럼들
    selected_question_id = Column(Integer, ForeignKey("care_note_questions.id"))
    question_number = Column(Integer)
    
    # 기존 컬럼들
    question_type = Column(String(50), nullable=False)
    question_text = Column(Text)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    care_session = relationship("CareSession")
    care_note_question = relationship("CareNoteQuestion")

class CareNoteQuestion(Base):
    """새로 추가되는 테이블"""
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

class AIReport(Base):
    """기존 ai_reports 테이블 (수정됨)"""
    __tablename__ = "ai_reports"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id"), nullable=False)
    
    # 새로 추가된 컬럼들
    report_type = Column(String(30))  # nutrition_report, hypertension_report, depression_report, care_note_comment
    checklist_type_code = Column(String(20))
    status_code = Column(Integer)  # 1:개선, 2:유지, 3:악화
    trend_analysis = Column(Text)  # 3주차 추이 분석 내용
    
    # 기존 컬럼들
    keywords = Column(JSON)
    content = Column(Text, nullable=False)
    ai_comment = Column(Text)
    status = Column(String(20), default=None)
    checklist_score_total = Column(Integer)
    checklist_score_percentage = Column(DECIMAL(5,2))
    trend_comparison = Column(JSON)
    special_notes_summary = Column(Text)
    n8n_workflow_id = Column(String(100))
    ai_processing_status = Column(String(20), default=None)
    created_at = Column(DateTime, server_default=func.now())
    senior_id = Column(Integer, ForeignKey("seniors.id"))
    category_details = Column(Text)
    ui_components = Column(Text)
    ui_enhancements = Column(Text)
    
    # 관계 설정
    care_session = relationship("CareSession")
    senior = relationship("Senior")

# 기존 CategoryTrendAnalysis 클래스도 그대로 활용
class CategoryTrendAnalysis(Base):
    """기존 category_trend_analysis 테이블"""
    __tablename__ = "category_trend_analysis"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    senior_id = Column(Integer, ForeignKey("seniors.id"), nullable=False)
    category_code = Column(String(50), nullable=False)
    analysis_date = Column(Date, nullable=False)
    current_score = Column(DECIMAL(5,2), nullable=False)
    previous_score = Column(DECIMAL(5,2))
    change_amount = Column(DECIMAL(5,2))
    change_direction = Column(String(20))  # up, stable, down
    status_level = Column(String(20))  # good, caution, warning
    avatar_emotion = Column(String(20))  # happy, worried, dizzy
    avatar_color = Column(String(20))  # blue, green, red
    status_message = Column(Text)
    trend_data = Column(Text)  # JSON
    ai_recommendation = Column(Text)
    family_action = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 관계 설정
    senior = relationship("Senior")
