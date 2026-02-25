"""
ML Weight Optimizer 테스트 (Phase 4)

- Feature 추출
- 학습 데이터 준비
- Time-Series Split
- 모델 학습
- Safety Gate
- Weight Smoothing
- Shadow Mode 비교
- 학습 파이프라인
- 모델 배포
- 상태 조회
- Celery 태스크
- API 엔드포인트
"""

import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from django.test import RequestFactory
from django.utils import timezone


# ════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════

@pytest.fixture
def optimizer():
    from news.services.ml_weight_optimizer import MLWeightOptimizer
    return MLWeightOptimizer()


@pytest.fixture
def sample_article():
    """ML Label이 있는 뉴스 기사 mock"""
    article = MagicMock()
    article.id = uuid.uuid4()
    article.source = 'reuters'
    article.sentiment_score = Decimal('0.5')
    article.published_at = timezone.now().replace(hour=10)  # 시장 시간
    article.rule_tickers = ['NVDA', 'AMD']
    article.rule_sectors = ['Technology']
    article.importance_score = 0.85
    article.ml_label_24h = 3.5
    article.ml_label_important = True
    article.ml_label_confidence = 0.8
    return article


@pytest.fixture
def sample_article_negative():
    """ml_label_important=False인 뉴스"""
    article = MagicMock()
    article.id = uuid.uuid4()
    article.source = 'seeking alpha'
    article.sentiment_score = Decimal('0.1')
    article.published_at = timezone.now().replace(hour=22)  # 야간
    article.rule_tickers = ['GE']
    article.rule_sectors = []
    article.importance_score = 0.35
    article.ml_label_24h = 0.3
    article.ml_label_important = False
    article.ml_label_confidence = 0.6
    return article


@pytest.fixture
def training_data():
    """학습용 X, y, weights 데이터"""
    np.random.seed(42)
    n = 300
    X = np.random.rand(n, 5)
    y = (X[:, 0] + X[:, 1] > 1.0).astype(int)  # f1+f2 > 1 → important
    weights = np.random.uniform(0.3, 1.0, n)
    return X, y, weights


@pytest.fixture
def request_factory():
    return RequestFactory()


# ════════════════════════════════════════
# Feature 추출 테스트
# ════════════════════════════════════════

class TestFeatureExtraction:

    def test_extract_features_basic(self, optimizer, sample_article):
        features = optimizer.extract_features(sample_article)
        assert len(features) == 5
        assert all(0 <= f <= 1 for f in features)

    def test_source_credibility_reuters(self, optimizer, sample_article):
        features = optimizer.extract_features(sample_article)
        assert features[0] == 1.0  # reuters = 1.0

    def test_source_credibility_unknown(self, optimizer, sample_article):
        sample_article.source = 'unknown_blog'
        features = optimizer.extract_features(sample_article)
        assert features[0] == 0.5  # default

    def test_entity_count_normalized(self, optimizer, sample_article):
        features = optimizer.extract_features(sample_article)
        # 2 tickers + 1 sector = 3 entities -> 3/5 = 0.6
        assert features[1] == 0.6

    def test_entity_count_capped(self, optimizer, sample_article):
        sample_article.rule_tickers = ['A', 'B', 'C', 'D', 'E']
        sample_article.rule_sectors = ['Tech']
        features = optimizer.extract_features(sample_article)
        assert features[1] == 1.0  # 6/5 capped to 1.0

    def test_sentiment_magnitude(self, optimizer, sample_article):
        features = optimizer.extract_features(sample_article)
        assert features[2] == 0.5  # |0.5| = 0.5

    def test_sentiment_none_default(self, optimizer, sample_article):
        sample_article.sentiment_score = None
        features = optimizer.extract_features(sample_article)
        assert features[2] == 0.3  # default

    def test_recency_market_hours(self, optimizer, sample_article):
        sample_article.published_at = timezone.now().replace(hour=10)
        features = optimizer.extract_features(sample_article)
        assert features[3] == 1.0

    def test_recency_off_hours(self, optimizer, sample_article):
        sample_article.published_at = timezone.now().replace(hour=22)
        features = optimizer.extract_features(sample_article)
        assert features[3] == 0.4

    def test_keyword_relevance(self, optimizer, sample_article):
        features = optimizer.extract_features(sample_article)
        # 1 sector -> 1/3 ≈ 0.333
        assert abs(features[4] - 1 / 3) < 0.01

    def test_keyword_relevance_none(self, optimizer, sample_article):
        sample_article.rule_sectors = None
        features = optimizer.extract_features(sample_article)
        assert features[4] == 0.0

    def test_empty_tickers(self, optimizer, sample_article):
        sample_article.rule_tickers = None
        sample_article.rule_sectors = None
        features = optimizer.extract_features(sample_article)
        assert features[1] == 0.0
        assert features[4] == 0.0


