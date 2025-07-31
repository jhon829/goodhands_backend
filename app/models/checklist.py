from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class ChecklistCategory(Base):
    __tablename__ = "checklist_categories"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    category_code = Column(String(50), unique=True, nullable=False)
    category_name = Column(String(100), nullable=False)
    description = Column(Text)
    icon_name = Column(String(50))
    display_order = Column(Integer)
    is_common = Column(Boolean, default=True)
    max_score = Column(Integer, default=16)
    created_at = Column(DateTime, server_default=func.now())

class ChecklistQuestion(Base):
    __tablename__ = "checklist_questions"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("checklist_categories.id"), nullable=False)
    question_code = Column(String(50), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), default='scale4')
    is_required = Column(Boolean, default=True)
    display_order = Column(Integer)
    target_diseases = Column(Text)  # JSON string
    scale_labels = Column(Text)  # JSON string
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # 관계 설정
    category = relationship("ChecklistCategory")

class ChecklistType(Base):
    __tablename__ = "checklist_types"
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    
    id = Column(Integer, primary_key=True, index=True)
    type_code = Column(String(20), unique=True, nullable=False)
    type_name = Column(String(50), nullable=False)
    description = Column(Text)
    max_score = Column(Integer, default=16)
    created_at = Column(DateTime, server_default=func.now())
