"""
스키마 패키지 __init__.py
"""
from .user import *
from .senior import *
from .care import *
from .report import *
from .home import *

__all__ = [
    # User schemas
    "UserLogin", "UserCreate", "UserResponse", "Token",
    "CaregiverResponse", "GuardianResponse", "AdminResponse",
    
    # Senior schemas
    "SeniorBase", "SeniorCreate", "SeniorUpdate", "SeniorResponse",
    "SeniorDiseaseBase", "SeniorDiseaseCreate", "SeniorDiseaseResponse",
    "SeniorDetailResponse",
    
    # Care schemas
    "CareSessionBase", "CareSessionCreate", "CareSessionUpdate", "CareSessionResponse",
    "AttendanceCheckIn", "AttendanceCheckOut", "AttendanceLogResponse",
    "ChecklistResponseItem", "ChecklistSubmission", "ChecklistResponseQuery",
    "CareNoteItem", "CareNoteSubmission", "CareNoteResponse",
    "CareHistoryResponse",
    
    # Report schemas
    "AIReportBase", "AIReportCreate", "AIReportResponse", "AIReportDetailResponse",
    "FeedbackBase", "FeedbackSubmission", "FeedbackResponse", "FeedbackDetailResponse",
    "NotificationBase", "NotificationCreate", "NotificationResponse", "NotificationDetailResponse",
    "AIAnalysisResult", "ChecklistAnalysisResponse",
    "TrendingKeyword", "TrendingKeywordsResponse",
    
    # Home schemas
    "CaregiverHomeResponse", "GuardianHomeResponse", "AdminHomeResponse",
    "DashboardStats", "ActivityLog",
]
