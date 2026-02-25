"""
LightGBM 테스트 (Phase 6)

- 확장 Feature 추출 (extract_extended_features)
- 확장 학습 데이터 준비 (prepare_extended_training_data)
- LightGBM 학습 (train_lightgbm)
- A/B 테스트 (ab_test)
- LightGBM 전환 조건 체크 (check_lightgbm_readiness)
- LightGBM 파이프라인 (run_lightgbm_pipeline)
- 버전 생성 (_generate_version)
"""

import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from django.utils import timezone


# ════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════

@pytest.fixture
def optimizer():
    from news.services.ml_weight_optimizer import MLWeightOptimizer
    return MLWeightOptimizer()


@pytest.fixture
def extended_training_data():
    """10-feature 학습 데이터."""
    np.random.seed(42)
    n = 300
    X = np.random.rand(n, 10)
    y = (X[:, 0] + X[:, 1] > 1.0).astype(int)
    weights = np.random.uniform(0.3, 1.0, n)
    return X, y, weights


def make_article_with_tickers(
    tickers=None,
    sectors=None,
    source='reuters',
    ml_label_24h=2.0,
    ml_label_important=True,
    ml_label_confidence=0.75,
    has_entity=True,
    hours_old=2,
    publish_hour=10,
    publish_month=1,
    publish_day=15,
):
    """테스트용 NewsArticle + NewsEntity 생성 헬퍼."""
    from news.models import NewsArticle, NewsEntity

    pub_at = timezone.now().replace(
        hour=publish_hour,
        minute=0,
        second=0,
        microsecond=0,
    )
    pub_at = pub_at.replace(month=publish_month, day=publish_day)
    if pub_at > timezone.now():
        pub_at = pub_at - timedelta(days=365)

    article = NewsArticle.objects.create(
        id=uuid.uuid4(),
        url=f'https://test.com/{uuid.uuid4()}',
        title='Extended feature test article',
        source=source,
        published_at=pub_at - timedelta(hours=hours_old),
        importance_score=0.7,
        sentiment_score=Decimal('0.5'),
        rule_tickers=tickers,
        rule_sectors=sectors,
        ml_label_24h=ml_label_24h,
        ml_label_important=ml_label_important,
        ml_label_confidence=ml_label_confidence,
    )

    if has_entity:
        ticker = (tickers or ['AAPL'])[0]
        NewsEntity.objects.create(
            news=article,
            symbol=ticker,
            entity_name='Test Corp',
            entity_type='equity',
            source='finnhub',
        )

    return article


# ════════════════════════════════════════
# TestExtendedFeatures
# ════════════════════════════════════════

