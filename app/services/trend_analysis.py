"""
추이 분석 서비스 - 최근 4주 상태 변화 분석
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func
import statistics

from app.models.enhanced_care import WeeklyChecklistScore, HealthTrendAnalysis

class TrendAnalysisService:
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_4week_trend(self, senior_id: int) -> Dict[str, Any]:
        """최근 4주 상태 변화 추이 분석"""
        
        # 최근 4주 데이터 조회
        four_weeks_ago = datetime.now() - timedelta(weeks=4)
        
        weekly_scores = self.db.query(WeeklyChecklistScore).filter(
            WeeklyChecklistScore.senior_id == senior_id,
            WeeklyChecklistScore.week_start_date >= four_weeks_ago.date()
        ).order_by(WeeklyChecklistScore.week_start_date).all()
        
        if len(weekly_scores) < 2:
            return {
                "trend": "insufficient_data", 
                "message": "분석할 데이터가 부족합니다",
                "weekly_data": [],
                "recommendations": ["더 많은 데이터 수집이 필요합니다"]
            }
        
        # 추이 계산
        scores = [float(score.score_percentage) for score in weekly_scores]
        trend_analysis = self._calculate_trend(scores)
        
        # 카테고리별 분석
        category_trends = self._analyze_categories(weekly_scores)
        
        # 특이사항 감지
        alerts = self._detect_alerts(weekly_scores)
        
        # 상세 주간 데이터
        weekly_data = []
        for i, score in enumerate(weekly_scores):
            trend_indicator = "stable"
            if i > 0:
                prev_score = float(weekly_scores[i-1].score_percentage)
                curr_score = float(score.score_percentage)
                if curr_score > prev_score + 5:
                    trend_indicator = "improving"
                elif curr_score < prev_score - 5:
                    trend_indicator = "declining"
            
            weekly_data.append({
                "week": score.week_start_date.strftime("%Y-%m-%d"),
                "score": float(score.score_percentage),
                "trend_indicator": trend_indicator,
                "checklist_count": score.checklist_count,
                "total_score": score.total_score
            })
        
        # 트렌드 분석 결과 저장
        self._save_trend_analysis(senior_id, {
            "trend": trend_analysis["trend"],
            "weekly_data": weekly_data,
            "category_analysis": category_trends,
            "alerts": alerts
        })
        
        return {
            "trend": trend_analysis["trend"],
            "trend_strength": trend_analysis["strength"],
            "average_score": statistics.mean(scores),
            "score_change": scores[-1] - scores[0] if len(scores) >= 2 else 0,
            "weekly_data": weekly_data,
            "category_analysis": category_trends,
            "alerts": alerts,
            "recommendations": self._generate_recommendations(trend_analysis, alerts)
        }
    
    def _calculate_trend(self, scores: List[float]) -> Dict[str, Any]:
        """점수 배열로부터 추이 계산"""
        if len(scores) < 2:
            return {"trend": "stable", "strength": 0}
        
        # 선형 회귀를 통한 추세 계산
        n = len(scores)
        x = list(range(n))
        y = scores
        
        # 기울기 계산 (최소제곱법)
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # 추세 판단
        if slope > 2:
            return {"trend": "improving", "strength": min(abs(slope), 10)}
        elif slope < -2:
            return {"trend": "declining", "strength": min(abs(slope), 10)}
        else:
            return {"trend": "stable", "strength": abs(slope)}
    
    def _analyze_categories(self, weekly_scores: List[WeeklyChecklistScore]) -> Dict[str, Any]:
        """카테고리별 상세 분석"""
        category_data = {}
        
        for score in weekly_scores:
            if score.score_breakdown:
                for category, value in score.score_breakdown.items():
                    if category not in category_data:
                        category_data[category] = []
                    category_data[category].append(float(value) if value else 0)
        
        category_trends = {}
        for category, values in category_data.items():
            if len(values) >= 2:
                trend = self._calculate_trend(values)
                category_trends[category] = {
                    "current_score": values[-1],
                    "trend": trend["trend"],
                    "change": values[-1] - values[0],
                    "average": statistics.mean(values)
                }
        
        return category_trends
    
    def _detect_alerts(self, weekly_scores: List[WeeklyChecklistScore]) -> List[Dict[str, Any]]:
        """이상 상황 감지"""
        alerts = []
        
        if len(weekly_scores) >= 2:
            latest = weekly_scores[-1]
            previous = weekly_scores[-2]
            
            # 급격한 점수 하락
            score_diff = float(latest.score_percentage) - float(previous.score_percentage)
            if score_diff < -15:
                alerts.append({
                    "type": "score_drop",
                    "severity": "high",
                    "message": f"이번 주 컨디션이 {abs(score_diff):.1f}% 급격히 저하되었습니다",
                    "recommendation": "가디언에게 즉시 연락하여 상태 확인이 필요합니다"
                })
            
            # 지속적인 하락 (3주 연속)
            if len(weekly_scores) >= 3:
                last_three = weekly_scores[-3:]
                scores = [float(s.score_percentage) for s in last_three]
                if all(scores[i] > scores[i+1] for i in range(len(scores)-1)):
                    alerts.append({
                        "type": "continuous_decline",
                        "severity": "medium", 
                        "message": "3주 연속 상태가 저하되고 있습니다",
                        "recommendation": "전문의 상담을 고려해보세요"
                    })
            
            # 체크리스트 제출 빈도 저하
            if latest.checklist_count < 2 and previous.checklist_count >= 3:
                alerts.append({
                    "type": "low_activity",
                    "severity": "low",
                    "message": "이번 주 케어 활동이 평소보다 적습니다",
                    "recommendation": "케어기버와 스케줄을 확인해보세요"
                })
        
        return alerts
    
    def _generate_recommendations(self, trend_analysis: Dict, alerts: List) -> List[str]:
        """상황별 추천사항 생성"""
        recommendations = []
        
        trend = trend_analysis.get("trend", "stable")
        
        if trend == "improving":
            recommendations.append("현재 상태가 좋아지고 있습니다! 지금의 케어 방식을 유지하세요")
            recommendations.append("가디언께서 더 자주 안부 연락을 해주시면 더욱 좋을 것 같습니다")
            
        elif trend == "declining":
            recommendations.append("상태 저하가 우려됩니다. 케어 계획을 점검해보세요")
            recommendations.append("의료진과 상담하여 케어 방식 조정을 고려해보세요")
            recommendations.append("가디언과의 소통을 늘려 정서적 지원을 강화하세요")
            
        else:  # stable
            recommendations.append("안정적인 상태를 유지하고 있습니다")
            recommendations.append("현재의 케어 루틴을 지속하시면 됩니다")
        
        # 알림별 추가 권장사항
        for alert in alerts:
            if alert["type"] == "score_drop":
                recommendations.append("응급 상황이 아닌지 확인하고 필요시 의료진에게 연락하세요")
            elif alert["type"] == "continuous_decline":
                recommendations.append("종합적인 건강 검진을 받아보시기 바랍니다")
        
        return recommendations
    
    def _save_trend_analysis(self, senior_id: int, analysis_data: Dict[str, Any]):
        """트렌드 분석 결과를 데이터베이스에 저장"""
        
        # 기존 분석 결과가 있는지 확인 (오늘 날짜)
        today = date.today()
        existing_analysis = self.db.query(HealthTrendAnalysis).filter(
            HealthTrendAnalysis.senior_id == senior_id,
            HealthTrendAnalysis.analysis_date == today
        ).first()
        
        if existing_analysis:
            # 기존 레코드 업데이트
            existing_analysis.trend_summary = analysis_data
            existing_analysis.ai_insights = f"트렌드: {analysis_data['trend']}, 알림: {len(analysis_data['alerts'])}개"
            existing_analysis.updated_at = func.now()
        else:
            # 새 레코드 생성
            new_analysis = HealthTrendAnalysis(
                senior_id=senior_id,
                analysis_date=today,
                period_weeks=4,
                trend_summary=analysis_data,
                key_indicators={
                    "trend": analysis_data["trend"],
                    "alert_count": len(analysis_data["alerts"]),
                    "weekly_count": len(analysis_data["weekly_data"])
                },
                ai_insights=f"트렌드: {analysis_data['trend']}, 알림: {len(analysis_data['alerts'])}개"
            )
            self.db.add(new_analysis)
        
        self.db.commit()
