"""
RAG Analysis Services

Neo4j 관련 import는 lazy로 처리하여 Celery fork pool worker에서
C 확장이 로드되지 않도록 합니다 (SIGSEGV 방지).
"""

from .cache import get_cache_service, BasicCacheService

# Neo4j imports — lazy via __getattr__ (fork pool SIGSEGV 방지)
# neo4j C 확장을 전이적으로 import하는 모듈도 모두 포함
_LAZY_IMPORTS = {
    # neo4j_driver
    'get_neo4j_driver': 'neo4j_driver',
    'close_neo4j_driver': 'neo4j_driver',
    'reset_connection': 'neo4j_driver',
    'force_reset_after_fork': 'neo4j_driver',
    # neo4j_service
    'get_neo4j_service': 'neo4j_service',
    'Neo4jServiceLite': 'neo4j_service',
    'reset_neo4j_service': 'neo4j_service',
    # graphrag_scorer (neo4j_service 전이 import)
    'GraphRAGScorer': 'graphrag_scorer',
    'ScoringWeights': 'graphrag_scorer',
    'get_graphrag_scorer': 'graphrag_scorer',
    # semantic_cache (neo4j_driver 전이 import)
    'SemanticCacheService': 'semantic_cache',
    'get_semantic_cache': 'semantic_cache',
    # semantic_cache_setup (neo4j_driver 전이 import)
    'setup_semantic_cache_index': 'semantic_cache_setup',
    'cleanup_expired_cache': 'semantic_cache_setup',
    'get_cache_stats': 'semantic_cache_setup',
    'drop_semantic_cache_index': 'semantic_cache_setup',
    # cache_warmer (semantic_cache 전이 import)
    'CacheWarmer': 'cache_warmer',
    'run_cache_warming_sync': 'cache_warmer',
}


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        import importlib
        module = importlib.import_module(f'.{_LAZY_IMPORTS[name]}', __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Search services (sentence-transformers, rank-bm25 필요)
# graphrag_scorer는 neo4j를 전이 import하므로 위 _LAZY_IMPORTS로 이동
try:
    from .vector_search import VectorSearchService, get_vector_search_service
    from .bm25_search import BM25SearchService, get_bm25_search_service
    from .hybrid_search import (
        HybridSearchService,
        get_hybrid_search_service,
        SearchWeights,
        MetadataFilterBuilder
    )
    from .reranker import (
        CrossEncoderReranker,
        RerankerWithThreshold,
        get_reranker
    )
    _search_available = True
except ImportError:
    _search_available = False

# Optional imports (LLM 서비스는 anthropic 패키지 필요)
try:
    from .context import DateAwareContextFormatter
    from .llm_service import LLMServiceLite, ResponseParser
    from .pipeline import AnalysisPipelineLite, AnalysisPipelineFinal
    from .entity_extractor import EntityExtractor, EntityNormalizer, ExtractedEntities
    from .context_compressor import ContextCompressor, QuestionAwareCompressor, get_context_compressor
    from .pipeline_v2 import AnalysisPipelineV2, PipelineV2EventType
    _llm_available = True
except ImportError:
    _llm_available = False

# Semantic Cache (Phase 3) — neo4j 전이 import → _LAZY_IMPORTS로 이동

__all__ = [
    'get_neo4j_driver',
    'close_neo4j_driver',
    'reset_connection',
    'get_neo4j_service',
    'Neo4jServiceLite',
    'get_cache_service',
    'BasicCacheService',
    'GraphRAGScorer',
    'ScoringWeights',
    'get_graphrag_scorer',
    'SemanticCacheService',
    'get_semantic_cache',
    'setup_semantic_cache_index',
    'cleanup_expired_cache',
    'get_cache_stats',
    'drop_semantic_cache_index',
    'CacheWarmer',
    'run_cache_warming_sync',
]

if _search_available:
    __all__.extend([
        'VectorSearchService',
        'get_vector_search_service',
        'BM25SearchService',
        'get_bm25_search_service',
        'HybridSearchService',
        'get_hybrid_search_service',
        'SearchWeights',
        'MetadataFilterBuilder',
        'CrossEncoderReranker',
        'RerankerWithThreshold',
        'get_reranker',
    ])

if _llm_available:
    __all__.extend([
        'DateAwareContextFormatter',
        'LLMServiceLite',
        'ResponseParser',
        'AnalysisPipelineLite',
        'AnalysisPipelineFinal',
        'EntityExtractor',
        'EntityNormalizer',
        'ExtractedEntities',
        'ContextCompressor',
        'QuestionAwareCompressor',
        'get_context_compressor',
        'AnalysisPipelineV2',
        'PipelineV2EventType',
    ])

# Cost Tracker
try:
    from .cost_tracker import CostTracker, get_cost_tracker
    _cost_tracker_available = True
except ImportError:
    _cost_tracker_available = False

if _cost_tracker_available:
    __all__.extend([
        'CostTracker',
        'get_cost_tracker',
    ])

# Cost Optimization (Phase 3 Week 3)
try:
    from .complexity_classifier import (
        ComplexityClassifier,
        QuestionComplexity,
        QuestionAnalyzer,
        get_complexity_classifier
    )
    from .adaptive_llm_service import (
        AdaptiveLLMService,
        get_adaptive_llm_service
    )
    from .token_budget_manager import (
        TokenBudgetManager,
        DynamicBudgetManager,
        ContentBlock,
        ContentPriority,
        get_token_budget_manager,
        get_dynamic_budget_manager
    )
    _cost_optimization_available = True
except ImportError:
    _cost_optimization_available = False

if _cost_optimization_available:
    __all__.extend([
        'ComplexityClassifier',
        'QuestionComplexity',
        'QuestionAnalyzer',
        'get_complexity_classifier',
        'AdaptiveLLMService',
        'get_adaptive_llm_service',
        'TokenBudgetManager',
        'DynamicBudgetManager',
        'ContentBlock',
        'ContentPriority',
        'get_token_budget_manager',
        'get_dynamic_budget_manager',
    ])