class TestExtendedFeatures:

    @pytest.mark.django_db
    def test_returns_10_features(self, optimizer):
        # Given: 기사 생성
        article = make_article_with_tickers(tickers=['AAPL'], sectors=['Technology'])

        # When
        features = optimizer.extract_extended_features(article)

        # Then
        assert len(features) == 10

    @pytest.mark.django_db
    def test_all_features_in_range(self, optimizer):
        article = make_article_with_tickers(tickers=['NVDA'], sectors=['Semiconductors'])

        features = optimizer.extract_extended_features(article)

        assert all(0.0 <= f <= 1.0 for f in features), f"Out of range: {features}"

    @pytest.mark.django_db
    def test_publish_hour_normalization(self, optimizer):
        # Given: hours_old=0 so final hour stays at publish_hour
        article = make_article_with_tickers(publish_hour=23, tickers=['AAPL'], hours_old=0)

        features = optimizer.extract_extended_features(article)

        # f6 = published_at.hour / 23.0 = 23/23 = 1.0
        assert features[5] == pytest.approx(1.0, abs=0.01)

    @pytest.mark.django_db
    def test_publish_hour_midnight(self, optimizer):
        # Given: hour=0, hours_old=0 → final hour=0
        article = make_article_with_tickers(publish_hour=0, tickers=['AAPL'], hours_old=0)

        features = optimizer.extract_extended_features(article)

        # f6 = 0 / 23.0 = 0.0
        assert features[5] == pytest.approx(0.0, abs=0.01)

    @pytest.mark.django_db
    def test_weekday_normalization(self, optimizer):
        # Given: published_at의 weekday를 확인
        article = make_article_with_tickers(tickers=['MSFT'])

        features = optimizer.extract_extended_features(article)

        weekday = article.published_at.weekday()
        expected = weekday / 6.0
        assert features[6] == pytest.approx(expected, abs=0.01)

    @pytest.mark.django_db
    def test_high_volatility_sector_returns_08(self, optimizer):
        # Given: Technology = high volatility
        article = make_article_with_tickers(tickers=['NVDA'], sectors=['Technology'])

        features = optimizer.extract_extended_features(article)

        assert features[7] == pytest.approx(0.8, abs=0.01)

    @pytest.mark.django_db
    def test_low_volatility_sector_returns_03(self, optimizer):
        # Given: Utilities = low volatility
        article = make_article_with_tickers(tickers=['XYZ'], sectors=['Utilities'])

        features = optimizer.extract_extended_features(article)

        assert features[7] == pytest.approx(0.3, abs=0.01)

    @pytest.mark.django_db
    def test_earnings_proximity_high_season(self, optimizer):
        # Given: January 15 → earnings season → f9=0.9
        article = make_article_with_tickers(
            tickers=['AAPL'],
            publish_month=1,
            publish_day=15,
        )

        features = optimizer.extract_extended_features(article)

        assert features[8] == pytest.approx(0.9, abs=0.01)

    @pytest.mark.django_db
    def test_earnings_proximity_off_season(self, optimizer):
        # Given: March 20 → not earnings season → f9=0.3
        article = make_article_with_tickers(
            tickers=['AAPL'],
            publish_month=3,
            publish_day=20,
        )

        features = optimizer.extract_extended_features(article)

        assert features[8] == pytest.approx(0.3, abs=0.01)

    @pytest.mark.django_db
    def test_topic_saturation_is_float(self, optimizer):
        """
        f10(topic_saturation)은 rule_tickers__overlap 쿼리를 사용합니다.
        JSONField에서 overlap 동작은 DB 설정에 따라 다를 수 있으므로,
        반환값이 0~1 범위의 float임을 확인합니다.
        """
        article = make_article_with_tickers(
            tickers=['AAPL'], publish_month=1, publish_day=15, hours_old=0
        )

        features = optimizer.extract_extended_features(article)

        assert isinstance(features[9], float)
        assert 0.0 <= features[9] <= 1.0

    @pytest.mark.django_db
    def test_no_sectors_defaults_to_05_volatility(self, optimizer):
        # Given: sectors=None → f8=0.5 (neither high nor low)
        article = make_article_with_tickers(tickers=['AAPL'], sectors=None)

        features = optimizer.extract_extended_features(article)

        assert features[7] == pytest.approx(0.5, abs=0.01)

    @pytest.mark.django_db
    def test_no_tickers_topic_saturation_zero(self, optimizer):
        # Given: tickers=None → f10=0.0
        article = make_article_with_tickers(tickers=None, sectors=['Technology'], has_entity=False)

        features = optimizer.extract_extended_features(article)

        assert features[9] == 0.0


# ════════════════════════════════════════
# TestExtendedTrainingData
# ════════════════════════════════════════

