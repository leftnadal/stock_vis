"""
ML Production Manager (News Intelligence Pipeline v3 - Phase 5)

Shadow Mode 검증 완료 후 ML 가중치를 실제 운영에 적용하는 매니저.
- 자동 배포 (4주 연속 Safety Gate 통과 시)
- Engine C ML 가중치 통합
- LLM 정확도 측정
- 주간 성능 리포트
- 롤백 기능
"""

import logging
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from ..models import MLModelHistory, NewsArticle

logger = logging.getLogger(__name__)

# 자동 배포 조건
AUTO_DEPLOY_CONSECUTIVE_WEEKS = 4
AUTO_DEPLOY_MIN_F1 = 0.55
AUTO_DEPLOY_MIN_AGREEMENT = 0.70


class MLProductionManager:
    """
    ML 모델 프로덕션 운영 매니저

    check_auto_deploy() → 자동 배포 조건 확인 + 실행
    measure_llm_accuracy() → LLM 분석 정확도 측정
    generate_weekly_report() → 주간 ML 성능 리포트
    rollback_model() → 이전 모델로 롤백
    get_deployed_weights() → 현재 배포된 ML 가중치 반환
    """

    # ════════════════════════════════════════
    # 자동 배포 체크
    # ════════════════════════════════════════

    def check_auto_deploy(self) -> dict:
        """
        자동 배포 조건 확인 및 실행

        조건:
        1. 최근 4주 연속 Safety Gate 통과 (F1 >= 0.55)
        2. 최근 Shadow 비교에서 agreement_rate >= 0.70
        3. 현재 deployed 모델이 없거나, 새 모델이 더 좋은 경우

        Returns:
            dict: {action, reason, model_version?, deployed?}
        """
        # 최근 4주 모델 조회 (최신순)
        recent_models = list(
            MLModelHistory.objects.filter(
                deployment_status__in=['shadow', 'deployed'],
            ).order_by('-trained_at')[:AUTO_DEPLOY_CONSECUTIVE_WEEKS]
        )

        if len(recent_models) < AUTO_DEPLOY_CONSECUTIVE_WEEKS:
            return {
                'action': 'wait',
                'reason': f'Need {AUTO_DEPLOY_CONSECUTIVE_WEEKS} consecutive models, '
                          f'have {len(recent_models)}',
                'models_count': len(recent_models),
            }

        # 4주 연속 Safety Gate 통과 확인
        all_passed = all(m.safety_gate_passed for m in recent_models)
        if not all_passed:
            failed_versions = [
                m.model_version for m in recent_models
                if not m.safety_gate_passed
            ]
            return {
                'action': 'wait',
                'reason': 'Not all recent models passed Safety Gate',
                'failed_versions': failed_versions,
            }

        # F1 최소 기준 확인
        all_above_f1 = all(
            m.f1_score >= AUTO_DEPLOY_MIN_F1 for m in recent_models
        )
        if not all_above_f1:
            low_f1_versions = [
                {'version': m.model_version, 'f1': m.f1_score}
                for m in recent_models
                if m.f1_score < AUTO_DEPLOY_MIN_F1
            ]
            return {
                'action': 'wait',
                'reason': f'Not all models meet F1 >= {AUTO_DEPLOY_MIN_F1}',
                'low_f1_versions': low_f1_versions,
            }

        # 최신 모델의 agreement rate 확인
        latest = recent_models[0]
        agreement_rate = 0.0
        if latest.shadow_comparison:
            agreement_rate = latest.shadow_comparison.get('agreement_rate', 0.0)

        if agreement_rate < AUTO_DEPLOY_MIN_AGREEMENT:
            return {
                'action': 'wait',
                'reason': f'Agreement rate {agreement_rate:.2f} < {AUTO_DEPLOY_MIN_AGREEMENT}',
                'agreement_rate': agreement_rate,
            }

        # 현재 deployed 모델 확인
        current_deployed = MLModelHistory.objects.filter(
            deployment_status='deployed',
        ).first()

        if current_deployed and current_deployed.id == latest.id:
            return {
                'action': 'skip',
                'reason': 'Latest model is already deployed',
                'model_version': latest.model_version,
            }

        # 배포 실행
        if latest.deployment_status == 'shadow':
            deploy_result = self._deploy_model(latest)
            return {
                'action': 'deployed',
                'reason': f'{AUTO_DEPLOY_CONSECUTIVE_WEEKS} consecutive weeks passed, '
                          f'agreement_rate={agreement_rate:.2f}',
                'model_version': latest.model_version,
                'model_id': latest.id,
                'weights': latest.smoothed_weights,
                **deploy_result,
            }

        return {
            'action': 'skip',
            'reason': f'Latest model status: {latest.deployment_status}',
            'model_version': latest.model_version,
        }

    def _deploy_model(self, model: MLModelHistory) -> dict:
        """모델을 deployed 상태로 전환"""
        # 이전 deployed 모델 → rolled_back
        prev_deployed = MLModelHistory.objects.filter(
            deployment_status='deployed',
        ).exclude(id=model.id)

        rolled_back_count = prev_deployed.update(
            deployment_status='rolled_back',
        )

        # 현재 모델 → deployed
        model.deployment_status = 'deployed'
        model.deployed_at = timezone.now()
        model.save(update_fields=['deployment_status', 'deployed_at'])

        logger.info(
            f"ML model deployed: {model.model_version} "
            f"(F1={model.f1_score:.3f}, rolled_back={rolled_back_count})"
        )

        return {
            'deployed_at': str(model.deployed_at),
            'rolled_back_count': rolled_back_count,
        }

    # ════════════════════════════════════════
    # LLM 정확도 측정
    # ════════════════════════════════════════

    def measure_llm_accuracy(self, days: int = 7) -> dict:
        """
        LLM 분석 정확도 측정

        LLM이 예측한 방향(bullish/bearish/neutral)과
        실제 주가 변동을 비교합니다.

        Args:
            days: 측정 기간 (기본: 7일)

        Returns:
            dict: {total, correct, accuracy, direction_accuracy, details}
        """
        cutoff = timezone.now() - timedelta(days=days)

        # LLM 분석 완료 + ML Label이 있는 뉴스
        articles = NewsArticle.objects.filter(
            llm_analyzed=True,
            llm_analysis__isnull=False,
            ml_label_24h__isnull=False,
            published_at__gte=cutoff,
        ).order_by('-published_at')[:200]

        total = 0
        correct_direction = 0
        correct_importance = 0
        details = []

        for article in articles:
            analysis = article.llm_analysis
            if not analysis:
                continue

            # LLM이 예측한 방향 추출
            direct_impacts = analysis.get('direct_impacts', [])
            if not direct_impacts:
                continue

            # 첫 번째 direct impact의 방향
            primary_impact = direct_impacts[0]
            llm_direction = primary_impact.get('direction', 'neutral')

            # 실제 주가 변동
            actual_change = article.ml_label_24h

            # 방향 일치 확인
            if actual_change is not None:
                total += 1
                actual_direction = (
                    'bullish' if actual_change > 0.5
                    else 'bearish' if actual_change < -0.5
                    else 'neutral'
                )
                if llm_direction == actual_direction:
                    correct_direction += 1
                elif llm_direction == 'neutral' and abs(actual_change) <= 1.0:
                    correct_direction += 1  # neutral 예측 + 작은 변동 = 정확

                # 중요도 일치 (LLM이 중요하다고 판단한 것이 실제 중요한지)
                llm_important = primary_impact.get('confidence', 0) >= 0.7
                actual_important = article.ml_label_important
                if llm_important == actual_important:
                    correct_importance += 1

                if len(details) < 20:
                    details.append({
                        'article_id': str(article.id),
                        'title': article.title[:80],
                        'llm_direction': llm_direction,
                        'actual_direction': actual_direction,
                        'actual_change': round(actual_change, 2),
                        'direction_match': llm_direction == actual_direction,
                    })

        direction_accuracy = (
            round(correct_direction / total, 4) if total > 0 else 0.0
        )
        importance_accuracy = (
            round(correct_importance / total, 4) if total > 0 else 0.0
        )

        result = {
            'period_days': days,
            'total_measured': total,
            'correct_direction': correct_direction,
            'correct_importance': correct_importance,
            'direction_accuracy': direction_accuracy,
            'importance_accuracy': importance_accuracy,
            'sample_details': details,
        }

        logger.info(
            f"LLM accuracy: direction={direction_accuracy:.2%} "
            f"importance={importance_accuracy:.2%} ({total} articles)"
        )
        return result

    # ════════════════════════════════════════
    # 주간 성능 리포트
    # ════════════════════════════════════════

    def generate_weekly_report(self) -> dict:
        """
        주간 ML 성능 리포트 생성

        Returns:
            dict: {
                period, model_status, performance_trend,
                llm_accuracy, data_stats, recommendations
            }
        """
        now = timezone.now()
        week_ago = now - timedelta(days=7)

        # 모델 상태
        deployed = MLModelHistory.objects.filter(
            deployment_status='deployed',
        ).first()

        latest = MLModelHistory.objects.order_by('-trained_at').first()

        # 최근 4주 성능 추이
        recent_models = list(
            MLModelHistory.objects.filter(
                trained_at__gte=now - timedelta(weeks=4),
            ).order_by('trained_at').values(
                'model_version', 'f1_score', 'precision', 'recall',
                'safety_gate_passed', 'deployment_status', 'trained_at',
            )
        )

        # F1 추이 분석
        f1_scores = [m['f1_score'] for m in recent_models if m['f1_score']]
        f1_trend = 'stable'
        if len(f1_scores) >= 2:
            diff = f1_scores[-1] - f1_scores[0]
            if diff > 0.02:
                f1_trend = 'improving'
            elif diff < -0.02:
                f1_trend = 'declining'

        # LLM 정확도 (최근 7일)
        llm_accuracy = self.measure_llm_accuracy(days=7)

        # 데이터 통계
        total_labeled = NewsArticle.objects.filter(
            ml_label_24h__isnull=False,
        ).count()

        new_labeled = NewsArticle.objects.filter(
            ml_label_24h__isnull=False,
            ml_label_updated_at__gte=week_ago,
        ).count()

        new_analyzed = NewsArticle.objects.filter(
            llm_analyzed=True,
            updated_at__gte=week_ago,
        ).count()

        # 추천 사항 생성
        recommendations = self._generate_recommendations(
            f1_trend, f1_scores, llm_accuracy, total_labeled
        )

        report = {
            'period': {
                'start': str(week_ago.date()),
                'end': str(now.date()),
            },
            'model_status': {
                'deployed_version': deployed.model_version if deployed else None,
                'deployed_f1': deployed.f1_score if deployed else None,
                'latest_version': latest.model_version if latest else None,
                'latest_f1': latest.f1_score if latest else None,
                'latest_status': latest.deployment_status if latest else None,
            },
            'performance_trend': {
                'trend': f1_trend,
                'recent_f1_scores': [
                    {'version': m['model_version'], 'f1': m['f1_score']}
                    for m in recent_models
                ],
                'gate_pass_rate': (
                    sum(1 for m in recent_models if m['safety_gate_passed'])
                    / len(recent_models) if recent_models else 0
                ),
            },
            'llm_accuracy': {
                'direction_accuracy': llm_accuracy['direction_accuracy'],
                'importance_accuracy': llm_accuracy['importance_accuracy'],
                'total_measured': llm_accuracy['total_measured'],
            },
            'data_stats': {
                'total_labeled': total_labeled,
                'new_labeled_this_week': new_labeled,
                'new_analyzed_this_week': new_analyzed,
            },
            'recommendations': recommendations,
            'generated_at': str(now),
        }

        logger.info(f"Weekly ML report generated: f1_trend={f1_trend}")
        return report

    @staticmethod
    def _generate_recommendations(
        f1_trend: str,
        f1_scores: list,
        llm_accuracy: dict,
        total_labeled: int,
    ) -> list[str]:
        """성능 기반 추천 사항 생성"""
        recs = []

        if f1_trend == 'declining':
            recs.append(
                'F1 score declining. Consider reviewing data quality '
                'or feature engineering.'
            )

        if f1_scores and f1_scores[-1] < 0.55:
            recs.append(
                f'Latest F1 ({f1_scores[-1]:.2f}) below threshold. '
                'Model not ready for deployment.'
            )

        if llm_accuracy['direction_accuracy'] < 0.5:
            recs.append(
                'LLM direction accuracy below 50%. '
                'Consider prompt tuning or tier recalibration.'
            )

        if total_labeled < 3000:
            recs.append(
                f'Only {total_labeled} labeled samples. '
                'Consider waiting for more data before LightGBM transition.'
            )
        elif total_labeled >= 10000:
            recs.append(
                f'{total_labeled} labeled samples available. '
                'Ready for LightGBM Phase 2 transition.'
            )

        if not recs:
            recs.append('All metrics healthy. System operating normally.')

        return recs

    # ════════════════════════════════════════
    # 롤백
    # ════════════════════════════════════════

    def rollback_model(self) -> dict:
        """
        현재 deployed 모델을 롤백하고 수동 가중치로 복귀

        Returns:
            dict: {status, rolled_back_version?, fallback}
        """
        deployed = MLModelHistory.objects.filter(
            deployment_status='deployed',
        ).first()

        if not deployed:
            return {
                'status': 'no_deployed_model',
                'fallback': 'manual_weights',
            }

        deployed.deployment_status = 'rolled_back'
        deployed.save(update_fields=['deployment_status'])

        logger.warning(
            f"ML model rolled back: {deployed.model_version}. "
            "Reverting to manual weights."
        )

        return {
            'status': 'rolled_back',
            'rolled_back_version': deployed.model_version,
            'fallback': 'manual_weights',
        }

    # ════════════════════════════════════════
    # 연속 하락 추세 감지
    # ════════════════════════════════════════

    def detect_consecutive_decline(self, weeks: int = 3) -> dict:
        """
        연속 하락 추세 감지 및 Rolling Window 축소 권고

        최근 weeks+1개 모델의 F1 score를 비교하여 연속 하락 여부를 확인합니다.
        연속 하락 감지 시 Rolling Window 축소 권고(8→6→4주)와
        Feature Importance 리포트를 반환합니다.

        Args:
            weeks: 연속 하락 감지 기준 주수 (기본: 3)

        Returns:
            dict: {
                consecutive_decline: bool,
                decline_weeks: int,
                f1_history: list,
                action_taken: str,
                previous_window: int,
                new_window: int,
                feature_importance: dict or None,
                alert_message: str or None,
            }
        """
        from news.services.ml_weight_optimizer import ROLLING_WINDOW_WEEKS

        # 최근 weeks+1개 모델 조회 (최신순)
        recent_models = list(
            MLModelHistory.objects.order_by('-trained_at')[:weeks + 1]
        )

        f1_history = [
            {
                'version': m.model_version,
                'f1': m.f1_score,
                'trained_at': str(m.trained_at),
            }
            for m in recent_models
        ]

        # 기본 반환값
        base_result = {
            'consecutive_decline': False,
            'decline_weeks': 0,
            'f1_history': f1_history,
            'action_taken': 'none',
            'previous_window': ROLLING_WINDOW_WEEKS,
            'new_window': ROLLING_WINDOW_WEEKS,
            'feature_importance': None,
            'alert_message': None,
        }

        # 모델이 충분하지 않으면 감지 불가
        if len(recent_models) < weeks + 1:
            return base_result

        # 연속 하락 확인: 최신 weeks개 모델이 각각 이전 모델보다 F1이 낮은지
        # recent_models[0] = 가장 최신, recent_models[-1] = 가장 오래된
        decline_count = 0
        for i in range(weeks):
            if recent_models[i].f1_score < recent_models[i + 1].f1_score:
                decline_count += 1
            else:
                break

        if decline_count < weeks:
            base_result['decline_weeks'] = decline_count
            return base_result

        # 연속 하락 감지 — Rolling Window 축소 계산
        latest = recent_models[0]

        # 현재 window 크기: training_config에서 읽거나 기본값 사용
        current_window = ROLLING_WINDOW_WEEKS
        if latest.training_config and isinstance(latest.training_config, dict):
            current_window = latest.training_config.get(
                'rolling_window_weeks', ROLLING_WINDOW_WEEKS
            )

        new_window = max(current_window - 2, 4)

        # Feature Importance 리포트
        feature_importance = None
        if latest.feature_importance and isinstance(latest.feature_importance, dict):
            feature_importance = latest.feature_importance

        alert_message = (
            f"{weeks}주 연속 F1 하락 감지 "
            f"(최근 F1: {latest.f1_score:.3f}). "
            f"Rolling Window 축소 권고: {current_window}주 → {new_window}주."
        )

        logger.warning(
            f"detect_consecutive_decline: {alert_message} "
            f"f1_history={[h['f1'] for h in f1_history]}"
        )

        return {
            'consecutive_decline': True,
            'decline_weeks': decline_count,
            'f1_history': f1_history,
            'action_taken': 'shrink_window',
            'previous_window': current_window,
            'new_window': new_window,
            'feature_importance': feature_importance,
            'alert_message': alert_message,
        }

    # ════════════════════════════════════════
    # 배포 가중치 조회
    # ════════════════════════════════════════

    @staticmethod
    def get_deployed_weights() -> Optional[dict]:
        """
        현재 deployed 모델의 가중치 반환

        Returns:
            dict or None: deployed 모델의 smoothed_weights
        """
        deployed = MLModelHistory.objects.filter(
            deployment_status='deployed',
        ).first()

        if deployed and deployed.smoothed_weights:
            return deployed.smoothed_weights

        return None
