'use client';

import { useState, useMemo } from 'react';
import { Plus, ExternalLink, TrendingUp, TrendingDown, ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-react';
import Link from 'next/link';
import type { ScreenerStock } from '@/services/strategyService';
import { KeywordList } from '@/components/keywords/KeywordList';

type SortField = 'price' | 'change' | 'market_cap' | 'volume' | 'dividend_yield' | null;
type SortDirection = 'asc' | 'desc';

interface ScreenerTableProps {
  stocks: ScreenerStock[];
  onAddToBasket?: (symbol: string) => void;
  keywords?: Record<string, string[]>;  // symbol -> keywords 매핑
  isLoadingKeywords?: boolean;
}

// 시가총액 포맷팅 함수
function formatMarketCap(marketCap?: number, formatted?: string): string {
  if (formatted) return formatted;
  if (!marketCap) return '-';

  if (marketCap >= 1_000_000_000_000) {
    return `$${(marketCap / 1_000_000_000_000).toFixed(1)}T`;
  } else if (marketCap >= 1_000_000_000) {
    return `$${(marketCap / 1_000_000_000).toFixed(1)}B`;
  } else if (marketCap >= 1_000_000) {
    return `$${(marketCap / 1_000_000).toFixed(1)}M`;
  }
  return `$${marketCap.toLocaleString()}`;
}

// 거래량 포맷팅 함수
function formatVolume(volume?: number, formatted?: string): string {
  if (formatted) return formatted;
  if (!volume) return '-';

  if (volume >= 1_000_000_000) {
    return `${(volume / 1_000_000_000).toFixed(1)}B`;
  } else if (volume >= 1_000_000) {
    return `${(volume / 1_000_000).toFixed(1)}M`;
  } else if (volume >= 1_000) {
    return `${(volume / 1_000).toFixed(1)}K`;
  }
  return volume.toLocaleString();
}

export function ScreenerTable({ stocks, onAddToBasket, keywords = {}, isLoadingKeywords = false }: ScreenerTableProps) {
  const [sortField, setSortField] = useState<SortField>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // 정렬된 종목 목록
  const sortedStocks = useMemo(() => {
    if (!sortField) return stocks;

    return [...stocks].sort((a, b) => {
      let aValue: number | null = null;
      let bValue: number | null = null;

      switch (sortField) {
        case 'price':
          aValue = a.price ?? null;
          bValue = b.price ?? null;
          break;
        case 'change':
          aValue = a.changes_percentage ?? a.change ?? null;
          bValue = b.changes_percentage ?? b.change ?? null;
          break;
        case 'market_cap':
          aValue = a.market_cap ?? null;
          bValue = b.market_cap ?? null;
          break;
        case 'volume':
          aValue = a.volume ?? null;
          bValue = b.volume ?? null;
          break;
        case 'dividend_yield':
          aValue = a.dividend_yield ?? null;
          bValue = b.dividend_yield ?? null;
          break;
      }

      // null 값 처리: null은 항상 뒤로
      if (aValue === null && bValue === null) return 0;
      if (aValue === null) return 1;
      if (bValue === null) return -1;

      // 정렬 방향에 따라 비교
      const comparison = aValue - bValue;
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [stocks, sortField, sortDirection]);

  // 정렬 핸들러
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // 같은 필드 클릭 시 방향 토글
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      // 다른 필드 클릭 시 해당 필드로 변경, 기본 내림차순
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // 정렬 아이콘 컴포넌트
  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-3 w-3 text-[#484F58] ml-1" />;
    }
    return sortDirection === 'asc'
      ? <ArrowUp className="h-3 w-3 text-[#58A6FF] ml-1" />
      : <ArrowDown className="h-3 w-3 text-[#58A6FF] ml-1" />;
  };

  if (stocks.length === 0) {
    return (
      <div className="rounded-lg border border-[#30363D] bg-[#161B22] p-8 text-center">
        <p className="text-sm text-[#8B949E]">조건에 맞는 종목이 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="overflow-hidden rounded-lg border border-[#30363D]">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#30363D] bg-[#0D1117]">
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#8B949E]">종목</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#8B949E]">거래소</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#8B949E]">섹터</th>
                <th
                  onClick={() => handleSort('price')}
                  className="px-4 py-3 text-right text-xs font-semibold text-[#8B949E] cursor-pointer hover:text-[#E6EDF3] transition-colors select-none"
                >
                  <div className="flex items-center justify-end">
                    가격
                    <SortIcon field="price" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('change')}
                  className="px-4 py-3 text-right text-xs font-semibold text-[#8B949E] cursor-pointer hover:text-[#E6EDF3] transition-colors select-none"
                >
                  <div className="flex items-center justify-end">
                    변동률
                    <SortIcon field="change" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('market_cap')}
                  className="px-4 py-3 text-right text-xs font-semibold text-[#8B949E] cursor-pointer hover:text-[#E6EDF3] transition-colors select-none"
                >
                  <div className="flex items-center justify-end">
                    시가총액
                    <SortIcon field="market_cap" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('volume')}
                  className="px-4 py-3 text-right text-xs font-semibold text-[#8B949E] cursor-pointer hover:text-[#E6EDF3] transition-colors select-none"
                >
                  <div className="flex items-center justify-end">
                    거래량 (주)
                    <SortIcon field="volume" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort('dividend_yield')}
                  className="px-4 py-3 text-right text-xs font-semibold text-[#8B949E] cursor-pointer hover:text-[#E6EDF3] transition-colors select-none"
                >
                  <div className="flex items-center justify-end">
                    배당률
                    <SortIcon field="dividend_yield" />
                  </div>
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[#8B949E]">베타</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-[#8B949E]">유형</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-[#8B949E]">AI 키워드</th>
                {onAddToBasket && (
                  <th className="px-4 py-3 text-center text-xs font-semibold text-[#8B949E]">액션</th>
                )}
              </tr>
            </thead>
          <tbody>
            {sortedStocks.map((stock) => {
              const displayName = stock.company_name || stock.name || '';
              const exchangeName = stock.exchange_short_name || stock.exchange || '-';
              const changePercent = stock.changes_percentage ?? stock.change ?? null;
              const isPositive = changePercent != null && changePercent >= 0;

              return (
                <tr
                  key={stock.symbol}
                  className="border-b border-[#30363D] transition-colors hover:bg-[#21262D]"
                >
                  {/* 종목명 */}
                  <td className="px-4 py-3">
                    <Link href={`/stocks/${stock.symbol}`} className="group">
                      <div className="flex items-center gap-1">
                        <span className="font-medium text-[#E6EDF3] group-hover:text-[#58A6FF]">
                          {stock.symbol}
                        </span>
                        <ExternalLink className="h-3 w-3 text-[#8B949E] opacity-0 transition-opacity group-hover:opacity-100" />
                      </div>
                      <div className="max-w-[180px] truncate text-xs text-[#8B949E]" title={displayName}>
                        {displayName}
                      </div>
                    </Link>
                  </td>

                  {/* 거래소 */}
                  <td className="px-4 py-3">
                    <span className="inline-flex rounded bg-[#21262D] px-2 py-0.5 text-xs font-medium text-[#8B949E]">
                      {exchangeName}
                    </span>
                  </td>

                  {/* 섹터 */}
                  <td className="px-4 py-3">
                    <div className="max-w-[120px] truncate text-xs text-[#8B949E]" title={stock.sector}>
                      {stock.sector || '-'}
                    </div>
                  </td>

                  {/* 가격 */}
                  <td className="px-4 py-3 text-right">
                    <div className="font-mono text-sm text-[#E6EDF3]">
                      {stock.price
                        ? `$${stock.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                        : '-'}
                    </div>
                  </td>

                  {/* 변동률 */}
                  <td className="px-4 py-3 text-right">
                    {changePercent != null ? (
                      <div className="flex items-center justify-end gap-1">
                        {isPositive ? (
                          <TrendingUp className="h-3 w-3 text-[#3FB950]" />
                        ) : (
                          <TrendingDown className="h-3 w-3 text-[#F85149]" />
                        )}
                        <span
                          className={`text-sm font-medium ${isPositive ? 'text-[#3FB950]' : 'text-[#F85149]'}`}
                        >
                          {isPositive ? '+' : ''}{changePercent.toFixed(2)}%
                        </span>
                      </div>
                    ) : (
                      <span className="text-sm text-[#8B949E]">-</span>
                    )}
                  </td>

                  {/* 시가총액 */}
                  <td className="px-4 py-3 text-right">
                    <div className="text-sm text-[#E6EDF3]">
                      {formatMarketCap(stock.market_cap, stock.formatted_market_cap)}
                    </div>
                  </td>

                  {/* 거래량 */}
                  <td className="px-4 py-3 text-right">
                    <div className="text-sm text-[#8B949E]">
                      {formatVolume(stock.volume, stock.formatted_volume)}
                    </div>
                  </td>

                  {/* 배당률 */}
                  <td className="px-4 py-3 text-right">
                    <div className="text-sm text-[#E6EDF3]">
                      {stock.dividend_yield != null
                        ? `${stock.dividend_yield.toFixed(2)}%`
                        : '-'}
                    </div>
                  </td>

                  {/* 베타 */}
                  <td className="px-4 py-3 text-right">
                    <div className="text-sm text-[#E6EDF3]">
                      {stock.beta != null ? stock.beta.toFixed(2) : '-'}
                    </div>
                  </td>

                  {/* 유형 (ETF/펀드/주식) */}
                  <td className="px-4 py-3 text-center">
                    {stock.is_etf ? (
                      <span className="inline-flex rounded bg-[#388BFD]/20 px-2 py-0.5 text-xs font-medium text-[#58A6FF]">
                        ETF
                      </span>
                    ) : stock.is_fund ? (
                      <span className="inline-flex rounded bg-[#A371F7]/20 px-2 py-0.5 text-xs font-medium text-[#A371F7]">
                        펀드
                      </span>
                    ) : (
                      <span className="inline-flex rounded bg-[#238636]/20 px-2 py-0.5 text-xs font-medium text-[#3FB950]">
                        주식
                      </span>
                    )}
                  </td>

                  {/* AI 키워드 */}
                  <td className="px-4 py-3">
                    <div className="max-w-[200px]">
                      <KeywordList
                        keywords={keywords[stock.symbol] || []}
                        isLoading={isLoadingKeywords}
                        maxVisible={3}
                        size="sm"
                        emptyMessage="-"
                      />
                    </div>
                  </td>

                  {/* 액션 */}
                  {onAddToBasket && (
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => onAddToBasket(stock.symbol)}
                        className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-[#58A6FF] transition-colors hover:bg-[#58A6FF]/10"
                        aria-label={`${stock.symbol}을(를) 바구니에 추가`}
                      >
                        <Plus className="h-3 w-3" />
                        바구니
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
          </table>
        </div>
      </div>

      {/* 단위 범례 */}
      <div className="flex items-center gap-4 rounded-lg border border-[#30363D] bg-[#0D1117] px-4 py-2 text-xs text-[#8B949E]">
        <span className="font-semibold">단위:</span>
        <span>K = 천</span>
        <span>M = 백만</span>
        <span>B = 십억</span>
        <span>T = 조</span>
      </div>
    </div>
  );
}