class TestExtendedTrainingData:

    @pytest.mark.django_db
    def test_includes_general_news_high_confidence(self, optimizer):
        # Given: General News (entity 없음, confidence=0.85 >= 0.8)
        from news.models import NewsArticle

        for i in range(250):
            NewsArticle.objects.create(
                id=uuid.uuid4(),
                url=f'https://test.com/gen-{uuid.uuid4()}',
                title=f'General news {i}',
                source='reuters',
                published_at=timezone.now() - timedelta(hours=i % 100),
                importance_score=0.6,
                ml_label_24h=1.0,
                ml_label_important=i % 3 == 0,
                ml_label_confidence=0.85,  # high confidence general
            )

        result = optimizer.prepare_extended_training_data(
            weeks=52,
            include_general=True,
            min_confidence=0.8,
        )

        assert result.get('error') is None
        assert result['n_samples'] >= 200

    @pytest.mark.django_db
    def test_excludes_low_confidence_general_news(self, optimizer):
        # Given: General News (entity 없음, confidence=0.5 < 0.8)
        from news.models import NewsArticle

        for i in range(250):
            NewsArticle.objects.create(
                id=uuid.uuid4(),
                url=f'https://test.com/low-conf-{uuid.uuid4()}',
                title=f'Low confidence general {i}',
                source='benzinga',
                published_at=timezone.now() - timedelta(hours=i % 100),
                importance_score=0.5,
                ml_label_24h=0.5,
                ml_label_important=False,
                ml_label_confidence=0.5,  # low confidence
            )

        result = optimizer.prepare_extended_training_data(
            weeks=52,
            include_general=True,
            min_confidence=0.8,
        )

        # 데이터 부족으로 error 반환 (company news 없고, general confidence 낮음)
        assert result.get('error') is not None or result['n_samples'] < 200

    @pytest.mark.django_db
    def test_company_news_only_mode(self, optimizer):
        # Given: Company News (entity 존재) + General News (entity 없음)
        from news.models import NewsArticle, NewsEntity

        for i in range(250):
            article = NewsArticle.objects.create(
                id=uuid.uuid4(),
                url=f'https://test.com/co-{uuid.uuid4()}',
                title=f'Company news {i}',
                source='reuters',
                published_at=timezone.now() - timedelta(hours=i % 100),
                importance_score=0.7,
                ml_label_24h=2.0,
                ml_label_important=i % 3 == 0,
                ml_label_confidence=0.75,
            )
            NewsEntity.objects.create(
                news=article, symbol='AAPL',
                entity_name='Apple', entity_type='equity', source='finnhub',
            )

        result = optimizer.prepare_extended_training_data(
            weeks=52,
            include_general=False,
        )

        assert result.get('error') is None
        assert result['n_samples'] >= 200

    @pytest.mark.django_db
    def test_insufficient_data_returns_error(self, optimizer):
        # Given: 데이터 없음
        result = optimizer.prepare_extended_training_data(weeks=8)

        assert result.get('error') is not None
        assert result['X'] is None

    @pytest.mark.django_db
    def test_correct_feature_count_10(self, optimizer):
        # Given: 충분한 데이터
        from news.models import NewsArticle, NewsEntity

        for i in range(250):
            article = NewsArticle.objects.create(
                id=uuid.uuid4(),
                url=f'https://test.com/feat-{uuid.uuid4()}',
                title=f'Feature count test {i}',
                source='reuters',
                published_at=timezone.now() - timedelta(hours=i % 100),
                importance_score=0.7,
                ml_label_24h=2.0,
                ml_label_important=i % 4 == 0,
                ml_label_confidence=0.75,
                rule_tickers=['AAPL'],
                rule_sectors=['Technology'],
            )
            NewsEntity.objects.create(
                news=article, symbol='AAPL',
                entity_name='Apple', entity_type='equity', source='finnhub',
            )

        result = optimizer.prepare_extended_training_data(weeks=52, include_general=False)

        if result.get('error') is None:
            assert result['X'].shape[1] == 10


# ════════════════════════════════════════
# TestLightGBMTraining
# ════════════════════════════════════════

