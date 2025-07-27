#!/usr/bin/env python3
"""
Good Hands AI 리포트 시스템 개선 - 데이터베이스 마이그레이션
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.config import settings
from app.database import Base, engine
from app.models.enhanced_care import CareSchedule, WeeklyChecklistScore, HealthTrendAnalysis, SpecialNote

def run_migration():
    """데이터베이스 마이그레이션 실행"""
    
    print("AI 리포트 시스템 개선 마이그레이션 시작...")
    
    # 1. 새로운 테이블 생성
    print("새로운 테이블 생성 중...")
    Base.metadata.create_all(bind=engine)
    
    # 2. 기존 테이블에 컬럼 추가
    print("기존 테이블 컬럼 추가 중...")
    
    alter_queries = [
        # ChecklistResponse 테이블 확장
        "ALTER TABLE checklist_responses ADD COLUMN score_value INTEGER",
        "ALTER TABLE checklist_responses ADD COLUMN category VARCHAR(50)",
        "ALTER TABLE checklist_responses ADD COLUMN weight DECIMAL(3,2) DEFAULT 1.0",
        
        # AIReport 테이블 확장
        "ALTER TABLE ai_reports ADD COLUMN checklist_score_total INTEGER",
        "ALTER TABLE ai_reports ADD COLUMN checklist_score_percentage DECIMAL(5,2)",
        "ALTER TABLE ai_reports ADD COLUMN trend_comparison JSON",
        "ALTER TABLE ai_reports ADD COLUMN special_notes_summary TEXT",
        "ALTER TABLE ai_reports ADD COLUMN n8n_workflow_id VARCHAR(100)",
        "ALTER TABLE ai_reports ADD COLUMN ai_processing_status VARCHAR(20) DEFAULT 'pending'"
    ]
    
    with engine.connect() as connection:
        for query in alter_queries:
            try:
                connection.execute(text(query))
                print(f"실행 완료: {query[:50]}...")
            except Exception as e:
                print(f"스키마 수정 오류 (무시 가능): {e}")
        
        connection.commit()
    
    print("마이그레이션 완료!")

if __name__ == "__main__":
    run_migration()
