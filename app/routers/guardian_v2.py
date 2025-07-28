"""
가디언을 위한 n8n v2.0 리포트 조회 엔드포인트 추가
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, date

from ..database import get_db
from ..models.care import WeeklyChecklistScore, ChecklistType
from ..models.report import AIReport
from ..models.senior import Senior
from ..models.user import Guardian, User
from ..services.auth import get_current_user

router = APIRouter()

@router.get("/reports/session/{session_id}/v2")
async def get_v2_session_reports(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """세션의 v2.0 AI 리포트들 조회 (4개 리포트)"""
    
    # 가디언 권한 확인
    guardian = db.query(Guardian).filter(Guardian.user_id == current_user.id).first()
    if not guardian:
        raise HTTPException(status_code=404, detail="가디언 정보를 찾을 수 없습니다")
    
    # 해당 세션의 모든 리포트 조회
    reports = db.query(AIReport).filter(
        AIReport.care_session_id == session_id
    ).order_by(AIReport.created_at.desc()).all()
    
    # 4가지 유형별로 분류
    report_types = {
        "nutrition_report": None,
        "hypertension_report": None,
        "depression_report": None,
        "care_note_comment": None
    }
    
    for report in reports:
        if report.report_type in report_types:
            report_types[report.report_type] = {
                "id": report.id,
                "content": report.content,
                "ai_comment": report.ai_comment,
                "status_code": report.status_code,
                "trend_analysis": report.trend_analysis,
                "created_at": report.created_at.isoformat()
            }
    
    return {
        "session_id": session_id,
        "reports": report_types,
        "total_reports": len([r for r in report_types.values() if r is not None]),
        "is_complete": len([r for r in report_types.values() if r is not None]) >= 4
    }

@router.get("/seniors/{senior_id}/weekly-trends")
async def get_senior_weekly_trends(
    senior_id: int,
    weeks: int = 4,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """시니어의 주간별 상태 추이 조회"""
    
    # 가디언 권한 확인
    guardian = db.query(Guardian).filter(Guardian.user_id == current_user.id).first()
    if not guardian:
        raise HTTPException(status_code=404, detail="가디언 정보를 찾을 수 없습니다")
    
    # 시니어가 가디언의 담당인지 확인
    senior = db.query(Senior).filter(
        Senior.id == senior_id,
        Senior.guardian_id == guardian.id
    ).first()
    
    if not senior:
        raise HTTPException(status_code=404, detail="해당 시니어 정보를 찾을 수 없습니다")
    
    # 최근 N주 주간 점수 조회
    from datetime import timedelta
    since_date = date.today() - timedelta(weeks=weeks)
    
    weekly_scores = db.query(WeeklyChecklistScore).filter(
        WeeklyChecklistScore.senior_id == senior_id,
        WeeklyChecklistScore.week_date >= since_date
    ).order_by(
        WeeklyChecklistScore.week_date.desc(),
        WeeklyChecklistScore.checklist_type_code
    ).all()
    
    # 유형별로 그룹화
    trends_by_type = {}
    for score in weekly_scores:
        type_code = score.checklist_type_code
        if type_code not in trends_by_type:
            trends_by_type[type_code] = []
        
        trends_by_type[type_code].append({
            "week_date": score.week_date.isoformat(),
            "total_score": score.total_score,
            "max_possible_score": score.max_possible_score,
            "score_percentage": float(score.score_percentage),
            "status_code": score.status_code,
            "status_text": {1: "개선", 2: "유지", 3: "악화"}.get(score.status_code, "알 수 없음")
        })
    
    # 체크리스트 유형 정보 추가
    checklist_types = db.query(ChecklistType).all()
    type_names = {ct.type_code: ct.type_name for ct in checklist_types}
    
    result = {}
    for type_code, scores in trends_by_type.items():
        result[type_code] = {
            "type_name": type_names.get(type_code, type_code),
            "scores": scores,
            "current_status": scores[0]["status_text"] if scores else "데이터 없음",
            "trend_direction": _calculate_trend_direction(scores)
        }
    
    return {
        "senior_id": senior_id,
        "senior_name": senior.name,
        "period_weeks": weeks,
        "trends_by_type": result
    }

@router.get("/seniors/{senior_id}/latest-status")
async def get_senior_latest_status(
    senior_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """시니어의 최신 상태 요약 조회"""
    
    # 가디언 권한 확인
    guardian = db.query(Guardian).filter(Guardian.user_id == current_user.id).first()
    if not guardian:
        raise HTTPException(status_code=404, detail="가디언 정보를 찾을 수 없습니다")
    
    # 시니어 확인
    senior = db.query(Senior).filter(
        Senior.id == senior_id,
        Senior.guardian_id == guardian.id
    ).first()
    
    if not senior:
        raise HTTPException(status_code=404, detail="해당 시니어 정보를 찾을 수 없습니다")
    
    # 최신 주간 점수 조회 (유형별)
    latest_scores = {}
    for type_code in ["nutrition", "hypertension", "depression"]:
        latest_score = db.query(WeeklyChecklistScore).filter(
            WeeklyChecklistScore.senior_id == senior_id,
            WeeklyChecklistScore.checklist_type_code == type_code
        ).order_by(WeeklyChecklistScore.week_date.desc()).first()
        
        if latest_score:
            latest_scores[type_code] = {
                "score_percentage": float(latest_score.score_percentage),
                "status_code": latest_score.status_code,
                "status_text": {1: "개선", 2: "유지", 3: "악화"}.get(latest_score.status_code, "알 수 없음"),
                "week_date": latest_score.week_date.isoformat()
            }
    
    # 최신 AI 코멘트 조회
    latest_comment = db.query(AIReport).filter(
        AIReport.report_type == "care_note_comment"
    ).join(
        # CareSession과 조인하여 senior_id로 필터링
        # 실제 구현에서는 적절한 조인 로직 필요
    ).order_by(AIReport.created_at.desc()).first()
    
    # 체크리스트 유형 정보
    checklist_types = db.query(ChecklistType).all()
    type_names = {ct.type_code: ct.type_name for ct in checklist_types}
    
    # 전반적 상태 계산
    overall_status = _calculate_overall_status(latest_scores)
    
    return {
        "senior_id": senior_id,
        "senior_name": senior.name,
        "overall_status": overall_status,
        "type_scores": {
            type_code: {
                "type_name": type_names.get(type_code, type_code),
                **score_data
            }
            for type_code, score_data in latest_scores.items()
        },
        "latest_ai_comment": {
            "content": latest_comment.ai_comment if latest_comment else None,
            "created_at": latest_comment.created_at.isoformat() if latest_comment else None
        },
        "last_updated": max([
            datetime.fromisoformat(score["week_date"]) 
            for score in latest_scores.values()
        ]).isoformat() if latest_scores else None
    }

@router.get("/reports/summary")
async def get_reports_summary(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """가디언의 최근 리포트 요약 조회"""
    
    # 가디언 정보 조회
    guardian = db.query(Guardian).filter(Guardian.user_id == current_user.id).first()
    if not guardian:
        raise HTTPException(status_code=404, detail="가디언 정보를 찾을 수 없습니다")
    
    # 담당 시니어들
    seniors = db.query(Senior).filter(Senior.guardian_id == guardian.id).all()
    senior_ids = [s.id for s in seniors]
    
    if not senior_ids:
        return {
            "message": "담당 시니어가 없습니다",
            "seniors": [],
            "total_reports": 0
        }
    
    # 최근 N일간의 리포트 통계
    from datetime import timedelta
    since_date = datetime.now() - timedelta(days=days)
    
    # 각 시니어별 리포트 통계 계산
    seniors_summary = []
    total_reports = 0
    
    for senior in seniors:
        # 해당 시니어의 최근 리포트 수
        recent_reports_count = db.query(AIReport).join(
            # CareSession 조인 필요
        ).filter(
            AIReport.created_at >= since_date
        ).count()
        
        # 최신 상태 코드들
        latest_status_codes = {}
        for type_code in ["nutrition", "hypertension", "depression"]:
            latest_score = db.query(WeeklyChecklistScore).filter(
                WeeklyChecklistScore.senior_id == senior.id,
                WeeklyChecklistScore.checklist_type_code == type_code
            ).order_by(WeeklyChecklistScore.week_date.desc()).first()
            
            if latest_score:
                latest_status_codes[type_code] = latest_score.status_code
        
        seniors_summary.append({
            "senior_id": senior.id,
            "senior_name": senior.name,
            "recent_reports_count": recent_reports_count,
            "latest_status_codes": latest_status_codes,
            "overall_trend": _calculate_senior_trend(latest_status_codes)
        })
        
        total_reports += recent_reports_count
    
    return {
        "guardian_name": guardian.name,
        "period_days": days,
        "seniors": seniors_summary,
        "total_reports": total_reports,
        "total_seniors": len(seniors)
    }

def _calculate_trend_direction(scores: List[Dict]) -> str:
    """점수 리스트에서 트렌드 방향 계산"""
    if len(scores) < 2:
        return "데이터 부족"
    
    # 최신 2개 점수 비교
    latest = scores[0]["score_percentage"]
    previous = scores[1]["score_percentage"]
    
    diff = latest - previous
    
    if diff > 5:
        return "상승"
    elif diff < -5:
        return "하락"
    else:
        return "안정"

def _calculate_overall_status(latest_scores: Dict) -> str:
    """전반적 상태 계산"""
    if not latest_scores:
        return "데이터 없음"
    
    # 평균 점수 계산
    avg_percentage = sum([
        score["score_percentage"] 
        for score in latest_scores.values()
    ]) / len(latest_scores)
    
    # 상태 코드 분포 확인
    status_codes = [score["status_code"] for score in latest_scores.values()]
    improving_count = status_codes.count(1)
    declining_count = status_codes.count(3)
    
    if avg_percentage >= 80 and declining_count == 0:
        return "좋음"
    elif avg_percentage >= 60 and improving_count >= declining_count:
        return "보통"
    else:
        return "주의 필요"

def _calculate_senior_trend(status_codes: Dict) -> str:
    """시니어의 전반적 트렌드 계산"""
    if not status_codes:
        return "데이터 없음"
    
    improving = sum([1 for code in status_codes.values() if code == 1])
    declining = sum([1 for code in status_codes.values() if code == 3])
    
    if improving > declining:
        return "개선"
    elif declining > improving:
        return "악화"
    else:
        return "안정"
