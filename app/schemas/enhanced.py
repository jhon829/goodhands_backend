"""
AI 리포트 시스템 개선을 위한 추가 스키마들
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date, time
from decimal import Decimal

# 케어 스케줄 관련 스키마
class CareScheduleBase(BaseModel):
    senior_id: int
    day_of_week: int  # 0=일요일, 1=월요일, ..., 6=토요일
    start_time: time
    end_time: time
    notes: Optional[str] = None

class CareScheduleCreate(CareScheduleBase):
    pass

class CareScheduleResponse(CareScheduleBase):
    id: int
    caregiver_id: int
    is_active: bool
    day_name: str
    next_care_date: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# 주간 점수 관련 스키마
class WeeklyScoreBase(BaseModel):
    senior_id: int
    week_start_date: date
    week_end_date: date
    total_score: int
    max_possible_score: int
    score_percentage: Decimal
    checklist_count: int
    score_breakdown: Optional[Dict[str, Any]] = None
    trend_indicator: Optional[str] = "stable"

class WeeklyScoreResponse(WeeklyScoreBase):
    id: int
    caregiver_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# 추이 분석 관련 스키마
class TrendAnalysisBase(BaseModel):
    senior_id: int
    analysis_date: date
    period_weeks: int = 4
    trend_summary: Optional[Dict[str, Any]] = None
    key_indicators: Optional[Dict[str, Any]] = None
    ai_insights: Optional[str] = None

class TrendAnalysisResponse(TrendAnalysisBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TrendAnalysisResult(BaseModel):
    trend: str  # 'improving', 'stable', 'declining'
    trend_strength: float
    average_score: float
    score_change: float
    weekly_data: List[Dict[str, Any]]
    category_analysis: Optional[Dict[str, Any]] = None
    alerts: List[Dict[str, Any]] = []
    recommendations: List[str] = []

# 특이사항 관련 스키마
class SpecialNoteBase(BaseModel):
    senior_id: int
    note_type: str
    short_summary: str
    detailed_content: Optional[str] = None
    priority_level: int = 1  # 1=낮음, 2=보통, 3=높음, 4=긴급

class SpecialNoteCreate(SpecialNoteBase):
    care_session_id: Optional[int] = None
    feedback_id: Optional[int] = None

class SpecialNoteResponse(SpecialNoteBase):
    id: int
    care_session_id: Optional[int] = None
    feedback_id: Optional[int] = None
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# AI 분석 트리거 관련 스키마
class AIAnalysisRequest(BaseModel):
    care_session_id: int

class AIAnalysisResponse(BaseModel):
    success: bool
    message: str
    report_id: int
    ai_result: Optional[Dict[str, Any]] = None

# 확장된 AI 리포트 스키마
class AIReportEnhanced(BaseModel):
    id: int
    care_session_id: int
    keywords: Optional[List[str]] = []
    content: str
    ai_comment: Optional[str] = None
    status: str = "generated"
    
    # 새로 추가된 필드들
    checklist_score_total: Optional[int] = None
    checklist_score_percentage: Optional[Decimal] = None
    trend_comparison: Optional[Dict[str, Any]] = None
    special_notes_summary: Optional[str] = None
    ai_processing_status: str = "pending"
    
    created_at: datetime
    
    class Config:
        from_attributes = True

# 확장된 체크리스트 응답 스키마
class ChecklistResponseEnhanced(BaseModel):
    id: int
    care_session_id: int
    question_key: str
    question_text: Optional[str] = None
    answer: Any
    notes: Optional[str] = None
    
    # 새로 추가된 필드들
    score_value: Optional[int] = None
    category: Optional[str] = None
    weight: Optional[Decimal] = Decimal('1.0')
    
    created_at: datetime
    
    class Config:
        from_attributes = True

# 홈 화면 개선 스키마
class CaregiverHomeEnhanced(BaseModel):
    caregiver_name: str
    today_sessions: List[Any]
    seniors: List[Any]
    notifications: List[Any]
    
    # 새로 추가된 정보들
    weekly_summary: Optional[Dict[str, Any]] = None
    upcoming_schedules: List[CareScheduleResponse] = []
    recent_alerts: List[SpecialNoteResponse] = []

class GuardianHomeEnhanced(BaseModel):
    guardian_name: str
    seniors: List[Any]
    recent_reports: List[AIReportEnhanced]
    unread_notifications: List[Any]
    
    # 새로 추가된 정보들
    trend_summaries: Dict[int, TrendAnalysisResult] = {}  # senior_id -> trend_analysis
    special_notes: List[SpecialNoteResponse] = []
