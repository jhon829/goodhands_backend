"""
AI 분석 트리거 서비스 (백엔드 전용, n8n 제외)
"""
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import CareSession, ChecklistResponse, CareNote, AIReport, Senior
from app.models.enhanced_care import WeeklyChecklistScore, SpecialNote
from app.config import settings

class AIAnalysisTrigger:
    def __init__(self, db: Session):
        self.db = db
    
    async def analyze_care_session(self, care_session_id: int) -> Dict[str, Any]:
        """케어 세션 분석 및 AI 리포트 생성 (백엔드 전용)"""
        
        # 1. 케어 세션 데이터 수집
        care_session = self.db.query(CareSession).filter(
            CareSession.id == care_session_id
        ).first()
        
        if not care_session:
            raise ValueError("케어 세션을 찾을 수 없습니다")
        
        # 2. 체크리스트 응답 수집
        checklist_responses = self.db.query(ChecklistResponse).filter(
            ChecklistResponse.care_session_id == care_session_id
        ).all()
        
        # 3. 돌봄노트 수집
        care_notes = self.db.query(CareNote).filter(
            CareNote.care_session_id == care_session_id
        ).all()
        
        # 4. 시니어 정보 조회
        senior = self.db.query(Senior).filter(
            Senior.id == care_session.senior_id
        ).first()
        
        # 5. 이전 4주 데이터 조회
        previous_data = self._get_previous_4weeks_data(care_session.senior_id)
        
        # 6. 점수 계산
        total_score, score_percentage, score_breakdown = self._calculate_scores(checklist_responses)
        
        # 7. 기본 AI 분석 (n8n 없이 내부 로직으로)
        ai_result = self._generate_basic_analysis(
            senior, checklist_responses, care_notes, previous_data, 
            total_score, score_percentage
        )
        
        # 8. AI 리포트 생성 또는 업데이트
        ai_report = self._create_or_update_report(
            care_session_id, ai_result, total_score, score_percentage, score_breakdown
        )
        
        # 9. 주간 점수 업데이트
        await self._update_weekly_score(
            care_session_id, total_score, score_breakdown
        )
        
        return {
            "success": True,
            "message": "AI 분석이 완료되었습니다",
            "report_id": ai_report.id,
            "ai_result": ai_result
        }
    
    def _get_previous_4weeks_data(self, senior_id: int) -> List[Dict[str, Any]]:
        """최근 4주 데이터 조회"""
        four_weeks_ago = datetime.now() - timedelta(weeks=4)
        
        weekly_scores = self.db.query(WeeklyChecklistScore).filter(
            WeeklyChecklistScore.senior_id == senior_id,
            WeeklyChecklistScore.week_start_date >= four_weeks_ago.date()
        ).order_by(WeeklyChecklistScore.week_start_date).all()
        
        return [
            {
                "week_start": score.week_start_date.isoformat(),
                "score_percentage": float(score.score_percentage),
                "trend_indicator": score.trend_indicator,
                "total_score": score.total_score,
                "checklist_count": score.checklist_count,
                "score_breakdown": score.score_breakdown
            } for score in weekly_scores
        ]
    
    def _calculate_scores(self, checklist_responses: List[ChecklistResponse]) -> tuple:
        """체크리스트 응답을 점수로 계산"""
        if not checklist_responses:
            return 0, 0.0, {}
        
        total_score = 0
        max_possible_score = 0
        score_breakdown = {}
        
        for response in checklist_responses:
            # 점수 계산
            score_value = self._calculate_score_value(response.answer, response.question_key)
            category = self._get_question_category(response.question_key)
            
            # 기존 레코드에 점수 정보 업데이트
            response.score_value = score_value
            response.category = category
            
            total_score += score_value
            max_possible_score += 5  # 가정: 5점 만점
            
            # 카테고리별 점수 집계
            if category not in score_breakdown:
                score_breakdown[category] = 0
            score_breakdown[category] += score_value
        
        self.db.commit()
        
        score_percentage = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0
        
        return total_score, score_percentage, score_breakdown
    
    def _calculate_score_value(self, answer: Any, question_key: str) -> int:
        """답변을 점수로 변환"""
        if isinstance(answer, bool):
            return 5 if answer else 1
        elif isinstance(answer, int):
            return max(1, min(5, answer))
        elif isinstance(answer, str):
            # 텍스트 답변의 경우 길이와 긍정성으로 점수 매김
            if len(answer) > 10:
                return 4
            elif len(answer) > 0:
                return 3
            else:
                return 1
        else:
            return 3  # 기본값
    
    def _get_question_category(self, question_key: str) -> str:
        """질문 키를 카테고리로 분류"""
        category_mapping = {
            "health": ["health", "medicine", "pain", "sleep"],
            "mental": ["mood", "emotion", "anxiety", "depression"],
            "physical": ["mobility", "exercise", "walk", "strength"],
            "social": ["family", "friend", "social", "communication"],
            "daily": ["meal", "hygiene", "daily", "routine"]
        }
        
        question_lower = question_key.lower()
        for category, keywords in category_mapping.items():
            if any(keyword in question_lower for keyword in keywords):
                return category
        
        return "general"
    
    def _generate_basic_analysis(
        self, 
        senior, 
        checklist_responses: List[ChecklistResponse], 
        care_notes: List[CareNote], 
        previous_data: List[Dict], 
        total_score: int, 
        score_percentage: float
    ) -> Dict[str, Any]:
        """기본 AI 분석 생성 (n8n 없이 내부 로직)"""
        
        # 키워드 생성
        keywords = self._generate_keywords(checklist_responses, care_notes)
        
        # 상태 변화 분석
        trend_analysis = self._analyze_trend_simple(previous_data, score_percentage)
        
        # AI 코멘트 생성 (템플릿 기반)
        ai_comment = self._generate_ai_comment_template(
            senior, checklist_responses, care_notes, trend_analysis
        )
        
        # 특이사항 확인
        special_notes = self._check_special_conditions(checklist_responses, care_notes)
        
        return {
            "ai_comment": ai_comment,
            "keywords": keywords,
            "trend_analysis": trend_analysis,
            "special_notes": special_notes,
            "total_score": total_score,
            "score_percentage": score_percentage
        }
    
    def _generate_keywords(self, checklist_responses: List, care_notes: List) -> List[str]:
        """키워드 생성"""
        keywords = []
        
        # 체크리스트 기반 키워드
        positive_responses = 0
        total_responses = len(checklist_responses)
        
        for response in checklist_responses:
            if isinstance(response.answer, bool) and response.answer:
                positive_responses += 1
            elif isinstance(response.answer, int) and response.answer >= 4:
                positive_responses += 1
        
        # 전반적 상태 키워드
        if total_responses > 0:
            positive_ratio = positive_responses / total_responses
            if positive_ratio >= 0.8:
                keywords.extend(["건강함", "기분좋음"])
            elif positive_ratio >= 0.6:
                keywords.extend(["보통", "안정적"])
            else:
                keywords.extend(["주의필요", "관찰필요"])
        
        # 돌봄노트 기반 키워드
        for note in care_notes:
            content_lower = note.content.lower()
            if "가족" in content_lower or "자녀" in content_lower:
                keywords.append("가족그리움")
            if "아프" in content_lower or "힘들" in content_lower:
                keywords.append("컨디션저하")
            if "좋" in content_lower or "기분" in content_lower:
                keywords.append("긍정적")
        
        return list(set(keywords))  # 중복 제거
    
    def _analyze_trend_simple(self, previous_data: List[Dict], current_score: float) -> Dict[str, Any]:
        """간단한 추이 분석"""
        if not previous_data:
            return {"trend": "stable", "change": 0, "message": "이전 데이터 없음"}
        
        # 최근 점수와 비교
        last_week_score = previous_data[-1]["score_percentage"] if previous_data else current_score
        change = current_score - last_week_score
        
        if change > 10:
            trend = "improving"
            message = f"지난 주 대비 {change:.1f}% 개선되었습니다"
        elif change < -10:
            trend = "declining"
            message = f"지난 주 대비 {abs(change):.1f}% 저하되었습니다"
        else:
            trend = "stable"
            message = "안정적인 상태를 유지하고 있습니다"
        
        return {
            "trend": trend,
            "change": change,
            "message": message
        }
    
    def _generate_ai_comment_template(self, senior, checklist_responses, care_notes, trend_analysis) -> str:
        """템플릿 기반 AI 코멘트 생성"""
        
        # 기본 인사
        comment_parts = []
        comment_parts.append(f"{senior.name}님의 오늘 케어가 완료되었습니다.")
        
        # 상태 평가
        avg_score = sum(r.score_value for r in checklist_responses) / len(checklist_responses) if checklist_responses else 3
        if avg_score >= 4:
            comment_parts.append("전반적으로 건강하고 안정적인 상태를 보이고 계십니다.")
        elif avg_score >= 3:
            comment_parts.append("보통 수준의 컨디션을 유지하고 계십니다.")
        else:
            comment_parts.append("오늘은 평소보다 컨디션이 좋지 않으신 것 같습니다.")
        
        # 추이 분석 결과
        comment_parts.append(trend_analysis["message"])
        
        # 가족 소통 제안
        family_mentioned = any("가족" in note.content for note in care_notes)
        if family_mentioned:
            comment_parts.append("어르신이 가족 이야기를 많이 하셨으니, 안부 전화를 드려보시면 좋을 것 같습니다.")
        else:
            comment_parts.append("오늘 저녁에 간단한 안부 인사라도 해주시면 어르신이 많이 기뻐하실 것 같습니다.")
        
        return " ".join(comment_parts)
    
    def _check_special_conditions(self, checklist_responses, care_notes) -> str:
        """특이사항 확인"""
        special_notes = []
        
        # 체크리스트에서 특이사항 확인
        for response in checklist_responses:
            if response.notes and len(response.notes.strip()) > 0:
                special_notes.append(response.notes.strip())
        
        # 돌봄노트에서 특이사항 확인
        for note in care_notes:
            content = note.content.strip()
            if any(keyword in content.lower() for keyword in ["아프", "힘들", "이상", "문제"]):
                special_notes.append(content[:50] + "..." if len(content) > 50 else content)
        
        return "; ".join(special_notes) if special_notes else ""
    
    def _create_or_update_report(
        self, 
        care_session_id: int, 
        ai_result: Dict, 
        total_score: int, 
        score_percentage: float, 
        score_breakdown: Dict
    ) -> AIReport:
        """AI 리포트 생성 또는 업데이트"""
        
        # 기존 리포트 확인
        existing_report = self.db.query(AIReport).filter(
            AIReport.care_session_id == care_session_id
        ).first()
        
        if existing_report:
            # 기존 리포트 업데이트
            existing_report.ai_comment = ai_result["ai_comment"]
            existing_report.keywords = ai_result["keywords"]
            existing_report.content = f"케어 세션 분석 결과: {ai_result['ai_comment']}"
            existing_report.checklist_score_total = total_score
            existing_report.checklist_score_percentage = score_percentage
            existing_report.trend_comparison = ai_result["trend_analysis"]
            existing_report.special_notes_summary = ai_result["special_notes"]
            existing_report.ai_processing_status = "completed"
            existing_report.status = "generated"
            
            ai_report = existing_report
        else:
            # 새 리포트 생성
            ai_report = AIReport(
                care_session_id=care_session_id,
                ai_comment=ai_result["ai_comment"],
                keywords=ai_result["keywords"],
                content=f"케어 세션 분석 결과: {ai_result['ai_comment']}",
                checklist_score_total=total_score,
                checklist_score_percentage=score_percentage,
                trend_comparison=ai_result["trend_analysis"],
                special_notes_summary=ai_result["special_notes"],
                ai_processing_status="completed",
                status="generated"
            )
            self.db.add(ai_report)
        
        # 특이사항이 있다면 별도 저장
        if ai_result["special_notes"]:
            care_session = self.db.query(CareSession).filter(
                CareSession.id == care_session_id
            ).first()
            
            special_note = SpecialNote(
                senior_id=care_session.senior_id,
                care_session_id=care_session_id,
                note_type="ai_analysis",
                short_summary=ai_result["special_notes"][:200],
                detailed_content=ai_result["ai_comment"],
                priority_level=2  # 보통 우선순위
            )
            self.db.add(special_note)
        
        self.db.commit()
        self.db.refresh(ai_report)
        
        return ai_report
    
    async def _update_weekly_score(
        self, 
        care_session_id: int, 
        total_score: int, 
        score_breakdown: Dict[str, Any]
    ):
        """주간 체크리스트 점수 업데이트"""
        
        care_session = self.db.query(CareSession).filter(
            CareSession.id == care_session_id
        ).first()
        
        if not care_session:
            return
        
        # 이번 주의 시작일과 종료일 계산
        session_date = care_session.start_time.date()
        week_start = session_date - timedelta(days=session_date.weekday())  # 월요일
        week_end = week_start + timedelta(days=6)  # 일요일
        
        # 기존 주간 점수 레코드 조회 또는 생성
        weekly_score = self.db.query(WeeklyChecklistScore).filter(
            WeeklyChecklistScore.senior_id == care_session.senior_id,
            WeeklyChecklistScore.week_start_date == week_start
        ).first()
        
        if weekly_score:
            # 기존 레코드 업데이트
            weekly_score.total_score += total_score
            weekly_score.checklist_count += 1
            weekly_score.max_possible_score += len(score_breakdown) * 5  # 가정: 5점 만점
            weekly_score.score_percentage = (weekly_score.total_score / weekly_score.max_possible_score) * 100
            
            # 점수 세부사항 업데이트
            if weekly_score.score_breakdown:
                for category, score in score_breakdown.items():
                    if category in weekly_score.score_breakdown:
                        weekly_score.score_breakdown[category] += score
                    else:
                        weekly_score.score_breakdown[category] = score
            else:
                weekly_score.score_breakdown = score_breakdown
                
        else:
            # 새 레코드 생성
            max_possible = len(score_breakdown) * 5  # 가정: 5점 만점
            weekly_score = WeeklyChecklistScore(
                senior_id=care_session.senior_id,
                caregiver_id=care_session.caregiver_id,
                week_start_date=week_start,
                week_end_date=week_end,
                total_score=total_score,
                max_possible_score=max_possible,
                score_percentage=(total_score / max_possible) * 100 if max_possible > 0 else 0,
                checklist_count=1,
                score_breakdown=score_breakdown,
                trend_indicator="stable"  # 기본값, 나중에 계산
            )
            self.db.add(weekly_score)
        
        self.db.commit()
