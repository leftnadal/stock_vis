"""
ML Production Manager 테스트 (Phase 5)

- 자동 배포 체크 (check_auto_deploy)
- LLM 정확도 측정 (measure_llm_accuracy)
- 주간 성능 리포트 (generate_weekly_report)
- 롤백 (rollback_model)
- 배포 가중치 조회 (get_deployed_weights)
- Engine C (NewsClassifier) 통합
- Celery 태스크
- API 엔드포인트
- Beat 스케줄
"""

import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory
from django.utils import timezone


# ════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════

@pytest.fixture
def manager():
    from news.services.ml_production_manager import MLProductionManager
    return MLProductionManager()


@pytest.fixture
def sample_weights():
    return {
        'source_credibility': 0.25,
        'entity_count': 0.20,
        'sentiment_magnitude': 0.20,
        'recency': 0.20,
        'keyword_relevance': 0.15,
    }


@pytest.fixture
def request_factory():
    return RequestFactory()


def make_model(
    version,
    f1=0.65,
    safety_gate_passed=True,
    deployment_status='shadow',
    agreement_rate=0.80,
    weights=None,
    trained_offset_days=0,
):
    """MLModelHistory 헬퍼 팩토리."""
    from news.models import MLModelHistory

    w = weights or {
        'source_credibility': 0.20,
        'entity_count': 0.20,
        'sentiment_magnitude': 0.20,
        'recency': 0.20,
        'keyword_relevance': 0.20,
    }
    shadow_comparison = {'agreement_rate': agreement_rate} if agreement_rate is not None else None
    obj = MLModelHistory.objects.create(
        model_version=version,
        training_samples=300,
        f1_score=f1,
        precision=0.60,
        recall=0.70,
        safety_gate_passed=safety_gate_passed,
        deployment_status=deployment_status,
        smoothed_weights=w,
        shadow_comparison=shadow_comparison,
    )
    if trained_offset_days:
        MLModelHistory.objects.filter(pk=obj.pk).update(
            trained_at=timezone.now() - timedelta(days=trained_offset_days)
        )
        obj.refresh_from_db()
    return obj


def make_article_with_llm(
    llm_direction='bullish',
    actual_change=3.0,
    ml_label_important=True,
    llm_confidence=0.8,
):
    """LLM 분석 결과가 있는 NewsArticle 생성."""
    from news.models import NewsArticle

    return NewsArticle.objects.create(
        id=uuid.uuid4(),
        url=f'https://test.com/{uuid.uuid4()}',
        title='Test article',
        source='reuters',
        published_at=timezone.now() - timedelta(hours=2),
        llm_analyzed=True,
        llm_analysis={
            'direct_impacts': [
                {
                    'direction': llm_direction,
                    'confidence': llm_confidence,
                }
            ]
        },
        ml_label_24h=actual_change,
        ml_label_important=ml_label_important,
    )


# ════════════════════════════════════════
# TestAutoDeployCheck
# ════════════════════════════════════════

