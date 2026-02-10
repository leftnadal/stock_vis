'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { ChevronDown, ChevronUp, RefreshCw, Sparkles, AlertCircle } from 'lucide-react';
import type { ScreenerFilters, ChainStock, ChainSightData } from '@/types/screener';
import { screenerService } from '@/services/screenerService';

interface ChainSightPanelProps {
  symbols: string[];
  filters: ScreenerFilters;
  isLoading?: boolean;
  className?: string;
}

interface StockCardProps {
  stock: ChainStock;
}

function StockCard({ stock }: StockCardProps) {
  // 유사도 퍼센트 표시
  const similarityPercent = Math.round((stock.similarity ?? 0) * 100);
  const sector = stock.metrics?.sector;

  return (
    <Link
      href={`/stocks/${stock.symbol}`}
      className="flex flex-col items-center gap-1 rounded-lg border border-[#30363D] bg-[#0D1117] p-3 transition-colors hover:border-[#58A6FF]/50"
    >
      <span className="text-sm font-bold text-[#58A6FF]">{stock.symbol}</span>
      <span className="text-xs text-[#8B949E]">
        유사도 {similarityPercent}%
      </span>
      {sector && (
        <span className="text-[10px] text-[#6E7681] truncate max-w-full">
          {sector}
        </span>
      )}
    </Link>
  );
}

function ChainSection({
  title,
  description,
  helpText,
  stocks,
  isLoading,
}: {
  title: string;
  description: string;
  helpText?: string;
  stocks: ChainStock[];
  isLoading: boolean;
}) {
  const [showAll, setShowAll] = useState(false);
  const displayStocks = showAll ? stocks : stocks.slice(0, 3);

  if (isLoading) {
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-[#E6EDF3]">{title}</h3>
        <div className="grid grid-cols-3 gap-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 animate-pulse rounded-lg bg-[#30363D]"
            />
          ))}
        </div>
      </div>
    );
  }

  if (stocks.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-[#E6EDF3]">
        {title} ({stocks.length})
      </h3>
      <div className="grid grid-cols-3 gap-2 md:grid-cols-4 lg:grid-cols-5">
        {displayStocks.map((stock, idx) => (
          <StockCard key={`${stock.symbol}-${idx}`} stock={stock} />
        ))}
        {!showAll && stocks.length > 3 && (
          <button
            onClick={() => setShowAll(true)}
            className="flex flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-[#30363D] bg-[#0D1117] p-3 text-xs text-[#8B949E] transition-colors hover:border-[#58A6FF]/50 hover:text-[#58A6FF]"
          >
            <span className="font-medium">+{stocks.length - 3}</span>
            <span>더보기</span>
          </button>
        )}
      </div>
      {helpText && (
        <p className="text-xs text-[#8B949E] bg-[#21262D] rounded px-2 py-1.5">
          💡 {helpText}
        </p>
      )}
      {description && (
        <p className="text-xs italic text-[#6E7681]">{description}</p>
      )}
    </div>
  );
}

