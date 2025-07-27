"""
홈 화면 관련 스키마
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date, time
from .senior import SeniorResponse
from .care import CareSessionResponse
from .report import AIReportResponse, NotificationResponse

"""
홈 화면 관련 스키마
"""
from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import datetime, date, time, timedelta
from .senior import SeniorResponse
from .care import CareSessionResponse
from .report import AIReportResponse, NotificationResponse

class CareScheduleResponse(BaseModel):
    id: int
    senior_id: int
    senior_name: str
    senior_photo: Optional[str]
    care_date: date
    start_time: time
    end_time: time
    status: str  # scheduled, completed, cancelled, rescheduled
    is_today: bool
    nursing_home_name: Optional[str]
    nursing_home_address: Optional[str]
    notes: Optional[str]
    
    @validator('start_time', pre=True)
    def convert_start_time(cls, v):
        if isinstance(v, timedelta):
            # timedelta를 time으로 변환
            total_seconds = int(v.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return time(hours, minutes)
        return v
    
    @validator('end_time', pre=True)
    def convert_end_time(cls, v):
        if isinstance(v, timedelta):
            # timedelta를 time으로 변환
            total_seconds = int(v.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return time(hours, minutes)
        return v
    
    class Config:
        from_attributes = True

class CareScheduleGroup(BaseModel):
    today_schedules: List[CareScheduleResponse]
    past_schedules: List[CareScheduleResponse] 
    upcoming_schedules: List[CareScheduleResponse]
    this_week_schedules: List[CareScheduleResponse]
    next_week_schedules: List[CareScheduleResponse]

class CaregiverHomeResponse(BaseModel):
    caregiver_name: str
    caregiver_id: int
    today_sessions: List[CareSessionResponse]
    seniors: List[SeniorResponse]
    notifications: List[NotificationResponse]
    care_schedules: CareScheduleGroup
    total_assigned_seniors: int
    completed_sessions_this_week: int
    pending_schedules_today: int
    
    class Config:
        from_attributes = True

class GuardianHomeResponse(BaseModel):
    guardian_name: str
    seniors: List[SeniorResponse]
    recent_reports: List[AIReportResponse]
    unread_notifications: List[NotificationResponse]
    
    class Config:
        from_attributes = True

class AdminHomeResponse(BaseModel):
    admin_name: str
    total_users: int
    total_seniors: int
    total_reports: int
    recent_activities: List[dict]
    system_status: dict
    
    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_caregivers: int
    total_guardians: int
    total_seniors: int
    active_sessions: int
    reports_today: int
    pending_feedbacks: int

class ActivityLog(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_type: str
    action: str
    description: str
    timestamp: datetime
    
    class Config:
        from_attributes = True
