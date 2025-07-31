"""
n8n 워크플로우 전용 AI API 라우터
- 8개 핵심 엔드포인트만 포함
- 중복 제거 및 코드 최적화
- Good Hands 프로젝트용

작성일: 2025-07-30
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
import random
import json

from ..database import get_db
from ..models import (
    User, CareSession, AIReport, ChecklistResponse, CareNote, 
    Senior, Caregiver, Guardian, CareNoteQuestion, ChecklistType,
    WeeklyChecklistScore, Notification
)
from ..schemas import AIReportResponse, AIReportCreate
from ..services.auth import get_current_user, verify_n8n_api_key

router = APIRouter()

# ============================================================================
# n8n 전용 API 엔드포인트들 (API Key 인증)
# ============================================================================

@router.get("/n8n/checklist-trend-data/{senior_id}/{type_code}")
async def get_checklist_trend_data_n8n(
    senior_id: int,
    type_code: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_n8n_api_key)  # n8n 전용 인증
):
    """
    n8n 전용: 특정 유형의 3주차 체크리스트 점수 추이 데이터 조회
    """
    try:
        # 시니어 존재 확인
        senior = db.query(Senior).filter(Senior.id == senior_id).first()
        if not senior:
            raise HTTPException(404, "시니어를 찾을 수 없습니다.")
        
        # 체크리스트 유형 확인
        checklist_type = db.query(ChecklistType).filter(
            ChecklistType.type_code == type_code
        ).first()
        
        if not checklist_type:
            raise HTTPException(404, f"체크리스트 유형을 찾을 수 없습니다: {type_code}")
        
        # 지난 3주차 점수 조회 (최신순)
        recent_scores = db.query(WeeklyChecklistScore).filter(
            WeeklyChecklistScore.senior_id == senior_id,
            WeeklyChecklistScore.checklist_type_code == type_code
        ).order_by(WeeklyChecklistScore.week_date.desc()).limit(3).all()
        
        # 현재 점수 (가장 최신)
        current_score = recent_scores[0] if recent_scores else None
        
        # 이전 점수들 (두 번째부터)
        previous_scores = recent_scores[1:] if len(recent_scores) > 1 else []
        
        return {
            "senior_id": senior_id,
            "senior_name": senior.name,
            "senior_age": senior.age,
            "checklist_type": {
                "type_code": type_code,
                "type_name": checklist_type.type_name,
                "max_score": checklist_type.max_score
            },
            "current_score": {
                "total_score": current_score.total_score if current_score else 0,
                "score_percentage": float(current_score.score_percentage) if current_score else 0,
                "status_code": current_score.status_code if current_score else 2,
                "week_date": current_score.week_date.isoformat() if current_score else None
            } if current_score else None,
            "previous_scores": [
                {
                    "total_score": score.total_score,
                    "score_percentage": float(score.score_percentage),
                    "status_code": score.status_code,
                    "week_date": score.week_date.isoformat()
                } for score in previous_scores
            ],
            "weeks_available": len(recent_scores)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"데이터 조회 중 오류: {str(e)}")

@router.get("/n8n/care-note-data/{session_id}")
async def get_care_note_data_n8n(
    session_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_n8n_api_key)  # n8n 전용 인증
):
    """
    n8n 전용: 특정 세션의 돌봄노트 데이터 조회
    """
    try:
        # 케어 세션 조회
        care_session = db.query(CareSession).filter(
            CareSession.id == session_id
        ).first()
        
        if not care_session:
            raise HTTPException(404, "케어 세션을 찾을 수 없습니다.")
        
        # 돌봄노트 조회
        care_note = db.query(CareNote).filter(
            CareNote.care_session_id == session_id
        ).first()
        
        if not care_note:
            raise HTTPException(404, "돌봄노트를 찾을 수 없습니다.")
        
        # 질문 정보 조회
        question_info = {}
        if care_note.selected_question_id:
            question = db.query(CareNoteQuestion).filter(
                CareNoteQuestion.id == care_note.selected_question_id
            ).first()
            if question:
                question_info = {
                    "question_title": question.question_title,
                    "question_text": question.question_text,
                    "guide_text": question.guide_text
                }
        
        # 시니어 정보 조회
        senior = db.query(Senior).filter(
            Senior.id == care_session.senior_id
        ).first()
        
        return {
            "session_id": session_id,
            "senior_id": care_session.senior_id,
            "content": care_note.content,
            "question_title": question_info.get("question_title", ""),
            "question_text": question_info.get("question_text", ""),
            "senior_name": senior.name if senior else "Unknown",
            "senior_age": senior.age if senior else None,
            "created_at": care_note.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"돌봄노트 데이터 조회 중 오류: {str(e)}")

@router.post("/n8n/save-complete-analysis")
async def save_complete_analysis_n8n(
    analysis_data: Dict[str, Any],
    db: Session = Depends(get_db),
    _: bool = Depends(verify_n8n_api_key)  # n8n 전용 인증
):
    """
    n8n 전용: 완전한 AI 분석 결과 저장 (4개 리포트)
    """
    try:
        session_id = analysis_data.get("session_id")
        senior_id = analysis_data.get("senior_id")
        reports = analysis_data.get("reports", [])
        
        if not all([session_id, senior_id, reports]):
            raise HTTPException(400, "session_id, senior_id, reports가 모두 필요합니다.")
        
        saved_report_ids = []
        
        for report in reports:
            ai_report = AIReport(
                care_session_id=session_id,
                senior_id=senior_id,
                report_type=report.get("report_type"),
                checklist_type_code=report.get("checklist_type_code"),
                content=report.get("content"),
                ai_comment=report.get("ai_comment"),
                status_code=report.get("status_code"),
                trend_analysis=report.get("trend_analysis"),
                created_at=datetime.now()
            )
            
            db.add(ai_report)
            db.flush()
            saved_report_ids.append(ai_report.id)
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"{len(reports)}개의 리포트가 저장되었습니다.",
            "report_ids": saved_report_ids,
            "session_id": session_id,
            "senior_id": senior_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"AI 분석 결과 저장 중 오류: {str(e)}")

@router.post("/n8n/send-guardian-notification")
async def send_guardian_notification_n8n(
    notification_data: Dict[str, Any],
    db: Session = Depends(get_db),
    _: bool = Depends(verify_n8n_api_key)  # n8n 전용 인증
):
    """
    n8n 전용: 가디언에게 분석 완료 알림 발송
    """
    try:
        senior_id = notification_data.get("senior_id")
        session_id = notification_data.get("session_id")
        summary = notification_data.get("summary", "돌봄 분석이 완료되었습니다.")
        
        if not all([senior_id, session_id]):
            raise HTTPException(400, "senior_id, session_id가 필요합니다.")
        
        # 시니어 정보 조회
        senior = db.query(Senior).filter(Senior.id == senior_id).first()
        if not senior or not senior.guardian_id:
            raise HTTPException(404, "시니어 또는 가디언을 찾을 수 없습니다.")
        
        # 가디언 정보 조회
        guardian = db.query(Guardian).filter(Guardian.id == senior.guardian_id).first()
        if not guardian:
            raise HTTPException(404, "가디언을 찾을 수 없습니다.")
        
        # 알림 생성
        notification = Notification(
            sender_id=11,  # 케어기버 user_id (고정값)
            receiver_id=guardian.user_id,
            type="complete_ai_analysis",
            title=f"{senior.name}님 돌봄 분석 완료",
            content=summary,
            data=json.dumps({
                "senior_id": senior_id,
                "session_id": session_id,
                "priority": "normal"
            }),
            is_read=False
        )
        
        db.add(notification)
        db.commit()
        
        return {
            "status": "success",
            "message": "알림이 발송되었습니다.",
            "notification_id": notification.id,
            "guardian_name": guardian.name,
            "sent_at": notification.created_at.isoformat()
        }
        
    except HTTPException:
        raise  
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"알림 발송 중 오류: {str(e)}")

# ============================================================================
# 기존 JWT 인증 API 엔드포인트들 (하위 호환성 유지)
# ============================================================================

@router.get("/checklist-trend-data/{senior_id}/{type_code}")
async def get_checklist_trend_data(
    senior_id: int,
    type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    특정 유형의 3주차 체크리스트 점수 추이 데이터 조회
    n8n 워크플로우에서 GPT 프롬프트 데이터로 사용
    """
    try:
        # 시니어 존재 확인
        senior = db.query(Senior).filter(Senior.id == senior_id).first()
        if not senior:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="시니어를 찾을 수 없습니다."
            )
        
        # 체크리스트 유형 확인
        checklist_type = db.query(ChecklistType).filter(
            ChecklistType.type_code == type_code
        ).first()
        
        if not checklist_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"체크리스트 유형을 찾을 수 없습니다: {type_code}"
            )
        
        # 지난 3주차 점수 조회 (최신순)
        recent_scores = db.query(WeeklyChecklistScore).filter(
            WeeklyChecklistScore.senior_id == senior_id,
            WeeklyChecklistScore.checklist_type_code == type_code
        ).order_by(WeeklyChecklistScore.week_date.desc()).limit(3).all()
        
        scores_data = []
        for score in recent_scores:
            scores_data.append({
                "week_date": score.week_date.isoformat(),
                "total_score": score.total_score,
                "max_possible_score": score.max_possible_score,
                "score_percentage": float(score.score_percentage),
                "status_code": score.status_code
            })
        
        return {
            "senior_id": senior_id,
            "checklist_type": {
                "code": type_code,
                "name": checklist_type.type_name,
                "max_score": checklist_type.max_score
            },
            "recent_scores": scores_data,
            "weeks_available": len(scores_data)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"체크리스트 추이 데이터 조회 중 오류가 발생했습니다: {str(e)}"
        )