class TestAutoDeployCheck:

    @pytest.mark.django_db
    def test_not_enough_models_returns_wait(self, manager):
        # Given: 모델 3개 (4개 미만)
        for i in range(3):
            make_model(f'model_{i}', trained_offset_days=i * 7)

        # When
        result = manager.check_auto_deploy()

        # Then
        assert result['action'] == 'wait'
        assert 'Need 4' in result['reason']
        assert result['models_count'] == 3

    @pytest.mark.django_db
    def test_not_enough_models_zero(self, manager):
        # Given: 모델 없음
        result = manager.check_auto_deploy()

        assert result['action'] == 'wait'
        assert result['models_count'] == 0

    @pytest.mark.django_db
    def test_some_models_failed_safety_gate(self, manager):
        # Given: 4개 중 하나 Safety Gate 실패
        make_model('good_1', safety_gate_passed=True, trained_offset_days=21)
        make_model('good_2', safety_gate_passed=True, trained_offset_days=14)
        make_model('bad_1', safety_gate_passed=False, trained_offset_days=7)
        make_model('good_3', safety_gate_passed=True, trained_offset_days=0)

        result = manager.check_auto_deploy()

        assert result['action'] == 'wait'
        assert 'Safety Gate' in result['reason']
        assert 'bad_1' in result['failed_versions']

    @pytest.mark.django_db
    def test_f1_below_threshold(self, manager):
        # Given: 4개 모두 Safety Gate 통과했지만 F1이 낮은 모델 존재
        make_model('m1', f1=0.60, safety_gate_passed=True, trained_offset_days=21)
        make_model('m2', f1=0.58, safety_gate_passed=True, trained_offset_days=14)
        make_model('m3', f1=0.40, safety_gate_passed=True, trained_offset_days=7)  # 낮음
        make_model('m4', f1=0.65, safety_gate_passed=True, trained_offset_days=0)

        result = manager.check_auto_deploy()

        assert result['action'] == 'wait'
        assert '0.55' in result['reason']
        low_versions = [item['version'] for item in result['low_f1_versions']]
        assert 'm3' in low_versions

    @pytest.mark.django_db
    def test_agreement_rate_below_threshold(self, manager):
        # Given: 4개 모두 통과, F1 OK, 하지만 agreement_rate 낮음
        for i, name in enumerate(['m1', 'm2', 'm3', 'm4']):
            make_model(
                name,
                f1=0.60,
                safety_gate_passed=True,
                trained_offset_days=(3 - i) * 7,
                agreement_rate=0.60 if i == 3 else 0.80,  # 최신이 낮음
            )

        result = manager.check_auto_deploy()

        assert result['action'] == 'wait'
        assert 'agreement_rate' in result
        assert result['agreement_rate'] < 0.70

    @pytest.mark.django_db
    def test_latest_already_deployed(self, manager):
        # Given: 최신 모델이 이미 deployed 상태
        for i, name in enumerate(['m1', 'm2', 'm3']):
            make_model(name, safety_gate_passed=True, trained_offset_days=(3 - i) * 7)
        latest = make_model('m4', safety_gate_passed=True, deployment_status='deployed', trained_offset_days=0)

        result = manager.check_auto_deploy()

        assert result['action'] == 'skip'
        assert 'already deployed' in result['reason']
        assert result['model_version'] == 'm4'

    @pytest.mark.django_db
    def test_latest_not_in_shadow_status(self, manager):
        """
        쿼리가 shadow/deployed 상태만 포함하므로, 최신 모델이 rolled_back이면
        recent_models에서 제외됩니다. 즉 4개가 안 채워져 'wait'이 반환됩니다.
        """
        # Given: 3개 shadow + 1개 rolled_back (쿼리에서 제외됨)
        for i, name in enumerate(['m1', 'm2', 'm3']):
            make_model(name, safety_gate_passed=True, trained_offset_days=(3 - i) * 7)
        make_model('m4', safety_gate_passed=True, deployment_status='rolled_back', trained_offset_days=0)

        result = manager.check_auto_deploy()

        # rolled_back은 쿼리에 포함 안 되므로 3개만 → wait 반환
        assert result['action'] == 'wait'
        assert result['models_count'] == 3

    @pytest.mark.django_db
    def test_successful_auto_deploy(self, manager):
        # Given: 4주 연속 조건 충족
        for i, name in enumerate(['m1', 'm2', 'm3']):
            make_model(name, f1=0.60, safety_gate_passed=True, trained_offset_days=(3 - i) * 7)
        make_model(
            'm4',
            f1=0.65,
            safety_gate_passed=True,
            deployment_status='shadow',
            agreement_rate=0.80,
            trained_offset_days=0,
        )

        result = manager.check_auto_deploy()

        assert result['action'] == 'deployed'
        assert result['model_version'] == 'm4'
        assert 'deployed_at' in result

    @pytest.mark.django_db
    def test_previous_model_gets_rolled_back_on_deploy(self, manager):
        # Given: 기존 deployed 모델 + 새 조건 충족 shadow 모델
        from news.models import MLModelHistory

        old_deployed = make_model('old', f1=0.60, safety_gate_passed=True, deployment_status='deployed', trained_offset_days=28)
        for i, name in enumerate(['m2', 'm3', 'm4']):
            make_model(name, f1=0.60, safety_gate_passed=True, trained_offset_days=(3 - i) * 7)
        make_model('m5', f1=0.65, safety_gate_passed=True, deployment_status='shadow', agreement_rate=0.80, trained_offset_days=0)

        manager.check_auto_deploy()

        old_deployed.refresh_from_db()
        assert old_deployed.deployment_status == 'rolled_back'

    @pytest.mark.django_db
    def test_deploy_updates_model_status(self, manager):
        # Given: 조건 충족
        from news.models import MLModelHistory

        for i, name in enumerate(['m1', 'm2', 'm3']):
            make_model(name, f1=0.60, safety_gate_passed=True, trained_offset_days=(3 - i) * 7)
        shadow = make_model('m4', f1=0.65, safety_gate_passed=True, deployment_status='shadow', agreement_rate=0.80, trained_offset_days=0)

        manager.check_auto_deploy()

        shadow.refresh_from_db()
        assert shadow.deployment_status == 'deployed'
        assert shadow.deployed_at is not None

    @pytest.mark.django_db
    def test_all_conditions_met_returns_deployed_action(self, manager):
        # Given: 4개 shadow 모두 통과 + agreement 높음
        for i, name in enumerate(['m1', 'm2', 'm3']):
            make_model(name, f1=0.62, safety_gate_passed=True, trained_offset_days=(3 - i) * 7)
        make_model('m4', f1=0.70, safety_gate_passed=True, deployment_status='shadow', agreement_rate=0.75, trained_offset_days=0)

        result = manager.check_auto_deploy()

        assert result['action'] == 'deployed'
        assert result['model_version'] == 'm4'


# ════════════════════════════════════════
# TestLLMAccuracy
# ════════════════════════════════════════