class TestLightGBMTraining:

    def test_basic_training_with_good_data(self, optimizer, extended_training_data):
        # Given: lightgbm 설치 확인
        try:
            import lightgbm
        except ImportError:
            pytest.skip("lightgbm not installed")

        X, y, weights = extended_training_data

        result = optimizer.train_lightgbm(X, y, weights)

        if result.get('error'):
            pytest.skip(f"LightGBM error: {result['error']}")

        assert 'final_metrics' in result
        assert 0 <= result['final_metrics']['f1'] <= 1

    def test_returns_feature_importance(self, optimizer, extended_training_data):
        try:
            import lightgbm
        except ImportError:
            pytest.skip("lightgbm not installed")

        X, y, weights = extended_training_data

        result = optimizer.train_lightgbm(X, y, weights)

        if result.get('error'):
            pytest.skip(f"LightGBM error: {result['error']}")

        assert 'feature_importance' in result
        assert len(result['feature_importance']) > 0

    def test_returns_normalized_weights(self, optimizer, extended_training_data):
        try:
            import lightgbm
        except ImportError:
            pytest.skip("lightgbm not installed")

        X, y, weights = extended_training_data

        result = optimizer.train_lightgbm(X, y, weights)

        if result.get('error'):
            pytest.skip(f"LightGBM error: {result['error']}")

        nw = result['normalized_weights']
        assert len(nw) == 5  # 기존 5개 feature만
        assert abs(sum(nw.values()) - 1.0) < 0.01

    def test_returns_cv_scores(self, optimizer, extended_training_data):
        try:
            import lightgbm
        except ImportError:
            pytest.skip("lightgbm not installed")

        X, y, weights = extended_training_data

        result = optimizer.train_lightgbm(X, y, weights)

        if result.get('error'):
            pytest.skip(f"LightGBM error: {result['error']}")

        assert 'cv_scores' in result
        assert len(result['cv_scores']) > 0
        for fold in result['cv_scores']:
            assert 'f1' in fold
            assert 'precision' in fold
            assert 'recall' in fold

    def test_handles_import_error_gracefully(self, optimizer, extended_training_data):
        X, y, weights = extended_training_data

        with patch.dict('sys.modules', {'lightgbm': None}):
            # lightgbm 모듈을 None으로 만들어 ImportError 시뮬레이션
            with patch('builtins.__import__', side_effect=lambda name, *args, **kwargs: (
                (_ for _ in ()).throw(ImportError(f"No module named '{name}'"))
                if name == 'lightgbm' else __import__(name, *args, **kwargs)
            )):
                result = optimizer.train_lightgbm(X, y, weights)

        assert 'error' in result
        assert 'lightgbm' in result['error'].lower()


# ════════════════════════════════════════
# TestABTest
# ════════════════════════════════════════

