"""
Entity Extractor - 사용자 질문에서 엔티티 추출

Gemini 2.5 Flash를 사용하여 질문에서 종목명, 지표, 개념, 시간 범위를 추출합니다.
"""

import json
import re
import logging
from typing import TypedDict, Optional

from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)


class ExtractedEntities(TypedDict):
    """추출된 엔티티 타입"""
    stocks: list[str]
    metrics: list[str]
    concepts: list[str]
    timeframe: Optional[str]


class EntityExtractor:
    """
    엔티티 추출기 (Gemini Flash 기반)

    사용자 질문에서 다음을 추출:
    - stocks: 종목명/코드
    - metrics: 재무/투자 지표
    - concepts: 투자 개념
    - timeframe: 시간 범위
    """

    MODEL = "gemini-2.5-flash"
    MAX_TOKENS = 200

    EXTRACTION_PROMPT = """주어진 질문에서 다음 엔티티를 추출하세요:

1. stocks: 종목명 또는 종목코드 (예: AAPL, 삼성전자, TSMC)
2. metrics: 재무/투자 지표 (예: PER, 매출, 영업이익, 실적)
3. concepts: 투자 개념 (예: 저평가, 성장주, 리스크, 영향)
4. timeframe: 시간 범위 (예: 2024년, 최근 3개월, Q3)

JSON 형식으로만 응답하세요. 없는 항목은 빈 리스트 또는 null로 표시합니다.

질문: {question}

JSON:"""

    def __init__(self):
        """Gemini API 클라이언트 초기화"""
        api_key = getattr(settings, 'GEMINI_API_KEY', None) or getattr(settings, 'GOOGLE_AI_API_KEY', None)

        if not api_key:
            logger.warning(
                "GEMINI_API_KEY not set. EntityExtractor will use fallback mode."
            )
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    async def extract(self, question: str) -> ExtractedEntities:
        """
        질문에서 엔티티 추출

        Args:
            question: 사용자 질문

        Returns:
            ExtractedEntities: 추출된 엔티티
        """
        # API 키가 없으면 폴백 사용
        if not self.client:
            return self._fallback_extraction(question)

        try:
            config = types.GenerateContentConfig(
                max_output_tokens=self.MAX_TOKENS,
                temperature=0.1,  # 낮은 온도로 일관된 JSON 출력
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            )

            response = await self.client.aio.models.generate_content(
                model=self.MODEL,
                contents=self.EXTRACTION_PROMPT.format(question=question),
                config=config,
            )

            content = response.text.strip()

            # JSON 파싱 - 마크다운 코드 블록 제거
            content = self._clean_json_response(content)

            entities = json.loads(content)

            return ExtractedEntities(
                stocks=entities.get("stocks", []),
                metrics=entities.get("metrics", []),
                concepts=entities.get("concepts", []),
                timeframe=entities.get("timeframe")
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Entity extraction JSON parse error: {e}")
            return self._fallback_extraction(question)

        except Exception as e:
            logger.error(f"Gemini API error in entity extraction: {e}")
            return self._fallback_extraction(question)

    def _clean_json_response(self, content: str) -> str:
        """
        LLM 응답에서 JSON만 추출

        마크다운 코드 블록 (```json ... ```) 제거
        """
        # 코드 블록으로 감싸진 경우
        if content.startswith("```"):
            # 첫 번째 ``` 제거
            parts = content.split("```", 2)
            if len(parts) >= 2:
                content = parts[1]
                # json 키워드 제거
                if content.startswith("json"):
                    content = content[4:]
                # 끝의 ``` 제거
                if "```" in content:
                    content = content.split("```")[0]

        return content.strip()

    def _fallback_extraction(self, question: str) -> ExtractedEntities:
        """
        폴백: 간단한 규칙 기반 추출

        Args:
            question: 사용자 질문

        Returns:
            ExtractedEntities: 추출된 엔티티
        """
        # 대문자 종목코드 패턴 (2-5글자)
        stock_pattern = r'\b[A-Z]{2,5}\b'
        stocks = re.findall(stock_pattern, question)

        # 한글 종목명 (미리 정의된 목록)
        korean_stocks = [
            '삼성전자', '삼성SDI', 'SK하이닉스', 'LG에너지솔루션',
            '현대차', 'NAVER', '네이버', '카카오', 'TSMC'
        ]
        found_korean = [s for s in korean_stocks if s in question]

        # 재무 지표 키워드
        metrics = []
        metric_keywords = {
            '매출': '매출',
            '영업이익': '영업이익',
            '순이익': '순이익',
            '실적': '실적',
            'PER': 'PER',
            'PBR': 'PBR',
            'ROE': 'ROE',
            'EPS': 'EPS',
        }
        for keyword, metric in metric_keywords.items():
            if keyword in question:
                metrics.append(metric)

        return ExtractedEntities(
            stocks=list(set(stocks + found_korean)),
            metrics=list(set(metrics)),
            concepts=[],
            timeframe=None
        )


class EntityNormalizer:
    """
    엔티티 정규화

    추출된 엔티티를 표준 형식으로 변환합니다.
    """

    # 한글 종목명 → 심볼 매핑
    STOCK_MAPPING = {
        '삼성전자': '005930.KS',
        '삼성SDI': '006400.KS',
        'SK하이닉스': '000660.KS',
        'LG에너지솔루션': '373220.KS',
        '현대차': '005380.KS',
        'NAVER': '035420.KS',
        '네이버': '035420.KS',
        '카카오': '035720.KS',
        'TSMC': 'TSM',
        '애플': 'AAPL',
        '엔비디아': 'NVDA',
        '마이크로소프트': 'MSFT',
        '구글': 'GOOGL',
        '아마존': 'AMZN',
        '테슬라': 'TSLA',
    }

    # 지표 키워드 → 표준 필드명 매핑
    METRIC_MAPPING = {
        '실적': ['revenue', 'earnings'],
        '매출': ['revenue'],
        '영업이익': ['operating_income'],
        '순이익': ['net_income'],
        'PER': ['pe_ratio'],
        'PBR': ['pb_ratio'],
        'ROE': ['return_on_equity'],
        'EPS': ['earnings_per_share'],
    }

    def normalize_stocks(self, stocks: list[str]) -> list[str]:
        """
        종목명 정규화

        Args:
            stocks: 추출된 종목명 리스트

        Returns:
            list[str]: 정규화된 심볼 리스트
        """
        normalized = []
        for stock in stocks:
            # 매핑 테이블에 있으면 변환
            if stock in self.STOCK_MAPPING:
                normalized.append(self.STOCK_MAPPING[stock])
            else:
                # 없으면 대문자 변환
                normalized.append(stock.upper())

        return list(set(normalized))

    def normalize_metrics(self, metrics: list[str]) -> list[str]:
        """
        지표 정규화

        Args:
            metrics: 추출된 지표 리스트

        Returns:
            list[str]: 정규화된 지표 필드명 리스트
        """
        normalized = []
        for metric in metrics:
            # 매핑 테이블에 있으면 변환
            if metric in self.METRIC_MAPPING:
                normalized.extend(self.METRIC_MAPPING[metric])
            else:
                # 없으면 소문자 + 언더스코어 변환
                normalized.append(metric.lower().replace(' ', '_'))

        return list(set(normalized))
