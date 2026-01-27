"""
Market Movers 키워드 생성 프롬프트 V2

풍부한 컨텍스트(Overview + 뉴스)를 활용한 개선된 프롬프트 시스템
"""

from datetime import date
from typing import Dict, Any, List, Optional
import json


class EnhancedKeywordPromptBuilder:
    """
    향상된 Market Movers 키워드 생성 프롬프트 빌더

    Features:
    - Overview 데이터 활용 (description, fundamentals)
    - 뉴스 데이터 활용 (최근 이벤트)
    - 5개 지표 분석
    - mover_type별 프롬프트 조정
    - Fallback 전략 (데이터 부족 시)
    """

    # 키워드 카테고리 (6개)
    CATEGORIES = [
        "event",       # 뉴스/이벤트 기반
        "product",     # 제품/서비스 관련
        "sector",      # 섹터/산업 트렌드
        "technical",   # 기술적 신호 (지표 기반)
        "fundamental", # 펀더멘털 (Overview 기반)
        "risk",        # 리스크 경고
    ]

    def __init__(self, language: str = "ko"):
        """
        Args:
            language: 키워드 언어 ('ko' 또는 'en')
        """
        self.language = language

    def get_system_prompt(self, mover_type: str) -> str:
        """
        시스템 프롬프트 (mover_type별 조정)

        Args:
            mover_type: 'gainers', 'losers', 'actives'

        Returns:
            시스템 프롬프트
        """
        today = date.today().strftime('%Y년 %m월 %d일')

        # mover_type별 지침
        mover_instructions = {
            'gainers': "상승 요인(뉴스, 실적, 섹터 트렌드 등)을 우선 강조하세요.",
            'losers': "하락 요인(리스크, 악재, 섹터 약세 등)을 우선 강조하세요.",
            'actives': "거래량 급증 이유(이벤트, 변동성, 투자자 관심)를 우선 강조하세요.",
        }

        mover_instruction = mover_instructions.get(mover_type, '')

        lang_instruction = (
            "한국어로 키워드를 생성하세요." if self.language == "ko"
            else "Generate keywords in English."
        )

        return f"""당신은 Market Movers 분석 전문가입니다.

## 역할
주식 종목의 급등/급락/거래량 급증 이유를 분석하여, 투자자가 빠르게 이해할 수 있는
간결하고 정확한 키워드를 생성합니다.

## 입력 데이터
1. **기본 정보**: 종목, 변동률, 섹터, 산업
2. **Overview** (있는 경우): 기업 설명, 시가총액, PE비율, 배당수익률 등
3. **뉴스** (있는 경우): 최근 3개 뉴스 제목
4. **5개 지표**: RVOL, Trend Strength, Sector Alpha, ETF Sync Rate, Volatility Percentile

## 지표 해석 가이드

### 1. RVOL (Relative Volume)
- 의미: 당일 거래량 / 20일 평균 거래량
- 해석:
  - 2.0 이상: 비정상적 관심도 → 주요 이벤트 발생 의심
  - 1.5~2.0: 높은 관심
  - 1.0~1.5: 평균 이상
  - 1.0 미만: 평균 이하

### 2. Trend Strength (추세 강도)
- 의미: (종가-시가) / (고가-저가)
- 해석:
  - +0.7 이상: 강한 상승 추세
  - +0.3~+0.7: 중간 상승
  - -0.3~+0.3: 횡보 (변동성 높음)
  - -0.7 이하: 강한 하락 추세

### 3. Sector Alpha (섹터 초과수익)
- 의미: 종목 수익률 - 섹터 ETF 수익률
- 해석:
  - 양수(+): 섹터 평균 초과 → 개별 이슈 강함
  - 음수(-): 섹터 평균 미달

### 4. ETF Sync Rate (ETF 동행률)
- 의미: 종목과 섹터 ETF의 피어슨 상관계수 (20일)
- 해석:
  - 0.8 이상: 강한 동조 → 섹터 트렌드 따름
  - 0.5 미만: 독립적 움직임 → 개별 이슈 주도

### 5. Volatility Percentile (변동성 백분위)
- 의미: 당일 변동성의 20일 백분위 (0-100)
- 해석:
  - 90 이상: 매우 높은 변동성 → 이벤트 리스크
  - 30 미만: 낮은 변동성 → 안정적 흐름

## 키워드 생성 규칙

1. **데이터 우선순위**:
   - 뉴스 있음 → event 카테고리 필수
   - Overview 있음 → fundamental 카테고리 추가
   - 지표만 있음 → technical, sector 카테고리 사용

2. **간결성**: 각 키워드는 2-6단어 이내

3. **카테고리 균형**:
   - 총 5-7개 키워드 생성
   - 최소 3개 카테고리 사용
   - event, technical은 우선 포함

4. **언어**: {lang_instruction}

5. **Confidence 점수**:
   - 0.9 이상: 뉴스/Overview로 명확히 확인된 정보
   - 0.7~0.9: 지표로 강하게 시사되는 정보
   - 0.5~0.7: 추측/일반적 해석

## mover_type별 지침
{mover_instruction}

## 출력 형식

반드시 JSON 형식으로 출력하세요:

```json
{{
  "symbol": "AAPL",
  "keywords": [
    {{"text": "AI 칩 수요 급증", "category": "event", "confidence": 0.95}},
    {{"text": "폭발적 거래량", "category": "technical", "confidence": 0.90}},
    {{"text": "섹터 초과수익", "category": "sector", "confidence": 0.85}},
    {{"text": "높은 변동성", "category": "technical", "confidence": 0.80}},
    {{"text": "기술주 강세", "category": "sector", "confidence": 0.75}}
  ],
  "summary": "AI 칩 수요 급증으로 폭발적 거래량을 기록하며 섹터 평균을 초과하는 강세"
}}
```

## 키워드 예시 (한국어)

**event**: "실적 서프라이즈", "신제품 발표", "M&A 루머"
**product**: "아이폰 판매 호조", "클라우드 성장", "신약 승인"
**sector**: "기술주 강세", "에너지 섹터 회복", "반도체 업황"
**technical**: "폭발적 거래량", "강한 상승세", "기술적 돌파"
**fundamental**: "밸류에이션 매력", "배당 수익률 상승", "부채비율 개선"
**risk**: "규제 리스크", "경쟁 심화", "실적 악화 우려"

## 키워드 예시 (영어)

**event**: "Earnings Surprise", "Product Launch", "M&A Rumor"
**product**: "iPhone Sales Growth", "Cloud Expansion", "Drug Approval"
**sector**: "Tech Rally", "Energy Recovery", "Chip Cycle"
**technical**: "Explosive Volume", "Strong Uptrend", "Technical Breakout"
**fundamental**: "Valuation Attractive", "Dividend Yield Up", "Debt Reduction"
**risk**: "Regulatory Risk", "Competition Intensified", "Earnings Concern"

## Fallback 전략

**데이터 부족 시 키워드 생성 방법**:

1. **Overview 없음** → fundamental 카테고리 제외, technical/sector 중심
2. **뉴스 없음** → event 카테고리 제외, 지표 기반 키워드 생성
3. **둘 다 없음** → 기본 정보(섹터, mover_type) + 지표만 사용

최소 키워드 예시:
- 섹터 기반: "기술주 강세"
- mover_type 기반: "급등 종목"
- 지표 기반: "폭발적 거래량"

현재 날짜: {today}
"""

    def build_user_prompt(
        self,
        context: Dict[str, Any]
    ) -> str:
        """
        사용자 프롬프트 구성 (단일 종목)

        Args:
            context: KeywordContextBuilder가 생성한 컨텍스트

        Returns:
            사용자 프롬프트
        """
        basic = context['basic']
        overview = context.get('overview')
        news = context.get('news')
        indicators = context['indicators']

        lines = [
            f"# {basic['symbol']} - {basic['company_name']}",
            "",
            "## 기본 정보",
            f"- 변동률: {basic['price_data'].get('change_percent', 'N/A')}%",
            f"- 현재가: ${basic['price_data'].get('price', 'N/A')}",
            f"- 거래량: {basic['price_data'].get('volume', 'N/A'):,}",
        ]

        if basic.get('sector'):
            lines.append(f"- 섹터: {basic['sector']}")
        if basic.get('industry'):
            lines.append(f"- 산업: {basic['industry']}")

        # Overview
        if overview:
            lines.append("")
            lines.append("## Overview")

            if overview.get('description'):
                lines.append(f"- 기업 설명: {overview['description']}")

            if overview.get('market_cap'):
                lines.append(f"- 시가총액: {overview['market_cap']}")
            if overview.get('pe_ratio'):
                lines.append(f"- PE Ratio: {overview['pe_ratio']}")
            if overview.get('dividend_yield'):
                lines.append(f"- 배당수익률: {overview['dividend_yield']}%")
            if overview.get('beta'):
                lines.append(f"- 베타: {overview['beta']}")

        # 뉴스
        if news:
            lines.append("")
            lines.append("## 최근 뉴스")

            for idx, item in enumerate(news, 1):
                sentiment_icon = {
                    'positive': '🟢',
                    'negative': '🔴',
                    'neutral': '⚪'
                }.get(item.get('sentiment', 'neutral'), '⚪')

                lines.append(f"{idx}. {sentiment_icon} {item['title']} ({item['source']})")

        # 지표
        lines.append("")
        lines.append("## 5개 지표")

        rvol = indicators.get('rvol')
        if rvol is not None:
            lines.append(f"- RVOL: {rvol:.2f}x")
        else:
            lines.append("- RVOL: N/A")

        trend = indicators.get('trend_strength')
        if trend is not None:
            trend_icon = "▲" if trend > 0 else "▼"
            lines.append(f"- Trend Strength: {trend_icon}{abs(trend):.2f}")
        else:
            lines.append("- Trend Strength: N/A")

        alpha = indicators.get('sector_alpha')
        if alpha is not None:
            alpha_sign = "+" if alpha > 0 else ""
            lines.append(f"- Sector Alpha: {alpha_sign}{alpha:.2f}%")
        else:
            lines.append("- Sector Alpha: N/A")

        sync = indicators.get('etf_sync_rate')
        if sync is not None:
            lines.append(f"- ETF Sync Rate: {sync:.2f}")
        else:
            lines.append("- ETF Sync Rate: N/A")

        vol_pct = indicators.get('volatility_pct')
        if vol_pct is not None:
            lines.append(f"- Volatility Percentile: {vol_pct}/100")
        else:
            lines.append("- Volatility Percentile: N/A")

        lines.append("")
        lines.append("위 정보를 바탕으로 키워드를 생성하세요.")

        return "\n".join(lines)

    def build_batch_prompt(
        self,
        contexts: List[Dict[str, Any]],
        mover_type: str
    ) -> str:
        """
        배치 처리용 프롬프트 (최대 20개 종목)

        Args:
            contexts: KeywordContextBuilder가 생성한 컨텍스트 리스트
            mover_type: 'gainers', 'losers', 'actives'

        Returns:
            배치 프롬프트
        """
        lines = [
            f"# Market Movers 키워드 생성 ({len(contexts)}개 종목)",
            "",
            "아래 종목들에 대해 각각 키워드를 생성하세요.",
            "각 종목마다 JSON 형식으로 출력하고, 전체를 배열로 묶어주세요.",
            "",
            "---",
            ""
        ]

        for idx, context in enumerate(contexts, 1):
            lines.append(f"## 종목 #{idx}")
            lines.append("")

            user_prompt = self.build_user_prompt(context)
            lines.append(user_prompt)

            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append("## 출력 형식")
        lines.append("")
        lines.append("```json")
        lines.append("[")
        lines.append("  {")
        lines.append('    "symbol": "AAPL",')
        lines.append('    "keywords": [')
        lines.append('      {"text": "...", "category": "event", "confidence": 0.95},')
        lines.append('      {"text": "...", "category": "technical", "confidence": 0.90}')
        lines.append('    ],')
        lines.append('    "summary": "..."')
        lines.append("  },")
        lines.append("  ...")
        lines.append("]")
        lines.append("```")

        return "\n".join(lines)


