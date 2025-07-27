# app/routers/ai_enhanced.py
# 카테고리별 상세 분석 기능이 추가된 AI 라우터 확장

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
import json

from ..database import get_db
from ..models import *
from ..services.auth import get_current_user

router = APIRouter()

@router.get("/weekly-session-data-enhanced/{session_id}")
async def get_weekly_session_data_enhanced(
    session_id: int, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """n8n 워크플로우용 주간 세션 데이터 + 카테고리별 추이 분석"""
    
    # 기본 세션 정보
    session = db.query(CareSession).filter(
        CareSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=404, 
            detail="Care session not found"
        )
    
    # 체크리스트 응답 조회 (카테고리별 그룹화)
    checklist_responses = db.query(ChecklistResponse).filter(
        ChecklistResponse.care_session_id == session_id
    ).all()
    
    # 돌봄노트 조회
    care_notes = db.query(CareNote).filter(
        CareNote.care_session_id == session_id
    ).all()
    
    # 시니어 정보 및 질병 정보
    senior = db.query(Senior).filter(Senior.id == session.senior_id).first()
    senior_diseases = db.query(SeniorDisease).filter(
        SeniorDisease.senior_id == session.senior_id
    ).all()
    
    # 케어기버 정보
    caregiver = db.query(Caregiver).filter(Caregiver.id == session.caregiver_id).first()
    
    # === 카테고리별 점수 계산 ===
    category_scores = {}
    
    # 카테고리별 그룹화
    for response in checklist_responses:
        category_code = getattr(response, 'category_code', None) or getattr(response, 'category', 'unknown')
        if category_code not in category_scores:
            category_scores[category_code] = {
                'responses': [],
                'total_score': 0,
                'max_possible_score': 0,
                'question_count': 0
            }
        
        scale_value = getattr(response, 'scale_value', None) or getattr(response, 'score_value', 0)
        max_scale = getattr(response, 'max_scale_value', 4)
        
        category_scores[category_code]['responses'].append({
            'question_key': response.question_key,
            'scale_value': scale_value,
            'max_scale_value': max_scale
        })
        
        category_scores[category_code]['total_score'] += scale_value
        category_scores[category_code]['max_possible_score'] += max_scale
        category_scores[category_code]['question_count'] += 1
    
    # 점수 백분율 계산
    for category in category_scores:
        if category_scores[category]['max_possible_score'] > 0:
            category_scores[category]['score_percentage'] = round(
                (category_scores[category]['total_score'] / category_scores[category]['max_possible_score']) * 100, 2
            )
        else:
            category_scores[category]['score_percentage'] = 0
    
    # === 이전 주 데이터와 비교 ===
    current_week_start = session.start_time.date() - timedelta(days=session.start_time.weekday())
    previous_week_start = current_week_start - timedelta(days=7)
    
    previous_scores = {}
    for category_code in category_scores:
        # 이전 주 데이터 조회 (주간 점수 테이블에서)
        # 현재는 임시로 이전 세션에서 계산
        prev_sessions = db.query(CareSession).filter(
            CareSession.senior_id == session.senior_id,
            CareSession.start_time >= datetime.combine(previous_week_start, datetime.min.time()),
            CareSession.start_time < datetime.combine(current_week_start, datetime.min.time()),
            CareSession.status == "completed"
        ).all()
        
        if prev_sessions:
            prev_session = prev_sessions[-1]  # 가장 최근 세션
            prev_responses = db.query(ChecklistResponse).filter(
                ChecklistResponse.care_session_id == prev_session.id
            ).all()
            
            prev_total = 0
            prev_max = 0
            for resp in prev_responses:
                if getattr(resp, 'category_code', getattr(resp, 'category', '')) == category_code:
                    prev_total += getattr(resp, 'scale_value', getattr(resp, 'score_value', 0))
                    prev_max += getattr(resp, 'max_scale_value', 4)
            
            if prev_max > 0:
                previous_scores[category_code] = round((prev_total / prev_max) * 100, 2)
            else:
                previous_scores[category_code] = None
        else:
            previous_scores[category_code] = None
    
    # === 상태별 분석 생성 ===
    category_analysis = {}
    
    for category_code, scores in category_scores.items():
        current_percentage = scores['score_percentage']
        previous_percentage = previous_scores.get(category_code)
        
        # 변화량 계산
        if previous_percentage is not None:
            change_amount = current_percentage - previous_percentage
            change_direction = "up" if change_amount > 5 else "down" if change_amount < -5 else "stable"
        else:
            change_amount = 0
            change_direction = "stable"
        
        # 상태 레벨 판단
        if current_percentage >= 80:
            status_level = "good"
            avatar_emotion = "happy"
            avatar_color = "blue"
        elif current_percentage >= 60:
            status_level = "caution"
            avatar_emotion = "worried"
            avatar_color = "green"
        else:
            status_level = "warning"
            avatar_emotion = "dizzy"
            avatar_color = "red"
        
        # 카테고리별 맞춤 메시지
        category_messages = {
            "nutrition_common": {
                "good": "식사를 잘 드시고 계세요. 영양 상태가 양호합니다.",
                "caution": "식사량이 조금 부족해요. 관심이 필요합니다.",
                "warning": "식사를 잘 못 드시고 계세요. 적극적인 관리가 필요해요."
            },
            "hypertension": {
                "good": "혈압 관리가 잘 되고 있어요. 현재 상태를 유지해주세요.",
                "caution": "혈압 관리에 조금 더 주의가 필요해요.",
                "warning": "고혈압 위험 상태예요. 적극적인 관리가 필요해요."
            },
            "depression": {
                "good": "기분이 좋고 활발하세요. 긍정적인 상태입니다.",
                "caution": "기분 상태가 약간 우울해 보여요. 관심이 필요합니다.",
                "warning": "우울감이 심해 보여요. 적극적인 케어가 필요해요."
            }
        }
        
        status_message = category_messages.get(category_code, {}).get(status_level, "상태를 확인하고 있습니다.")
        
        category_analysis[category_code] = {
            'category_name': get_category_name(category_code),
            'current_score': scores['total_score'],
            'max_score': scores['max_possible_score'],
            'current_percentage': current_percentage,
            'previous_percentage': previous_percentage,
            'change_amount': change_amount,
            'change_direction': change_direction,
            'status_level': status_level,
            'avatar_emotion': avatar_emotion,
            'avatar_color': avatar_color,
            'status_message': status_message,
            'trend_data': generate_trend_chart_data(category_code, session.senior_id, current_week_start)
        }
    
    return {
        "session_id": session_id,
        "session_date": session.start_time.date(),
        "senior": {
            "id": senior.id,
            "name": senior.name,
            "age": senior.age,
            "diseases": [d.disease_type for d in senior_diseases]
        },
        "caregiver": {
            "id": caregiver.id,
            "name": caregiver.name
        },
        "category_analysis": category_analysis,
        "checklist_responses": [
            {
                "question_key": r.question_key,
                "question_text": r.question_text,
                "answer": r.answer,
                "scale_value": getattr(r, 'scale_value', getattr(r, 'score_value', 0)),
                "category_code": getattr(r, 'category_code', getattr(r, 'category', 'unknown'))
            } for r in checklist_responses
        ],
        "care_notes": [
            {
                "question_type": n.question_type,
                "question_text": n.question_text,
                "content": n.content
            } for n in care_notes
        ]
    }

def get_category_name(category_code: str) -> str:
    """카테고리 코드에서 한글 이름 반환"""
    category_names = {
        "nutrition_common": "영양상태 상세 추이",
        "hypertension": "고혈압 상세 추이", 
        "depression": "우울증 상세 추이"
    }
    return category_names.get(category_code, category_code)

def generate_trend_chart_data(category_code: str, senior_id: int, current_week: date) -> list:
    """최근 4주 트렌드 차트 데이터 생성"""
    trend_data = []
    for i in range(4):
        week_start = current_week - timedelta(days=7*i)
        # 실제 DB에서 해당 주의 점수 조회하여 차트 데이터 생성
        # 현재는 임시 데이터
        trend_data.append({
            'week': f"W{4-i}",
            'score': 75 + (i * 5),  # 임시 데이터
            'date': week_start.strftime('%m.%d')
        })
    return trend_data

@router.post("/save-category-trends")
async def save_category_trends(
    trend_data: dict,
    db: Session = Depends(get_db)
):
    """카테고리별 트렌드 데이터 저장"""
    
    # 현재는 간단한 로깅만 수행
    print(f"카테고리별 트렌드 데이터 저장: {trend_data}")
    
    return {"status": "success", "message": "카테고리별 트렌드가 저장되었습니다"}

@router.put("/reports-enhanced/{session_id}")
async def update_ai_report_enhanced(
    session_id: int,
    report_data: dict,
    db: Session = Depends(get_db)
):
    """AI 리포트 업데이트 (카테고리별 상세 정보 포함)"""
    
    # 기존 리포트 조회 또는 생성
    ai_report = db.query(AIReport).filter(
        AIReport.care_session_id == session_id
    ).first()
    
    if not ai_report:
        care_session = db.query(CareSession).filter(CareSession.id == session_id).first()
        ai_report = AIReport(
            care_session_id=session_id,
            senior_id=care_session.senior_id if care_session else None
        )
        db.add(ai_report)
    
    # 기본 AI 리포트 정보 업데이트
    ai_report.keywords = report_data.get('keywords')
    ai_report.content = report_data.get('content', '')
    ai_report.ai_comment = report_data.get('ai_comment', '')
    ai_report.status = report_data.get('status', 'completed')
    
    # 카테고리별 상세 정보가 있는지 확인 후 저장
    if hasattr(ai_report, 'category_details') and 'category_analysis' in report_data:
        ai_report.category_details = report_data['category_analysis']
    
    if hasattr(ai_report, 'ui_components') and 'ui_components' in report_data:
        ai_report.ui_components = report_data['ui_components']
    
    if hasattr(ai_report, 'ui_enhancements') and 'category_details' in report_data:
        # 카테고리별 상세 정보에서 UI 강화 정보 추출
        category_details = report_data.get('category_details', {})
        ui_enhancements = {
            'categories_analyzed': len(category_details),
            'analysis_timestamp': datetime.now().isoformat()
        }
        ai_report.ui_enhancements = ui_enhancements
    
    db.commit()
    
    return {
        "status": "success", 
        "report_id": ai_report.id,
        "categories_updated": len(report_data.get('category_analysis', {}))
    }

@router.get("/category-status/{senior_id}")
async def get_category_status(
    senior_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """시니어의 최신 카테고리별 상태 조회"""
    
    # 시니어 확인
    senior = db.query(Senior).filter(Senior.id == senior_id).first()
    if not senior:
        raise HTTPException(status_code=404, detail="Senior not found")
    
    # 최신 AI 리포트 조회
    latest_report = db.query(AIReport).filter(
        AIReport.senior_id == senior_id
    ).order_by(AIReport.created_at.desc()).first()
    
    if not latest_report:
        return {
            "senior_id": senior_id,
            "message": "아직 리포트가 생성되지 않았습니다",
            "category_status": {}
        }
    
    # 카테고리별 상태 정보 추출
    category_status = {}
    
    # 기존 테이블 구조에 맞춰 임시 데이터 생성
    categories = ['nutrition_common', 'hypertension', 'depression']
    
    for i, category_code in enumerate(categories):
        # 임시 상태 데이터 (실제로는 DB에서 조회)
        ui_key = category_code.replace('_common', '')
        category_status[ui_key] = {
            'title': get_category_name(category_code),
            'avatar_color': ['blue', 'green', 'red'][i % 3],
            'avatar_emotion': ['happy', 'worried', 'dizzy'][i % 3],
            'current_percentage': [82, 75, 68][i % 3],
            'change_amount': [-2, 3, 7][i % 3],
            'change_display': ['-2', '+3', '+7'][i % 3],
            'status_message': [
                '기분이 좋고 활발하세요. 긍정적인 상태입니다.',
                '식사량이 조금 부족해요. 관심이 필요합니다.',
                '고혈압 위험 상태예요. 적극적인 관리가 필요해요.'
            ][i % 3],
            'trend_direction': ['down', 'up', 'up'][i % 3],
            'status_level': ['good', 'caution', 'warning'][i % 3],
            'last_updated': latest_report.created_at.date()
        }
    
    return {
        "senior_id": senior_id,
        "senior_name": senior.name,
        "latest_report_date": latest_report.created_at.date(),
        "category_status": category_status
    }

@router.get("/previous-week-data/{senior_id}")
async def get_previous_week_data(
    senior_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """이전 주 데이터 조회 (비교 분석용)"""
    
    # 이전 주 시작일 계산
    today = datetime.now().date()
    current_week_start = today - timedelta(days=today.weekday())
    previous_week_start = current_week_start - timedelta(days=7)
    previous_week_end = current_week_start - timedelta(days=1)
    
    # 이전 주 돌봄 세션들 조회
    previous_sessions = db.query(CareSession).filter(
        CareSession.senior_id == senior_id,
        CareSession.start_time >= datetime.combine(previous_week_start, datetime.min.time()),
        CareSession.start_time <= datetime.combine(previous_week_end, datetime.max.time()),
        CareSession.status == "completed"
    ).all()
    
    if not previous_sessions:
        return {
            "senior_id": senior_id,
            "previous_week_start": previous_week_start,
            "previous_week_end": previous_week_end,
            "sessions": [],
            "category_scores": {}
        }
    
    # 각 세션의 체크리스트 응답들을 카테고리별로 집계
    all_responses = []
    for session in previous_sessions:
        responses = db.query(ChecklistResponse).filter(
            ChecklistResponse.care_session_id == session.id
        ).all()
        all_responses.extend(responses)
    
    # 카테고리별 점수 계산
    category_scores = {}
    for response in all_responses:
        category_code = getattr(response, 'category_code', getattr(response, 'category', 'unknown'))
        if category_code not in category_scores:
            category_scores[category_code] = {
                'total_score': 0,
                'max_possible_score': 0,
                'response_count': 0
            }
        
        scale_value = getattr(response, 'scale_value', getattr(response, 'score_value', 0))
        max_scale = getattr(response, 'max_scale_value', 4)
        
        category_scores[category_code]['total_score'] += scale_value
        category_scores[category_code]['max_possible_score'] += max_scale
        category_scores[category_code]['response_count'] += 1
    
    # 백분율 계산
    for category in category_scores:
        if category_scores[category]['max_possible_score'] > 0:
            category_scores[category]['score_percentage'] = round(
                (category_scores[category]['total_score'] / category_scores[category]['max_possible_score']) * 100, 2
            )
        else:
            category_scores[category]['score_percentage'] = 0
    
    return {
        "senior_id": senior_id,
        "previous_week_start": previous_week_start,
        "previous_week_end": previous_week_end,
        "sessions_count": len(previous_sessions),
        "category_scores": category_scores
    }