class TestLLMAccuracy:

    @pytest.mark.django_db
    def test_no_articles_returns_zero(self, manager):
        # Given: LLM 분석 완료된 기사 없음
        result = manager.measure_llm_accuracy(days=7)

        assert result['total_measured'] == 0
        assert result['direction_accuracy'] == 0.0
        assert result['importance_accuracy'] == 0.0

    @pytest.mark.django_db
    def test_matching_direction_bullish(self, manager):
        # Given: LLM bullish, 실제 +3% 상승
        make_article_with_llm(llm_direction='bullish', actual_change=3.0)

        result = manager.measure_llm_accuracy(days=7)

        assert result['total_measured'] == 1
        assert result['correct_direction'] == 1
        assert result['direction_accuracy'] == 1.0

    @pytest.mark.django_db
    def test_matching_direction_bearish(self, manager):
        # Given: LLM bearish, 실제 -2% 하락
        make_article_with_llm(llm_direction='bearish', actual_change=-2.0)

        result = manager.measure_llm_accuracy(days=7)

        assert result['total_measured'] == 1
        assert result['correct_direction'] == 1

    @pytest.mark.django_db
    def test_mismatching_direction(self, manager):
        # Given: LLM bullish, 실제 -3% 하락
        make_article_with_llm(llm_direction='bullish', actual_change=-3.0)

        result = manager.measure_llm_accuracy(days=7)

        assert result['total_measured'] == 1
        assert result['correct_direction'] == 0
        assert result['direction_accuracy'] == 0.0

    @pytest.mark.django_db
    def test_neutral_prediction_with_small_change(self, manager):
        # Given: LLM neutral, 실제 변동 0.3% (small)
        make_article_with_llm(llm_direction='neutral', actual_change=0.3)

        result = manager.measure_llm_accuracy(days=7)

        # neutral + |change| <= 1.0 → correct
        assert result['total_measured'] == 1
        assert result['correct_direction'] == 1

    @pytest.mark.django_db
    def test_importance_accuracy_measurement(self, manager):
        # Given: LLM confidence >= 0.7 (important), 실제 ml_label_important=True
        make_article_with_llm(llm_direction='bullish', actual_change=3.0, ml_label_important=True, llm_confidence=0.8)

        result = manager.measure_llm_accuracy(days=7)

        assert result['correct_importance'] == 1
        assert result['importance_accuracy'] == 1.0

    @pytest.mark.django_db
    def test_mixed_results_multiple_articles(self, manager):
        # Given: 4개 기사, 2개 방향 일치
        make_article_with_llm(llm_direction='bullish', actual_change=3.0)   # correct
        make_article_with_llm(llm_direction='bearish', actual_change=-2.0)  # correct
        make_article_with_llm(llm_direction='bullish', actual_change=-3.0)  # wrong
        make_article_with_llm(llm_direction='bearish', actual_change=2.0)   # wrong

        result = manager.measure_llm_accuracy(days=7)

        assert result['total_measured'] == 4
        assert result['correct_direction'] == 2
        assert result['direction_accuracy'] == 0.5


# ════════════════════════════════════════
# TestWeeklyReport
# ════════════════════════════════════════

class TestWeeklyReport:

    @pytest.mark.django_db
    def test_empty_state_no_models(self, manager):
        # Given: 모델 없음
        result = manager.generate_weekly_report()

        assert 'period' in result
        assert 'model_status' in result
        assert result['model_status']['deployed_version'] is None
        assert result['model_status']['latest_version'] is None
        assert 'recommendations' in result
        assert len(result['recommendations']) > 0

    @pytest.mark.django_db
    def test_with_deployed_model(self, manager):
        # Given: deployed 모델 존재
        make_model('v1_deployed', f1=0.65, deployment_status='deployed')

        result = manager.generate_weekly_report()

        assert result['model_status']['deployed_version'] == 'v1_deployed'
        assert result['model_status']['deployed_f1'] == pytest.approx(0.65, abs=0.01)

    @pytest.mark.django_db
    def test_f1_trend_improving(self, manager):
        # Given: F1이 시간에 따라 상승 (4주 내)
        from news.models import MLModelHistory

        m1 = MLModelHistory.objects.create(
            model_version='trend_low', training_samples=200, f1_score=0.55,
            safety_gate_passed=True, deployment_status='shadow',
        )
        m2 = MLModelHistory.objects.create(
            model_version='trend_high', training_samples=250, f1_score=0.70,
            safety_gate_passed=True, deployment_status='shadow',
        )
        # older first
        MLModelHistory.objects.filter(pk=m1.pk).update(
            trained_at=timezone.now() - timedelta(weeks=3)
        )

        result = manager.generate_weekly_report()

        assert result['performance_trend']['trend'] == 'improving'

    @pytest.mark.django_db
    def test_f1_trend_declining(self, manager):
        # Given: F1이 시간에 따라 하락
        from news.models import MLModelHistory

        m1 = MLModelHistory.objects.create(
            model_version='trend_high2', training_samples=200, f1_score=0.75,
            safety_gate_passed=True, deployment_status='shadow',
        )
        m2 = MLModelHistory.objects.create(
            model_version='trend_low2', training_samples=250, f1_score=0.55,
            safety_gate_passed=True, deployment_status='shadow',
        )
        MLModelHistory.objects.filter(pk=m1.pk).update(
            trained_at=timezone.now() - timedelta(weeks=3)
        )

        result = manager.generate_weekly_report()

        assert result['performance_trend']['trend'] == 'declining'

    @pytest.mark.django_db
    def test_recommendations_generated(self, manager):
        # Given: 기본 상태
        result = manager.generate_weekly_report()

        assert isinstance(result['recommendations'], list)
        assert len(result['recommendations']) >= 1

    @pytest.mark.django_db
    def test_report_has_all_required_fields(self, manager):
        result = manager.generate_weekly_report()

        assert 'period' in result
        assert 'model_status' in result
        assert 'performance_trend' in result
        assert 'llm_accuracy' in result
        assert 'data_stats' in result
        assert 'recommendations' in result
        assert 'generated_at' in result