# ============================================================================
# 2. 랜덤 돌봄노트 질문 선택 (n8n → 랜덤 질문 선택)
# ============================================================================

@router.get("/random-care-question")
async def get_random_care_question(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    6개 돌봄노트 질문 중 랜덤으로 1개 선택
    n8n 워크플로우에서 이번 주 질문 결정용
    """
    try:
        # 활성화된 돌봄노트 질문들 조회
        questions = db.query(CareNoteQuestion).filter(
            CareNoteQuestion.is_active == True
        ).all()
        
        if not questions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="활성화된 돌봄노트 질문이 없습니다."
            )
        
        # 랜덤 선택
        selected_question = random.choice(questions)
        
        return {
            "question_id": selected_question.id,
            "question_number": selected_question.question_number,
            "question_title": selected_question.question_title,
            "question_text": selected_question.question_text,
            "guide_text": selected_question.guide_text,
            "examples": selected_question.examples
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"랜덤 돌봄노트 질문 조회 중 오류가 발생했습니다: {str(e)}"
        )

# ============================================================================
# 3. 돌봄노트 데이터 조회 (n8n → GPT 입력 데이터)
# ============================================================================

@router.get("/care-note-data/{session_id}")
async def get_care_note_data(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    특정 세션의 돌봄노트 데이터 조회
    n8n 워크플로우에서 GPT 가족 소통 코멘트 생성용
    """
    try:
        # 케어 세션 조회
        care_session = db.query(CareSession).filter(
            CareSession.id == session_id
        ).first()
        
        if not care_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="케어 세션을 찾을 수 없습니다."
            )
        
        # 돌봄노트 조회
        care_note = db.query(CareNote).filter(
            CareNote.care_session_id == session_id
        ).first()
        
        if not care_note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="돌봄노트를 찾을 수 없습니다."
            )
        
        # 질문 정보 조회
        question_info = None
        if care_note.selected_question_id:
            question = db.query(CareNoteQuestion).filter(
                CareNoteQuestion.id == care_note.selected_question_id
            ).first()
            if question:
                question_info = {
                    "question_title": question.question_title,
                    "question_text": question.question_text,
                    "guide_text": question.guide_text
                }
        
        # 시니어 정보 조회
        senior = db.query(Senior).filter(
            Senior.id == care_session.senior_id
        ).first()
        
        senior_info = {
            "name": senior.name if senior else "Unknown",
            "age": senior.age if senior else None,
            "diseases": []  # TODO: 질병 정보 추가 필요시
        }
        
        return {
            "session_id": session_id,
            "senior_id": care_session.senior_id,
            "care_note": {
                "question_number": care_note.question_number,
                "content": care_note.content
            },
            "question_info": question_info,
            "senior_info": senior_info
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"돌봄노트 데이터 조회 중 오류가 발생했습니다: {str(e)}"
        )

