"""
케어기버 관련 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, date, timedelta

from ..database import get_db
from ..models import User, Senior, CareSession, ChecklistResponse, CareNote, Notification, NursingHome
from ..models.enhanced_care import CareSchedule
from ..schemas import (
    CareSessionResponse, SeniorResponse, ChecklistSubmission, CareNoteSubmission,
    CaregiverHomeResponse, AttendanceCheckIn, AttendanceCheckOut
)
from ..schemas.home import CareScheduleResponse, CareScheduleGroup
from ..services.auth import get_current_user
from ..services.care import CareService

router = APIRouter()

@router.get("/home", response_model=CaregiverHomeResponse)
async def get_caregiver_home(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """케어기버 홈 화면 데이터 조회 - 돌봄 일정 포함"""
    try:
        # 케어기버 프로필 조회 (관계를 통해)
        if not current_user.caregiver_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="케어기버 정보를 찾을 수 없습니다."
            )
        
        caregiver = current_user.caregiver_profile
        
        # 오늘 날짜 기준 돌봄 세션 조회
        today = date.today()
        today_sessions = db.query(CareSession).filter(
            CareSession.caregiver_id == caregiver.id,
            CareSession.created_at >= today
        ).all()
        
        # 담당 시니어 목록 조회
        seniors = db.query(Senior).filter(
            Senior.caregiver_id == caregiver.id
        ).all()
        
        # 읽지 않은 알림 조회
        notifications = db.query(Notification).filter(
            Notification.receiver_id == current_user.id,
            Notification.is_read == False
        ).order_by(Notification.created_at.desc()).limit(10).all()
        
        # ===== 새로운 돌봄 일정 조회 로직 =====
        care_schedules = await get_caregiver_care_schedules(caregiver.id, db)
        
        # 통계 계산
        total_assigned_seniors = len(seniors)
        
        # 이번 주 완료된 세션 수
        week_start = today - timedelta(days=today.weekday())
        completed_sessions_this_week = db.query(CareSession).filter(
            CareSession.caregiver_id == caregiver.id,
            CareSession.start_time >= week_start,
            CareSession.status == "completed"
        ).count()
        
        # 오늘 대기 중인 일정 수
        pending_schedules_today = len([s for s in care_schedules.today_schedules if s.status == "scheduled"])
        
        return CaregiverHomeResponse(
            caregiver_name=caregiver.name,
            caregiver_id=caregiver.id,
            today_sessions=today_sessions,
            seniors=seniors,
            notifications=notifications,
            care_schedules=care_schedules,
            total_assigned_seniors=total_assigned_seniors,
            completed_sessions_this_week=completed_sessions_this_week,
            pending_schedules_today=pending_schedules_today
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"홈 데이터 조회 중 오류가 발생했습니다: {str(e)}"
        )

async def get_caregiver_care_schedules(caregiver_id: int, db: Session) -> CareScheduleGroup:
    """케어기버의 돌봄 일정을 조회하여 분류"""
    
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # 이번 주 월요일
    week_end = week_start + timedelta(days=6)  # 이번 주 일요일
    next_week_start = week_end + timedelta(days=1)  # 다음 주 월요일
    next_week_end = next_week_start + timedelta(days=6)  # 다음 주 일요일
    
    # care_calendar 테이블에서 돌봄 일정 조회 (시니어 정보와 요양원 정보 포함)
    from sqlalchemy import text
    from datetime import time as time_obj
    
    # 지난 30일부터 앞으로 30일까지의 일정 조회
    start_date = today - timedelta(days=30)
    end_date = today + timedelta(days=30)
    
    query = text("""
        SELECT 
            cc.id,
            cc.senior_id,
            s.name as senior_name,
            s.photo as senior_photo,
            cc.care_date,
            cc.start_time,
            cc.end_time,
            cc.status,
            cc.notes,
            nh.name as nursing_home_name,
            nh.address as nursing_home_address
        FROM care_calendar cc
        JOIN seniors s ON cc.senior_id = s.id
        LEFT JOIN nursing_homes nh ON s.nursing_home_id = nh.id
        WHERE cc.caregiver_id = :caregiver_id
        AND cc.care_date BETWEEN :start_date AND :end_date
        ORDER BY cc.care_date ASC, cc.start_time ASC
    """)
    
    result = db.execute(query, {
        "caregiver_id": caregiver_id,
        "start_date": start_date,
        "end_date": end_date
    })
    
    schedule_rows = result.fetchall()
    
    # 일정을 분류
    today_schedules = []
    past_schedules = []
    upcoming_schedules = []
    this_week_schedules = []
    next_week_schedules = []
    
    def convert_timedelta_to_time(td):
        """timedelta를 time 객체로 변환"""
        if td is None:
            return None
        if isinstance(td, timedelta):
            # timedelta의 총 초를 시간:분:초로 변환
            total_seconds = int(td.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return time_obj(hours, minutes, seconds)
        return td  # 이미 time 객체인 경우
    
    for row in schedule_rows:
        # timedelta를 time으로 변환
        start_time_converted = convert_timedelta_to_time(row.start_time)
        end_time_converted = convert_timedelta_to_time(row.end_time)
        
        schedule = CareScheduleResponse(
            id=row.id,
            senior_id=row.senior_id,
            senior_name=row.senior_name,
            senior_photo=row.senior_photo,
            care_date=row.care_date,
            start_time=start_time_converted,
            end_time=end_time_converted,
            status=row.status,
            is_today=(row.care_date == today),
            nursing_home_name=row.nursing_home_name,
            nursing_home_address=row.nursing_home_address,
            notes=row.notes
        )
        
        # 오늘 일정
        if row.care_date == today:
            today_schedules.append(schedule)
        
        # 과거 일정 (최근 7일)
        elif row.care_date < today and row.care_date >= today - timedelta(days=7):
            past_schedules.append(schedule)
        
        # 미래 일정 (내일부터 30일)
        elif row.care_date > today:
            upcoming_schedules.append(schedule)
        
        # 이번 주 일정
        if week_start <= row.care_date <= week_end:
            this_week_schedules.append(schedule)
        
        # 다음 주 일정
        elif next_week_start <= row.care_date <= next_week_end:
            next_week_schedules.append(schedule)
    
    return CareScheduleGroup(
        today_schedules=today_schedules,
        past_schedules=past_schedules,
        upcoming_schedules=upcoming_schedules,
        this_week_schedules=this_week_schedules,
        next_week_schedules=next_week_schedules
    )

@router.get("/seniors", response_model=List[SeniorResponse])
async def get_assigned_seniors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """담당 시니어 목록 조회"""
    try:
        # 케어기버 프로필 확인
        if not current_user.caregiver_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="케어기버 정보를 찾을 수 없습니다."
            )
        
        caregiver = current_user.caregiver_profile
        
        seniors = db.query(Senior).filter(
            Senior.caregiver_id == caregiver.id
        ).all()
        
        return seniors
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"시니어 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/attendance/checkin")
async def check_in_attendance(
    senior_id: int = Form(...),
    location: str = Form(...),
    attendance_status: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """출근 체크인"""
    try:
        # 케어기버 프로필 확인
        if not current_user.caregiver_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="케어기버 정보를 찾을 수 없습니다."
            )
        
        caregiver = current_user.caregiver_profile
        
        # 시니어 확인
        senior = db.query(Senior).filter(Senior.id == senior_id).first()
        if not senior:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="시니어를 찾을 수 없습니다."
            )
        
        # 돌봄 세션 생성
        care_session = CareSession(
            caregiver_id=caregiver.id,
            senior_id=senior_id,
            start_time=datetime.utcnow(),
            start_location=location,
            status="active"
        )
        
        db.add(care_session)
        db.commit()
        db.refresh(care_session)
        
        # 출석 로그 생성
        from ..models.care import AttendanceLog
        
        attendance_log = AttendanceLog(
            care_session_id=care_session.id,
            type="checkin",
            location=location,
            attendance_status=attendance_status
        )
        
        db.add(attendance_log)
        db.commit()
        
        return {
            "message": "출근 체크가 완료되었습니다.",
            "session_id": care_session.id,
            "start_time": care_session.start_time,
            "attendance_status": attendance_status
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"출근 체크 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/attendance/checkout")
async def check_out_attendance(
    session_id: int = Form(...),
    location: str = Form(...),
    attendance_status: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """퇴근 체크아웃"""
    try:
        # 돌봄 세션 조회
        care_session = db.query(CareSession).filter(
            CareSession.id == session_id,
            CareSession.caregiver_id == current_user.caregiver_profile.id
        ).first()
        
        if not care_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="돌봄 세션을 찾을 수 없습니다."
            )
        
        if care_session.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 종료된 세션입니다."
            )
        
        # 돌봄 세션 종료
        care_session.end_time = datetime.utcnow()
        care_session.end_location = location
        care_session.status = "completed"
        
        # 출석 로그 생성
        from ..models.care import AttendanceLog
        
        attendance_log = AttendanceLog(
            care_session_id=care_session.id,
            type="checkout",
            location=location,
            attendance_status=attendance_status
        )
        
        db.add(attendance_log)
        db.commit()
        
        return {
            "message": "퇴근 체크가 완료되었습니다.",
            "session_id": care_session.id,
            "end_time": care_session.end_time,
            "duration": str(care_session.end_time - care_session.start_time),
            "attendance_status": attendance_status
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"퇴근 체크 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/checklist/{senior_id}")
async def get_checklist_template(
    senior_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """체크리스트 템플릿 조회"""
    try:
        # 시니어 정보 조회
        senior = db.query(Senior).filter(Senior.id == senior_id).first()
        if not senior:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="시니어를 찾을 수 없습니다."
            )
        
        # 케어 서비스를 통해 체크리스트 템플릿 생성
        care_service = CareService(db)
        template = care_service.get_checklist_template(senior)
        
        return {
            "senior_info": senior,
            "template": template
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"체크리스트 템플릿 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/checklist")
async def submit_checklist(
    checklist_data: ChecklistSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """체크리스트 제출"""
    try:
        # 돌봄 세션 확인
        care_session = db.query(CareSession).filter(
            CareSession.id == checklist_data.session_id,
            CareSession.caregiver_id == current_user.id
        ).first()
        
        if not care_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="돌봄 세션을 찾을 수 없습니다."
            )
        
        # 체크리스트 응답 저장
        for response in checklist_data.responses:
            checklist_response = ChecklistResponse(
                session_id=checklist_data.session_id,
                question_key=response.question_key,
                question_text=response.question_text,
                answer=response.answer,
                notes=response.notes
            )
            db.add(checklist_response)
        
        db.commit()
        
        return {
            "message": "체크리스트가 성공적으로 제출되었습니다.",
            "session_id": checklist_data.session_id,
            "responses_count": len(checklist_data.responses)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"체크리스트 제출 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/care-note")
async def submit_care_note(
    care_note_data: CareNoteSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """돌봄노트 제출"""
    try:
        # 돌봄 세션 확인
        care_session = db.query(CareSession).filter(
            CareSession.id == care_note_data.session_id,
            CareSession.caregiver_id == current_user.id
        ).first()
        
        if not care_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="돌봄 세션을 찾을 수 없습니다."
            )
        
        # 돌봄노트 저장
        for note in care_note_data.notes:
            care_note = CareNote(
                session_id=care_note_data.session_id,
                question_type=note.question_type,
                question_text=note.question_text,
                content=note.content
            )
            db.add(care_note)
        
        db.commit()
        
        # === 돌봄노트 제출 완료 후 AI 분석 워크플로우 트리거 ===
        # 세션 상태를 완료로 업데이트
        care_session.status = "completed"
        care_session.end_time = datetime.now()
        db.commit()
        
        # 새로운 카테고리별 상세 분석 워크플로우 트리거
        await trigger_enhanced_ai_analysis_workflow(care_note_data.session_id)
        
        return {
            "message": "돌봄노트가 성공적으로 제출되었습니다.",
            "session_id": care_note_data.session_id,
            "notes_count": len(care_note_data.notes),
            "ai_analysis_triggered": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"돌봄노트 제출 중 오류가 발생했습니다: {str(e)}"
        )

async def trigger_enhanced_ai_analysis_workflow(session_id: int):
    """카테고리별 상세 분석이 포함된 AI 워크플로우 트리거"""
    import requests
    from datetime import datetime
    
    webhook_data = {
        "session_id": session_id,
        "trigger_time": datetime.now().isoformat(),
        "analysis_type": "enhanced_category_analysis"
    }
    
    # 새로운 카테고리별 상세 분석 워크플로우 호출
    try:
        response = requests.post(
            "http://pay.gzonesoft.co.kr:10006/webhook/weekly-ai-comment-enhanced",
            json=webhook_data,
            timeout=30
        )
        print(f"Enhanced AI Analysis Workflow triggered: {response.status_code}")
        return {"status": "triggered", "session_id": session_id}
    except Exception as e:
        print(f"Enhanced AI Analysis Workflow failed: {e}")
        
        # 실패 시 기존 워크플로우로 폴백
        try:
            fallback_response = requests.post(
                "http://pay.gzonesoft.co.kr:10006/webhook/weekly-ai-comment",
                json=webhook_data,
                timeout=30
            )
            print(f"Fallback to basic workflow: {fallback_response.status_code}")
            return {"status": "fallback", "session_id": session_id}
        except Exception as fallback_error:
            print(f"Fallback workflow also failed: {fallback_error}")
            return {"status": "failed", "session_id": session_id}

@router.get("/care-history")
async def get_care_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """돌봄 이력 조회"""
    try:
        query = db.query(CareSession).filter(
            CareSession.caregiver_id == current_user.id
        )
        
        if start_date:
            query = query.filter(CareSession.start_time >= start_date)
        if end_date:
            query = query.filter(CareSession.start_time <= end_date)
        
        care_sessions = query.order_by(CareSession.start_time.desc()).all()
        
        return {
            "care_sessions": care_sessions,
            "total_count": len(care_sessions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"돌봄 이력 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/profile")
async def get_caregiver_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """케어기버 프로필 조회"""
    try:
        return {
            "user_info": current_user,
            "assigned_seniors_count": db.query(Senior).filter(
                Senior.caregiver_id == current_user.id
            ).count(),
            "total_sessions": db.query(CareSession).filter(
                CareSession.caregiver_id == current_user.id
            ).count()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"프로필 조회 중 오류가 발생했습니다: {str(e)}"
        )

# 날짜별 돌봄 일정 조회 API 추가
@router.get("/schedule")
async def get_care_schedule_by_date(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """날짜별 돌봄 일정 조회"""
    try:
        # 케어기버 프로필 확인
        if not current_user.caregiver_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="케어기버 정보를 찾을 수 없습니다."
            )
        
        caregiver = current_user.caregiver_profile
        
        # 기본값 설정 (지정하지 않으면 이번 달)
        if not start_date:
            today = date.today()
            start_date = today.replace(day=1)  # 이번 달 1일
        
        if not end_date:
            # 다음 달 1일 - 1일 = 이번 달 마지막 날
            if start_date.month == 12:
                next_month = start_date.replace(year=start_date.year + 1, month=1)
            else:
                next_month = start_date.replace(month=start_date.month + 1)
            end_date = next_month - timedelta(days=1)
        
        # 돌봄 일정 조회
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                cc.id,
                cc.senior_id,
                s.name as senior_name,
                s.photo as senior_photo,
                cc.care_date,
                cc.start_time,
                cc.end_time,
                cc.status,
                cc.notes,
                nh.name as nursing_home_name,
                nh.address as nursing_home_address,
                cs.id as session_id,
                cs.status as session_status
            FROM care_calendar cc
            JOIN seniors s ON cc.senior_id = s.id
            LEFT JOIN nursing_homes nh ON s.nursing_home_id = nh.id
            LEFT JOIN care_sessions cs ON (cs.care_calendar_id = cc.id)
            WHERE cc.caregiver_id = :caregiver_id
            AND cc.care_date BETWEEN :start_date AND :end_date
            ORDER BY cc.care_date ASC, cc.start_time ASC
        """)
        
        result = db.execute(query, {
            "caregiver_id": caregiver.id,
            "start_date": start_date,
            "end_date": end_date
        })
        
        schedule_rows = result.fetchall()
        
        schedules = []
        for row in schedule_rows:
            schedule = {
                "id": row.id,
                "senior_id": row.senior_id,
                "senior_name": row.senior_name,
                "senior_photo": row.senior_photo,
                "care_date": row.care_date.isoformat(),
                "start_time": row.start_time.strftime("%H:%M"),
                "end_time": row.end_time.strftime("%H:%M"),
                "status": row.status,
                "nursing_home_name": row.nursing_home_name,
                "nursing_home_address": row.nursing_home_address,
                "notes": row.notes,
                "session_id": row.session_id,
                "session_status": row.session_status,
                "is_today": row.care_date == date.today()
            }
            schedules.append(schedule)
        
        return {
            "caregiver_id": caregiver.id,
            "caregiver_name": caregiver.name,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "schedules": schedules,
            "total_count": len(schedules)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"돌봄 일정 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/care-schedule/{senior_id}")