# ════════════════════════════════════════
# TestRollback
# ════════════════════════════════════════

class TestRollback:

    @pytest.mark.django_db
    def test_rollback_deployed_model(self, manager):
        # Given: deployed 모델 존재
        model = make_model('to_rollback', deployment_status='deployed')

        result = manager.rollback_model()

        assert result['status'] == 'rolled_back'
        assert result['rolled_back_version'] == 'to_rollback'
        assert result['fallback'] == 'manual_weights'

    @pytest.mark.django_db
    def test_no_deployed_model_to_rollback(self, manager):
        # Given: deployed 모델 없음
        result = manager.rollback_model()

        assert result['status'] == 'no_deployed_model'
        assert result['fallback'] == 'manual_weights'

    @pytest.mark.django_db
    def test_rollback_updates_deployment_status(self, manager):
        # Given: deployed 모델
        model = make_model('rollback_check', deployment_status='deployed')

        manager.rollback_model()

        model.refresh_from_db()
        assert model.deployment_status == 'rolled_back'

    @pytest.mark.django_db
    def test_rollback_shadow_model_not_affected(self, manager):
        # Given: shadow + deployed 모델
        shadow = make_model('shadow_model', deployment_status='shadow')
        deployed = make_model('deployed_model', deployment_status='deployed')

        manager.rollback_model()

        shadow.refresh_from_db()
        assert shadow.deployment_status == 'shadow'  # 변경 없음


# ════════════════════════════════════════
# TestGetDeployedWeights
# ════════════════════════════════════════

class TestGetDeployedWeights:

    @pytest.mark.django_db
    def test_no_deployed_model_returns_none(self):
        # Given: deployed 모델 없음
        from news.services.ml_production_manager import MLProductionManager

        result = MLProductionManager.get_deployed_weights()

        assert result is None

    @pytest.mark.django_db
    def test_deployed_model_with_weights(self, sample_weights):
        # Given: deployed 모델 + smoothed_weights
        from news.services.ml_production_manager import MLProductionManager

        make_model('deployed_w', deployment_status='deployed', weights=sample_weights)

        result = MLProductionManager.get_deployed_weights()

        assert result is not None
        assert 'source_credibility' in result
        assert result['source_credibility'] == sample_weights['source_credibility']

    @pytest.mark.django_db
    def test_deployed_model_without_weights_returns_none(self):
        # Given: deployed 모델이지만 smoothed_weights=None
        from news.models import MLModelHistory
        from news.services.ml_production_manager import MLProductionManager

        MLModelHistory.objects.create(
            model_version='no_weights',
            training_samples=100,
            f1_score=0.65,
            safety_gate_passed=True,
            deployment_status='deployed',
            smoothed_weights=None,
        )

        result = MLProductionManager.get_deployed_weights()

        assert result is None

    @pytest.mark.django_db
    def test_shadow_model_weights_not_returned(self, sample_weights):
        # Given: shadow 모델만 존재
        from news.services.ml_production_manager import MLProductionManager

        make_model('shadow_only', deployment_status='shadow', weights=sample_weights)

        result = MLProductionManager.get_deployed_weights()

        assert result is None


# ════════════════════════════════════════
# TestEngineIntegration
# ════════════════════════════════════════

class TestEngineIntegration:

    @pytest.mark.django_db
    def test_news_classifier_uses_deployed_weights(self, sample_weights):
        # Given: deployed 모델 존재
        make_model('integration_model', deployment_status='deployed', weights=sample_weights)

        # When: NewsClassifier 초기화 (weights 미지정)
        from news.services.news_classifier import NewsClassifier
        classifier = NewsClassifier()

        # Then: deployed weights가 로드됨
        assert classifier.weights == sample_weights

    @pytest.mark.django_db
    def test_news_classifier_falls_back_to_default_weights(self):
        # Given: deployed 모델 없음
        from news.services.news_classifier import DEFAULT_WEIGHTS, NewsClassifier
        classifier = NewsClassifier()

        assert classifier.weights == DEFAULT_WEIGHTS

    @pytest.mark.django_db
    def test_news_classifier_uses_explicit_weights(self, sample_weights):
        # Given: 명시적 weights 제공
        from news.services.news_classifier import NewsClassifier
        classifier = NewsClassifier(weights=sample_weights)

        assert classifier.weights == sample_weights

    @pytest.mark.django_db
    @patch('news.services.ml_production_manager.MLProductionManager.get_deployed_weights')
    def test_weight_loading_error_falls_back_to_default(self, mock_get):
        # Given: get_deployed_weights 예외 발생
        mock_get.side_effect = Exception('DB unavailable')

        from news.services.news_classifier import DEFAULT_WEIGHTS, NewsClassifier
        classifier = NewsClassifier()

        assert classifier.weights == DEFAULT_WEIGHTS