# ════════════════════════════════════════
# Time-Series Split 테스트
# ════════════════════════════════════════

class TestTimeSeriesSplit:

    def test_basic_split(self, optimizer):
        splits = optimizer.time_series_split(300, n_splits=3)
        assert len(splits) > 0

    def test_split_ordering(self, optimizer):
        splits = optimizer.time_series_split(300, n_splits=3)
        for train_idx, test_idx in splits:
            # Train은 test보다 항상 앞에
            assert train_idx[-1] < test_idx[0]

    def test_split_no_overlap(self, optimizer):
        splits = optimizer.time_series_split(300, n_splits=3)
        for train_idx, test_idx in splits:
            assert len(set(train_idx) & set(test_idx)) == 0

    def test_small_data(self, optimizer):
        splits = optimizer.time_series_split(10, n_splits=3)
        # 작은 데이터에서도 동작
        assert isinstance(splits, list)

    def test_progressive_train_size(self, optimizer):
        splits = optimizer.time_series_split(400, n_splits=3)
        if len(splits) > 1:
            # 첫 번째보다 두 번째 train set이 더 큼
            assert len(splits[1][0]) > len(splits[0][0])


# ════════════════════════════════════════
# 모델 학습 테스트
# ════════════════════════════════════════

class TestModelTraining:

    def test_train_returns_coefficients(self, optimizer, training_data):
        X, y, w = training_data
        result = optimizer.train_model(X, y, w)
        assert 'coefficients' in result
        assert len(result['coefficients']) == 5

    def test_train_returns_normalized_weights(self, optimizer, training_data):
        X, y, w = training_data
        result = optimizer.train_model(X, y, w)
        weights = result['normalized_weights']
        assert len(weights) == 5
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_train_returns_cv_scores(self, optimizer, training_data):
        X, y, w = training_data
        result = optimizer.train_model(X, y, w)
        assert 'cv_scores' in result
        assert len(result['cv_scores']) > 0

    def test_cv_scores_have_metrics(self, optimizer, training_data):
        X, y, w = training_data
        result = optimizer.train_model(X, y, w)
        for fold in result['cv_scores']:
            assert 'f1' in fold
            assert 'precision' in fold
            assert 'recall' in fold
            assert 'accuracy' in fold

    def test_final_metrics(self, optimizer, training_data):
        X, y, w = training_data
        result = optimizer.train_model(X, y, w)
        metrics = result['final_metrics']
        assert 0 <= metrics['f1'] <= 1
        assert 0 <= metrics['precision'] <= 1
        assert 0 <= metrics['recall'] <= 1
        assert 0 <= metrics['accuracy'] <= 1

    def test_train_small_data_poor_metrics(self, optimizer):
        """데이터 너무 작으면 메트릭이 낮음"""
        X = np.random.rand(5, 5)
        y = np.array([0, 1, 0, 1, 0])
        w = np.ones(5)
        result = optimizer.train_model(X, y, w)
        # 작은 데이터로도 학습은 되지만 메트릭이 매우 낮음
        assert result['final_metrics']['f1'] <= 0.5


# ════════════════════════════════════════
# Safety Gate 테스트
# ════════════════════════════════════════