# ============================================================================
# 4. 주간 점수 계산 및 저장 (n8n → 점수 계산)
# ============================================================================

@router.post("/calculate-weekly-scores")
async def calculate_weekly_scores(
    session_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    주간 체크리스트 점수 계산 및 저장
    n8n 워크플로우에서 AI 분석 전 점수 계산용
    """
    try:
        session_id = session_data.get("session_id")
        senior_id = session_data.get("senior_id")  
        week_date = session_data.get("week_date")
        
        if not all([session_id, senior_id, week_date]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id, senior_id, week_date가 모두 필요합니다."
            )
        
        # 케어 세션에서 caregiver_id 가져오기
        care_session = db.query(CareSession).filter(
            CareSession.id == session_id
        ).first()
        
        if not care_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="케어 세션을 찾을 수 없습니다."
            )
        
        caregiver_id = care_session.caregiver_id
        
        # 3가지 유형별 점수 계산
        type_codes = ["nutrition", "hypertension", "depression"]
        calculated_scores = []
        
        for type_code in type_codes:
            # 해당 유형의 체크리스트 응답 조회
            responses = db.query(ChecklistResponse).filter(
                ChecklistResponse.care_session_id == session_id,
                ChecklistResponse.checklist_type_code == type_code
            ).all()
            
            # 점수 합계 계산
            total_score = sum([r.selected_score for r in responses if r.selected_score])
            
            # 체크리스트 유형 정보 조회
            checklist_type = db.query(ChecklistType).filter(
                ChecklistType.type_code == type_code
            ).first()
            
            max_score = checklist_type.max_score if checklist_type else 16
            score_percentage = (total_score / max_score) * 100 if max_score > 0 else 0
            
            # 지난 주 점수와 비교하여 상태코드 결정
            last_week_score = db.query(WeeklyChecklistScore).filter(
                WeeklyChecklistScore.senior_id == senior_id,
                WeeklyChecklistScore.checklist_type_code == type_code
            ).order_by(WeeklyChecklistScore.week_date.desc()).first()
            
            status_code = 2  # 기본값: 유지
            if last_week_score:
                if total_score > last_week_score.total_score:
                    status_code = 1  # 개선
                elif total_score < last_week_score.total_score:
                    status_code = 3  # 악화
            
            # 주간 점수 저장
            weekly_score = WeeklyChecklistScore(
                senior_id=senior_id,
                caregiver_id=caregiver_id,  # 세션에서 가져온 caregiver_id 사용
                care_session_id=session_id,
                checklist_type_code=type_code,
                week_date=datetime.fromisoformat(week_date).date(),
                week_start_date=datetime.fromisoformat(week_date).date(),  # 임시로 같은 값
                week_end_date=datetime.fromisoformat(week_date).date(),    # 임시로 같은 값
                total_score=total_score,
                max_possible_score=max_score,
                score_percentage=score_percentage,
                status_code=status_code,
                checklist_count=len(responses),  # 응답 개수
                trend_indicator="stable"  # 기본값
            )
            db.add(weekly_score)
            
            calculated_scores.append({
                "type_code": type_code,
                "total_score": total_score,
                "max_possible_score": max_score,
                "score_percentage": score_percentage,
                "status_code": status_code
            })
        
        db.commit()
        return {
            "status": "success", 
            "scores": calculated_scores
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"주간 점수 계산 중 오류가 발생했습니다: {str(e)}"
        )

# ============================================================================
# 5. 유형별 AI 리포트 저장 (n8n GPT 결과 → DB 저장)
# ============================================================================

@router.post("/save-type-reports")
async def save_type_reports(
    report_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    3가지 유형별 AI 리포트 저장
    n8n 워크플로우에서 GPT 생성 결과 저장용
    """
    try:
        session_id = report_data.get("session_id")
        senior_id = report_data.get("senior_id")
        reports = report_data.get("reports", [])
        
        if not all([session_id, senior_id, reports]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id, senior_id, reports가 모두 필요합니다."
            )
        
        saved_report_ids = []
        
        for report in reports:
            ai_report = AIReport(
                care_session_id=session_id,
                senior_id=senior_id,
                report_type=report.get("report_type"),
                checklist_type_code=report.get("checklist_type_code"),
                content=report.get("content"),
                status_code=report.get("status_code"),
                trend_analysis=report.get("trend_analysis"),
                status="completed",
                ai_processing_status="completed",
                created_at=datetime.now()
            )
            
            db.add(ai_report)
            db.flush()  # ID 생성을 위해
            saved_report_ids.append(ai_report.id)
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"{len(reports)}개의 유형별 리포트가 성공적으로 저장되었습니다.",
            "report_ids": saved_report_ids
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 리포트 저장 중 오류가 발생했습니다: {str(e)}"
        )