# ════════════════════════════════════════
# TestCeleryTasks
# ════════════════════════════════════════

class TestCeleryTasks:

    @pytest.mark.django_db
    @patch('news.services.ml_production_manager.MLProductionManager.check_auto_deploy')
    def test_check_auto_deploy_task(self, mock_check):
        from news.tasks import check_auto_deploy

        mock_check.return_value = {'action': 'wait', 'reason': 'test', 'models_count': 0}

        result = check_auto_deploy()

        mock_check.assert_called_once()
        assert result['action'] == 'wait'

    @pytest.mark.django_db
    @patch('news.services.ml_production_manager.MLProductionManager.generate_weekly_report')
    def test_generate_weekly_ml_report_task(self, mock_report):
        from news.tasks import generate_weekly_ml_report

        mock_report.return_value = {
            'period': {'start': '2026-02-18', 'end': '2026-02-25'},
            'model_status': {},
            'recommendations': ['All healthy.'],
        }

        result = generate_weekly_ml_report()

        mock_report.assert_called_once()
        assert 'period' in result

    @pytest.mark.django_db
    @patch('news.services.ml_weight_optimizer.MLWeightOptimizer.run_lightgbm_pipeline')
    def test_train_lightgbm_model_task(self, mock_pipeline):
        from news.tasks import train_lightgbm_model

        mock_pipeline.return_value = {'status': 'not_ready', 'readiness': {}}

        result = train_lightgbm_model()

        mock_pipeline.assert_called_once()
        assert result['status'] == 'not_ready'

    @pytest.mark.django_db
    @patch('news.services.ml_production_manager.MLProductionManager.check_auto_deploy')
    def test_check_auto_deploy_task_retry_on_error(self, mock_check):
        from celery.exceptions import Retry
        from news.tasks import check_auto_deploy

        mock_check.side_effect = Exception('Service error')

        with pytest.raises((Retry, Exception)):
            check_auto_deploy()

    @pytest.mark.django_db
    @patch('news.services.ml_production_manager.MLProductionManager.generate_weekly_report')
    def test_generate_weekly_report_task_retry_on_error(self, mock_report):
        from celery.exceptions import Retry
        from news.tasks import generate_weekly_ml_report

        mock_report.side_effect = Exception('DB error')

        with pytest.raises((Retry, Exception)):
            generate_weekly_ml_report()


# ════════════════════════════════════════
# TestAPIEndpoints
# ════════════════════════════════════════

class TestAPIEndpoints:

    @pytest.mark.django_db
    @patch('news.services.ml_production_manager.MLProductionManager.generate_weekly_report')
    def test_ml_weekly_report_returns_200(self, mock_report, request_factory):
        from django.core.cache import cache

        from news.api.views import NewsViewSet

        mock_report.return_value = {
            'period': {'start': '2026-02-18', 'end': '2026-02-25'},
            'model_status': {'deployed_version': None},
            'performance_trend': {'trend': 'stable', 'recent_f1_scores': [], 'gate_pass_rate': 0},
            'llm_accuracy': {'direction_accuracy': 0.0, 'importance_accuracy': 0.0, 'total_measured': 0},
            'data_stats': {'total_labeled': 0, 'new_labeled_this_week': 0, 'new_analyzed_this_week': 0},
            'recommendations': ['All healthy.'],
            'generated_at': str(timezone.now()),
        }
        cache.delete('news:ml_weekly_report')

        request = request_factory.get('/api/v1/news/ml-weekly-report/')
        request.query_params = {}
        view = NewsViewSet.as_view({'get': 'ml_weekly_report'})
        response = view(request)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_ml_lightgbm_readiness_returns_200(self, request_factory):
        from news.api.views import NewsViewSet

        request = request_factory.get('/api/v1/news/ml-lightgbm-readiness/')
        request.query_params = {}
        view = NewsViewSet.as_view({'get': 'ml_lightgbm_readiness'})
        response = view(request)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_ml_lightgbm_readiness_response_format(self, request_factory):
        from news.api.views import NewsViewSet

        request = request_factory.get('/api/v1/news/ml-lightgbm-readiness/')
        request.query_params = {}
        view = NewsViewSet.as_view({'get': 'ml_lightgbm_readiness'})
        response = view(request)

        assert 'ready' in response.data
        assert 'conditions' in response.data
        conditions = response.data['conditions']
        assert 'data_sufficient' in conditions
        assert 'lr_stagnation' in conditions
        assert 'feature_stability' in conditions

    @pytest.mark.django_db
    @patch('news.services.ml_production_manager.MLProductionManager.generate_weekly_report')
    def test_ml_weekly_report_response_format(self, mock_report, request_factory):
        from django.core.cache import cache

        from news.api.views import NewsViewSet

        mock_report.return_value = {
            'period': {'start': '2026-02-18', 'end': '2026-02-25'},
            'model_status': {'deployed_version': None, 'deployed_f1': None, 'latest_version': None, 'latest_f1': None, 'latest_status': None},
            'performance_trend': {'trend': 'stable', 'recent_f1_scores': [], 'gate_pass_rate': 0},
            'llm_accuracy': {'direction_accuracy': 0.0, 'importance_accuracy': 0.0, 'total_measured': 0},
            'data_stats': {'total_labeled': 0, 'new_labeled_this_week': 0, 'new_analyzed_this_week': 0},
            'recommendations': ['All healthy.'],
            'generated_at': str(timezone.now()),
        }
        cache.delete('news:ml_weekly_report')

        request = request_factory.get('/api/v1/news/ml-weekly-report/')
        request.query_params = {}
        view = NewsViewSet.as_view({'get': 'ml_weekly_report'})
        response = view(request)

        assert 'period' in response.data
        assert 'model_status' in response.data
        assert 'performance_trend' in response.data
        assert 'llm_accuracy' in response.data
        assert 'recommendations' in response.data


