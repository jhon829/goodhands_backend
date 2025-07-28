"""
현재 배포된 DB v1.4.0 구조를 활용한 n8n v2.0 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import requests
import random

from ..database import get_db
from ..models.senior import Senior
from ..models.user import User, Guardian
from ..models.care import CareSession, CareNote
from ..models.report import AIReport
from ..services.auth import get_current_user

router = APIRouter()

# ==========================================
# 기존 DB 구조를 활용한 n8n v2.0 엔드포인트들
# ==========================================

@router.get("/checklist-trend-data/{senior_id}/{category_code}")
async def get_checklist_trend_data_v2(
    senior_id: int,
    category_code: str,  # nutrition_common, hypertension, depression
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """기존 weekly_category_scores를 활용한 3주차 추이 데이터 조회"""
    
    # 기존 테이블을 활용하여 데이터 조회
    from sqlalchemy import text
    
    query = text("""
        SELECT 
            wcs.id,
            wcs.senior_id,
            wcs.week_start_date as week_date,
            wcs.total_score,
            wcs.max_possible_score,
            wcs.score_percentage,
            CASE wcs.trend_direction
                WHEN 'improving' THEN 1
                WHEN 'stable' THEN 2  
                WHEN 'declining' THEN 3
                ELSE 2
            END as status_code,
            wcs.created_at
        FROM weekly_category_scores wcs
        JOIN checklist_categories cc ON wcs.category_id = cc.id
        WHERE wcs.senior_id = :senior_id 
        AND cc.category_code = :category_code
        ORDER BY wcs.week_start_date DESC
        LIMIT 3
    """)
    
    result = db.execute(query, {
        "senior_id": senior_id, 
        "category_code": category_code
    }).fetchall()
    
    scores_data = []
    for row in result:
        scores_data.append({
            "id": row.id,
            "senior_id": row.senior_id,
            "week_date": row.week_date,
            "total_score": float(row.total_score),
            "max_possible_score": float(row.max_possible_score),
            "score_percentage": float(row.score_percentage),
            "status_code": row.status_code,
            "created_at": row.created_at
        })
    
    # 카테고리 정보 조회
    category_query = text("""
        SELECT category_code, category_name, max_score 
        FROM checklist_categories 
        WHERE category_code = :category_code
    """)
    
    category_result = db.execute(category_query, {"category_code": category_code}).fetchone()
    
    return {
        "senior_id": senior_id,
        "checklist_type": {
            "code": category_code,
            "name": category_result.category_name if category_result else "",
            "max_score": category_result.max_score if category_result else 16
        },
        "recent_scores": scores_data,
        "weeks_available": len(scores_data)
    }

@router.post("/calculate-weekly-scores-v2")
async def calculate_weekly_scores_v2(
    session_data: dict,
    db: Session = Depends(get_db)
):
    """기존 weekly_category_scores 테이블을 활용한 주간 점수 계산"""
    
    session_id = session_data.get("session_id")
    senior_id = session_data.get("senior_id")
    week_date = session_data.get("week_date", date.today())
    
    # 3가지 카테고리별 점수 계산
    from sqlalchemy import text
    
    categories_query = text("""
        SELECT id, category_code, category_name, max_score 
        FROM checklist_categories 
        WHERE category_code IN ('nutrition_common', 'hypertension', 'depression')
    """)
    
    categories = db.execute(categories_query).fetchall()
    calculated_scores = []
    
    for category in categories:
        # 해당 카테고리의 체크리스트 응답 조회
        responses_query = text("""
            SELECT cr.scale_value, cr.max_scale_value
            FROM checklist_responses cr
            JOIN checklist_questions cq ON cr.question_id = cq.id
            WHERE cr.care_session_id = :session_id 
            AND cq.category_id = :category_id
            AND cr.scale_value IS NOT NULL
        """)
        
        responses_result = db.execute(responses_query, {
            "session_id": session_id,
            "category_id": category.id
        }).fetchall()
        
        if not responses_result:
            continue
            
        # 점수 합계 계산
        total_score = sum([r.scale_value for r in responses_result if r.scale_value])
        max_score = category.max_score
        score_percentage = (total_score / max_score) * 100 if max_score > 0 else 0
        
        # 지난 주 점수와 비교하여 트렌드 결정
        last_week_query = text("""
            SELECT total_score, trend_direction
            FROM weekly_category_scores
            WHERE senior_id = :senior_id AND category_id = :category_id
            ORDER BY week_start_date DESC
            LIMIT 1
        """)
        
        last_week_result = db.execute(last_week_query, {
            "senior_id": senior_id,
            "category_id": category.id
        }).fetchone()
        
        trend_direction = "stable"
        status_code = 2  # 유지
        
        if last_week_result:
            if total_score > float(last_week_result.total_score):
                trend_direction = "improving"
                status_code = 1  # 개선
            elif total_score < float(last_week_result.total_score):
                trend_direction = "declining"
                status_code = 3  # 악화
        
        # 기존 테이블에 저장 (간소화된 형태)
        insert_query = text("""
            INSERT INTO weekly_category_scores 
            (senior_id, caregiver_id, category_id, week_start_date, week_end_date,
             total_score, max_possible_score, score_percentage, question_count, 
             completed_questions, trend_direction, risk_level)
            VALUES 
            (:senior_id, :caregiver_id, :category_id, :week_start, :week_end,
             :total_score, :max_score, :score_percentage, :question_count,
             :completed_questions, :trend_direction, :risk_level)
        """)
        
        week_start = week_date if isinstance(week_date, date) else datetime.strptime(week_date, '%Y-%m-%d').date()
        week_end = week_start + timedelta(days=6)
        
        # 케어기버 ID 조회
        caregiver_query = text("""
            SELECT caregiver_id FROM care_sessions WHERE id = :session_id
        """)
        caregiver_result = db.execute(caregiver_query, {"session_id": session_id}).fetchone()
        caregiver_id = caregiver_result.caregiver_id if caregiver_result else 1
        
        db.execute(insert_query, {
            "senior_id": senior_id,
            "caregiver_id": caregiver_id,
            "category_id": category.id,
            "week_start": week_start,
            "week_end": week_end,
            "total_score": total_score,
            "max_score": max_score,
            "score_percentage": score_percentage,
            "question_count": len(responses_result),
            "completed_questions": len(responses_result),
            "trend_direction": trend_direction,
            "risk_level": "normal" if score_percentage >= 70 else "caution"
        })
        
        calculated_scores.append({
            "category_code": category.category_code,
            "total_score": total_score,
            "max_possible_score": max_score,
            "score_percentage": score_percentage,
            "status_code": status_code,
            "trend_direction": trend_direction
        })
    
    db.commit()
    return {"status": "success", "scores": calculated_scores}

@router.get("/random-care-question")
async def get_random_care_question_v2(
    db: Session = Depends(get_db)
):
    """랜덤 돌봄노트 질문 1개 선택 (새 테이블 활용)"""
    
    from sqlalchemy import text
    
    questions_query = text("""
        SELECT id, question_number, question_title, question_text, guide_text, examples
        FROM care_note_questions 
        WHERE is_active = 1
    """)
    
    questions_result = db.execute(questions_query).fetchall()
    
    if not questions_result:
        raise HTTPException(status_code=404, detail="활성화된 질문이 없습니다")
    
    # 랜덤 선택
    selected_question = random.choice(questions_result)
    
    return {
        "question_id": selected_question.id,
        "question_number": selected_question.question_number,
        "question_title": selected_question.question_title,
        "question_text": selected_question.question_text,
        "guide_text": selected_question.guide_text,
        "examples": selected_question.examples
    }

@router.get("/care-note-data/{session_id}")
async def get_care_note_data_v2(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """돌봄노트 데이터 조회 (기존 + 새 구조 활용)"""
    
    # 세션 정보
    session = db.query(CareSession).filter(CareSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    
    # 돌봄노트 조회 (새 컬럼 포함)
    care_note = db.query(CareNote).filter(
        CareNote.care_session_id == session_id
    ).first()
    
    if not care_note:
        raise HTTPException(status_code=404, detail="돌봄노트를 찾을 수 없습니다")
    
    # 질문 정보 조회 (새 테이블에서)
    question_info = None
    if care_note.selected_question_id:
        from sqlalchemy import text
        
        question_query = text("""
            SELECT question_title, question_text, guide_text 
            FROM care_note_questions 
            WHERE id = :question_id
        """)
        
        question_result = db.execute(question_query, {
            "question_id": care_note.selected_question_id
        }).fetchone()
        
        if question_result:
            question_info = {
                "question_title": question_result.question_title,
                "question_text": question_result.question_text,
                "guide_text": question_result.guide_text
            }
    
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
        "question_info": question_info or {
            "question_title": "",
            "question_text": "",
            "guide_text": ""
        },
        "senior_info": {
            "name": senior.name,
            "age": senior.age,
            "gender": senior.gender
        } if senior else None
    }

@router.post("/save-type-reports-v2")
async def save_type_reports_v2(
    report_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """유형별 AI 리포트 저장 (기존 ai_reports 테이블 활용)"""
    
    session_id = report_data.get("session_id")
    senior_id = report_data.get("senior_id")
    reports = report_data.get("reports", [])
    
    saved_reports = []
    
    for report in reports:
        ai_report = AIReport(
            care_session_id=session_id,
            senior_id=senior_id,
            report_type=report["report_type"],
            checklist_type_code=report.get("checklist_type_code"),
            content=report["content"],
            status_code=report.get("status_code"),
            trend_analysis=report.get("trend_analysis"),
            keywords=[],
            ai_comment="",
            status="generated"
        )
        
        db.add(ai_report)
        db.flush()
        saved_reports.append(ai_report.id)
    
    db.commit()
    
    return {
        "status": "success",
        "session_id": session_id,
        "saved_report_ids": saved_reports,
        "message": f"{len(saved_reports)}개의 유형별 리포트가 저장되었습니다"
    }

@router.post("/save-care-comment-v2")
async def save_care_comment_v2(
    comment_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """돌봄노트 기반 AI 코멘트 저장"""
    
    session_id = comment_data.get("session_id")
    
    # 기존 테이블 구조 활용
    ai_report = AIReport(
        care_session_id=session_id,
        report_type="care_note_comment",
        checklist_type_code=None,
        content="가족 소통 코멘트",
        ai_comment=comment_data.get("ai_comment"),
        status_code=None,
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
async def get_session_reports_v2(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """세션의 모든 AI 리포트 조회 (기존 구조 활용)"""
    
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
    
    return {
        "session_id": session_id,
        "senior_id": senior_id,
        "reports": report_data,
        "processing_status": "completed" if len(reports) >= 4 else "processing"
    }

# ==========================================
# n8n 워크플로우 트리거
# ==========================================

async def trigger_ai_analysis_workflows_v2(session_id: int, senior_id: int):
    """n8n AI 분석 워크플로우 v2.0 트리거 (기존 구조 활용)"""
    
    webhook_base_url = "http://pay.gzonesoft.co.kr:10006/webhook"
    
    trigger_data = {
        "session_id": session_id,
        "senior_id": senior_id,
        "trigger_time": datetime.now().isoformat(),
        "db_version": "1.4.0"  # 현재 DB 버전 표시
    }
    
    try:
        response = requests.post(
            f"{webhook_base_url}/complete-ai-analysis",
            json=trigger_data,
            timeout=30
        )
        print(f"n8n v2.0 워크플로우 트리거 성공: {response.status_code}")
        return {"status": "triggered", "session_id": session_id}
    except Exception as e:
        print(f"n8n v2.0 워크플로우 트리거 실패: {e}")
        return {"status": "failed", "error": str(e)}

@router.post("/trigger-workflows")
async def trigger_workflows_manually_v2(
    trigger_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """수동으로 n8n 워크플로우 트리거 (테스트용)"""
    
    session_id = trigger_data.get("session_id")
    senior_id = trigger_data.get("senior_id")
    
    if not session_id or not senior_id:
        raise HTTPException(status_code=400, detail="session_id와 senior_id가 필요합니다")
    
    results = await trigger_ai_analysis_workflows_v2(session_id, senior_id)
    
    return {
        "status": "triggered",
        "session_id": session_id,
        "senior_id": senior_id,
        "workflow_results": results,
        "db_version": "1.4.0"
    }
