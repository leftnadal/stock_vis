"""
관계 키워드 생성 서비스

StockRelationship 레코드에 AI 생성 키워드를 추가합니다.
"""
import json
import logging
import re
import time
from typing import List, Dict, Optional
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from google import genai
from google.genai import types

from serverless.models import StockRelationship


logger = logging.getLogger(__name__)


class RelationshipKeywordEnricher:
    """
    관계 키워드 생성 서비스

    Gemini 2.5 Flash를 사용하여 StockRelationship에 대한
    핵심 키워드 3개를 생성하고 context["keywords"]에 저장합니다.

    Features:
    - 우선순위 기반 처리 (PEER_OF > CO_MENTIONED > ...)
    - Gemini sync API (Bug #8: Celery에서 async 금지)
    - 15 RPM Rate Limit 준수 (4초 대기)
    - 에러 핸들링 및 fallback
    """

    # 관계 타입 우선순위 (중요도 순)
    PRIORITY = [
        'PEER_OF',          # 경쟁사 (가장 중요)
        'CO_MENTIONED',     # 뉴스 동시언급
        'SUPPLIED_BY',      # 공급망
        'CUSTOMER_OF',      # 고객사
        'ACQUIRED',         # 인수
        'INVESTED_IN',      # 투자
        'PARTNER_OF',       # 파트너십
        'SPIN_OFF',         # 분사
        'SUED_BY',          # 소송
        'SAME_INDUSTRY',    # 동일 산업
        'HAS_THEME',        # 테마 공유
    ]

    # Gemini 15 RPM Rate Limit
    CALL_DELAY = 4.0  # 초 (60초 / 15 calls = 4초)

    # 시스템 프롬프트
    SYSTEM_PROMPT = """당신은 투자 분석 전문가입니다.

두 기업의 관계를 설명하는 핵심 키워드 3개를 JSON 배열로 반환하세요.
각 키워드는 2-6단어 이내, 구체적이고 객관적이어야 합니다.

## 규칙

1. **간결성**: 각 키워드는 2-6단어 이내
2. **구체성**: 추상적 표현 금지 ("관계" ❌ → "GPU 시장 경쟁" ✅)
3. **투자 관점**: 투자자에게 유용한 정보
4. **객관성**: 확인 가능한 사실 기반

## 출력 형식

JSON 배열만 반환하세요 (설명 없음):

["키워드1", "키워드2", "키워드3"]

## 예시

입력: NVDA와 AMD의 PEER_OF 관계
출력: ["GPU 시장 경쟁", "AI 가속기", "데이터센터 칩"]

입력: AAPL과 TSM의 SUPPLIED_BY 관계
출력: ["반도체 위탁생산", "칩 공급망", "첨단 공정"]

입력: MSFT와 ATVI의 ACQUIRED 관계
출력: ["게임 사업 확장", "M&A 딜", "콘텐츠 IP 확보"]"""

    def __init__(self):
        """Gemini API 클라이언트 초기화 (동기 호출용)"""
        api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError("GOOGLE_AI_API_KEY 또는 GEMINI_API_KEY가 설정되지 않았습니다.")
        self.client = genai.Client(api_key=api_key)

    def enrich_batch(self, limit: int = 100) -> Dict:
        """
        키워드 없는 관계를 우선순위별 배치 처리

        Args:
            limit: 최대 처리 개수

        Returns:
            {
                'enriched': int,
                'skipped': int,
                'failed': int,
                'duration_ms': int
            }
        """
        logger.info(f"🔄 관계 키워드 배치 생성 시작 (limit={limit})")
        start_time = time.time()

        results = {'enriched': 0, 'skipped': 0, 'failed': 0}

        # 1. 키워드 없는 관계 조회 (우선순위 정렬)
        relationships = self._get_relationships_without_keywords(limit)

        if not relationships:
            logger.info("✅ 키워드 생성이 필요한 관계가 없습니다.")
            return {**results, 'duration_ms': int((time.time() - start_time) * 1000)}

        logger.info(f"📊 처리 대상: {len(relationships)}개 관계")

        # 2. 각 관계별 키워드 생성
        for rel in relationships:
            try:
                # 이미 키워드가 있으면 스킵
                if self._has_keywords(rel):
                    logger.debug(f"  ⏭️ {rel.source_symbol}-{rel.target_symbol}: 이미 키워드 존재")
                    results['skipped'] += 1
                    continue

                # 키워드 생성
                keywords = self._generate_keywords(
                    rel.source_symbol,
                    rel.target_symbol,
                    rel.relationship_type
                )

                if keywords:
                    # context 업데이트
                    self._save_keywords(rel, keywords)
                    logger.info(
                        f"  ✅ {rel.source_symbol}-{rel.target_symbol} "
                        f"({rel.get_relationship_type_display()}): {keywords}"
                    )
                    results['enriched'] += 1
                else:
                    logger.warning(
                        f"  ⚠️ {rel.source_symbol}-{rel.target_symbol}: "
                        f"키워드 생성 실패"
                    )
                    results['failed'] += 1

                # Rate limit 준수
                time.sleep(self.CALL_DELAY)

            except Exception as e:
                logger.exception(
                    f"  ❌ {rel.source_symbol}-{rel.target_symbol} 처리 중 에러: {e}"
                )
                results['failed'] += 1
                continue

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"✅ 관계 키워드 배치 생성 완료: "
            f"enriched={results['enriched']}, failed={results['failed']}, "
            f"skipped={results['skipped']}, duration={duration_ms}ms"
        )

        return {**results, 'duration_ms': duration_ms}

    def _get_relationships_without_keywords(self, limit: int) -> List[StockRelationship]:
        """
        키워드 없는 관계를 우선순위 순으로 조회

        우선순위 정렬을 위해 CASE WHEN을 사용합니다.
        """
        from django.db.models import Case, When, IntegerField

        # PRIORITY 리스트를 CASE WHEN으로 변환
        whens = [
            When(relationship_type=rel_type, then=idx)
            for idx, rel_type in enumerate(self.PRIORITY)
        ]

        return list(
            StockRelationship.objects.annotate(
                priority_order=Case(
                    *whens,
                    default=999,
                    output_field=IntegerField()
                )
            )
            .filter(
                # context가 null이거나, keywords 키가 없거나, keywords가 빈 리스트
                # Django JSONField 쿼리: __isnull 또는 전체 조회 후 필터
            )
            .order_by('priority_order', 'source_symbol')[:limit]
        )

    def _has_keywords(self, rel: StockRelationship) -> bool:
        """관계에 이미 키워드가 있는지 확인"""
        if not rel.context:
            return False
        keywords = rel.context.get('keywords')
        return bool(keywords and isinstance(keywords, list) and len(keywords) > 0)

    def _generate_keywords(
        self,
        source_symbol: str,
        target_symbol: str,
        rel_type: str
    ) -> List[str]:
        """
        단일 관계 키워드 생성 (3개)

        Args:
            source_symbol: 출발 종목
            target_symbol: 도착 종목
            rel_type: 관계 타입

        Returns:
            키워드 리스트 (3개) 또는 빈 리스트 (실패 시)
        """
        try:
            # 1. 프롬프트 생성
            prompt = self._build_prompt(source_symbol, target_symbol, rel_type)

            # 2. LLM 호출 (동기)
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=f"{self.SYSTEM_PROMPT}\n\n{prompt}")]
                    )
                ],
                config=types.GenerateContentConfig(
                    max_output_tokens=200,
                    temperature=0.5,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=0,
                    ),
                )
            )

            # 3. 응답 추출
            full_text = response.text if hasattr(response, 'text') else ""

            # 4. 파싱
            keywords = self._parse_keywords(full_text)

            return keywords

        except Exception as e:
            logger.error(
                f"키워드 생성 실패 ({source_symbol}-{target_symbol}): {e}"
            )
            return []

    def _build_prompt(
        self,
        source_symbol: str,
        target_symbol: str,
        rel_type: str
    ) -> str:
        """
        프롬프트 생성

        Args:
            source_symbol: 출발 종목
            target_symbol: 도착 종목
            rel_type: 관계 타입 (예: 'PEER_OF')

        Returns:
            프롬프트 문자열
        """
        # 관계 타입 표시명 조회
        rel_type_choices = dict(StockRelationship.RELATIONSHIP_TYPES)
        rel_type_display = rel_type_choices.get(rel_type, rel_type)

        return f"""{source_symbol}와 {target_symbol}의 {rel_type_display} 관계

위 관계를 설명하는 핵심 키워드 3개를 JSON 배열로 반환하세요.

JSON:"""

    def _parse_keywords(self, text: str) -> List[str]:
        """
        JSON 파싱 + fallback

        Args:
            text: LLM 응답 텍스트

        Returns:
            키워드 리스트 (1-5개) 또는 빈 리스트
        """
        try:
            # 1. JSON 배열 추출 (코드 블록 제거)
            clean_text = text.strip()
            clean_text = clean_text.replace('```json', '').replace('```', '').strip()

            # 2. JSON 파싱 시도
            try:
                keywords = json.loads(clean_text)
                if isinstance(keywords, list) and 1 <= len(keywords) <= 5:
                    # 문자열 리스트 검증
                    valid_keywords = [
                        str(kw).strip()
                        for kw in keywords
                        if kw and isinstance(kw, str) and len(str(kw).strip()) <= 30
                    ]
                    if valid_keywords:
                        return valid_keywords[:5]
            except json.JSONDecodeError:
                pass

            # 3. Fallback: 정규식으로 추출
            # 패턴: "키워드1", "키워드2", ...
            pattern = r'"([^"]+)"'
            matches = re.findall(pattern, clean_text)

            if matches and len(matches) >= 1:
                keywords = [
                    m.strip()
                    for m in matches
                    if m.strip() and len(m.strip()) <= 30
                ]
                if keywords:
                    logger.info(f"정규식 파싱 성공: {keywords[:5]}")
                    return keywords[:5]

            logger.warning(f"키워드 파싱 실패: {clean_text[:100]}")
            return []

        except Exception as e:
            logger.warning(f"키워드 파싱 중 에러: {e}, 원문: {text[:100]}")
            return []

    @transaction.atomic
    def _save_keywords(self, rel: StockRelationship, keywords: List[str]):
        """
        키워드를 StockRelationship.context에 저장

        Args:
            rel: StockRelationship 인스턴스
            keywords: 키워드 리스트
        """
        if not rel.context:
            rel.context = {}

        rel.context['keywords'] = keywords
        rel.context['keywords_generated_at'] = timezone.now().isoformat()
        rel.save(update_fields=['context', 'last_verified_at'])

    def enrich_single(
        self,
        source_symbol: str,
        target_symbol: str,
        rel_type: str
    ) -> Optional[List[str]]:
        """
        단일 관계 키워드 생성 (API/테스트용)

        Args:
            source_symbol: 출발 종목
            target_symbol: 도착 종목
            rel_type: 관계 타입

        Returns:
            키워드 리스트 또는 None
        """
        try:
            rel = StockRelationship.objects.get(
                source_symbol=source_symbol.upper(),
                target_symbol=target_symbol.upper(),
                relationship_type=rel_type
            )

            keywords = self._generate_keywords(source_symbol, target_symbol, rel_type)

            if keywords:
                self._save_keywords(rel, keywords)
                logger.info(
                    f"✅ 키워드 생성 성공: {source_symbol}-{target_symbol}: {keywords}"
                )
                return keywords
            else:
                logger.warning(
                    f"⚠️ 키워드 생성 실패: {source_symbol}-{target_symbol}"
                )
                return None

        except StockRelationship.DoesNotExist:
            logger.error(
                f"관계를 찾을 수 없음: {source_symbol}-{target_symbol} ({rel_type})"
            )
            return None
        except Exception as e:
            logger.exception(f"키워드 생성 중 에러: {e}")
            return None
