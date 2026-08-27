'use client';

import Link from 'next/link';
import { ArrowUpRight, ArrowDownRight, Network } from 'lucide-react';
import { MiniSparkline } from './MiniSparkline';
import { NewsContextBadge } from './NewsContextBadge';
import { ConfidenceBadge } from './ConfidenceBadge';
import { AxisChipStrip } from './AxisChipStrip';
import { buildTechnicalDetail } from './technicalLabels';
import { CHANGE_TEXT } from '@/components/common/colorSemantics';
import type { SignalStock } from '@/types/eod';

interface StockRowProps {
  stock: SignalStock;
  /** 전 카드 합류 축 수(useConfluenceMap). 미로딩·미존재=0 → 합류 칩 생략(정칙 ⑴). */
  axisCount?: number;
}

function formatPrice(price: number): string {
  if (price >= 1000) {
    return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (price >= 1) return price.toFixed(2);
  return price.toFixed(4);
}

function formatVolume(volume: number): string {
  if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(1)}M`;
  if (volume >= 1_000) return `${(volume / 1_000).toFixed(0)}K`;
  return volume.toString();
}

// 체급($) 압축 표기 — 시총·거래대금. 정칙 ⑸(합류 배지-체급 문맥 결박).
function formatCompactUSD(value: number | null | undefined): string | null {
  if (value == null || value <= 0) return null;
  if (value >= 1_000_000_000_000) return `$${(value / 1_000_000_000_000).toFixed(1)}T`;
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(0)}M`;
  return `$${(value / 1_000).toFixed(0)}K`;
}

export function StockRow({ stock, axisCount = 0 }: StockRowProps) {
  const isPositive = stock.change_percent >= 0;
  const marketCapText = formatCompactUSD(stock.market_cap);
  const dollarVolumeText = formatCompactUSD(stock.dollar_volume);
  // 기술 칸 4값 전체(RSI·52주·MA) — technical 부재/전결측 시 빈 배열 → 무렌더(정칙 ⑴).
  const technicalDetail = buildTechnicalDetail(stock.technical);

  return (
    <div className="group px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-700/40 rounded-lg transition-colors border border-transparent hover:border-gray-200 dark:hover:border-gray-600">
      {/* 상단 행: 종목 + 스파크라인 + 가격 */}
      <div className="flex items-center gap-2">
        {/* 종목 정보 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <Link
              href={`/stocks/${stock.symbol}`}
              className="text-sm font-bold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              {stock.symbol}
            </Link>
            {(stock.chain_sight_cta || process.env.NEXT_PUBLIC_FORCE_CHAIN_SIGHT === 'true') && (
              <Link
                href={`/stocks/${stock.symbol}?tab=chain-sight`}
                className="text-purple-500 dark:text-purple-400 hover:text-purple-600 dark:hover:text-purple-300 transition-colors"
                title="Chain Sight 연계 분석"
              >
                <Network className="w-3 h-3" />
              </Link>
            )}
            <ConfidenceBadge score={stock.composite_score} />
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[140px]">
            {stock.company_name}
          </p>
        </div>

        {/* 스파크라인 */}
        <div className="flex-shrink-0">
          <MiniSparkline data={stock.mini_chart_20d} width={64} height={24} />
        </div>

        {/* 가격 */}
        <div className="text-right flex-shrink-0 min-w-[72px]">
          <p className="text-sm font-semibold text-gray-900 dark:text-white">
            ${formatPrice(stock.close_price)}
          </p>
          <div
            className={`inline-flex items-center gap-0.5 text-xs font-semibold ${
              isPositive ? CHANGE_TEXT.up : CHANGE_TEXT.down
            }`}
          >
            {isPositive ? (
              <ArrowUpRight className="w-3 h-3" />
            ) : (
              <ArrowDownRight className="w-3 h-3" />
            )}
            {Math.abs(stock.change_percent).toFixed(2)}%
          </div>
        </div>
      </div>

      {/* 직교 축 칩 슬롯 (합류·섹터·뉴스 + 미래 축) — 데이터 없는 축은 자연 생략(정칙 ⑴) */}
      <AxisChipStrip stock={stock} axisCount={axisCount} />

      {/* 시그널 레이블 + 체급(시총·거래대금·거래량) — 정칙 ⑸ 문맥 결박 */}
      <div className="flex items-center justify-between mt-1 mb-1.5 gap-2">
        <span className="text-[11px] text-blue-600 dark:text-blue-400 font-medium truncate">
          {stock.signal_label}
        </span>
        <span className="text-[11px] text-gray-400 dark:text-gray-500 flex-shrink-0 flex items-center gap-1.5">
          {marketCapText && <span title="시가총액">시총 {marketCapText}</span>}
          {dollarVolumeText && <span title="거래대금">대금 {dollarVolumeText}</span>}
          <span>거래량 {formatVolume(stock.volume)}</span>
        </span>
      </div>

      {/* 기술 칸: RSI·52주·MA 4값 전체(정칙 ⑴로 present만·매매어 없음 정칙 ⑵). technical 부재 시 무렌더. */}
      {technicalDetail.length > 0 && (
        <p className="text-[10px] text-gray-400 dark:text-gray-500 mb-1">
          {technicalDetail.join(' · ')}
        </p>
      )}

      {/* 뉴스 컨텍스트 */}
      {stock.news_context?.headline && (
        <NewsContextBadge news={stock.news_context} />
      )}
    </div>
  );
}
