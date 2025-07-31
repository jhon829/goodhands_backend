from typing import Dict, List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from fastapi import HTTPException

from app.models.care import ChecklistResponse, CareSession, WeeklyChecklistScore
from app.models.checklist import ChecklistCategory, ChecklistType

class ChecklistService:
    
    @staticmethod
    def calculate_percentage_score(scores: List[int], max_score_per_item: int = 4) -> float:
        """점수 배열을 100% 환산"""
        if not scores:
            return 0.0
        
        total_score = sum(scores)
        max_possible = len(scores) * max_score_per_item
        return round((total_score / max_possible) * 100, 2)
    
    @staticmethod
    def validate_daily_submission(db: Session, care_session_id: int) -> bool:
        """하루 1회 제약 검증"""
        today = date.today()
        
        # 오늘 이미 제출한 체크리스트가 있는지 확인
        existing = db.query(ChecklistResponse).filter(
            and_(
                ChecklistResponse.care_session_id == care_session_id,
                func.date(ChecklistResponse.created_at) == today
            )
        ).first()
        
        return existing is None
    
    @staticmethod
    def validate_active_session(db: Session, care_session_id: int) -> bool:
        """활성 세션 검증"""
        session = db.query(CareSession).filter(
            and_(
                CareSession.id == care_session_id,
                CareSession.status == 'active'
            )
        ).first()
        
        return session is not None
    
    @staticmethod
    def get_session_info(db: Session, care_session_id: int) -> Optional[CareSession]:
        """세션 정보 조회"""
        return db.query(CareSession).filter(
            CareSession.id == care_session_id
        ).first()
    
    @staticmethod
    def process_checklist_scores(
        db: Session, 
        care_session_id: int, 
        checklist_scores: Dict[str, List[int]]
    ) -> Dict[str, float]:
        """점수 배열 처리 및 저장"""
        
        results = {}
        session = ChecklistService.get_session_info(db, care_session_id)
        
        if not session:
            raise HTTPException(400, "세션을 찾을 수 없습니다")
        
        for category_code, scores in checklist_scores.items():
            # 100% 환산 계산
            percentage = ChecklistService.calculate_percentage_score(scores)
            results[category_code] = percentage
            
            # DB에 개별 점수 저장
            for i, score in enumerate(scores):
                question_key = f"{category_code}_{i+1}"
                
                # 기존 응답 확인 (중복 방지)
                existing = db.query(ChecklistResponse).filter(
                    and_(
                        ChecklistResponse.care_session_id == care_session_id,
                        ChecklistResponse.question_key == question_key
                    )
                ).first()
                
                if existing:
                    # 기존 응답 업데이트
                    existing.selected_score = score
                else:
                    # 새 응답 생성
                    response = ChecklistResponse(
                        care_session_id=care_session_id,
                        question_key=question_key,
                        selected_score=score
                    )
                    db.add(response)
            
            # 주간 점수 저장
            ChecklistService.save_weekly_score(
                db, session, category_code, scores, percentage
            )
        
        db.commit()
        return results
    
    @staticmethod
    def save_weekly_score(
        db: Session,
        session: CareSession,
        category_code: str,
        scores: List[int],
        percentage: float
    ):
        """주간 점수 저장"""
        
        total_score = sum(scores)
        max_possible = len(scores) * 4
        
        # 기존 주간 점수 확인
        existing_score = db.query(WeeklyChecklistScore).filter(
            and_(
                WeeklyChecklistScore.care_session_id == session.id,
                WeeklyChecklistScore.checklist_type_code == category_code
            )
        ).first()
        
        if existing_score:
            # 기존 점수 업데이트
            existing_score.total_score = total_score
            existing_score.max_possible_score = max_possible
            existing_score.score_percentage = int(percentage)
        else:
            # 새 주간 점수 생성
            weekly_score = WeeklyChecklistScore(
                senior_id=session.senior_id,
                caregiver_id=session.caregiver_id,
                care_session_id=session.id,
                checklist_type_code=category_code,
                week_date=session.start_time.date(),
                week_start_date=session.start_time.date(),
                week_end_date=session.start_time.date(),
                total_score=total_score,
                max_possible_score=max_possible,
                score_percentage=int(percentage),
                checklist_count=1
            )
            db.add(weekly_score)
    
    @staticmethod
    def get_completion_status(db: Session, care_session_id: int) -> bool:
        """체크리스트 완료 상태 확인"""
        today = date.today()
        
        count = db.query(ChecklistResponse).filter(
            and_(
                ChecklistResponse.care_session_id == care_session_id,
                func.date(ChecklistResponse.created_at) == today
            )
        ).count()
        
        return count > 0
    
    @staticmethod
    def get_category_scores(db: Session, care_session_id: int) -> Dict[str, float]:
        """카테고리별 점수 조회"""
        scores = {}
        
        # 각 카테고리별로 점수 계산
        categories = ['nutrition', 'hypertension', 'depression']
        
        for category in categories:
            responses = db.query(ChecklistResponse).filter(
                and_(
                    ChecklistResponse.care_session_id == care_session_id,
                    ChecklistResponse.question_key.like(f"{category}_%")
                )
            ).all()
            
            if responses:
                score_values = [r.selected_score for r in responses]
                percentage = ChecklistService.calculate_percentage_score(score_values)
                scores[category] = percentage
        
        return scores
