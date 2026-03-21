"""Builder State Models: LLM 기반 가설 빌더 상태 정의 (Phase A-MVP)"""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class BuilderMode(str, Enum):
    LLM = 'llm'
    WIZARD = 'wizard'


class BuilderPhase(str, Enum):
    PROPOSAL = 'proposal'
    PRESET = 'preset'
    CONFIRM = 'confirm'
    COMPLETE = 'complete'
    FALLBACK = 'fallback'


class FallbackReason(str, Enum):
    LLM_API_ERROR = 'llm_api_error'
    SCHEMA_PARSE_ERROR = 'schema_parse_error'
    VALIDATION_ERROR = 'validation_error'
    STATE_ERROR = 'state_error'


class ChatMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str


class IndicatorRecommendation(BaseModel):
    indicator_db_id: Optional[int] = None
    indicator_name: Optional[str] = None
    why: str = ''
    signal_type: str = 'coincident'  # leading / coincident / lagging


class PremiseData(BaseModel):
    title: str
    description: str = ''
    recommended_indicators: list[IndicatorRecommendation] = Field(default_factory=list)


class CollectedData(BaseModel):
    direction: Optional[str] = None
    target: Optional[str] = None
    target_type: Optional[str] = None
    thesis_type: list[str] = Field(default_factory=list)
    premises: list[PremiseData] = Field(default_factory=list)
    timeframe: Optional[str] = None
    magnitude: Optional[str] = None
    sensitivity: Optional[str] = None
    title: Optional[str] = None
    selected_indicator_ids: list[int] = Field(default_factory=list)


class ConversationState(BaseModel):
    conv_id: str
    entry_source: str = 'free_input'
    mode: BuilderMode = BuilderMode.LLM
    phase: BuilderPhase = BuilderPhase.PROPOSAL
    history: list[ChatMessage] = Field(default_factory=list)
    collected: CollectedData = Field(default_factory=CollectedData)
    turn_count: int = 0
    source_news_id: Optional[str] = None

    class Config:
        use_enum_values = True


# 유효한 가설 유형
VALID_THESIS_TYPES = {'earnings', 'flow', 'macro', 'chain', 'event'}

# 모니터링 프리셋
MONITORING_PRESETS = {
    'short': {
        'timeframe': '1개월 이내',
        'magnitude': '살짝 조정',
        'sensitivity': 'high',
        'label': '⚡ 단기 (1개월)',
        'description': '빠른 변화 감지, 민감한 알림',
    },
    'medium': {
        'timeframe': '1~3개월',
        'magnitude': '꽤 빠진다',
        'sensitivity': 'medium',
        'label': '📈 중기 (1~3개월)',
        'description': '균형 잡힌 추적, 적당한 알림',
    },
    'long': {
        'timeframe': '6개월~1년',
        'magnitude': '크게 빠진다',
        'sensitivity': 'low',
        'label': '🔭 장기 (6개월+)',
        'description': '느긋한 추적, 중요 변화만 알림',
    },
}
