"""
RAG Analysis Services
"""

from .neo4j_driver import get_neo4j_driver, close_neo4j_driver, reset_connection
from .neo4j_service import get_neo4j_service, Neo4jServiceLite
from .cache import get_cache_service, BasicCacheService

# Search services (sentence-transformers, rank-bm25 필요)
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
    from .graphrag_scorer import (
        GraphRAGScorer,
        ScoringWeights,
        get_graphrag_scorer
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

# Semantic Cache (Phase 3)
try:
    from .semantic_cache import SemanticCacheService, get_semantic_cache
    from .semantic_cache_setup import (
        setup_semantic_cache_index,
        cleanup_expired_cache,
        get_cache_stats,
        drop_semantic_cache_index
    )
    from .cache_warmer import CacheWarmer, run_cache_warming_sync
    _semantic_cache_available = True
except ImportError:
    _semantic_cache_available = False

__all__ = [
    'get_neo4j_driver',
    'close_neo4j_driver',
    'reset_connection',
    'get_neo4j_service',
    'Neo4jServiceLite',
    'get_cache_service',
    'BasicCacheService',
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
        'GraphRAGScorer',
        'ScoringWeights',
        'get_graphrag_scorer',
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

if _semantic_cache_available:
    __all__.extend([
        'SemanticCacheService',
        'get_semantic_cache',
        'setup_semantic_cache_index',
        'cleanup_expired_cache',
        'get_cache_stats',
        'drop_semantic_cache_index',
        'CacheWarmer',
        'run_cache_warming_sync',
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
