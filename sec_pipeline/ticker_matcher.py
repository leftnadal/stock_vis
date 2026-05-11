"""
SEC-PR-7: Ticker 매칭 엔진

3단계 매칭:
  1순위: CompanyAlias (context_sector 포함, 없으면 범용)
  2순위: Stock.stock_name 정확 매칭
  3순위: rapidfuzz token_sort_ratio ≥ 85%

미매칭 시 UnmatchedCompanyQueue 적재.
"""

import logging
from typing import Optional

from rapidfuzz import fuzz

from stocks.models import Stock

logger = logging.getLogger(__name__)


class TickerMatcher:
    """LLM 추출 회사명 → Ticker 매칭."""

    def __init__(self):
        # Stock 이름 → symbol 캐시 (lazy load)
        self._stock_map: dict = {}
        self._loaded = False

    def _ensure_loaded(self):
        """Stock 테이블 캐시 로드."""
        if self._loaded:
            return
        stocks = Stock.objects.values_list('symbol', 'stock_name')
        for symbol, name in stocks:
            if name:
                self._stock_map[name.lower()] = symbol
                # 약어 변형도 등록 (Inc., Corp. 등 제거)
                cleaned = self._clean_name(name)
                if cleaned:
                    self._stock_map[cleaned] = symbol
        self._loaded = True

    def match(self, company_name: str, context_sector: str = '') -> tuple:
        """
        회사명 → (ticker | None, method).

        Returns:
            (ticker, method) — method: 'alias', 'exact', 'fuzzy', None
        """
        if not company_name or len(company_name) < 2:
            return None, None

        name = company_name.strip()

        # 1순위: CompanyAlias
        ticker = self._match_alias(name, context_sector)
        if ticker:
            return ticker, 'alias'

        # 2순위: Stock.stock_name 정확 매칭
        self._ensure_loaded()
        ticker = self._match_exact(name)
        if ticker:
            return ticker, 'exact'

        # 3순위: rapidfuzz ≥ 85%
        ticker, score = self._match_fuzzy(name)
        if ticker:
            return ticker, 'fuzzy'

        return None, None

    def match_with_queue(self, company_name: str, evidence,
                         document, source_symbol: str):
        """
        매칭 시도 + 실패 시 UnmatchedCompanyQueue 적재.

        Args:
            company_name: LLM 추출 회사명
            evidence: SupplyChainEvidence 인스턴스
            document: RawDocumentStore 인스턴스
            source_symbol: 어떤 기업의 10-K에서 나왔는지
        """
        from .models import UnmatchedCompanyQueue

        # 소스 기업의 sector 가져오기
        source_stock = Stock.objects.filter(symbol=source_symbol.upper()).first()
        context_sector = source_stock.sector if source_stock else ''

        ticker, method = self.match(company_name, context_sector)

        if ticker:
            # 매칭 성공 → evidence.target_company 업데이트
            target_stock = Stock.objects.filter(symbol=ticker).first()
            if target_stock:
                evidence.target_company = target_stock
                evidence.neo4j_dirty = True
                evidence.save(update_fields=['target_company', 'neo4j_dirty'])
                logger.info(
                    f"Matched: {company_name} → {ticker} (method={method})"
                )
            return ticker, method

        # 매칭 실패 → 큐 적재
        queue_entry, created = UnmatchedCompanyQueue.objects.get_or_create(
            raw_company_name=company_name,
            defaults={
                'source_symbol': source_symbol.upper(),
                'status': 'pending',
                'source_sectors': [context_sector] if context_sector else [],
                'fuzzy_candidates': self._get_fuzzy_candidates(company_name),
            }
        )

        if not created:
            # 기존 건: occurrence_count 증가, source_sectors 축적
            queue_entry.occurrence_count += 1
            if context_sector:
                sectors = set(queue_entry.source_sectors or [])
                sectors.add(context_sector)
                queue_entry.source_sectors = sorted(sectors)
            queue_entry.save(update_fields=['occurrence_count', 'source_sectors'])

        logger.debug(f"Unmatched: {company_name} (source={source_symbol})")
        return None, None

    # ── Private methods ──

    def _match_alias(self, name: str, context_sector: str) -> Optional[str]:
        """CompanyAlias 테이블 조회."""
        from .models import CompanyAlias

        # context_sector 우선 조회
        if context_sector:
            alias = CompanyAlias.objects.filter(
                alias__iexact=name,
                context_sector__iexact=context_sector,
            ).first()
            if alias:
                return alias.ticker

        # 범용 (context_sector='') 조회
        alias = CompanyAlias.objects.filter(
            alias__iexact=name,
            context_sector='',
        ).first()
        return alias.ticker if alias else None

    def _match_exact(self, name: str) -> Optional[str]:
        """Stock.stock_name 정확 매칭."""
        cleaned = name.lower()
        if cleaned in self._stock_map:
            return self._stock_map[cleaned]

        # cleaned 버전으로도 시도
        cleaned2 = self._clean_name(name)
        if cleaned2 and cleaned2 in self._stock_map:
            return self._stock_map[cleaned2]

        return None

    def _match_fuzzy(self, name: str, threshold: int = 80) -> tuple:
        """rapidfuzz token_sort_ratio 매칭."""
        self._ensure_loaded()
        best_score = 0
        best_symbol = None

        for stock_name, symbol in self._stock_map.items():
            score = fuzz.token_sort_ratio(name.lower(), stock_name)
            if score > best_score:
                best_score = score
                best_symbol = symbol

        if best_score >= threshold:
            return best_symbol, best_score
        return None, best_score

    def _get_fuzzy_candidates(self, name: str, top_k: int = 5) -> list:
        """상위 fuzzy 후보 리스트."""
        self._ensure_loaded()
        scored = []
        seen_symbols = set()

        for stock_name, symbol in self._stock_map.items():
            if symbol in seen_symbols:
                continue
            score = fuzz.token_sort_ratio(name.lower(), stock_name)
            if score >= 50:
                stock = Stock.objects.filter(symbol=symbol).first()
                scored.append({
                    'ticker': symbol,
                    'name': stock.stock_name if stock else stock_name,
                    'score': round(score / 100, 2),
                })
                seen_symbols.add(symbol)

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _clean_name(name: str) -> str:
        """회사명에서 Inc., Corp., Ltd. 등 접미사 제거."""
        import re
        cleaned = re.sub(
            r',?\s*(Inc\.?|Corp\.?|Corporation|Ltd\.?|Limited|Co\.?|'
            r'Company|LLC|L\.P\.|PLC|S\.A\.?|N\.V\.?|AG|SE|Group)\.?\s*$',
            '', name, flags=re.IGNORECASE,
        ).strip()
        return cleaned.lower() if cleaned else ''
