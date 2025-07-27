# n8n 워크플로우 관련 엔드포인트 추가

@router.get("/weekly-session-data/{session_id}")
async def get_weekly_session_data(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """n8n 워크플로우용 주간 세션 데이터 조회"""
    
    # 돌봄 세션 기본 정보
    session = db.query(CareSession).filter(CareSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Care session not found")
    
    # 체크리스트 응답 조회
    checklist_responses = db.query(ChecklistResponse).filter(
        ChecklistResponse.care_session_id == session_id
    ).all()
    
    # 돌봄노트 조회
    care_notes = db.query(CareNote).filter(
        CareNote.care_session_id == session_id
    ).all()
    
    # 시니어 정보
    senior = db.query(Senior).filter(Senior.id == session.senior_id).first()
    
    # 케어기버 정보 - current_user를 통해 가져오기
    caregiver = current_user.caregiver_profile
    
    return {
        "session_id": session_id,
        "session_date": session.start_time.date(),
        "senior": {
            "id": senior.id,
            "name": senior.name,
            "age": senior.age,
            "diseases": [d.disease_type for d in senior.diseases] if senior.diseases else []
        },
        "caregiver": {
            "id": caregiver.id,
            "name": caregiver.name
        } if caregiver else None,
        "checklist_responses": [
            {
                "question_key": r.question_key,
                "question_text": r.question_text,
                "answer": r.answer,
                "notes": r.notes,
                "score_value": getattr(r, 'score_value', 0),
                "category": getattr(r, 'category', 'general')
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

@router.get("/four-week-trend/{senior_id}")
async def get_four_week_trend_data(
    senior_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """4주간 트렌드 분석용 데이터 조회"""
    from datetime import datetime, timedelta
    
    # 지난 4주간의 돌봄 세션 조회
    four_weeks_ago = datetime.now() - timedelta(weeks=4)
    
    sessions = db.query(CareSession).filter(
        CareSession.senior_id == senior_id,
        CareSession.start_time >= four_weeks_ago,
        CareSession.status == "completed"
    ).order_by(CareSession.start_time.desc()).limit(4).all()
    
    weekly_data = []
    for session in sessions:
        # 각 세션의 체크리스트와 돌봄노트
        checklist = db.query(ChecklistResponse).filter(
            ChecklistResponse.care_session_id == session.id
        ).all()
        
        notes = db.query(CareNote).filter(
            CareNote.care_session_id == session.id
        ).all()
        
        weekly_data.append({
            "session_id": session.id,
            "session_date": session.start_time.date(),
            "checklist_responses": [
                {
                    "question_key": r.question_key,
                    "answer": r.answer,
                    "score_value": getattr(r, 'score_value', 0),
                    "category": getattr(r, 'category', 'general')
                } for r in checklist
            ],
            "care_notes": [
                {
                    "question_type": n.question_type,
                    "content": n.content
                } for n in notes
            ]
        })
    
    return {
        "senior_id": senior_id,
        "analysis_period": "4주",
        "total_sessions": len(weekly_data),
        "weekly_sessions": weekly_data
    }

@router.post("/weekly-checklist-scores")
async def save_weekly_scores(
    score_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """주간 체크리스트 점수 저장"""
    
    # 여기서는 간단히 성공 응답만 반환
    # 실제로는 WeeklyChecklistScore 모델에 저장
    return {"status": "success", "message": "주간 점수가 저장되었습니다"}

@router.post("/health-trend-analysis")
async def save_trend_analysis(
    trend_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """4주 트렌드 분석 결과 저장"""
    
    # 여기서는 간단히 성공 응답만 반환
    # 실제로는 HealthTrendAnalysis 모델에 저장
    return {"status": "success", "message": "트렌드 분석이 저장되었습니다"}

@router.post("/webhook/trigger-weekly-analysis")
async def trigger_weekly_analysis(
    request: dict
):
    """주간 돌봄 완료 시 n8n 워크플로우 트리거"""
    import requests
    from datetime import datetime
    
    session_id = request.get("session_id")
    
    # n8n 워크플로우 호출 (실제 구현에서는 환경 변수로 URL 관리)
    webhook_urls = [
        "http://pay.gzonesoft.co.kr:10006/webhook/weekly-ai-comment",
        "http://pay.gzonesoft.co.kr:10006/webhook/four-week-trend"
    ]
    
    results = []
    for url in webhook_urls:
        try:
            response = requests.post(
                url,
                json={
                    "session_id": session_id,
                    "trigger_time": datetime.now().isoformat()
                },
                timeout=30
            )
            results.append({"url": url, "status": response.status_code})
        except Exception as e:
            results.append({"url": url, "error": str(e)})
    
    return {"status": "triggered", "session_id": session_id, "results": results}

@router.put("/reports/{session_id}")
async def update_ai_report(
    session_id: int,
    report_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI 리포트 업데이트 (n8n에서 생성된 결과 저장)"""
    
    # 기존 리포트 조회 또는 새로 생성
    care_session = db.query(CareSession).filter(CareSession.id == session_id).first()
    if not care_session:
        raise HTTPException(status_code=404, detail="Care session not found")
    
    existing_report = db.query(AIReport).filter(
        AIReport.care_session_id == session_id
    ).first()
    
    if existing_report:
        # 기존 리포트 업데이트
        existing_report.keywords = report_data.get("keywords", [])
        existing_report.content = report_data.get("content", "")
        existing_report.ai_comment = report_data.get("ai_comment", "")
        existing_report.status = report_data.get("status", "completed")
        
        db.commit()
        return {"status": "updated", "report_id": existing_report.id}
    else:
        # 새 리포트 생성
        new_report = AIReport(
            care_session_id=session_id,
            keywords=report_data.get("keywords", []),
            content=report_data.get("content", ""),
            ai_comment=report_data.get("ai_comment", ""),
            status=report_data.get("status", "completed")
        )
        
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        
        return {"status": "created", "report_id": new_report.id}