export default function ChainSightPanel({
  symbols,
  filters,
  isLoading = false,
  className = '',
}: ChainSightPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [chainData, setChainData] = useState<ChainSightData | null>(null);
  const [isFetching, setIsFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchChainSight = useCallback(async () => {
    if (symbols.length === 0) {
      setChainData(null);
      return;
    }

    setIsFetching(true);
    setError(null);

    try {
      const response = await screenerService.getChainSight(symbols, filters);
      if (response.success) {
        setChainData(response.data);
      } else {
        setError('데이터를 불러오는데 실패했습니다.');
      }
    } catch (err) {
      console.error('Chain Sight fetch error:', err);
      setError('연관 종목을 분석하는 중 오류가 발생했습니다.');
    } finally {
      setIsFetching(false);
    }
  }, [symbols, filters]);

  // Auto-fetch when symbols change
  useEffect(() => {
    if (symbols.length > 0) {
      fetchChainSight();
    }
  }, [symbols.length]); // Only re-fetch when symbols count changes

  const handleRefresh = () => {
    fetchChainSight();
  };

  const showLoading = isLoading || isFetching;
  const hasData = chainData && (chainData.sector_peers.length > 0 || chainData.fundamental_similar.length > 0);

  return (
    <div
      className={`rounded-lg border border-[#30363D] bg-[#161B22] ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#30363D] px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">🧬</span>
          <h2 className="text-base font-semibold text-[#E6EDF3]">
            연관 종목 DNA
          </h2>
          {hasData && (
            <span className="rounded-full bg-[#1F6FEB]/20 px-2 py-0.5 text-xs font-medium text-[#58A6FF]">
              {chainData.chains_count}개 발견
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={showLoading || symbols.length === 0}
            className="rounded p-1 text-[#8B949E] transition-colors hover:bg-[#30363D] hover:text-[#E6EDF3] disabled:opacity-50"
            title="새로고침"
          >
            <RefreshCw className={`h-4 w-4 ${showLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="rounded p-1 text-[#8B949E] transition-colors hover:bg-[#30363D] hover:text-[#E6EDF3]"
            title={isCollapsed ? '펼치기' : '접기'}
          >
            {isCollapsed ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronUp className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className="space-y-4 p-4">
          {/* Error State */}
          {error && !showLoading && (
            <div className="flex items-center gap-2 rounded-lg border border-[#F85149]/30 bg-[#F85149]/10 p-3">
              <AlertCircle className="h-4 w-4 text-[#F85149]" />
              <p className="text-sm text-[#F85149]">{error}</p>
              <button
                onClick={handleRefresh}
                className="ml-auto text-xs text-[#58A6FF] hover:underline"
              >
                다시 시도
              </button>
            </div>
          )}

          {/* Empty State - No symbols */}
          {!showLoading && !error && symbols.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="mb-2 text-4xl">🔍</div>
              <p className="text-sm text-[#8B949E]">
                필터링된 종목이 없습니다
              </p>
              <p className="mt-1 text-xs text-[#6E7681]">
                필터를 조정하여 종목을 검색해보세요
              </p>
            </div>
          )}

          {/* Empty State - No related stocks found */}
          {!showLoading && !error && symbols.length > 0 && chainData && !hasData && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="mb-2 text-4xl">🧬</div>
              <p className="text-sm text-[#8B949E]">
                연관 종목을 찾지 못했습니다
              </p>
              <p className="mt-1 text-xs text-[#6E7681]">
                다른 필터 조건으로 검색해보세요
              </p>
            </div>
          )}

          {/* Loading State */}
          {showLoading && (
            <>
              <ChainSection
                title="섹터 피어"
                description=""
                helpText=""
                stocks={[]}
                isLoading={true}
              />
              <ChainSection
                title="유사 펀더멘탈"
                description=""
                helpText=""
                stocks={[]}
                isLoading={true}
              />
            </>
          )}

          {/* Data Display */}
          {!showLoading && !error && hasData && (
            <>
              {/* Sector Peers */}
              {chainData.sector_peers.length > 0 && (() => {
                // 섹터 피어의 섹터 목록 추출
                const sectors = [...new Set(
                  chainData.sector_peers
                    .map(s => s.metrics?.sector)
                    .filter(Boolean)
                )];
                const sectorText = sectors.length > 0 ? sectors.join(', ') : '';

                return (
                  <ChainSection
                    title="섹터 피어"
                    helpText={`선택한 종목과 같은 섹터(${sectorText || '동일 산업군'})에 속하면서 PER, ROE, 시가총액 등 펀더멘탈 지표가 유사한 기업들입니다. 같은 산업 내 경쟁사나 유사 비즈니스 모델을 가진 기업을 발견할 수 있습니다.`}
                    description=""
                    stocks={chainData.sector_peers}
                    isLoading={false}
                  />
                );
              })()}

              {/* Fundamental Similar */}
              {chainData.fundamental_similar.length > 0 && (() => {
                // 유사 펀더멘탈의 섹터 목록 추출 (다양한 섹터)
                const sectors = [...new Set(
                  chainData.fundamental_similar
                    .map(s => s.metrics?.sector)
                    .filter(Boolean)
                )];
                const sectorText = sectors.length > 0 ? sectors.slice(0, 3).join(', ') : '';

                return (
                  <ChainSection
                    title="유사 펀더멘탈"
                    helpText={`선택한 종목과 다른 섹터(${sectorText || '타 산업군'})에 속하지만, PER, ROE, 시가총액 등 재무 지표가 유사한 기업들입니다. 업종은 다르지만 비슷한 밸류에이션과 수익성을 가진 투자 대안을 찾을 수 있습니다.`}
                    description=""
                    stocks={chainData.fundamental_similar}
                    isLoading={false}
                  />
                );
              })()}

              {/* AI Insights */}
              {chainData.ai_insights && (
                <div className="rounded-lg border border-[#1F6FEB]/30 bg-[#1F6FEB]/10 p-3">
                  <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-[#58A6FF]">
                    <Sparkles className="h-3.5 w-3.5" />
                    AI 인사이트
                  </div>
                  <p className="text-sm leading-relaxed text-[#E6EDF3]">
                    {chainData.ai_insights}
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
