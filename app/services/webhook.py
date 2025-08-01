"""
n8n 웹훅 호출 서비스
케어기버 퇴근 시 AI 분석 워크플로우 자동 트리거
"""

import requests
import urllib3
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import Caregiver
from app.models.senior import Senior
from app.models.care import CareSession

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 로거 설정
logger = logging.getLogger(__name__)

class N8NWebhookService:
    """n8n 웹훅 호출 서비스"""
    
    def __init__(self):
        self.webhook_url = "https://pay.gzonesoft.co.kr:10006/webhook/complete-ai-analysis"
        self.timeout = 30
        self.enabled = True
        
    async def trigger_ai_analysis(
        self, 
        db: Session, 
        care_session_id: int,
        caregiver_id: int
    ) -> Dict[str, Any]:
        """
        AI 분석 워크플로우 트리거
        """
        
        if not self.enabled:
            logger.info("n8n 웹훅이 비활성화되어 있습니다.")
            return {"status": "disabled", "message": "웹훅이 비활성화됨"}
        
        try:
            # 필요한 데이터 조회
            webhook_data = await self._prepare_webhook_data(
                db, care_session_id, caregiver_id
            )
            
            if not webhook_data:
                return {"status": "error", "message": "웹훅 데이터 준비 실패"}
            
            # 웹훅 호출
            response = await self._call_webhook(webhook_data)
            
            # 결과 로깅
            logger.info(f"n8n 웹훅 호출 성공: session_id={care_session_id}")
            
            return {
                "status": "success",
                "webhook_data": webhook_data,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"n8n 웹훅 호출 실패: {str(e)}")
            return {
                "status": "error", 
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _prepare_webhook_data(
        self, 
        db: Session, 
        care_session_id: int,
        caregiver_id: int
    ) -> Optional[Dict[str, Any]]:
        """웹훅 호출에 필요한 데이터 준비"""
        
        try:
            # 돌봄 세션 조회
            care_session = db.query(CareSession).filter(
                CareSession.id == care_session_id
            ).first()
            
            if not care_session:
                logger.error(f"돌봄 세션을 찾을 수 없음: {care_session_id}")
                return None
            
            # 케어기버 조회
            caregiver = db.query(Caregiver).filter(
                Caregiver.id == caregiver_id
            ).first()
            
            if not caregiver:
                logger.error(f"케어기버를 찾을 수 없음: {caregiver_id}")
                return None
            
            # 시니어 조회
            senior = db.query(Senior).filter(
                Senior.id == care_session.senior_id
            ).first()
            
            if not senior:
                logger.error(f"시니어를 찾을 수 없음: {care_session.senior_id}")
                return None
            
            # 웹훅 데이터 구성
            webhook_data = {
                "session_id": care_session_id,
                "senior_id": care_session.senior_id,
                "caregiver_name": caregiver.name,
                "senior_name": senior.name,
                "care_date": datetime.now().strftime("%Y-%m-%d"),
                "care_start_time": care_session.start_time.isoformat() if care_session.start_time else None,
                "care_end_time": datetime.now().isoformat(),
                "trigger_source": "caregiver_checkout"
            }
            
            logger.info(f"웹훅 데이터 준비 완료: {webhook_data}")
            return webhook_data
            
        except Exception as e:
            logger.error(f"웹훅 데이터 준비 중 오류: {str(e)}")
            return None
    
    async def _call_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """실제 웹훅 HTTP 호출"""
        
        try:
            logger.info(f"n8n 웹훅 호출 시작: {self.webhook_url}")
            
            # HTTP POST 요청
            response = requests.post(
                url=self.webhook_url,
                json=data,
                timeout=self.timeout,
                verify=False,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "GoodHands-Backend/1.0"
                }
            )
            
            # 응답 확인
            response.raise_for_status()
            
            result = {
                "status_code": response.status_code,
                "response_data": response.json() if response.text else {},
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
            
            logger.info(f"웹훅 호출 성공: {result}")
            return result
            
        except requests.exceptions.Timeout:
            error_msg = f"웹훅 호출 타임아웃 ({self.timeout}초)"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        except requests.exceptions.ConnectionError:
            error_msg = "웹훅 서버 연결 실패"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"웹훅 HTTP 오류: {e.response.status_code}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"웹훅 호출 중 예상치 못한 오류: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def test_webhook_connection(self) -> Dict[str, Any]:
        """웹훅 연결 테스트 (개발용)"""
        
        test_data = {
            "session_id": 999,
            "senior_id": 1,
            "caregiver_name": "테스트케어기버",
            "senior_name": "테스트시니어",
            "care_date": datetime.now().strftime("%Y-%m-%d"),
            "trigger_source": "connection_test"
        }
        
        try:
            response = requests.post(
                url=self.webhook_url,
                json=test_data,
                timeout=10,
                verify=False,
                headers={"Content-Type": "application/json"}
            )
            
            return {
                "status": "success",
                "status_code": response.status_code,
                "response": response.json() if response.text else {},
                "test_data": test_data
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "test_data": test_data
            }

# 싱글톤 인스턴스 생성
webhook_service = N8NWebhookService()
