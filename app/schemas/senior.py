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

# ✅ 질병 정보 스키마
class SeniorDiseaseResponse(BaseModel):
    id: int
    disease_type: str
    severity: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# ✅ 수정: 기본 시니어 응답에 질병 정보 포함
class SeniorResponse(SeniorBase):
    id: int
    photo: Optional[str] = None
    nursing_home_id: Optional[int] = None
    caregiver_id: Optional[int] = None
    guardian_id: Optional[int] = None
    created_at: datetime
    
    # ✅ 추가: 질병 정보 포함
    diseases: List[SeniorDiseaseResponse] = []
    
    class Config:
        from_attributes = True

class SeniorDiseaseBase(BaseModel):
    disease_type: str
    severity: Optional[str] = None
    notes: Optional[str] = None
    
    @validator('disease_type')
    def validate_disease_type(cls, v):
        # ✅ 수정: n8n API와 완전히 일치하는 타입 코드 사용
        allowed_diseases = [
            'nutrition',      # n8n: nutrition ✅
            'hypertension',   # n8n: hypertension ✅
            'depression',     # n8n: depression ✅
            'diabetes',       # n8n: diabetes ✅
            'dementia',       # 추가 질병들
            'arthritis',      
            'heart_disease',  
            'stroke',         
            'parkinsons',     
            'osteoporosis',   
            'other'           
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
    nursing_home: Optional[dict] = None
    caregiver: Optional[dict] = None
    guardian: Optional[dict] = None

# ✅ 추가: 프론트엔드에서 사용할 체크리스트 타입 정보
class AvailableChecklistType(BaseModel):
    type_code: str
    type_name: str
    description: Optional[str] = None

class SeniorWithChecklistTypes(SeniorResponse):
    """체크리스트 타입 정보가 포함된 시니어 응답"""
    available_checklist_types: List[AvailableChecklistType] = []