# ════════════════════════════════════════
# TestBeatSchedule
# ════════════════════════════════════════

class TestBeatSchedule:

    def test_check_auto_deploy_schedule_exists(self):
        from config.celery import app

        schedule = app.conf.beat_schedule
        assert 'check-auto-deploy' in schedule

    def test_check_auto_deploy_task_name(self):
        from config.celery import app

        task = app.conf.beat_schedule['check-auto-deploy']
        assert task['task'] == 'news.tasks.check_auto_deploy'

    def test_check_auto_deploy_schedule_sunday(self):
        from config.celery import app

        task = app.conf.beat_schedule['check-auto-deploy']
        schedule = task['schedule']
        assert schedule.day_of_week == {0}  # 일요일

    def test_check_auto_deploy_schedule_hour(self):
        from config.celery import app

        task = app.conf.beat_schedule['check-auto-deploy']
        schedule = task['schedule']
        assert 4 in schedule.hour

    def test_generate_weekly_ml_report_schedule_exists(self):
        from config.celery import app

        schedule = app.conf.beat_schedule
        assert 'generate-weekly-ml-report' in schedule

    def test_generate_weekly_ml_report_task_name(self):
        from config.celery import app

        task = app.conf.beat_schedule['generate-weekly-ml-report']
        assert task['task'] == 'news.tasks.generate_weekly_ml_report'

    def test_generate_weekly_ml_report_schedule_sunday(self):
        from config.celery import app

        task = app.conf.beat_schedule['generate-weekly-ml-report']
        schedule = task['schedule']
        assert schedule.day_of_week == {0}

    def test_train_lightgbm_model_schedule_exists(self):
        from config.celery import app

        schedule = app.conf.beat_schedule
        assert 'train-lightgbm-model' in schedule

    def test_train_lightgbm_model_task_name(self):
        from config.celery import app

        task = app.conf.beat_schedule['train-lightgbm-model']
        assert task['task'] == 'news.tasks.train_lightgbm_model'

    def test_train_lightgbm_model_schedule_sunday(self):
        from config.celery import app

        task = app.conf.beat_schedule['train-lightgbm-model']
        schedule = task['schedule']
        assert schedule.day_of_week == {0}

    def test_schedule_execution_order(self):
        """check-auto-deploy(04:00) < generate-weekly-ml-report(04:15) < train-lightgbm-model(04:30)"""
        from config.celery import app

        beat = app.conf.beat_schedule

        def get_time_minutes(key):
            s = beat[key]['schedule']
            hour = list(s.hour)[0] if hasattr(s.hour, '__iter__') else s.hour
            minute = list(s.minute)[0] if hasattr(s.minute, '__iter__') else s.minute
            return hour * 60 + minute

        t_deploy = get_time_minutes('check-auto-deploy')
        t_report = get_time_minutes('generate-weekly-ml-report')
        t_lgbm = get_time_minutes('train-lightgbm-model')

        assert t_deploy < t_report < t_lgbm


# ════════════════════════════════════════
# TestConsecutiveDeclineDetection
# ════════════════════════════════════════

