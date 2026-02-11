"""
LLM Relation Extractor Service (Phase 5)

뉴스/SEC 공시에서 Gemini LLM을 사용하여 기업 관계를 추출합니다.

관계 타입:
- ACQUIRED: 인수 (Microsoft acquired Activision)
- INVESTED_IN: 투자 (SoftBank invested in Arm)
- PARTNER_OF: 파트너십 (Apple partnered with Goldman Sachs)
- SPIN_OFF: 분사 (GE spun off GE Healthcare)
- SUED_BY: 소송 (Apple sued by Epic Games)

비용 최적화:
- RelationPreFilter로 ~80% 불필요 LLM 호출 제거
- 배치 처리로 API 호출 최적화
- Redis 캐싱 (동일 뉴스 재처리 방지)
- 월 예산 ~$5

Usage:
    from serverless.services.llm_relation_extractor import LLMRelationExtractor

    extractor = LLMRelationExtractor()

    # 단일 뉴스 처리
    relations = extractor.extract_from_news(news_entity)

    # 배치 처리
    results = extractor.extract_batch(news_list)

    # SEC 10-K 처리
    relations = extractor.extract_from_10k(filing_text, symbol)
"""
import logging
import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from google import genai
from google.genai import types

from serverless.models import LLMExtractedRelation
from serverless.services.relation_pre_filter import (
    RelationPreFilter,
    PreFilterResult,
    get_pre_filter,
)
from serverless.services.symbol_matcher import SymbolMatcher, get_symbol_matcher


logger = logging.getLogger(__name__)


@dataclass
class ExtractedRelation:
    """추출된 관계 데이터"""
    source_company: str
    target_company: str
    relation_type: str
    confidence_score: float
    evidence: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """추출 결과"""
    relations: List[ExtractedRelation]
    source_id: str
    source_type: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    extraction_time_ms: int = 0
    error: Optional[str] = None


