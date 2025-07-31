"""
가디언 관련 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, date, timedelta

from ..database import get_db
from ..models import User, Guardian, Senior, AIReport, CareSession, Feedback, Notification, Caregiver, ChecklistResponse, CareNote
from ..schemas import (
    GuardianHomeResponse, AIReportResponse, FeedbackSubmission, 
    SeniorResponse, NotificationResponse
)
from sqlalchemy import text
from ..services.auth import get_current_user
from ..services.notification import NotificationService

router = APIRouter()

@router.get("/home")
async def get_guardian_home(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """가디언 홈 화면 데이터 조회 - 이번 주의 돌봄노트 형태"""
    try:
        # 1. 현재 사용자의 가디언 정보 조회
        guardian = db.query(Guardian).filter(
            Guardian.user_id == current_user.id
        ).first()
        
        if not guardian:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="가디언 정보를 찾을 수 없습니다."
            )
        
        # 2. 담당 시니어 목록 조회 (관계 정보 포함)
        seniors = db.query(Senior).options(
            joinedload(Senior.caregiver),
            joinedload(Senior.nursing_home)
        ).filter(
            Senior.guardian_id == guardian.id
        ).all()
        
        if not seniors:
            return {
                "guardian_name": guardian.name,
                "seniors_care_notes": [],
                "recent_reports": [],
                "unread_notifications": [],
                "weekly_summary": {
                    "total_seniors": 0,
                    "completed_care": 0,
                    "pending_care": 0
                }
            }
        
        # 3. 이번 주 날짜 계산 (월요일 시작)
        today = datetime.now().date()
        days_since_monday = today.weekday()  # 0=월요일, 6=일요일
        week_start = today - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        
        # 4. 시니어별 이번 주 돌봄 현황 분석
        seniors_care_notes = []
        total_completed = 0
        total_pending = 0
        
        for senior in seniors:
            # 이번 주 돌봄 세션 조회
            weekly_sessions = db.query(CareSession).filter(
                CareSession.senior_id == senior.id,
                CareSession.start_time >= week_start,
                CareSession.start_time <= week_end
            ).all()
            
            # 돌봄 완료도 계산
            total_sessions = len(weekly_sessions)
            completed_sessions = len([s for s in weekly_sessions if s.status == 'completed'])
            
            # 최신 돌봄 세션의 특이사항 조회
            latest_session = None
            special_note = "특이사항 없음"
            progress_ratio = f"{completed_sessions}/{total_sessions}" if total_sessions > 0 else "0/0"
            
            if weekly_sessions:
                latest_session = max(weekly_sessions, key=lambda x: x.start_time)
                
                # 최신 세션의 돌봄노트에서 특이사항 추출
                care_notes = db.query(CareNote).filter(
                    CareNote.care_session_id == latest_session.id
                ).all()
                
                # 가장 중요한 특이사항 추출 (family_longing 또는 health_observation 우선)
                priority_notes = [note for note in care_notes if note.question_type in ['family_longing', 'health_observation']]
                if priority_notes:
                    special_note = priority_notes[0].content[:50] + "..." if len(priority_notes[0].content) > 50 else priority_notes[0].content
                elif care_notes:
                    special_note = care_notes[0].content[:50] + "..." if len(care_notes[0].content) > 50 else care_notes[0].content
                
                # AI 리포트 확인
                ai_report = db.query(AIReport).filter(
                    AIReport.care_session_id == latest_session.id
                ).first()
                
                if ai_report and ai_report.keywords:
                    try:
                        import json
                        keywords = json.loads(ai_report.keywords) if isinstance(ai_report.keywords, str) else ai_report.keywords
                        if keywords and len(keywords) > 0:
                            special_note = f"{keywords[0]} 관련 상태"
                    except:
                        pass
            
            # 케어기버 정보 (관계를 통해 이미 로드됨)
            caregiver_name = senior.caregiver.name if senior.caregiver else "케어기버 미배정"
            
            # 시니어 돌봄 정보 구성
            senior_care_info = {
                "senior_id": senior.id,
                "senior_name": senior.name,
                "senior_age": senior.age,
                "senior_photo": senior.photo,
                "caregiver_name": caregiver_name,
                "special_note": special_note,
                "progress_ratio": progress_ratio,
                "total_sessions_this_week": total_sessions,
                "completed_sessions": completed_sessions,
                "nursing_home": senior.nursing_home.name if senior.nursing_home else "요양원 정보 없음",
                "last_care_date": latest_session.start_time.strftime("%Y-%m-%d") if latest_session else None,
                "status": "완료" if completed_sessions > 0 else "대기중"
            }
            
            seniors_care_notes.append(senior_care_info)
            
            if completed_sessions > 0:
                total_completed += 1
            else:
                total_pending += 1
        
        # 5. 최근 AI 리포트 조회 (최근 5개)
        senior_ids = [senior.id for senior in seniors]
        recent_reports = db.query(AIReport).join(CareSession).filter(
            CareSession.senior_id.in_(senior_ids)
        ).order_by(AIReport.created_at.desc()).limit(5).all()
        
        recent_reports_data = []
        for report in recent_reports:
            session = db.query(CareSession).filter(CareSession.id == report.care_session_id).first()
            senior = db.query(Senior).filter(Senior.id == session.senior_id).first()
            
            recent_reports_data.append({
                "report_id": report.id,
                "senior_name": senior.name,
                "created_date": report.created_at.strftime("%Y-%m-%d"),
                "keywords": report.keywords,
                "status": report.status,
                "priority": "high" if "위험" in (report.ai_comment or "") else "normal"
            })
        
        # 6. 읽지 않은 알림 조회
        unread_notifications = db.query(Notification).filter(
            Notification.receiver_id == current_user.id,
            Notification.is_read == False
        ).order_by(Notification.created_at.desc()).limit(10).all()
        
        unread_notifications_data = []
        for notification in unread_notifications:
            # notification.data 처리 (문자열이면 JSON 파싱, 딕셔너리면 그대로 사용)
            notification_data = {}
            if notification.data:
                if isinstance(notification.data, str):
                    try:
                        import json
                        notification_data = json.loads(notification.data)
                    except (json.JSONDecodeError, TypeError):
                        notification_data = {}
                elif isinstance(notification.data, dict):
                    notification_data = notification.data
            
            unread_notifications_data.append({
                "id": notification.id,
                "type": notification.type,
                "title": notification.title,
                "content": notification.content,
                "created_at": notification.created_at.strftime("%Y-%m-%d %H:%M"),
                "priority": notification_data.get("priority", "normal")
            })
        
        return {
            "guardian_name": guardian.name,
            "guardian_country": guardian.country,
            "guardian_relationship": guardian.relationship_type,
            "week_period": {
                "start_date": week_start.strftime("%Y-%m-%d"),
                "end_date": week_end.strftime("%Y-%m-%d"),
                "week_description": f"{week_start.strftime('%m월 %d일')} - {week_end.strftime('%m월 %d일')}"
            },
            "seniors_care_notes": seniors_care_notes,
            "recent_reports": recent_reports_data,
            "unread_notifications": unread_notifications_data,
            "weekly_summary": {
                "total_seniors": len(seniors),
                "completed_care": total_completed,
                "pending_care": total_pending,
                "completion_rate": round((total_completed / len(seniors)) * 100, 1) if seniors else 0
            },
            "quick_actions": [
                {
                    "action": "view_reports",
                    "title": "리포트 조회",
                    "description": "최신 돌봄 리포트 확인"
                },
                {
                    "action": "send_feedback",
                    "title": "피드백 전송",
                    "description": "케어기버에게 메시지 보내기"
                },
                {
                    "action": "view_notifications",
                    "title": "알림 확인",
                    "description": f"{len(unread_notifications_data)}개의 읽지 않은 알림"
                }
            ]
        }
        
    except Exception as e:
        print(f"Guardian home error: {str(e)}")  # 디버깅용 로그
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"홈 데이터 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/seniors")
async def get_guardian_seniors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """담당 시니어 목록 조회 - 수정된 버전"""
    try:
        # 가디언 정보 조회
        guardian = db.query(Guardian).filter(
            Guardian.user_id == current_user.id
        ).first()
        
        if not guardian:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="가디언 정보를 찾을 수 없습니다."
            )
        
        # 시니어 목록 조회 (관계 정보 포함)
        seniors = db.query(Senior).options(
            joinedload(Senior.caregiver),
            joinedload(Senior.nursing_home),
            joinedload(Senior.diseases)  # ✅ 추가: 질병 정보 함께 조회
        ).filter(
            Senior.guardian_id == guardian.id
        ).all()
        
        seniors_data = []
        for senior in seniors:
            # 최근 돌봄 세션 정보
            latest_session = db.query(CareSession).filter(
                CareSession.senior_id == senior.id
            ).order_by(CareSession.start_time.desc()).first()
            
            # 최근 AI 리포트 정보
            latest_report = None
            if latest_session:
                latest_report = db.query(AIReport).filter(
                    AIReport.care_session_id == latest_session.id
                ).first()
            
            seniors_data.append({
                "id": senior.id,
                "name": senior.name,
                "age": senior.age,
                "gender": senior.gender,
                "photo": senior.photo,
                "diseases": [disease.disease_type for disease in senior.diseases],
                "caregiver": {
                    "name": senior.caregiver.name if senior.caregiver else None,
                    "phone": senior.caregiver.phone if senior.caregiver else None
                },
                "nursing_home": {
                    "name": senior.nursing_home.name if senior.nursing_home else None,
                    "address": senior.nursing_home.address if senior.nursing_home else None
                },
                "latest_care": {
                    "date": latest_session.start_time.strftime("%Y-%m-%d") if latest_session else None,
                    "status": latest_session.status if latest_session else None
                },
                "latest_report": {
                    "id": latest_report.id if latest_report else None,
                    "status": latest_report.status if latest_report else None,
                    "created_date": latest_report.created_at.strftime("%Y-%m-%d") if latest_report else None
                }
            })
        
        return {
            "guardian_name": guardian.name,
            "seniors": seniors_data,
            "total_count": len(seniors_data)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"시니어 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/reports")
async def get_reports(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    senior_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI 리포트 목록 조회 - 수정된 버전"""
    try:
        # 가디언 정보 조회
        guardian = db.query(Guardian).filter(
            Guardian.user_id == current_user.id
        ).first()
        
        if not guardian:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="가디언 정보를 찾을 수 없습니다."
            )
        
        # 가디언이 담당하는 시니어들 조회
        seniors = db.query(Senior).filter(
            Senior.guardian_id == guardian.id
        ).all()
        
        senior_ids = [senior.id for senior in seniors]
        
        if not senior_ids:
            return {
                "reports": [],
                "total_count": 0
            }
        
        # 리포트 쿼리 작성
        query = db.query(AIReport).join(CareSession).filter(
            CareSession.senior_id.in_(senior_ids)
        )
        
        # 필터 적용
        if start_date:
            query = query.filter(AIReport.created_at >= start_date)
        if end_date:
            query = query.filter(AIReport.created_at <= end_date)
        if senior_id:
            if senior_id not in senior_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="해당 시니어의 리포트에 접근할 권한이 없습니다."
                )
            query = query.filter(CareSession.senior_id == senior_id)
        
        reports = query.order_by(AIReport.created_at.desc()).all()
        
        reports_data = []
        for report in reports:
            session = db.query(CareSession).filter(CareSession.id == report.care_session_id).first()
            senior = db.query(Senior).filter(Senior.id == session.senior_id).first()
            caregiver = db.query(Caregiver).filter(Caregiver.id == session.caregiver_id).first()
            
            reports_data.append({
                "id": report.id,
                "keywords": report.keywords,
                "content": report.content,
                "ai_comment": report.ai_comment,
                "status": report.status,
                "created_at": report.created_at.strftime("%Y-%m-%d %H:%M"),
                "senior": {
                    "id": senior.id,
                    "name": senior.name,
                    "photo": senior.photo
                },
                "caregiver": {
                    "name": caregiver.name
                },
                "session_date": session.start_time.strftime("%Y-%m-%d")
            })
        
        return {
            "reports": reports_data,
            "total_count": len(reports_data)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"리포트 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/reports/{report_id}")