class TestSafetyGate:

    @pytest.mark.django_db
    def test_all_pass(self, optimizer):
        metrics = {'f1': 0.70, 'precision': 0.65, 'recall': 0.75}
        result = optimizer.safety_gate_check(metrics)
        assert result['passed'] is True
        assert result['tier1']['passed'] is True
        assert result['tier2']['passed'] is True
        assert result['tier3']['passed'] is True

    @pytest.mark.django_db
    def test_tier1_fail_low_f1(self, optimizer):
        metrics = {'f1': 0.40, 'precision': 0.65, 'recall': 0.50}
        result = optimizer.safety_gate_check(metrics)
        assert result['passed'] is False
        assert result['tier1']['passed'] is False

    @pytest.mark.django_db
    def test_tier2_fail_low_precision(self, optimizer):
        metrics = {'f1': 0.60, 'precision': 0.40, 'recall': 0.80}
        result = optimizer.safety_gate_check(metrics)
        assert result['passed'] is False
        assert result['tier2']['passed'] is False

    @pytest.mark.django_db
    def test_tier3_no_previous_model(self, optimizer):
        """이전 모델 없으면 tier3 자동 통과"""
        metrics = {'f1': 0.60, 'precision': 0.55, 'recall': 0.65}
        result = optimizer.safety_gate_check(metrics)
        assert result['tier3']['passed'] is True

    @pytest.mark.django_db
    def test_tier3_degradation_check(self, optimizer):
        """이전 모델 대비 하락 체크"""
        from news.models import MLModelHistory
        MLModelHistory.objects.create(
            model_version='prev_test',
            training_samples=100,
            f1_score=0.80,
            safety_gate_passed=True,
            deployment_status='shadow',
        )

        # 0.80 → 0.60 = 0.20 하락 > 0.10 threshold
        metrics = {'f1': 0.60, 'precision': 0.55, 'recall': 0.65}
        result = optimizer.safety_gate_check(metrics)
        assert result['tier3']['passed'] is False

    @pytest.mark.django_db
    def test_tier3_acceptable_degradation(self, optimizer):
        """허용 범위 내 하락은 통과"""
        from news.models import MLModelHistory
        MLModelHistory.objects.create(
            model_version='prev_test2',
            training_samples=100,
            f1_score=0.65,
            safety_gate_passed=True,
            deployment_status='shadow',
        )

        # 0.65 → 0.60 = 0.05 하락 <= 0.10 threshold
        metrics = {'f1': 0.60, 'precision': 0.55, 'recall': 0.65}
        result = optimizer.safety_gate_check(metrics)
        assert result['tier3']['passed'] is True


# ════════════════════════════════════════
# Weight Smoothing 테스트
# ════════════════════════════════════════

class TestWeightSmoothing:

    def test_no_previous_weights(self, optimizer):
        new = {
            'source_credibility': 0.20,
            'entity_count': 0.25,
            'sentiment_magnitude': 0.20,
            'recency': 0.15,
            'keyword_relevance': 0.20,
        }
        smoothed = optimizer.smooth_weights(new, None)
        assert smoothed == new

    def test_smoothing_formula(self, optimizer):
        new = {
            'source_credibility': 0.30,
            'entity_count': 0.20,
            'sentiment_magnitude': 0.20,
            'recency': 0.15,
            'keyword_relevance': 0.15,
        }
        prev = {
            'source_credibility': 0.10,
            'entity_count': 0.30,
            'sentiment_magnitude': 0.20,
            'recency': 0.25,
            'keyword_relevance': 0.15,
        }
        smoothed = optimizer.smooth_weights(new, prev)
        # 0.7 * 0.30 + 0.3 * 0.10 = 0.24 (before normalization)
        assert 'source_credibility' in smoothed
        total = sum(smoothed.values())
        assert abs(total - 1.0) < 0.01

    def test_smoothing_normalized(self, optimizer):
        """Smoothing 결과가 합 1.0으로 정규화"""
        new = {
            'source_credibility': 0.40,
            'entity_count': 0.10,
            'sentiment_magnitude': 0.10,
            'recency': 0.30,
            'keyword_relevance': 0.10,
        }
        prev = {
            'source_credibility': 0.10,
            'entity_count': 0.40,
            'sentiment_magnitude': 0.10,
            'recency': 0.10,
            'keyword_relevance': 0.30,
        }
        smoothed = optimizer.smooth_weights(new, prev)
        assert abs(sum(smoothed.values()) - 1.0) < 0.01


# ════════════════════════════════════════
# Shadow Mode 비교 테스트
# ════════════════════════════════════════

