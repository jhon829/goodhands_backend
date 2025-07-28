"""
n8n 워크플로우 v2.0을 위한 새로운 AI 엔드포인트들
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import requests
import random

from ..database import get_db
from ..models.care import ChecklistType, WeeklyChecklistScore, CareNoteQuestion, CareSession, ChecklistResponse, CareNote
from ..models.report import AIReport
from ..models.senior import Senior
from ..models.user import User
from ..schemas.enhanced_care import (
    ChecklistTrendData, WeeklyScoreCalculation, RandomQuestionResponse,
    TypedChecklistSubmission, EnhancedCareNoteSubmission, AIWorkflowTrigger,
    WorkflowStatus, TypedAIReportResponse, MultipleReportsResponse
)
from ..services.auth import get_current_user

router = APIRouter()

# ==========================================
# 새로운 n8n 워크플로우 v2.0 엔드포인트들
# ==========================================

@router.get("/checklist-trend-data/{senior_id}/{type_code}")
async def get_checklist_trend_data(
    senior_id: int,
    type_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ChecklistTrendData:
    """특정 유형의 3주차 체크리스트 점수 추이 데이터 조회"""
    
    # 지난 3주차 점수 조회
    recent_scores = db.query(WeeklyChecklistScore).filter(
        WeeklyChecklistScore.senior_id == senior_id,
        WeeklyChecklistScore.checklist_type_code == type_code
    ).order_by(WeeklyChecklistScore.week_date.desc()).limit(3).all()
    
    scores_data = []
    for score in recent_scores:
        scores_data.append({
            "id": score.id,
            "senior_id": score.senior_id,
            "checklist_type_code": score.checklist_type_code,
            "week_date": score.week_date,
            "total_score": score.total_score,
            "max_possible_score": score.max_possible_score,
            "score_percentage": float(score.score_percentage),
            "status_code": score.status_code,
            "created_at": score.created_at
        })
    
    # 체크리스트 유형 정보
    checklist_type = db.query(ChecklistType).filter(
        ChecklistType.type_code == type_code
    ).first()
    
    return ChecklistTrendData(
        senior_id=senior_id,
        checklist_type={
            "code": type_code,
            "name": checklist_type.type_name if checklist_type else "",
            "max_score": checklist_type.max_score if checklist_type else 16
        },
        recent_scores=scores_data,
        weeks_available=len(scores_data)
    )

@router.post("/calculate-weekly-scores")
async def calculate_weekly_scores(
    session_data: WeeklyScoreCalculation,
    db: Session = Depends(get_db)
):
    """주간 체크리스트 점수 계산 및 저장"""
    
    session_id = session_data.session_id
    senior_id = session_data.senior_id
    week_date = session_data.week_date
    
    # 3가지 유형별 점수 계산
    type_codes = ["nutrition", "hypertension", "depression"]
    calculated_scores = []
    
    for type_code in type_codes:
        # 해당 유형의 체크리스트 응답 조회
        responses = db.query(ChecklistResponse).filter(
            ChecklistResponse.care_session_id == session_id,
            ChecklistResponse.checklist_type_code == type_code
        ).all()
        
        if not responses:
            continue
            
        # 점수 합계 계산
        total_score = sum([r.selected_score for r in responses if r.selected_score])
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
            care_session_id=session_id,
            checklist_type_code=type_code,
            week_date=week_date,
            total_score=total_score,
            max_possible_score=max_score,
            score_percentage=score_percentage,
            status_code=status_code
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
    return {"status": "success", "scores": calculated_scores}

@router.get("/random-care-question")
async def get_random_care_question(
    db: Session = Depends(get_db)
) -> RandomQuestionResponse:
    """랜덤 돌봄노트 질문 1개 선택"""
    
    questions = db.query(CareNoteQuestion).filter(
        CareNoteQuestion.is_active == True
    ).all()
    
    if not questions:
        raise HTTPException(status_code=404, detail="활성화된 질문이 없습니다")
    
    # 랜덤 선택
    selected_question = random.choice(questions)
    
    return RandomQuestionResponse(
        question_id=selected_question.id,
        question_number=selected_question.question_number,
        question_title=selected_question.question_title,
        question_text=selected_question.question_text,
        guide_text=selected_question.guide_text,
        examples=selected_question.examples
    )

@router.get("/care-note-data/{session_id}")
async def get_care_note_data(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """돌봄노트 데이터 조회 (n8n 워크플로우용)"""
    
    # 세션 정보
    session = db.query(CareSession).filter(CareSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    
    # 돌봄노트 조회
    care_note = db.query(CareNote).filter(
        CareNote.care_session_id == session_id
    ).first()
    
    if not care_note:
        raise HTTPException(status_code=404, detail="돌봄노트를 찾을 수 없습니다")
    
    # 질문 정보 조회
    question_info = db.query(CareNoteQuestion).filter(
        CareNoteQuestion.id == care_note.selected_question_id
    ).first()
    
    # 시니어 정보
    senior = db.query(Senior).filter(Senior.id == session.senior_id).first()
    
    return {
        "session_id": session_id,
        "senior_id": session.senior_id,
        "care_note": {
            "question_number": care_note.question_number,
            "content": care_note.content,
            "created_at": care_note.created_at
        },
        "question_info": {
            "question_title": question_info.question_title if question_info else "",
            "question_text": question_info.question_text if question_info else "",
            "guide_text": question_info.guide_text if question_info else ""
        },
        "senior_info": {
            "name": senior.name,
            "age": senior.age,
            "gender": senior.gender
        } if senior else None
    }

@router.get("/analysis-status/{session_id}")
async def get_analysis_status(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> WorkflowStatus:
    """분석 완료 상태 확인"""
    
    # 해당 세션의 AI 리포트 개수 확인
    completed_reports = db.query(AIReport).filter(
        AIReport.care_session_id == session_id
    ).count()
    
    return WorkflowStatus(
        session_id=session_id,
        completed_reports=completed_reports,
        total_expected=4,  # 3개 유형별 + 1개 코멘트
        status="completed" if completed_reports >= 4 else "processing"
    )

@router.post("/save-type-reports")
async def save_type_reports(
    report_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """유형별 AI 리포트 저장"""
    
    session_id = report_data.get("session_id")
    senior_id = report_data.get("senior_id")
    reports = report_data.get("reports", [])
    
    saved_reports = []
    
    for report in reports:
        ai_report = AIReport(
            care_session_id=session_id,
            report_type=report["report_type"],
            checklist_type_code=report.get("checklist_type_code"),
            content=report["content"],
            status_code=report.get("status_code"),
            trend_analysis=report.get("trend_analysis"),
            keywords=[],  # 키워드는 별도 처리
            ai_comment="",  # 유형별 리포트는 코멘트 없음
            status="generated"
        )
        
        db.add(ai_report)
        db.flush()  # ID 생성을 위해 flush
        saved_reports.append(ai_report.id)
    
    db.commit()
    
    return {
        "status": "success",
        "session_id": session_id,
        "saved_report_ids": saved_reports,
        "message": f"{len(saved_reports)}개의 유형별 리포트가 저장되었습니다"
    }

@router.post("/save-care-comment")
async def save_care_comment(
    comment_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """돌봄노트 기반 AI 코멘트 저장"""
    
    session_id = comment_data.get("session_id")
    
    ai_report = AIReport(
        care_session_id=session_id,
        report_type="care_note_comment",
        checklist_type_code=None,
        content="가족 소통 코멘트",
        ai_comment=comment_data.get("ai_comment"),
        status_code=None,  # 코멘트는 상태코드 없음
        trend_analysis=None,
        keywords=[],
        status="generated"
    )
    
    db.add(ai_report)
    db.commit()
    db.refresh(ai_report)
    
    return {
        "status": "success",
        "session_id": session_id,
        "comment_report_id": ai_report.id,
        "message": "가족 소통 코멘트가 저장되었습니다"
    }

@router.get("/reports/session/{session_id}")
async def get_session_reports(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> MultipleReportsResponse:
    """세션의 모든 AI 리포트 조회"""
    
    reports = db.query(AIReport).filter(
        AIReport.care_session_id == session_id
    ).order_by(AIReport.created_at.desc()).all()
    
    session = db.query(CareSession).filter(CareSession.id == session_id).first()
    senior_id = session.senior_id if session else None
    
    report_data = []
    for report in reports:
        report_data.append({
            "id": report.id,
            "care_session_id": report.care_session_id,
            "report_type": report.report_type,
            "checklist_type_code": report.checklist_type_code,
            "content": report.content,
            "ai_comment": report.ai_comment,
            "status_code": report.status_code,
            "trend_analysis": report.trend_analysis,
            "keywords": report.keywords or [],
            "created_at": report.created_at
        })
    
    return MultipleReportsResponse(
        session_id=session_id,
        senior_id=senior_id,
        reports=report_data,
        processing_status="completed" if len(reports) >= 4 else "processing"
    )

# ==========================================
# n8n 워크플로우 트리거 함수들
# ==========================================

async def trigger_ai_analysis_workflows(session_id: int, senior_id: int):
    """n8n AI 분석 워크플로우들을 트리거"""
    
    import os
    from ..config import settings
    
    # n8n 웹훅 URL들
    webhook_base_url = getattr(settings, 'N8N_WEBHOOK_BASE_URL', 'http://pay.gzonesoft.co.kr:10006/webhook')
    
    workflows = [
        f"{webhook_base_url}/complete-ai-analysis"
    ]
    
    trigger_data = {
        "session_id": session_id,
        "senior_id": senior_id,
        "trigger_time": datetime.now().isoformat()
    }
    
    results = []
    for webhook_url in workflows:
        try:
            response = requests.post(
                webhook_url,
                json=trigger_data,
                timeout=30
            )
            results.append({
                "url": webhook_url,
                "status_code": response.status_code,
                "success": response.status_code == 200
            })
        except Exception as e:
            results.append({
                "url": webhook_url,
                "error": str(e),
                "success": False
            })
    
    return results

@router.post("/trigger-workflows")
async def trigger_workflows_manually(
    trigger_data: AIWorkflowTrigger,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """수동으로 n8n 워크플로우 트리거"""
    
    # 관리자 권한 확인
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    
    results = await trigger_ai_analysis_workflows(
        session_id=trigger_data.session_id,
        senior_id=trigger_data.senior_id
    )
    
    return {
        "status": "triggered",
        "session_id": trigger_data.session_id,
        "senior_id": trigger_data.senior_id,
        "workflow_results": results
    }

# ==========================================
# 알림 관련 엔드포인트들
# ==========================================

@router.post("/send-complete-analysis")
async def send_complete_analysis_notification(
    notification_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """분석 완료 알림 발송"""
    
    from ..models.report import Notification
    from ..models.user import Guardian
    
    session_id = notification_data.get("session_id")
    senior_id = notification_data.get("senior_id")
    
    # 시니어의 가디언 찾기
    senior = db.query(Senior).filter(Senior.id == senior_id).first()
    if not senior or not senior.guardian_id:
        return {"status": "skipped", "message": "가디언을 찾을 수 없습니다"}
    
    guardian = db.query(Guardian).filter(Guardian.id == senior.guardian_id).first()
    if not guardian:
        return {"status": "skipped", "message": "가디언 정보를 찾을 수 없습니다"}
    
    # 알림 생성
    notification = Notification(
        sender_id=1,  # 시스템 계정
        receiver_id=guardian.user_id,
        type="complete_ai_analysis",
        title=notification_data.get("title", "이번 주 돌봄 분석 완료"),
        content=notification_data.get("content", "3가지 상태 분석과 가족 소통 제안이 준비되었습니다."),
        data={
            "session_id": session_id,
            "senior_id": senior_id,
            "senior_name": senior.name
        },
        is_read=False
    )
    
    db.add(notification)
    db.commit()
    
    return {
        "status": "success",
        "notification_id": notification.id,
        "message": f"{guardian.name}님에게 알림이 발송되었습니다"
    }

# ==========================================
# 통계 및 모니터링 엔드포인트들
# ==========================================

@router.get("/workflow-statistics")
async def get_workflow_statistics(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """워크플로우 실행 통계"""
    
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    
    # 지난 N일간의 리포트 생성 통계
    since_date = datetime.now() - timedelta(days=days)
    
    total_reports = db.query(AIReport).filter(
        AIReport.created_at >= since_date
    ).count()
    
    # 유형별 리포트 통계
    type_counts = {}
    reports_by_type = db.query(AIReport.report_type, db.func.count(AIReport.id)).filter(
        AIReport.created_at >= since_date
    ).group_by(AIReport.report_type).all()
    
    for report_type, count in reports_by_type:
        type_counts[report_type or 'unknown'] = count
    
    # 주간 점수 통계
    total_weekly_scores = db.query(WeeklyChecklistScore).filter(
        WeeklyChecklistScore.created_at >= since_date
    ).count()
    
    return {
        "period_days": days,
        "total_reports_generated": total_reports,
        "reports_by_type": type_counts,
        "total_weekly_scores": total_weekly_scores,
        "average_reports_per_day": round(total_reports / days, 2) if days > 0 else 0
    }
