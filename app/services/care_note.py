from typing import Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from fastapi import HTTPException
import random

from app.models.care import CareNote, CareSession, CareNoteQuestion

class CareNoteService:
    
    @staticmethod
    def get_random_question(db: Session) -> Optional[CareNoteQuestion]:
        """6개 질문 중 1개 랜덤 선택"""
        questions = db.query(CareNoteQuestion).filter(
            CareNoteQuestion.is_active == True
        ).all()
        
        if not questions:
            return None
            
        return random.choice(questions)
    
    @staticmethod
    def get_all_questions(db: Session) -> list[CareNoteQuestion]:
        """모든 활성 질문 조회"""
        return db.query(CareNoteQuestion).filter(
            CareNoteQuestion.is_active == True
        ).order_by(CareNoteQuestion.question_number).all()
    
    @staticmethod
    def validate_daily_submission(db: Session, care_session_id: int) -> bool:
        """하루 1회 제약 검증"""
        # 해당 세션에 이미 돌봄노트가 있는지 확인
        existing = db.query(CareNote).filter(
            CareNote.care_session_id == care_session_id
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
    def create_care_note(
        db: Session,
        care_session_id: int,
        content: str,
        question_id: Optional[int] = None
    ) -> CareNote:
        """돌봄노트 생성"""
        
        # 질문 자동 선택 (question_id가 없으면)
        selected_question = None
        if question_id:
            selected_question = db.query(CareNoteQuestion).filter(
                CareNoteQuestion.id == question_id
            ).first()
        else:
            selected_question = CareNoteService.get_random_question(db)
        
        if not selected_question:
            raise HTTPException(400, "사용 가능한 질문이 없습니다")
        
        # 돌봄노트 생성
        care_note = CareNote(
            care_session_id=care_session_id,
            selected_question_id=selected_question.id,
            question_number=selected_question.question_number,
            question_type=selected_question.question_title,
            question_text=selected_question.question_text,
            content=content,
            is_final=True,
            modification_blocked=True
        )
        
        db.add(care_note)
        db.commit()
        db.refresh(care_note)
        
        return care_note
    
    @staticmethod
    def get_completion_status(db: Session, care_session_id: int) -> bool:
        """돌봄노트 완료 상태 확인"""
        existing = db.query(CareNote).filter(
            CareNote.care_session_id == care_session_id
        ).first()
        
        return existing is not None
    
    @staticmethod
    def get_care_note_by_session(db: Session, care_session_id: int) -> Optional[CareNote]:
        """세션별 돌봄노트 조회"""
        return db.query(CareNote).filter(
            CareNote.care_session_id == care_session_id
        ).first()
    
    @staticmethod
    def validate_content_length(content: str) -> bool:
        """돌봄노트 내용 길이 검증"""
        return 20 <= len(content.strip()) <= 500
    
    @staticmethod
    def is_modification_blocked(care_note_id: int) -> bool:
        """수정 차단 여부 확인 (항상 True)"""
        return True
    
    @staticmethod
    def get_question_by_id(db: Session, question_id: int) -> Optional[CareNoteQuestion]:
        """질문 ID로 질문 조회"""
        return db.query(CareNoteQuestion).filter(
            and_(
                CareNoteQuestion.id == question_id,
                CareNoteQuestion.is_active == True
            )
        ).first()
