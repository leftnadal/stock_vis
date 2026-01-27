"""
Market Movers 키워드 생성 프롬프트 시스템

LLM을 활용하여 Market Movers 종목에 대한 키워드를 자동 생성합니다.
5개 지표(RVOL, Trend Strength, Sector Alpha, ETF Sync, Volatility)를 분석하여
투자자가 빠르게 이해할 수 있는 한국어/영어 키워드를 생성합니다.
"""

from datetime import date
from typing import Dict, Any, List, Optional


class KeywordPromptBuilder:
    """
    Market Movers 키워드 생성 프롬프트 빌더

    Features:
    - 5개 지표 기반 키워드 생성
    - 한국어/영어 키워드 출력
    - Structured JSON 출력
    - 배치 처리 최적화 (20개 종목 일괄 처리)
    """

    # 지표 해석 가이드 (LLM에 제공)
    INDICATOR_GUIDE = """
## 지표 해석 가이드

### 1. RVOL (Relative Volume)
- 의미: 당일 거래량 / 20일 평균 거래량
- 해석:
  - 2.0 이상: 비정상적 관심도 (주요 이벤트 의심)
  - 1.5~2.0: 높은 관심
  - 1.0~1.5: 평균 이상
  - 1.0 미만: 평균 이하

### 2. Trend Strength (추세 강도)
- 의미: (종가-시가) / (고가-저가)
- 해석:
  - +0.7 이상: 강한 상승 추세
  - +0.3~+0.7: 중간 상승
  - -0.3~+0.3: 횡보 (변동성 높음)
  - -0.7~-0.3: 중간 하락
  - -0.7 이하: 강한 하락 추세

### 3. Sector Alpha (섹터 초과수익)
- 의미: 종목 수익률 - 섹터 ETF 수익률
- 해석:
  - 양수(+): 섹터 평균 초과 (상대 강세)
  - 음수(-): 섹터 평균 미달 (상대 약세)
  - 절대값이 클수록 섹터 대비 독립적 움직임

### 4. ETF Sync Rate (ETF 동행률)
- 의미: 종목과 섹터 ETF의 피어슨 상관계수 (20일)
- 해석:
  - 0.8 이상: 강한 동조 (섹터 트렌드 따름)
  - 0.5~0.8: 중간 동조
  - 0.5 미만: 독립적 움직임 (개별 이슈)

### 5. Volatility Percentile (변동성 백분위)
- 의미: 당일 변동성의 20일 백분위 (0-100)
- 해석:
  - 90 이상: 매우 높은 변동성
  - 70~90: 높은 변동성
  - 30~70: 평균 변동성
  - 30 미만: 낮은 변동성
"""

    # 키워드 카테고리
    KEYWORD_CATEGORIES = [
        "거래량",     # 거래량 관련 (RVOL)
        "추세",       # 추세 방향 (Trend Strength)
        "섹터",       # 섹터 관련 (Sector Alpha, ETF Sync)
        "변동성",     # 변동성 (Volatility Percentile)
        "특징",       # 종합 특징
    ]

    def __init__(self, language: str = "ko"):
        """
        Args:
            language: 키워드 언어 ('ko' 또는 'en')
        """
        self.language = language

    def get_system_prompt(self) -> str:
        """
        키워드 생성 시스템 프롬프트

        Returns:
            str: 시스템 프롬프트
        """
        today = date.today().strftime('%Y년 %m월 %d일')
        lang_instruction = (
            "한국어로 키워드를 생성하세요." if self.language == "ko"
            else "Generate keywords in English."
        )

        return f"""당신은 Market Movers 종목 분석 전문가입니다.

## 역할
주식 데이터와 5개의 고급 지표를 분석하여, 투자자가 종목을 빠르게 이해할 수 있는
간결하고 정확한 키워드를 생성합니다.

{self.INDICATOR_GUIDE}

## 키워드 생성 규칙

1. **간결성**: 각 키워드는 2-4단어 이내로 작성
2. **정확성**: 지표 수치를 정확히 반영
3. **카테고리 균형**: 5개 카테고리(거래량, 추세, 섹터, 변동성, 특징)를 고르게 분배
4. **언어**: {lang_instruction}
5. **투자자 관점**: 투자 판단에 도움되는 키워드 우선

## 키워드 예시 (한국어)
- 거래량: "폭발적 거래량", "평균 이하 관심"
- 추세: "강한 상승세", "하락 반전"
- 섹터: "섹터 초과수익", "섹터 동조"
- 변동성: "극심한 변동성", "안정적 흐름"
- 특징: "이슈주 의심", "기관 매집"

## 키워드 예시 (영어)
- Volume: "Explosive Volume", "Below Average Interest"
- Trend: "Strong Uptrend", "Downward Reversal"
- Sector: "Sector Outperformer", "Sector Aligned"
- Volatility: "Extreme Volatility", "Stable Flow"
- Feature: "News Driven", "Institutional Buying"

## 출력 형식
반드시 JSON 형식으로 출력하세요:

```json
{{
  "symbol": "AAPL",
  "keywords": [
    {{"text": "폭발적 거래량", "category": "거래량", "confidence": 0.95}},
    {{"text": "강한 상승세", "category": "추세", "confidence": 0.90}},
    {{"text": "섹터 초과수익", "category": "섹터", "confidence": 0.85}},
    {{"text": "높은 변동성", "category": "변동성", "confidence": 0.80}},
    {{"text": "기술주 강세", "category": "특징", "confidence": 0.88}}
  ],
  "summary": "폭발적 거래량과 강한 상승세를 보이는 기술주 강세 종목"
}}
```

**중요**:
- 각 종목당 5-7개의 키워드 생성
- confidence는 0.0~1.0 (해당 키워드의 확신도)
- summary는 1-2문장의 종합 요약
- 모든 카테고리에서 최소 1개씩 키워드 선택

현재 날짜: {today}
"""

    def build_single_stock_prompt(
        self,
        symbol: str,
        company_name: str,
        mover_type: str,
        price_data: Dict[str, Any],
        indicators: Dict[str, Any],
        sector: Optional[str] = None,
        industry: Optional[str] = None
    ) -> str:
        """
        단일 종목 키워드 생성 프롬프트

        Args:
            symbol: 심볼
            company_name: 회사명
            mover_type: 'gainers', 'losers', 'actives'
            price_data: {'price', 'change_percent', 'volume', 'open', 'high', 'low'}
            indicators: {'rvol', 'trend_strength', 'sector_alpha', 'etf_sync_rate', 'volatility_pct'}
            sector: 섹터명 (선택)
            industry: 산업명 (선택)

        Returns:
            str: 사용자 프롬프트
        """
        mover_type_kr = {
            'gainers': '상승 종목',
            'losers': '하락 종목',
            'actives': '거래량 상위 종목'
        }

        lines = [
            f"# {symbol} - {company_name}",
            f"분류: {mover_type_kr.get(mover_type, mover_type)}",
            "",
            "## 가격 정보",
            f"- 현재가: ${price_data.get('price', 'N/A')}",
            f"- 등락률: {price_data.get('change_percent', 'N/A')}%",
            f"- 거래량: {price_data.get('volume', 'N/A'):,}",
        ]

        if price_data.get('open') and price_data.get('high') and price_data.get('low'):
            lines.extend([
                f"- 시가: ${price_data['open']}",
                f"- 고가: ${price_data['high']}",
                f"- 저가: ${price_data['low']}",
            ])

        if sector or industry:
            lines.append("")
            lines.append("## 섹터/산업")
            if sector:
                lines.append(f"- 섹터: {sector}")
            if industry:
                lines.append(f"- 산업: {industry}")

        lines.append("")
        lines.append("## 5개 지표")

        # RVOL
        rvol = indicators.get('rvol')
        if rvol is not None:
            lines.append(f"- RVOL (상대 거래량): {rvol:.2f}x")
        else:
            lines.append("- RVOL: 데이터 없음")

        # Trend Strength
        trend = indicators.get('trend_strength')
        if trend is not None:
            trend_icon = "▲" if trend > 0 else "▼"
            lines.append(f"- Trend Strength (추세 강도): {trend_icon}{abs(trend):.2f}")
        else:
            lines.append("- Trend Strength: 데이터 없음")

        # Sector Alpha
        alpha = indicators.get('sector_alpha')
        if alpha is not None:
            alpha_sign = "+" if alpha > 0 else ""
            lines.append(f"- Sector Alpha (섹터 초과수익): {alpha_sign}{alpha:.2f}%")
        else:
            lines.append("- Sector Alpha: 데이터 없음")

        # ETF Sync Rate
        sync = indicators.get('etf_sync_rate')
        if sync is not None:
            lines.append(f"- ETF Sync Rate (ETF 동행률): {sync:.2f}")
        else:
            lines.append("- ETF Sync Rate: 데이터 없음")

        # Volatility Percentile
        vol_pct = indicators.get('volatility_pct')
        if vol_pct is not None:
            lines.append(f"- Volatility Percentile (변동성 백분위): {vol_pct}/100")
        else:
            lines.append("- Volatility Percentile: 데이터 없음")

        lines.append("")
        lines.append("위 정보를 바탕으로 키워드를 생성하세요.")

        return "\n".join(lines)

    def build_batch_prompt(
        self,
        stocks: List[Dict[str, Any]],
        max_stocks: int = 20
    ) -> str:
        """
        배치 처리용 프롬프트 (최대 20개 종목)

        Args:
            stocks: 종목 리스트 (각 dict는 build_single_stock_prompt의 파라미터 포함)
            max_stocks: 최대 처리 종목 수

        Returns:
            str: 배치 프롬프트
        """
        stocks = stocks[:max_stocks]

        lines = [
            f"# Market Movers 키워드 생성 ({len(stocks)}개 종목)",
            "",
            "아래 종목들에 대해 각각 키워드를 생성하세요.",
            "각 종목마다 JSON 형식으로 출력하고, 전체를 배열로 묶어주세요.",
            "",
            "---",
            ""
        ]

        for idx, stock in enumerate(stocks, 1):
            lines.append(f"## 종목 #{idx}")
            lines.append("")

            single_prompt = self.build_single_stock_prompt(
                symbol=stock['symbol'],
                company_name=stock['company_name'],
                mover_type=stock['mover_type'],
                price_data=stock['price_data'],
                indicators=stock['indicators'],
                sector=stock.get('sector'),
                industry=stock.get('industry')
            )

            lines.append(single_prompt)
            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append("## 출력 형식")
        lines.append("")
        lines.append("```json")
        lines.append("[")
        lines.append("  {")
        lines.append('    "symbol": "AAPL",')
        lines.append('    "keywords": [...],')
        lines.append('    "summary": "..."')
        lines.append("  },")
        lines.append("  {")
        lines.append('    "symbol": "TSLA",')
        lines.append('    "keywords": [...],')
        lines.append('    "summary": "..."')
        lines.append("  }")
        lines.append("]")
        lines.append("```")

        return "\n".join(lines)

    def estimate_tokens(
        self,
        num_stocks: int,
        avg_chars_per_stock: int = 800
    ) -> Dict[str, int]:
        """
        토큰 사용량 추정

        Args:
            num_stocks: 종목 수
            avg_chars_per_stock: 종목당 평균 문자 수

        Returns:
            dict: {'input_tokens', 'estimated_output_tokens', 'total_tokens'}
        """
        # 시스템 프롬프트 토큰 (약 1000 토큰)
        system_tokens = 1000

        # 사용자 프롬프트 토큰 (1 char ≈ 0.4 tokens in Korean)
        user_tokens = int(num_stocks * avg_chars_per_stock * 0.4)

        input_tokens = system_tokens + user_tokens

        # 출력 토큰 추정 (종목당 약 300 토큰)
        # - 키워드 5-7개 * 50 토큰 = 250-350 토큰
        # - summary 1-2문장 = 50-100 토큰
        output_tokens = num_stocks * 300

        return {
            'input_tokens': input_tokens,
            'estimated_output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens
        }