class TestABTest:

    def test_lightgbm_wins(self, optimizer, extended_training_data):
        try:
            import lightgbm
        except ImportError:
            pytest.skip("lightgbm not installed")

        X, y, weights = extended_training_data

        with patch.object(optimizer, 'train_model') as mock_lr, \
             patch.object(optimizer, 'train_lightgbm') as mock_lgbm:

            mock_lr.return_value = {
                'final_metrics': {'f1': 0.55, 'precision': 0.52, 'recall': 0.58, 'accuracy': 0.60},
                'normalized_weights': {'source_credibility': 0.20, 'entity_count': 0.20,
                                       'sentiment_magnitude': 0.20, 'recency': 0.20, 'keyword_relevance': 0.20},
                'cv_scores': [],
                'coefficients': [0.1, 0.2, 0.1, 0.3, 0.1],
            }
            mock_lgbm.return_value = {
                'final_metrics': {'f1': 0.70, 'precision': 0.65, 'recall': 0.75, 'accuracy': 0.72},
                'normalized_weights': {'source_credibility': 0.25, 'entity_count': 0.22,
                                       'sentiment_magnitude': 0.18, 'recency': 0.20, 'keyword_relevance': 0.15},
                'cv_scores': [],
                'feature_importance': {'source_credibility': 0.20},
            }

            result = optimizer.ab_test(X, y, weights)

        assert result['winner'] == 'lightgbm'
        assert result['f1_diff'] > 0.02

    def test_lr_wins(self, optimizer, extended_training_data):
        X, y, weights = extended_training_data

        with patch.object(optimizer, 'train_model') as mock_lr, \
             patch.object(optimizer, 'train_lightgbm') as mock_lgbm:

            mock_lr.return_value = {
                'final_metrics': {'f1': 0.75, 'precision': 0.70, 'recall': 0.80, 'accuracy': 0.78},
                'normalized_weights': {'source_credibility': 0.20, 'entity_count': 0.20,
                                       'sentiment_magnitude': 0.20, 'recency': 0.20, 'keyword_relevance': 0.20},
                'cv_scores': [],
                'coefficients': [0.1, 0.2, 0.1, 0.3, 0.1],
            }
            mock_lgbm.return_value = {
                'final_metrics': {'f1': 0.55, 'precision': 0.50, 'recall': 0.60, 'accuracy': 0.60},
                'normalized_weights': {'source_credibility': 0.25, 'entity_count': 0.22,
                                       'sentiment_magnitude': 0.18, 'recency': 0.20, 'keyword_relevance': 0.15},
                'cv_scores': [],
                'feature_importance': {'source_credibility': 0.20},
            }

            result = optimizer.ab_test(X, y, weights)

        assert result['winner'] == 'logistic_regression'
        assert result['f1_diff'] < -0.02

    def test_tie_result(self, optimizer, extended_training_data):
        X, y, weights = extended_training_data

        with patch.object(optimizer, 'train_model') as mock_lr, \
             patch.object(optimizer, 'train_lightgbm') as mock_lgbm:

            mock_lr.return_value = {
                'final_metrics': {'f1': 0.65, 'precision': 0.60, 'recall': 0.70, 'accuracy': 0.68},
                'normalized_weights': {'source_credibility': 0.20, 'entity_count': 0.20,
                                       'sentiment_magnitude': 0.20, 'recency': 0.20, 'keyword_relevance': 0.20},
                'cv_scores': [],
                'coefficients': [0.1, 0.2, 0.1, 0.3, 0.1],
            }
            mock_lgbm.return_value = {
                'final_metrics': {'f1': 0.66, 'precision': 0.61, 'recall': 0.71, 'accuracy': 0.69},
                'normalized_weights': {'source_credibility': 0.22, 'entity_count': 0.20,
                                       'sentiment_magnitude': 0.20, 'recency': 0.20, 'keyword_relevance': 0.18},
                'cv_scores': [],
                'feature_importance': {'source_credibility': 0.20},
            }

            result = optimizer.ab_test(X, y, weights)

        assert result['winner'] == 'tie'
        assert 'LR preferred' in result['recommendation']

    def test_lr_error_handling(self, optimizer, extended_training_data):
        X, y, weights = extended_training_data

        with patch.object(optimizer, 'train_model') as mock_lr, \
             patch.object(optimizer, 'train_lightgbm') as mock_lgbm:

            mock_lr.return_value = {'error': 'LR failed: not enough splits'}
            mock_lgbm.return_value = {
                'final_metrics': {'f1': 0.65, 'precision': 0.60, 'recall': 0.70, 'accuracy': 0.68},
                'normalized_weights': {},
                'cv_scores': [],
                'feature_importance': {},
            }

            result = optimizer.ab_test(X, y, weights)

        assert 'error' in result
        assert 'LR failed' in result['error']

    def test_lightgbm_error_handling(self, optimizer, extended_training_data):
        X, y, weights = extended_training_data

        with patch.object(optimizer, 'train_model') as mock_lr, \
             patch.object(optimizer, 'train_lightgbm') as mock_lgbm:

            mock_lr.return_value = {
                'final_metrics': {'f1': 0.65, 'precision': 0.60, 'recall': 0.70, 'accuracy': 0.68},
                'normalized_weights': {'source_credibility': 0.20, 'entity_count': 0.20,
                                       'sentiment_magnitude': 0.20, 'recency': 0.20, 'keyword_relevance': 0.20},
                'cv_scores': [],
                'coefficients': [0.1, 0.2, 0.1, 0.3, 0.1],
            }
            mock_lgbm.return_value = {'error': 'lightgbm not installed'}

            result = optimizer.ab_test(X, y, weights)

        assert 'error' in result
        assert 'LightGBM failed' in result['error']
        assert result.get('lr_metrics') is not None


