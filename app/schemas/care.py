"""
돌봄 관련 스키마
"""
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class CareSessionBase(BaseModel):
    senior_id: int
    status: str = "active"
    
    @validator('status')
    def validate_status(cls, v):
        if v not in ['active', 'completed', 'cancelled']:
            raise ValueError('상태는 active, completed, cancelled 중 하나여야 합니다.')
        return v

class CareSessionCreate(CareSessionBase):
    pass

class CareSessionUpdate(BaseModel):
    status: Optional[str] = None
    end_time: Optional[datetime] = None

class CareSessionResponse(CareSessionBase):
    id: int
    caregiver_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class AttendanceCheckIn(BaseModel):
    senior_id: int
    location: str
    attendance_status: str

class AttendanceCheckOut(BaseModel):
    session_id: int
    location: str
    attendance_status: str

class AttendanceLogResponse(BaseModel):
    id: int
    care_session_id: int
    type: str
    location: Optional[str] = None
    attendance_status: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChecklistResponseItem(BaseModel):
    question_key: str
    question_text: str
    answer: Any  # Boolean, String, Number 등
    notes: Optional[str] = None

class ChecklistSubmission(BaseModel):
    session_id: int
    responses: List[ChecklistResponseItem]
    
    @validator('responses')
    def validate_responses(cls, v):
        if not v:
            raise ValueError('적어도 하나의 응답이 필요합니다.')
        return v

class ChecklistResponseQuery(BaseModel):
    id: int
    session_id: int
    question_key: str
    question_text: str
    answer: Any
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class CareNoteItem(BaseModel):
    question_type: str
    question_text: str
    content: str
    
    @validator('question_type')
    def validate_question_type(cls, v):
        allowed_types = [
            'special_moments', 'family_longing', 'emotional_state',
            'conversation', 'changes', 'care_episodes'
        ]
        if v not in allowed_types:
            raise ValueError(f'질문 유형은 {", ".join(allowed_types)} 중 하나여야 합니다.')
        return v

class CareNoteSubmission(BaseModel):
    session_id: int
    notes: List[CareNoteItem]
    
    @validator('notes')
    def validate_notes(cls, v):
        if not v:
            raise ValueError('적어도 하나의 노트가 필요합니다.')
        return v

class CareNoteResponse(BaseModel):
    id: int
    session_id: int
    question_type: str
    question_text: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class CareHistoryResponse(BaseModel):
    care_sessions: List[CareSessionResponse]
    total_count: int