async def get_care_schedule(
    senior_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """시니어별 케어 스케줄 조회"""
    
    # 케어기버 권한 확인
    if not current_user.caregiver_profile:
        raise HTTPException(status_code=403, detail="케어기버 권한이 필요합니다")
    
    schedules = db.query(CareSchedule).filter(
        CareSchedule.senior_id == senior_id,
        CareSchedule.caregiver_id == current_user.caregiver_profile.id,
        CareSchedule.is_active == True
    ).all()
    
    # 요일명 매핑
    day_names = ["일", "월", "화", "수", "목", "금", "토"]
    
    schedule_data = []
    for schedule in schedules:
        # 다음 케어 날짜 계산
        next_care_date = calculate_next_care_date(schedule.day_of_week)
        
        schedule_data.append({
            "id": schedule.id,
            "day_of_week": schedule.day_of_week,
            "day_name": day_names[schedule.day_of_week],
            "start_time": schedule.start_time.strftime("%H:%M"),
            "end_time": schedule.end_time.strftime("%H:%M"),
            "next_care_date": next_care_date.strftime("%Y-%m-%d"),
            "notes": schedule.notes
        })
    
    return {
        "senior_id": senior_id,
        "schedules": schedule_data,
        "total_schedules": len(schedule_data)
    }

def calculate_next_care_date(day_of_week: int) -> date:
    """다음 케어 날짜 계산"""
    today = date.today()
    days_ahead = day_of_week - today.weekday()
    
    if days_ahead <= 0:  # 오늘이거나 지나간 요일
        days_ahead += 7
    
    return today + timedelta(days=days_ahead)

@router.post("/care-schedule")
async def create_care_schedule(
    schedule_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새로운 케어 스케줄 생성"""
    
    if not current_user.caregiver_profile:
        raise HTTPException(status_code=403, detail="케어기버 권한이 필요합니다")
    
    # 중복 스케줄 확인
    existing = db.query(CareSchedule).filter(
        CareSchedule.senior_id == schedule_data["senior_id"],
        CareSchedule.caregiver_id == current_user.caregiver_profile.id,
        CareSchedule.day_of_week == schedule_data["day_of_week"],
        CareSchedule.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="해당 요일에 이미 스케줄이 있습니다")
    
    new_schedule = CareSchedule(
        caregiver_id=current_user.caregiver_profile.id,
        senior_id=schedule_data["senior_id"],
        day_of_week=schedule_data["day_of_week"],
        start_time=datetime.strptime(schedule_data["start_time"], "%H:%M").time(),
        end_time=datetime.strptime(schedule_data["end_time"], "%H:%M").time(),
        notes=schedule_data.get("notes", "")
    )
    
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    
    return {
        "message": "케어 스케줄이 생성되었습니다",
        "schedule_id": new_schedule.id
    }