class KeywordResponseParser:
    """
    LLM 응답 파싱 유틸리티

    JSON 응답 파싱 및 유효성 검증
    """

    VALID_CATEGORIES = {
        "ko": ["거래량", "추세", "섹터", "변동성", "특징"],
        "en": ["Volume", "Trend", "Sector", "Volatility", "Feature"]
    }

    @staticmethod
    def parse_single_response(response: str, language: str = "ko") -> Optional[Dict[str, Any]]:
        """
        단일 종목 응답 파싱

        Args:
            response: LLM 응답 텍스트
            language: 키워드 언어

        Returns:
            dict: {'symbol', 'keywords', 'summary'} 또는 None (파싱 실패)
        """
        import json
        import re

        # JSON 블록 추출
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # JSON 블록 없이 그대로 파싱 시도
            json_str = response

        try:
            data = json.loads(json_str)

            # 유효성 검증
            if not isinstance(data, dict):
                return None

            if 'symbol' not in data or 'keywords' not in data:
                return None

            # 키워드 검증
            keywords = data['keywords']
            if not isinstance(keywords, list):
                return None

            valid_keywords = []
            valid_categories = KeywordResponseParser.VALID_CATEGORIES.get(language, [])

            for kw in keywords:
                if not isinstance(kw, dict):
                    continue

                if 'text' not in kw or 'category' not in kw:
                    continue

                # confidence 기본값
                if 'confidence' not in kw:
                    kw['confidence'] = 0.8

                # confidence 범위 검증
                kw['confidence'] = max(0.0, min(1.0, kw['confidence']))

                # 카테고리 검증 (선택)
                # if valid_categories and kw['category'] not in valid_categories:
                #     continue

                valid_keywords.append(kw)

            if not valid_keywords:
                return None

            return {
                'symbol': data['symbol'].upper(),
                'keywords': valid_keywords,
                'summary': data.get('summary', '')
            }

        except json.JSONDecodeError:
            return None
        except Exception:
            return None

    @staticmethod
    def parse_batch_response(response: str, language: str = "ko") -> List[Dict[str, Any]]:
        """
        배치 응답 파싱

        Args:
            response: LLM 응답 텍스트
            language: 키워드 언어

        Returns:
            list: [{'symbol', 'keywords', 'summary'}, ...]
        """
        import json
        import re

        # JSON 배열 블록 추출
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response

        try:
            data = json.loads(json_str)

            if not isinstance(data, list):
                # 단일 객체인 경우 배열로 감싸기
                data = [data]

            results = []
            for item in data:
                parsed = KeywordResponseParser.parse_single_response(
                    json.dumps(item),
                    language
                )
                if parsed:
                    results.append(parsed)

            return results

        except json.JSONDecodeError:
            return []
        except Exception:
            return []
