"""
ML Weight Optimizer (News Intelligence Pipeline v3 - Phase 4+6)

Engine C의 beta 가중치를 ML로 학습합니다.

Phase 4 (Logistic Regression):
- Company News 데이터만 사용 (초기)
- label_confidence를 sample_weight로 사용
- Time-Series Split (시간순, 랜덤 셔플 금지)
- Rolling Window 6~8주
- Safety Gate 3단계 검증
- Smoothing (0.7 x new + 0.3 x previous)
- Shadow Mode: ML vs 수동 가중치 비교 리포트

Phase 6 (LightGBM):
- 확장 Feature ⑥~⑩ (publish_hour, weekday, sector_volatility,
  earnings_proximity, topic_saturation)
- General News 점진 추가 (Engine A confidence >= 0.8)
- LightGBM Gradient Boosting
- Feature Importance 리포트
- A/B 테스트 (LR vs LightGBM)
"""

import logging
from datetime import timedelta
from typing import Optional

import numpy as np
from django.utils import timezone

from ..models import MLModelHistory, NewsArticle

logger = logging.getLogger(__name__)

# ── 학습 설정 ──

MIN_TRAINING_SAMPLES = 200
ROLLING_WINDOW_WEEKS = 8
TIME_SERIES_SPLITS = 3

# Safety Gate 임계값
SAFETY_GATE = {
    'tier1_f1': 0.55,
    'tier2_precision': 0.50,
    'tier3_degradation_max': 0.10,
}

# Smoothing 계수
SMOOTHING_NEW = 0.7
SMOOTHING_PREV = 0.3

# Feature 이름 (Engine C beta_1~beta_5)
FEATURE_NAMES = [
    'source_credibility',
    'entity_count',
    'sentiment_magnitude',
    'recency',
    'keyword_relevance',
]

# 확장 Feature 이름 (Phase 6: ⑥~⑩)
EXTENDED_FEATURE_NAMES = [
    'source_credibility',
    'entity_count',
    'sentiment_magnitude',
    'recency',
    'keyword_relevance',
    'publish_hour',
    'weekday',
    'sector_volatility',
    'earnings_proximity',
    'topic_saturation',
]

# LightGBM 전환 조건
LIGHTGBM_MIN_SAMPLES = 10000
LIGHTGBM_STAGNATION_WEEKS = 3
LIGHTGBM_STAGNATION_THRESHOLD = 0.01  # 1%p

# 소스 신뢰도 (Engine C와 동일)
SOURCE_CREDIBILITY = {
    'reuters': 1.0, 'bloomberg': 1.0, 'wsj': 0.95,
    'wall street journal': 0.95, 'cnbc': 0.90,
    'financial times': 0.95, 'ft': 0.95,
    'barrons': 0.90, "barron's": 0.90, 'marketwatch': 0.85,
    'seeking alpha': 0.75, 'motley fool': 0.70,
    'yahoo finance': 0.80, 'benzinga': 0.75,
    'investopedia': 0.70, 'the verge': 0.70,
    'techcrunch': 0.70, 'associated press': 0.90, 'ap': 0.90,
}
DEFAULT_SOURCE_SCORE = 0.5


