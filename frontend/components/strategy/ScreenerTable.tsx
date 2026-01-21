'use client';

import { Plus, ExternalLink, TrendingUp, TrendingDown } from 'lucide-react';
import Link from 'next/link';
import type { ScreenerStock } from '@/services/strategyService';

interface ScreenerTableProps {
  stocks: ScreenerStock[];
  onAddToBasket?: (symbol: string) => void;
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

export function ScreenerTable({ stocks, onAddToBasket }: ScreenerTableProps) {
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
                <th className="px-4 py-3 text-right text-xs font-semibold text-[#8B949E]">가격</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[#8B949E]">변동률</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[#8B949E]">시가총액</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[#8B949E]">거래량 (주)</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[#8B949E]">배당률</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[#8B949E]">베타</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-[#8B949E]">유형</th>
                {onAddToBasket && (
                  <th className="px-4 py-3 text-center text-xs font-semibold text-[#8B949E]">액션</th>
                )}
              </tr>
            </thead>
          <tbody>
            {stocks.map((stock) => {
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
