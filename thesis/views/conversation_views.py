"""Conversation Views: 대화형 가설 빌더 API"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from thesis.serializers import ConversationStartSerializer, ConversationResponseSerializer
from thesis.services.thesis_builder import start_conversation, process_response

# conversation_state 허용 필드 (조작 방지)
ALLOWED_STATE_KEYS = {'conv_id', 'entry_source', 'step', 'collected', 'source_news_id'}
ALLOWED_ENTRY_SOURCES = {'news', 'free_input', 'popular', 'template', 'chainsight'}
MAX_STEP = 10


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


class ConversationStartView(APIView):
    """POST /conversation/start/ → 대화 시작."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConversationStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = start_conversation(
            entry_source=serializer.validated_data['entry_source'],
            source_news_id=serializer.validated_data.get('source_news_id'),
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
        sanitized_state = _sanitize_conversation_state(raw_state)
        if sanitized_state is None:
            return Response(
                {'error': '잘못된 대화 상태입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = process_response(
            conversation_state=sanitized_state,
            user_input=serializer.validated_data['user_input'],
            user=request.user,
        )
        return Response(result)
