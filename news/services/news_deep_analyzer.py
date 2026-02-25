"""
뉴스 LLM 심층 분석 서비스 (News Intelligence Pipeline v3 - Phase 2)

Gemini 2.5 Flash를 사용하여 중요 뉴스의 심층 분석을 수행합니다.
- direct/indirect impact 추출
- 3-Tier 프롬프트 분기 (중요도별 분석 깊이 차등)
- Ticker 유효성 검증 (Stock DB)
- 구조화 JSON 출력
"""

import json
import logging
import re
import time
from typing import Optional

from django.conf import settings
from django.utils import timezone
from google import genai
from google.genai import types

from stocks.models import Stock
from ..models import NewsArticle

logger = logging.getLogger(__name__)


class NewsDeepAnalyzer:
    """
    LLM 기반 뉴스 심층 분석 서비스

    Tier A: importance_score >= 0.7 → 짧은 프롬프트 (direct_impact만)
    Tier B: importance_score >= 0.85 → 중간 프롬프트 (전체, indirect 최대 3개)
    Tier C: importance_score >= 0.93 → 긴 프롬프트 (전체 + opportunity + chain)
    """

    MODEL = "gemini-2.5-flash"
    TEMPERATURE = 0.3
    RPM_DELAY = 4  # 15 RPM 준수: 4초 간격

    # Tier 임계값
    TIER_C_THRESHOLD = 0.93
    TIER_B_THRESHOLD = 0.85
    TIER_A_THRESHOLD = 0.70

    def __init__(self):
        api_key = (
            getattr(settings, 'GOOGLE_AI_API_KEY', None)
            or getattr(settings, 'GEMINI_API_KEY', None)
        )
        if not api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
        self.client = genai.Client(api_key=api_key)
        # 유효 심볼 캐시 (배치 내 재사용)
        self._valid_symbols_cache = None

    def analyze_batch(self, max_articles: int = 50) -> dict:
        """
        당일 누적 기준 상위 15% 중 미분석 뉴스를 배치 분석합니다.

        Returns:
            dict: {analyzed: int, errors: int, skipped: int}
        """
        today = timezone.now().date()
        from datetime import datetime
        start_of_day = timezone.make_aware(
            datetime.combine(today, datetime.min.time())
        )

        # 오늘 수집된 뉴스 중 importance_score가 있고, llm_analyzed=False인 것
        articles = NewsArticle.objects.filter(
            published_at__gte=start_of_day,
            importance_score__isnull=False,
            llm_analyzed=False,
        ).order_by('-importance_score')[:max_articles]

        analyzed = 0
        errors = 0
        skipped = 0

        for article in articles:
            try:
                tier = self._determine_tier(article.importance_score)
                if tier is None:
                    skipped += 1
                    continue

                analysis = self._analyze_single(article, tier)
                if analysis:
                    article.llm_analysis = analysis
                    article.llm_analyzed = True
                    article.save(update_fields=['llm_analysis', 'llm_analyzed', 'updated_at'])
                    analyzed += 1
                else:
                    errors += 1

                # RPM 준수
                time.sleep(self.RPM_DELAY)

            except Exception as e:
                logger.error(f"Deep analysis failed for {article.id}: {e}")
                errors += 1

        result = {'analyzed': analyzed, 'errors': errors, 'skipped': skipped}
        logger.info(f"NewsDeepAnalyzer batch complete: {result}")
        return result

    def _determine_tier(self, score: float) -> Optional[str]:
        """importance_score 기반 분석 Tier 결정"""
        if score >= self.TIER_C_THRESHOLD:
            return 'C'
        elif score >= self.TIER_B_THRESHOLD:
            return 'B'
        elif score >= self.TIER_A_THRESHOLD:
            return 'A'
        return None

    def _analyze_single(self, article: NewsArticle, tier: str) -> Optional[dict]:
        """단일 뉴스 LLM 심층 분석"""
        prompt = self._build_prompt(article, tier)
        system_prompt = self._build_system_prompt(tier)
        max_tokens = {'A': 2000, 'B': 4000, 'C': 6000}[tier]

        try:
            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_tokens,
                    temperature=self.TEMPERATURE,
                ),
            )
            raw = response.text
            analysis = self._parse_response(raw, tier)

            if analysis:
                # Ticker 유효성 검증
                analysis = self._validate_tickers(analysis)
                analysis['tier'] = tier
                analysis['analyzed_at'] = timezone.now().isoformat()

            return analysis

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None

    def _build_system_prompt(self, tier: str) -> str:
        """Tier별 시스템 프롬프트"""
        base = (
            "You are a financial news analyst. Analyze the given news article "
            "and extract structured impact analysis in JSON format.\n"
            "All output must be valid JSON. Do not include markdown code fences.\n"
        )

        if tier == 'A':
            return base + (
                "Focus only on DIRECT impact. Identify affected stocks with "
                "direction (bullish/bearish/neutral) and confidence (0-1).\n"
                "Output: {\"direct_impacts\": [{\"symbol\": str, \"direction\": str, "
                "\"confidence\": float, \"reason\": str}]}"
            )
        elif tier == 'B':
            return base + (
                "Analyze both DIRECT and INDIRECT impacts. For indirect, explain "
                "the chain_logic (how the news indirectly affects the stock).\n"
                "Limit indirect_impacts to 3.\n"
                "Output: {\"direct_impacts\": [...], \"indirect_impacts\": "
                "[{\"symbol\": str, \"direction\": str, \"confidence\": float, "
                "\"reason\": str, \"chain_logic\": str}]}"
            )
        else:  # tier == 'C'
            return base + (
                "Perform comprehensive analysis:\n"
                "1. DIRECT impacts (affected stocks)\n"
                "2. INDIRECT impacts with chain_logic\n"
                "3. OPPORTUNITY plays (contrarian or second-order effects)\n"
                "4. sector_ripple: which sectors are affected and how\n"
                "Output: {\"direct_impacts\": [...], \"indirect_impacts\": [...], "
                "\"opportunities\": [{\"symbol\": str, \"thesis\": str, "
                "\"timeframe\": str, \"confidence\": float}], "
                "\"sector_ripple\": [{\"sector\": str, \"direction\": str, "
                "\"reason\": str}]}"
            )

    def _build_prompt(self, article: NewsArticle, tier: str) -> str:
        """Tier별 사용자 프롬프트"""
        # 기존 규칙 엔진 결과를 컨텍스트로 제공
        context_parts = [
            f"Title: {article.title}",
            f"Summary: {article.summary[:500] if article.summary else 'N/A'}",
            f"Source: {article.source}",
            f"Published: {article.published_at.isoformat()}",
        ]

        if article.rule_tickers:
            context_parts.append(f"Detected Tickers: {', '.join(article.rule_tickers)}")
        if article.rule_sectors:
            context_parts.append(f"Detected Sectors: {', '.join(article.rule_sectors)}")

        sentiment_str = f"{article.sentiment_score}" if article.sentiment_score else 'N/A'
        context_parts.append(f"Sentiment Score: {sentiment_str}")

        prompt = "\n".join(context_parts)

        if tier == 'A':
            prompt += "\n\nAnalyze the direct stock impacts of this news."
        elif tier == 'B':
            prompt += (
                "\n\nAnalyze both direct and indirect stock impacts. "
                "For indirect impacts, explain the chain of causation."
            )
        else:
            prompt += (
                "\n\nPerform a comprehensive impact analysis including "
                "direct impacts, indirect impacts with chain logic, "
                "opportunity plays, and sector ripple effects."
            )

        return prompt

    def _parse_response(self, raw: str, tier: str) -> Optional[dict]:
        """LLM 응답 JSON 파싱"""
        try:
            # JSON 추출 (코드 블록 처리)
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                data = json.loads(json_match.group())

                # 필수 필드 검증
                if 'direct_impacts' not in data:
                    data['direct_impacts'] = []

                # 각 impact 검증
                for impact in data.get('direct_impacts', []):
                    impact.setdefault('confidence', 0.5)
                    impact.setdefault('direction', 'neutral')
                    impact.setdefault('reason', '')

                for impact in data.get('indirect_impacts', []):
                    impact.setdefault('confidence', 0.3)
                    impact.setdefault('chain_logic', '')

                return data

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse LLM response: {e}")

        return None

    def _validate_tickers(self, analysis: dict) -> dict:
        """Stock DB 기준 ticker 유효성 검증, 무효 ticker 제거"""
        valid_symbols = self._get_valid_symbols()

        for key in ['direct_impacts', 'indirect_impacts', 'opportunities']:
            impacts = analysis.get(key, [])
            analysis[key] = [
                imp for imp in impacts
                if imp.get('symbol', '').upper() in valid_symbols
            ]
            # symbol 대문자 정규화
            for imp in analysis[key]:
                imp['symbol'] = imp['symbol'].upper()

        return analysis

    def _get_valid_symbols(self) -> set:
        """Stock DB에서 유효 심볼 집합 반환 (배치 내 캐시)"""
        if self._valid_symbols_cache is None:
            self._valid_symbols_cache = set(
                Stock.objects.values_list('symbol', flat=True)
            )
        return self._valid_symbols_cache