class TestShadowComparison:

    @pytest.mark.django_db
    def test_empty_articles(self, optimizer):
        ml_weights = {
            'source_credibility': 0.20,
            'entity_count': 0.25,
            'sentiment_magnitude': 0.20,
            'recency': 0.15,
            'keyword_relevance': 0.20,
        }
        result = optimizer.generate_shadow_comparison(ml_weights, days=7)
        assert result['total_articles'] == 0
        assert result['agreement_rate'] == 0.0

    @pytest.mark.django_db
    def test_with_articles(self, optimizer):
        """뉴스가 있을 때 비교 리포트 생성"""
        from news.models import NewsArticle

        # 테스트 뉴스 생성
        for i in range(20):
            NewsArticle.objects.create(
                url=f'https://test.com/article-shadow-{i}',
                title=f'Test article {i}',
                source='reuters' if i % 3 == 0 else 'benzinga',
                published_at=timezone.now() - timedelta(hours=i),
                importance_score=0.5 + (i % 10) * 0.05,
                sentiment_score=Decimal(str(0.1 * (i % 5 - 2))),
            )

        ml_weights = {
            'source_credibility': 0.30,
            'entity_count': 0.10,
            'sentiment_magnitude': 0.20,
            'recency': 0.25,
            'keyword_relevance': 0.15,
        }
        result = optimizer.generate_shadow_comparison(ml_weights, days=7)
        assert result['total_articles'] == 20
        assert result['manual_selected'] > 0
        assert result['ml_selected'] > 0
        assert 0 <= result['agreement_rate'] <= 1

    @pytest.mark.django_db
    def test_comparison_fields(self, optimizer):
        """비교 리포트 필수 필드"""
        ml_weights = {
            'source_credibility': 0.20,
            'entity_count': 0.20,
            'sentiment_magnitude': 0.20,
            'recency': 0.20,
            'keyword_relevance': 0.20,
        }
        result = optimizer.generate_shadow_comparison(ml_weights)
        assert 'period' in result
        assert 'total_articles' in result
        assert 'manual_selected' in result
        assert 'ml_selected' in result
        assert 'overlap' in result
        assert 'agreement_rate' in result


# ════════════════════════════════════════
# 학습 데이터 준비 테스트
# ════════════════════════════════════════

class TestPrepareTrainingData:

    @pytest.mark.django_db
    def test_insufficient_data(self, optimizer):
        """데이터 부족 시 error 반환"""
        result = optimizer.prepare_training_data(weeks=8)
        assert result.get('error') is not None
        assert result['X'] is None

    @pytest.mark.django_db
    def test_with_sufficient_data(self, optimizer):
        """충분한 데이터가 있을 때 정상 반환"""
        from news.models import NewsArticle, NewsEntity

        # 300개 뉴스 + entity 생성
        for i in range(250):
            article = NewsArticle.objects.create(
                url=f'https://test.com/train-{i}',
                title=f'Training article {i}',
                source='reuters',
                published_at=timezone.now() - timedelta(days=i % 50, hours=10),
                importance_score=0.5 + (i % 10) * 0.05,
                sentiment_score=Decimal(str(0.1 * (i % 5 - 2))),
                rule_tickers=['AAPL'] if i % 2 == 0 else None,
                rule_sectors=['Technology'] if i % 3 == 0 else None,
                ml_label_24h=2.0 + (i % 10) * 0.5 if i % 3 == 0 else 0.3,
                ml_label_important=i % 3 == 0,
                ml_label_confidence=0.7 + (i % 5) * 0.05,
            )
            # Company News entity
            NewsEntity.objects.create(
                news=article,
                symbol='AAPL',
                entity_name='Apple Inc.',
                entity_type='equity',
                source='finnhub',
            )

        result = optimizer.prepare_training_data(weeks=8, company_news_only=True)

        assert result.get('error') is None
        assert result['X'] is not None
        assert result['n_samples'] >= 200
        assert result['X'].shape[1] == 5
        assert len(result['y']) == result['n_samples']
        assert len(result['weights']) == result['n_samples']

    @pytest.mark.django_db
    def test_date_range(self, optimizer):
        """date_range가 올바르게 반환"""
        from news.models import NewsArticle, NewsEntity

        for i in range(210):
            article = NewsArticle.objects.create(
                url=f'https://test.com/date-range-{i}',
                title=f'Date range test {i}',
                source='cnbc',
                published_at=timezone.now() - timedelta(days=50 - i % 50, hours=10),
                importance_score=0.5,
                ml_label_24h=1.0,
                ml_label_important=i % 4 == 0,
                ml_label_confidence=0.5,
            )
            NewsEntity.objects.create(
                news=article,
                symbol='MSFT',
                entity_name='Microsoft',
                entity_type='equity',
                source='finnhub',
            )

        result = optimizer.prepare_training_data(weeks=8)
        if result['date_range']:
            start, end = result['date_range']
            assert start <= end


