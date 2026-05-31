from .aggregator import NewsAggregatorService
from .circuit_breaker import CircuitBreaker
from .deduplicator import NewsDeduplicator
from .interest_options import InterestOptionsService
from .keyword_extractor import NewsKeywordExtractor
from .market_feed import MarketFeedService
from .ml_label_collector import MLLabelCollector
from .ml_production_manager import MLProductionManager

# NewsNeo4jSyncService — lazy import (neo4j C 확장 fork SIGSEGV 방지)
from .ml_weight_optimizer import MLWeightOptimizer
from .news_classifier import NewsClassifier
from .news_deep_analyzer import NewsDeepAnalyzer
from .personalized_feed import PersonalizedFeedService
from .sentiment_normalizer import SentimentNormalizer
from .stock_insights import NewsBasedStockInsights
from .stock_recommender import NewsBasedStockRecommender

# Neo4j 전이 import를 lazy로 처리 (Celery fork pool SIGSEGV 방지)
_LAZY_NEO4J_IMPORTS = {
    "NewsNeo4jSyncService": "news_neo4j_sync",
}


def __getattr__(name):
    if name in _LAZY_NEO4J_IMPORTS:
        import importlib

        module = importlib.import_module(f".{_LAZY_NEO4J_IMPORTS[name]}", __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "NewsAggregatorService",
    "NewsDeduplicator",
    "NewsKeywordExtractor",
    "NewsBasedStockRecommender",
    "NewsBasedStockInsights",
    "MarketFeedService",
    "InterestOptionsService",
    "PersonalizedFeedService",
    "NewsClassifier",
    "NewsDeepAnalyzer",
    "MLLabelCollector",
    "NewsNeo4jSyncService",
    "MLWeightOptimizer",
    "MLProductionManager",
    "CircuitBreaker",
    "SentimentNormalizer",
]
