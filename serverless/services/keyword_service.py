"""
Market Movers 키워드 생성 서비스
"""
import json
import logging
import time
from typing import List, Dict, Optional
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from google import genai
from google.genai import types

from serverless.models import StockKeyword, MarketMover


logger = logging.getLogger(__name__)


class KeywordGenerationService:
    """
    LLM 기반 Market Movers 키워드 생성 서비스

    Features:
    - Gemini 2.5 Flash 사용 (빠르고 저렴)
    - 배치 생성 (일일 60개 종목)
    - 실패 시 fallback 키워드
    - 지수 백오프 재시도
    """

    # 시스템 프롬프트
    SYSTEM_PROMPT = """당신은 투자 분석 전문가입니다.

주어진 종목의 급등/급락 이유를 3-5개의 핵심 키워드로 요약하세요.

## 규칙

1. **간결성**: 각 키워드는 2-6단어 이내
2. **구체성**: 추상적 표현 금지 ("호재" ❌ → "AI 반도체 수요" ✅)
3. **최신성**: 당일 시장 이벤트 반영
4. **객관성**: 확인된 정보만 사용

## 출력 형식

JSON 배열만 반환하세요 (추가 설명 없음):

["키워드1", "키워드2", "키워드3"]

## 예시

입력:
- 종목: NVDA
- 상승률: +8.45%
- 섹터: Technology
- 산업: Semiconductors

출력:
["AI 반도체 수요", "데이터센터 확장", "실적 서프라이즈"]
"""

    # Fallback 키워드 (LLM 실패 시)
    FALLBACK_KEYWORDS = {
        'gainers': ["급등", "거래량 증가", "모멘텀"],
        'losers': ["급락", "매도 압력", "조정"],
        'actives': ["거래량 급증", "변동성", "투자자 관심"],
        'screener': ["분석 대상", "투자 검토", "모니터링"],
    }

    def __init__(self):
        """Gemini API 클라이언트 초기화 (동기 호출용)"""
        api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError("GOOGLE_AI_API_KEY 또는 GEMINI_API_KEY가 설정되지 않았습니다.")
        self.client = genai.Client(api_key=api_key)

    def generate_keyword(
        self,
        symbol: str,
        company_name: str,
        date,
        mover_type: str,
        change_percent: float,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        max_retries: int = 2
    ) -> Dict:
        """
        단일 종목 키워드 생성

        Args:
            symbol: 종목 심볼
            company_name: 회사명
            date: 날짜
            mover_type: 'gainers', 'losers', 'actives'
            change_percent: 변동률
            sector: 섹터
            industry: 산업
            max_retries: 최대 재시도 횟수

        Returns:
            {
                'keywords': [...],
                'status': 'completed' | 'failed',
                'error_message': str,
                'metadata': {...}
            }
        """
        start_time = time.time()

        # 1. 프롬프트 구성
        user_prompt = self._build_prompt(
            symbol, company_name, mover_type, change_percent, sector, industry
        )

        # 2. LLM 호출 (동기)
        try:
            keywords, metadata = self._call_llm_sync(user_prompt, max_retries)

            # 3. 검증
            if not keywords or len(keywords) < 3:
                logger.warning(f"{symbol}: 키워드 부족 ({len(keywords)}개) → Fallback 사용")
                keywords = self.FALLBACK_KEYWORDS.get(mover_type, ["변동성"])
                status = 'failed'
                error_message = "키워드 개수 부족"
            else:
                status = 'completed'
                error_message = None

        except Exception as e:
            logger.exception(f"{symbol} 키워드 생성 실패: {e}")
            keywords = self.FALLBACK_KEYWORDS.get(mover_type, ["변동성"])
            status = 'failed'
            error_message = str(e)
            metadata = {}

        # 4. 소요 시간 계산
        generation_time_ms = int((time.time() - start_time) * 1000)

        return {
            'keywords': keywords,
            'status': status,
            'error_message': error_message,
            'metadata': {
                'generation_time_ms': generation_time_ms,
                'prompt_tokens': metadata.get('input_tokens', 0),
                'completion_tokens': metadata.get('output_tokens', 0),
            }
        }

    def batch_generate(
        self,
        date,
        mover_type: str,
        limit: int = 20
    ) -> Dict[str, int]:
        """
        일괄 키워드 생성 (Celery 태스크용)

        Args:
            date: 날짜
            mover_type: 'gainers', 'losers', 'actives'
            limit: 처리 개수 (기본값: 20)

        Returns:
            {'success': 18, 'failed': 2, 'skipped': 0}
        """
        logger.info(f"🔄 키워드 배치 생성 시작: {date} {mover_type} (limit={limit})")

        results = {'success': 0, 'failed': 0, 'skipped': 0}

        # 1. MarketMover 조회
        movers = MarketMover.objects.filter(
            date=date,
            mover_type=mover_type
        ).order_by('rank')[:limit]

        # 2. 각 종목별 키워드 생성
        for mover in movers:
            # 이미 생성된 키워드 스킵
            if StockKeyword.objects.filter(
                symbol=mover.symbol,
                date=date,
                status='completed'
            ).exists():
                logger.debug(f"  ⏭️ {mover.symbol}: 이미 생성됨 (스킵)")
                results['skipped'] += 1
                continue

            # 키워드 생성
            result = self.generate_keyword(
                symbol=mover.symbol,
                company_name=mover.company_name,
                date=date,
                mover_type=mover_type,
                change_percent=float(mover.change_percent),
                sector=mover.sector,
                industry=mover.industry
            )

            # DB 저장
            StockKeyword.objects.update_or_create(
                symbol=mover.symbol,
                date=date,
                defaults={
                    'company_name': mover.company_name,
                    'keywords': result['keywords'],
                    'status': result['status'],
                    'error_message': result['error_message'],
                    'llm_model': 'gemini-2.5-flash',
                    'generation_time_ms': result['metadata'].get('generation_time_ms'),
                    'prompt_tokens': result['metadata'].get('prompt_tokens'),
                    'completion_tokens': result['metadata'].get('completion_tokens'),
                    'expires_at': timezone.now() + timedelta(days=7),
                }
            )

            # 결과 집계
            if result['status'] == 'completed':
                logger.info(f"  ✅ {mover.symbol}: {result['keywords']}")
                results['success'] += 1
            else:
                logger.warning(f"  ⚠️ {mover.symbol}: {result['error_message']}")
                results['failed'] += 1

        logger.info(
            f"✅ 키워드 배치 생성 완료: "
            f"success={results['success']}, failed={results['failed']}, skipped={results['skipped']}"
        )

        # 캐시 무효화
        self.invalidate_cache_after_generation(date, mover_type)

        return results

    def _build_prompt(
        self,
        symbol: str,
        company_name: str,
        mover_type: str,
        change_percent: float,
        sector: Optional[str],
        industry: Optional[str]
    ) -> str:
        """프롬프트 구성"""
        direction = "급등" if mover_type == "gainers" else "급락" if mover_type == "losers" else "거래량 증가"

        return f"""다음 종목의 {direction} 이유를 3개 핵심 키워드로 요약하세요.

종목: {symbol} ({company_name})
변동률: {change_percent:+.2f}%
섹터: {sector or 'N/A'}
산업: {industry or 'N/A'}

규칙:
- 정확히 3개 키워드만 반환
- 각 키워드는 15자 이내로 짧게
- 반드시 완전한 JSON 배열 형식

예시: ["AI 수요 증가", "실적 호조", "목표가 상향"]

JSON:"""

    def _call_llm_sync(self, prompt: str, max_retries: int) -> tuple:
        """
        LLM 동기 호출 (Gemini API 직접 사용)

        Celery Worker 환경에서도 안정적으로 동작하도록
        비동기 대신 동기 API를 직접 사용합니다.

        Returns:
            (keywords: List[str], metadata: Dict)
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # Gemini API 동기 호출
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part(text=f"{self.SYSTEM_PROMPT}\n\n{prompt}")]
                        )
                    ],
                    config=types.GenerateContentConfig(
                        max_output_tokens=1200,  # 한국어 응답을 위해 증가 (800 → 1200)
                        temperature=0.5,
                    )
                )

                # 응답 텍스트 추출
                full_text = response.text if hasattr(response, 'text') else ""

                # 토큰 사용량 (있는 경우)
                metadata = {}
                if hasattr(response, 'usage_metadata'):
                    usage = response.usage_metadata
                    metadata = {
                        'input_tokens': getattr(usage, 'prompt_token_count', 0),
                        'output_tokens': getattr(usage, 'candidates_token_count', 0),
                    }

                # JSON 파싱
                keywords = self._parse_keywords(full_text)

                return keywords, metadata

            except Exception as e:
                last_error = e
                error_msg = str(e).lower()

                # Rate limit 에러: 재시도
                if 'rate' in error_msg or 'quota' in error_msg or '429' in error_msg:
                    wait_time = (attempt + 1) * 2  # 2, 4, 6초
                    logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue

                # 기타 에러: 즉시 실패
                logger.error(f"LLM 호출 실패 (시도 {attempt + 1}/{max_retries + 1}): {e}")
                if attempt == max_retries:
                    raise Exception(f"LLM API 오류: {e}")
                time.sleep(1)

        raise Exception(f"LLM API 최대 재시도 초과: {last_error}")

    def _parse_keywords(self, text: str) -> List[str]:
        """
        LLM 응답에서 JSON 배열 파싱 (잘린 JSON 복구 지원)

        Args:
            text: LLM 응답 텍스트

        Returns:
            키워드 리스트
        """
        import re

        try:
            # JSON 배열 추출 (코드 블록 제거)
            clean_text = text.strip()
            clean_text = clean_text.replace('```json', '').replace('```', '').strip()

            # JSON 파싱 시도
            try:
                keywords = json.loads(clean_text)
                if isinstance(keywords, list) and len(keywords) >= 3:
                    return [str(kw).strip() for kw in keywords[:5] if kw]
            except json.JSONDecodeError:
                pass

            # 잘린 JSON 복구 시도
            # 패턴: ["키워드1", "키워드2", ...
            pattern = r'"([^"]+)"'
            matches = re.findall(pattern, clean_text)

            if matches and len(matches) >= 2:
                # 최소 2개 이상 추출되면 성공으로 처리
                keywords = [m.strip() for m in matches if m.strip() and len(m.strip()) <= 30]
                if len(keywords) >= 2:
                    logger.info(f"잘린 JSON 복구 성공: {keywords[:5]}")
                    return keywords[:5]

            raise ValueError(f"키워드 추출 실패: {clean_text[:100]}")

        except Exception as e:
            logger.warning(f"키워드 파싱 실패: {e}, 원문: {text[:100]}")
            raise

    def invalidate_cache_after_generation(self, date, mover_type: str):
        """
        키워드 생성 후 캐시 무효화

        Args:
            date: 날짜
            mover_type: 'gainers', 'losers', 'actives'
        """
        from django.core.cache import cache

        cache_key = f'movers_with_keywords:{date}:{mover_type}'
        cache.delete(cache_key)
        logger.info(f"🗑️ 캐시 무효화: {cache_key}")