# ════════════════════════════════════════
# 전체 파이프라인 테스트
# ════════════════════════════════════════

class TestTrainingPipeline:

    @pytest.mark.django_db
    def test_pipeline_insufficient_data(self, optimizer):
        """데이터 부족 시 failed 상태"""
        result = optimizer.run_training_pipeline()
        assert result['status'] == 'failed'
        assert 'Insufficient' in result['reason']

    @pytest.mark.django_db
    def test_pipeline_creates_history(self, optimizer):
        """파이프라인 실행 시 MLModelHistory 생성"""
        from news.models import MLModelHistory

        result = optimizer.run_training_pipeline()
        assert MLModelHistory.objects.exists()
        history = MLModelHistory.objects.order_by('-trained_at').first()
        assert history.algorithm == 'logistic_regression'

    @pytest.mark.django_db
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.prepare_training_data')
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.train_model')
    def test_pipeline_success_flow(self, mock_train, mock_data, optimizer):
        """성공 플로우 (mock)"""
        np.random.seed(42)
        mock_data.return_value = {
            'X': np.random.rand(300, 5),
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
            'coefficients': [0.5, 0.3, 0.2, 0.1, 0.15],
            'normalized_weights': {
                'source_credibility': 0.40,
                'entity_count': 0.24,
                'sentiment_magnitude': 0.16,
                'recency': 0.08,
                'keyword_relevance': 0.12,
            },
            'cv_scores': [
                {'f1': 0.70, 'precision': 0.65, 'recall': 0.75, 'accuracy': 0.72,
                 'train_size': 200, 'test_size': 100},
            ],
            'final_metrics': {
                'f1': 0.70,
                'precision': 0.65,
                'recall': 0.75,
                'accuracy': 0.72,
            },
        }

        result = optimizer.run_training_pipeline()
        assert result['status'] == 'shadow'
        assert result['safety_gate'] is True
        assert result['model_version'] is not None

    @pytest.mark.django_db
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.prepare_training_data')
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.train_model')
    def test_pipeline_safety_gate_fail(self, mock_train, mock_data, optimizer):
        """Safety Gate 실패 시 failed 상태"""
        np.random.seed(42)
        mock_data.return_value = {
            'X': np.random.rand(300, 5),
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
            'coefficients': [0.5, 0.3, 0.2, 0.1, 0.15],
            'normalized_weights': {
                'source_credibility': 0.40,
                'entity_count': 0.24,
                'sentiment_magnitude': 0.16,
                'recency': 0.08,
                'keyword_relevance': 0.12,
            },
            'cv_scores': [{'f1': 0.30, 'precision': 0.25, 'recall': 0.35,
                           'accuracy': 0.40, 'train_size': 200, 'test_size': 100}],
            'final_metrics': {
                'f1': 0.30,  # 0.55 미만 → tier1 실패
                'precision': 0.25,
                'recall': 0.35,
                'accuracy': 0.40,
            },
        }

        result = optimizer.run_training_pipeline()
        assert result['status'] == 'failed'
        assert result['safety_gate'] is False


# ════════════════════════════════════════
# 모델 배포 테스트
# ════════════════════════════════════════

