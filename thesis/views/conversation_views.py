"""Conversation Views: 대화형 가설 빌더 API (wizard + LLM 모드)"""

import json
import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thesis.serializers import ConversationStartSerializer, ConversationResponseSerializer
from thesis.services.thesis_builder import (
    start_conversation, process_response,
    start_llm_conversation, process_llm_turn,
)
from thesis.feature_flags import get_feature_flags

logger = logging.getLogger(__name__)

# wizard conversation_state 허용 필드 (조작 방지)
ALLOWED_STATE_KEYS = {'conv_id', 'entry_source', 'step', 'collected', 'source_news_id'}
ALLOWED_ENTRY_SOURCES = {'news', 'free_input', 'popular', 'template', 'chainsight'}
MAX_STEP = 10

# LLM state 허용 필드
LLM_STATE_KEYS = {
    'conv_id', 'entry_source', 'mode', 'phase', 'history',
    'collected', 'turn_count', 'source_news_id',
}
MAX_HISTORY_LENGTH = 20
MAX_STATE_SIZE = 50_000  # bytes


def _sanitize_conversation_state(state):
    """클라이언트가 보낸 conversation_state를 검증/정제."""
    if not isinstance(state, dict):
        return None

    # 허용되지 않은 키 제거
    sanitized = {k: v for k, v in state.items() if k in ALLOWED_STATE_KEYS}

    # entry_source 검증
    if sanitized.get('entry_source') not in ALLOWED_ENTRY_SOURCES:
        return None

    # step 범위 검증
    step = sanitized.get('step')
    if not isinstance(step, int) or step < 1 or step > MAX_STEP:
        return None

    # collected 검증: dict여야 하고, 값은 str/list/dict/bool/None만 허용
    collected = sanitized.get('collected')
    if collected is not None:
        if not isinstance(collected, dict):
            return None
        # collected 내부의 키는 문자열, 값은 기본 타입만 허용
        ALLOWED_COLLECTED_KEYS = {
            'direction', 'premises', 'timeframe', 'magnitude',
            'news_title', 'raw_text', 'parsed', 'title',
            'recommended_indicators', 'create_counter_thesis',
            'neutral_resolved', 'source_news_id',
        }
        sanitized['collected'] = {
            k: v for k, v in collected.items()
            if isinstance(k, str) and k in ALLOWED_COLLECTED_KEYS
        }

    return sanitized


def _sanitize_llm_state(state):
    """LLM 모드 conversation_state 검증."""
    if not isinstance(state, dict):
        return None

    # 크기 제한
    state_json = json.dumps(state, default=str)
    if len(state_json) > MAX_STATE_SIZE:
        return None

    # 허용 키만
    sanitized = {k: v for k, v in state.items() if k in LLM_STATE_KEYS}

    # entry_source 검증
    if sanitized.get('entry_source') not in ALLOWED_ENTRY_SOURCES:
        return None

    # mode 검증
    if sanitized.get('mode') != 'llm':
        return None

    # history 길이 제한
    history = sanitized.get('history', [])
    if isinstance(history, list) and len(history) > MAX_HISTORY_LENGTH:
        sanitized['history'] = history[-MAX_HISTORY_LENGTH:]

    # turn_count 검증
    turn_count = sanitized.get('turn_count', 0)
    if not isinstance(turn_count, int) or turn_count < 0 or turn_count > 50:
        return None

    return sanitized


def _detect_mode(state):
    """conversation_state에서 mode 탐지."""
    if isinstance(state, dict) and state.get('mode') == 'llm':
        return 'llm'
    return 'wizard'


class ConversationStartView(APIView):
    """POST /conversation/start/ → 대화 시작."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConversationStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry_source = serializer.validated_data['entry_source']
        source_news_id = serializer.validated_data.get('source_news_id')

        # LLM 모드 활성 시 LLM 빌더 사용
        flags = get_feature_flags()
        if flags.get('LLM_BUILDER_ENABLED'):
            result = start_llm_conversation(
                entry_source=entry_source,
                source_news_id=source_news_id,
            )
            return Response(result)

        # wizard 모드 (기존)
        result = start_conversation(
            entry_source=entry_source,
            source_news_id=source_news_id,
            user=request.user,
        )
        return Response(result)


class ConversationRespondView(APIView):
    """POST /conversation/respond/ → 사용자 응답 처리."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConversationResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        raw_state = serializer.validated_data['conversation_state']
        user_input = serializer.validated_data['user_input']
        mode = _detect_mode(raw_state)

        if mode == 'llm':
            # LLM 모드
            sanitized_state = _sanitize_llm_state(raw_state)
            if sanitized_state is None:
                return Response(
                    {'error': '잘못된 대화 상태입니다.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            result = process_llm_turn(
                raw_state=sanitized_state,
                user_input=user_input,
                user=request.user,
            )
            return Response(result)

        # wizard 모드 (기존)
        sanitized_state = _sanitize_conversation_state(raw_state)
        if sanitized_state is None:
            return Response(
                {'error': '잘못된 대화 상태입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = process_response(
            conversation_state=sanitized_state,
            user_input=user_input,
            user=request.user,
        )
        return Response(result)
