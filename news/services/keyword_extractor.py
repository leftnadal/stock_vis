"""
뉴스 키워드 추출 서비스 (Phase 2)

Gemini 2.5 Flash를 사용하여 일일 뉴스에서 핵심 키워드를 추출합니다.
"""

import json
import logging
import re
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from google import genai
from google.genai import types

from ..models import DailyNewsKeyword, NewsArticle

logger = logging.getLogger(__name__)


class NewsKeywordExtractor:
    """
    LLM 기반 뉴스 키워드 추출 서비스

    Features:
    - Gemini 2.5 Flash 사용 (저비용, 빠른 응답)
    - 일일 뉴스 요약 및 핵심 키워드 추출
    - 키워드별 감성 분석 및 관련 종목 매핑
    - 폴백 키워드 제공 (LLM 실패 시)
    """

    MODEL = "gemini-2.5-flash"
    MAX_OUTPUT_TOKENS = 6000  # 충분한 응답 토큰 (한국어는 토큰 소비가 많음)
    TEMPERATURE = 0.3  # 일관된 키워드 생성
    MAX_NEWS_PER_REQUEST = 100  # 한 번에 처리할 최대 뉴스 수

    # 기본 키워드 (LLM 실패 시)
    FALLBACK_KEYWORDS = [
        {"text": "시장 동향", "sentiment": "neutral", "related_symbols": [], "reason": "전반적인 시장 흐름을 확인하세요"},
        {"text": "거래량 증가", "sentiment": "neutral", "related_symbols": [], "reason": "주요 종목의 거래량 변화를 주시하세요"},
        {"text": "변동성 확대", "sentiment": "neutral", "related_symbols": [], "reason": "시장 변동성이 높아 주의가 필요합니다"},
    ]

    def __init__(self, language: str = "ko"):
        """
        Args:
            language: 키워드 언어 ('ko' 또는 'en')
        """
        self.language = language

        # Gemini API 클라이언트 초기화
        api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError(
                "GOOGLE_AI_API_KEY 또는 GEMINI_API_KEY가 설정되지 않았습니다."
            )
        self.client = genai.Client(api_key=api_key)

    def extract_daily_keywords(
        self,
        target_date: Optional[date] = None,
        force: bool = False
    ) -> DailyNewsKeyword:
        """
        특정 날짜의 뉴스에서 키워드 추출

        Args:
            target_date: 추출 대상 날짜 (기본: 오늘)
            force: 기존 키워드 덮어쓰기 여부

        Returns:
            DailyNewsKeyword: 추출된 키워드 모델
        """
        if target_date is None:
            target_date = timezone.now().date()

        # 이미 추출된 키워드가 있는지 확인
        existing = DailyNewsKeyword.objects.filter(date=target_date).first()
        if existing and existing.status == 'completed' and not force:
            logger.info(f"Keywords already exist for {target_date}")
            return existing

        # 해당 날짜의 뉴스 조회
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        # timezone aware로 변환
        if timezone.is_naive(start_datetime):
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)

        # 기본 쿼리 (슬라이스 전)
        base_query = NewsArticle.objects.filter(
            published_at__gte=start_datetime,
            published_at__lte=end_datetime
        )

        # 전체 건수 확인
        total_count = base_query.count()
        if total_count == 0:
            logger.warning(f"No news found for {target_date}")
            return self._create_or_update_keyword(
                target_date,
                status='failed',
                error_message='No news found for this date'
            )

        # 소스별 건수 집계 (슬라이스 전에 수행)
        sources_count = {}
        finnhub_count = base_query.filter(finnhub_id__isnull=False).count()
        marketaux_count = base_query.filter(marketaux_uuid__isnull=False).exclude(marketaux_uuid='').count()
        if finnhub_count:
            sources_count['finnhub'] = finnhub_count
        if marketaux_count:
            sources_count['marketaux'] = marketaux_count

        # 슬라이스하여 articles 가져오기
        articles = base_query.order_by('-published_at')[:self.MAX_NEWS_PER_REQUEST]

        # 뉴스 데이터 준비
        news_data = self._prepare_news_data(articles)

        # LLM 호출
        start_time = time.time()
        try:
            keywords = self._call_llm(news_data, target_date)
            generation_time_ms = int((time.time() - start_time) * 1000)

            return self._create_or_update_keyword(
                target_date,
                keywords=keywords,
                total_news_count=articles.count(),
                sources=sources_count,
                status='completed',
                generation_time_ms=generation_time_ms
            )

        except Exception as e:
            logger.exception(f"Failed to extract keywords: {e}")
            generation_time_ms = int((time.time() - start_time) * 1000)

            return self._create_or_update_keyword(
                target_date,
                keywords=self.FALLBACK_KEYWORDS,
                total_news_count=articles.count(),
                sources=sources_count,
                status='failed',
                error_message=str(e),
                generation_time_ms=generation_time_ms
            )

    def _prepare_news_data(self, articles) -> List[Dict]:
        """뉴스 데이터를 LLM 입력 형식으로 변환"""
        news_list = []
        for article in articles:
            # 관련 종목 추출
            symbols = list(article.entities.values_list('symbol', flat=True)[:5])

            news_list.append({
                'title': article.title,
                'summary': article.summary[:300] if article.summary else '',  # 요약 길이 제한
                'source': article.source,
                'category': article.category,
                'sentiment_score': float(article.sentiment_score) if article.sentiment_score else None,
                'symbols': symbols
            })
        return news_list

    def _call_llm(self, news_data: List[Dict], target_date: date) -> List[Dict]:
        """LLM 호출하여 키워드 추출"""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(news_data, target_date)

        # 동기 API 호출 (Celery 호환)
        response = self.client.models.generate_content(
            model=self.MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=self.MAX_OUTPUT_TOKENS,
                temperature=self.TEMPERATURE,
            ),
        )

        response_text = response.text
        logger.debug(f"LLM response: {response_text}")

        # JSON 파싱
        keywords = self._parse_response(response_text)
        return keywords

    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 구성"""
        return """당신은 금융 뉴스 분석 전문가입니다.
