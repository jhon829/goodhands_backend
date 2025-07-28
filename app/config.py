from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # 데이터베이스 설정 (개발환경: SQLite, 운영환경: MariaDB)
    database_url: str = "mysql+pymysql://goodhands:goodhands2024@49.50.132.155:3306/goodhands?charset=utf8mb4"
    # database_url: str = "sqlite:///./goodhands.db"
    
    # JWT 설정
    secret_key: str = "your-secret-key-here-please-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7일 = 7 * 24 * 60 = 10080분
    
    # 파일 업로드 설정
    upload_dir: str = "uploads"
    max_file_size: int = 10485760  # 10MB
    base_url: str = "http://localhost:8000"
    
    # AI 서비스 설정 (n8n 대신 내부 처리)
    ai_service_url: str = "http://localhost:8001"
    
    # 환경 설정
    environment: str = "development"
    debug: bool = True
    app_version: str = "1.4.0"
    
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
