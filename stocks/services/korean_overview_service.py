"""
S&P 500 종목 한글 기업 개요 생성 서비스

Gemini 2.5 Flash를 사용하여 기업 정보를 한국어로 정리합니다.
"""

import json
import logging
import time

from django.conf import settings
from django.utils import timezone
from google import genai
from google.genai import types

from stocks.models import Stock, StockOverviewKo, SP500Constituent

logger = logging.getLogger(__name__)


class KoreanOverviewService:
    """한글 기업 개요 생성 서비스"""

    MODEL = "gemini-2.5-flash"
    TEMPERATURE = 0.3
    RPM_DELAY = 4  # Gemini Free: 15 RPM

    def __init__(self):
        api_key = (
            getattr(settings, 'GOOGLE_AI_API_KEY', None)
            or getattr(settings, 'GEMINI_API_KEY', None)
        )
        if not api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
        self.client = genai.Client(api_key=api_key)

    def generate_for_stock(self, symbol: str, force: bool = False) -> StockOverviewKo:
        """
        단일 종목 한글 개요 생성

        Args:
            symbol: 종목 심볼
            force: 기존 개요 덮어쓰기 여부
        """
        symbol = symbol.upper()
        stock = Stock.objects.filter(symbol=symbol).first()
        if not stock:
            raise ValueError(f"Stock {symbol} not found")

        # 이미 존재하는 경우
        if not force:
            existing = StockOverviewKo.objects.filter(stock=stock).first()
            if existing:
                logger.info(f"Korean overview already exists for {symbol}, skipping")
                return existing

        # 프롬프트 구성
        prompt = self._build_prompt(stock)

        start_time = time.time()

        try:
            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.TEMPERATURE,
                    response_mime_type="application/json",
                ),
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            # JSON 파싱
            result = json.loads(response.text)

            # DB 저장
            overview_ko, created = StockOverviewKo.objects.update_or_create(
                stock=stock,
                defaults={
                    'summary': result.get('summary', ''),
                    'business_model': result.get('business_model', ''),
                    'competitive_edge': result.get('competitive_edge', ''),
                    'risk_factors': result.get('risk_factors', ''),
                    'llm_model': self.MODEL,
                    'generated_at': timezone.now(),
                    'generation_time_ms': elapsed_ms,
                }
            )

            action = "생성" if created else "갱신"
            logger.info(f"Korean overview {action}: {symbol} ({elapsed_ms}ms)")
            return overview_ko

        except Exception as e:
            logger.error(f"Failed to generate Korean overview for {symbol}: {e}")
            raise

    def batch_generate(self, symbols: list[str] = None, force: bool = False) -> dict:
        """
        배치 한글 개요 생성 (S&P 500)

        Args:
            symbols: 대상 심볼 리스트 (None이면 S&P 500 중 미생성 종목)
            force: 전체 재생성 여부
        """
        if symbols is None:
            # S&P 500 중 한글 개요 미생성 종목
            sp500_symbols = list(
                SP500Constituent.objects.filter(is_active=True)
                .values_list('symbol', flat=True)
            )
            if force:
                symbols = sp500_symbols
            else:
                existing = set(
                    StockOverviewKo.objects.filter(stock_id__in=sp500_symbols)
                    .values_list('stock_id', flat=True)
                )
                symbols = [s for s in sp500_symbols if s not in existing]

        total = len(symbols)
        success = 0
        errors = 0

        logger.info(f"Batch Korean overview: {total} stocks to process (force={force})")

        for i, symbol in enumerate(symbols):
            try:
                self.generate_for_stock(symbol, force=force)
                success += 1
            except Exception as e:
                logger.error(f"[{i+1}/{total}] Failed {symbol}: {e}")
                errors += 1

            # Rate limiting
            if i < total - 1:
                time.sleep(self.RPM_DELAY)

            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i+1}/{total} (success={success}, errors={errors})")

        result = {
            'total': total,
            'success': success,
            'errors': errors,
        }
        logger.info(f"Batch Korean overview completed: {result}")
        return result

    def _build_prompt(self, stock: Stock) -> str:
        """LLM 프롬프트 구성"""
        # 재무 데이터 수집
        financials = []
        if stock.market_capitalization:
            cap = float(stock.market_capitalization)
            if cap >= 1e12:
                financials.append(f"시가총액: ${cap/1e12:.1f}T")
            elif cap >= 1e9:
                financials.append(f"시가총액: ${cap/1e9:.1f}B")
        if stock.pe_ratio:
            financials.append(f"PER: {float(stock.pe_ratio):.1f}")
        if stock.eps:
            financials.append(f"EPS: ${float(stock.eps):.2f}")
        if stock.dividend_yield:
            financials.append(f"배당수익률: {float(stock.dividend_yield)*100:.2f}%")
        if stock.profit_margin:
            financials.append(f"순이익률: {float(stock.profit_margin)*100:.1f}%")
        if stock.return_on_equity_ttm:
            financials.append(f"ROE: {float(stock.return_on_equity_ttm)*100:.1f}%")
        if stock.revenue_ttm:
            rev = float(stock.revenue_ttm)
            if rev >= 1e9:
                financials.append(f"연매출: ${rev/1e9:.1f}B")
        if stock.beta:
            financials.append(f"Beta: {float(stock.beta):.2f}")

        financials_str = ", ".join(financials) if financials else "재무 데이터 없음"

        description_str = stock.description[:500] if stock.description else "설명 없음"

        return f"""당신은 한국 투자자를 위한 기업 분석 전문가입니다.
아래 기업 정보를 바탕으로 한국어 기업 개요를 작성하세요.

## 기업 정보
- 심볼: {stock.symbol}
- 기업명: {stock.stock_name or stock.symbol}
- 섹터: {stock.sector or '미분류'}
- 산업: {stock.industry or '미분류'}
- 거래소: {stock.exchange or ''}
- 재무: {financials_str}
- 영문 설명: {description_str}

## 작성 지침
1. 한국 투자자가 이해하기 쉬운 자연스러운 한국어로 작성
2. 객관적 사실 중심, 투자 권유 표현 금지
3. 전문 용어는 괄호 안에 영문 병기 (예: 주당순이익(EPS))
4. 각 섹션은 2-4문장으로 간결하게

## 출력 형식 (JSON)
{{
  "summary": "기업의 핵심 사업과 시장 위치를 요약한 2-3문단 (300-500자)",
  "business_model": "매출 구조와 핵심 사업 부문 설명 (200-300자)",
  "competitive_edge": "경쟁 우위, 기술적 해자(moat), 시장 지배력 (200-300자)",
  "risk_factors": "투자 시 고려할 주요 리스크 요인 2-3가지 (200-300자)"
}}"""