주어진 뉴스 목록을 분석하여 오늘 시장의 핵심 키워드를 추출합니다.

## 규칙:
1. 정확히 10개의 키워드를 추출하세요
2. 각 키워드는 다음 형식을 따르세요:
   - text: 핵심 문구 (25자 이내, 한국어)
     ★ 반드시 "주어/목적어 + 동사" 구조로 작성하세요.
     ✅ 좋은 예: "NVDA 실적 기대 상회", "Fed 금리 동결 시사", "테슬라 중국 판매 급증", "반도체 재고 바닥 확인"
     ❌ 나쁜 예: "AI 반도체", "금리 인하", "실적 발표" (명사만 나열 금지)
   - sentiment: "positive", "negative", "neutral" 중 하나만 사용
   - related_symbols: 관련 종목 심볼 리스트 (최대 3개) - 가능한 한 관련 종목을 찾아 포함하세요!
   - importance: 중요도 (0.0 ~ 1.0)
   - reason: 이 키워드가 왜 중요한지 투자자 관점에서 1-2문장 설명 (50자 이내)
     예: "NVDA 실적 발표 임박, AI 칩 수요 지속 확인 기대"
     예: "Fed 의사록 공개 예정, 금리 인하 시점 단서 주목"
3. 키워드는 중요도 순으로 정렬하세요
4. 다양한 주제를 다루세요 (섹터, 이슈, 트렌드 등)
5. 반드시 완전한 JSON 배열 형식으로 응답하세요

## 중요 - related_symbols 가이드:
- 뉴스에서 언급된 종목 심볼을 적극적으로 포함하세요
- 직접 언급되지 않아도, 키워드와 관련된 대표 종목을 추론하세요
- 예: "AI 반도체 수요 급증" → NVDA, AMD, INTC
- 예: "테슬라 자율주행 승인" → TSLA, RIVN, NIO
- 예: "빅테크 실적 하회" → AAPL, MSFT, GOOGL, META
- 예: "비트코인 10만불 돌파" → COIN, MSTR, RIOT
- 최소 7개 이상의 키워드에 related_symbols를 포함하세요

