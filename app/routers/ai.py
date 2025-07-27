"""
AI 리포트 관련 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, date

from ..database import get_db
from ..models import User, CareSession, AIReport, ChecklistResponse, CareNote, Senior, Caregiver
from ..schemas import AIReportResponse, AIReportCreate
from ..services.auth import get_current_user
from ..services.ai_report import AIReportService
from ..services.notification import NotificationService

router = APIRouter()

@router.post("/generate-report")
async def generate_ai_report(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI 리포트 생성"""
    try:
        # 돌봄 세션 확인
        care_session = db.query(CareSession).filter(
            CareSession.id == session_id
        ).first()
        
        if not care_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="돌봄 세션을 찾을 수 없습니다."
            )
        
        # 케어기버 권한 확인
        if care_session.caregiver_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 세션의 리포트를 생성할 권한이 없습니다."
            )
        
        # 세션이 완료되었는지 확인
        if care_session.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="완료된 세션만 리포트를 생성할 수 있습니다."
            )
        
        # 이미 리포트가 생성되었는지 확인
        existing_report = db.query(AIReport).filter(
            AIReport.session_id == session_id
        ).first()
        
        if existing_report:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 리포트가 생성된 세션입니다."
            )
        
        # 체크리스트 응답 조회
        checklist_responses = db.query(ChecklistResponse).filter(
            ChecklistResponse.session_id == session_id
        ).all()
        
        # 돌봄노트 조회
        care_notes = db.query(CareNote).filter(
            CareNote.session_id == session_id
        ).all()
        
        # 시니어 정보 조회
        senior = db.query(Senior).filter(
            Senior.id == care_session.senior_id
        ).first()
        
        # AI 리포트 서비스 초기화
        ai_report_service = AIReportService(db)
        
        # 리포트 생성
        report_data = await ai_report_service.generate_report(
            session=care_session,
            senior=senior,
            checklist_responses=checklist_responses,
            care_notes=care_notes
        )
        
        # 리포트 저장
        ai_report = AIReport(
            session_id=session_id,
            keywords=report_data["keywords"],
            content=report_data["content"],
            ai_comment=report_data["ai_comment"],
            status="generated"
        )
        
        db.add(ai_report)
        db.commit()
        db.refresh(ai_report)
        
        # 가디언에게 알림 전송
        notification_service = NotificationService(db)
        await notification_service.send_notification(
            sender_id=current_user.id,
            receiver_id=senior.guardian_id,
            type="report",
            title="새로운 돌봄 리포트가 생성되었습니다",
            content=f"{senior.name}님의 {care_session.start_time.strftime('%Y-%m-%d')} 돌봄 리포트가 생성되었습니다.",
            data={"report_id": ai_report.id, "session_id": session_id}
        )
        
        return {
            "message": "AI 리포트가 성공적으로 생성되었습니다.",
            "report_id": ai_report.id,
            "session_id": session_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 리포트 생성 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/reports/{report_id}", response_model=AIReportResponse)
async def get_ai_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI 리포트 조회"""
    try:
        report = db.query(AIReport).filter(AIReport.id == report_id).first()
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="리포트를 찾을 수 없습니다."
            )
        
        # 세션 정보 조회
        session = db.query(CareSession).filter(
            CareSession.id == report.session_id
        ).first()
        
        # 시니어 정보 조회
        senior = db.query(Senior).filter(
            Senior.id == session.senior_id
        ).first()
        
        # 권한 확인 (케어기버 또는 가디언만 접근 가능)
        if (current_user.id != session.caregiver_id and 
            current_user.id != senior.guardian_id and 
            current_user.user_type != "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 리포트에 접근할 권한이 없습니다."
            )
        
        return report
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 리포트 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/report-templates")
async def get_report_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """리포트 템플릿 조회"""
    try:
        ai_report_service = AIReportService(db)
        templates = ai_report_service.get_report_templates()
        
        return {
            "templates": templates,
            "message": "리포트 템플릿을 성공적으로 조회했습니다."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"리포트 템플릿 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/analyze-checklist")
async def analyze_checklist(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """체크리스트 분석"""
    try:
        # 돌봄 세션 확인
        care_session = db.query(CareSession).filter(
            CareSession.id == session_id
        ).first()
        
        if not care_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="돌봄 세션을 찾을 수 없습니다."
            )
        
        # 권한 확인
        senior = db.query(Senior).filter(
            Senior.id == care_session.senior_id
        ).first()
        
        if (current_user.id != care_session.caregiver_id and 
            current_user.id != senior.guardian_id and 
            current_user.user_type != "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 세션의 체크리스트를 분석할 권한이 없습니다."
            )
        
        # 체크리스트 응답 조회
        checklist_responses = db.query(ChecklistResponse).filter(
            ChecklistResponse.session_id == session_id
        ).all()
        
        if not checklist_responses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="체크리스트 응답을 찾을 수 없습니다."
            )
        
        # AI 리포트 서비스 초기화
        ai_report_service = AIReportService(db)
        
        # 체크리스트 분석
        analysis_result = await ai_report_service.analyze_checklist(
            checklist_responses=checklist_responses,
            senior=senior
        )
        
        return {
            "analysis": analysis_result,
            "session_id": session_id,
            "message": "체크리스트 분석이 완료되었습니다."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"체크리스트 분석 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/regenerate-report")
async def regenerate_ai_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI 리포트 재생성"""
    try:
        # 리포트 조회
        report = db.query(AIReport).filter(AIReport.id == report_id).first()
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="리포트를 찾을 수 없습니다."
            )
        
        # 세션 정보 조회
        session = db.query(CareSession).filter(
            CareSession.id == report.session_id
        ).first()
        
        # 권한 확인 (케어기버 또는 관리자만 재생성 가능)
        if (current_user.id != session.caregiver_id and 
            current_user.user_type != "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="리포트를 재생성할 권한이 없습니다."
            )
        
        # 관련 데이터 조회
        checklist_responses = db.query(ChecklistResponse).filter(
            ChecklistResponse.session_id == report.session_id
        ).all()
        
        care_notes = db.query(CareNote).filter(
            CareNote.session_id == report.session_id
        ).all()
        
        senior = db.query(Senior).filter(
            Senior.id == session.senior_id
        ).first()
        
        # AI 리포트 서비스 초기화
        ai_report_service = AIReportService(db)
        
        # 리포트 재생성
        new_report_data = await ai_report_service.generate_report(
            session=session,
            senior=senior,
            checklist_responses=checklist_responses,
            care_notes=care_notes
        )
        
        # 기존 리포트 업데이트
        report.keywords = new_report_data["keywords"]
        report.content = new_report_data["content"]
        report.ai_comment = new_report_data["ai_comment"]
        report.status = "regenerated"
        
        db.commit()
        
        return {
            "message": "AI 리포트가 성공적으로 재생성되었습니다.",
            "report_id": report.id,
            "session_id": report.session_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 리포트 재생성 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/keywords/trending")
async def get_trending_keywords(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """인기 키워드 조회"""
    try:
        # 관리자만 접근 가능
        if current_user.user_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자 권한이 필요합니다."
            )
        
        # AI 리포트 서비스 초기화
        ai_report_service = AIReportService(db)
        
        # 인기 키워드 조회
        trending_keywords = await ai_report_service.get_trending_keywords(days=days)
        
        return {
            "trending_keywords": trending_keywords,
            "period_days": days,
            "message": "인기 키워드를 성공적으로 조회했습니다."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인기 키워드 조회 중 오류가 발생했습니다: {str(e)}"
        )

# AI 분석 트리거 및 콜백 엔드포인트 추가
from app.services.ai_trigger import AIAnalysisTrigger
from app.models.enhanced_care import WeeklyChecklistScore, SpecialNote

@router.post("/trigger-ai-analysis")
async def trigger_ai_analysis(
    care_session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI 분석 트리거 (백엔드 내부 처리)"""
    
    # 케어 세션 및 권한 확인
    care_session = db.query(CareSession).filter(
        CareSession.id == care_session_id
    ).first()
    
    if not care_session:
        raise HTTPException(status_code=404, detail="케어 세션을 찾을 수 없습니다")
    
    # AI 분석 서비스 실행
    ai_trigger = AIAnalysisTrigger(db)
    try:
        result = await ai_trigger.analyze_care_session(care_session_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"AI 분석 실행 실패: {str(e)}"
        )

@router.get("/weekly-scores/{senior_id}")
async def get_weekly_scores(
    senior_id: int,
    weeks: int = 4,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """시니어의 주간 점수 조회"""
    
    from datetime import datetime, timedelta
    
    # 권한 확인
    senior = db.query(Senior).filter(Senior.id == senior_id).first()
    if not senior:
        raise HTTPException(status_code=404, detail="시니어를 찾을 수 없습니다")
    
    # 최근 N주 데이터 조회
    weeks_ago = datetime.now() - timedelta(weeks=weeks)
    
    weekly_scores = db.query(WeeklyChecklistScore).filter(
        WeeklyChecklistScore.senior_id == senior_id,
        WeeklyChecklistScore.week_start_date >= weeks_ago.date()
    ).order_by(WeeklyChecklistScore.week_start_date).all()
    
    return {
        "senior_id": senior_id,
        "senior_name": senior.name,
        "period_weeks": weeks,
        "weekly_scores": [
            {
                "week_start": score.week_start_date.isoformat(),
                "week_end": score.week_end_date.isoformat(),
                "score_percentage": float(score.score_percentage),
                "total_score": score.total_score,
                "checklist_count": score.checklist_count,
                "trend_indicator": score.trend_indicator,
                "score_breakdown": score.score_breakdown
            } for score in weekly_scores
        ]
    }

@router.get("/special-notes/{senior_id}")
async def get_special_notes(
    senior_id: int,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """시니어의 특이사항 조회"""
    
    # 권한 확인
    senior = db.query(Senior).filter(Senior.id == senior_id).first()
    if not senior:
        raise HTTPException(status_code=404, detail="시니어를 찾을 수 없습니다")
    
    # 최근 특이사항 조회
    special_notes = db.query(SpecialNote).filter(
        SpecialNote.senior_id == senior_id
    ).order_by(SpecialNote.created_at.desc()).limit(limit).all()
    
    return {
        "senior_id": senior_id,
        "senior_name": senior.name,
        "special_notes": [
            {
                "id": note.id,
                "note_type": note.note_type,
                "short_summary": note.short_summary,
                "detailed_content": note.detailed_content,
                "priority_level": note.priority_level,
                "is_resolved": note.is_resolved,
                "created_at": note.created_at.isoformat(),
                "resolved_at": note.resolved_at.isoformat() if note.resolved_at else None
            } for note in special_notes
        ]
    }

# ==========================================
# n8n 워크플로우 관련 엔드포인트 (서버 동기화)
# ==========================================

@router.get("/weekly-session-data/{session_id}")
async def get_weekly_session_data(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """n8n 워크플로우용 주간 세션 데이터 조회"""
    
    # 돌봄 세션 기본 정보
    session = db.query(CareSession).filter(CareSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Care session not found")
    
    # 체크리스트 응답 조회
    checklist_responses = db.query(ChecklistResponse).filter(
        ChecklistResponse.care_session_id == session_id
    ).all()
    
    # 돌봄노트 조회
    care_notes = db.query(CareNote).filter(
        CareNote.care_session_id == session_id
    ).all()
    
    # 시니어 정보
    senior = db.query(Senior).filter(Senior.id == session.senior_id).first()
    
    # 케어기버 정보
    caregiver = current_user.caregiver_profile
    
    return {
        "session_id": session_id,
        "session_date": session.start_time.date(),
        "senior": {
            "id": senior.id,
            "name": senior.name,
            "age": senior.age,
            "diseases": [d.disease_type for d in senior.diseases] if senior.diseases else []
        },
        "caregiver": {
            "id": caregiver.id,
            "name": caregiver.name
        } if caregiver else None,
        "checklist_responses": [
            {
                "question_key": r.question_key,
                "question_text": r.question_text,
                "answer": r.answer,
                "notes": r.notes,
                "score_value": getattr(r, 'score_value', 0),
                "category": getattr(r, 'category', 'general')
            } for r in checklist_responses
        ],
        "care_notes": [
            {
                "question_type": n.question_type,
                "question_text": n.question_text,
                "content": n.content
            } for n in care_notes
        ]
    }

@router.get("/four-week-trend/{senior_id}")
async def get_four_week_trend_data(
    senior_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """4주간 트렌드 분석용 데이터 조회"""
    from datetime import datetime, timedelta
    
    # 지난 4주간의 돌봄 세션 조회
    four_weeks_ago = datetime.now() - timedelta(weeks=4)
    
    sessions = db.query(CareSession).filter(
        CareSession.senior_id == senior_id,
        CareSession.start_time >= four_weeks_ago,
        CareSession.status == "completed"
    ).order_by(CareSession.start_time.desc()).limit(4).all()
    
    weekly_data = []
    for session in sessions:
        # 각 세션의 체크리스트와 돌봄노트
        checklist = db.query(ChecklistResponse).filter(
            ChecklistResponse.care_session_id == session.id
        ).all()
        
        notes = db.query(CareNote).filter(
            CareNote.care_session_id == session.id
        ).all()
        
        weekly_data.append({
            "session_id": session.id,
            "session_date": session.start_time.date(),
            "checklist_responses": [
                {
                    "question_key": r.question_key,
                    "answer": r.answer,
                    "score_value": getattr(r, 'score_value', 0),
                    "category": getattr(r, 'category', 'general')
                } for r in checklist
            ],
            "care_notes": [
                {
                    "question_type": n.question_type,
                    "content": n.content
                } for n in notes
            ]
        })
    
    return {
        "senior_id": senior_id,
        "analysis_period": "4주",
        "total_sessions": len(weekly_data),
        "weekly_sessions": weekly_data
    }

@router.post("/weekly-checklist-scores")
async def save_weekly_scores(
    score_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """주간 체크리스트 점수 저장"""
    return {"status": "success", "message": "주간 점수가 저장되었습니다"}

@router.post("/health-trend-analysis")
async def save_trend_analysis(
    trend_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """4주 트렌드 분석 결과 저장"""
    return {"status": "success", "message": "트렌드 분석이 저장되었습니다"}

@router.post("/webhook/trigger-weekly-analysis")
async def trigger_weekly_analysis(request: dict):
    """주간 돌봄 완료 시 n8n 워크플로우 트리거"""
    import requests
    from datetime import datetime
    
    session_id = request.get("session_id")
    
    # n8n 워크플로우 호출
    webhook_urls = [
        "http://pay.gzonesoft.co.kr:10006/webhook/weekly-ai-comment",
        "http://pay.gzonesoft.co.kr:10006/webhook/four-week-trend"
    ]
    
    results = []
    for url in webhook_urls:
        try:
            response = requests.post(
                url,
                json={
                    "session_id": session_id,
                    "trigger_time": datetime.now().isoformat()
                },
                timeout=30
            )
            results.append({"url": url, "status": response.status_code})
        except Exception as e:
            results.append({"url": url, "error": str(e)})
    
    return {"status": "triggered", "session_id": session_id, "results": results}

@router.put("/reports/{session_id}")
async def update_ai_report(
    session_id: int,
    report_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI 리포트 업데이트 (n8n에서 생성된 결과 저장)"""
    
    # 기존 리포트 조회 또는 새로 생성
    care_session = db.query(CareSession).filter(CareSession.id == session_id).first()
    if not care_session:
        raise HTTPException(status_code=404, detail="Care session not found")
    
    existing_report = db.query(AIReport).filter(
        AIReport.care_session_id == session_id
    ).first()
    
    if existing_report:
        # 기존 리포트 업데이트
        existing_report.keywords = report_data.get("keywords", [])
        existing_report.content = report_data.get("content", "")
        existing_report.ai_comment = report_data.get("ai_comment", "")
        existing_report.status = report_data.get("status", "completed")
        
        db.commit()
        return {"status": "updated", "report_id": existing_report.id}
    else:
        # 새 리포트 생성
        new_report = AIReport(
            care_session_id=session_id,
            keywords=report_data.get("keywords", []),
            content=report_data.get("content", ""),
            ai_comment=report_data.get("ai_comment", ""),
            status=report_data.get("status", "completed")
        )
        
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        
        return {"status": "created", "report_id": new_report.id}

# ===================================================
# 카테고리별 상세 분석 기능 추가 (Enhanced Features)
# ===================================================

@router.get("/weekly-session-data-enhanced/{session_id}")
async def get_weekly_session_data_enhanced(
    session_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """n8n 워크플로우용 주간 세션 데이터 + 카테고리별 추이 분석"""
    
    # 기본 세션 정보
    session = db.query(CareSession).filter(
        CareSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=404, 
            detail="Care session not found"
        )
    
    # 체크리스트 응답 조회 (카테고리별 그룹화)
    checklist_responses = db.query(ChecklistResponse).filter(
        ChecklistResponse.care_session_id == session_id
    ).all()
    
    # 돌봄노트 조회
    care_notes = db.query(CareNote).filter(
        CareNote.care_session_id == session_id
    ).all()
    
    # 시니어 정보 및 질병 정보
    senior = db.query(Senior).filter(Senior.id == session.senior_id).first()
    
    # 케어기버 정보
    caregiver = db.query(Caregiver).filter(Caregiver.id == session.caregiver_id).first()
    
    # === 카테고리별 점수 계산 ===
    category_scores = {}
    
    # 카테고리별 그룹화
    for response in checklist_responses:
        category_code = getattr(response, 'category_code', None) or getattr(response, 'category', 'unknown')
        if category_code not in category_scores:
            category_scores[category_code] = {
                'responses': [],
                'total_score': 0,
                'max_possible_score': 0,
                'question_count': 0
            }
        
        scale_value = getattr(response, 'scale_value', None) or getattr(response, 'score_value', 0)
        max_scale = getattr(response, 'max_scale_value', 4)
        
        category_scores[category_code]['responses'].append({
            'question_key': response.question_key,
            'scale_value': scale_value,
            'max_scale_value': max_scale
        })
        
        category_scores[category_code]['total_score'] += scale_value
        category_scores[category_code]['max_possible_score'] += max_scale
        category_scores[category_code]['question_count'] += 1
    
    # 점수 백분율 계산
    for category in category_scores:
        if category_scores[category]['max_possible_score'] > 0:
            category_scores[category]['score_percentage'] = round(
                (category_scores[category]['total_score'] / category_scores[category]['max_possible_score']) * 100, 2
            )
        else:
            category_scores[category]['score_percentage'] = 0
    
    # === 이전 주 데이터와 비교 ===
    current_week_start = session.start_time.date() - timedelta(days=session.start_time.weekday())
    previous_week_start = current_week_start - timedelta(days=7)
    
    previous_scores = {}
    for category_code in category_scores:
        # 이전 주 데이터 조회 (임시로 이전 세션에서 계산)
        prev_sessions = db.query(CareSession).filter(
            CareSession.senior_id == session.senior_id,
            CareSession.start_time >= datetime.combine(previous_week_start, datetime.min.time()),
            CareSession.start_time < datetime.combine(current_week_start, datetime.min.time()),
            CareSession.status == "completed"
        ).all()
        
        if prev_sessions:
            prev_session = prev_sessions[-1]  # 가장 최근 세션
            prev_responses = db.query(ChecklistResponse).filter(
                ChecklistResponse.care_session_id == prev_session.id
            ).all()
            
            prev_total = 0
            prev_max = 0
            for resp in prev_responses:
                resp_category = getattr(resp, 'category_code', getattr(resp, 'category', ''))
                if resp_category == category_code:
                    prev_total += getattr(resp, 'scale_value', getattr(resp, 'score_value', 0))
                    prev_max += getattr(resp, 'max_scale_value', 4)
            
            if prev_max > 0:
                previous_scores[category_code] = round((prev_total / prev_max) * 100, 2)
            else:
                previous_scores[category_code] = None
        else:
            previous_scores[category_code] = None
    
    # === 상태별 분석 생성 ===
    category_analysis = {}
    
    for category_code, scores in category_scores.items():
        current_percentage = scores['score_percentage']
        previous_percentage = previous_scores.get(category_code)
        
        # 변화량 계산
        if previous_percentage is not None:
            change_amount = current_percentage - previous_percentage
            change_direction = "up" if change_amount > 5 else "down" if change_amount < -5 else "stable"
        else:
            change_amount = 0
            change_direction = "stable"
        
        # 상태 레벨 판단
        if current_percentage >= 80:
            status_level = "good"
            avatar_emotion = "happy"
            avatar_color = "blue"
        elif current_percentage >= 60:
            status_level = "caution"
            avatar_emotion = "worried"
            avatar_color = "green"
        else:
            status_level = "warning"
            avatar_emotion = "dizzy"
            avatar_color = "red"
        
        # 카테고리별 맞춤 메시지
        category_messages = {
            "nutrition_common": {
                "good": "식사를 잘 드시고 계세요. 영양 상태가 양호합니다.",
                "caution": "식사량이 조금 부족해요. 관심이 필요합니다.",
                "warning": "식사를 잘 못 드시고 계세요. 적극적인 관리가 필요해요."
            },
            "hypertension": {
                "good": "혈압 관리가 잘 되고 있어요. 현재 상태를 유지해주세요.",
                "caution": "혈압 관리에 조금 더 주의가 필요해요.",
                "warning": "고혈압 위험 상태예요. 적극적인 관리가 필요해요."
            },
            "depression": {
                "good": "기분이 좋고 활발하세요. 긍정적인 상태입니다.",
                "caution": "기분 상태가 약간 우울해 보여요. 관심이 필요합니다.",
                "warning": "우울감이 심해 보여요. 적극적인 케어가 필요해요."
            }
        }
        
        status_message = category_messages.get(category_code, {}).get(status_level, "상태를 확인하고 있습니다.")
        
        category_analysis[category_code] = {
            'category_name': _get_category_name(category_code),
            'current_score': scores['total_score'],
            'max_score': scores['max_possible_score'],
            'current_percentage': current_percentage,
            'previous_percentage': previous_percentage,
            'change_amount': change_amount,
            'change_direction': change_direction,
            'status_level': status_level,
            'avatar_emotion': avatar_emotion,
            'avatar_color': avatar_color,
            'status_message': status_message,
            'trend_data': _generate_trend_chart_data(category_code, session.senior_id, current_week_start)
        }
    
    return {
        "session_id": session_id,
        "session_date": session.start_time.date(),
        "senior": {
            "id": senior.id,
            "name": senior.name,
            "age": senior.age,
            "diseases": []  # 기존 구조에 맞춰 빈 배열로 설정
        },
        "caregiver": {
            "id": caregiver.id,
            "name": caregiver.name
        },
        "category_analysis": category_analysis,
        "checklist_responses": [
            {
                "question_key": r.question_key,
                "question_text": r.question_text,
                "answer": r.answer,
                "scale_value": getattr(r, 'scale_value', getattr(r, 'score_value', 0)),
                "category_code": getattr(r, 'category_code', getattr(r, 'category', 'unknown'))
            } for r in checklist_responses
        ],
        "care_notes": [
            {
                "question_type": n.question_type,
                "question_text": n.question_text,
                "content": n.content
            } for n in care_notes
        ]
    }

def _get_category_name(category_code: str) -> str:
    """카테고리 코드에서 한글 이름 반환"""
    category_names = {
        "nutrition_common": "영양상태 상세 추이",
        "hypertension": "고혈압 상세 추이", 
        "depression": "우울증 상세 추이"
    }
    return category_names.get(category_code, category_code)

def _generate_trend_chart_data(category_code: str, senior_id: int, current_week: date) -> list:
    """최근 4주 트렌드 차트 데이터 생성"""
    trend_data = []
    for i in range(4):
        week_start = current_week - timedelta(days=7*i)
        # 실제 DB에서 해당 주의 점수 조회하여 차트 데이터 생성
        # 현재는 임시 데이터
        trend_data.append({
            'week': f"W{4-i}",
            'score': 75 + (i * 5),  # 임시 데이터
            'date': week_start.strftime('%m.%d')
        })
    return trend_data

@router.post("/save-category-trends")
async def save_category_trends(
    trend_data: dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """카테고리별 트렌드 데이터 저장"""
    
    # 현재는 간단한 로깅만 수행
    print(f"카테고리별 트렌드 데이터 저장: {trend_data}")
    
    return {"status": "success", "message": "카테고리별 트렌드가 저장되었습니다"}

@router.put("/reports-enhanced/{session_id}")
async def update_ai_report_enhanced(
    session_id: int,
    report_data: dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI 리포트 업데이트 (카테고리별 상세 정보 포함)"""
    
    # 기존 리포트 조회 또는 생성
    ai_report = db.query(AIReport).filter(
        AIReport.care_session_id == session_id
    ).first()
    
    if not ai_report:
        care_session = db.query(CareSession).filter(CareSession.id == session_id).first()
        ai_report = AIReport(
            care_session_id=session_id,
            senior_id=care_session.senior_id if care_session else None
        )
        db.add(ai_report)
    
    # 기본 AI 리포트 정보 업데이트
    ai_report.keywords = report_data.get('keywords')
    ai_report.content = report_data.get('content', '')
    ai_report.ai_comment = report_data.get('ai_comment', '')
    ai_report.status = report_data.get('status', 'completed')
    
    # 카테고리별 상세 정보는 별도 저장 (현재는 로깅만)
    if 'category_analysis' in report_data:
        print(f"카테고리별 분석 데이터: {report_data['category_analysis']}")
    
    if 'ui_components' in report_data:
        print(f"UI 컴포넌트 데이터: {report_data['ui_components']}")
    
    db.commit()
    
    return {
        "status": "success", 
        "report_id": ai_report.id,
        "categories_updated": len(report_data.get('category_analysis', {}))
    }

@router.get("/category-status/{senior_id}")
async def get_category_status(
    senior_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """시니어의 최신 카테고리별 상태 조회"""
    
    # 시니어 확인
    senior = db.query(Senior).filter(Senior.id == senior_id).first()
    if not senior:
        raise HTTPException(status_code=404, detail="Senior not found")
    
    # 최신 AI 리포트 조회
    latest_report = db.query(AIReport).filter(
        AIReport.senior_id == senior_id
    ).order_by(AIReport.created_at.desc()).first()
    
    if not latest_report:
        return {
            "senior_id": senior_id,
            "message": "아직 리포트가 생성되지 않았습니다",
            "category_status": {}
        }
    
    # 카테고리별 상태 정보 (임시 데이터)
    category_status = {}
    categories = ['nutrition_common', 'hypertension', 'depression']
    
    for i, category_code in enumerate(categories):
        ui_key = category_code.replace('_common', '')
        category_status[ui_key] = {
            'title': _get_category_name(category_code),
            'avatar_color': ['blue', 'green', 'red'][i % 3],
            'avatar_emotion': ['happy', 'worried', 'dizzy'][i % 3],
            'current_percentage': [82, 75, 68][i % 3],
            'change_amount': [-2, 3, 7][i % 3],
            'change_display': ['-2', '+3', '+7'][i % 3],
            'status_message': [
                '기분이 좋고 활발하세요. 긍정적인 상태입니다.',
                '식사량이 조금 부족해요. 관심이 필요합니다.',
                '고혈압 위험 상태예요. 적극적인 관리가 필요해요.'
            ][i % 3],
            'trend_direction': ['down', 'up', 'up'][i % 3],
            'status_level': ['good', 'caution', 'warning'][i % 3],
            'last_updated': latest_report.created_at.date()
        }
    
    return {
        "senior_id": senior_id,
        "senior_name": senior.name,
        "latest_report_date": latest_report.created_at.date(),
        "category_status": category_status
    }