async def get_report_detail(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI 리포트 상세 조회"""
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
        
        # 시니어 정보 조회
        senior = db.query(Senior).filter(
            Senior.id == session.senior_id
        ).first()
        
        # 권한 확인
        if senior.guardian_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 리포트에 접근할 권한이 없습니다."
            )
        
        # 리포트 읽음 상태 업데이트
        if report.status == "generated":
            report.status = "read"
            db.commit()
        
        return {
            "report": report,
            "session": session,
            "senior": senior,
            "caregiver": session.caregiver
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"리포트 상세 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/feedback")
async def submit_feedback(
    feedback_data: FeedbackSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """피드백 제출"""
    try:
        # 리포트 존재 확인
        report = db.query(AIReport).filter(
            AIReport.id == feedback_data.report_id
        ).first()
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="리포트를 찾을 수 없습니다."
            )
        
        # 세션 및 시니어 정보 조회
        session = db.query(CareSession).filter(
            CareSession.id == report.session_id
        ).first()
        
        senior = db.query(Senior).filter(
            Senior.id == session.senior_id
        ).first()
        
        # 권한 확인
        if senior.guardian_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 리포트에 피드백할 권한이 없습니다."
            )
        
        # 피드백 생성
        feedback = Feedback(
            report_id=feedback_data.report_id,
            guardian_id=current_user.id,
            message=feedback_data.message,
            requirements=feedback_data.requirements,
            status="pending"
        )
        
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        # 케어기버에게 알림 전송
        notification_service = NotificationService(db)
        await notification_service.send_notification(
            sender_id=current_user.id,
            receiver_id=session.caregiver_id,
            type="feedback",
            title="새로운 피드백이 도착했습니다",
            content=f"{senior.name}님 담당 가디언으로부터 피드백이 도착했습니다.",
            data={"feedback_id": feedback.id, "report_id": report.id}
        )
        
        return {
            "message": "피드백이 성공적으로 제출되었습니다.",
            "feedback_id": feedback.id,
            "status": "pending"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"피드백 제출 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/feedback/history")
async def get_feedback_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """피드백 이력 조회"""
    try:
        feedbacks = db.query(Feedback).filter(
            Feedback.guardian_id == current_user.id
        ).order_by(Feedback.created_at.desc()).all()
        
        return {
            "feedbacks": feedbacks,
            "total_count": len(feedbacks)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"피드백 이력 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """알림 목록 조회"""
    try:
        query = db.query(Notification).filter(
            Notification.receiver_id == current_user.id
        )
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        notifications = query.order_by(Notification.created_at.desc()).all()
        
        return notifications
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"알림 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """알림 읽음 처리"""
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.receiver_id == current_user.id
        ).first()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="알림을 찾을 수 없습니다."
            )
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        
        db.commit()
        
        return {"message": "알림이 읽음 처리되었습니다."}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"알림 읽음 처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/profile")
async def get_guardian_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """가디언 프로필 조회"""
    try:
        # 담당 시니어 수 조회
        seniors_count = db.query(Senior).filter(
            Senior.guardian_id == current_user.id
        ).count()
        
        # 총 리포트 수 조회
        seniors = db.query(Senior).filter(
            Senior.guardian_id == current_user.id
        ).all()
        
        senior_ids = [senior.id for senior in seniors]
        
        total_reports = db.query(AIReport).join(CareSession).filter(
            CareSession.senior_id.in_(senior_ids)
        ).count()
        
        return {
            "user_info": current_user,
            "assigned_seniors_count": seniors_count,
            "total_reports": total_reports,
            "pending_feedback": db.query(Feedback).filter(
                Feedback.guardian_id == current_user.id,
                Feedback.status == "pending"
            ).count()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"프로필 조회 중 오류가 발생했습니다: {str(e)}"
        )

# 추이 분석 엔드포인트 추가
from app.services.trend_analysis import TrendAnalysisService

@router.get("/trend-analysis/{senior_id}")
async def get_trend_analysis(
    senior_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """시니어 상태 변화 추이 분석"""
    
    # 권한 확인 (가디언이 해당 시니어의 보호자인지)
    senior = db.query(Senior).filter(
        Senior.id == senior_id,
        Senior.guardian_id == current_user.guardian_profile.id
    ).first()
    
    if not senior:
        raise HTTPException(status_code=404, detail="시니어 정보를 찾을 수 없습니다")
    
    # 추이 분석 수행
    trend_service = TrendAnalysisService(db)
    analysis = trend_service.analyze_4week_trend(senior_id)
    
    return {
        "senior_name": senior.name,
        "analysis_date": datetime.now().isoformat(),
        "trend_analysis": analysis
    }

# ==========================================
# 4단계: 카테고리별 상세 분석 엔드포인트
# ==========================================

@router.get("/home-enhanced")
async def get_guardian_home_enhanced(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """카테고리별 상태 포함 가디언 홈 화면"""
    try:
        # 담당 시니어 목록 조회
        seniors = db.query(Senior).filter(
            Senior.guardian_id == current_user.id
        ).all()
        
        if not seniors:
            return {
                "guardian_name": current_user.name,
                "seniors": [],
                "recent_reports": [],
                "unread_notifications": []
            }
        
        senior_ids = [senior.id for senior in seniors]
        
        # 시니어별 최신 카테고리 상태 조회 (뷰 사용)
        seniors_with_categories = []
        for senior in seniors:
            # 최신 카테고리 상태 조회
            category_query = text("""
                SELECT * FROM v_latest_category_status 
                WHERE senior_id = :senior_id
            """)
            
            category_result = db.execute(category_query, {"senior_id": senior.id}).fetchone()
            
            if category_result:
                category_status = {
                    "nutrition": {
                        "title": "영양상태 상세 추이",
                        "avatar_color": category_result.nutrition_color or "blue",
                        "avatar_emotion": category_result.nutrition_emotion or "happy",
                        "change_display": category_result.nutrition_change_display or "0",
                        "current_percentage": category_result.nutrition_percentage or 0,
                        "status_message": category_result.nutrition_message or "상태 확인 중입니다."
                    },
                    "hypertension": {
                        "title": "고혈압 상세 추이", 
                        "avatar_color": category_result.hypertension_color or "blue",
                        "avatar_emotion": category_result.hypertension_emotion or "happy",
                        "change_display": category_result.hypertension_change_display or "0",
                        "current_percentage": category_result.hypertension_percentage or 0,
                        "status_message": category_result.hypertension_message or "상태 확인 중입니다."
                    },
                    "depression": {
                        "title": "우울증 상세 추이",
                        "avatar_color": category_result.depression_color or "blue", 
                        "avatar_emotion": category_result.depression_emotion or "happy",
                        "change_display": category_result.depression_change_display or "0",
                        "current_percentage": category_result.depression_percentage or 0,
                        "status_message": category_result.depression_message or "상태 확인 중입니다."
                    }
                }
            else:
                # 기본값 설정
                category_status = {
                    "nutrition": {
                        "title": "영양상태 상세 추이",
                        "avatar_color": "blue",
                        "avatar_emotion": "happy", 
                        "change_display": "0",
                        "current_percentage": 0,
                        "status_message": "아직 데이터가 없습니다."
                    },
                    "hypertension": {
                        "title": "고혈압 상세 추이",
                        "avatar_color": "blue",
                        "avatar_emotion": "happy",
                        "change_display": "0", 
                        "current_percentage": 0,
                        "status_message": "아직 데이터가 없습니다."
                    },
                    "depression": {
                        "title": "우울증 상세 추이",
                        "avatar_color": "blue",
                        "avatar_emotion": "happy",
                        "change_display": "0",
                        "current_percentage": 0,
                        "status_message": "아직 데이터가 없습니다."
                    }
                }
            
            seniors_with_categories.append({
                "id": senior.id,
                "name": senior.name,
                "age": senior.age,
                "photo": senior.photo,
                "category_status": category_status
            })
        
        # 최근 리포트 조회 (향상된 버전 - 카테고리 정보 포함)
        recent_reports_query = text("""
            SELECT 
                ar.id, ar.keywords, ar.content, ar.ai_comment,
                ar.created_at, ar.status,
                ar.category_details, ar.ui_components,
                cs.senior_id,
                s.name as senior_name
            FROM ai_reports ar
            JOIN care_sessions cs ON ar.session_id = cs.id
            JOIN seniors s ON cs.senior_id = s.id
            WHERE cs.senior_id IN :senior_ids
            ORDER BY ar.created_at DESC
            LIMIT 10
        """)
        
        recent_reports_result = db.execute(
            recent_reports_query, 
            {"senior_ids": tuple(senior_ids)}
        ).fetchall()
        
        recent_reports = [
            {
                "id": report.id,
                "keywords": report.keywords,
                "content": report.content,
                "ai_comment": report.ai_comment,
                "created_at": report.created_at,
                "status": report.status,
                "category_details": report.category_details,
                "ui_components": report.ui_components,
                "senior_id": report.senior_id,
                "senior_name": report.senior_name
            } for report in recent_reports_result
        ]
        
        # 읽지 않은 알림 조회
        unread_notifications = db.query(Notification).filter(
            Notification.receiver_id == current_user.id,
            Notification.is_read == False
        ).order_by(Notification.created_at.desc()).limit(10).all()
        
        return {
            "guardian_name": current_user.name,
            "seniors": seniors_with_categories,
            "recent_reports": recent_reports,
            "unread_notifications": unread_notifications,
            "enhanced_features": {
                "category_analysis_enabled": True,
                "ui_version": "enhanced_v1.0"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"향상된 홈 데이터 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/senior/{senior_id}/category-details")
async def get_senior_category_details(
    senior_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """시니어 카테고리별 상세 정보 조회"""
    try:
        # 권한 확인
        senior = db.query(Senior).filter(
            Senior.id == senior_id,
            Senior.guardian_id == current_user.id
        ).first()
        
        if not senior:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 시니어 정보를 찾을 수 없거나 접근 권한이 없습니다."
            )
        
        # 4주간 카테고리별 트렌드 데이터 조회
        trend_query = text("""
            SELECT 
                cta.analysis_date,
                cta.category_name,
                cta.current_score,
                cta.previous_score,
                cta.score_change,
                cta.trend_direction,
                cta.category_insights,
                cta.recommendations,
                cta.ui_data
            FROM category_trend_analysis cta
            WHERE cta.senior_id = :senior_id
            AND cta.analysis_date >= DATE_SUB(CURDATE(), INTERVAL 4 WEEK)
            ORDER BY cta.analysis_date DESC, cta.category_name
        """)
        
        trend_results = db.execute(trend_query, {"senior_id": senior_id}).fetchall()
        
        # 카테고리별로 데이터 그룹화
        category_details = {
            "nutrition": {
                "title": "영양상태 상세 추이",
                "description": "식사량, 영양 섭취, 체중 변화 등을 종합 분석",
                "weekly_data": [],
                "current_status": {},
                "insights": [],
                "recommendations": []
            },
            "hypertension": {
                "title": "고혈압 상세 추이", 
                "description": "혈압 측정, 복약 관리, 증상 관찰 등을 종합 분석",
                "weekly_data": [],
                "current_status": {},
                "insights": [],
                "recommendations": []
            },
            "depression": {
                "title": "우울증 상세 추이",
                "description": "감정 상태, 활동 참여, 소통 정도 등을 종합 분석", 
                "weekly_data": [],
                "current_status": {},
                "insights": [],
                "recommendations": []
            }
        }
        
        # 트렌드 데이터를 카테고리별로 분류
        for trend in trend_results:
            category = trend.category_name
            if category in category_details:
                week_data = {
                    "date": trend.analysis_date,
                    "score": trend.current_score,
                    "change": trend.score_change,
                    "trend": trend.trend_direction,
                    "ui_data": trend.ui_data
                }
                category_details[category]["weekly_data"].append(week_data)
                
                # 가장 최근 데이터를 현재 상태로 설정
                if not category_details[category]["current_status"] or \
                   trend.analysis_date > category_details[category]["current_status"].get("date"):
                    category_details[category]["current_status"] = {
                        "score": trend.current_score,
                        "previous_score": trend.previous_score,
                        "change": trend.score_change,
                        "trend": trend.trend_direction,
                        "date": trend.analysis_date
                    }
                
                # 인사이트와 권장사항 추가
                if trend.category_insights:
                    category_details[category]["insights"].append(trend.category_insights)
                if trend.recommendations:
                    category_details[category]["recommendations"].append(trend.recommendations)
        
        # 최근 관련 리포트 조회
        recent_reports_query = text("""
            SELECT 
                ar.id, ar.content, ar.ai_comment, ar.created_at,
                ar.category_details
            FROM ai_reports ar
            JOIN care_sessions cs ON ar.session_id = cs.id
            WHERE cs.senior_id = :senior_id
            AND ar.category_details IS NOT NULL
            ORDER BY ar.created_at DESC
            LIMIT 5
        """)
        
        recent_reports = db.execute(recent_reports_query, {"senior_id": senior_id}).fetchall()
        
        return {
            "senior": {
                "id": senior.id,
                "name": senior.name,
                "age": senior.age,
                "photo": senior.photo
            },
            "category_details": category_details,
            "recent_reports": [
                {
                    "id": report.id,
                    "content": report.content,
                    "ai_comment": report.ai_comment,
                    "created_at": report.created_at,
                    "category_details": report.category_details
                } for report in recent_reports
            ],
            "analysis_summary": {
                "total_weeks_analyzed": len(set(trend.analysis_date for trend in trend_results)),
                "last_analysis_date": max((trend.analysis_date for trend in trend_results), default=None)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"카테고리별 상세 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/reports-enhanced")
async def get_reports_enhanced(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    senior_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """상세 분석 포함 AI 리포트 목록 조회"""
    try:
        # 가디언이 담당하는 시니어들 조회
        seniors = db.query(Senior).filter(
            Senior.guardian_id == current_user.id
        ).all()
        
        senior_ids = [senior.id for senior in seniors]
        
        if not senior_ids:
            return {
                "reports": [],
                "total_count": 0,
                "categories_summary": {}
            }
        
        # 향상된 리포트 쿼리 (카테고리 정보 포함)
        query_conditions = ["cs.senior_id IN :senior_ids"]
        query_params = {"senior_ids": tuple(senior_ids)}
        
        # 필터 조건 추가
        if start_date:
            query_conditions.append("ar.created_at >= :start_date")
            query_params["start_date"] = start_date
        if end_date:
            query_conditions.append("ar.created_at <= :end_date") 
            query_params["end_date"] = end_date
        if senior_id:
            if senior_id not in senior_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="해당 시니어의 리포트에 접근할 권한이 없습니다."
                )
            query_conditions.append("cs.senior_id = :specific_senior_id")
            query_params["specific_senior_id"] = senior_id
        
        where_clause = " AND ".join(query_conditions)
        
        enhanced_reports_query = text(f"""
            SELECT 
                ar.id,
                ar.keywords,
                ar.content,
                ar.ai_comment,
                ar.status,
                ar.created_at,
                ar.category_details,
                ar.ui_components,
                ar.ui_enhancements,
                cs.senior_id,
                s.name as senior_name,
                s.photo as senior_photo,
                cg.name as caregiver_name
            FROM ai_reports ar
            JOIN care_sessions cs ON ar.session_id = cs.id
            JOIN seniors s ON cs.senior_id = s.id
            JOIN caregivers cg ON cs.caregiver_id = cg.id
            WHERE {where_clause}
            ORDER BY ar.created_at DESC
        """)
        
        reports_result = db.execute(enhanced_reports_query, query_params).fetchall()
        
        # 카테고리별 요약 통계
        categories_summary = {
            "nutrition": {"total": 0, "improving": 0, "stable": 0, "declining": 0},
            "hypertension": {"total": 0, "improving": 0, "stable": 0, "declining": 0},
            "depression": {"total": 0, "improving": 0, "stable": 0, "declining": 0}
        }
        
        enhanced_reports = []
        for report in reports_result:
            # 카테고리 세부 정보 파싱
            category_details = None
            ui_components = None
            
            if report.category_details:
                try:
                    import json
                    category_details = json.loads(report.category_details) if isinstance(report.category_details, str) else report.category_details
                except:
                    category_details = None
            
            if report.ui_components:
                try:
                    import json
                    ui_components = json.loads(report.ui_components) if isinstance(report.ui_components, str) else report.ui_components
                except:
                    ui_components = None
            
            # 카테고리별 통계 업데이트
            if category_details:
                for category in ["nutrition", "hypertension", "depression"]:
                    if category in category_details:
                        categories_summary[category]["total"] += 1
                        trend = category_details[category].get("trend_direction", "stable")
                        if trend in categories_summary[category]:
                            categories_summary[category][trend] += 1
            
            enhanced_reports.append({
                "id": report.id,
                "keywords": report.keywords,
                "content": report.content,
                "ai_comment": report.ai_comment,
                "status": report.status,
                "created_at": report.created_at,
                "category_details": category_details,
                "ui_components": ui_components,
                "ui_enhancements": report.ui_enhancements,
                "senior": {
                    "id": report.senior_id,
                    "name": report.senior_name,
                    "photo": report.senior_photo
                },
                "caregiver_name": report.caregiver_name
            })
        
        return {
            "reports": enhanced_reports,
            "total_count": len(enhanced_reports),
            "categories_summary": categories_summary,
            "enhanced_features": {
                "category_analysis": True,
                "trend_tracking": True,
                "ui_enhancements": True
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"향상된 리포트 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/report/{report_id}/detailed")
async def get_report_detailed(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """상세 리포트 조회 (카테고리별 분석 포함)"""
    try:
        # 상세 리포트 조회
        detailed_query = text("""
            SELECT 
                ar.id,
                ar.keywords,
                ar.content,
                ar.ai_comment,
                ar.status,
                ar.created_at,
                ar.category_details,
                ar.ui_components,
                ar.ui_enhancements,
                cs.id as session_id,
                cs.start_time,
                cs.end_time,
                cs.senior_id,
                s.name as senior_name,
                s.age as senior_age,
                s.photo as senior_photo,
                cg.id as caregiver_id,
                cg.name as caregiver_name,
                cg.phone as caregiver_phone
            FROM ai_reports ar
            JOIN care_sessions cs ON ar.session_id = cs.id
            JOIN seniors s ON cs.senior_id = s.id
            JOIN caregivers cg ON cs.caregiver_id = cg.id
            WHERE ar.id = :report_id
        """)
        
        report_result = db.execute(detailed_query, {"report_id": report_id}).fetchone()
        
        if not report_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="리포트를 찾을 수 없습니다."
            )
        
        # 권한 확인
        senior = db.query(Senior).filter(
            Senior.id == report_result.senior_id,
            Senior.guardian_id == current_user.id
        ).first()
        
        if not senior:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 리포트에 접근할 권한이 없습니다."
            )
        
        # 카테고리 세부 정보 파싱
        category_details = None
        ui_components = None
        
        if report_result.category_details:
            try:
                import json
                category_details = json.loads(report_result.category_details) if isinstance(report_result.category_details, str) else report_result.category_details
            except:
                category_details = None
        
        if report_result.ui_components:
            try:
                import json
                ui_components = json.loads(report_result.ui_components) if isinstance(report_result.ui_components, str) else report_result.ui_components
            except:
                ui_components = None
        
        # 관련 체크리스트 및 돌봄노트 조회
        session_details_query = text("""
            SELECT 
                'checklist' as type,
                cr.question_key,
                cr.question_text,
                cr.answer,
                cr.notes,
                cr.score_value,
                cr.category
            FROM checklist_responses cr
            WHERE cr.care_session_id = :session_id
            
            UNION ALL
            
            SELECT 
                'care_note' as type,
                cn.question_type as question_key,
                cn.question_text,
                cn.content as answer,
                NULL as notes,
                NULL as score_value,
                NULL as category
            FROM care_notes cn
            WHERE cn.care_session_id = :session_id
        """)
        
        session_details = db.execute(session_details_query, {"session_id": report_result.session_id}).fetchall()
        
        # 체크리스트와 돌봄노트 분리
        checklist_data = [detail for detail in session_details if detail.type == 'checklist']
        care_notes_data = [detail for detail in session_details if detail.type == 'care_note']
        
        # 리포트 읽음 상태 업데이트
        if report_result.status == "generated":
            update_query = text("UPDATE ai_reports SET status = 'read' WHERE id = :report_id")
            db.execute(update_query, {"report_id": report_id})
            db.commit()
        
        return {
            "report": {
                "id": report_result.id,
                "keywords": report_result.keywords,
                "content": report_result.content,
                "ai_comment": report_result.ai_comment,
                "status": "read",  # 읽음 처리됨
                "created_at": report_result.created_at,
                "category_details": category_details,
                "ui_components": ui_components,
                "ui_enhancements": report_result.ui_enhancements
            },
            "session": {
                "id": report_result.session_id,
                "start_time": report_result.start_time,
                "end_time": report_result.end_time,
                "checklist_responses": [
                    {
                        "question_key": item.question_key,
                        "question_text": item.question_text,
                        "answer": item.answer,
                        "notes": item.notes,
                        "score_value": item.score_value,
                        "category": item.category
                    } for item in checklist_data
                ],
                "care_notes": [
                    {
                        "question_type": item.question_key,
                        "question_text": item.question_text,
                        "content": item.answer
                    } for item in care_notes_data
                ]
            },
            "senior": {
                "id": report_result.senior_id,
                "name": report_result.senior_name,
                "age": report_result.senior_age,
                "photo": report_result.senior_photo
            },
            "caregiver": {
                "id": report_result.caregiver_id,
                "name": report_result.caregiver_name,
                "phone": report_result.caregiver_phone
            },
            "enhanced_features": {
                "category_breakdown": True,
                "visual_components": True,
                "trend_analysis": True
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상세 리포트 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """알림 목록 조회"""
    
    if not current_user.guardian_profile:
        raise HTTPException(status_code=403, detail="가디언 권한이 필요합니다")
    
    try:
        query = db.query(Notification).filter(
            Notification.receiver_id == current_user.guardian_profile.id
        )
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        notifications = query.order_by(Notification.created_at.desc()).all()
        
        return [
            {
                "id": notification.id,
                "title": notification.title,
                "content": notification.content,
                "type": notification.type,
                "sender_id": notification.sender_id,
                "receiver_id": notification.receiver_id,
                "data": notification.data,
                "is_read": notification.is_read,
                "read_at": notification.read_at,
                "created_at": notification.created_at
            } for notification in notifications
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"알림 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """알림 읽음 처리"""
    
    if not current_user.guardian_profile:
        raise HTTPException(status_code=403, detail="가디언 권한이 필요합니다")
    
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.receiver_id == current_user.guardian_profile.id
        ).first()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="알림을 찾을 수 없습니다."
            )
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        
        db.commit()
        
        return {"message": "알림이 읽음 처리되었습니다."}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"알림 읽음 처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/feedback/history")
async def get_feedback_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """피드백 이력 조회"""
    
    if not current_user.guardian_profile:
        raise HTTPException(status_code=403, detail="가디언 권한이 필요합니다")
    
    try:
        feedbacks = db.query(Feedback).filter(
            Feedback.guardian_id == current_user.guardian_profile.id
        ).order_by(Feedback.created_at.desc()).all()
        
        return {
            "feedbacks": [
                {
                    "id": feedback.id,
                    "message": feedback.message,
                    "requirements": feedback.requirements,
                    "report_id": feedback.report_id,
                    "status": feedback.status,
                    "created_at": feedback.created_at,
                    "updated_at": feedback.updated_at
                } for feedback in feedbacks
            ],
            "total_count": len(feedbacks)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"피드백 이력 조회 중 오류가 발생했습니다: {str(e)}"
        )
