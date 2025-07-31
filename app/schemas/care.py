"""
돌봄 관련 스키마
"""
from pydantic import BaseModel, validator, Field
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
    location: Optional[str] = "요양원"  # 기본값 설정
    attendance_status: Optional[str] = "정상출근"  # 기본값 설정

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

# ✅ 추가: 질병별 체크리스트 제출을 위한 새로운 스키마
class DiseaseChecklistResponseItem(BaseModel):
    question_id: int
    scale_value: int  # 1-4 척도 값
    weight: Optional[float] = 1.0
    notes: Optional[str] = None

class DiseaseChecklistData(BaseModel):
    total_score: int  # 프론트에서 계산한 합계
    responses: List[DiseaseChecklistResponseItem]

class DiseaseChecklistSubmission(BaseModel):
    session_id: int
    senior_id: int
    disease_responses: Dict[str, DiseaseChecklistData]
    # 예시: {"nutrition": {...}, "hypertension": {...}}
    
    @validator('disease_responses')
    def validate_disease_responses(cls, v):
        if not v:
            raise ValueError('적어도 하나의 질병별 응답이 필요합니다.')
        
        # 유효한 질병 타입 확인
        valid_disease_types = ['nutrition', 'hypertension', 'depression', 'diabetes', 'dementia']
        for disease_type in v.keys():
            if disease_type not in valid_disease_types:
                raise ValueError(f'유효하지 않은 질병 타입: {disease_type}')
        
        return v
# === 기존 스키마에 추가 ===

# 체크리스트 관련 스키마 (새로운 점수 배열 방식)
class ChecklistRequest(BaseModel):
    """체크리스트 요청 스키마 (점수 배열 방식)"""
    session_id: int = Field(..., description="돌봄 세션 ID")
    checklist_scores: Dict[str, List[int]] = Field(
        ..., 
        description="카테고리별 점수 배열",
        example={
            "nutrition": [3, 4],
            "hypertension": [4, 4, 4, 4], 
            "depression": [3, 4, 4, 4]
        }
    )
    
    @validator('checklist_scores')
    def validate_scores(cls, v):
        """점수 배열 검증"""
        valid_categories = ['nutrition', 'hypertension', 'depression']
        
        for category, scores in v.items():
            # 유효한 카테고리 확인
            if category not in valid_categories:
                raise ValueError(f"'{category}'은 유효하지 않은 카테고리입니다. 사용 가능: {valid_categories}")
            
            # 점수 배열 확인
            if not isinstance(scores, list) or len(scores) == 0:
                raise ValueError(f"{category} 점수는 비어있지 않은 배열이어야 합니다")
            
            # 개별 점수 확인
            for i, score in enumerate(scores):
                if not isinstance(score, int) or score < 1 or score > 4:
                    raise ValueError(f"{category}[{i}] 점수는 1-4 사이의 정수여야 합니다 (현재: {score})")
        
        return v

class ChecklistSuccessResponse(BaseModel):
    """체크리스트 성공 응답 스키마"""
    status: str = "success"
    message: str
    session_id: int
    results: Dict[str, float] = Field(..., description="카테고리별 100% 환산 점수")
    processing_time: Optional[str] = None

class ChecklistStatusResponse(BaseModel):
    """체크리스트 상태 응답 스키마"""
    session_id: int
    checklist_completed: bool
    completion_time: Optional[datetime] = None
    category_scores: Dict[str, float] = {}
    message: str

# 돌봄노트 관련 스키마 (새로운 랜덤 질문 방식)
class CareNoteRequest(BaseModel):
    """돌봄노트 요청 스키마"""
    session_id: int = Field(..., description="돌봄 세션 ID")
    content: str = Field(
        ..., 
        min_length=20, 
        max_length=500,
        description="돌봄노트 내용 (20-500자)"
    )
    question_id: Optional[int] = Field(None, description="선택할 질문 ID (없으면 랜덤 선택)")
    
    @validator('content')
    def validate_content(cls, v):
        """내용 검증"""
        content = v.strip()
        if len(content) < 20:
            raise ValueError("돌봄노트는 20자 이상 작성해주세요")
        if len(content) > 500:
            raise ValueError("돌봄노트는 500자 이하로 작성해주세요")
        return content

class SelectedQuestionInfo(BaseModel):
    """선택된 질문 정보"""
    id: int
    question_number: int
    question_title: str
    question_text: str
    guide_text: Optional[str] = None

class CareNoteSuccessResponse(BaseModel):
    """돌봄노트 성공 응답 스키마"""
    status: str = "success"
    message: str
    session_id: int
    care_note_id: int
    selected_question: Optional[SelectedQuestionInfo] = None
    content_length: int

class RandomQuestionResponse(BaseModel):
    """랜덤 질문 응답 스키마"""
    id: int
    question_number: int
    question_title: str
    question_text: str
    guide_text: Optional[str] = None
    examples: Optional[str] = None

# 작업 상태 관련 스키마
class TaskStatusResponse(BaseModel):
    """작업 완료 상태 응답 스키마"""
    session_id: int
    checklist_completed: bool
    care_note_completed: bool
    can_checkout: bool
    missing_tasks: List[str] = []
    completion_summary: Dict[str, Optional[str]] = {}

# 퇴근 관련 스키마
class AttendanceCheckoutRequest(BaseModel):
    """퇴근 체크 요청 스키마"""
    location: str = Field(..., description="퇴근 위치")
    notes: Optional[str] = Field(None, description="퇴근 관련 메모")

class CheckoutSuccessResponse(BaseModel):
    """퇴근 성공 응답 스키마"""
    status: str = "success"
    message: str
    session_id: int
    checkout_time: datetime
    ai_analysis_triggered: bool = False
    n8n_response: Optional[dict] = None

# 에러 응답 스키마
class ErrorDetail(BaseModel):
    """에러 상세 정보"""
    error_code: str
    message: str
    suggestion: Optional[str] = None
    retry_after: Optional[str] = None

class ErrorResponse(BaseModel):
    """에러 응답 스키마"""
    success: bool = False
    detail: ErrorDetail
    timestamp: datetime
    path: str
