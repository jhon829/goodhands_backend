"""
표준화된 에러 응답 시스템
"""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from datetime import datetime
import traceback

class StandardHTTPException(HTTPException):
    """표준화된 HTTP 예외"""
    
    def __init__(
        self, 
        status_code: int, 
        detail: str = None, 
        error_code: str = None,
        headers: dict = None
    ):
        super().__init__(status_code, detail, headers)
        self.error_code = error_code or f"HTTP_{status_code}"

# 에러 코드 정의
class ErrorCodes:
    # 인증 관련
    INVALID_CREDENTIALS = "AUTH_001"
    TOKEN_EXPIRED = "AUTH_002"
    INSUFFICIENT_PERMISSIONS = "AUTH_003"
    
    # 사용자 관련
    USER_NOT_FOUND = "USER_001"
    USER_ALREADY_EXISTS = "USER_002"
    INVALID_USER_TYPE = "USER_003"
    
    # 케어 관련
    SENIOR_NOT_FOUND = "CARE_001"
    CARE_SESSION_NOT_FOUND = "CARE_002"
    INVALID_CHECKLIST_DATA = "CARE_003"
    CARE_SCHEDULE_CONFLICT = "CARE_004"
    
    # 파일 관련
    FILE_TOO_LARGE = "FILE_001"
    INVALID_FILE_TYPE = "FILE_002"
    FILE_UPLOAD_FAILED = "FILE_003"
    
    # AI 관련
    AI_ANALYSIS_FAILED = "AI_001"
    INSUFFICIENT_DATA = "AI_002"
    
    # 데이터베이스 관련
    DATABASE_ERROR = "DB_001"
    CONSTRAINT_VIOLATION = "DB_002"

async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 핸들러"""
    
    error_code = getattr(exc, 'error_code', f"HTTP_{exc.status_code}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "detail": exc.detail,
            "error_code": error_code,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path)
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "detail": "내부 서버 오류가 발생했습니다",
            "error_code": "INTERNAL_SERVER_ERROR",
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url.path),
            # 개발 환경에서만 스택 트레이스 포함
            **({"traceback": traceback.format_exc()} if request.app.debug else {})
        }
    )

# 공통 예외 함수들
def raise_not_found(message: str, error_code: str = None):
    """404 Not Found 예외 발생"""
    raise StandardHTTPException(
        status_code=404,
        detail=message,
        error_code=error_code or ErrorCodes.USER_NOT_FOUND
    )

def raise_bad_request(message: str, error_code: str = None):
    """400 Bad Request 예외 발생"""
    raise StandardHTTPException(
        status_code=400,
        detail=message,
        error_code=error_code or "BAD_REQUEST"
    )

def raise_unauthorized(message: str = "인증이 필요합니다"):
    """401 Unauthorized 예외 발생"""
    raise StandardHTTPException(
        status_code=401,
        detail=message,
        error_code=ErrorCodes.INVALID_CREDENTIALS
    )

def raise_forbidden(message: str = "권한이 부족합니다"):
    """403 Forbidden 예외 발생"""
    raise StandardHTTPException(
        status_code=403,
        detail=message,
        error_code=ErrorCodes.INSUFFICIENT_PERMISSIONS
    )
