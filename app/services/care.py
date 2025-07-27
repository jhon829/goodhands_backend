"""
돌봄 서비스 로직
"""
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from app.models import Senior, SeniorDisease

class CareService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_checklist_template(self, senior: Senior) -> List[Dict[str, Any]]:
        """시니어의 질병에 따른 체크리스트 템플릿 생성"""
        
        # 기본 공통 체크리스트
        common_checklist = [
            {
                "key": "meal_intake",
                "question": "식사를 잘 드셨나요?",
                "type": "select",
                "options": ["완전 섭취", "절반 섭취", "소량 섭취", "거의 안 드심"],
                "required": True
            },
            {
                "key": "water_intake",
                "question": "물을 충분히 마셨나요?",
                "type": "boolean",
                "required": True
            },
            {
                "key": "sleep_quality",
                "question": "지난 밤 잠은 잘 주무셨나요?",
                "type": "select",
                "options": ["잘 주무심", "보통", "자주 깨심", "잠들기 어려워함"],
                "required": True
            },
            {
                "key": "mood_state",
                "question": "오늘 기분 상태는 어떠신가요?",
                "type": "select",
                "options": ["매우 좋음", "좋음", "보통", "나쁨", "매우 나쁨"],
                "required": True
            },
            {
                "key": "activity_level",
                "question": "활동 수준은 어떠했나요?",
                "type": "select",
                "options": ["매우 활발", "활발", "보통", "조용함", "매우 조용함"],
                "required": True
            },
            {
                "key": "communication",
                "question": "의사소통은 원활했나요?",
                "type": "boolean",
                "required": True
            },
            {
                "key": "pain_discomfort",
                "question": "통증이나 불편함을 호소하셨나요?",
                "type": "boolean",
                "required": True
            },
            {
                "key": "medication_taken",
                "question": "처방약을 정시에 복용하셨나요?",
                "type": "boolean",
                "required": True
            },
            {
                "key": "bathroom_needs",
                "question": "화장실 사용에 어려움이 있었나요?",
                "type": "boolean",
                "required": True
            },
            {
                "key": "social_interaction",
                "question": "다른 사람과 교류하셨나요?",
                "type": "boolean",
                "required": True
            }
        ]
        
        # 시니어의 질병별 추가 체크리스트
        disease_specific_checklist = []
        senior_diseases = self.db.query(SeniorDisease).filter(
            SeniorDisease.senior_id == senior.id
        ).all()
        
        for disease in senior_diseases:
            disease_questions = self._get_disease_specific_questions(disease.disease_type)
            disease_specific_checklist.extend(disease_questions)
        
        # 중복 제거
        all_questions = common_checklist + disease_specific_checklist
        seen_keys = set()
        unique_questions = []
        
        for question in all_questions:
            if question["key"] not in seen_keys:
                unique_questions.append(question)
                seen_keys.add(question["key"])
        
        return unique_questions
    
    def _get_disease_specific_questions(self, disease_type: str) -> List[Dict[str, Any]]:
        """질병별 특화 체크리스트 문항"""
        
        disease_questions = {
            "치매": [
                {
                    "key": "memory_check",
                    "question": "오늘 날짜와 요일을 기억하시나요?",
                    "type": "select",
                    "options": ["정확히 기억", "부분적으로 기억", "헷갈려함", "전혀 기억 안함"],
                    "required": True
                },
                {
                    "key": "family_recognition",
                    "question": "가족 사진을 보고 누구인지 아시나요?",
                    "type": "boolean",
                    "required": True
                },
                {
                    "key": "wandering_behavior",
                    "question": "배회하는 행동을 보이셨나요?",
                    "type": "boolean",
                    "required": True
                },
                {
                    "key": "confusion_level",
                    "question": "혼란스러워하는 정도는 어떠했나요?",
                    "type": "select",
                    "options": ["없음", "가벼움", "보통", "심함"],
                    "required": True
                },
                {
                    "key": "agitation",
                    "question": "초조함이나 불안함을 보이셨나요?",
                    "type": "boolean",
                    "required": True
                }
            ],
            "당뇨": [
                {
                    "key": "blood_sugar_check",
                    "question": "혈당을 측정했나요?",
                    "type": "boolean",
                    "required": True
                },
                {
                    "key": "blood_sugar_level",
                    "question": "혈당 수치는 어떠했나요? (mg/dL)",
                    "type": "number",
                    "required": False
                },
                {
                    "key": "diabetes_medication",
                    "question": "당뇨약을 정시에 복용하셨나요?",
                    "type": "boolean",
                    "required": True
                },
                {
                    "key": "foot_care",
                    "question": "발 상태를 확인했나요?",
                    "type": "boolean",
                    "required": True
                },
                {
                    "key": "thirst_frequency",
                    "question": "평소보다 목이 많이 마르셨나요?",
                    "type": "boolean",
                    "required": True
                }
            ],
            "고혈압": [
                {
                    "key": "blood_pressure_check",
                    "question": "혈압을 측정했나요?",
                    "type": "boolean",
                    "required": True
                },
                {
                    "key": "blood_pressure_systolic",
                    "question": "수축기 혈압 (mmHg)",
                    "type": "number",
                    "required": False
                },
                {
                    "key": "blood_pressure_diastolic",
                    "question": "이완기 혈압 (mmHg)",
                    "type": "number",
                    "required": False
                },
                {
                    "key": "salt_intake",
                    "question": "짠 음식을 피하셨나요?",
                    "type": "boolean",
                    "required": True
                },
                {
                    "key": "dizziness",
                    "question": "어지러움을 호소하셨나요?",
                    "type": "boolean",
                    "required": True
                }
            ],
            "관절염": [
                {
                    "key": "joint_pain",
                    "question": "관절 통증을 호소하셨나요?",
                    "type": "select",
                    "options": ["없음", "가벼움", "보통", "심함"],
                    "required": True
                },
                {
                    "key": "joint_stiffness",
                    "question": "관절 경직이 있었나요?",
                    "type": "boolean",
                    "required": True
                },
                {
                    "key": "mobility_difficulty",
                    "question": "움직임에 어려움이 있었나요?",
                    "type": "boolean",
                    "required": True
                }
            ],
            "심장질환": [
                {
                    "key": "chest_pain",
                    "question": "가슴 통증을 호소하셨나요?",
                    "type": "boolean",
                    "required": True
                },
                {
                    "key": "breathing_difficulty",
                    "question": "호흡 곤란이 있었나요?",
                    "type": "boolean",
                    "required": True
                },
                {
                    "key": "heart_rate",
                    "question": "맥박이 불규칙했나요?",
                    "type": "boolean",
                    "required": True
                }
            ]
        }
        
        return disease_questions.get(disease_type, [])
    
    def get_care_note_template(self) -> List[Dict[str, str]]:
        """돌봄노트 6개 핵심 질문 템플릿"""
        return [
            {
                "key": "special_moments",
                "question": "오늘 특별한 순간이 있었나요?",
                "placeholder": "웃으시거나 기뻐하신 순간, 새로운 시도를 하신 일 등을 적어주세요."
            },
            {
                "key": "family_longing",
                "question": "가족에 대한 그리움을 표현하셨나요?",
                "placeholder": "가족을 언급하시거나 보고 싶어하신 내용을 적어주세요."
            },
            {
                "key": "emotional_state",
                "question": "전반적인 감정 상태는 어떠했나요?",
                "placeholder": "하루 종일 어떤 감정을 주로 보이셨는지 적어주세요."
            },
            {
                "key": "conversation",
                "question": "어떤 대화를 나누셨나요?",
                "placeholder": "기억에 남는 대화나 자주 하신 말씀을 적어주세요."
            },
            {
                "key": "changes",
                "question": "평소와 다른 변화가 있었나요?",
                "placeholder": "행동, 식사, 수면 등에서 평소와 다른 점이 있었다면 적어주세요."
            },
            {
                "key": "care_episodes",
                "question": "특별한 돌봄 에피소드가 있었나요?",
                "placeholder": "함께 한 활동, 도움을 드린 일, 감동적인 순간 등을 적어주세요."
            }
        ]
