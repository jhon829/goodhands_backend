"""
AI 리포트 생성 서비스
"""
import json
from typing import Dict, List, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Senior, CareSession, ChecklistResponse, CareNote

class AIReportService:
    def __init__(self, db: Session):
        self.db = db
    
    async def generate_report(
        self,
        session: CareSession,
        senior: Senior,
        checklist_responses: List[ChecklistResponse],
        care_notes: List[CareNote]
    ) -> Dict[str, Any]:
        """AI 리포트 생성"""
        
        # 키워드 생성
        keywords = self._generate_keywords(checklist_responses, care_notes)
        
        # 리포트 본문 생성
        content = self._generate_report_content(
            session, senior, checklist_responses, care_notes
        )
        
        # AI 코멘트 생성
        ai_comment = self._generate_ai_comment(
            checklist_responses, care_notes, senior
        )
        
        return {
            "keywords": keywords,
            "content": content,
            "ai_comment": ai_comment
        }
    
    def _generate_keywords(
        self, 
        checklist_responses: List[ChecklistResponse], 
        care_notes: List[CareNote]
    ) -> List[str]:
        """키워드 생성 로직"""
        
        keywords = []
        
        # 체크리스트 기반 키워드 생성
        mood_responses = [
            r for r in checklist_responses 
            if r.question_key == "mood_state"
        ]
        
        if mood_responses:
            mood_answer = mood_responses[0].answer
            if mood_answer in ["매우 좋음", "좋음"]:
                keywords.append("기분좋음")
            elif mood_answer in ["나쁨", "매우 나쁨"]:
                keywords.append("기분저하")
        
        # 건강 상태 키워드
        health_positive = 0
        health_negative = 0
        
        for response in checklist_responses:
            if response.question_key in ["meal_intake", "water_intake", "sleep_quality"]:
                if response.answer in [True, "완전 섭취", "잘 주무심"]:
                    health_positive += 1
                elif response.answer in [False, "거의 안 드심", "잠들기 어려워함"]:
                    health_negative += 1
        
        if health_positive > health_negative:
            keywords.append("건강함")
        elif health_negative > health_positive:
            keywords.append("건강주의")
        
        # 돌봄노트 기반 키워드
        family_notes = [
            note for note in care_notes 
            if note.question_type == "family_longing"
        ]
        
        if family_notes:
            content = family_notes[0].content.lower()
            if any(word in content for word in ["그리워", "보고싶", "가족"]):
                keywords.append("가족그리움")
        
        # 특별한 순간 키워드
        special_notes = [
            note for note in care_notes 
            if note.question_type == "special_moments"
        ]
        
        if special_notes:
            content = special_notes[0].content.lower()
            if any(word in content for word in ["웃음", "기쁨", "행복", "즐거움"]):
                keywords.append("행복한순간")
        
        # 최대 5개 키워드 반환
        return keywords[:5]