class TestModelDeployment:

    @pytest.mark.django_db
    def test_deploy_nonexistent(self, optimizer):
        result = optimizer.deploy_model(9999)
        assert result['status'] == 'error'

    @pytest.mark.django_db
    def test_deploy_without_gate(self, optimizer):
        """Safety Gate 미통과 모델 배포 거부"""
        from news.models import MLModelHistory
        model = MLModelHistory.objects.create(
            model_version='test_deploy_1',
            training_samples=100,
            f1_score=0.40,
            safety_gate_passed=False,
            deployment_status='failed',
        )
        result = optimizer.deploy_model(model.id)
        assert result['status'] == 'error'

    @pytest.mark.django_db
    def test_deploy_success(self, optimizer):
        from news.models import MLModelHistory
        model = MLModelHistory.objects.create(
            model_version='test_deploy_2',
            training_samples=300,
            f1_score=0.70,
            safety_gate_passed=True,
            deployment_status='shadow',
            smoothed_weights={
                'source_credibility': 0.20,
                'entity_count': 0.25,
                'sentiment_magnitude': 0.20,
                'recency': 0.15,
                'keyword_relevance': 0.20,
            },
        )
        result = optimizer.deploy_model(model.id)
        assert result['status'] == 'deployed'

        model.refresh_from_db()
        assert model.deployment_status == 'deployed'
        assert model.deployed_at is not None

    @pytest.mark.django_db
    def test_deploy_rolls_back_previous(self, optimizer):
        """새 배포 시 이전 deployed 모델 → rolled_back"""
        from news.models import MLModelHistory
        old = MLModelHistory.objects.create(
            model_version='old_deployed',
            training_samples=200,
            f1_score=0.65,
            safety_gate_passed=True,
            deployment_status='deployed',
            deployed_at=timezone.now(),
        )
        new = MLModelHistory.objects.create(
            model_version='new_deploy',
            training_samples=300,
            f1_score=0.72,
            safety_gate_passed=True,
            deployment_status='shadow',
            smoothed_weights={'source_credibility': 0.20,
                              'entity_count': 0.20,
                              'sentiment_magnitude': 0.20,
                              'recency': 0.20,
                              'keyword_relevance': 0.20},
        )

        result = optimizer.deploy_model(new.id)
        assert result['status'] == 'deployed'

        old.refresh_from_db()
        assert old.deployment_status == 'rolled_back'

    @pytest.mark.django_db
    def test_deploy_already_deployed(self, optimizer):
        from news.models import MLModelHistory
        model = MLModelHistory.objects.create(
            model_version='already_deployed',
            training_samples=300,
            f1_score=0.70,
            safety_gate_passed=True,
            deployment_status='deployed',
            deployed_at=timezone.now(),
        )
        result = optimizer.deploy_model(model.id)
        assert result['status'] == 'already_deployed'


# ════════════════════════════════════════
# 상태 조회 테스트
# ════════════════════════════════════════

class TestGetStatus:

    @pytest.mark.django_db
    def test_empty_status(self):
        from news.services.ml_weight_optimizer import MLWeightOptimizer
        status = MLWeightOptimizer.get_current_status()
        assert status['latest_model'] is None
        assert status['deployed_model'] is None
        assert status['recent_history'] == []
        assert status['labeled_data_count'] >= 0

    @pytest.mark.django_db
    def test_with_models(self):
        from news.models import MLModelHistory
        from news.services.ml_weight_optimizer import MLWeightOptimizer

        MLModelHistory.objects.create(
            model_version='status_test_1',
            training_samples=200,
            f1_score=0.65,
            precision=0.60,
            recall=0.70,
            safety_gate_passed=True,
            deployment_status='shadow',
        )

        status = MLWeightOptimizer.get_current_status()
        assert status['latest_model'] is not None
        assert status['latest_model']['version'] == 'status_test_1'
        assert len(status['recent_history']) == 1

    @pytest.mark.django_db
    def test_ready_for_training(self):
        from news.services.ml_weight_optimizer import MLWeightOptimizer
        status = MLWeightOptimizer.get_current_status()
        assert 'ready_for_training' in status
        assert 'min_required' in status


# ════════════════════════════════════════
# Version 생성 테스트
# ════════════════════════════════════════

class TestVersionGeneration:

    @pytest.mark.django_db
    def test_version_format(self, optimizer):
        version = optimizer._generate_version()
        assert version.startswith('lr_v1_')
        parts = version.split('_')
        assert len(parts) == 4  # lr, v1, YYYYMMDD, count


# ════════════════════════════════════════
# Celery 태스크 테스트
# ════════════════════════════════════════

