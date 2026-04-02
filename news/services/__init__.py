from .aggregator import NewsAggregatorService
from .deduplicator import NewsDeduplicator
from .keyword_extractor import NewsKeywordExtractor
from .stock_recommender import NewsBasedStockRecommender
from .stock_insights import NewsBasedStockInsights
from .market_feed import MarketFeedService
from .interest_options import InterestOptionsService
from .personalized_feed import PersonalizedFeedService
from .news_classifier import NewsClassifier
from .news_deep_analyzer import NewsDeepAnalyzer
from .ml_label_collector import MLLabelCollector
# NewsNeo4jSyncService — lazy import (neo4j C 확장 fork SIGSEGV 방지)
from .ml_weight_optimizer import MLWeightOptimizer
from .ml_production_manager import MLProductionManager
from .circuit_breaker import CircuitBreaker
from .sentiment_normalizer import SentimentNormalizer

# Neo4j 전이 import를 lazy로 처리 (Celery fork pool SIGSEGV 방지)
_LAZY_NEO4J_IMPORTS = {
    'NewsNeo4jSyncService': 'news_neo4j_sync',
}


def __getattr__(name):
    if name in _LAZY_NEO4J_IMPORTS:
        import importlib
        module = importlib.import_module(f'.{_LAZY_NEO4J_IMPORTS[name]}', __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'NewsAggregatorService',
    'NewsDeduplicator',
    'NewsKeywordExtractor',
    'NewsBasedStockRecommender',
    'NewsBasedStockInsights',
    'MarketFeedService',
    'InterestOptionsService',
    'PersonalizedFeedService',
    'NewsClassifier',
    'NewsDeepAnalyzer',
    'MLLabelCollector',
    'NewsNeo4jSyncService',
    'MLWeightOptimizer',
    'MLProductionManager',
    'CircuitBreaker',
    'SentimentNormalizer',
]
