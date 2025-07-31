import requests
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.care import CareSession, ChecklistResponse, CareNote
from app.exceptions import RequiredTasksIncomplete
from app.config import settings

class CheckoutService:
    
    @staticmethod
    def validate_required_tasks(db: Session, care_session_id: int) -> tuple[bool, List[str]]:
        """필수 작업 완료 확인"""
        missing_tasks = []
        
        # 체크리스트 완료 확인
        checklist_count = db.query(ChecklistResponse).filter(
            ChecklistResponse.care_session_id == care_session_id
        ).count()
        
        if checklist_count == 0:
            missing_tasks.append("체크리스트")
        
        # 돌봄노트 완료 확인
        care_note_count = db.query(CareNote).filter(
            CareNote.care_session_id == care_session_id
        ).count()
        
        if care_note_count == 0:
            missing_tasks.append("돌봄노트")
        
        return len(missing_tasks) == 0, missing_tasks
    
    @staticmethod
    async def trigger_n8n_workflow(session_id: int, senior_id: int) -> bool:
        """n8n 워크플로우 자동 트리거"""
        try:
            n8n_url = getattr(settings, 'N8N_WEBHOOK_URL', 'http://pay.gzonesoft.co.kr:10006')
            response = requests.post(
                f"{n8n_url}/webhook/complete-ai-analysis",
                json={
                    "session_id": session_id,
                    "senior_id": senior_id,
                    "trigger_time": datetime.now().isoformat()
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"n8n 트리거 실패: {e}")
            return False
