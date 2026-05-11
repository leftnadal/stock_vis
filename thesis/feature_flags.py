"""Feature Flags: LLM 빌더 기능 플래그 (Phase A~C)"""

FEATURE_FLAGS = {
    'LLM_BUILDER_ENABLED': True,
    'INDICATOR_CONTEXT_ENABLED': True,
    'KEYWORD_HINTS_ENABLED': False,
    'CHAIN_KEYWORDS_ENABLED': False,
    'EOD_KEYWORDS_ENABLED': False,
    'NEWS_KEYWORDS_ENABLED': False,
    'MINI_DASHBOARD_PREVIEW': False,
    'GUIDED_SUGGESTION': False,
    'MULTI_TURN_EDIT': False,
    'STREAMING_RESPONSE': False,
    'NEWS_SUGGESTIONS_ENABLED': True,
}


def get_feature_flags():
    """현재 활성 플래그 반환."""
    return FEATURE_FLAGS.copy()