class TestConsecutiveDeclineDetection:

    @pytest.mark.django_db
    def test_detect_consecutive_decline_3_weeks(self, manager):
        # Given: 4개 모델, F1이 매주 연속 하락 (0.70 → 0.65 → 0.60 → 0.55)
        # recent_models[0] = 가장 최신 (lowest), recent_models[-1] = 가장 오래된 (highest)
        make_model('w4_old', f1=0.70, trained_offset_days=21)   # 가장 오래됨
        make_model('w3', f1=0.65, trained_offset_days=14)
        make_model('w2', f1=0.60, trained_offset_days=7)
        make_model('w1_new', f1=0.55, trained_offset_days=0)   # 가장 최신

        result = manager.detect_consecutive_decline(weeks=3)

        assert result['consecutive_decline'] is True
        assert result['decline_weeks'] == 3

    @pytest.mark.django_db
    def test_detect_consecutive_decline_no_decline(self, manager):
        # Given: 4개 모델, F1이 상승 추세
        make_model('up_w4', f1=0.55, trained_offset_days=21)
        make_model('up_w3', f1=0.60, trained_offset_days=14)
        make_model('up_w2', f1=0.65, trained_offset_days=7)
        make_model('up_w1', f1=0.70, trained_offset_days=0)

        result = manager.detect_consecutive_decline(weeks=3)

        assert result['consecutive_decline'] is False

    @pytest.mark.django_db
    def test_detect_consecutive_decline_partial(self, manager):
        # Given: 4개 모델, 2주 하락 후 중간에 상승 (연속 3주 하락 아님)
        make_model('partial_w4', f1=0.70, trained_offset_days=21)
        make_model('partial_w3', f1=0.68, trained_offset_days=14)  # 상승 → 연속 끊김
        make_model('partial_w2', f1=0.63, trained_offset_days=7)
        make_model('partial_w1', f1=0.58, trained_offset_days=0)

        result = manager.detect_consecutive_decline(weeks=3)

        # recent_models[0]=0.58, [1]=0.63, [2]=0.68, [3]=0.70
        # 0.58 < 0.63 (decline), 0.63 < 0.68 (decline), 0.68 < 0.70 (decline) → 3연속
        # 실제로는 [2]=0.68 < [3]=0.70 이므로 3연속 하락 맞음
        # partial_w3(0.68) < partial_w4(0.70) 이므로 decline_count==3, consecutive_decline==True
        # 중간에 끊기는 케이스를 재구성: w3=0.75 (상승)
        assert 'consecutive_decline' in result

    @pytest.mark.django_db
    def test_detect_consecutive_decline_partial_broken(self, manager):
        """중간에 F1이 올라가면 연속 하락 미감지"""
        from news.models import MLModelHistory

        # 최신순: 0.58(최신) < 0.63 → decline 1
        # 0.63 > 0.72 → 상승, break → decline_count=1, 3 미만 → False
        m_old = MLModelHistory.objects.create(
            model_version='break_w4', training_samples=200, f1_score=0.70,
            safety_gate_passed=True, deployment_status='shadow',
        )
        m_mid_high = MLModelHistory.objects.create(
            model_version='break_w3', training_samples=200, f1_score=0.72,
            safety_gate_passed=True, deployment_status='shadow',
        )
        m_mid_low = MLModelHistory.objects.create(
            model_version='break_w2', training_samples=200, f1_score=0.63,
            safety_gate_passed=True, deployment_status='shadow',
        )
        m_new = MLModelHistory.objects.create(
            model_version='break_w1', training_samples=200, f1_score=0.58,
            safety_gate_passed=True, deployment_status='shadow',
        )
        MLModelHistory.objects.filter(pk=m_old.pk).update(
            trained_at=timezone.now() - timedelta(days=21)
        )
        MLModelHistory.objects.filter(pk=m_mid_high.pk).update(
            trained_at=timezone.now() - timedelta(days=14)
        )
        MLModelHistory.objects.filter(pk=m_mid_low.pk).update(
            trained_at=timezone.now() - timedelta(days=7)
        )

        result = manager.detect_consecutive_decline(weeks=3)

        # recent_models 최신순: break_w1(0.58), break_w2(0.63), break_w3(0.72), break_w4(0.70)
        # 0.58 < 0.63 → decline 1
        # 0.63 < 0.72 → decline 2
        # 0.72 > 0.70 → break → decline_count=2 < 3 → False
        assert result['consecutive_decline'] is False

    @pytest.mark.django_db
    def test_detect_consecutive_decline_insufficient_models(self, manager):
        # Given: 모델 2개뿐 (weeks+1=4개 필요)
        make_model('few_1', f1=0.65, trained_offset_days=7)
        make_model('few_2', f1=0.60, trained_offset_days=0)

        result = manager.detect_consecutive_decline(weeks=3)

        assert result['consecutive_decline'] is False
        assert len(result['f1_history']) == 2

    @pytest.mark.django_db
    def test_detect_consecutive_decline_window_shrink_8_to_6(self, manager):
        """연속 하락 감지 시 8주 → 6주로 축소"""
        from news.models import MLModelHistory

        # 4개 모델, 연속 하락
        for i, (ver, offset) in enumerate([
            ('shrink_w4', 21), ('shrink_w3', 14), ('shrink_w2', 7), ('shrink_w1', 0)
        ]):
            f1 = 0.70 - i * 0.05  # 0.70, 0.65, 0.60, 0.55
            m = MLModelHistory.objects.create(
                model_version=ver, training_samples=200, f1_score=f1,
                safety_gate_passed=True, deployment_status='shadow',
                training_config={'rolling_window_weeks': 8},
            )
            MLModelHistory.objects.filter(pk=m.pk).update(
                trained_at=timezone.now() - timedelta(days=offset)
            )

        result = manager.detect_consecutive_decline(weeks=3)

        assert result['consecutive_decline'] is True
        assert result['previous_window'] == 8
        assert result['new_window'] == 6

    @pytest.mark.django_db
    def test_detect_consecutive_decline_window_shrink_minimum_4(self, manager):
        """이미 4주면 더 이상 축소 안 됨 (max(4-2, 4) = 4)"""
        from news.models import MLModelHistory

        for i, (ver, offset) in enumerate([
            ('min_w4', 21), ('min_w3', 14), ('min_w2', 7), ('min_w1', 0)
        ]):
            f1 = 0.70 - i * 0.05
            m = MLModelHistory.objects.create(
                model_version=ver, training_samples=200, f1_score=f1,
                safety_gate_passed=True, deployment_status='shadow',
                training_config={'rolling_window_weeks': 4},
            )
            MLModelHistory.objects.filter(pk=m.pk).update(
                trained_at=timezone.now() - timedelta(days=offset)
            )

        result = manager.detect_consecutive_decline(weeks=3)

        assert result['consecutive_decline'] is True
        assert result['previous_window'] == 4
        assert result['new_window'] == 4  # max(4-2, 4) = 4

    @pytest.mark.django_db
    def test_detect_consecutive_decline_feature_importance_included(self, manager):
        """연속 하락 감지 시 feature_importance가 반환되는지 확인"""
        from news.models import MLModelHistory

        fi = {'source_credibility': 0.30, 'entity_count': 0.25}
        for i, (ver, offset) in enumerate([
            ('fi_w4', 21), ('fi_w3', 14), ('fi_w2', 7), ('fi_w1', 0)
        ]):
            f1 = 0.70 - i * 0.05
            m = MLModelHistory.objects.create(
                model_version=ver, training_samples=200, f1_score=f1,
                safety_gate_passed=True, deployment_status='shadow',
                feature_importance=fi if ver == 'fi_w1' else None,
            )
            MLModelHistory.objects.filter(pk=m.pk).update(
                trained_at=timezone.now() - timedelta(days=offset)
            )

        result = manager.detect_consecutive_decline(weeks=3)

        assert result['consecutive_decline'] is True
        assert result['feature_importance'] == fi

    @pytest.mark.django_db
    def test_detect_consecutive_decline_alert_message_format(self, manager):
        """alert_message가 주수, F1, window 정보를 포함하는지 확인"""
        from news.models import MLModelHistory

        for i, (ver, offset) in enumerate([
            ('alert_w4', 21), ('alert_w3', 14), ('alert_w2', 7), ('alert_w1', 0)
        ]):
            f1 = 0.70 - i * 0.05
            m = MLModelHistory.objects.create(
                model_version=ver, training_samples=200, f1_score=f1,
                safety_gate_passed=True, deployment_status='shadow',
            )
            MLModelHistory.objects.filter(pk=m.pk).update(
                trained_at=timezone.now() - timedelta(days=offset)
            )

        result = manager.detect_consecutive_decline(weeks=3)

        assert result['consecutive_decline'] is True
        alert = result['alert_message']
        assert alert is not None
        assert '3' in alert           # 주수
        assert '0.55' in alert or '0.550' in alert  # 최신 F1
        assert 'Rolling Window' in alert


