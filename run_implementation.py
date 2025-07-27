#!/usr/bin/env python3
"""
Good Hands AI 리포트 시스템 개선 - 전체 구현 실행 스크립트
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    print("🚀 Good Hands AI 리포트 시스템 개선 구현 시작!")
    print("=" * 60)
    
    # 1. 환경 확인
    print("1️⃣ 환경 확인 중...")
    check_environment()
    
    # 2. 데이터베이스 마이그레이션
    print("2️⃣ 데이터베이스 마이그레이션 실행 중...")
    run_migration()
    
    # 3. 환경 변수 설정 확인
    print("3️⃣ 환경 변수 설정 확인 중...")
    check_env_variables()
    
    # 4. 테스트 데이터 생성
    print("4️⃣ 테스트 데이터 생성 중...")
    create_test_data()
    
    print("🎉 구현 완료!")
    print("=" * 60)
    print("다음 단계:")
    print("1. FastAPI 서버 실행: python -m uvicorn app.main:app --reload")
    print("2. 테스트 API 호출: POST /api/ai/trigger-ai-analysis")
    print("3. 추이 분석 확인: GET /api/guardian/trend-analysis/{senior_id}")

def check_environment():
    """환경 확인"""
    required_packages = [
        "fastapi", "sqlalchemy", "requests", "python-jose", 
        "passlib", "python-multipart", "pillow"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package}")
    
    if missing_packages:
        print(f"누락된 패키지를 설치하세요: pip install {' '.join(missing_packages)}")
        sys.exit(1)

def run_migration():
    """데이터베이스 마이그레이션 실행"""
    try:
        # 마이그레이션 스크립트 실행
        subprocess.run([sys.executable, "database_migration.py"], check=True)
        print("  ✅ 데이터베이스 마이그레이션 완료")
    except subprocess.CalledProcessError:
        print("  ❌ 마이그레이션 오류")
        print("  수동으로 실행하세요: python database_migration.py")

def check_env_variables():
    """환경 변수 확인"""
    required_vars = [
        "DATABASE_URL", "SECRET_KEY"
    ]
    
    env_path = Path(".env")
    if not env_path.exists():
        print("  ⚠️ .env 파일이 없습니다. 생성해주세요.")
        create_env_template()
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}")
        else:
            print(f"  ❌ {var} - 설정 필요")

def create_env_template():
    """환경 변수 템플릿 생성"""
    template = """
# 데이터베이스 설정
DATABASE_URL=sqlite:///./goodhands.db

# JWT 설정  
SECRET_KEY=your-secret-key-here-please-change-in-production

# AI 분석 설정
TREND_ANALYSIS_WEEKS=4
MIN_DATA_POINTS=2
ALERT_THRESHOLD_PERCENTAGE=15

# 점수 계산 설정
DEFAULT_MAX_SCORE=5
"""
    
    with open(".env.template", "w") as f:
        f.write(template.strip())
    
    print("  📝 .env.template 파일이 생성되었습니다. 복사해서 .env로 사용하세요.")

def create_test_data():
    """테스트 데이터 생성"""
    try:
        # 기존 시드 데이터 실행
        subprocess.run([sys.executable, "seed_data.py"], check=True)
        print("  ✅ 테스트 데이터 생성 완료")
    except subprocess.CalledProcessError:
        print("  ⚠️ 테스트 데이터 생성 실패. 수동으로 실행하세요: python seed_data.py")

if __name__ == "__main__":
    main()
