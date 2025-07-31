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
    DAILY_LIMIT_EXCEEDED = "CARE_005"
    SESSION_NOT_ACTIVE = "CARE_006"
    MODIFICATION_BLOCKED = "CARE_007"
    REQUIRED_TASKS_INCOMPLETE = "CARE_008"
    INVALID_SCORE_FORMAT = "CARE_009"
    CONTENT_LENGTH_ERROR = "CARE_010"
    QUESTION_NOT_FOUND = "CARE_011"
    N8N_TRIGGER_FAILED = "CARE_012"
    
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

# === 체크리스트 & 돌봄노트 전용 예외들 ===

class DailyLimitExceeded(StandardHTTPException):
    """하루 1회 제한 초과 예외"""
    def __init__(self, task_type: str = "작업"):
        super().__init__(
            status_code=400,
            detail=f"오늘 이미 {task_type}을 완료하셨습니다. 내일 다시 시도해주세요.",
            error_code=ErrorCodes.DAILY_LIMIT_EXCEEDED
        )

class SessionNotActive(StandardHTTPException):
    """비활성 세션 예외"""
    def __init__(self):
        super().__init__(
            status_code=400,
            detail="활성 돌봄 세션이 아닙니다. 출근 체크 후 이용해주세요.",
            error_code=ErrorCodes.SESSION_NOT_ACTIVE
        )

class SessionNotFound(StandardHTTPException):
    """세션 없음 예외"""
    def __init__(self):
        super().__init__(
            status_code=404,
            detail="돌봄 세션을 찾을 수 없습니다. 올바른 세션 ID를 확인해주세요.",
            error_code=ErrorCodes.CARE_SESSION_NOT_FOUND
        )

class ModificationBlocked(StandardHTTPException):
    """수정 차단 예외"""
    def __init__(self, task_type: str = "내용"):
        super().__init__(
            status_code=403,
            detail=f"{task_type}은 데이터 무결성 보장을 위해 수정할 수 없습니다.",
            error_code=ErrorCodes.MODIFICATION_BLOCKED
        )

class RequiredTasksIncomplete(StandardHTTPException):
    """필수 작업 미완료 예외"""
    def __init__(self, missing_tasks: list):
        missing_str = ', '.join(missing_tasks)
        super().__init__(
            status_code=400,
            detail=f"필수 작업을 완료해주세요: {missing_str}",
            error_code=ErrorCodes.REQUIRED_TASKS_INCOMPLETE
        )

class InvalidScoreFormat(StandardHTTPException):
    """잘못된 점수 형식 예외"""
    def __init__(self, message: str = "점수 형식이 올바르지 않습니다"):
        super().__init__(
            status_code=400,
            detail=f"{message}. 점수는 1-4 사이의 정수 배열이어야 합니다.",
            error_code=ErrorCodes.INVALID_SCORE_FORMAT
        )

class ContentLengthError(StandardHTTPException):
    """내용 길이 오류 예외"""
    def __init__(self, min_length: int = 20, max_length: int = 500):
        super().__init__(
            status_code=400,
            detail=f"내용은 {min_length}자 이상 {max_length}자 이하로 작성해주세요.",
            error_code=ErrorCodes.CONTENT_LENGTH_ERROR
        )

class QuestionNotFound(StandardHTTPException):
    """질문 없음 예외"""
    def __init__(self):
        super().__init__(
            status_code=404,
            detail="사용 가능한 질문이 없습니다. 관리자에게 문의하세요.",
            error_code=ErrorCodes.QUESTION_NOT_FOUND
        )

class N8nTriggerFailed(StandardHTTPException):
    """n8n 트리거 실패 예외"""
    def __init__(self):
        super().__init__(
            status_code=500,
            detail="AI 분석 시스템 연결에 실패했습니다. 퇴근은 정상 처리되었지만 AI 리포트 생성이 지연될 수 있습니다.",
            error_code=ErrorCodes.N8N_TRIGGER_FAILED
        )
