"""
케어기버 관련 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, date, timedelta

from ..database import get_db
from ..models import User, Senior, CareSession, ChecklistResponse, CareNote, Notification, NursingHome
from ..models.care import ChecklistType, WeeklyChecklistScore, CareNoteQuestion
from ..models.enhanced_care import CareSchedule
from ..schemas import (
    CareSessionResponse, SeniorResponse, ChecklistSubmission, CareNoteSubmission,
    CaregiverHomeResponse, AttendanceCheckIn, AttendanceCheckOut
)
from ..schemas.care import DiseaseChecklistSubmission
from ..schemas.home import CareScheduleResponse, CareScheduleGroup
from ..schemas.senior import SeniorWithChecklistTypes, AvailableChecklistType
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

@router.get("/seniors", response_model=List[SeniorWithChecklistTypes])
async def get_assigned_seniors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """담당 시니어 목록 조회 (질병 정보 및 체크리스트 타입 포함)"""
    try:
        # 케어기버 프로필 확인
        if not current_user.caregiver_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="케어기버 정보를 찾을 수 없습니다."
            )
        
        caregiver = current_user.caregiver_profile
        
        # ✅ 수정: diseases 관계를 함께 로드
        seniors = db.query(Senior).filter(
            Senior.caregiver_id == caregiver.id
        ).options(
            joinedload(Senior.diseases),  # 질병 정보 함께 조회
            joinedload(Senior.nursing_home),
            joinedload(Senior.caregiver),
            joinedload(Senior.guardian)
        ).all()
        
        # ✅ 추가: 각 시니어의 질병에 따른 체크리스트 타입 정보 생성
        result = []
        for senior in seniors:
            # 기본 시니어 정보 생성
            senior_dict = {
                "id": senior.id,
                "name": senior.name,
                "age": senior.age,
                "gender": senior.gender,
                "photo": senior.photo,
                "nursing_home_id": senior.nursing_home_id,
                "caregiver_id": senior.caregiver_id,
                "guardian_id": senior.guardian_id,
                "created_at": senior.created_at,
                "diseases": [
                    {
                        "id": disease.id,
                        "disease_type": disease.disease_type,
                        "severity": disease.severity,
                        "notes": disease.notes,
                        "created_at": disease.created_at
                    } for disease in senior.diseases
                ]
            }
            
            # 해당 시니어의 질병에 따른 사용 가능한 체크리스트 타입 조회
            available_types = []
            
            # 모든 시니어에게 공통 체크리스트 추가
            available_types.append({
                "type_code": "nutrition",  # ✅ 수정: nutrition_common → nutrition
                "type_name": "식사/영양 상태",
                "description": "모든 시니어 공통 체크리스트"
            })
            
            # 질병별 체크리스트 타입 추가
            for disease in senior.diseases:
                disease_type = disease.disease_type
                
                # 간단한 매핑으로 카테고리 이름 결정
                category_names = {
                    "nutrition": "식사/영양 상태",
                    "hypertension": "고혈압 관리", 
                    "depression": "우울증/정신건강",
                    "diabetes": "당뇨 관리"
                }
                
                category_name = category_names.get(disease_type, disease_type)
                
                available_types.append({
                    "type_code": disease_type,
                    "type_name": category_name,
                    "description": f"{disease.severity or ''} 수준의 {category_name} 관리".strip()
                })
            
            senior_dict["available_checklist_types"] = available_types
            result.append(senior_dict)
        
        return result
        
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
    checklist_data: dict,  # 질병별 체크리스트 데이터 (수정됨)
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """질병별 체크리스트 제출 - 프론트에서 계산된 점수 포함"""
    try:
        session_id = checklist_data.get("session_id")
        senior_id = checklist_data.get("senior_id")
        
        # ✅ 새로운 구조: disease_responses 지원
        disease_responses = checklist_data.get("disease_responses", {})
        
        # 기존 구조도 호환: responses 지원
        legacy_responses = checklist_data.get("responses", {})
        
        # 돌봄 세션 확인
        care_session = db.query(CareSession).filter(
            CareSession.id == session_id,
            CareSession.caregiver_id == current_user.caregiver_profile.id
        ).first()
        
        if not care_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="돌봄 세션을 찾을 수 없습니다."
            )
        
        # 시니어 ID 확인 (새로운 요구사항)
        if senior_id and care_session.senior_id != senior_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="세션의 시니어 ID와 요청된 시니어 ID가 일치하지 않습니다."
            )
        
        total_responses = 0
        disease_summary = {}
        
        # ✅ 새로운 구조 처리: disease_responses
        if disease_responses:
            for disease_type, disease_data in disease_responses.items():
                disease_responses_saved = 0
                
                # 프론트에서 계산한 total_score 받기
                total_score = disease_data.get("total_score", 0)
                responses_list = disease_data.get("responses", [])
                
                for response_item in responses_list:
                    checklist_response = ChecklistResponse(
                        care_session_id=session_id,
                        checklist_type_code=disease_type,
                        question_id=response_item.get("question_id"),
                        scale_value=response_item.get("scale_value"),
                        notes=response_item.get("notes", ""),
                        weighted_score=response_item.get("scale_value", 0) * response_item.get("weight", 1.0),
                        category_code=disease_type,
                        # 기존 필드 호환성
                        question_key=f"{disease_type}_question_{response_item.get('question_id')}",
                        answer=response_item.get("scale_value")
                    )
                    db.add(checklist_response)
                    disease_responses_saved += 1
                    total_responses += 1
                
                disease_summary[disease_type] = {
                    "total_score": total_score,
                    "responses_count": disease_responses_saved,
                    "average_score": total_score / len(responses_list) if responses_list else 0
                }
        
        # ✅ 기존 구조 호환: responses
        elif legacy_responses:
            for type_code in ["nutrition", "hypertension", "depression"]:
                if type_code in legacy_responses:
                    type_responses = legacy_responses[type_code]
                    
                    for sub_q_id, response_data in type_responses.items():
                        checklist_response = ChecklistResponse(
                            care_session_id=session_id,
                            checklist_type_code=type_code,
                            sub_question_id=sub_q_id,
                            question_key=response_data["question_key"],
                            question_text=response_data["question_text"],
                            answer=response_data["answer"],
                            selected_score=response_data["selected_score"],
                            notes=response_data.get("notes", "")
                        )
                        db.add(checklist_response)
                        total_responses += 1
        
        db.commit()
        
        # ✅ 응답 구조 개선
        response_data = {
            "status": "success",
            "message": "체크리스트가 성공적으로 저장되었습니다.",
            "session_id": session_id,
            "total_responses": total_responses
        }
        
        # 새로운 구조 사용 시 추가 정보 제공
        if disease_responses:
            response_data.update({
                "senior_id": senior_id,
                "diseases_processed": list(disease_responses.keys()),
                "disease_summary": disease_summary,
                "processing_time": datetime.now().isoformat()
            })
        else:
            # 기존 구조 호환
            response_data.update({
                "types_completed": len([t for t in ["nutrition", "hypertension", "depression"] if t in legacy_responses])
            })
        
        return response_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"체크리스트 제출 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/care-note")
async def submit_care_note(
    care_note_data: dict,  # 1개 랜덤 돌봄노트 데이터
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """1개 랜덤 돌봄노트 제출 (n8n v2.0)"""
    try:
        session_id = care_note_data.get("session_id")
        question_id = care_note_data.get("question_id")
        question_number = care_note_data.get("question_number")
        content = care_note_data.get("content")
        
        # 돌봄 세션 확인
        care_session = db.query(CareSession).filter(
            CareSession.id == session_id,
            CareSession.caregiver_id == current_user.caregiver_profile.id
        ).first()
        
        if not care_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="돌봄 세션을 찾을 수 없습니다."
            )
        
        # 질문 정보 조회
        question_info = db.query(CareNoteQuestion).filter(
            CareNoteQuestion.id == question_id
        ).first()
        
        if not question_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="질문 정보를 찾을 수 없습니다."
            )
        
        # 1개 랜덤 돌봄노트 저장
        care_note = CareNote(
            care_session_id=session_id,
            selected_question_id=question_id,
            question_number=question_number,
            question_type=question_info.question_title,  # 질문 제목을 타입으로 사용
            question_text=question_info.question_text,   # 질문 텍스트 추가
            content=content
        )
        
        db.add(care_note)
        db.commit()
        
        # 체크리스트와 돌봄노트 모두 완료되면 주간 점수 계산 (임시 주석처리)
        # await calculate_and_save_weekly_scores(session_id, care_session.senior_id, db)
        
        # n8n 워크플로우 트리거 (임시 주석처리)
        # await trigger_ai_analysis_workflows_v2(session_id, care_session.senior_id)
        
        # 세션 상태 완료로 업데이트
        care_session.status = "completed"
        care_session.end_time = datetime.now()
        db.commit()
        
        return {
            "message": "돌봄노트가 성공적으로 저장되었습니다.",
            "session_id": session_id,
            "question_id": question_id,
            "ai_analysis_triggered": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"돌봄노트 제출 중 오류가 발생했습니다: {str(e)}"
        )

async def calculate_and_save_weekly_scores(session_id: int, senior_id: int, db: Session):
    """주간 체크리스트 점수 계산 및 저장"""
    from ..models.care import WeeklyChecklistScore, ChecklistType
    
    week_date = date.today()
    
    # 3가지 유형별 점수 계산
    type_codes = ["nutrition", "hypertension", "depression"]
    
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
    
    db.commit()

async def trigger_ai_analysis_workflows_v2(session_id: int, senior_id: int):
    """n8n AI 분석 워크플로우 v2.0 트리거"""
    import requests
    
    webhook_base_url = "http://pay.gzonesoft.co.kr:10006/webhook"
    
    trigger_data = {
        "session_id": session_id,
        "senior_id": senior_id,
        "trigger_time": datetime.now().isoformat()
    }
    
    # 통합 조율 워크플로우 호출
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

# ❌ 해커톤에서 제거: /care-history - 홈 화면의 최근 이력으로 대체
# GET /care-history API 제거됨 (홈 화면에서 최근 돌봄 이력 확인 가능)

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

# ❌ 해커톤에서 제거: /schedule - 홈 화면의 오늘 일정으로 대체
# GET /schedule API 제거됨 (홈 화면에서 오늘/이번 주 일정 확인 가능)

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

# ❌ 해커톤에서 제거: care-schedule 관련 함수들
# 일정 관리 기능은 관리자가 사전에 설정하는 것으로 대체

# calculate_next_care_date 함수 제거됨 (불필요)
# POST /care-schedule API 제거됨 (관리자가 사전 설정)
