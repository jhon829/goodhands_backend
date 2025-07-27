"""
AI 리포트 및 피드백 관련 스키마
"""
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class AIReportBase(BaseModel):
    content: str
    ai_comment: Optional[str] = None

class AIReportCreate(AIReportBase):
    session_id: int
    keywords: List[str] = []

class AIReportResponse(AIReportBase):
    id: int
    session_id: int
    keywords: List[str] = []
    status: str = "generated"
    created_at: datetime
    
    class Config:
        from_attributes = True

class AIReportDetailResponse(AIReportResponse):
    session: Optional[dict] = None
    senior: Optional[dict] = None
    caregiver: Optional[dict] = None

class FeedbackBase(BaseModel):
    message: str
    requirements: Optional[str] = None

class FeedbackSubmission(FeedbackBase):
    report_id: int

class FeedbackResponse(FeedbackBase):
    id: int
    report_id: int
    guardian_id: int
    status: str = "pending"
    created_at: datetime
    
    class Config:
        from_attributes = True

class FeedbackDetailResponse(FeedbackResponse):
    report: Optional[AIReportResponse] = None
    guardian: Optional[dict] = None

class NotificationBase(BaseModel):
    title: str
    content: str
    type: str
    
    @validator('type')
    def validate_type(cls, v):
        allowed_types = ['report', 'feedback', 'announcement', 'system']
        if v not in allowed_types:
            raise ValueError(f'알림 유형은 {", ".join(allowed_types)} 중 하나여야 합니다.')
        return v

class NotificationCreate(NotificationBase):
    sender_id: int
    receiver_id: int
    data: Optional[Dict[str, Any]] = None

class NotificationResponse(NotificationBase):
    id: int
    sender_id: int
    receiver_id: int
    data: Optional[Dict[str, Any]] = None
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationDetailResponse(NotificationResponse):
    sender: Optional[dict] = None

class AIAnalysisResult(BaseModel):
    overall_health: str
    mood_state: str
    special_notes: List[str]
    recommendations: List[str]
    risk_factors: List[str]

class ChecklistAnalysisResponse(BaseModel):
    analysis: AIAnalysisResult
    session_id: int
    created_at: datetime

class TrendingKeyword(BaseModel):
    keyword: str
    count: int
    percentage: float

class TrendingKeywordsResponse(BaseModel):
    trending_keywords: List[TrendingKeyword]
    period_days: int
    total_reports: int