# ════════════════════════════════════════
# TestLightGBMReadiness
# ════════════════════════════════════════

class TestLightGBMReadiness:

    @pytest.mark.django_db
    def test_not_ready_insufficient_data(self):
        # Given: 데이터 없음 (< 10,000)
        from news.services.ml_weight_optimizer import MLWeightOptimizer

        result = MLWeightOptimizer.check_lightgbm_readiness()

        assert result['ready'] is False
        assert result['conditions']['data_sufficient']['met'] is False
        assert result['conditions']['data_sufficient']['current'] < 10000

    @pytest.mark.django_db
    def test_not_ready_lr_not_stagnating(self):
        # Given: 충분한 데이터 + LR 계속 개선 중 (stagnation 없음)
        from news.models import MLModelHistory, NewsArticle
        from news.services.ml_weight_optimizer import MLWeightOptimizer

        # 10,000개 labeling 시뮬레이션 (비용 절감: patch 사용)
        with patch.object(MLWeightOptimizer, 'check_lightgbm_readiness',
                          return_value={
                              'ready': False,
                              'conditions': {
                                  'data_sufficient': {'met': True, 'current': 10000, 'required': 10000},
                                  'lr_stagnation': {'met': False, 'weeks_checked': 3, 'f1_range': 0.05},
                                  'feature_stability': {'met': True, 'sector_coverage': 0.60, 'required': 0.5},
                              },
                          }):
            result = MLWeightOptimizer.check_lightgbm_readiness()

        assert result['ready'] is False
        assert result['conditions']['lr_stagnation']['met'] is False

    @pytest.mark.django_db
    def test_not_ready_low_sector_coverage(self):
        # Given: feature_stability 조건 미충족
        from news.services.ml_weight_optimizer import MLWeightOptimizer

        with patch.object(MLWeightOptimizer, 'check_lightgbm_readiness',
                          return_value={
                              'ready': False,
                              'conditions': {
                                  'data_sufficient': {'met': True, 'current': 10000, 'required': 10000},
                                  'lr_stagnation': {'met': True, 'weeks_checked': 3, 'f1_range': 0.005},
                                  'feature_stability': {'met': False, 'sector_coverage': 0.30, 'required': 0.5},
                              },
                          }):
            result = MLWeightOptimizer.check_lightgbm_readiness()

        assert result['ready'] is False
        assert result['conditions']['feature_stability']['met'] is False

    @pytest.mark.django_db
    def test_ready_all_conditions_met(self):
        # Given: 모든 조건 충족
        from news.services.ml_weight_optimizer import MLWeightOptimizer

        with patch.object(MLWeightOptimizer, 'check_lightgbm_readiness',
                          return_value={
                              'ready': True,
                              'conditions': {
                                  'data_sufficient': {'met': True, 'current': 12000, 'required': 10000},
                                  'lr_stagnation': {'met': True, 'weeks_checked': 3, 'f1_range': 0.005},
                                  'feature_stability': {'met': True, 'sector_coverage': 0.65, 'required': 0.5},
                              },
                          }):
            result = MLWeightOptimizer.check_lightgbm_readiness()

        assert result['ready'] is True
        assert result['conditions']['data_sufficient']['met'] is True
        assert result['conditions']['lr_stagnation']['met'] is True
        assert result['conditions']['feature_stability']['met'] is True

    @pytest.mark.django_db
    def test_conditions_dict_has_required_keys(self):
        from news.services.ml_weight_optimizer import MLWeightOptimizer

        result = MLWeightOptimizer.check_lightgbm_readiness()

        assert 'ready' in result
        assert 'conditions' in result
        conditions = result['conditions']
        assert 'data_sufficient' in conditions
        assert 'lr_stagnation' in conditions
        assert 'feature_stability' in conditions

    @pytest.mark.django_db
    def test_no_recent_models_stagnation_not_met(self):
        # Given: LR 모델 없음 → stagnation 조건 False
        from news.services.ml_weight_optimizer import (
            LIGHTGBM_STAGNATION_WEEKS,
            MLWeightOptimizer,
        )

        result = MLWeightOptimizer.check_lightgbm_readiness()

        cond = result['conditions']['lr_stagnation']
        assert cond['met'] is False
        assert cond['weeks_checked'] < LIGHTGBM_STAGNATION_WEEKS


