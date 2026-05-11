"""
투자 테제 빌더 서비스 (Phase 2.3 - Investment Thesis Builder)

스크리너 결과를 바탕으로 LLM이 투자 테제를 자동 생성합니다.

IMPORTANT: Celery 호환을 위해 동기 API만 사용합니다.
"""

import logging
import json
import re
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from google import genai
from google.genai import types

from serverless.models import InvestmentThesis

logger = logging.getLogger(__name__)


class ThesisBuilder:
    """
    LLM 기반 투자 테제 생성 서비스

    Features:
    - Gemini 2.5 Flash 사용 (저비용)
    - 동기 API 호출 (Celery 호환)
    - 스크리너 필터 → 투자 논리 자동 생성
    - InvestmentThesis 모델에 저장
    - share_code 자동 생성 (공유 기능)
    """

    MODEL = "gemini-2.5-flash"
    MAX_TOKENS = 4000  # 충분한 출력 토큰 확보
    TEMPERATURE = 0.5  # 창의적이면서도 일관된 테제 생성

    def __init__(self, language: str = "ko"):
        """
        Args:
            language: 테제 언어 ('ko' 또는 'en')
        """
        self.language = language

        # Gemini API 클라이언트 초기화
        api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None) or getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError(
                "GOOGLE_AI_API_KEY 또는 GEMINI_API_KEY가 설정되지 않았습니다."
            )
        self.client = genai.Client(api_key=api_key)

    def build_thesis(
        self,
        stocks: List[Dict[str, Any]],
        filters: Dict[str, Any],
        user=None,
        user_notes: str = '',
        preset_ids: Optional[List[int]] = None
    ) -> InvestmentThesis:
        """
        투자 테제 생성

        Args:
            stocks: 스크리너 결과 종목 리스트
                [
                    {
                        'symbol': str,
                        'company_name': str,
                        'price': float,
                        'change_percent': float,
                        'sector': str,
                        'pe_ratio': float,
                        'roe': float,
                        ...
                    },
                    ...
                ]
            filters: 적용된 필터 조건
                {
                    'pe_max': 20,
                    'roe_min': 15,
                    'sector': 'Technology',
                    ...
                }
            user: User 인스턴스 (선택)
            user_notes: 사용자 추가 메모 (선택)
            preset_ids: 사용된 프리셋 IDs (선택)

        Returns:
            InvestmentThesis 모델 인스턴스 (저장됨)
        """
        if not stocks:
            raise ValueError("종목 리스트가 비어있습니다.")

        logger.info(
            f"투자 테제 생성 시작: {len(stocks)}개 종목, "
            f"{len(filters)}개 필터 조건"
        )

        start_time = timezone.now()

        try:
            # LLM 프롬프트 구성
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(stocks, filters, user_notes)

            # LLM 호출 (동기)
            response_text = self._call_llm_sync(system_prompt, user_prompt)

            # 응답 파싱
            thesis_data = self._parse_response(response_text)

            if not thesis_data:
                raise ValueError("LLM 응답 파싱 실패")

            # 생성 시간 계산
            generation_time_ms = int(
                (timezone.now() - start_time).total_seconds() * 1000
            )

            # InvestmentThesis 모델에 저장
            thesis = InvestmentThesis.objects.create(
                user=user,
                title=thesis_data['title'],
                summary=thesis_data['summary'],
                filters_snapshot=filters,
                preset_ids=preset_ids or [],
                key_metrics=thesis_data.get('key_metrics', []),
                top_picks=thesis_data.get('top_picks', [])[:5],  # 최대 5개
                risks=thesis_data.get('risks', []),
                rationale=thesis_data.get('rationale', ''),
                llm_model=self.MODEL,
                generation_time_ms=generation_time_ms,
                is_public=False,
                share_code=self._generate_share_code(),
            )

            logger.info(
                f"투자 테제 생성 완료: ID={thesis.id}, "
                f"제목='{thesis.title}', 소요 시간={generation_time_ms}ms"
            )

            return thesis

        except Exception as e:
            logger.exception(f"투자 테제 생성 실패: {e}")
            raise

    def _build_system_prompt(self) -> str:
        """
        시스템 프롬프트 구성

        Returns:
            시스템 프롬프트
        """
        lang_instruction = (
            "한국어로 투자 테제를 작성하세요." if self.language == "ko"
            else "Write the investment thesis in English."
        )

        return f"""당신은 전문 투자 분석가입니다.

## 역할
스크리너 결과를 분석하여 투자자를 위한 간결하고 실행 가능한 투자 테제를 작성합니다.

## 투자 테제란?
투자 테제는 "왜 이 종목들에 투자해야 하는가?"를 설명하는 논리적 근거입니다.
다음 요소를 포함해야 합니다:

1. **제목**: 테제의 핵심을 한 문장으로 요약 (15자 이내)
2. **요약**: 투자 논리를 1-2문장으로 설명
3. **핵심 지표**: 필터 조건을 투자 기준으로 변환 (3-5개)
4. **추천 종목**: 선별된 종목 중 상위 종목 (최대 5개, 심볼만)
5. **리스크**: 고려해야 할 위험 요인 (2-4개)
6. **투자 근거**: 테제를 뒷받침하는 상세 설명 (2-3문장)

## 작성 원칙

1. **간결성**: 투자자가 30초 안에 이해할 수 있어야 합니다.
2. **구체성**: "좋은 종목"이 아니라 "PER 15 이하, ROE 20% 이상"처럼 구체적으로.
3. **균형**: 긍정적 요인과 리스크를 모두 제시합니다.
4. **실행 가능성**: "지금 당장 투자할 수 있는" 테제를 작성합니다.

## 언어
{lang_instruction}

## 출력 형식

반드시 JSON 형식으로 출력하세요:

```json
{{
  "title": "저평가 고수익 기술주",
  "summary": "PER 15 이하, ROE 20% 이상 기준으로 선별된 기술주. 밸류에이션 매력과 높은 자본 효율성을 동시에 확보.",
  "key_metrics": [
    "PER < 15 (시장 평균 대비 저평가)",
    "ROE > 20% (높은 자본 효율성)",
    "섹터: Technology (성장 산업)",
    "시가총액 > $10B (안정성)"
  ],
  "top_picks": ["AAPL", "MSFT", "GOOGL", "META", "NVDA"],
  "risks": [
    "기술주 밸류에이션 압박 (금리 상승)",
    "경기 둔화 시 성장률 하락",
    "규제 리스크 (반독점 이슈)"
  ],
  "rationale": "선별된 종목들은 시장 평균 대비 저평가되어 있으면서도 높은 ROE로 자본 효율성을 입증했습니다. 기술주 섹터의 장기 성장 트렌드를 고려할 때 현재 밸류에이션은 매력적인 진입 기회를 제공합니다."
}}
```

## 예시 (한국어)

**제목**: "배당 + 성장 하이브리드"
**요약**: "배당수익률 3% 이상, PEG 비율 1.5 이하 종목. 안정적 배당 수익과 성장 가능성을 동시 확보."
**핵심 지표**: ["배당수익률 > 3%", "PEG < 1.5", "부채비율 < 50%"]
**리스크**: ["배당 감소 가능성", "성장률 둔화 시 PEG 상승"]

## 예시 (영어)

**제목**: "High-Growth Tech Leaders"
**요약**: "Revenue growth >30%, Strong margins. Riding AI and cloud trends."
**핵심 지표**: ["Revenue Growth > 30%", "Gross Margin > 60%", "Sector: Technology"]
**리스크**: ["Valuation Risk", "Competition Intensified"]
"""

    def _build_user_prompt(
        self,
        stocks: List[Dict[str, Any]],
        filters: Dict[str, Any],
        user_notes: str = ''
    ) -> str:
        """
        사용자 프롬프트 구성

        Args:
            stocks: 스크리너 결과 종목 리스트
            filters: 적용된 필터 조건
            user_notes: 사용자 추가 메모

        Returns:
            사용자 프롬프트
        """
        lines = [
            "# 스크리너 결과 분석 요청",
            "",
            "## 적용된 필터 조건",
            ""
        ]

        # 필터 조건 표시 (읽기 쉽게 포맷팅)
        if filters:
            for key, value in filters.items():
                # snake_case를 읽기 쉬운 형태로 변환
                label = key.replace('_', ' ').title()

                if isinstance(value, (int, float, Decimal)):
                    lines.append(f"- {label}: {value}")
                elif isinstance(value, list):
                    lines.append(f"- {label}: {', '.join(map(str, value))}")
                else:
                    lines.append(f"- {label}: {value}")
        else:
            lines.append("(필터 조건 없음)")

        lines.append("")
        lines.append(f"## 선별된 종목 ({len(stocks)}개)")
        lines.append("")

        # 종목 목록 (최대 10개만 표시 - 토큰 절약)
        display_stocks = stocks[:10]
        for idx, stock in enumerate(display_stocks, 1):
            symbol = stock.get('symbol', 'N/A')
            # camelCase와 snake_case 모두 지원
            company_name = stock.get('companyName') or stock.get('company_name', 'N/A')
            sector = stock.get('sector', 'N/A')

            # 주요 지표 추출 (camelCase/snake_case 모두 지원)
            metrics = []
            pe = stock.get('peRatioTTM') or stock.get('pe_ratio')
            if pe:
                metrics.append(f"PER: {float(pe):.1f}")
            roe = stock.get('returnOnEquityTTM') or stock.get('roe')
            if roe:
                metrics.append(f"ROE: {float(roe):.1f}%")
            market_cap = stock.get('marketCap') or stock.get('market_cap')
            if market_cap:
                market_cap_b = float(market_cap) / 1e9
                metrics.append(f"Cap: ${market_cap_b:.1f}B")
            change = stock.get('changesPercentage') or stock.get('change_percent')
            if change:
                metrics.append(f"Change: {float(change):+.1f}%")

            metrics_str = ', '.join(metrics) if metrics else ''

            lines.append(
                f"{idx}. {symbol} - {company_name} ({sector})"
            )
            if metrics_str:
                lines.append(f"   {metrics_str}")

        if len(stocks) > 10:
            lines.append(f"   ... 외 {len(stocks) - 10}개 종목")

        # 사용자 메모 (있는 경우)
        if user_notes:
            lines.append("")
            lines.append("## 사용자 메모")
            lines.append("")
            lines.append(user_notes)

        lines.append("")
        lines.append("위 정보를 바탕으로 투자 테제를 작성하세요.")

        return "\n".join(lines)

    def _call_llm_sync(self, system_prompt: str, user_prompt: str) -> str:
        """
        LLM API 동기 호출 (Celery 호환)

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트

        Returns:
            LLM 응답 텍스트
        """
        logger.info(f"LLM 호출 시작: model={self.MODEL}, max_tokens={self.MAX_TOKENS}")

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=self.MAX_TOKENS,
            temperature=self.TEMPERATURE,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            # response_mime_type 제거 - 응답 잘림 문제 발생
        )

        # 동기 호출 (client.models.generate_content - async 없음)
        response = self.client.models.generate_content(
            model=self.MODEL,
            contents=user_prompt,
            config=config,
        )

        # 응답 텍스트 추출
        response_text = self._extract_response_text(response)

        logger.info(f"LLM 응답 수신: {len(response_text)}자")
        print(f"[THESIS LLM] 응답 ({len(response_text)}자):\n{response_text[:500]}...")

        return response_text

    def _extract_response_text(self, response) -> str:
        """
        Gemini API 응답에서 텍스트 추출

        Args:
            response: Gemini API 응답 객체

        Returns:
            응답 텍스트
        """
        # 응답 텍스트 추출
        if hasattr(response, 'text') and response.text:
            return response.text

        # candidates에서 추출
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and candidate.content:
                if hasattr(candidate.content, 'parts') and candidate.content.parts:
                    return candidate.content.parts[0].text

        raise ValueError("No text found in LLM response")

    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        LLM 응답 파싱

        Args:
            response: LLM 응답 텍스트

        Returns:
            {
                'title': str,
                'summary': str,
                'key_metrics': [str, ...],
                'top_picks': [str, ...],
                'risks': [str, ...],
                'rationale': str
            }
            또는 None (파싱 실패)
        """
        logger.info(f"LLM 응답 파싱 시작 (길이: {len(response)})")
        print(f"[THESIS PARSE] 응답 길이: {len(response)}", flush=True)
        print(f"[THESIS PARSE] 응답 원문:\n{response[:1500]}", flush=True)

        json_str = None

        # 방법 1: ```json ... ``` 블록 추출
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            logger.info("JSON 블록 (```json```) 발견")

        # 방법 2: ``` ... ``` 블록 추출 (언어 명시 없음)
        if not json_str:
            json_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                logger.info("JSON 블록 (```) 발견")

        # 방법 3: { ... } 객체 추출
        if not json_str:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group(0).strip()
                logger.info("JSON 객체 ({...}) 발견")

        # 방법 4: 전체 응답 사용
        if not json_str:
            json_str = response.strip()
            logger.info("JSON 블록 없음, 전체 응답 사용")

        # JSON 정리 (제어 문자 제거)
        json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)

        try:
            data = json.loads(json_str)

            # 필수 필드 검증
            if not isinstance(data, dict):
                logger.error(f"LLM 응답이 dict가 아닙니다: {type(data)}")
                return None

            if 'title' not in data or 'summary' not in data:
                logger.error(f"필수 필드 누락. keys: {list(data.keys())}")
                return None

            # 리스트 필드 검증 및 기본값
            if 'key_metrics' not in data or not isinstance(data['key_metrics'], list):
                data['key_metrics'] = []
            if 'top_picks' not in data or not isinstance(data['top_picks'], list):
                data['top_picks'] = []
            if 'risks' not in data or not isinstance(data['risks'], list):
                data['risks'] = []

            # 문자열 필드 기본값
            if 'rationale' not in data:
                data['rationale'] = ''

            # top_picks 심볼 대문자 변환
            data['top_picks'] = [
                symbol.upper() for symbol in data['top_picks'] if symbol
            ]

            logger.info(
                f"LLM 응답 파싱 성공: "
                f"title='{data['title']}', "
                f"key_metrics={len(data['key_metrics'])}개, "
                f"top_picks={len(data['top_picks'])}개, "
                f"risks={len(data['risks'])}개"
            )

            return data

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            print(f"[THESIS ERROR] JSON 파싱 실패: {e}", flush=True)
            print(f"[THESIS ERROR] 파싱 시도한 문자열:\n{json_str[:800]}", flush=True)

            # 복구 시도: 잘린 JSON 수리
            try:
                # 끝에 누락된 괄호 추가 시도
                if json_str.count('{') > json_str.count('}'):
                    json_str += '}'
                if json_str.count('[') > json_str.count(']'):
                    json_str += ']'
                data = json.loads(json_str)
                logger.info("JSON 수리 후 파싱 성공")
                return self._validate_and_normalize(data)
            except:
                pass

            return None

        except (ValueError, TypeError) as e:
            logger.error(f"LLM 응답 처리 실패: {e}")
            return None

    def _validate_and_normalize(self, data: Dict) -> Optional[Dict[str, Any]]:
        """파싱된 데이터 검증 및 정규화"""
        if not isinstance(data, dict):
            return None

        if 'title' not in data or 'summary' not in data:
            return None

        # 기본값 설정
        data.setdefault('key_metrics', [])
        data.setdefault('top_picks', [])
        data.setdefault('risks', [])
        data.setdefault('rationale', '')

        # top_picks 대문자 변환
        data['top_picks'] = [s.upper() for s in data['top_picks'] if s]

        return data

    def _generate_share_code(self) -> str:
        """
        공유 코드 생성 (8자 랜덤 문자열)

        Returns:
            공유 코드 (예: "A3F8K2J9")
        """
        return uuid.uuid4().hex[:8].upper()

    def estimate_cost(self, num_stocks: int, num_filters: int) -> Dict[str, Any]:
        """
        테제 생성 비용 추정

        Args:
            num_stocks: 종목 수
            num_filters: 필터 수

        Returns:
            {
                'input_tokens': int,
                'output_tokens': int,
                'total_tokens': int,
                'cost_usd': float
            }
        """
        # 대략적 토큰 추정
        # - 시스템 프롬프트: 1800 토큰
        # - 필터당 입력: 30 토큰
        # - 종목당 입력: 50 토큰
        # - 출력: 800 토큰 (테제 + JSON)
        input_tokens = 1800 + (num_filters * 30) + (min(num_stocks, 20) * 50)
        output_tokens = 800

        total_tokens = input_tokens + output_tokens

        # Gemini 2.5 Flash 가격 (2025년 1월 기준)
        # Input: $0.30 / 1M tokens
        # Output: $1.20 / 1M tokens
        INPUT_COST_PER_1M = 0.30
        OUTPUT_COST_PER_1M = 1.20

        input_cost = (input_tokens / 1_000_000) * INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * OUTPUT_COST_PER_1M

        total_cost = input_cost + output_cost

        return {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'input_cost_usd': round(input_cost, 6),
            'output_cost_usd': round(output_cost, 6),
            'total_cost_usd': round(total_cost, 6),
        }


# 폴백 테제 생성 (LLM 실패 시)
def create_fallback_thesis(
    stocks: List[Dict[str, Any]],
    filters: Dict[str, Any],
    user=None,
    preset_ids: Optional[List[int]] = None
) -> InvestmentThesis:
    """
    LLM 실패 시 기본 테제 생성

    Args:
        stocks: 스크리너 결과 종목 리스트
        filters: 적용된 필터 조건
        user: User 인스턴스 (선택)
        preset_ids: 사용된 프리셋 IDs (선택)

    Returns:
        InvestmentThesis 모델 인스턴스 (저장됨)
    """
    # 필터 조건을 문자열로 변환
    filter_labels = []
    for key, value in filters.items():
        label = key.replace('_', ' ').title()
        filter_labels.append(f"{label}: {value}")

    title = "스크리너 결과 분석"
    summary = f"{len(stocks)}개 종목이 선별되었습니다. 필터 조건을 검토하고 투자 전략을 수립하세요."

    # 상위 5개 종목 추출
    top_picks = [stock.get('symbol', '') for stock in stocks[:5]]

    thesis = InvestmentThesis.objects.create(
        user=user,
        title=title,
        summary=summary,
        filters_snapshot=filters,
        preset_ids=preset_ids or [],
        key_metrics=filter_labels[:5],
        top_picks=top_picks,
        risks=["자동 생성 실패로 기본 테제 생성됨"],
        rationale="",
        llm_model="fallback",
        generation_time_ms=0,
        is_public=False,
        share_code=uuid.uuid4().hex[:8].upper(),
    )

    logger.warning(f"폴백 테제 생성: ID={thesis.id}")

    return thesis
