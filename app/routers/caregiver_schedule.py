"""
케어기버 일정 관련 추가 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta

from ..database import get_db
from ..models import User, Senior, CareSession
from ..services.auth import get_current_user

router = APIRouter()

@router.post("/start-care/{schedule_id}")
async def start_care_session(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """예정된 돌봄 일정에서 실제 돌봄 시작"""
    try:
        # 케어기버 프로필 확인
        if not current_user.caregiver_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="케어기버 정보를 찾을 수 없습니다."
            )
        
        caregiver = current_user.caregiver_profile
        
        # 돌봄 일정 확인
        from sqlalchemy import text
        query = text("""
            SELECT cc.*, s.name as senior_name
            FROM care_calendar cc
            JOIN seniors s ON cc.senior_id = s.id
            WHERE cc.id = :schedule_id 
            AND cc.caregiver_id = :caregiver_id
            AND cc.status = 'scheduled'
        """)
        
        result = db.execute(query, {
            "schedule_id": schedule_id,
            "caregiver_id": caregiver.id
        }).fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="예정된 돌봄 일정을 찾을 수 없습니다."
            )
        
        # 새로운 돌봄 세션 생성
        care_session = CareSession(
            caregiver_id=caregiver.id,
            senior_id=result.senior_id,
            care_calendar_id=schedule_id,
            start_time=datetime.now(),
            status="active"
        )
        
        db.add(care_session)
        
        # 일정 상태를 '진행중'으로 업데이트
        update_query = text("""
            UPDATE care_calendar 
            SET status = 'in_progress' 
            WHERE id = :schedule_id
        """)
        db.execute(update_query, {"schedule_id": schedule_id})
        
        db.commit()
        db.refresh(care_session)
        
        return {
            "message": f"{result.senior_name}님 돌봄이 시작되었습니다.",
            "session_id": care_session.id,
            "schedule_id": schedule_id,
            "senior_name": result.senior_name,
            "start_time": care_session.start_time,
            "status": "active"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"돌봄 시작 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/today-schedule")
async def get_today_schedule(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """오늘의 돌봄 일정 상세 조회"""
    try:
        # 케어기버 프로필 확인
        if not current_user.caregiver_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="케어기버 정보를 찾을 수 없습니다."
            )
        
        caregiver = current_user.caregiver_profile
        today = date.today()
        
        # 오늘의 돌봄 일정 조회
        from sqlalchemy import text
        from datetime import time as time_obj
        
        def convert_timedelta_to_time(td):
            """timedelta를 time 객체로 변환"""
            if td is None:
                return None
            if isinstance(td, timedelta):
                total_seconds = int(td.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                return time_obj(hours, minutes, seconds)
            return td
        query = text("""
            SELECT 
                cc.id as schedule_id,
                cc.senior_id,
                s.name as senior_name,
                s.photo as senior_photo,
                s.age,
                s.gender,
                cc.care_date,
                cc.start_time,
                cc.end_time,
                cc.status as schedule_status,
                cc.notes,
                nh.name as nursing_home_name,
                nh.address as nursing_home_address,
                nh.phone as nursing_home_phone,
                cs.id as session_id,
                cs.status as session_status,
                cs.start_time as actual_start_time,
                sd.disease_type
            FROM care_calendar cc
            JOIN seniors s ON cc.senior_id = s.id
            LEFT JOIN nursing_homes nh ON s.nursing_home_id = nh.id
            LEFT JOIN care_sessions cs ON cs.care_calendar_id = cc.id
            LEFT JOIN senior_diseases sd ON sd.senior_id = s.id
            WHERE cc.caregiver_id = :caregiver_id
            AND cc.care_date = :today
            ORDER BY cc.start_time ASC
        """)
        
        result = db.execute(query, {
            "caregiver_id": caregiver.id,
            "today": today
        })
        
        rows = result.fetchall()
        
        # 시니어별로 그룹화
        schedules_by_senior = {}
        for row in rows:
            senior_id = row.senior_id
            if senior_id not in schedules_by_senior:
                # timedelta를 time으로 변환
                start_time_converted = convert_timedelta_to_time(row.start_time)
                end_time_converted = convert_timedelta_to_time(row.end_time)
                
                schedules_by_senior[senior_id] = {
                    "schedule_id": row.schedule_id,
                    "senior_id": senior_id,
                    "senior_name": row.senior_name,
                    "senior_photo": row.senior_photo,
                    "age": row.age,
                    "gender": row.gender,
                    "care_date": row.care_date.isoformat(),
                    "start_time": start_time_converted.strftime("%H:%M") if start_time_converted else None,
                    "end_time": end_time_converted.strftime("%H:%M") if end_time_converted else None,
                    "schedule_status": row.schedule_status,
                    "notes": row.notes,
                    "nursing_home": {
                        "name": row.nursing_home_name,
                        "address": row.nursing_home_address,
                        "phone": row.nursing_home_phone
                    },
                    "session_id": row.session_id,
                    "session_status": row.session_status,
                    "actual_start_time": row.actual_start_time.isoformat() if row.actual_start_time else None,
                    "diseases": []
                }
            
            # 질병 정보 추가
            if row.disease_type and row.disease_type not in schedules_by_senior[senior_id]["diseases"]:
                schedules_by_senior[senior_id]["diseases"].append(row.disease_type)
        
        schedules = list(schedules_by_senior.values())
        
        # 시간순 정렬
        schedules.sort(key=lambda x: x["start_time"])
        
        return {
            "caregiver_name": caregiver.name,
            "date": today.isoformat(),
            "day_of_week": ["월", "화", "수", "목", "금", "토", "일"][today.weekday()],
            "total_schedules": len(schedules),
            "schedules": schedules,
            "summary": {
                "scheduled": len([s for s in schedules if s["schedule_status"] == "scheduled"]),
                "in_progress": len([s for s in schedules if s["schedule_status"] == "in_progress"]),
                "completed": len([s for s in schedules if s["schedule_status"] == "completed"])
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"오늘 일정 조회 중 오류가 발생했습니다: {str(e)}"
        )
