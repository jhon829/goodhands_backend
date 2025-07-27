"""
알림 서비스
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.models import User, Notification
from datetime import datetime

class NotificationService:
    def __init__(self, db: Session):
        self.db = db
    
    async def send_notification(
        self,
        sender_id: int,
        receiver_id: int,
        type: str,
        title: str,
        content: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """알림 전송"""
        
        notification = Notification(
            sender_id=sender_id,
            receiver_id=receiver_id,
            type=type,
            title=title,
            content=content,
            data=data
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        # 여기서 실제 푸시 알림 전송 로직을 구현할 수 있습니다
        # await self._send_push_notification(notification)
        
        return notification
    
    async def send_bulk_notification(
        self,
        sender_id: int,
        receiver_ids: List[int],
        type: str,
        title: str,
        content: str,
        data: Optional[Dict[str, Any]] = None
    ) -> List[Notification]:
        """대량 알림 전송"""
        
        notifications = []
        
        for receiver_id in receiver_ids:
            notification = Notification(
                sender_id=sender_id,
                receiver_id=receiver_id,
                type=type,
                title=title,
                content=content,
                data=data
            )
            notifications.append(notification)
        
        self.db.add_all(notifications)
        self.db.commit()
        
        return notifications
    
    def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """알림 읽음 처리"""
        
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.receiver_id == user_id
        ).first()
        
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            self.db.commit()
            return True
        
        return False
    
    def get_unread_count(self, user_id: int) -> int:
        """읽지 않은 알림 개수 조회"""
        
        return self.db.query(Notification).filter(
            Notification.receiver_id == user_id,
            Notification.is_read == False
        ).count()
    
    def get_notifications(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False
    ) -> List[Notification]:
        """사용자 알림 목록 조회"""
        
        query = self.db.query(Notification).filter(
            Notification.receiver_id == user_id
        )
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        return query.order_by(
            Notification.created_at.desc()
        ).offset(offset).limit(limit).all()
    
    async def _send_push_notification(self, notification: Notification):
        """실제 푸시 알림 전송 (Firebase 등)"""
        # 실제 구현 시 Firebase Cloud Messaging 등을 사용
        pass
