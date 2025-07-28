"""
n8n 워크플로우 v2.0을 위한 개선된 돌봄 스키마
"""
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date

# 체크리스트 유형 관련 스키마
class ChecklistTypeResponse(BaseModel):
    id: int
    type_code: str
    type_name: str
    description: Optional[str] = None
    max_score: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# 개선된 체크리스트 응답 스키마
class EnhancedChecklistResponseItem(BaseModel):
    question_key: str
    question_text: str
    answer: Any
    selected_score: int  # 1-4점
    notes: Optional[str] = None
    
    @validator('selected_score')
    def validate_score(cls, v):
        if not 1 <= v <= 4:
            raise ValueError('점수는 1-4 사이여야 합니다.')
        return v

class TypedChecklistSubmission(BaseModel):
    session_id: int
    responses: Dict[str, Dict[str, EnhancedChecklistResponseItem]]  # {type_code: {sub_question_id: response}}
    
    @validator('responses')
    def validate_responses(cls, v):
        required_types = ['nutrition', 'hypertension', 'depression']
        for type_code in required_types:
            if type_code not in v:
                raise ValueError(f'{type_code} 유형의 응답이 필요합니다.')
        return v

# 주간 점수 관련 스키마
class WeeklyScoreCalculation(BaseModel):
    session_id: int
    senior_id: int
    week_date: date

class WeeklyChecklistScoreResponse(BaseModel):
    id: int
    senior_id: int
    checklist_type_code: str
    week_date: date
    total_score: int
    max_possible_score: int
    score_percentage: float
    status_code: Optional[int] = None  # 1:개선, 2:유지, 3:악화
    created_at: datetime
    
    class Config:
        from_attributes = True

# 돌봄노트 질문 관련 스키마
class CareNoteQuestionResponse(BaseModel):
    id: int
    question_number: int
    question_title: str
    question_text: str
    guide_text: Optional[str] = None
    examples: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True

class RandomQuestionResponse(BaseModel):
    question_id: int
    question_number: int
    question_title: str
    question_text: str
    guide_text: Optional[str] = None
    examples: Optional[str] = None

# 개선된 돌봄노트 스키마
class EnhancedCareNoteSubmission(BaseModel):
    session_id: int
    question_id: int
    question_number: int
    content: str
    
    @validator('content')
    def validate_content(cls, v):
        if len(v.strip()) < 10:
            raise ValueError('돌봄노트는 최소 10자 이상 작성해주세요.')
        return v.strip()

class EnhancedCareNoteResponse(BaseModel):
    id: int
    session_id: int
    selected_question_id: Optional[int] = None
    question_number: Optional[int] = None
    question_type: Optional[str] = None
    question_text: Optional[str] = None
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# 체크리스트 추이 분석 스키마
class ChecklistTrendData(BaseModel):
    senior_id: int
    checklist_type: Dict[str, Any]  # {code, name, max_score}
    recent_scores: List[WeeklyChecklistScoreResponse]
    weeks_available: int

class TrendAnalysisRequest(BaseModel):
    senior_id: int
    type_code: str

# n8n 워크플로우 트리거 스키마
class AIWorkflowTrigger(BaseModel):
    session_id: int
    senior_id: int
    trigger_time: Optional[datetime] = None

class WorkflowStatus(BaseModel):
    session_id: int
    completed_reports: int
    total_expected: int = 4  # 3개 유형별 + 1개 코멘트
    status: str  # pending, processing, completed, failed

# AI 리포트 유형별 스키마
class TypedAIReportResponse(BaseModel):
    id: int
    care_session_id: int
    report_type: str  # nutrition_report, hypertension_report, depression_report, care_note_comment
    checklist_type_code: Optional[str] = None
    content: str
    ai_comment: Optional[str] = None
    status_code: Optional[int] = None
    trend_analysis: Optional[str] = None
    keywords: Optional[List[str]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class MultipleReportsResponse(BaseModel):
    session_id: int
    senior_id: int
    reports: List[TypedAIReportResponse]
    processing_status: str
    
# 사용 통계 스키마
class CareStatistics(BaseModel):
    total_sessions: int
    completed_sessions: int
    pending_sessions: int
    average_checklist_score: float
    recent_trend: str  # improving, stable, declining