class TestCeleryTasks:

    @pytest.mark.django_db
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.run_training_pipeline')
    def test_train_importance_model_task(self, mock_pipeline):
        from news.tasks import train_importance_model

        mock_pipeline.return_value = {
            'status': 'shadow',
            'model_version': 'lr_v1_test',
        }

        result = train_importance_model()
        mock_pipeline.assert_called_once()
        assert result['status'] == 'shadow'

    @pytest.mark.django_db
    def test_generate_shadow_report_no_model(self):
        from news.tasks import generate_shadow_report

        result = generate_shadow_report()
        assert result['status'] == 'no_model'

    @pytest.mark.django_db
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.generate_shadow_comparison')
    def test_generate_shadow_report_with_model(self, mock_comparison):
        from news.models import MLModelHistory
        from news.tasks import generate_shadow_report

        MLModelHistory.objects.create(
            model_version='shadow_report_test',
            training_samples=200,
            f1_score=0.65,
            safety_gate_passed=True,
            deployment_status='shadow',
            smoothed_weights={'source_credibility': 0.20,
                              'entity_count': 0.20,
                              'sentiment_magnitude': 0.20,
                              'recency': 0.20,
                              'keyword_relevance': 0.20},
        )

        mock_comparison.return_value = {
            'period': 'Last 7 days',
            'total_articles': 100,
            'agreement_rate': 0.75,
        }

        result = generate_shadow_report(days=7)
        assert 'comparison' in result
        mock_comparison.assert_called_once()


# ════════════════════════════════════════
# API 엔드포인트 테스트
# ════════════════════════════════════════

class TestAPIEndpoints:

    @pytest.mark.django_db
    def test_ml_status_endpoint(self, request_factory):
        from news.api.views import NewsViewSet

        request = request_factory.get('/api/v1/news/ml-status/')
        request.query_params = {}
        view = NewsViewSet.as_view({'get': 'ml_status'})
        response = view(request)
        assert response.status_code == 200
        assert 'labeled_data_count' in response.data

    @pytest.mark.django_db
    def test_ml_shadow_report_no_data(self, request_factory):
        from news.api.views import NewsViewSet

        request = request_factory.get('/api/v1/news/ml-shadow-report/')
        request.query_params = {}
        view = NewsViewSet.as_view({'get': 'ml_shadow_report'})
        response = view(request)
        assert response.status_code == 200
        assert response.data.get('status') == 'no_report'

    @pytest.mark.django_db
    def test_ml_shadow_report_with_data(self, request_factory):
        from news.api.views import NewsViewSet
        from news.models import MLModelHistory

        MLModelHistory.objects.create(
            model_version='api_test',
            training_samples=200,
            f1_score=0.65,
            precision=0.60,
            recall=0.70,
            safety_gate_passed=True,
            deployment_status='shadow',
            smoothed_weights={'source_credibility': 0.20,
                              'entity_count': 0.20,
                              'sentiment_magnitude': 0.20,
                              'recency': 0.20,
                              'keyword_relevance': 0.20},
            shadow_comparison={
                'period': 'Last 7 days',
                'total_articles': 100,
                'agreement_rate': 0.80,
            },
        )

        request = request_factory.get('/api/v1/news/ml-shadow-report/')
        request.query_params = {}
        view = NewsViewSet.as_view({'get': 'ml_shadow_report'})
        response = view(request)
        assert response.status_code == 200
        assert response.data['model_version'] == 'api_test'
        assert response.data['shadow_comparison']['agreement_rate'] == 0.80


# ════════════════════════════════════════
# Beat 스케줄 테스트
# ════════════════════════════════════════

class TestBeatSchedule:

    def test_train_schedule_exists(self):
        from config.celery import app
        schedule = app.conf.beat_schedule
        assert 'train-importance-model' in schedule
        task = schedule['train-importance-model']
        assert task['task'] == 'news.tasks.train_importance_model'

    def test_shadow_report_schedule_exists(self):
        from config.celery import app
        schedule = app.conf.beat_schedule
        assert 'generate-shadow-report' in schedule
        task = schedule['generate-shadow-report']
        assert task['task'] == 'news.tasks.generate_shadow_report'
        assert task['kwargs']['days'] == 7

    def test_train_schedule_sunday(self):
        from config.celery import app
        task = app.conf.beat_schedule['train-importance-model']
        assert task['schedule'].day_of_week == {0}  # Sunday

    def test_shadow_after_training(self):
        from config.celery import app
        train = app.conf.beat_schedule['train-importance-model']
        shadow = app.conf.beat_schedule['generate-shadow-report']
        # shadow report runs after training (03:30 > 03:00)
        train_minute = list(train['schedule'].minute)[0] if hasattr(train['schedule'].minute, '__iter__') else train['schedule'].minute
        shadow_minute = list(shadow['schedule'].minute)[0] if hasattr(shadow['schedule'].minute, '__iter__') else shadow['schedule'].minute
        assert shadow_minute > train_minute