class LLMRelationExtractor:
    """
    LLM 기반 기업 관계 추출 서비스

    핵심 기능:
    1. 뉴스/SEC 공시에서 관계 추출
    2. RelationPreFilter로 후보 필터링
    3. Gemini 2.5 Flash로 관계 추출
    4. SymbolMatcher로 티커 변환
    5. LLMExtractedRelation 모델에 저장
    """

    MODEL = "gemini-2.5-flash"
    MAX_OUTPUT_TOKENS = 1500
    TEMPERATURE = 0.2  # 정확도 중시
    CACHE_PREFIX = "llm_relation:"
    CACHE_TTL = 3600  # 1시간 (동일 뉴스 재처리 방지)

    VALID_RELATION_TYPES = {
        'ACQUIRED', 'INVESTED_IN', 'PARTNER_OF', 'SPIN_OFF', 'SUED_BY'
    }

    SYSTEM_PROMPT = """You are a financial news analyst specializing in extracting corporate relationships from news articles and SEC filings.

Your task is to identify and extract corporate relationships from the given text.

## Relationship Types to Extract:
1. ACQUIRED - Company A acquired/bought/merged with Company B
2. INVESTED_IN - Company A invested in/funded/took stake in Company B
3. PARTNER_OF - Company A partnered/collaborated/formed alliance with Company B
4. SPIN_OFF - Company A spun off/divested/separated Company B
5. SUED_BY - Company A is being sued by/in litigation with Company B

## Rules:
- Only extract relationships that are EXPLICITLY stated in the text
- Do NOT infer or assume relationships
- Extract the most specific company names possible
- Include confidence score (0.0 to 1.0) based on clarity
- Include relevant context (deal value, date, status if mentioned)
- If no relationships found, return empty list

## Output Format (JSON only):
```json
{
  "relations": [
    {
      "source_company": "Company A (the actor)",
      "target_company": "Company B (the target)",
      "relation_type": "ACQUIRED|INVESTED_IN|PARTNER_OF|SPIN_OFF|SUED_BY",
      "confidence": 0.95,
      "evidence": "exact quote from text",
      "context": {
        "deal_value": "$10B (if mentioned)",
        "date": "2024-01-15 (if mentioned)",
        "status": "completed|pending|announced (if mentioned)"
      }
    }
  ]
}
```

Important: Return ONLY valid JSON. No explanations or additional text."""

    def __init__(self):
        # Gemini API 클라이언트 초기화
        api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None) or \
                  getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError(
                "GOOGLE_AI_API_KEY 또는 GEMINI_API_KEY가 설정되지 않았습니다."
            )
        self.client = genai.Client(api_key=api_key)

        # 의존 서비스
        self.pre_filter = get_pre_filter()
        self.symbol_matcher = get_symbol_matcher()

        logger.info("LLMRelationExtractor initialized")

    def extract_from_text(
        self,
        text: str,
        source_id: str,
        source_type: str = 'news',
        source_url: Optional[str] = None,
        skip_prefilter: bool = False
    ) -> ExtractionResult:
        """
        텍스트에서 관계 추출

        Args:
            text: 뉴스 본문 또는 SEC 공시 텍스트
            source_id: 소스 ID (뉴스 UUID 또는 SEC 파일링 ID)
            source_type: 소스 타입 ('news', 'sec_10k', 'sec_8k')
            source_url: 원본 URL (선택)
            skip_prefilter: 사전 필터링 스킵 여부

        Returns:
            ExtractionResult with relations list
        """
        start_time = time.time()

        # 캐시 확인
        cache_key = f"{self.CACHE_PREFIX}{source_id}"
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for {source_id}")
            return cached

        # 사전 필터링
        if not skip_prefilter:
            pre_result = self.pre_filter.analyze(text)
            if not pre_result.is_candidate:
                logger.debug(f"Pre-filter rejected: {source_id}")
                result = ExtractionResult(
                    relations=[],
                    source_id=source_id,
                    source_type=source_type,
                    extraction_time_ms=int((time.time() - start_time) * 1000)
                )
                cache.set(cache_key, result, self.CACHE_TTL)
                return result

        # LLM 호출
        try:
            llm_result = self._call_llm(text)
            relations = self._parse_llm_response(llm_result)

            result = ExtractionResult(
                relations=relations,
                source_id=source_id,
                source_type=source_type,
                prompt_tokens=llm_result.get('prompt_tokens', 0),
                completion_tokens=llm_result.get('completion_tokens', 0),
                extraction_time_ms=int((time.time() - start_time) * 1000)
            )

            # 결과 캐싱
            cache.set(cache_key, result, self.CACHE_TTL)

            logger.info(
                f"Extracted {len(relations)} relations from {source_id} "
                f"in {result.extraction_time_ms}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Extraction failed for {source_id}: {e}")
            return ExtractionResult(
                relations=[],
                source_id=source_id,
                source_type=source_type,
                extraction_time_ms=int((time.time() - start_time) * 1000),
                error=str(e)
            )

    def extract_and_save(
        self,
        text: str,
        source_id: str,
        source_type: str = 'news',
        source_url: Optional[str] = None,
    ) -> List[LLMExtractedRelation]:
        """
        텍스트에서 관계 추출 후 DB 저장

        Args:
            text: 뉴스 본문 또는 SEC 공시 텍스트
            source_id: 소스 ID
            source_type: 소스 타입
            source_url: 원본 URL (선택)

        Returns:
            저장된 LLMExtractedRelation 리스트
        """
        result = self.extract_from_text(
            text=text,
            source_id=source_id,
            source_type=source_type,
            source_url=source_url
        )

        if result.error or not result.relations:
            return []

        saved_relations = []

        for rel in result.relations:
            # 회사명 → 티커 변환
            source_symbol = self.symbol_matcher.match(rel.source_company)
            target_symbol = self.symbol_matcher.match(rel.target_company)

            if not source_symbol or not target_symbol:
                logger.debug(
                    f"Symbol not found: {rel.source_company} -> {source_symbol}, "
                    f"{rel.target_company} -> {target_symbol}"
                )
                continue

            # 중복 확인 후 저장
            try:
                obj, created = LLMExtractedRelation.objects.update_or_create(
                    source_symbol=source_symbol,
                    target_symbol=target_symbol,
                    relation_type=rel.relation_type,
                    source_id=source_id,
                    defaults={
                        'source_type': source_type,
                        'source_url': source_url,
                        'evidence': rel.evidence[:500],  # 최대 500자
                        'context': rel.context,
                        'confidence': self._score_to_level(rel.confidence_score),
                        'llm_confidence_score': rel.confidence_score,
                        'llm_model': self.MODEL,
                        'prompt_tokens': result.prompt_tokens,
                        'completion_tokens': result.completion_tokens,
                        'extraction_time_ms': result.extraction_time_ms,
                        'expires_at': timezone.now() + timedelta(days=30),
                    }
                )

                if created:
                    logger.info(
                        f"Created relation: {source_symbol} --{rel.relation_type}--> "
                        f"{target_symbol}"
                    )

                saved_relations.append(obj)

            except Exception as e:
                logger.error(f"Failed to save relation: {e}")

        return saved_relations

    def extract_batch(
        self,
        documents: List[Dict[str, Any]],
        text_field: str = 'content',
        id_field: str = 'id',
        source_type: str = 'news'
    ) -> Dict[str, ExtractionResult]:
        """
        배치 문서 처리

        Args:
            documents: 문서 리스트
            text_field: 텍스트 필드명
            id_field: ID 필드명
            source_type: 소스 타입

        Returns:
            {source_id: ExtractionResult} 딕셔너리
        """
        results = {}

        # 사전 필터링
        candidates = self.pre_filter.filter_batch(
            documents,
            text_field=text_field,
            min_confidence=0.3
        )

        logger.info(
            f"Batch processing: {len(candidates)}/{len(documents)} "
            f"passed pre-filter"
        )

        for doc, pre_result in candidates:
            source_id = str(doc.get(id_field, ''))
            text = doc.get(text_field, '')
            source_url = doc.get('url') or doc.get('source_url')

            result = self.extract_from_text(
                text=text,
                source_id=source_id,
                source_type=source_type,
                source_url=source_url,
                skip_prefilter=True  # 이미 필터링됨
            )

            results[source_id] = result

            # Rate limiting (Gemini 무료 티어: 15 RPM)
            time.sleep(4)

        return results

    def _call_llm(self, text: str) -> Dict[str, Any]:
        """Gemini LLM 호출"""
        # 텍스트 길이 제한 (토큰 절약)
        truncated_text = text[:5000] if len(text) > 5000 else text

        user_prompt = f"""Extract corporate relationships from the following text:

---
{truncated_text}
---

Return only valid JSON with the extracted relations."""

        try:
            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text=self.SYSTEM_PROMPT),
                            types.Part(text=user_prompt),
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=self.TEMPERATURE,
                    max_output_tokens=self.MAX_OUTPUT_TOKENS,
                    response_mime_type="application/json",
                )
            )

            # 토큰 사용량 추출
            usage = getattr(response, 'usage_metadata', None)
            prompt_tokens = getattr(usage, 'prompt_token_count', 0) if usage else 0
            completion_tokens = getattr(usage, 'candidates_token_count', 0) if usage else 0

            return {
                'text': response.text,
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
            }

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_llm_response(self, llm_result: Dict[str, Any]) -> List[ExtractedRelation]:
        """LLM 응답 파싱"""
        relations = []

        try:
            text = llm_result.get('text', '')

            # JSON 파싱
            data = json.loads(text)
            raw_relations = data.get('relations', [])

            for r in raw_relations:
                # 필수 필드 검증
                if not all(k in r for k in ['source_company', 'target_company', 'relation_type']):
                    continue

                # 관계 타입 검증
                relation_type = r['relation_type'].upper()
                if relation_type not in self.VALID_RELATION_TYPES:
                    continue

                relations.append(ExtractedRelation(
                    source_company=r['source_company'],
                    target_company=r['target_company'],
                    relation_type=relation_type,
                    confidence_score=float(r.get('confidence', 0.5)),
                    evidence=r.get('evidence', ''),
                    context=r.get('context', {}),
                ))

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed: {e}")
            # 정규식으로 복구 시도
            relations = self._recover_from_partial_json(llm_result.get('text', ''))

        return relations

    def _recover_from_partial_json(self, text: str) -> List[ExtractedRelation]:
        """잘린 JSON 복구 시도"""
        relations = []

        # 관계 패턴 추출
        pattern = r'"source_company"\s*:\s*"([^"]+)".*?"target_company"\s*:\s*"([^"]+)".*?"relation_type"\s*:\s*"([^"]+)"'

        for match in re.finditer(pattern, text, re.DOTALL):
            source, target, rel_type = match.groups()

            if rel_type.upper() in self.VALID_RELATION_TYPES:
                relations.append(ExtractedRelation(
                    source_company=source,
                    target_company=target,
                    relation_type=rel_type.upper(),
                    confidence_score=0.5,  # 복구된 데이터는 중간 신뢰도
                    evidence="[Recovered from partial response]",
                    context={},
                ))

        if relations:
            logger.info(f"Recovered {len(relations)} relations from partial JSON")

        return relations

    def _score_to_level(self, score: float) -> str:
        """신뢰도 점수 → 레벨 변환"""
        if score >= 0.8:
            return 'high'
        elif score >= 0.6:
            return 'medium'
        else:
            return 'low'


# 싱글톤 인스턴스
_extractor = None


def get_relation_extractor() -> LLMRelationExtractor:
    """싱글톤 인스턴스 반환"""
    global _extractor
    if _extractor is None:
        _extractor = LLMRelationExtractor()
    return _extractor
