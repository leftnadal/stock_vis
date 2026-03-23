"""Conversation Views: 대화형 가설 빌더 API (wizard + LLM 모드)"""

import json
import logging
from datetime import timedelta

from django.utils import timezone
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


class NewsIssuesView(APIView):
    """GET /conversation/news-issues/ → 최근 뉴스를 한국어 이슈로 변환."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from news.models import NewsArticle

        cutoff = timezone.now() - timedelta(days=7)
        articles = (
            NewsArticle.objects.filter(published_at__gte=cutoff)
            .order_by('-published_at')[:12]
        )

        if not articles:
            return Response({'issues': []})

        # Gemini로 한국어 이슈 변환
        titles = [{'id': str(a.id), 'title': a.title, 'url': a.url or ''} for a in articles]
        issues = self._convert_to_korean_issues(titles)

        return Response({'issues': issues})

    def _convert_to_korean_issues(self, titles):
        """뉴스 제목 목록 → Gemini 한국어 이슈 변환 (1회 호출)."""
        import re
        from django.conf import settings

        try:
            from google import genai
            from google.genai import types

            api_key = (
                getattr(settings, 'GOOGLE_AI_API_KEY', None)
                or getattr(settings, 'GEMINI_API_KEY', None)
            )
            if not api_key:
                return self._fallback_issues(titles)

            client = genai.Client(api_key=api_key)

            title_list = '\n'.join(
                f'{i+1}. {t["title"][:80]}' for i, t in enumerate(titles[:8])
            )

            prompt = f"""아래 영문 뉴스 제목들을 한국어 투자 이슈로 변환해줘.

{title_list}

각 뉴스에 대해 다음 JSON 배열로 반환해:
[
  {{"index": 1, "keyword": "핵심 키워드 (15자 이내)", "summary": "한 줄 요약 (40자 이내)", "sentiment": "positive" 또는 "negative" 또는 "neutral"}}
]

규칙:
- keyword는 투자자가 바로 이해할 수 있는 한국어 핵심 키워드
- summary는 투자 관점에서 의미 있는 한 줄 요약
- 같은 주제의 뉴스는 하나로 합쳐서
- 투자와 무관한 뉴스는 제외
- 최대 6개만

JSON만 반환해."""

            config = types.GenerateContentConfig(
                max_output_tokens=1000,
                temperature=0.2,
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            )

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config,
            )

            text = response.text if hasattr(response, 'text') and response.text else ''
            if not text:
                return self._fallback_issues(titles)

            parsed = json.loads(text)
            if not isinstance(parsed, list):
                return self._fallback_issues(titles)

            # 원본 뉴스의 id/url 매핑
            result = []
            for item in parsed[:6]:
                idx = item.get('index', 1) - 1
                if 0 <= idx < len(titles):
                    original = titles[idx]
                    result.append({
                        'id': original['id'],
                        'keyword': item.get('keyword', '')[:20],
                        'summary': item.get('summary', '')[:60],
                        'sentiment': item.get('sentiment', 'neutral'),
                        'url': original.get('url', ''),
                        'source': 'news',
                    })
            return result

        except Exception as e:
            logger.exception(f"Gemini news issue conversion failed: {e}")
            return self._fallback_issues(titles)

    def _fallback_issues(self, titles):
        """Gemini 실패 시 제목 기반 fallback."""
        return [
            {
                'id': t['id'],
                'keyword': t['title'][:20],
                'summary': t['title'][:60],
                'sentiment': 'neutral',
                'url': t.get('url', ''),
                'source': 'news',
            }
            for t in titles[:6]
        ]
