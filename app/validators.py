"""
입력 검증 및 밸리데이션 강화
"""
from pydantic import BaseModel, validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time
import re

class CaregiverAttendanceRequest(BaseModel):
    """출근/퇴근 요청 검증"""
    senior_id: int = Field(..., gt=0, description="시니어 ID")
    location: str = Field(..., min_length=1, max_length=255, description="위치")
    gps_lat: float = Field(..., ge=-90, le=90, description="위도")
    gps_lng: float = Field(..., ge=-180, le=180, description="경도")
    notes: Optional[str] = Field(None, max_length=500, description="메모")
    
    @validator('location')
    def validate_location(cls, v):
        if not v.strip():
            raise ValueError('위치는 빈 값일 수 없습니다')
        return v.strip()

class ChecklistSubmissionRequest(BaseModel):
    """체크리스트 제출 요청 검증"""
    senior_id: int = Field(..., gt=0, description="시니어 ID")
    responses: List[Dict[str, Any]] = Field(..., min_items=1, description="응답 목록")
    
    @validator('responses')
    def validate_responses(cls, v):
        for response in v:
            if 'question_key' not in response:
                raise ValueError('question_key는 필수입니다')
            if 'answer' not in response:
                raise ValueError('answer는 필수입니다')
        return v

class CareNoteSubmissionRequest(BaseModel):
    """돌봄노트 제출 요청 검증"""
    senior_id: int = Field(..., gt=0, description="시니어 ID")
    notes: List[Dict[str, str]] = Field(..., min_items=1, max_items=10, description="돌봄노트")
    
    @validator('notes')
    def validate_notes(cls, v):
        for note in v:
            if 'question_type' not in note:
                raise ValueError('question_type은 필수입니다')
            if 'content' not in note:
                raise ValueError('content는 필수입니다')
            if len(note['content'].strip()) == 0:
                raise ValueError('내용은 빈 값일 수 없습니다')
            if len(note['content']) > 1000:
                raise ValueError('내용은 1000자를 초과할 수 없습니다')
        return v

class FeedbackSubmissionRequest(BaseModel):
    """피드백 제출 요청 검증"""
    ai_report_id: int = Field(..., gt=0, description="AI 리포트 ID")
    message: str = Field(..., min_length=1, max_length=2000, description="피드백 메시지")
    requirements: Optional[str] = Field(None, max_length=1000, description="요구사항")
    rating: Optional[int] = Field(None, ge=1, le=5, description="평점 (1-5)")
    
    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('피드백 메시지는 빈 값일 수 없습니다')
        return v.strip()

class CareScheduleRequest(BaseModel):
    """케어 스케줄 요청 검증"""
    senior_id: int = Field(..., gt=0, description="시니어 ID")
    day_of_week: int = Field(..., ge=0, le=6, description="요일 (0=일요일, 6=토요일)")
    start_time: str = Field(..., regex=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', description="시작 시간 (HH:MM)")
    end_time: str = Field(..., regex=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', description="종료 시간 (HH:MM)")
    notes: Optional[str] = Field(None, max_length=500, description="메모")
    
    @validator('end_time')
    def validate_time_order(cls, v, values):
        if 'start_time' in values:
            start = datetime.strptime(values['start_time'], '%H:%M').time()
            end = datetime.strptime(v, '%H:%M').time()
            if end <= start:
                raise ValueError('종료 시간은 시작 시간보다 늦어야 합니다')
        return v

class UserRegistrationRequest(BaseModel):
    """사용자 등록 요청 검증"""
    user_code: str = Field(..., min_length=3, max_length=10, description="사용자 코드")
    password: str = Field(..., min_length=8, max_length=50, description="비밀번호")
    user_type: str = Field(..., regex=r'^(caregiver|guardian|admin)$', description="사용자 유형")
    name: str = Field(..., min_length=1, max_length=50, description="이름")
    phone: Optional[str] = Field(None, regex=r'^01[0-9]-?[0-9]{4}-?[0-9]{4}$', description="전화번호")
    email: Optional[str] = Field(None, regex=r'^[^@]+@[^@]+\.[^@]+$', description="이메일")
    country: Optional[str] = Field(None, max_length=50, description="국가 (가디언용)")
    
    @validator('user_code')
    def validate_user_code(cls, v):
        if not re.match(r'^[A-Z]{2}[0-9]{3}$', v):
            raise ValueError('사용자 코드는 CG001, GD001 형식이어야 합니다')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('비밀번호는 최소 하나의 영문자를 포함해야 합니다')
        if not re.search(r'[0-9]', v):
            raise ValueError('비밀번호는 최소 하나의 숫자를 포함해야 합니다')
        return v

class PaginationRequest(BaseModel):
    """페이지네이션 요청 검증"""
    page: int = Field(1, ge=1, description="페이지 번호")
    size: int = Field(20, ge=1, le=100, description="페이지 크기")
    sort_by: Optional[str] = Field("created_at", description="정렬 기준")
    sort_order: str = Field("desc", regex=r'^(asc|desc)$', description="정렬 순서")

class DateRangeRequest(BaseModel):
    """날짜 범위 요청 검증"""
    start_date: date = Field(..., description="시작 날짜")
    end_date: date = Field(..., description="종료 날짜")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('종료 날짜는 시작 날짜보다 늦어야 합니다')
        return v

class FileUploadRequest(BaseModel):
    """파일 업로드 검증"""
    file_type: str = Field(..., regex=r'^(image|document)$', description="파일 타입")
    max_size_mb: int = Field(10, ge=1, le=50, description="최대 파일 크기 (MB)")
    
    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
        """파일 확장자 검증"""
        if not filename:
            return False
        ext = filename.lower().split('.')[-1]
        return f'.{ext}' in allowed_extensions
    
    @staticmethod
    def validate_file_size(file_size: int, max_size_mb: int) -> bool:
        """파일 크기 검증"""
        max_size_bytes = max_size_mb * 1024 * 1024
        return file_size <= max_size_bytes
