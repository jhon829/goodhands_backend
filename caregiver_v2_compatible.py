"""
현재 배포된 DB v1.4.0 구조를 활용한 케어기버 라우터 수정
"""

# 기존 체크리스트 제출 함수를 수정합니다
@router.post("/checklist")
async def submit_checklist_v2(
    checklist_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """기존 DB 구조를 활용한 3가지 유형별 체크리스트 제출"""
    try:
        session_id = checklist_data.get("session_id")
        responses = checklist_data.get("responses", {})
        
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
        
        # 기존 checklist_responses 테이블 구조 활용
        from sqlalchemy import text
        
        total_responses = 0
        for category_code in ["nutrition_common", "hypertension", "depression"]:
            if category_code in responses:
                category_responses = responses[category_code]
                
                # 카테고리 ID 조회
                category_query = text("""
                    SELECT id FROM checklist_categories WHERE category_code = :category_code
                """)
                category_result = db.execute(category_query, {"category_code": category_code}).fetchone()
                
                if not category_result:
                    continue
                    
                category_id = category_result.id
                
                # 해당 카테고리의 질문들 조회
                questions_query = text("""
                    SELECT id, question_code, question_text, display_order 
                    FROM checklist_questions 
                    WHERE category_id = :category_id AND is_active = 1
                    ORDER BY display_order
                """)
                questions_result = db.execute(questions_query, {"category_id": category_id}).fetchall()
                
                # 각 질문에 대한 응답 저장
                for i, question in enumerate(questions_result):
                    sub_q_id = ["A", "B", "C", "D"][i] if i < 4 else "A"
                    
                    if sub_q_id in category_responses:
                        response_data = category_responses[sub_q_id]
                        
                        # 기존 테이블 구조에 맞춰 저장
                        checklist_response = ChecklistResponse(
                            care_session_id=session_id,
                            question_key=response_data.get("question_key", question.question_code),
                            question_text=response_data.get("question_text", question.question_text),
                            answer=response_data.get("answer"),
                            notes=response_data.get("notes", ""),
                            score_value=response_data.get("selected_score", 3),
                            category=category_code,
                            # 새 컬럼들 활용
                            category_id=category_id,
                            question_id=question.id,
                            scale_value=response_data.get("selected_score", 3),
                            max_scale_value=4,
                            category_code=category_code,
                            ui_category_mapping=category_code.replace("_common", "")
                        )
                        db.add(checklist_response)
                        total_responses += 1
        
        db.commit()
        
        return {
            "message": "3가지 유형별 체크리스트가 성공적으로 저장되었습니다.",
            "session_id": session_id,
            "responses_count": total_responses,
            "types_completed": len([t for t in ["nutrition_common", "hypertension", "depression"] if t in responses])
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"체크리스트 제출 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/care-note")
async def submit_care_note_v2(
    care_note_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """기존 DB 구조를 활용한 1개 랜덤 돌봄노트 제출"""
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
        
        # 선택된 질문 정보 조회
        from sqlalchemy import text
        question_query = text("""
            SELECT question_title, question_text 
            FROM care_note_questions 
            WHERE id = :question_id
        """)
        question_result = db.execute(question_query, {"question_id": question_id}).fetchone()
        
        # 기존 care_notes 테이블에 저장 (새 컬럼 활용)
        care_note = CareNote(
            care_session_id=session_id,
            selected_question_id=question_id,
            question_number=question_number,
            question_type=f"question_{question_number}",
            question_text=question_result.question_text if question_result else "",
            content=content
        )
        
        db.add(care_note)
        db.commit()
        
        # 체크리스트와 돌봄노트 모두 완료되면 주간 점수 계산
        await calculate_and_save_weekly_scores_v2(session_id, care_session.senior_id, db)
        
        # n8n 워크플로우 트리거
        await trigger_ai_analysis_workflows_v2(session_id, care_session.senior_id)
        
        # 세션 상태 완료로 업데이트
        care_session.status = "completed"
        care_session.end_time = datetime.now()
        db.commit()
        
        return {
            "message": "돌봄노트가 성공적으로 저장되었습니다.",
            "session_id": session_id,
            "question_id": question_id,
            "ai_analysis_triggered": True,
            "db_version": "1.4.0"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"돌봄노트 제출 중 오류가 발생했습니다: {str(e)}"
        )

async def calculate_and_save_weekly_scores_v2(session_id: int, senior_id: int, db: Session):
    """기존 weekly_category_scores 테이블을 활용한 주간 점수 계산"""
    
    from sqlalchemy import text
    
    week_start = date.today()
    week_end = week_start + timedelta(days=6)
    
    # 3가지 카테고리별 점수 계산
    categories_query = text("""
        SELECT id, category_code, category_name, max_score 
        FROM checklist_categories 
        WHERE category_code IN ('nutrition_common', 'hypertension', 'depression')
    """)
    
    categories = db.execute(categories_query).fetchall()
    
    for category in categories:
        # 해당 카테고리의 체크리스트 응답 조회
        responses_query = text("""
            SELECT cr.scale_value
            FROM checklist_responses cr
            WHERE cr.care_session_id = :session_id 
            AND cr.category_id = :category_id
            AND cr.scale_value IS NOT NULL
        """)
        
        responses_result = db.execute(responses_query, {
            "session_id": session_id,
            "category_id": category.id
        }).fetchall()
        
        if not responses_result:
            continue
            
        # 점수 합계 계산
        total_score = sum([r.scale_value for r in responses_result])
        max_score = category.max_score
        score_percentage = (total_score / max_score) * 100 if max_score > 0 else 0
        
        # 지난 주 점수와 비교하여 트렌드 결정
        last_week_query = text("""
            SELECT total_score 
            FROM weekly_category_scores
            WHERE senior_id = :senior_id AND category_id = :category_id
            ORDER BY week_start_date DESC
            LIMIT 1
        """)
        
        last_week_result = db.execute(last_week_query, {
            "senior_id": senior_id,
            "category_id": category.id
        }).fetchone()
        
        trend_direction = "stable"
        score_change = 0
        
        if last_week_result:
            score_change = score_percentage - float(last_week_result.total_score)
            if score_change > 5:
                trend_direction = "improving"
            elif score_change < -5:
                trend_direction = "declining"
        
        # 케어기버 ID 조회
        caregiver_query = text("""
            SELECT caregiver_id FROM care_sessions WHERE id = :session_id
        """)
        caregiver_result = db.execute(caregiver_query, {"session_id": session_id}).fetchone()
        caregiver_id = caregiver_result.caregiver_id if caregiver_result else 1
        
        # 기존 테이블에 저장
        insert_query = text("""
            INSERT INTO weekly_category_scores 
            (senior_id, caregiver_id, category_id, week_start_date, week_end_date,
             total_score, max_possible_score, score_percentage, question_count, 
             completed_questions, previous_week_score, score_change, trend_direction, risk_level)
            VALUES 
            (:senior_id, :caregiver_id, :category_id, :week_start, :week_end,
             :total_score, :max_score, :score_percentage, :question_count,
             :completed_questions, :previous_week_score, :score_change, :trend_direction, :risk_level)
        """)
        
        db.execute(insert_query, {
            "senior_id": senior_id,
            "caregiver_id": caregiver_id,
            "category_id": category.id,
            "week_start": week_start,
            "week_end": week_end,
            "total_score": total_score,
            "max_score": max_score,
            "score_percentage": score_percentage,
            "question_count": len(responses_result),
            "completed_questions": len(responses_result),
            "previous_week_score": float(last_week_result.total_score) if last_week_result else None,
            "score_change": score_change,
            "trend_direction": trend_direction,
            "risk_level": "normal" if score_percentage >= 70 else ("caution" if score_percentage >= 50 else "warning")
        })
    
    db.commit()

async def trigger_ai_analysis_workflows_v2(session_id: int, senior_id: int):
    """n8n AI 분석 워크플로우 v2.0 트리거"""
    import requests
    
    webhook_base_url = "http://pay.gzonesoft.co.kr:10006/webhook"
    
    trigger_data = {
        "session_id": session_id,
        "senior_id": senior_id,
        "trigger_time": datetime.now().isoformat(),
        "db_version": "1.4.0"
    }
    
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
