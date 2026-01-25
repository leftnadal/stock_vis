'use client';

import { memo } from 'react';
import Link from 'next/link';
import type { MarketMoverItem } from '@/types/market';
import { ArrowUpRight, ArrowDownRight, Info } from 'lucide-react';
import { KeywordList } from '@/components/keywords/KeywordList';
import { useKeywords } from '@/hooks/useKeywords';

interface MoverCardProps {
  mover: MarketMoverItem;
  showKeywords?: boolean;
}

export const MoverCard = memo(function MoverCard({ mover, showKeywords = true }: MoverCardProps) {
  const changePercent = parseFloat(mover.change_percent);
  const isPositive = changePercent > 0;

  // 키워드 조회 (optional)
  const { data: keywordData, isLoading: keywordsLoading, error: keywordsError } = useKeywords(
    mover.symbol,
    undefined,
  );
  const keywords = keywordData?.data?.keywords ?? [];

  // RVOL 색상 결정
  const getRvolColor = (rvol: string) => {
    const rvolNum = parseFloat(rvol || '0');
    if (rvolNum > 2.0) return 'text-red-600 dark:text-red-400';
    if (rvolNum > 1.5) return 'text-orange-500 dark:text-orange-400';
    return 'text-gray-500 dark:text-gray-400';
  };

  // 추세강도 색상 결정
  const getTrendColor = (trend: string) => {
    const trendNum = parseFloat(trend || '0');
    if (trendNum > 0.7) return 'text-green-600 dark:text-green-400';
    if (trendNum < -0.7) return 'text-red-600 dark:text-red-400';
    return 'text-gray-500 dark:text-gray-400';
  };

  // 섹터 알파 색상 결정
  const getAlphaColor = (alpha: string) => {
    if (!alpha || alpha === 'N/A') return 'text-gray-500 dark:text-gray-400';
    const alphaNum = parseFloat(alpha);
    if (alphaNum > 0) return 'text-green-600 dark:text-green-400';
    if (alphaNum < 0) return 'text-red-600 dark:text-red-400';
    return 'text-gray-500 dark:text-gray-400';
  };

  // ETF 동행률 색상 결정
  const getSyncColor = (sync: string) => {
    if (!sync || sync === 'N/A') return 'text-gray-500 dark:text-gray-400';
    const syncNum = parseFloat(sync);
    if (syncNum >= 0.8) return 'text-blue-600 dark:text-blue-400';
    if (syncNum >= 0.5) return 'text-gray-600 dark:text-gray-400';
    return 'text-orange-500 dark:text-orange-400';
  };

  // 변동성 백분위 색상 결정
  const getVolatilityColor = (vol: string) => {
    if (!vol || vol === 'N/A') return 'text-gray-500 dark:text-gray-400';
    const volNum = parseFloat(vol);
    if (volNum >= 90) return 'text-red-600 dark:text-red-400';
    if (volNum >= 70) return 'text-orange-500 dark:text-orange-400';
    return 'text-gray-500 dark:text-gray-400';
  };

  // 가격 포맷팅
  const formatPrice = (price: string) => {
    const priceNum = parseFloat(price);
    if (priceNum >= 1000) {
      return priceNum.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    if (priceNum >= 1) {
      return priceNum.toFixed(2);
    }
    return priceNum.toFixed(4);
  };

  return (
    <Link
      href={`/stocks/${mover.symbol}`}
      className="group flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors border border-transparent hover:border-gray-200 dark:hover:border-gray-600"
    >
      {/* 순위 */}
      <div className="w-5 text-center pt-1">
        <span className="text-xs font-medium text-gray-400 dark:text-gray-500">
          {mover.rank}
        </span>
      </div>

      {/* 종목 정보 */}
      <div className="flex-1 min-w-0">
        {/* 상단: 심볼 + 회사명 */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-semibold text-gray-900 dark:text-white">
            {mover.symbol}
          </span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
          {mover.company_name}
        </p>
        {/* 섹터/산업 정보 */}
        {(mover.sector || mover.industry) && (
          <p className="text-[10px] text-gray-400 dark:text-gray-500 truncate mb-1.5">
            {[mover.sector, mover.industry].filter(Boolean).join(' · ')}
          </p>
        )}
        {!mover.sector && !mover.industry && <div className="mb-2" />}

        {/* LLM 키워드 (선택 사항) */}
        {showKeywords && (
          <div className="mb-2">
            <KeywordList
              keywords={keywords}
              isLoading={keywordsLoading}
              error={keywordsError}
              maxVisible={3}
              size="sm"
              layout="horizontal"
            />
          </div>
        )}

        {/* 하단: 지표 5개 (2줄) */}
        <div className="space-y-1">
          {/* 1줄: RVOL, 추세, 알파 */}
          <div className="flex items-center gap-3 text-xs">
            {/* RVOL */}
            <div className="flex items-center gap-1 group/tooltip relative">
              <span className="text-gray-400">RVOL</span>
              <span className={`font-medium ${getRvolColor(mover.rvol || '0')}`}>
                {mover.rvol_display}
              </span>
              <Info className="w-3 h-3 text-gray-300 dark:text-gray-600 cursor-help" />
              <div className="absolute bottom-full left-0 mb-1 hidden group-hover/tooltip:block z-10 w-48 p-2 bg-gray-900 dark:bg-gray-700 text-white text-[10px] rounded shadow-lg">
                평소 대비 거래량 배수. 2.0 이상이면 비정상적 관심도.
              </div>
            </div>

            {/* 추세강도 */}
            <div className="flex items-center gap-1 group/tooltip relative">
              <span className="text-gray-400">추세</span>
              <span className={`font-medium ${getTrendColor(mover.trend_strength || '0')}`}>
                {mover.trend_display}
              </span>
              <Info className="w-3 h-3 text-gray-300 dark:text-gray-600 cursor-help" />
              <div className="absolute bottom-full left-0 mb-1 hidden group-hover/tooltip:block z-10 w-48 p-2 bg-gray-900 dark:bg-gray-700 text-white text-[10px] rounded shadow-lg">
                (종가-시가)/(고가-저가). ±0.7 이상이면 강한 방향성.
              </div>
            </div>

            {/* 섹터 알파 */}
            <div className="flex items-center gap-1 group/tooltip relative">
              <span className="text-gray-400">알파</span>
              <span className={`font-medium ${getAlphaColor(mover.sector_alpha_display)}`}>
                {mover.sector_alpha_display}
              </span>
              <Info className="w-3 h-3 text-gray-300 dark:text-gray-600 cursor-help" />
              <div className="absolute bottom-full left-0 mb-1 hidden group-hover/tooltip:block z-10 w-48 p-2 bg-gray-900 dark:bg-gray-700 text-white text-[10px] rounded shadow-lg">
                섹터 ETF 대비 초과 수익률. 양수면 섹터 평균보다 우수.
              </div>
            </div>
          </div>

          {/* 2줄: ETF 동행률, 변동성 */}
          <div className="flex items-center gap-3 text-xs">
            {/* ETF 동행률 */}
            <div className="flex items-center gap-1 group/tooltip relative">
              <span className="text-gray-400">동행</span>
              <span className={`font-medium ${getSyncColor(mover.etf_sync_display)}`}>
                {mover.etf_sync_display}
              </span>
              <Info className="w-3 h-3 text-gray-300 dark:text-gray-600 cursor-help" />
              <div className="absolute bottom-full left-0 mb-1 hidden group-hover/tooltip:block z-10 w-48 p-2 bg-gray-900 dark:bg-gray-700 text-white text-[10px] rounded shadow-lg">
                섹터 ETF와의 동조율 (0~1). 0.8 이상이면 강한 동조.
              </div>
            </div>

            {/* 변동성 백분위 */}
            <div className="flex items-center gap-1 group/tooltip relative">
              <span className="text-gray-400">변동성</span>
              <span className={`font-medium ${getVolatilityColor(mover.volatility_pct_display)}`}>
                P{mover.volatility_pct_display}
              </span>
              <Info className="w-3 h-3 text-gray-300 dark:text-gray-600 cursor-help" />
              <div className="absolute bottom-full left-0 mb-1 hidden group-hover/tooltip:block z-10 w-48 p-2 bg-gray-900 dark:bg-gray-700 text-white text-[10px] rounded shadow-lg">
                변동성 백분위 (0~100). 90 이상이면 매우 높은 변동성.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 가격 정보 */}
      <div className="text-right">
        <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
          ${formatPrice(mover.price)}
        </p>
        {/* 변동률 배지 */}
        <div
          className={`
            inline-flex items-center gap-0.5 px-2 py-0.5 rounded-md text-xs font-semibold
            ${isPositive
              ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400'
              : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
            }
          `}
        >
          {isPositive ? (
            <ArrowUpRight className="w-3 h-3" />
          ) : (
            <ArrowDownRight className="w-3 h-3" />
          )}
          <span>{Math.abs(changePercent).toFixed(2)}%</span>
        </div>
      </div>
    </Link>
  );
});
