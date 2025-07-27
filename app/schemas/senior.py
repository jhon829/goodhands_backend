"""
시니어 관련 스키마
"""
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime

class SeniorBase(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    
    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError('나이는 0-150 사이여야 합니다.')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        if v is not None and v not in ['남성', '여성', 'male', 'female']:
            raise ValueError('성별은 남성, 여성, male, female 중 하나여야 합니다.')
        return v

class SeniorCreate(SeniorBase):
    nursing_home_id: Optional[int] = None
    caregiver_id: Optional[int] = None
    guardian_id: Optional[int] = None

class SeniorUpdate(SeniorBase):
    name: Optional[str] = None

class SeniorResponse(SeniorBase):
    id: int
    photo: Optional[str] = None
    nursing_home_id: Optional[int] = None
    caregiver_id: Optional[int] = None
    guardian_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class SeniorDiseaseBase(BaseModel):
    disease_type: str
    severity: Optional[str] = None
    notes: Optional[str] = None
    
    @validator('disease_type')
    def validate_disease_type(cls, v):
        allowed_diseases = [
            '치매', '당뇨', '고혈압', '관절염', '심장질환', 
            '뇌졸중', '파킨슨병', '골다공증', '천식', '기타'
        ]
        if v not in allowed_diseases:
            raise ValueError(f'질병 유형은 {", ".join(allowed_diseases)} 중 하나여야 합니다.')
        return v
    
    @validator('severity')
    def validate_severity(cls, v):
        if v is not None and v not in ['경증', '중등도', '중증']:
            raise ValueError('중증도는 경증, 중등도, 중증 중 하나여야 합니다.')
        return v

class SeniorDiseaseCreate(SeniorDiseaseBase):
    senior_id: int

class SeniorDiseaseResponse(SeniorDiseaseBase):
    id: int
    senior_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class SeniorDetailResponse(SeniorResponse):
    diseases: List[SeniorDiseaseResponse] = []
    nursing_home: Optional[dict] = None
    caregiver: Optional[dict] = None
    guardian: Optional[dict] = None