class EnhancedKeywordResponseParser:
    """
    향상된 LLM 응답 파싱 유틸리티

    카테고리별 키워드 분류 및 유효성 검증
    """

    VALID_CATEGORIES = [
        "event",
        "product",
        "sector",
        "technical",
        "fundamental",
        "risk",
    ]

    @staticmethod
    def parse_single_response(response: str) -> Optional[Dict[str, Any]]:
        """
        단일 종목 응답 파싱

        Args:
            response: LLM 응답 텍스트

        Returns:
            {
                'symbol': str,
                'keywords': [
                    {'text': str, 'category': str, 'confidence': float},
                    ...
                ],
                'summary': str
            }
            또는 None (파싱 실패)
        """
        import re

        # JSON 블록 추출
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
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
            for kw in keywords:
                if not isinstance(kw, dict):
                    continue

                if 'text' not in kw or 'category' not in kw:
                    continue

                # confidence 기본값
                if 'confidence' not in kw:
                    kw['confidence'] = 0.7

                # confidence 범위 검증
                kw['confidence'] = max(0.0, min(1.0, float(kw['confidence'])))

                # 카테고리 검증 (유효하지 않으면 'technical'로 변경)
                if kw['category'] not in EnhancedKeywordResponseParser.VALID_CATEGORIES:
                    kw['category'] = 'technical'

                valid_keywords.append({
                    'text': str(kw['text']).strip(),
                    'category': kw['category'],
                    'confidence': kw['confidence']
                })

            if not valid_keywords:
                return None

            return {
                'symbol': data['symbol'].upper(),
                'keywords': valid_keywords,
                'summary': data.get('summary', '')
            }

        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    @staticmethod
    def parse_batch_response(response: str) -> List[Dict[str, Any]]:
        """
        배치 응답 파싱

        Args:
            response: LLM 응답 텍스트

        Returns:
            [{'symbol', 'keywords', 'summary'}, ...]
        """
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
                parsed = EnhancedKeywordResponseParser.parse_single_response(
                    json.dumps(item)
                )
                if parsed:
                    results.append(parsed)

            return results

        except (json.JSONDecodeError, ValueError, TypeError):
            return []

    @staticmethod
    def get_keywords_by_category(
        keywords: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        카테고리별 키워드 그룹화

        Args:
            keywords: 키워드 리스트

        Returns:
            {
                'event': [...],
                'technical': [...],
                ...
            }
        """
        grouped = {cat: [] for cat in EnhancedKeywordResponseParser.VALID_CATEGORIES}

        for kw in keywords:
            category = kw.get('category', 'technical')
            if category in grouped:
                grouped[category].append(kw)

        # 빈 카테고리 제거
        return {k: v for k, v in grouped.items() if v}
