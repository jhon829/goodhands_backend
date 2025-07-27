#!/usr/bin/env python3
"""
GoodHands Care Service 실행 스크립트
"""
import uvicorn
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

if __name__ == "__main__":
    # 개발 환경에서 실행 (포트 10007)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 10007)),
        reload=True if os.getenv("DEBUG", "True") == "True" else False,
        log_level="info"
    )