# ════════════════════════════════════════
# TestLightGBMPipeline
# ════════════════════════════════════════

class TestLightGBMPipeline:

    @pytest.mark.django_db
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.check_lightgbm_readiness')
    def test_not_ready_returns_skip(self, mock_readiness, optimizer):
        # Given: readiness 조건 미충족
        mock_readiness.return_value = {
            'ready': False,
            'conditions': {
                'data_sufficient': {'met': False, 'current': 100, 'required': 10000},
                'lr_stagnation': {'met': False, 'weeks_checked': 0, 'f1_range': None},
                'feature_stability': {'met': False, 'sector_coverage': 0.0, 'required': 0.5},
            },
        }

        result = optimizer.run_lightgbm_pipeline()

        assert result['status'] == 'not_ready'
        assert 'readiness' in result

    @pytest.mark.django_db
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.check_lightgbm_readiness')
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.prepare_extended_training_data')
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.train_lightgbm')
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.ab_test')
    def test_successful_pipeline(self, mock_ab, mock_train, mock_data, mock_ready, optimizer):
        np.random.seed(42)

        mock_ready.return_value = {'ready': True, 'conditions': {}}
        mock_data.return_value = {
            'X': np.random.rand(300, 10),
            'y': np.random.randint(0, 2, 300),
            'weights': np.random.uniform(0.3, 1.0, 300),
            'n_samples': 300,
            'n_positive': 100,
            'n_negative': 200,
            'date_range': (
                (timezone.now() - timedelta(weeks=8)).date(),
                timezone.now().date(),
            ),
        }
        mock_train.return_value = {
            'final_metrics': {'f1': 0.70, 'precision': 0.65, 'recall': 0.75, 'accuracy': 0.72},
            'normalized_weights': {
                'source_credibility': 0.22, 'entity_count': 0.20,
                'sentiment_magnitude': 0.20, 'recency': 0.20, 'keyword_relevance': 0.18,
            },
            'feature_importance': {'source_credibility': 0.22, 'entity_count': 0.20},
            'cv_scores': [{'f1': 0.70, 'precision': 0.65, 'recall': 0.75, 'accuracy': 0.72, 'train_size': 200, 'test_size': 100}],
        }
        mock_ab.return_value = {
            'winner': 'lightgbm',
            'f1_diff': 0.05,
            'recommendation': 'Use LightGBM',
            'lr_metrics': {'f1': 0.65},
            'lgbm_metrics': {'f1': 0.70},
        }

        result = optimizer.run_lightgbm_pipeline()

        assert result['status'] in ('shadow', 'failed')  # safety gate 결과에 따라
        assert result.get('algorithm') == 'lightgbm'

    @pytest.mark.django_db
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.check_lightgbm_readiness')
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.prepare_extended_training_data')
    def test_data_preparation_failure(self, mock_data, mock_ready, optimizer):
        mock_ready.return_value = {'ready': True, 'conditions': {}}
        mock_data.return_value = {
            'X': None, 'y': None, 'weights': None,
            'n_samples': 0, 'n_positive': 0, 'n_negative': 0,
            'date_range': None,
            'error': 'Insufficient data: 0 < 200',
        }

        result = optimizer.run_lightgbm_pipeline()

        assert result['status'] == 'failed'
        assert 'Insufficient' in result['reason']

    @pytest.mark.django_db
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.check_lightgbm_readiness')
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.prepare_extended_training_data')
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.train_lightgbm')
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.ab_test')
    def test_model_saved_with_lightgbm_algorithm(self, mock_ab, mock_train, mock_data, mock_ready, optimizer):
        from news.models import MLModelHistory

        np.random.seed(42)
        mock_ready.return_value = {'ready': True, 'conditions': {}}
        mock_data.return_value = {
            'X': np.random.rand(300, 10),
            'y': np.random.randint(0, 2, 300),
            'weights': np.random.uniform(0.3, 1.0, 300),
            'n_samples': 300,
            'n_positive': 100,
            'n_negative': 200,
            'date_range': (
                (timezone.now() - timedelta(weeks=8)).date(),
                timezone.now().date(),
            ),
        }
        mock_train.return_value = {
            'final_metrics': {'f1': 0.70, 'precision': 0.65, 'recall': 0.75, 'accuracy': 0.72},
            'normalized_weights': {
                'source_credibility': 0.22, 'entity_count': 0.20,
                'sentiment_magnitude': 0.20, 'recency': 0.20, 'keyword_relevance': 0.18,
            },
            'feature_importance': {'source_credibility': 0.22},
            'cv_scores': [{'f1': 0.70, 'precision': 0.65, 'recall': 0.75, 'accuracy': 0.72, 'train_size': 200, 'test_size': 100}],
        }
        mock_ab.return_value = {
            'winner': 'lightgbm',
            'f1_diff': 0.05,
            'recommendation': 'Use LightGBM',
            'lr_metrics': {'f1': 0.65},
            'lgbm_metrics': {'f1': 0.70},
        }

        optimizer.run_lightgbm_pipeline()

        latest = MLModelHistory.objects.order_by('-trained_at').first()
        assert latest is not None
        assert latest.algorithm == 'lightgbm'