# ============================================================================
# 6. 돌봄노트 코멘트 저장 (n8n GPT 결과 → DB 저장)
# ============================================================================

@router.post("/save-care-comment")
async def save_care_comment(
    comment_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    돌봄노트 기반 가족 소통 코멘트 저장
    n8n 워크플로우에서 GPT 생성 코멘트 저장용
    """
    try:
        session_id = comment_data.get("session_id")
        senior_id = comment_data.get("senior_id")
        ai_comment = comment_data.get("ai_comment")
        
        if not all([session_id, senior_id, ai_comment]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id, senior_id, ai_comment가 모두 필요합니다."
            )
        
        # 가족 소통 코멘트 저장
        care_comment_report = AIReport(
            care_session_id=session_id,
            senior_id=senior_id,
            report_type="care_note_comment",
            content=ai_comment,
            ai_comment=comment_data.get("priority_level", "normal"),
            status="completed",
            ai_processing_status="completed",
            created_at=datetime.now()
        )
        
        db.add(care_comment_report)
        db.commit()
        
        return {
            "status": "success",
            "message": "가족 소통 코멘트가 성공적으로 저장되었습니다.",
            "comment_id": care_comment_report.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"돌봄노트 코멘트 저장 중 오류가 발생했습니다: {str(e)}"
        )

# ============================================================================
# 7. 분석 상태 확인 (n8n → 완료 여부 체크)
# ============================================================================

@router.get("/analysis-status/{session_id}")
async def get_analysis_status(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    AI 분석 완료 상태 확인
    n8n 워크플로우에서 4개 리포트 생성 완료 체크용
    """
    try:
        # 해당 세션의 완료된 AI 리포트 개수 조회
        completed_reports = db.query(AIReport).filter(
            AIReport.care_session_id == session_id,
            AIReport.status == "completed"
        ).all()
        
        reports_info = []
        for report in completed_reports:
            reports_info.append({
                "report_type": report.report_type,
                "status": report.status,
                "created_at": report.created_at.isoformat()
            })
        
        # 케어 세션 정보 조회
        care_session = db.query(CareSession).filter(
            CareSession.id == session_id
        ).first()
        
        senior_id = care_session.senior_id if care_session else None
        
        return {
            "session_id": session_id,
            "senior_id": senior_id,
            "completed_reports": len(completed_reports),
            "total_expected": 4,  # 3개 유형별 리포트 + 1개 코멘트
            "status": "completed" if len(completed_reports) >= 4 else "in_progress",
            "reports": reports_info
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"분석 상태 확인 중 오류가 발생했습니다: {str(e)}"
        )

# ============================================================================
# 8. 완료 알림 발송 (n8n → 가디언 알림)
# ============================================================================

@router.post("/send-complete-analysis")
async def send_complete_analysis_notification(
    notification_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    분석 완료 알림을 가디언에게 발송
    n8n 워크플로우에서 최종 알림 발송용
    """
    try:
        senior_id = notification_data.get("senior_id")
        session_id = notification_data.get("session_id")
        title = notification_data.get("title", "이번 주 돌봄 분석 완료")
        content = notification_data.get("content", "3가지 상태 분석과 가족 소통 제안이 준비되었습니다.")
        
        if not all([senior_id, session_id]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="senior_id, session_id가 필요합니다."
            )
        
        # 해당 시니어의 가디언 조회
        senior = db.query(Senior).filter(Senior.id == senior_id).first()
        if not senior or not senior.guardian_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="시니어 또는 가디언 정보를 찾을 수 없습니다."
            )
        
        guardian = db.query(Guardian).filter(Guardian.id == senior.guardian_id).first()
        if not guardian:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="가디언을 찾을 수 없습니다."
            )
        
        # 알림 생성 및 저장
        notification = Notification(
            sender_id=current_user.id,
            receiver_id=guardian.user_id,
            type="complete_ai_analysis",
            title=title,
            content=content,
            data=json.dumps({
                "senior_id": senior_id,
                "session_id": session_id,
                "priority": "medium"
            }),
            is_read=False,
            created_at=datetime.now()
        )
        
        db.add(notification)
        db.commit()
        
        return {
            "status": "success",
            "message": "알림이 성공적으로 발송되었습니다.",
            "notification_id": notification.id,
            "recipients": [{
                "guardian_id": guardian.id,
                "user_id": guardian.user_id,
                "name": guardian.name,
                "sent_at": notification.created_at.isoformat()
            }]
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"알림 발송 중 오류가 발생했습니다: {str(e)}"
        )