class MLWeightOptimizer:
    """
    Engine C 가중치를 ML로 최적화하는 서비스

    run_training_pipeline() → 주간 학습 + Safety Gate + Smoothing + 저장
    generate_shadow_comparison() → Shadow Mode 비교 리포트
    get_current_status() → 현재 모델 상태 요약
    """

    # ════════════════════════════════════════
    # Feature 추출
    # ════════════════════════════════════════

    @staticmethod
    def extract_features(article: NewsArticle) -> list[float]:
        """
        NewsArticle에서 Engine C의 5개 raw feature 추출

        Returns:
            [f1, f2, f3, f4, f5] - 각 0~1 범위
        """
        # f1: source_credibility
        source_lower = (article.source or '').lower().strip()
        f1 = SOURCE_CREDIBILITY.get(source_lower, DEFAULT_SOURCE_SCORE)

        # f2: entity_count (normalized)
        tickers = article.rule_tickers or []
        sectors = article.rule_sectors or []
        entity_raw = len(tickers) + len(sectors)
        f2 = min(entity_raw / 5.0, 1.0)

        # f3: sentiment_magnitude
        if article.sentiment_score is not None:
            f3 = min(abs(float(article.sentiment_score)), 1.0)
        else:
            f3 = 0.3

        # f4: recency proxy (publish hour EST -> normalized)
        # 시장 시간(9:30-16:00) 발행일수록 높은 점수
        pub_hour = article.published_at.hour
        if 9 <= pub_hour <= 16:
            f4 = 1.0
        elif 6 <= pub_hour <= 9 or 16 < pub_hour <= 19:
            f4 = 0.7
        else:
            f4 = 0.4

        # f5: keyword_relevance (sector match depth)
        f5 = min(len(sectors) / 3.0, 1.0) if sectors else 0.0

        return [f1, f2, f3, f4, f5]

    # ════════════════════════════════════════
    # 학습 데이터 준비
    # ════════════════════════════════════════

    def prepare_training_data(
        self,
        weeks: int = ROLLING_WINDOW_WEEKS,
        company_news_only: bool = True,
    ) -> dict:
        """
        학습 데이터 준비

        Args:
            weeks: Rolling window 크기 (주)
            company_news_only: Company News만 사용 여부

        Returns:
            {
                'X': np.ndarray (n_samples, 5),
                'y': np.ndarray (n_samples,),
                'weights': np.ndarray (n_samples,),
                'n_samples': int,
                'n_positive': int,
                'n_negative': int,
                'date_range': (start_date, end_date),
            }
        """
        cutoff = timezone.now() - timedelta(weeks=weeks)

        queryset = NewsArticle.objects.filter(
            ml_label_24h__isnull=False,
            ml_label_important__isnull=False,
            ml_label_confidence__isnull=False,
            importance_score__isnull=False,
            published_at__gte=cutoff,
        ).order_by('published_at')

        if company_news_only:
            queryset = queryset.filter(
                entities__isnull=False,
            ).distinct()

        articles = list(queryset.select_related().prefetch_related('entities'))

        if len(articles) < MIN_TRAINING_SAMPLES:
            return {
                'X': None, 'y': None, 'weights': None,
                'n_samples': len(articles),
                'n_positive': 0, 'n_negative': 0,
                'date_range': None,
                'error': f'Insufficient data: {len(articles)} < {MIN_TRAINING_SAMPLES}',
            }

        X = []
        y = []
        weights = []

        for article in articles:
            features = self.extract_features(article)
            X.append(features)
            y.append(1 if article.ml_label_important else 0)
            weights.append(article.ml_label_confidence)

        X = np.array(X, dtype=np.float64)
        y = np.array(y, dtype=np.int32)
        weights = np.array(weights, dtype=np.float64)

        n_positive = int(np.sum(y == 1))
        n_negative = int(np.sum(y == 0))

        date_range = (
            articles[0].published_at.date(),
            articles[-1].published_at.date(),
        )

        return {
            'X': X,
            'y': y,
            'weights': weights,
            'n_samples': len(articles),
            'n_positive': n_positive,
            'n_negative': n_negative,
            'date_range': date_range,
        }

    # ════════════════════════════════════════
    # Time-Series Cross Validation
    # ════════════════════════════════════════

    @staticmethod
    def time_series_split(
        n_samples: int,
        n_splits: int = TIME_SERIES_SPLITS,
    ) -> list[tuple]:
        """
        Time-Series Split (시간순, 랜덤 셔플 금지)

        Returns:
            [(train_idx, test_idx), ...] - n_splits개의 (train, test) 인덱스 쌍
        """
        splits = []
        min_train_size = n_samples // (n_splits + 1)

        for i in range(n_splits):
            train_end = min_train_size * (i + 1) + min_train_size
            test_end = min(train_end + min_train_size, n_samples)

            if train_end >= n_samples or test_end <= train_end:
                break

            train_idx = np.arange(0, train_end)
            test_idx = np.arange(train_end, test_end)
            splits.append((train_idx, test_idx))

        return splits

    # ════════════════════════════════════════
    # 모델 학습
    # ════════════════════════════════════════

    def train_model(self, X, y, weights) -> dict:
        """
        Logistic Regression 학습 + Time-Series CV

        Returns:
            {
                'coefficients': list[float],
                'normalized_weights': dict,
                'cv_scores': list[dict],
                'final_metrics': dict,
            }
        """
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import (
            f1_score, precision_score, recall_score, accuracy_score,
        )

        splits = self.time_series_split(len(X))
        if not splits:
            return {'error': 'Not enough data for time-series split'}

        cv_scores = []

        for train_idx, test_idx in splits:
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            w_train = weights[train_idx]

            model = LogisticRegression(
                class_weight='balanced',
                max_iter=1000,
                random_state=42,
                solver='lbfgs',
            )
            model.fit(X_train, y_train, sample_weight=w_train)
            y_pred = model.predict(X_test)

            fold_metrics = {
                'f1': float(f1_score(y_test, y_pred, zero_division=0)),
                'precision': float(precision_score(y_test, y_pred, zero_division=0)),
                'recall': float(recall_score(y_test, y_pred, zero_division=0)),
                'accuracy': float(accuracy_score(y_test, y_pred)),
                'train_size': len(train_idx),
                'test_size': len(test_idx),
            }
            cv_scores.append(fold_metrics)

        # Final model: 전체 데이터로 학습
        final_model = LogisticRegression(
            class_weight='balanced',
            max_iter=1000,
            random_state=42,
            solver='lbfgs',
        )
        final_model.fit(X, y, sample_weight=weights)

        # 계수 추출 및 정규화
        coefficients = final_model.coef_[0].tolist()
        abs_coeffs = [abs(c) for c in coefficients]
        total = sum(abs_coeffs) or 1.0
        normalized = {
            name: round(abs_c / total, 4)
            for name, abs_c in zip(FEATURE_NAMES, abs_coeffs)
        }

        # CV 평균 메트릭
        avg_metrics = {
            'f1': round(np.mean([s['f1'] for s in cv_scores]), 4),
            'precision': round(np.mean([s['precision'] for s in cv_scores]), 4),
            'recall': round(np.mean([s['recall'] for s in cv_scores]), 4),
            'accuracy': round(np.mean([s['accuracy'] for s in cv_scores]), 4),
        }

        return {
            'coefficients': [round(c, 6) for c in coefficients],
            'normalized_weights': normalized,
            'cv_scores': cv_scores,
            'final_metrics': avg_metrics,
        }

    # ════════════════════════════════════════
    # Safety Gate (3단계)
    # ════════════════════════════════════════

    def safety_gate_check(self, metrics: dict) -> dict:
        """
        Safety Gate 3단계 검증

        Tier 1: F1 >= 0.55
        Tier 2: Precision >= 0.50
        Tier 3: 이전 모델 대비 F1 하락 <= 10%p

        Returns:
            {'passed': bool, 'tier1': dict, 'tier2': dict, 'tier3': dict}
        """
        f1 = metrics.get('f1', 0)
        precision = metrics.get('precision', 0)

        # Tier 1: 기본 F1 임계값
        tier1 = {
            'check': 'F1 >= 0.55',
            'value': f1,
            'threshold': SAFETY_GATE['tier1_f1'],
            'passed': f1 >= SAFETY_GATE['tier1_f1'],
        }

        # Tier 2: Precision 임계값 (false positive 통제)
        tier2 = {
            'check': 'Precision >= 0.50',
            'value': precision,
            'threshold': SAFETY_GATE['tier2_precision'],
            'passed': precision >= SAFETY_GATE['tier2_precision'],
        }

        # Tier 3: 이전 모델 대비 성능 저하 체크
        prev_model = MLModelHistory.objects.filter(
            safety_gate_passed=True,
        ).order_by('-trained_at').first()

        if prev_model:
            prev_f1 = prev_model.f1_score
            degradation = prev_f1 - f1
            tier3 = {
                'check': f'F1 degradation <= {SAFETY_GATE["tier3_degradation_max"]}',
                'value': round(degradation, 4),
                'prev_f1': round(prev_f1, 4),
                'threshold': SAFETY_GATE['tier3_degradation_max'],
                'passed': degradation <= SAFETY_GATE['tier3_degradation_max'],
            }
        else:
            # 이전 모델 없음 → 자동 통과
            tier3 = {
                'check': 'No previous model (auto-pass)',
                'value': 0,
                'prev_f1': None,
                'threshold': SAFETY_GATE['tier3_degradation_max'],
                'passed': True,
            }

        all_passed = tier1['passed'] and tier2['passed'] and tier3['passed']

        return {
            'passed': all_passed,
            'tier1': tier1,
            'tier2': tier2,
            'tier3': tier3,
        }

    # ════════════════════════════════════════
    # Weight Smoothing
    # ════════════════════════════════════════

    @staticmethod
    def smooth_weights(
        new_weights: dict,
        prev_weights: Optional[dict] = None,
    ) -> dict:
        """
        가중치 스무딩: 0.7 x new + 0.3 x previous

        급격한 가중치 변동 방지
        """
        if not prev_weights:
            return new_weights

        smoothed = {}
        for name in FEATURE_NAMES:
            new_val = new_weights.get(name, 0.2)
            prev_val = prev_weights.get(name, 0.2)
            smoothed[name] = round(
                SMOOTHING_NEW * new_val + SMOOTHING_PREV * prev_val, 4
            )

        # 합계 정규화
        total = sum(smoothed.values()) or 1.0
        return {k: round(v / total, 4) for k, v in smoothed.items()}

    # ════════════════════════════════════════
    # Shadow Mode 비교 리포트
    # ════════════════════════════════════════

    def generate_shadow_comparison(
        self,
        ml_weights: dict,
        manual_weights: Optional[dict] = None,
        days: int = 7,
    ) -> dict:
        """
        Shadow Mode: ML 가중치 vs 수동 가중치 비교

        Returns:
            {
                'period': str,
                'total_articles': int,
                'manual_selected': int,
                'ml_selected': int,
                'overlap': int,
                'agreement_rate': float,
                'only_manual': list,
                'only_ml': list,
            }
        """
        if manual_weights is None:
            from .news_classifier import DEFAULT_WEIGHTS
            manual_weights = DEFAULT_WEIGHTS

        cutoff = timezone.now() - timedelta(days=days)
        articles = list(
            NewsArticle.objects.filter(
                published_at__gte=cutoff,
                importance_score__isnull=False,
            ).order_by('-published_at')[:500]
        )

        if not articles:
            return {
                'period': f'Last {days} days',
                'total_articles': 0,
                'manual_selected': 0,
                'ml_selected': 0,
                'overlap': 0,
                'agreement_rate': 0.0,
            }

        # 각 가중치로 importance 재계산
        manual_scores = {}
        ml_scores = {}

        for article in articles:
            features = self.extract_features(article)
            article_id = str(article.id)

            # 수동 가중치 점수
            manual_score = sum(
                manual_weights.get(FEATURE_NAMES[i], 0.2) * features[i]
                for i in range(5)
            )
            manual_scores[article_id] = manual_score

            # ML 가중치 점수
            ml_score = sum(
                ml_weights.get(FEATURE_NAMES[i], 0.2) * features[i]
                for i in range(5)
            )
            ml_scores[article_id] = ml_score

        # 상위 15% 선별
        top_n = max(1, int(len(articles) * 0.15))

        manual_top = set(
            sorted(manual_scores, key=manual_scores.get, reverse=True)[:top_n]
        )
        ml_top = set(
            sorted(ml_scores, key=ml_scores.get, reverse=True)[:top_n]
        )

        overlap = manual_top & ml_top
        only_manual = manual_top - ml_top
        only_ml = ml_top - manual_top

        agreement = len(overlap) / max(len(manual_top), 1)

        return {
            'period': f'Last {days} days',
            'total_articles': len(articles),
            'manual_selected': len(manual_top),
            'ml_selected': len(ml_top),
            'overlap': len(overlap),
            'agreement_rate': round(agreement, 4),
            'only_manual_count': len(only_manual),
            'only_ml_count': len(only_ml),
        }

    # ════════════════════════════════════════
    # 전체 학습 파이프라인
    # ════════════════════════════════════════

    def run_training_pipeline(self) -> dict:
        """
        주간 학습 파이프라인 (일요일 03:00 EST)

        1. 학습 데이터 준비 (Company News, Rolling Window)
        2. Logistic Regression 학습 + Time-Series CV
        3. Safety Gate 3단계 검증
        4. Weight Smoothing
        5. Shadow Mode 비교 리포트
        6. MLModelHistory 저장

        Returns:
            dict: 학습 결과 요약
        """
        logger.info("ML Weight Optimizer: Starting training pipeline")

        # 1. 데이터 준비
        data = self.prepare_training_data(
            weeks=ROLLING_WINDOW_WEEKS,
            company_news_only=True,
        )

        if data.get('error') or data['X'] is None:
            error_msg = data.get('error', 'Unknown error')
            logger.warning(f"Training aborted: {error_msg}")

            MLModelHistory.objects.create(
                model_version=self._generate_version(),
                algorithm='logistic_regression',
                training_samples=data.get('n_samples', 0),
                feature_count=5,
                f1_score=0.0,
                deployment_status='failed',
                training_config={
                    'rolling_window_weeks': ROLLING_WINDOW_WEEKS,
                    'company_news_only': True,
                    'error': error_msg,
                },
            )
            return {'status': 'failed', 'reason': error_msg}

        logger.info(
            f"Training data: {data['n_samples']} samples "
            f"(+:{data['n_positive']}, -:{data['n_negative']}), "
            f"range: {data['date_range']}"
        )

        # 2. 모델 학습
        train_result = self.train_model(data['X'], data['y'], data['weights'])

        if train_result.get('error'):
            error_msg = train_result['error']
            logger.warning(f"Training error: {error_msg}")

            MLModelHistory.objects.create(
                model_version=self._generate_version(),
                algorithm='logistic_regression',
                training_samples=data['n_samples'],
                feature_count=5,
                f1_score=0.0,
                deployment_status='failed',
                training_config={'error': error_msg},
            )
            return {'status': 'failed', 'reason': error_msg}

        metrics = train_result['final_metrics']
        new_weights = train_result['normalized_weights']
        logger.info(f"Training metrics: {metrics}")
        logger.info(f"Learned weights: {new_weights}")

        # 3. Safety Gate
        gate_result = self.safety_gate_check(metrics)
        logger.info(f"Safety Gate: {'PASSED' if gate_result['passed'] else 'FAILED'}")

        # 4. Weight Smoothing
        prev_model = MLModelHistory.objects.filter(
            safety_gate_passed=True,
        ).order_by('-trained_at').first()

        prev_weights = prev_model.smoothed_weights if prev_model else None
        smoothed = self.smooth_weights(new_weights, prev_weights)
        logger.info(f"Smoothed weights: {smoothed}")

        # 5. Shadow Mode 비교
        shadow = self.generate_shadow_comparison(
            ml_weights=smoothed, days=7,
        )

        # 6. 배포 상태 결정
        deployment_status = 'shadow' if gate_result['passed'] else 'failed'

        # 7. MLModelHistory 저장
        version = self._generate_version()
        history = MLModelHistory.objects.create(
            model_version=version,
            algorithm='logistic_regression',
            training_samples=data['n_samples'],
            feature_count=5,
            f1_score=metrics['f1'],
            precision=metrics['precision'],
            recall=metrics['recall'],
            accuracy=metrics['accuracy'],
            weights=new_weights,
            smoothed_weights=smoothed,
            feature_importance={
                name: {
                    'coefficient': coeff,
                    'weight': new_weights[name],
                    'smoothed_weight': smoothed[name],
                }
                for name, coeff in zip(
                    FEATURE_NAMES, train_result['coefficients']
                )
            },
            training_config={
                'rolling_window_weeks': ROLLING_WINDOW_WEEKS,
                'time_series_splits': TIME_SERIES_SPLITS,
                'company_news_only': True,
                'n_positive': data['n_positive'],
                'n_negative': data['n_negative'],
                'date_range': [
                    str(data['date_range'][0]),
                    str(data['date_range'][1]),
                ],
                'cv_scores': train_result['cv_scores'],
            },
            safety_gate_passed=gate_result['passed'],
            safety_gate_details=gate_result,
            deployment_status=deployment_status,
            shadow_comparison=shadow,
        )

        result = {
            'status': deployment_status,
            'model_version': version,
            'model_id': history.id,
            'metrics': metrics,
            'safety_gate': gate_result['passed'],
            'weights': smoothed,
            'shadow': shadow,
            'training_samples': data['n_samples'],
        }

        logger.info(f"Training pipeline complete: {result['status']}")
        return result

    # ════════════════════════════════════════
    # 모델 배포 (Shadow → Deployed)
    # ════════════════════════════════════════

    def deploy_model(self, model_id: int) -> dict:
        """
        Shadow Mode 모델을 Production으로 배포

        Safety Gate를 통과한 모델의 smoothed_weights를
        Engine C에 적용합니다.

        Args:
            model_id: MLModelHistory ID

        Returns:
            dict: 배포 결과
        """
        try:
            model = MLModelHistory.objects.get(id=model_id)
        except MLModelHistory.DoesNotExist:
            return {'status': 'error', 'reason': f'Model {model_id} not found'}

        if not model.safety_gate_passed:
            return {
                'status': 'error',
                'reason': 'Model did not pass Safety Gate',
            }

        if model.deployment_status == 'deployed':
            return {
                'status': 'already_deployed',
                'model_version': model.model_version,
            }

        # 이전 deployed 모델 → rolled_back
        MLModelHistory.objects.filter(
            deployment_status='deployed',
        ).update(deployment_status='rolled_back')

        # 현재 모델 → deployed
        model.deployment_status = 'deployed'
        model.deployed_at = timezone.now()
        model.save(update_fields=['deployment_status', 'deployed_at'])

        return {
            'status': 'deployed',
            'model_version': model.model_version,
            'weights': model.smoothed_weights,
            'deployed_at': str(model.deployed_at),
        }

    # ════════════════════════════════════════
    # 현재 상태 조회
    # ════════════════════════════════════════

    @staticmethod
    def get_current_status() -> dict:
        """
        현재 ML 모델 상태 요약

        Returns:
            dict: 최신 모델 정보, 배포 상태, 성능 추이
        """
        latest = MLModelHistory.objects.order_by('-trained_at').first()
        deployed = MLModelHistory.objects.filter(
            deployment_status='deployed',
        ).first()

        # 최근 4주 성능 추이
        recent_models = list(
            MLModelHistory.objects.order_by('-trained_at')[:4].values(
                'model_version', 'f1_score', 'precision', 'recall',
                'safety_gate_passed', 'deployment_status', 'trained_at',
            )
        )

        # 학습 가능 데이터 수
        labeled_count = NewsArticle.objects.filter(
            ml_label_24h__isnull=False,
            ml_label_important__isnull=False,
        ).count()

        return {
            'latest_model': {
                'version': latest.model_version if latest else None,
                'f1_score': latest.f1_score if latest else None,
                'status': latest.deployment_status if latest else None,
                'trained_at': str(latest.trained_at) if latest else None,
                'safety_gate': latest.safety_gate_passed if latest else None,
            } if latest else None,
            'deployed_model': {
                'version': deployed.model_version if deployed else None,
                'f1_score': deployed.f1_score if deployed else None,
                'weights': deployed.smoothed_weights if deployed else None,
                'deployed_at': str(deployed.deployed_at) if deployed else None,
            } if deployed else None,
            'recent_history': [
                {
                    'version': m['model_version'],
                    'f1': m['f1_score'],
                    'precision': m['precision'],
                    'recall': m['recall'],
                    'gate_passed': m['safety_gate_passed'],
                    'status': m['deployment_status'],
                    'trained_at': str(m['trained_at']),
                }
                for m in recent_models
            ],
            'labeled_data_count': labeled_count,
            'min_required': MIN_TRAINING_SAMPLES,
            'ready_for_training': labeled_count >= MIN_TRAINING_SAMPLES,
        }

    # ════════════════════════════════════════
    # Helper
    # ════════════════════════════════════════

    # ════════════════════════════════════════
    # Phase 6: 확장 Feature 추출
    # ════════════════════════════════════════

    @staticmethod
    def extract_extended_features(article: NewsArticle) -> list[float]:
        """
        NewsArticle에서 10개 확장 feature 추출 (Phase 6)

        Returns:
            [f1..f5 (기존), f6..f10 (확장)] - 각 0~1 범위
        """
        # f1~f5: 기존 feature
        base_features = MLWeightOptimizer.extract_features(article)

        # f6: publish_hour (0~23 → 0~1)
        f6 = article.published_at.hour / 23.0

        # f7: weekday (0=월 ~ 6=일 → 0~1)
        f7 = article.published_at.weekday() / 6.0

        # f8: sector_volatility (섹터 기반 변동성 proxy)
        # High-volatility 섹터에 더 높은 점수
        HIGH_VOL_SECTORS = {
            'Technology', 'Cryptocurrency', 'Biotechnology',
            'Energy', 'Semiconductors', 'Cannabis',
        }
        LOW_VOL_SECTORS = {
            'Utilities', 'Consumer Staples', 'Healthcare',
            'Real Estate',
        }
        sectors = article.rule_sectors or []
        if any(s in HIGH_VOL_SECTORS for s in sectors):
            f8 = 0.8
        elif any(s in LOW_VOL_SECTORS for s in sectors):
            f8 = 0.3
        elif sectors:
            f8 = 0.5
        else:
            f8 = 0.5

        # f9: earnings_proximity (실적 발표 근접도 proxy)
        # 1분기(Jan-Mar), 2분기(Apr-Jun) 시작 시점에 높음
        month = article.published_at.month
        day = article.published_at.day
        # 실적 시즌: 1월, 4월, 7월, 10월 중순~말
        if month in (1, 4, 7, 10) and day >= 10:
            f9 = 0.9
        elif month in (1, 4, 7, 10):
            f9 = 0.7
        elif month in (2, 5, 8, 11) and day <= 10:
            f9 = 0.6
        else:
            f9 = 0.3

        # f10: topic_saturation (같은 키워드/종목 뉴스 포화도)
        # 같은 날 같은 rule_tickers를 가진 뉴스 수로 추정
        tickers = article.rule_tickers or []
        if tickers:
            same_day_count = NewsArticle.objects.filter(
                published_at__date=article.published_at.date(),
                rule_tickers__overlap=tickers,
            ).count()
            f10 = min(same_day_count / 20.0, 1.0)
        else:
            f10 = 0.0

        return base_features + [f6, f7, f8, f9, f10]

    # ════════════════════════════════════════
    # Phase 6: 확장 학습 데이터 (General News 포함)
    # ════════════════════════════════════════

    def prepare_extended_training_data(
        self,
        weeks: int = ROLLING_WINDOW_WEEKS,
        include_general: bool = True,
        min_confidence: float = 0.8,
    ) -> dict:
        """
        확장 학습 데이터 준비 (Phase 6)

        Company News + General News(confidence >= 0.8)

        Args:
            weeks: Rolling window 크기 (주)
            include_general: General News 포함 여부
            min_confidence: General News 최소 label confidence

        Returns:
            prepare_training_data와 동일 형식 (10 features)
        """
        cutoff = timezone.now() - timedelta(weeks=weeks)

        queryset = NewsArticle.objects.filter(
            ml_label_24h__isnull=False,
            ml_label_important__isnull=False,
            ml_label_confidence__isnull=False,
            importance_score__isnull=False,
            published_at__gte=cutoff,
        ).order_by('published_at')

        if include_general:
            # Company News (all) + General News (high confidence)
            from django.db.models import Q
            queryset = queryset.filter(
                Q(entities__isnull=False) |  # Company News
                Q(ml_label_confidence__gte=min_confidence)  # High-confidence General
            ).distinct()
        else:
            queryset = queryset.filter(
                entities__isnull=False,
            ).distinct()

        articles = list(queryset.select_related().prefetch_related('entities'))

        if len(articles) < MIN_TRAINING_SAMPLES:
            return {
                'X': None, 'y': None, 'weights': None,
                'n_samples': len(articles),
                'n_positive': 0, 'n_negative': 0,
                'date_range': None,
                'error': f'Insufficient data: {len(articles)} < {MIN_TRAINING_SAMPLES}',
            }

        X = []
        y = []
        weights = []

        for article in articles:
            features = self.extract_extended_features(article)
            X.append(features)
            y.append(1 if article.ml_label_important else 0)
            weights.append(article.ml_label_confidence)

        X = np.array(X, dtype=np.float64)
        y = np.array(y, dtype=np.int32)
        weights = np.array(weights, dtype=np.float64)

        return {
            'X': X,
            'y': y,
            'weights': weights,
            'n_samples': len(articles),
            'n_positive': int(np.sum(y == 1)),
            'n_negative': int(np.sum(y == 0)),
            'date_range': (
                articles[0].published_at.date(),
                articles[-1].published_at.date(),
            ),
        }

    # ════════════════════════════════════════
    # Phase 6: LightGBM 학습
    # ════════════════════════════════════════

    def train_lightgbm(self, X, y, weights) -> dict:
        """
        LightGBM Gradient Boosting 학습

        Returns:
            {
                'feature_importance': dict,
                'normalized_weights': dict,
                'cv_scores': list[dict],
                'final_metrics': dict,
            }
        """
        try:
            import lightgbm as lgb
        except ImportError:
            return {'error': 'lightgbm not installed'}

        from sklearn.metrics import (
            f1_score, precision_score, recall_score, accuracy_score,
        )

        feature_names = (
            EXTENDED_FEATURE_NAMES if X.shape[1] == 10
            else FEATURE_NAMES
        )

        splits = self.time_series_split(len(X))
        if not splits:
            return {'error': 'Not enough data for time-series split'}

        cv_scores = []

        for train_idx, test_idx in splits:
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            w_train = weights[train_idx]

            train_data = lgb.Dataset(
                X_train, label=y_train, weight=w_train,
                feature_name=feature_names,
            )

            params = {
                'objective': 'binary',
                'metric': 'binary_logloss',
                'is_unbalance': True,
                'num_leaves': 15,
                'learning_rate': 0.05,
                'n_estimators': 100,
                'max_depth': 4,
                'min_child_samples': 20,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42,
                'verbose': -1,
            }

            model = lgb.LGBMClassifier(**params)
            model.fit(
                X_train, y_train,
                sample_weight=w_train,
            )
            y_pred = model.predict(X_test)

            fold_metrics = {
                'f1': float(f1_score(y_test, y_pred, zero_division=0)),
                'precision': float(precision_score(y_test, y_pred, zero_division=0)),
                'recall': float(recall_score(y_test, y_pred, zero_division=0)),
                'accuracy': float(accuracy_score(y_test, y_pred)),
                'train_size': len(train_idx),
                'test_size': len(test_idx),
            }
            cv_scores.append(fold_metrics)

        # Final model: 전체 데이터로 학습
        final_model = lgb.LGBMClassifier(**params)
        final_model.fit(X, y, sample_weight=weights)

        # Feature importance
        importance_raw = final_model.feature_importances_
        total_imp = sum(importance_raw) or 1.0
        feature_importance = {
            name: round(float(imp) / total_imp, 4)
            for name, imp in zip(feature_names, importance_raw)
        }

        # Engine C 가중치용: 상위 5개 feature만 정규화
        base_importance = {
            k: v for k, v in feature_importance.items()
            if k in FEATURE_NAMES
        }
        base_total = sum(base_importance.values()) or 1.0
        normalized_weights = {
            k: round(v / base_total, 4) for k, v in base_importance.items()
        }

        avg_metrics = {
            'f1': round(np.mean([s['f1'] for s in cv_scores]), 4),
            'precision': round(np.mean([s['precision'] for s in cv_scores]), 4),
            'recall': round(np.mean([s['recall'] for s in cv_scores]), 4),
            'accuracy': round(np.mean([s['accuracy'] for s in cv_scores]), 4),
        }

        return {
            'feature_importance': feature_importance,
            'normalized_weights': normalized_weights,
            'cv_scores': cv_scores,
            'final_metrics': avg_metrics,
        }

    # ════════════════════════════════════════
    # Phase 6: A/B 테스트 (LR vs LightGBM)
    # ════════════════════════════════════════

    def ab_test(self, X, y, weights) -> dict:
        """
        LR vs LightGBM A/B 테스트

        동일 데이터에 대해 두 모델을 학습하고 성능 비교.

        Returns:
            {
                'lr_metrics': dict,
                'lgbm_metrics': dict,
                'winner': str,
                'f1_diff': float,
                'recommendation': str,
            }
        """
        lr_result = self.train_model(
            X[:, :5] if X.shape[1] > 5 else X,
            y, weights,
        )
        lgbm_result = self.train_lightgbm(X, y, weights)

        if lr_result.get('error'):
            return {
                'error': f'LR failed: {lr_result["error"]}',
                'lgbm_metrics': lgbm_result.get('final_metrics'),
            }
        if lgbm_result.get('error'):
            return {
                'lr_metrics': lr_result.get('final_metrics'),
                'error': f'LightGBM failed: {lgbm_result["error"]}',
            }

        lr_f1 = lr_result['final_metrics']['f1']
        lgbm_f1 = lgbm_result['final_metrics']['f1']
        f1_diff = lgbm_f1 - lr_f1

        if f1_diff > 0.02:
            winner = 'lightgbm'
            recommendation = (
                f'LightGBM outperforms LR by {f1_diff:.3f} F1. '
                'Consider deploying LightGBM.'
            )
        elif f1_diff < -0.02:
            winner = 'logistic_regression'
            recommendation = (
                f'LR outperforms LightGBM by {-f1_diff:.3f} F1. '
                'Keep using LR.'
            )
        else:
            winner = 'tie'
            recommendation = (
                f'Performance similar (diff={f1_diff:.3f}). '
                'LR preferred for interpretability.'
            )

        return {
            'lr_metrics': lr_result['final_metrics'],
            'lgbm_metrics': lgbm_result['final_metrics'],
            'winner': winner,
            'f1_diff': round(f1_diff, 4),
            'recommendation': recommendation,
            'lgbm_feature_importance': lgbm_result.get('feature_importance'),
        }

    # ════════════════════════════════════════
    # Phase 6: LightGBM 전환 조건 체크
    # ════════════════════════════════════════

    @staticmethod
    def check_lightgbm_readiness() -> dict:
        """
        LightGBM 전환 3가지 조건 체크

        1. 데이터 10,000건+
        2. LR 정확도 3주 연속 정체 (<1%p 개선)
        3. 확장 feature 수집 안정화

        Returns:
            dict: {ready, conditions}
        """
        # 조건 1: 데이터 수
        labeled_count = NewsArticle.objects.filter(
            ml_label_24h__isnull=False,
            ml_label_important__isnull=False,
        ).count()
        condition_data = labeled_count >= LIGHTGBM_MIN_SAMPLES

        # 조건 2: 정확도 정체
        recent_models = list(
            MLModelHistory.objects.filter(
                algorithm='logistic_regression',
                safety_gate_passed=True,
            ).order_by('-trained_at')[:LIGHTGBM_STAGNATION_WEEKS]
        )

        condition_stagnation = False
        if len(recent_models) >= LIGHTGBM_STAGNATION_WEEKS:
            f1_scores = [m.f1_score for m in recent_models]
            max_diff = max(f1_scores) - min(f1_scores)
            condition_stagnation = max_diff < LIGHTGBM_STAGNATION_THRESHOLD

        # 조건 3: 확장 feature 안정화 (rule_sectors가 있는 뉴스 비율)
        recent_total = NewsArticle.objects.filter(
            published_at__gte=timezone.now() - timedelta(weeks=2),
        ).count()
        recent_with_sectors = NewsArticle.objects.filter(
            published_at__gte=timezone.now() - timedelta(weeks=2),
            rule_sectors__isnull=False,
        ).count()
        sector_coverage = (
            recent_with_sectors / recent_total if recent_total > 0 else 0
        )
        condition_features = sector_coverage >= 0.5

        ready = condition_data and condition_stagnation and condition_features

        return {
            'ready': ready,
            'conditions': {
                'data_sufficient': {
                    'met': condition_data,
                    'current': labeled_count,
                    'required': LIGHTGBM_MIN_SAMPLES,
                },
                'lr_stagnation': {
                    'met': condition_stagnation,
                    'weeks_checked': len(recent_models),
                    'f1_range': (
                        round(max(f1_scores) - min(f1_scores), 4)
                        if len(recent_models) >= LIGHTGBM_STAGNATION_WEEKS
                        else None
                    ),
                },
                'feature_stability': {
                    'met': condition_features,
                    'sector_coverage': round(sector_coverage, 4),
                    'required': 0.5,
                },
            },
        }

    # ════════════════════════════════════════
    # Phase 6: LightGBM 학습 파이프라인
    # ════════════════════════════════════════

    def run_lightgbm_pipeline(self) -> dict:
        """
        LightGBM 학습 파이프라인 (Phase 6)

        1. 전환 조건 확인
        2. 확장 데이터 준비 (10 features, General News 포함)
        3. LightGBM 학습 + Time-Series CV
        4. A/B 테스트 (LR 대비)
        5. Safety Gate 검증
        6. MLModelHistory 저장

        Returns:
            dict: 학습 결과 요약
        """
        logger.info("LightGBM pipeline: Starting")

        # 1. 전환 조건 확인
        readiness = self.check_lightgbm_readiness()
        if not readiness['ready']:
            logger.info(f"LightGBM not ready: {readiness['conditions']}")
            return {
                'status': 'not_ready',
                'readiness': readiness,
            }

        # 2. 확장 데이터 준비
        data = self.prepare_extended_training_data(
            weeks=ROLLING_WINDOW_WEEKS,
            include_general=True,
            min_confidence=0.8,
        )

        if data.get('error') or data['X'] is None:
            error_msg = data.get('error', 'Unknown error')
            logger.warning(f"LightGBM data prep failed: {error_msg}")
            return {'status': 'failed', 'reason': error_msg}

        logger.info(
            f"LightGBM data: {data['n_samples']} samples "
            f"(+:{data['n_positive']}, -:{data['n_negative']})"
        )

        # 3. LightGBM 학습
        train_result = self.train_lightgbm(
            data['X'], data['y'], data['weights'],
        )

        if train_result.get('error'):
            return {'status': 'failed', 'reason': train_result['error']}

        metrics = train_result['final_metrics']

        # 4. A/B 테스트
        ab_result = self.ab_test(data['X'], data['y'], data['weights'])

        # 5. Safety Gate
        gate_result = self.safety_gate_check(metrics)

        # 6. Weight Smoothing
        new_weights = train_result['normalized_weights']
        prev_model = MLModelHistory.objects.filter(
            safety_gate_passed=True,
        ).order_by('-trained_at').first()
        prev_weights = prev_model.smoothed_weights if prev_model else None
        smoothed = self.smooth_weights(new_weights, prev_weights)

        # 7. 저장
        deployment_status = 'shadow' if gate_result['passed'] else 'failed'
        version = self._generate_version(algorithm='lgbm')

        history = MLModelHistory.objects.create(
            model_version=version,
            algorithm='lightgbm',
            training_samples=data['n_samples'],
            feature_count=data['X'].shape[1],
            f1_score=metrics['f1'],
            precision=metrics['precision'],
            recall=metrics['recall'],
            accuracy=metrics['accuracy'],
            weights=new_weights,
            smoothed_weights=smoothed,
            feature_importance=train_result.get('feature_importance'),
            training_config={
                'rolling_window_weeks': ROLLING_WINDOW_WEEKS,
                'include_general': True,
                'min_confidence': 0.8,
                'n_positive': data['n_positive'],
                'n_negative': data['n_negative'],
                'cv_scores': train_result['cv_scores'],
                'ab_test': {
                    'winner': ab_result.get('winner'),
                    'f1_diff': ab_result.get('f1_diff'),
                    'lr_f1': ab_result.get('lr_metrics', {}).get('f1'),
                    'lgbm_f1': ab_result.get('lgbm_metrics', {}).get('f1'),
                },
            },
            safety_gate_passed=gate_result['passed'],
            safety_gate_details=gate_result,
            deployment_status=deployment_status,
        )

        result = {
            'status': deployment_status,
            'model_version': version,
            'model_id': history.id,
            'algorithm': 'lightgbm',
            'metrics': metrics,
            'safety_gate': gate_result['passed'],
            'weights': smoothed,
            'feature_importance': train_result.get('feature_importance'),
            'ab_test': {
                'winner': ab_result.get('winner'),
                'recommendation': ab_result.get('recommendation'),
            },
            'training_samples': data['n_samples'],
        }

        logger.info(f"LightGBM pipeline complete: {result['status']}")
        return result

    # ════════════════════════════════════════
    # Helper
    # ════════════════════════════════════════

    @staticmethod
    def _generate_version(algorithm: str = 'lr') -> str:
        """모델 버전 생성 (예: lr_v1_20260225_1, lgbm_v2_20260225_1)"""
        today = timezone.now().strftime('%Y%m%d')
        count = MLModelHistory.objects.filter(
            trained_at__date=timezone.now().date(),
        ).count()
        prefix = 'lgbm_v2' if algorithm == 'lgbm' else 'lr_v1'
        return f"{prefix}_{today}_{count + 1}"