## 출력 형식:
[
  {"text": "AI 반도체 수요 급증", "sentiment": "positive", "related_symbols": ["NVDA", "AMD", "INTC"], "importance": 0.95, "reason": "NVDA 실적 발표 임박, 공급망 전체 주목"},
  {"text": "빅테크 가이던스 하향", "sentiment": "negative", "related_symbols": ["AAPL", "MSFT", "GOOGL"], "importance": 0.90, "reason": "어닝 시즌 시작, 실적 우려 확산"},
  {"text": "비트코인 급락세 지속", "sentiment": "negative", "related_symbols": ["COIN", "MSTR"], "importance": 0.85, "reason": "규제 불확실성 재부각, 관련주 동반 약세"},
  ...
]"""

    def _build_user_prompt(self, news_data: List[Dict], target_date: date) -> str:
        """사용자 프롬프트 구성"""
        # 뉴스 요약 구성
        news_summary = []
        for i, news in enumerate(news_data[:50], 1):  # 최대 50개만 포함
            symbols_str = ', '.join(news['symbols']) if news['symbols'] else '없음'
            sentiment_str = f"{news['sentiment_score']:.2f}" if news['sentiment_score'] else 'N/A'
            news_summary.append(
                f"{i}. [{news['source']}] {news['title']}\n"
                f"   요약: {news['summary'][:100]}...\n"
                f"   감성: {sentiment_str}, 관련종목: {symbols_str}"
            )

        return f"""# {target_date.strftime('%Y년 %m월 %d일')} 뉴스 분석

## 오늘의 뉴스 ({len(news_data)}건)

{chr(10).join(news_summary)}

---
위 뉴스들을 분석하여 오늘 시장의 핵심 키워드 10개를 JSON 형식으로 추출해주세요."""

    def _parse_response(self, response_text: str) -> List[Dict]:
        """LLM 응답 파싱"""
        try:
            # JSON 배열 추출 (코드 블록 처리)
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                json_str = json_match.group()
                keywords = json.loads(json_str)

                # 유효성 검증
                validated = []
                VALID_SENTIMENTS = {'positive', 'negative', 'neutral'}
                for kw in keywords:
                    if isinstance(kw, dict) and 'text' in kw:
                        raw_sentiment = str(kw.get('sentiment', 'neutral')).lower().strip()
                        # LLM이 유효하지 않은 값을 반환할 수 있으므로 정규화
                        if raw_sentiment not in VALID_SENTIMENTS:
                            raw_sentiment = 'neutral'
                        validated.append({
                            'text': str(kw.get('text', ''))[:25],
                            'sentiment': raw_sentiment,
                            'related_symbols': kw.get('related_symbols', [])[:3],
                            'importance': float(kw.get('importance', 0.5)),
                            'reason': str(kw.get('reason', ''))[:80],
                        })
                return validated[:10]

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed, attempting recovery: {e}")

            # 정규식으로 부분 복구
            pattern = r'"text"\s*:\s*"([^"]+)"'
            matches = re.findall(pattern, response_text)
            if matches:
                return [
                    {"text": text[:25], "sentiment": "neutral", "related_symbols": [], "importance": 0.5, "reason": ""}
                    for text in matches[:10]
                ]

        # 폴백
        return self.FALLBACK_KEYWORDS

    def _create_or_update_keyword(
        self,
        target_date: date,
        keywords: List[Dict] = None,
        total_news_count: int = 0,
        sources: Dict = None,
        status: str = 'pending',
        error_message: str = '',
        generation_time_ms: int = None
    ) -> DailyNewsKeyword:
        """DailyNewsKeyword 생성 또는 업데이트"""
        defaults = {
            'keywords': keywords or [],
            'total_news_count': total_news_count,
            'sources': sources or {},
            'status': status,
            'error_message': error_message,
            'llm_model': self.MODEL,
        }
        if generation_time_ms is not None:
            defaults['generation_time_ms'] = generation_time_ms

        keyword_obj, created = DailyNewsKeyword.objects.update_or_create(
            date=target_date,
            defaults=defaults
        )

        action = "Created" if created else "Updated"
        logger.info(f"{action} DailyNewsKeyword for {target_date}: {status}")

        return keyword_obj

    def get_latest_keywords(self, limit: int = 7) -> List[DailyNewsKeyword]:
        """최근 N일간의 키워드 조회"""
        return list(DailyNewsKeyword.objects.filter(
            status='completed'
        ).order_by('-date')[:limit])
