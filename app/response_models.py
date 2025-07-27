"""
표준화된 API 응답 모델
"""
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List, Any
from datetime import datetime

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    """표준 API 응답 모델"""
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    timestamp: datetime = datetime.now()

class PaginatedResponse(BaseModel, Generic[T]):
    """페이지네이션 응답 모델"""
    success: bool = True
    items: List[T]
    total: int
    page: int
    size: int
    has_next: bool
    has_previous: bool
    total_pages: int
    timestamp: datetime = datetime.now()

class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    success: bool = False
    detail: str
    error_code: str
    timestamp: datetime = datetime.now()
    path: Optional[str] = None

# 공통 응답 생성 함수들
def success_response(data: T = None, message: str = None) -> APIResponse[T]:
    """성공 응답 생성"""
    return APIResponse(
        success=True,
        data=data,
        message=message,
        timestamp=datetime.now()
    )

def paginated_response(
    items: List[T],
    total: int,
    page: int,
    size: int
) -> PaginatedResponse[T]:
    """페이지네이션 응답 생성"""
    total_pages = (total + size - 1) // size
    
    return PaginatedResponse(
        success=True,
        items=items,
        total=total,
        page=page,
        size=size,
        has_next=page < total_pages,
        has_previous=page > 1,
        total_pages=total_pages,
        timestamp=datetime.now()
    )

def error_response(
    detail: str,
    error_code: str,
    path: str = None
) -> ErrorResponse:
    """에러 응답 생성"""
    return ErrorResponse(
        success=False,
        detail=detail,
        error_code=error_code,
        timestamp=datetime.now(),
        path=path
    )

# 특화된 응답 모델들
class LoginResponse(BaseModel):
    """로그인 응답 모델"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 초 단위
    user_type: str
    user_info: dict

class FileUploadResponse(BaseModel):
    """파일 업로드 응답 모델"""
    filename: str
    file_url: str
    file_size: int
    content_type: str
    upload_timestamp: datetime

class AnalysisResponse(BaseModel):
    """분석 결과 응답 모델"""
    analysis_id: str
    status: str  # 'completed', 'processing', 'failed'
    result: Optional[dict] = None
    progress: Optional[int] = None  # 0-100%
    estimated_completion: Optional[datetime] = None