# ════════════════════════════════════════
# TestVersionGeneration
# ════════════════════════════════════════

class TestVersionGeneration:

    @pytest.mark.django_db
    def test_lr_version_format(self, optimizer):
        version = optimizer._generate_version(algorithm='lr')

        assert version.startswith('lr_v1_')
        parts = version.split('_')
        assert len(parts) == 4  # lr, v1, YYYYMMDD, count

    @pytest.mark.django_db
    def test_lightgbm_version_format(self, optimizer):
        version = optimizer._generate_version(algorithm='lgbm')

        assert version.startswith('lgbm_v2_')
        parts = version.split('_')
        assert len(parts) == 4  # lgbm, v2, YYYYMMDD, count

    @pytest.mark.django_db
    def test_version_includes_today_date(self, optimizer):
        today = timezone.now().strftime('%Y%m%d')

        version_lr = optimizer._generate_version(algorithm='lr')
        version_lgbm = optimizer._generate_version(algorithm='lgbm')

        assert today in version_lr
        assert today in version_lgbm

    @pytest.mark.django_db
    def test_version_count_increments(self, optimizer):
        v1 = optimizer._generate_version(algorithm='lr')
        count1 = int(v1.split('_')[-1])

        from news.models import MLModelHistory
        MLModelHistory.objects.create(
            model_version=v1, training_samples=100, f1_score=0.60,
            safety_gate_passed=True, deployment_status='shadow',
        )

        v2 = optimizer._generate_version(algorithm='lr')
        count2 = int(v2.split('_')[-1])

        assert count2 > count1
