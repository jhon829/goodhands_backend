from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # 데이터베이스 설정 (환경변수에서 읽어오기)
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./goodhands.db")
    database_host: str = os.getenv("DATABASE_HOST", "localhost")
    database_port: int = int(os.getenv("DATABASE_PORT", "3306"))
    database_name: str = os.getenv("DATABASE_NAME", "goodhands")
    database_user: str = os.getenv("DATABASE_USER", "goodhands")
    database_password: str = os.getenv("DATABASE_PASSWORD", "goodhands2024")
    
    # JWT 설정 (환경변수에서 읽어오기)
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here-please-change-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # 파일 업로드 설정
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    base_url: str = os.getenv("BASE_URL", "http://localhost:8000")
    
    # AI 서비스 설정 (n8n 연동)
    ai_service_url: str = os.getenv("AI_SERVICE_URL", "http://localhost:8001")
    n8n_webhook_url: str = os.getenv("N8N_WEBHOOK_URL", "http://pay.gzonesoft.co.kr:10006")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # n8n 전용 인증 설정
    n8n_api_key: str = os.getenv("N8N_API_KEY", "goodhands-n8n-api-key-2025")
    n8n_allowed_ips: List[str] = ["127.0.0.1", "localhost", "pay.gzonesoft.co.kr"]
    
    # 체크리스트 & 돌봄노트 설정
    daily_submission_limit: int = int(os.getenv("DAILY_SUBMISSION_LIMIT", "1"))
    checklist_types: List[str] = ["nutrition", "hypertension", "depression"]
    care_note_questions_count: int = int(os.getenv("CARE_NOTE_QUESTIONS_COUNT", "6"))
    max_checklist_score: int = int(os.getenv("MAX_CHECKLIST_SCORE", "4"))
    min_checklist_score: int = int(os.getenv("MIN_CHECKLIST_SCORE", "1"))
    care_note_min_length: int = int(os.getenv("CARE_NOTE_MIN_LENGTH", "20"))
    care_note_max_length: int = int(os.getenv("CARE_NOTE_MAX_LENGTH", "500"))
    
    # 환경 설정
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    app_version: str = os.getenv("APP_VERSION", "1.4.0")
    
    # CORS 설정
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:19006",  # React Native 개발 서버
        "exp://localhost:19000"   # Expo 개발 서버
    ]
    
    # 페이지네이션 설정
    default_page_size: int = 20
    max_page_size: int = 100
    
    # 캐시 설정
    cache_expire_minutes: int = 60
    
    # 로깅 설정
    log_level: str = "INFO"
    log_file: str = "app.log"
    
    # 보안 설정
    password_min_length: int = 8
    max_login_attempts: int = 5
    
    # 추이 분석 설정
    trend_analysis_weeks: int = 4
    min_data_points: int = 2
    alert_threshold_percentage: int = 15
    
    # AI 분석 설정
    ai_comment_max_length: int = 500
    keywords_max_count: int = 10
    special_notes_max_length: int = 200
    
    # 점수 계산 설정
    default_max_score: int = 5
    score_weights: dict = {
        "health": 1.2,
        "mental": 1.1,
        "physical": 1.0,
        "social": 0.9,
        "daily": 1.0,
        "general": 1.0
    }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 추가 필드 무시

settings = Settings()
