"""
라우터 초기화 파일
"""
from .caregiver import router as caregiver_router
from .guardian import router as guardian_router
from .admin import router as admin_router
from .ai import router as ai_router

__all__ = [
    "caregiver_router", 
    "guardian_router",
    "admin_router",
    "ai_router"
]
