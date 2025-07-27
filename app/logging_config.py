"""
구조화된 로깅 시스템
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import time

class StructuredFormatter(logging.Formatter):
    """구조화된 로그 포맷터"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 추가 컨텍스트 정보 포함
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'execution_time'):
            log_data['execution_time'] = record.execution_time
        if hasattr(record, 'extra_data'):
            log_data['extra_data'] = record.extra_data
            
        return json.dumps(log_data, ensure_ascii=False)

def setup_logging():
    """로깅 설정"""
    
    # 루트 로거 설정
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 핸들러 생성
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler('app.log', encoding='utf-8')
    
    # 포맷터 설정
    structured_formatter = StructuredFormatter()
    console_handler.setFormatter(structured_formatter)
    file_handler.setFormatter(structured_formatter)
    
    # 핸들러 추가
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 반환"""
    return logging.getLogger(name)

def log_api_call(func):
    """API 호출 로깅 데코레이터"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger = get_logger(f"api.{func.__module__}.{func.__name__}")
        start_time = time.time()
        
        try:
            # 요청 정보 로깅
            logger.info(
                f"API 호출 시작: {func.__name__}",
                extra={
                    'extra_data': {
                        'function': func.__name__,
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    }
                }
            )
            
            # 함수 실행
            result = await func(*args, **kwargs)
            
            # 실행 시간 계산
            execution_time = time.time() - start_time
            
            # 성공 로깅
            logger.info(
                f"API 호출 완료: {func.__name__}",
                extra={
                    'execution_time': execution_time,
                    'extra_data': {
                        'function': func.__name__,
                        'success': True
                    }
                }
            )
            
            return result
            
        except Exception as e:
            # 에러 로깅
            execution_time = time.time() - start_time
            logger.error(
                f"API 호출 실패: {func.__name__} - {str(e)}",
                extra={
                    'execution_time': execution_time,
                    'extra_data': {
                        'function': func.__name__,
                        'error': str(e),
                        'error_type': type(e).__name__
                    }
                }
            )
            raise
            
    return wrapper

def log_database_operation(operation: str, table: str, record_id: Optional[int] = None):
    """데이터베이스 작업 로깅"""
    logger = get_logger("database")
    logger.info(
        f"DB 작업: {operation}",
        extra={
            'extra_data': {
                'operation': operation,
                'table': table,
                'record_id': record_id
            }
        }
    )

def log_user_action(user_id: int, action: str, details: Dict[str, Any] = None):
    """사용자 액션 로깅"""
    logger = get_logger("user_action")
    logger.info(
        f"사용자 액션: {action}",
        extra={
            'user_id': user_id,
            'extra_data': {
                'action': action,
                'details': details or {}
            }
        }
    )

def log_ai_analysis(senior_id: int, analysis_type: str, result: Dict[str, Any]):
    """AI 분석 로깅"""
    logger = get_logger("ai_analysis")
    logger.info(
        f"AI 분석 완료: {analysis_type}",
        extra={
            'extra_data': {
                'senior_id': senior_id,
                'analysis_type': analysis_type,
                'result_summary': {
                    'keywords_count': len(result.get('keywords', [])),
                    'score': result.get('score_percentage'),
                    'trend': result.get('trend_analysis', {}).get('trend')
                }
            }
        }
    )

def log_file_operation(operation: str, filename: str, file_size: int = None, user_id: int = None):
    """파일 작업 로깅"""
    logger = get_logger("file_operation")
    logger.info(
        f"파일 작업: {operation}",
        extra={
            'user_id': user_id,
            'extra_data': {
                'operation': operation,
                'filename': filename,
                'file_size': file_size
            }
        }
    )

def log_security_event(event_type: str, user_id: Optional[int] = None, ip_address: str = None, details: Dict[str, Any] = None):
    """보안 이벤트 로깅"""
    logger = get_logger("security")
    logger.warning(
        f"보안 이벤트: {event_type}",
        extra={
            'user_id': user_id,
            'extra_data': {
                'event_type': event_type,
                'ip_address': ip_address,
                'details': details or {}
            }
        }
    )

class LoggingMiddleware:
    """로깅 미들웨어"""
    
    def __init__(self, app):
        self.app = app
        self.logger = get_logger("middleware")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            start_time = time.time()
            
            # 요청 정보 추출
            method = scope["method"]
            path = scope["path"]
            client_ip = scope.get("client", ["unknown"])[0]
            
            # 요청 로깅
            self.logger.info(
                f"HTTP 요청: {method} {path}",
                extra={
                    'extra_data': {
                        'method': method,
                        'path': path,
                        'client_ip': client_ip
                    }
                }
            )
            
            # 응답 후 로깅을 위한 래퍼
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    status_code = message["status"]
                    execution_time = time.time() - start_time
                    
                    # 응답 로깅
                    self.logger.info(
                        f"HTTP 응답: {method} {path} - {status_code}",
                        extra={
                            'execution_time': execution_time,
                            'extra_data': {
                                'method': method,
                                'path': path,
                                'status_code': status_code,
                                'client_ip': client_ip
                            }
                        }
                    )
                
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)

# 로깅 설정 초기화
logger = setup_logging()
