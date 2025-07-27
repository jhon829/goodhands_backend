#!/usr/bin/env python3
"""
Good Hands 데이터베이스 성별 데이터 수정 스크립트
서버에서 발견된 성별 검증 오류 해결: 'male'/'female' → '남성'/'여성'
"""

import requests
import json

def fix_gender_data():
    """성별 데이터 수정을 위한 SQL 스크립트 생성"""
    
    sql_script = """
-- Good Hands 성별 데이터 수정 SQL
-- 'male'/'female' → '남성'/'여성' 변환

-- 1. seniors 테이블 성별 수정
UPDATE seniors 
SET gender = CASE 
    WHEN gender = 'male' THEN '남성'
    WHEN gender = 'female' THEN '여성'
    WHEN gender = 'M' THEN '남성'
    WHEN gender = 'F' THEN '여성'
    WHEN gender = 'm' THEN '남성'
    WHEN gender = 'f' THEN '여성'
    ELSE gender
END
WHERE gender IS NOT NULL;

-- 2. 결과 확인
SELECT gender, COUNT(*) as count
FROM seniors 
WHERE gender IS NOT NULL
GROUP BY gender;

-- 3. 검증: 올바르지 않은 성별 값 확인
SELECT id, name, gender
FROM seniors 
WHERE gender IS NOT NULL 
  AND gender NOT IN ('남성', '여성');
"""
    
    with open("fix_gender_data.sql", "w", encoding="utf-8") as f:
        f.write(sql_script)
    
    print("✅ 성별 데이터 수정 SQL 스크립트 생성: fix_gender_data.sql")
    print("\n📋 실행 방법:")
    print("1. MariaDB에 접속")
    print("2. fix_gender_data.sql 파일 실행")
    print("3. 또는 Docker 컨테이너에서 직접 실행:")
    print("   docker exec -i goodhands-postgres-https psql -U goodhands_user -d goodhands < fix_gender_data.sql")

def create_updated_senior_model():
    """업데이트된 시니어 모델 생성 (성별 자동 변환 포함)"""
    
    updated_model = '''from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from ..database import Base
from datetime import datetime

class Senior(Base):
    __tablename__ = "seniors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    age = Column(Integer)
    _gender = Column("gender", String(10))  # 내부 저장용
    photo = Column(Text)
    nursing_home_id = Column(Integer, ForeignKey("nursing_homes.id"))
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"))
    guardian_id = Column(Integer, ForeignKey("guardians.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    nursing_home = relationship("NursingHome", back_populates="seniors")
    caregiver = relationship("Caregiver", back_populates="seniors")
    guardian = relationship("Guardian", back_populates="seniors")
    diseases = relationship("SeniorDisease", back_populates="senior", cascade="all, delete-orphan")
    care_sessions = relationship("CareSession", back_populates="senior")
    
    @hybrid_property
    def gender(self):
        """성별 자동 변환 (영어 → 한국어)"""
        if self._gender:
            gender_map = {
                'male': '남성',
                'female': '여성', 
                'M': '남성',
                'F': '여성',
                'm': '남성',
                'f': '여성'
            }
            return gender_map.get(self._gender, self._gender)
        return self._gender
    
    @gender.setter
    def gender(self, value):
        """성별 설정 (한국어 → 영어 자동 변환도 지원)"""
        if value:
            # 한국어 → 영어 변환 (데이터베이스 호환성)
            korean_to_english = {
                '남성': 'male',
                '여성': 'female'
            }
            # 영어 → 한국어 변환
            english_to_korean = {
                'male': '남성',
                'female': '여성',
                'M': '남성', 
                'F': '여성',
                'm': '남성',
                'f': '여성'
            }
            
            # 이미 한국어면 그대로, 영어면 한국어로 변환하여 저장
            if value in ['남성', '여성']:
                self._gender = value
            elif value in english_to_korean:
                self._gender = english_to_korean[value]
            else:
                self._gender = value
        else:
            self._gender = value
'''
    
    with open("updated_senior_model.py", "w", encoding="utf-8") as f:
        f.write(updated_model)
    
    print("✅ 업데이트된 시니어 모델 생성: updated_senior_model.py")

if __name__ == "__main__":
    print("🔧 Good Hands 성별 데이터 수정 도구")
    print("=" * 50)
    
    # 1. SQL 스크립트 생성
    fix_gender_data()
    
    print()
    
    # 2. 업데이트된 모델 생성
    create_updated_senior_model()
    
    print("\n🎯 다음 단계:")
    print("1. fix_gender_data.sql을 데이터베이스에서 실행")
    print("2. updated_senior_model.py 내용을 app/models/senior.py에 적용")
    print("3. 서버 재시작 후 API 테스트")
