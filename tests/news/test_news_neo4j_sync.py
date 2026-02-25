"""
News Neo4j Sync Service 테스트 (Phase 3)

NewsNeo4jSyncService의 모든 기능을 테스트합니다:
- NewsEvent 노드 생성
- DIRECTLY_IMPACTS / INDIRECTLY_IMPACTS / CREATES_OPPORTUNITY / AFFECTS_SECTOR 관계 생성
- sync_article / sync_batch
- cleanup_expired_relationships
- get_news_events_for_symbol / get_impact_map / get_symbol_impact_summary
- reinforce_relationships
- Neo4j 미연결 시 graceful fallback
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from django.utils import timezone


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def mock_neo4j_driver():
    """Neo4j driver mock"""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=False)
    return driver, session


@pytest.fixture
def sync_service(mock_neo4j_driver):
    """NewsNeo4jSyncService with mocked driver"""
    driver, session = mock_neo4j_driver
    with patch('news.services.news_neo4j_sync.get_neo4j_driver', return_value=driver):
        from news.services.news_neo4j_sync import NewsNeo4jSyncService
        service = NewsNeo4jSyncService()
        service._session = session
        return service


@pytest.fixture
def unavailable_service():
    """Neo4j unavailable service"""
    with patch('news.services.news_neo4j_sync.get_neo4j_driver', return_value=None):
        from news.services.news_neo4j_sync import NewsNeo4jSyncService
        return NewsNeo4jSyncService()


@pytest.fixture
def sample_article():
    """LLM 분석 완료된 뉴스 기사 mock"""
    article = MagicMock()
    article.id = uuid.uuid4()
    article.title = "NVIDIA reports record quarterly revenue"
    article.source = "Reuters"
    article.importance_score = 0.95
    article.published_at = timezone.now()
    article.llm_analysis = {
        'tier': 'C',
        'analyzed_at': timezone.now().isoformat(),
        'direct_impacts': [
            {
                'symbol': 'NVDA',
                'direction': 'bullish',
                'confidence': 0.95,
                'reason': 'Record revenue directly benefits stock price',
            },
        ],
        'indirect_impacts': [
            {
                'symbol': 'AMD',
                'direction': 'bullish',
                'confidence': 0.7,
                'reason': 'Competitor benefits from sector momentum',
                'chain_logic': 'NVDA revenue → AI demand validated → AMD benefits',
            },
        ],
        'opportunities': [
            {
                'symbol': 'ARM',
                'thesis': 'ARM chip design licensing benefits from AI boom',
                'timeframe': '3-6 months',
                'confidence': 0.6,
            },
        ],
        'sector_ripple': [
            {
                'sector': 'Technology',
                'direction': 'positive',
                'reason': 'AI semiconductor demand lifts entire tech sector',
            },
        ],
    }
    return article


@pytest.fixture
def sample_article_tier_a():
    """Tier A 뉴스 기사 (direct only)"""
    article = MagicMock()
    article.id = uuid.uuid4()
    article.title = "Apple upgrades iPhone camera"
    article.source = "CNBC"
    article.importance_score = 0.72
    article.published_at = timezone.now()
    article.llm_analysis = {
        'tier': 'A',
        'analyzed_at': timezone.now().isoformat(),
        'direct_impacts': [
            {
                'symbol': 'AAPL',
                'direction': 'bullish',
                'confidence': 0.8,
                'reason': 'Product improvement',
            },
        ],
    }
    return article


# ========================================
# Availability Tests
# ========================================

class TestAvailability:
    """Neo4j 연결 상태 관련 테스트"""

    def test_is_available_with_driver(self, sync_service):
        assert sync_service.is_available() is True

    def test_is_not_available_without_driver(self, unavailable_service):
        assert unavailable_service.is_available() is False


# ========================================
# Node Creation Tests
# ========================================

class TestNewsEventNodeCreation:
    """NewsEvent 노드 생성 테스트"""

    def test_create_news_event_node_success(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'article_id': 'test-id'}
        session.run.return_value = mock_result

        result = sync_service.create_news_event_node(
            article_id='test-id',
            title='Test article',
            source='Reuters',
            importance_score=0.9,
            tier='C',
            published_at=timezone.now(),
        )
        assert result is True
        session.run.assert_called_once()

    def test_create_news_event_node_no_record(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = None
        session.run.return_value = mock_result

        result = sync_service.create_news_event_node(
            article_id='test-id',
            title='Test',
            source='Reuters',
            importance_score=0.5,
            tier='A',
            published_at=timezone.now(),
        )
        assert result is False

    def test_create_news_event_node_unavailable(self, unavailable_service):
        result = unavailable_service.create_news_event_node(
            article_id='test-id',
            title='Test',
            source='Reuters',
            importance_score=0.5,
            tier='A',
            published_at=timezone.now(),
        )
        assert result is False

    def test_create_news_event_node_exception(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        session.run.side_effect = Exception("Connection error")

        result = sync_service.create_news_event_node(
            article_id='test-id',
            title='Test',
            source='Reuters',
            importance_score=0.5,
            tier='A',
            published_at=timezone.now(),
        )
        assert result is False

    def test_title_truncation(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'article_id': 'test'}
        session.run.return_value = mock_result

        long_title = "A" * 300
        sync_service.create_news_event_node(
            article_id='test',
            title=long_title,
            source='Reuters',
            importance_score=0.5,
            tier='A',
            published_at=timezone.now(),
        )
        call_kwargs = session.run.call_args
        assert len(call_kwargs.kwargs['title']) == 200


# ========================================
# Direct Impact Tests
# ========================================

class TestDirectImpact:
    """DIRECTLY_IMPACTS 관계 테스트"""

    def test_create_direct_impact_success(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'rel_type': 'DIRECTLY_IMPACTS'}
        session.run.return_value = mock_result

        result = sync_service.create_direct_impact(
            article_id='test-id',
            symbol='NVDA',
            direction='bullish',
            confidence=0.95,
            reason='Strong earnings',
        )
        assert result is True

    def test_create_direct_impact_symbol_uppercase(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'rel_type': 'DIRECTLY_IMPACTS'}
        session.run.return_value = mock_result

        sync_service.create_direct_impact(
            article_id='test-id',
            symbol='nvda',
            direction='bullish',
            confidence=0.9,
            reason='Test',
        )
        call_kwargs = session.run.call_args
        assert call_kwargs.kwargs['symbol'] == 'NVDA'

    def test_create_direct_impact_confidence_cap(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'rel_type': 'DIRECTLY_IMPACTS'}
        session.run.return_value = mock_result

        sync_service.create_direct_impact(
            article_id='test-id',
            symbol='NVDA',
            direction='bullish',
            confidence=1.5,  # 초과값
            reason='Test',
        )
        call_kwargs = session.run.call_args
        assert call_kwargs.kwargs['confidence'] == 1.0

    def test_create_direct_impact_unavailable(self, unavailable_service):
        result = unavailable_service.create_direct_impact(
            article_id='test', symbol='NVDA', direction='bullish',
            confidence=0.9, reason='Test',
        )
        assert result is False

    def test_create_direct_impact_exception(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        session.run.side_effect = Exception("DB error")

        result = sync_service.create_direct_impact(
            article_id='test', symbol='NVDA', direction='bullish',
            confidence=0.9, reason='Test',
        )
        assert result is False


# ========================================
# Indirect Impact Tests
# ========================================

class TestIndirectImpact:
    """INDIRECTLY_IMPACTS 관계 테스트"""

    def test_create_indirect_impact_success(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'rel_type': 'INDIRECTLY_IMPACTS'}
        session.run.return_value = mock_result

        result = sync_service.create_indirect_impact(
            article_id='test-id',
            symbol='AMD',
            direction='bullish',
            confidence=0.7,
            reason='Competitor benefits',
            chain_logic='NVDA → AI demand → AMD benefits',
        )
        assert result is True

    def test_create_indirect_impact_chain_logic_truncation(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'rel_type': 'INDIRECTLY_IMPACTS'}
        session.run.return_value = mock_result

        sync_service.create_indirect_impact(
            article_id='test',
            symbol='AMD',
            direction='bullish',
            confidence=0.7,
            reason='Test',
            chain_logic='X' * 2000,
        )
        call_kwargs = session.run.call_args
        assert len(call_kwargs.kwargs['chain_logic']) == 1000

    def test_create_indirect_impact_unavailable(self, unavailable_service):
        result = unavailable_service.create_indirect_impact(
            article_id='test', symbol='AMD', direction='bullish',
            confidence=0.7, reason='Test', chain_logic='Test',
        )
        assert result is False


# ========================================
# Opportunity Tests
# ========================================

class TestOpportunity:
    """CREATES_OPPORTUNITY 관계 테스트"""

    def test_create_opportunity_success(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'rel_type': 'CREATES_OPPORTUNITY'}
        session.run.return_value = mock_result

        result = sync_service.create_opportunity(
            article_id='test-id',
            symbol='ARM',
            thesis='AI boom benefits ARM licensing',
            timeframe='3-6 months',
            confidence=0.6,
        )
        assert result is True

    def test_create_opportunity_unavailable(self, unavailable_service):
        result = unavailable_service.create_opportunity(
            article_id='test', symbol='ARM', thesis='Test',
            timeframe='1 month', confidence=0.5,
        )
        assert result is False


# ========================================
# Sector Ripple Tests
# ========================================

class TestSectorRipple:
    """AFFECTS_SECTOR 관계 테스트"""

    def test_create_sector_ripple_success(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'rel_type': 'AFFECTS_SECTOR'}
        session.run.return_value = mock_result

        result = sync_service.create_sector_ripple(
            article_id='test-id',
            sector='Technology',
            direction='positive',
            reason='AI boom',
        )
        assert result is True

    def test_create_sector_ripple_unavailable(self, unavailable_service):
        result = unavailable_service.create_sector_ripple(
            article_id='test', sector='Technology',
            direction='positive', reason='Test',
        )
        assert result is False

    def test_create_sector_ripple_exception(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        session.run.side_effect = Exception("DB error")

        result = sync_service.create_sector_ripple(
            article_id='test', sector='Technology',
            direction='positive', reason='Test',
        )
        assert result is False


# ========================================
# Sync Article Tests
# ========================================

class TestSyncArticle:
    """단일 기사 동기화 테스트"""

    def test_sync_article_full(self, sync_service, mock_neo4j_driver, sample_article):
        """Tier C 기사 전체 동기화 (direct + indirect + opportunity + sector)"""
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'article_id': str(sample_article.id)}
        session.run.return_value = mock_result

        result = sync_service.sync_article(sample_article)

        assert result['nodes_created'] == 1
        # 1 direct + 1 indirect + 1 opportunity + 1 sector = 4
        assert result['relationships_created'] == 4
        assert result['errors'] == 0

    def test_sync_article_tier_a(self, sync_service, mock_neo4j_driver, sample_article_tier_a):
        """Tier A 기사 (direct only)"""
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'article_id': 'test'}
        session.run.return_value = mock_result

        result = sync_service.sync_article(sample_article_tier_a)

        assert result['nodes_created'] == 1
        assert result['relationships_created'] == 1  # direct only
        assert result['errors'] == 0

    def test_sync_article_no_analysis(self, sync_service):
        """llm_analysis가 None인 경우"""
        article = MagicMock()
        article.llm_analysis = None

        result = sync_service.sync_article(article)
        assert result == {'nodes_created': 0, 'relationships_created': 0, 'errors': 0}

    def test_sync_article_empty_analysis(self, sync_service, mock_neo4j_driver):
        """빈 분석 결과"""
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'article_id': 'test'}
        session.run.return_value = mock_result

        article = MagicMock()
        article.id = uuid.uuid4()
        article.title = "Test"
        article.source = "Test"
        article.importance_score = 0.5
        article.published_at = timezone.now()
        article.llm_analysis = {'tier': 'A', 'direct_impacts': []}

        result = sync_service.sync_article(article)
        assert result['nodes_created'] == 1
        assert result['relationships_created'] == 0

    def test_sync_article_unavailable(self, unavailable_service, sample_article):
        result = unavailable_service.sync_article(sample_article)
        assert result == {'nodes_created': 0, 'relationships_created': 0, 'errors': 0}

    def test_sync_article_node_creation_failure(self, sync_service, mock_neo4j_driver, sample_article):
        """노드 생성 실패 시 관계 생성 시도하지 않음"""
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = None  # 노드 생성 실패
        session.run.return_value = mock_result

        result = sync_service.sync_article(sample_article)
        assert result['nodes_created'] == 0
        assert result['errors'] == 1
        assert result['relationships_created'] == 0

    def test_sync_article_skip_empty_symbol(self, sync_service, mock_neo4j_driver):
        """빈 심볼은 스킵"""
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'article_id': 'test'}
        session.run.return_value = mock_result

        article = MagicMock()
        article.id = uuid.uuid4()
        article.title = "Test"
        article.source = "Test"
        article.importance_score = 0.5
        article.published_at = timezone.now()
        article.llm_analysis = {
            'tier': 'A',
            'direct_impacts': [
                {'symbol': '', 'direction': 'bullish', 'confidence': 0.9, 'reason': 'Test'},
                {'symbol': 'NVDA', 'direction': 'bullish', 'confidence': 0.9, 'reason': 'Test'},
            ],
        }

        result = sync_service.sync_article(article)
        assert result['relationships_created'] == 1  # 빈 심볼 제외


# ========================================
# Sync Batch Tests
# ========================================

@pytest.mark.django_db
class TestSyncBatch:
    """배치 동기화 테스트"""

    def test_sync_batch_unavailable(self, unavailable_service):
        result = unavailable_service.sync_batch()
        assert result['synced'] == 0
        assert result['skipped'] == 0

    def test_sync_batch_with_articles(self, mock_neo4j_driver):
        """실제 DB 기사를 모킹하여 배치 동기화"""
        driver, session = mock_neo4j_driver

        # Neo4j 세션 결과 모킹
        mock_result = MagicMock()
        mock_result.single.return_value = {'article_id': 'test'}
        session.run.return_value = mock_result

        # 기존 이벤트 ID 조회: 빈 set 반환
        with patch('news.services.news_neo4j_sync.get_neo4j_driver', return_value=driver):
            from news.services.news_neo4j_sync import NewsNeo4jSyncService
            service = NewsNeo4jSyncService()

            with patch.object(service, '_get_existing_event_ids', return_value=set()):
                # NewsArticle 쿼리 모킹
                mock_article = MagicMock()
                mock_article.id = uuid.uuid4()
                mock_article.title = "Test article"
                mock_article.source = "Reuters"
                mock_article.importance_score = 0.9
                mock_article.published_at = timezone.now()
                mock_article.llm_analysis = {
                    'tier': 'A',
                    'direct_impacts': [
                        {'symbol': 'AAPL', 'direction': 'bullish', 'confidence': 0.8, 'reason': 'Test'},
                    ],
                }

                with patch('news.models.NewsArticle') as MockArticle:
                    mock_qs = MagicMock()
                    mock_qs.filter.return_value = mock_qs
                    mock_qs.order_by.return_value = mock_qs
                    mock_qs.__getitem__ = MagicMock(return_value=[mock_article])
                    MockArticle.objects = mock_qs

                    result = service.sync_batch(max_articles=10)

                    assert result['synced'] == 1
                    assert result['total_nodes'] == 1
                    assert result['total_rels'] == 1

    def test_sync_batch_skips_existing(self, mock_neo4j_driver):
        """이미 동기화된 기사 스킵"""
        driver, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'article_id': 'test'}
        session.run.return_value = mock_result

        existing_id = uuid.uuid4()

        with patch('news.services.news_neo4j_sync.get_neo4j_driver', return_value=driver):
            from news.services.news_neo4j_sync import NewsNeo4jSyncService
            service = NewsNeo4jSyncService()

            with patch.object(service, '_get_existing_event_ids', return_value={str(existing_id)}):
                mock_article = MagicMock()
                mock_article.id = existing_id
                mock_article.llm_analysis = {'tier': 'A', 'direct_impacts': []}

                with patch('news.models.NewsArticle') as MockArticle:
                    mock_qs = MagicMock()
                    mock_qs.filter.return_value = mock_qs
                    mock_qs.order_by.return_value = mock_qs
                    mock_qs.__getitem__ = MagicMock(return_value=[mock_article])
                    MockArticle.objects = mock_qs

                    result = service.sync_batch()

                    assert result['skipped'] == 1
                    assert result['synced'] == 0


# ========================================
# Get Existing Event IDs Tests
# ========================================

class TestGetExistingEventIds:

    def test_get_existing_event_ids_success(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = [
            {'aid': 'id-1'},
            {'aid': 'id-2'},
            {'aid': 'id-3'},
        ]
        session.run.return_value = mock_result

        ids = sync_service._get_existing_event_ids()
        assert ids == {'id-1', 'id-2', 'id-3'}

    def test_get_existing_event_ids_empty(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        session.run.return_value = []

        ids = sync_service._get_existing_event_ids()
        assert ids == set()

    def test_get_existing_event_ids_unavailable(self, unavailable_service):
        ids = unavailable_service._get_existing_event_ids()
        assert ids == set()

    def test_get_existing_event_ids_exception(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        session.run.side_effect = Exception("DB error")

        ids = sync_service._get_existing_event_ids()
        assert ids == set()


# ========================================
# Reinforcement Tests
# ========================================

class TestReinforcement:
    """관계 강화 테스트"""

    def test_reinforce_relationships_success(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'reinforced_count': 5}
        session.run.return_value = mock_result

        result = sync_service.reinforce_relationships('NVDA', days=7)
        assert result == {'reinforced': 5}

    def test_reinforce_relationships_none(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = None
        session.run.return_value = mock_result

        result = sync_service.reinforce_relationships('NVDA')
        assert result == {'reinforced': 0}

    def test_reinforce_relationships_unavailable(self, unavailable_service):
        result = unavailable_service.reinforce_relationships('NVDA')
        assert result == {'reinforced': 0}

    def test_reinforce_relationships_exception(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        session.run.side_effect = Exception("DB error")

        result = sync_service.reinforce_relationships('NVDA')
        assert result == {'reinforced': 0}

    def test_reinforce_uses_correct_parameters(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'reinforced_count': 0}
        session.run.return_value = mock_result

        sync_service.reinforce_relationships('aapl', days=14)
        call_kwargs = session.run.call_args.kwargs
        assert call_kwargs['symbol'] == 'AAPL'
        assert call_kwargs['days'] == 14
        assert call_kwargs['threshold'] == 3
        assert call_kwargs['boost'] == 0.1


# ========================================
# Cleanup Tests
# ========================================

class TestCleanup:
    """만료 관계 정리 테스트"""

    def test_cleanup_expired_success(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver

        # 각 관계 타입별 삭제 결과 + orphan 삭제
        results = [
            MagicMock(single=MagicMock(return_value={'deleted': 3})),   # DIRECTLY_IMPACTS
            MagicMock(single=MagicMock(return_value={'deleted': 2})),   # INDIRECTLY_IMPACTS
            MagicMock(single=MagicMock(return_value={'deleted': 1})),   # CREATES_OPPORTUNITY
            MagicMock(single=MagicMock(return_value={'deleted': 0})),   # AFFECTS_SECTOR
            MagicMock(single=MagicMock(return_value={'deleted': 2})),   # Orphan nodes
        ]
        session.run.side_effect = results

        result = sync_service.cleanup_expired_relationships()
        assert result['deleted_relationships'] == 6  # 3+2+1+0
        assert result['deleted_nodes'] == 2

    def test_cleanup_unavailable(self, unavailable_service):
        result = unavailable_service.cleanup_expired_relationships()
        assert result == {'deleted_relationships': 0, 'deleted_nodes': 0}

    def test_cleanup_exception(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        session.run.side_effect = Exception("DB error")

        result = sync_service.cleanup_expired_relationships()
        assert result['deleted_relationships'] == 0
        assert result['deleted_nodes'] == 0


# ========================================
# Query: News Events for Symbol Tests
# ========================================

class TestGetNewsEventsForSymbol:
    """종목별 뉴스 이벤트 조회 테스트"""

    def test_get_events_success(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver

        mock_records = [
            {
                'article_id': 'id-1',
                'title': 'NVDA earnings beat',
                'source': 'Reuters',
                'importance_score': 0.95,
                'tier': 'C',
                'published_at': '2026-02-25T10:00:00Z',
                'relationship_type': 'DIRECTLY_IMPACTS',
                'direction': 'bullish',
                'confidence': 0.95,
                'reason': 'Strong earnings',
                'chain_logic': None,
                'thesis': None,
                'timeframe': None,
                'reinforced': True,
            },
            {
                'article_id': 'id-2',
                'title': 'AI demand surge',
                'source': 'Bloomberg',
                'importance_score': 0.88,
                'tier': 'B',
                'published_at': '2026-02-24T14:00:00Z',
                'relationship_type': 'INDIRECTLY_IMPACTS',
                'direction': 'bullish',
                'confidence': 0.7,
                'reason': 'Sector momentum',
                'chain_logic': 'AI demand → chip demand → NVDA',
                'thesis': None,
                'timeframe': None,
                'reinforced': False,
            },
        ]
        session.run.return_value = mock_records

        events = sync_service.get_news_events_for_symbol('NVDA', days=7)

        assert len(events) == 2
        assert events[0]['article_id'] == 'id-1'
        assert events[0]['relationship_type'] == 'DIRECTLY_IMPACTS'
        assert events[0]['reinforced'] is True
        assert events[1]['chain_logic'] == 'AI demand → chip demand → NVDA'

    def test_get_events_empty(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        session.run.return_value = []

        events = sync_service.get_news_events_for_symbol('XYZ', days=7)
        assert events == []

    def test_get_events_unavailable(self, unavailable_service):
        events = unavailable_service.get_news_events_for_symbol('NVDA')
        assert events == []

    def test_get_events_cached(self, sync_service, mock_neo4j_driver):
        """캐시 히트 테스트"""
        _, session = mock_neo4j_driver

        with patch('news.services.news_neo4j_sync.cache') as mock_cache:
            mock_cache.get.return_value = [{'article_id': 'cached'}]

            events = sync_service.get_news_events_for_symbol('NVDA')
            assert events == [{'article_id': 'cached'}]
            session.run.assert_not_called()

    def test_get_events_opportunity_fields(self, sync_service, mock_neo4j_driver):
        """CREATES_OPPORTUNITY 관계의 추가 필드"""
        _, session = mock_neo4j_driver
        mock_records = [
            {
                'article_id': 'id-3',
                'title': 'AI boom',
                'source': 'CNBC',
                'importance_score': 0.85,
                'tier': 'C',
                'published_at': '2026-02-25T10:00:00Z',
                'relationship_type': 'CREATES_OPPORTUNITY',
                'direction': None,
                'confidence': 0.6,
                'reason': None,
                'chain_logic': None,
                'thesis': 'ARM benefits from AI licensing',
                'timeframe': '3-6 months',
                'reinforced': False,
            },
        ]
        session.run.return_value = mock_records

        events = sync_service.get_news_events_for_symbol('ARM')
        assert events[0]['thesis'] == 'ARM benefits from AI licensing'
        assert events[0]['timeframe'] == '3-6 months'


# ========================================
# Query: Impact Map Tests
# ========================================

class TestGetImpactMap:
    """영향도 맵 조회 테스트"""

    def test_get_impact_map_success(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_records = [
            {
                'event_id': 'evt-1',
                'event_title': 'NVDA earnings',
                'event_score': 0.95,
                'tier': 'C',
                'rel_type': 'DIRECTLY_IMPACTS',
                'direction': 'bullish',
                'confidence': 0.95,
                'target_type': 'Stock',
                'target_id': 'NVDA',
                'target_name': 'NVIDIA',
            },
            {
                'event_id': 'evt-1',
                'event_title': 'NVDA earnings',
                'event_score': 0.95,
                'tier': 'C',
                'rel_type': 'AFFECTS_SECTOR',
                'direction': 'positive',
                'confidence': None,
                'target_type': 'Sector',
                'target_id': 'Technology',
                'target_name': 'Technology',
            },
        ]
        session.run.return_value = mock_records

        data = sync_service.get_impact_map(days=7)

        assert len(data['nodes']) == 3  # 1 event + 1 stock + 1 sector
        assert len(data['edges']) == 2
        assert data['stats']['total_events'] == 1
        assert data['stats']['total_stocks'] == 1
        assert data['stats']['total_sectors'] == 1

    def test_get_impact_map_empty(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        session.run.return_value = []

        data = sync_service.get_impact_map()
        assert data == {'nodes': [], 'edges': [], 'stats': {
            'total_events': 0, 'total_stocks': 0,
            'total_sectors': 0, 'total_relationships': 0,
        }}

    def test_get_impact_map_unavailable(self, unavailable_service):
        data = unavailable_service.get_impact_map()
        assert data == {'nodes': [], 'edges': [], 'stats': {}}

    def test_get_impact_map_cached(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver

        with patch('news.services.news_neo4j_sync.cache') as mock_cache:
            mock_cache.get.return_value = {'cached': True}

            data = sync_service.get_impact_map()
            assert data == {'cached': True}
            session.run.assert_not_called()


# ========================================
# Query: Symbol Impact Summary Tests
# ========================================

class TestGetSymbolImpactSummary:
    """종목 영향 요약 테스트"""

    def test_get_summary_success(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {
            'total_events': 5,
            'bullish': 3,
            'bearish': 1,
            'avg_confidence': 0.75432,
            'direct': 3,
            'indirect': 1,
            'opportunity': 1,
        }
        session.run.return_value = mock_result

        summary = sync_service.get_symbol_impact_summary('NVDA', days=7)

        assert summary['symbol'] == 'NVDA'
        assert summary['total_events'] == 5
        assert summary['bullish_count'] == 3
        assert summary['bearish_count'] == 1
        assert summary['avg_confidence'] == 0.754
        assert summary['direct_count'] == 3
        assert summary['indirect_count'] == 1
        assert summary['opportunity_count'] == 1

    def test_get_summary_no_record(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = None
        session.run.return_value = mock_result

        summary = sync_service.get_symbol_impact_summary('XYZ')
        assert summary['total_events'] == 0

    def test_get_summary_unavailable(self, unavailable_service):
        summary = unavailable_service.get_symbol_impact_summary('NVDA')
        assert summary['symbol'] == 'NVDA'
        assert summary['total_events'] == 0

    def test_get_summary_cached(self, sync_service, mock_neo4j_driver):
        _, session = mock_neo4j_driver

        with patch('news.services.news_neo4j_sync.cache') as mock_cache:
            mock_cache.get.return_value = {'symbol': 'NVDA', 'total_events': 10}

            summary = sync_service.get_symbol_impact_summary('NVDA')
            assert summary['total_events'] == 10
            session.run.assert_not_called()

    def test_get_summary_null_avg_confidence(self, sync_service, mock_neo4j_driver):
        """avg_confidence가 None인 경우"""
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {
            'total_events': 0,
            'bullish': 0,
            'bearish': 0,
            'avg_confidence': None,
            'direct': 0,
            'indirect': 0,
            'opportunity': 0,
        }
        session.run.return_value = mock_result

        summary = sync_service.get_symbol_impact_summary('XYZ')
        assert summary['avg_confidence'] == 0.0


# ========================================
# TTL Configuration Tests
# ========================================

class TestTTLConfiguration:
    """TTL 설정 테스트"""

    def test_ttl_values(self):
        from news.services.news_neo4j_sync import NewsNeo4jSyncService
        ttl = NewsNeo4jSyncService.RELATIONSHIP_TTL
        assert ttl['DIRECTLY_IMPACTS'] == 30
        assert ttl['INDIRECTLY_IMPACTS'] == 21
        assert ttl['CREATES_OPPORTUNITY'] == 14
        assert ttl['AFFECTS_SECTOR'] == 21

    def test_reinforcement_threshold(self):
        from news.services.news_neo4j_sync import NewsNeo4jSyncService
        assert NewsNeo4jSyncService.REINFORCEMENT_THRESHOLD == 3
        assert NewsNeo4jSyncService.REINFORCEMENT_BOOST == 0.1


# ========================================
# Celery Task Tests
# ========================================

class TestCeleryTasks:
    """Phase 3 Celery 태스크 테스트"""

    def test_sync_news_to_neo4j_task_success(self):
        with patch('news.services.news_neo4j_sync.get_neo4j_driver') as mock_driver:
            mock_driver.return_value = MagicMock()

            with patch('news.services.news_neo4j_sync.NewsNeo4jSyncService') as MockService:
                mock_instance = MagicMock()
                mock_instance.is_available.return_value = True
                mock_instance.sync_batch.return_value = {
                    'synced': 5, 'skipped': 2, 'errors': 0,
                    'total_nodes': 5, 'total_rels': 12,
                }
                MockService.return_value = mock_instance

                from news.tasks import sync_news_to_neo4j
                result = sync_news_to_neo4j(max_articles=50)

                assert result['synced'] == 5
                assert result['total_rels'] == 12

    def test_sync_news_to_neo4j_unavailable(self):
        with patch('news.services.news_neo4j_sync.get_neo4j_driver', return_value=None):
            from news.tasks import sync_news_to_neo4j
            result = sync_news_to_neo4j(max_articles=50)

            assert result['neo4j_unavailable'] is True
            assert result['synced'] == 0

    def test_cleanup_expired_task_success(self):
        with patch('news.services.news_neo4j_sync.get_neo4j_driver') as mock_driver:
            mock_driver.return_value = MagicMock()

            with patch('news.services.news_neo4j_sync.NewsNeo4jSyncService') as MockService:
                mock_instance = MagicMock()
                mock_instance.is_available.return_value = True
                mock_instance.cleanup_expired_relationships.return_value = {
                    'deleted_relationships': 10, 'deleted_nodes': 3,
                }
                MockService.return_value = mock_instance

                from news.tasks import cleanup_expired_news_relationships
                result = cleanup_expired_news_relationships()

                assert result['deleted_relationships'] == 10
                assert result['deleted_nodes'] == 3

    def test_cleanup_expired_unavailable(self):
        with patch('news.services.news_neo4j_sync.get_neo4j_driver', return_value=None):
            from news.tasks import cleanup_expired_news_relationships
            result = cleanup_expired_news_relationships()

            assert result['neo4j_unavailable'] is True


# ========================================
# API Endpoint Tests
# ========================================

@pytest.mark.django_db
class TestNewsEventsAPI:
    """뉴스 이벤트 API 엔드포인트 테스트"""

    def test_news_events_requires_symbol(self, client):
        """symbol 파라미터 필수"""
        response = client.get('/api/v1/news/news-events/')
        assert response.status_code == 400

    def test_news_events_success(self, client):
        """정상 요청"""
        with patch('news.services.news_neo4j_sync.NewsNeo4jSyncService') as MockService:
            mock_instance = MagicMock()
            mock_instance.get_news_events_for_symbol.return_value = []
            mock_instance.get_symbol_impact_summary.return_value = {
                'symbol': 'NVDA', 'total_events': 0,
                'bullish_count': 0, 'bearish_count': 0,
                'avg_confidence': 0.0, 'direct_count': 0,
                'indirect_count': 0, 'opportunity_count': 0,
            }
            MockService.return_value = mock_instance

            response = client.get('/api/v1/news/news-events/?symbol=NVDA')
            assert response.status_code == 200
            data = response.json()
            assert data['symbol'] == 'NVDA'
            assert 'events' in data
            assert 'summary' in data

    def test_news_events_days_cap(self, client):
        """days 최대 30일 제한"""
        with patch('news.services.news_neo4j_sync.NewsNeo4jSyncService') as MockService:
            mock_instance = MagicMock()
            mock_instance.get_news_events_for_symbol.return_value = []
            mock_instance.get_symbol_impact_summary.return_value = {
                'symbol': 'NVDA', 'total_events': 0,
                'bullish_count': 0, 'bearish_count': 0,
                'avg_confidence': 0.0, 'direct_count': 0,
                'indirect_count': 0, 'opportunity_count': 0,
            }
            MockService.return_value = mock_instance

            response = client.get('/api/v1/news/news-events/?symbol=NVDA&days=60')
            assert response.status_code == 200
            data = response.json()
            assert data['days'] == 30

    def test_impact_map_success(self, client):
        """영향도 맵 정상 요청"""
        with patch('news.services.news_neo4j_sync.NewsNeo4jSyncService') as MockService:
            mock_instance = MagicMock()
            mock_instance.get_impact_map.return_value = {
                'nodes': [], 'edges': [],
                'stats': {'total_events': 0, 'total_stocks': 0,
                          'total_sectors': 0, 'total_relationships': 0},
            }
            MockService.return_value = mock_instance

            response = client.get('/api/v1/news/news-events/impact-map/')
            assert response.status_code == 200
            data = response.json()
            assert 'nodes' in data
            assert 'edges' in data
            assert 'stats' in data


# ========================================
# Sector Ripple Propagation Tests
# ========================================

class TestSectorRipplePropagation:
    """propagate_sector_ripple() 2-hop 확산 테스트"""

    def test_propagate_sector_ripple_via_belongs_to(self, sync_service, mock_neo4j_driver):
        """BELONGS_TO 관계로 종목 찾기 후 INDIRECTLY_IMPACTS 생성"""
        _, session = mock_neo4j_driver

        # BELONGS_TO 쿼리에서 3개 종목 반환 (propagated > 0)
        mock_result = MagicMock()
        mock_result.single.return_value = {'propagated': 3}
        session.run.return_value = mock_result

        result = sync_service.propagate_sector_ripple(
            article_id='test-id',
            sector='Technology',
            direction='positive',
            confidence=0.8,
        )

        assert result['propagated'] == 3
        assert result['sector'] == 'Technology'
        # BELONGS_TO 쿼리만 1회 호출 (폴백 불필요)
        assert session.run.call_count == 1

    def test_propagate_sector_ripple_via_sector_property(self, sync_service, mock_neo4j_driver):
        """BELONGS_TO 실패(0) 후 sector 속성으로 폴백"""
        _, session = mock_neo4j_driver

        # 1차: BELONGS_TO 쿼리 → 0개 (폴백 유발)
        # 2차: sector 속성 쿼리 → 5개
        mock_result_empty = MagicMock()
        mock_result_empty.single.return_value = {'propagated': 0}

        mock_result_fallback = MagicMock()
        mock_result_fallback.single.return_value = {'propagated': 5}

        session.run.side_effect = [mock_result_empty, mock_result_fallback]

        result = sync_service.propagate_sector_ripple(
            article_id='test-id',
            sector='Technology',
            direction='positive',
            confidence=0.7,
        )

        assert result['propagated'] == 5
        assert result['sector'] == 'Technology'
        # 두 쿼리 모두 호출됨
        assert session.run.call_count == 2

    def test_propagate_sector_ripple_excludes_direct_impacts(self, sync_service, mock_neo4j_driver):
        """DIRECTLY_IMPACTS로 이미 연결된 종목은 제외하는 쿼리 전달 확인"""
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'propagated': 2}
        session.run.return_value = mock_result

        sync_service.propagate_sector_ripple(
            article_id='test-article',
            sector='Healthcare',
            direction='negative',
            confidence=0.6,
        )

        call_args = session.run.call_args
        query = call_args.args[0]
        # 쿼리에 DIRECTLY_IMPACTS 제외 로직이 포함됨
        assert 'DIRECTLY_IMPACTS' in query
        assert 'NOT EXISTS' in query

    def test_propagate_sector_ripple_max_limit(self, sync_service, mock_neo4j_driver):
        """MAX_RELATIONSHIPS_PER_NODE(20) 제한이 쿼리에 전달되는지 확인"""
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'propagated': 20}
        session.run.return_value = mock_result

        sync_service.propagate_sector_ripple(
            article_id='test-id',
            sector='Energy',
            direction='positive',
            confidence=0.9,
        )

        call_kwargs = session.run.call_args.kwargs
        assert call_kwargs['max_limit'] == 20

    def test_propagate_sector_ripple_confidence_decay(self, sync_service, mock_neo4j_driver):
        """confidence 0.4배 감쇠 확인"""
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'propagated': 1}
        session.run.return_value = mock_result

        original_confidence = 0.8
        sync_service.propagate_sector_ripple(
            article_id='test-id',
            sector='Financials',
            direction='positive',
            confidence=original_confidence,
        )

        call_kwargs = session.run.call_args.kwargs
        expected_decayed = round(original_confidence * 0.4, 4)
        assert call_kwargs['confidence'] == expected_decayed

    def test_propagate_sector_ripple_chain_logic_text(self, sync_service, mock_neo4j_driver):
        """chain_logic 텍스트가 섹터 이름을 포함하는지 확인"""
        _, session = mock_neo4j_driver
        mock_result = MagicMock()
        mock_result.single.return_value = {'propagated': 1}
        session.run.return_value = mock_result

        sector_name = 'Consumer Discretionary'
        sync_service.propagate_sector_ripple(
            article_id='test-id',
            sector=sector_name,
            direction='positive',
            confidence=0.5,
        )

        call_kwargs = session.run.call_args.kwargs
        assert sector_name in call_kwargs['chain_logic']
        assert sector_name in call_kwargs['reason']

    def test_propagate_sector_ripple_neo4j_unavailable(self, unavailable_service):
        """Neo4j 연결 불가 시 graceful 반환"""
        result = unavailable_service.propagate_sector_ripple(
            article_id='test-id',
            sector='Technology',
            direction='positive',
            confidence=0.8,
        )

        assert result == {'propagated': 0, 'sector': 'Technology'}

    def test_sync_article_calls_propagate_after_sector_ripple(self, mock_neo4j_driver):
        """sync_article에서 sector_ripple 처리 후 propagate_sector_ripple 호출 확인"""
        driver, session = mock_neo4j_driver

        with patch('news.services.news_neo4j_sync.get_neo4j_driver', return_value=driver):
            from news.services.news_neo4j_sync import NewsNeo4jSyncService
            service = NewsNeo4jSyncService()

            # session.run: 노드 생성, direct impact, sector ripple 모두 성공
            mock_result = MagicMock()
            mock_result.single.return_value = {'article_id': 'test', 'rel_type': 'OK', 'propagated': 2}
            session.run.return_value = mock_result

            # propagate_sector_ripple만 spy
            with patch.object(
                service, 'propagate_sector_ripple', return_value={'propagated': 2, 'sector': 'Technology'}
            ) as mock_propagate:
                article = MagicMock()
                article.id = uuid.uuid4()
                article.title = 'Test'
                article.source = 'Reuters'
                article.importance_score = 0.9
                article.published_at = timezone.now()
                article.llm_analysis = {
                    'tier': 'C',
                    'direct_impacts': [
                        {'symbol': 'NVDA', 'direction': 'bullish', 'confidence': 0.9, 'reason': 'Test'},
                    ],
                    'sector_ripple': [
                        {
                            'sector': 'Technology',
                            'direction': 'positive',
                            'reason': 'AI demand surge',
                            'confidence': 0.8,
                        },
                    ],
                }

                result = service.sync_article(article)

                mock_propagate.assert_called_once_with(
                    article_id=str(article.id),
                    sector='Technology',
                    direction='positive',
                    confidence=0.8,
                )
                # propagated 2개가 relationships_created에 더해짐
                assert result['relationships_created'] >= 3  # 1 direct + 1 sector + 2 propagated
