'use client';

import React from 'react';
import Link from 'next/link';
import { TrendingUp, TrendingDown, Minus, Building2, BarChart3, ChevronRight } from 'lucide-react';

interface Keyword {
  id?: string;
  text: string;
  category?: string;
  confidence?: number;
}

interface MobileStockCardProps {
  symbol: string;
  companyName?: string;
  name?: string;
  sector?: string;
  price?: number;
  changePercent?: number;
  changesPercentage?: number;
  marketCap?: number;
  mktCap?: number;
  volume?: number;
  pe?: number;
  peRatio?: number;
  roe?: number;
  dividendYield?: number;
  beta?: number;
  keywords?: string[] | Keyword[];
  isLoadingKeywords?: boolean;
  onClick?: () => void;
}

function normalizeKeywords(keywords: string[] | Keyword[] | undefined): Keyword[] {
  if (!keywords || keywords.length === 0) return [];

  if (typeof keywords[0] === 'string') {
    return (keywords as string[]).map((text, i) => ({
      id: `kw-${i}`,
      text,
    }));
  }

  return keywords as Keyword[];
}

function formatMarketCap(value: number | undefined): string {
  if (!value) return '-';
  if (value >= 1_000_000_000_000) {
    return `$${(value / 1_000_000_000_000).toFixed(1)}T`;
  }
  if (value >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  return `$${value.toLocaleString()}`;
}

function formatVolume(value: number | undefined): string {
  if (!value) return '-';
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toLocaleString();
}

export default function MobileStockCard({
  symbol,
  companyName,
  name,
  sector,
  price,
  changePercent,
  changesPercentage,
  marketCap,
  mktCap,
  volume,
  pe,
  peRatio,
  roe,
  dividendYield,
  beta,
  keywords,
  isLoadingKeywords,
  onClick,
}: MobileStockCardProps) {
  const displayName = companyName || name || symbol;
  const displayChangePercent = changePercent ?? changesPercentage ?? 0;
  const displayMarketCap = marketCap || mktCap;
  const displayPE = pe ?? peRatio;

  const changeColor =
    displayChangePercent > 0
      ? 'text-[#3FB950]'
      : displayChangePercent < 0
      ? 'text-[#F85149]'
      : 'text-[#8B949E]';

  const changeBgColor =
    displayChangePercent > 0
      ? 'bg-[#238636]/20'
      : displayChangePercent < 0
      ? 'bg-[#F85149]/20'
      : 'bg-[#30363D]';

  const ChangeIcon =
    displayChangePercent > 0
      ? TrendingUp
      : displayChangePercent < 0
      ? TrendingDown
      : Minus;

  const normalizedKeywords = normalizeKeywords(keywords);

  return (
    <div
      className="rounded-lg border border-[#30363D] bg-[#161B22] p-4 transition-colors hover:border-[#58A6FF]/50"
      onClick={onClick}
    >
      {/* Header: Symbol & Price */}
      <div className="mb-3 flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Link
              href={`/stocks/${symbol}`}
              className="text-lg font-bold text-[#58A6FF] hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {symbol}
            </Link>
            <span className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-medium ${changeBgColor} ${changeColor}`}>
              <ChangeIcon className="h-3 w-3" />
              {displayChangePercent > 0 ? '+' : ''}
              {displayChangePercent.toFixed(2)}%
            </span>
          </div>
          <p className="mt-0.5 truncate text-sm text-[#8B949E]">{displayName}</p>
        </div>
        <div className="text-right">
          <p className="text-lg font-semibold text-[#E6EDF3]">
            ${price?.toFixed(2) || '-'}
          </p>
        </div>
      </div>

      {/* Sector */}
      {sector && (
        <div className="mb-3 flex items-center gap-1.5 text-xs text-[#8B949E]">
          <Building2 className="h-3.5 w-3.5" />
          <span>{sector}</span>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="mb-3 grid grid-cols-3 gap-2 rounded-lg bg-[#0D1117] p-2">
        <div className="text-center">
          <p className="text-[10px] uppercase text-[#6E7681]">시가총액</p>
          <p className="text-sm font-medium text-[#E6EDF3]">
            {formatMarketCap(displayMarketCap)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-[10px] uppercase text-[#6E7681]">PER</p>
          <p className="text-sm font-medium text-[#E6EDF3]">
            {displayPE?.toFixed(1) || '-'}
          </p>
        </div>
        <div className="text-center">
          <p className="text-[10px] uppercase text-[#6E7681]">거래량</p>
          <p className="text-sm font-medium text-[#E6EDF3]">
            {formatVolume(volume)}
          </p>
        </div>
      </div>

      {/* Additional Metrics */}
      <div className="mb-3 flex flex-wrap gap-2 text-xs">
        {roe !== undefined && roe !== null && (
          <span className="rounded bg-[#21262D] px-2 py-1 text-[#E6EDF3]">
            ROE <span className="font-medium">{roe.toFixed(1)}%</span>
          </span>
        )}
        {dividendYield !== undefined && dividendYield !== null && dividendYield > 0 && (
          <span className="rounded bg-[#21262D] px-2 py-1 text-[#E6EDF3]">
            배당 <span className="font-medium">{dividendYield.toFixed(2)}%</span>
          </span>
        )}
        {beta !== undefined && beta !== null && (
          <span className="rounded bg-[#21262D] px-2 py-1 text-[#E6EDF3]">
            베타 <span className="font-medium">{beta.toFixed(2)}</span>
          </span>
        )}
      </div>

      {/* Keywords */}
      {isLoadingKeywords ? (
        <div className="flex gap-1">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-5 w-16 animate-pulse rounded bg-[#30363D]"
            />
          ))}
        </div>
      ) : normalizedKeywords.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {normalizedKeywords.slice(0, 3).map((kw, idx) => (
            <span
              key={kw.id || idx}
              className="rounded bg-[#1F6FEB]/20 px-2 py-0.5 text-xs text-[#58A6FF]"
            >
              {kw.text}
            </span>
          ))}
        </div>
      ) : null}

      {/* View Details Link */}
      <Link
        href={`/stocks/${symbol}`}
        className="mt-3 flex items-center justify-center gap-1 rounded-lg bg-[#21262D] py-2 text-xs font-medium text-[#8B949E] transition-colors hover:bg-[#30363D] hover:text-[#E6EDF3]"
        onClick={(e) => e.stopPropagation()}
      >
        <BarChart3 className="h-3.5 w-3.5" />
        상세 분석
        <ChevronRight className="h-3.5 w-3.5" />
      </Link>
    </div>
  );
}