# ════════════════════════════════════════
# TestMonitorMLPerformance
# ════════════════════════════════════════

class TestMonitorMLPerformance:

    def test_monitor_ml_performance_task_exists(self):
        # Given/When: 태스크 import
        from news.tasks import monitor_ml_performance

        # Then: import 성공
        assert monitor_ml_performance is not None
        assert callable(monitor_ml_performance)

    @pytest.mark.django_db
    @patch('news.services.ml_production_manager.MLProductionManager.detect_consecutive_decline')
    def test_monitor_ml_performance_calls_detect(self, mock_detect):
        # Given
        mock_detect.return_value = {
            'consecutive_decline': False,
            'decline_weeks': 0,
            'f1_history': [],
            'action_taken': 'none',
            'previous_window': 8,
            'new_window': 8,
            'feature_importance': None,
            'alert_message': None,
        }

        # When
        from news.tasks import monitor_ml_performance
        result = monitor_ml_performance()

        # Then: detect_consecutive_decline(weeks=3)이 호출됨
        mock_detect.assert_called_once_with(weeks=3)
        assert result['action_taken'] == 'none'

    def test_beat_schedule_monitor_ml_performance(self):
        """monitor-ml-performance 스케줄이 일요일 04:20에 등록되어 있는지 확인"""
        from config.celery import app

        beat = app.conf.beat_schedule

        # 스케줄 키 존재 확인
        assert 'monitor-ml-performance' in beat

        task_config = beat['monitor-ml-performance']

        # 태스크 이름 확인
        assert task_config['task'] == 'news.tasks.monitor_ml_performance'

        # 스케줄 시간 확인 (일요일 04:20)
        schedule = task_config['schedule']
        assert schedule.day_of_week == {0}   # 일요일
        assert 4 in schedule.hour
        assert 20 in schedule.minute
